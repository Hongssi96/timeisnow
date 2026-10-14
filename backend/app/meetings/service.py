"""Meeting core business rules: creation, confirmation, transitions, invites and membership.

계약 기준: meeting_api.md·Notion 16절 v0.76. 비참여자·탈퇴자는 존재를 노출하지 않도록 404로 처리한다.
"""
import base64
import hashlib
import json
from datetime import datetime, timezone
import secrets
from uuid import UUID, uuid4

from psycopg.types.json import Jsonb

from app.auth import security
from app.common.database import database
from app.common.errors import AuthError
from app.common.response import answer
from app.common.timeutil import iso
from app.meetings import repository
from app.meetings.dto import checked_idempotency_key, meeting_id_value

MEETING_STATUSES = ('draft', 'confirmed', 'completed', 'cancelled')


def missing_meeting():
    raise AuthError(404, 'RESOURCE_NOT_FOUND', '약속을 찾을 수 없어요. 이미 삭제됐거나 참여하지 않은 약속이에요.')


def missing_invite():
    raise AuthError(404, 'INVITE_UNAVAILABLE', '사용할 수 없는 초대예요. 만료되었거나 이미 사용된 초대입니다.')


def missing_job():
    raise AuthError(404, 'RESOURCE_NOT_FOUND', '작업을 찾을 수 없어요. 이미 정리되었거나 다른 회원의 작업이에요.')


def role_required():
    raise AuthError(403, 'MEETING_ROLE_REQUIRED', '약속 주최자만 할 수 있는 작업이에요.')


def digest(value):
    return hashlib.sha256(value.encode()).hexdigest()


def body_fingerprint(body):
    return digest(json.dumps(body.model_dump(mode='json'), sort_keys=True))


def invite_usable(invite):
    return (invite['revoked_at'] is None and invite['accepted_at'] is None
            and invite['expires_at'] > datetime.now(timezone.utc))


def member_data(row):
    return {'member_id': str(row['id']), 'display_name': row['display_name'], 'role': row['role'],
            'participation_status': row['participation_status'], 'origin_ready': False, 'version': row['version']}


def destination_data(snapshot):
    return {'name': snapshot['name'], 'latitude': float(snapshot['latitude']),
            'longitude': float(snapshot['longitude']), 'provider': snapshot.get('provider'),
            'place_ref': snapshot.get('place_ref')}


def revision_data(row):
    return {'revision_id': str(row['id']), 'revision_no': row['revision_no'],
            'target_arrival_at': iso(row['target_arrival_at']), 'timezone': row['timezone'],
            'destination': destination_data(row['destination_snapshot']), 'confirmed_at': iso(row['confirmed_at'])}


def meeting_data(meeting, members, revision):
    organizer = next(member for member in members if member['role'] == 'organizer')
    return {'meeting_id': str(meeting['id']), 'title': meeting['title'], 'status': meeting['status'],
            'version': meeting['version'], 'organizer_member_id': str(organizer['id']),
            'max_members': meeting['max_members'], 'member_count': len(members),
            'current_revision': revision_data(revision) if revision else None,
            'members': [member_data(member) for member in members],
            'created_at': iso(meeting['created_at']), 'updated_at': iso(meeting['updated_at'])}


def members_and_revision(connection, meeting_id):
    members = repository.list_active_members(connection, [str(meeting_id)])
    revision = repository.latest_revision(connection, meeting_id)
    return members, revision


def check_version(meeting, expected_version):
    if expected_version != meeting['version']:
        raise AuthError(409, 'VERSION_CONFLICT', '약속이 다른 화면에서 변경됐어요. 새로 확인해주세요.',
                        details=[{'field': 'expected_version', 'current_version': meeting['version']}])


def entered_meeting(connection, request, meeting_id, write, organizer=False, lock=False):
    """Active participation is required before anything about the meeting is revealed."""
    user_id = security.authenticated(connection, request, write)
    if lock:
        repository.advisory_lock(connection, 'meeting-write:' + str(meeting_id))
    member = repository.find_member(connection, meeting_id, user_id)
    if not member or member['participation_status'] != 'active':
        missing_meeting()
    meeting = repository.find_meeting_for_update(connection, meeting_id) if lock \
        else repository.find_meeting(connection, meeting_id)
    if not meeting:
        missing_meeting()
    if organizer and member['role'] != 'organizer':
        role_required()
    return meeting, member


def encode_cursor(meeting_id, status):
    raw = json.dumps({'m': str(meeting_id), 's': status}, separators=(',', ':')).encode()
    return base64.urlsafe_b64encode(raw).decode()


def decode_cursor(cursor):
    try:
        data = json.loads(base64.urlsafe_b64decode(cursor.encode()))
        if set(data) != {'m', 's'} or not isinstance(data['m'], str):
            raise ValueError('cursor shape')
        if data['s'] is not None and data['s'] not in MEETING_STATUSES:
            raise ValueError('cursor status')
        return UUID(data['m']), data['s']
    except (ValueError, TypeError, KeyError, UnicodeDecodeError):
        raise AuthError(422, 'VALIDATION_ERROR', '목록 조회 위치를 확인해주세요.') from None


def create(request, body):
    key = checked_idempotency_key(request)
    fingerprint = body_fingerprint(body)
    with database() as connection:
        user_id = security.authenticated(connection, request, True)
        repository.delete_expired_keys(connection)
        repository.advisory_lock(connection, 'meeting-create:' + str(user_id) + ':' + key)
        previous = repository.find_idempotency_key(connection, user_id, 'meeting-create', key)
        if previous:
            if previous['body_hash'] != fingerprint:
                raise AuthError(409, 'IDEMPOTENCY_CONFLICT', '다른 생성 요청이에요. 다시 확인해주세요.')
            if previous['meeting_id'] is None:
                missing_meeting()
            meeting = repository.find_meeting(connection, previous['meeting_id'])
            if not meeting:
                missing_meeting()
            members, revision = members_and_revision(connection, meeting['id'])
            return meeting_data(meeting, members, revision)
        meeting = repository.insert_meeting(connection, (uuid4(), user_id, body.title))
        repository.insert_member(connection, (uuid4(), meeting['id'], user_id, 'organizer'))
        repository.insert_idempotency_key(connection, (user_id, 'meeting-create', key, fingerprint, meeting['id']))
        members, revision = members_and_revision(connection, meeting['id'])
        data = meeting_data(meeting, members, revision)
    return data


def listing(request, status, cursor, limit):
    if status is not None and status not in MEETING_STATUSES:
        raise AuthError(422, 'VALIDATION_ERROR', '약속 상태 값을 확인해주세요.')
    cursor_id, cursor_status = decode_cursor(cursor) if cursor is not None else (None, None)
    if cursor is not None and cursor_status != status:
        raise AuthError(422, 'VALIDATION_ERROR', '목록 필터가 바뀌면 이전 조회 위치를 재사용할 수 없어요. 처음부터 다시 조회해주세요.')
    with database() as connection:
        user_id = security.authenticated(connection, request)
        cursor_time = None
        if cursor_id is not None:
            boundary = repository.find_meeting_created_at(connection, cursor_id, user_id)
            if not boundary:
                raise AuthError(422, 'VALIDATION_ERROR', '목록 조회 위치를 확인해주세요.')
            cursor_time = boundary['created_at']
        rows = repository.list_meetings(connection, user_id, status, cursor_id, cursor_time, limit)
        items = rows[:limit]
        members = repository.list_active_members(connection, [str(row['id']) for row in items]) if items else []
        revisions = repository.latest_revisions(connection, [str(row['id']) for row in items]) if items else []
        grouped = {}
        for member in members:
            grouped.setdefault(member['meeting_id'], []).append(member)
        revision_by_meeting = {row['meeting_id']: row for row in revisions}
        data = {'items': [meeting_data(row, grouped.get(row['id'], []), revision_by_meeting.get(row['id'])) for row in items],
                'next_cursor': encode_cursor(rows[limit - 1]['id'], status) if len(rows) > limit else None}
    return data


def detail(request, meeting_id):
    with database() as connection:
        meeting, _ = entered_meeting(connection, request, meeting_id_value(meeting_id), write=False)
        members, revision = members_and_revision(connection, meeting['id'])
        data = meeting_data(meeting, members, revision)
    return data


def update(request, meeting_id, body):
    with database() as connection:
        meeting, _ = entered_meeting(connection, request, meeting_id_value(meeting_id), write=True,
                                     organizer=True, lock=True)
        if meeting['status'] in ('completed', 'cancelled'):
            raise AuthError(409, 'MEETING_CLOSED', '종료되거나 취소된 약속은 변경할 수 없어요.')
        check_version(meeting, body.expected_version)
        meeting = repository.update_meeting_title(connection, meeting['id'], body.title)
        members, revision = members_and_revision(connection, meeting['id'])
        data = meeting_data(meeting, members, revision)
    return data


def confirm(request, meeting_id, body):
    with database() as connection:
        meeting, member = entered_meeting(connection, request, meeting_id_value(meeting_id), write=True,
                                          organizer=True, lock=True)
        if meeting['status'] in ('completed', 'cancelled'):
            raise AuthError(409, 'MEETING_CLOSED', '종료되거나 취소된 약속은 확정할 수 없어요.')
        check_version(meeting, body.expected_version)
        if body.target_arrival_at <= repository.db_now(connection):
            raise AuthError(422, 'VALIDATION_ERROR', '목표 도착 시각은 미래 시각으로 보내주세요.')
        revision = repository.insert_revision(connection, (uuid4(), meeting['id'],
                                                           repository.next_revision_no(connection, meeting['id']),
                                                           body.target_arrival_at, body.timezone,
                                                           Jsonb(body.destination.model_dump()), member['id']))
        meeting = repository.confirm_meeting(connection, meeting['id'])
        members, _ = members_and_revision(connection, meeting['id'])
        data = {'meeting': meeting_data(meeting, members, revision), 'revision': revision_data(revision)}
    return data


def transition(request, meeting_id, body):
    with database() as connection:
        meeting, _ = entered_meeting(connection, request, meeting_id_value(meeting_id), write=True,
                                     organizer=True, lock=True)
        check_version(meeting, body.expected_version)
        if body.status == 'completed':
            if meeting['status'] == 'draft':
                raise AuthError(409, 'MEETING_NOT_CONFIRMED', '먼저 약속 장소와 시각을 확정해주세요.')
            if meeting['status'] != 'confirmed':
                raise AuthError(409, 'MEETING_CLOSED', '이미 종료되거나 취소된 약속이에요.')
        elif meeting['status'] in ('completed', 'cancelled'):
            raise AuthError(409, 'MEETING_CLOSED', '이미 종료되거나 취소된 약속이에요.')
        meeting = repository.close_meeting(connection, meeting['id'], body.status)
        members, revision = members_and_revision(connection, meeting['id'])
        data = meeting_data(meeting, members, revision)
    return data


def delete(request, meeting_id, expected_version):
    with database() as connection:
        meeting, member = entered_meeting(connection, request, meeting_id_value(meeting_id), write=True,
                                          organizer=True, lock=True)
        check_version(meeting, expected_version)
        job = repository.insert_job(connection, (uuid4(), member['user_id']))
        repository.delete_meeting(connection, meeting['id'])
        repository.finish_job(connection, job['id'])
    return {'job_id': str(job['id'])}


def issue_invite(request, meeting_id, body):
    key = checked_idempotency_key(request)
    fingerprint = body_fingerprint(body)
    with database() as connection:
        user_id = security.authenticated(connection, request, True)
        repository.delete_expired_keys(connection)
        repository.advisory_lock(connection, 'meeting-invite:' + str(user_id) + ':' + key)
        previous = repository.find_idempotency_key(connection, user_id, 'invite-issue', key)
        if previous:
            # Token responses are never stored, so a lost response always needs a new key.
            if previous['body_hash'] == fingerprint:
                raise AuthError(409, 'INVITE_RESPONSE_EXPIRED', '초대 응답을 다시 만들 수 없어요. 새 요청 키로 다시 발급해주세요.')
            raise AuthError(409, 'IDEMPOTENCY_CONFLICT', '다른 발급 요청이에요. 다시 확인해주세요.')
        meeting, member = entered_meeting(connection, request, meeting_id_value(meeting_id), write=True,
                                          organizer=True, lock=True)
        if meeting['status'] in ('completed', 'cancelled'):
            raise AuthError(409, 'MEETING_CLOSED', '종료되거나 취소된 약속은 초대를 발급할 수 없어요.')
        check_version(meeting, body.expected_version)
        if repository.count_active_members(connection, meeting['id']) >= meeting['max_members']:
            raise AuthError(409, 'MEETING_FULL', '참여 인원이 가득 찼어요.')
        repository.revoke_active_invites(connection, meeting['id'])
        token = secrets.token_urlsafe(32)
        invite = repository.insert_invite(connection, (uuid4(), meeting['id'], member['id'], digest(token)))
        repository.insert_idempotency_key(connection, (user_id, 'invite-issue', key, fingerprint, None))
        meeting = repository.bump_meeting_version(connection, meeting['id'])
        data = {'invite_id': str(invite['id']), 'token': token, 'expires_at': iso(invite['expires_at']),
                'meeting_version': meeting['version']}
    return data


def revoke_invite(request, meeting_id, invite_id, expected_version):
    with database() as connection:
        meeting, _ = entered_meeting(connection, request, meeting_id_value(meeting_id), write=True,
                                     organizer=True, lock=True)
        check_version(meeting, expected_version)
        invite = repository.find_invite(connection, meeting['id'], meeting_id_value(invite_id))
        if not invite or not invite_usable(invite):
            missing_invite()
        repository.revoke_invite(connection, invite['id'])
        repository.bump_meeting_version(connection, meeting['id'])
    return None


def preview(request, body):
    with database() as connection:
        user_id = security.authenticated(connection, request)
        _, secret, _ = security.settings()
        limit_key = security.bucket(connection, 'meeting-invite-preview', str(user_id), 60, 10, secret)
        security.increment(connection, limit_key)
        invite = repository.find_invite_by_token(connection, digest(body.token))
        if not invite or not invite_usable(invite):
            missing_invite()
        meeting = repository.find_meeting(connection, invite['meeting_id'])
        if not meeting or meeting['status'] not in ('draft', 'confirmed'):
            missing_invite()
        members = repository.list_active_members(connection, [str(meeting['id'])])
        organizer = next(member for member in members if member['role'] == 'organizer')
        data = {'title': meeting['title'], 'organizer_display_name': organizer['display_name'],
                'member_count': len(members), 'max_members': meeting['max_members'],
                'expires_at': iso(invite['expires_at'])}
    return data


def accept(request, body):
    key = checked_idempotency_key(request)
    fingerprint = body_fingerprint(body)
    with database() as connection:
        user_id = security.authenticated(connection, request, True)
        repository.delete_expired_keys(connection)
        repository.advisory_lock(connection, 'meeting-accept:' + str(user_id) + ':' + key)
        previous = repository.find_idempotency_key(connection, user_id, 'invite-accept', key)
        if previous and previous['body_hash'] != fingerprint:
            raise AuthError(409, 'IDEMPOTENCY_CONFLICT', '다른 수락 요청이에요. 다시 확인해주세요.')
        invite = repository.find_invite_by_token(connection, digest(body.token))
        if not invite:
            missing_invite()
        meeting_id = invite['meeting_id']
        repository.advisory_lock(connection, 'meeting-write:' + str(meeting_id))
        meeting = repository.find_meeting_for_update(connection, meeting_id)
        if not meeting:
            missing_invite()
        member = repository.find_member(connection, meeting_id, user_id)
        if member and member['participation_status'] == 'active':
            if invite['accepted_by_user_id'] != user_id:
                missing_invite()
            # Same member re-accepting the same token is a deterministic replay.
            if not previous:
                repository.insert_idempotency_key(connection, (user_id, 'invite-accept', key, fingerprint, meeting_id))
            member = repository.find_member_with_name(connection, member['id'])
            return {'meeting_id': str(meeting_id), 'member': member_data(member), 'meeting_version': meeting['version']}
        if meeting['status'] not in ('draft', 'confirmed') or not invite_usable(invite):
            missing_invite()
        if repository.count_active_members(connection, meeting_id) >= meeting['max_members']:
            raise AuthError(409, 'MEETING_FULL', '참여 인원이 가득 찼어요.')
        if member:
            member = repository.reactivate_member(connection, member['id'])
        else:
            member = repository.insert_member(connection, (uuid4(), meeting_id, user_id, 'participant'))
        repository.consume_invite(connection, invite['id'], user_id)
        if not previous:
            repository.insert_idempotency_key(connection, (user_id, 'invite-accept', key, fingerprint, meeting_id))
        meeting = repository.bump_meeting_version(connection, meeting_id)
        member = repository.find_member_with_name(connection, member['id'])
        data = {'meeting_id': str(meeting_id), 'member': member_data(member), 'meeting_version': meeting['version']}
    return data


def leave(request, meeting_id, expected_version):
    with database() as connection:
        meeting, member = entered_meeting(connection, request, meeting_id_value(meeting_id), write=True, lock=True)
        if member['role'] == 'organizer':
            raise AuthError(409, 'ORGANIZER_CANNOT_LEAVE', '주최자는 약속을 탈퇴할 수 없어요. 약속을 삭제하거나 종료해주세요.')
        if expected_version != member['version']:
            raise AuthError(409, 'VERSION_CONFLICT', '참여 정보가 다른 화면에서 변경됐어요. 새로 확인해주세요.',
                            details=[{'field': 'expected_version', 'current_version': member['version']}])
        repository.leave_member(connection, member['id'])
        repository.bump_meeting_version(connection, meeting['id'])
    return None


def job_result(request, job_id):
    """GET /jobs/{job_id} fallback for meeting deletion jobs; journey jobs stay in journeys."""
    with database() as connection:
        user_id = security.authenticated(connection, request)
        repository.delete_expired_jobs(connection)
        row = repository.find_job(connection, meeting_id_value(job_id), user_id)
    if not row:
        missing_job()
    expired = row['expires_at'] <= datetime.now(timezone.utc)
    return answer(request, {'job_id': str(row['id']), 'status': row['status'], 'error': row['error'],
                            'result_ref': None,
                            'finished_at': iso(row['finished_at']) if row['finished_at'] else None,
                            'expires_at': iso(row['expires_at']), 'result_expired': expired})
