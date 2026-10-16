"""Meeting core business rules: creation, confirmation, transitions, invites and membership.

계약 기준: meeting_api.md·Notion 16절. 비참여자·탈퇴자는 존재를 노출하지 않도록 404로 처리한다.
협업 객체(repository·database·identity·clock·tokens)는 생성자로 주입받는다. 순수 계산은
모듈 수준 함수에 남겨 두었다.
"""
import base64
import hashlib
import json
from datetime import datetime, timedelta, timezone
from decimal import Decimal, ROUND_CEILING
from uuid import UUID, uuid4, uuid5, NAMESPACE_URL
from app.common.errors import AuthError
from app.common.ports import Clock, Database, Identity, TokenIssuer
from app.common.response import answer
from app.common.timeutil import iso
from app.journeys import service as journeys
from app.meetings.dto import checked_idempotency_key, meeting_id_value
from app.meetings.repository import MeetingRepository

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


def invite_usable(invite, now):
    return (invite['revoked_at'] is None and invite['accepted_at'] is None
            and invite['expires_at'] > now)


def member_data(row):
    return {'member_id': str(row['id']), 'display_name': row['display_name'], 'role': row['role'],
            'participation_status': row['participation_status'],
            'origin_ready': row['private_origin'] is not None, 'version': row['version']}


def share_event_digest(body):
    """Body fingerprint for arrival/correction retransmission checks."""
    return hashlib.sha256(json.dumps(body.model_dump(mode='json'), sort_keys=True,
                                     ensure_ascii=False).encode('utf-8')).hexdigest()


def meeting_trip_summary(connection, meeting_id, member_id):
    from app.trips import repository as trip_repository
    return trip_repository.meeting_trip_summary(connection, meeting_id, member_id)


def share_time(value):
    """jsonb correction fields come back as strings; DB timestamps stay datetimes."""
    if value is None or isinstance(value, datetime):
        return value
    return datetime.fromisoformat(str(value).replace('Z', '+00:00'))


def share_eta(snapshot, now):
    """Server-estimated arrival from the trip's stored guidance, valid until min(calculation+120s, evidence)."""
    departure = snapshot.get('departure') or {}
    calculated = departure.get('calculated_at')
    alighting = departure.get('estimated_final_alighting_at')
    if not calculated or not alighting:
        return None
    legs = (snapshot.get('candidate') or {}).get('ordered_legs') or []
    last_vehicle = -1
    for index, leg in enumerate(legs):
        if leg.get('type') != 'WALKING':
            last_vehicle = index
    if last_vehicle < 0:
        return None
    tail = legs[last_vehicle + 1:]
    if not tail or not all(leg.get('type') == 'WALKING' and leg.get('walking_role') == 'egress'
                           and leg.get('seconds', 0) > 0 for leg in tail):
        return None
    calculated_at = datetime.fromisoformat(str(calculated).replace('Z', '+00:00'))
    estimated = datetime.fromisoformat(str(alighting).replace('Z', '+00:00')) + timedelta(
        seconds=sum(leg['seconds'] for leg in tail))
    valid_until = calculated_at + timedelta(seconds=120)
    evidence_until = (departure.get('arrival_evidence') or {}).get('valid_until')
    if evidence_until:
        until = datetime.fromisoformat(str(evidence_until).replace('Z', '+00:00'))
        if until < valid_until:
            valid_until = until
    if now > valid_until:
        return None
    return {'estimated_arrival_at': estimated, 'eta_calculated_at': calculated_at, 'valid_until': valid_until}


def origin_data(row):
    if row['private_origin'] is None:
        return None
    return {'origin': row['private_origin'], 'origin_version': row['origin_version'],
            'recommendation_consent': row['recommendation_consent'], 'updated_at': iso(row['updated_at'])}


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


def check_version(meeting, expected_version):
    if expected_version != meeting['version']:
        raise AuthError(409, 'VERSION_CONFLICT', '약속이 다른 화면에서 변경됐어요. 새로 확인해주세요.',
                        details=[{'field': 'expected_version', 'current_version': meeting['version']}])


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


class MeetingService:
    """Meeting use cases. Collaborators arrive through the constructor (의존성 주입)."""

    def __init__(self, repository: MeetingRepository, database: Database, identity: Identity,
                 clock: Clock, tokens: TokenIssuer):
        self.repository = repository
        self.database = database
        self.identity = identity
        self.clock = clock
        self.tokens = tokens

    def _members_and_revision(self, connection, meeting_id):
        members = self.repository.list_active_members(connection, [str(meeting_id)])
        revision = self.repository.latest_revision(connection, meeting_id)
        return members, revision

    def _entered(self, connection, request, meeting_id, write, organizer=False, lock=False):
        """Active participation is required before anything about the meeting is revealed."""
        user_id = self.identity.authenticate(connection, request, write)
        if lock:
            self.repository.advisory_lock(connection, 'meeting-write:' + str(meeting_id))
        member = self.repository.find_member(connection, meeting_id, user_id)
        if not member or member['participation_status'] != 'active':
            missing_meeting()
        meeting = self.repository.find_meeting_for_update(connection, meeting_id) if lock \
            else self.repository.find_meeting(connection, meeting_id)
        if not meeting:
            missing_meeting()
        if organizer and member['role'] != 'organizer':
            role_required()
        return meeting, member

    def create(self, request, body):
        key = checked_idempotency_key(request)
        fingerprint = body_fingerprint(body)
        with self.database.connect() as connection:
            user_id = self.identity.authenticate(connection, request, True)
            self.repository.delete_expired_keys(connection)
            self.repository.advisory_lock(connection, 'meeting-create:' + str(user_id) + ':' + key)
            previous = self.repository.find_idempotency_key(connection, user_id, 'meeting-create', key)
            if previous:
                if previous['body_hash'] != fingerprint:
                    raise AuthError(409, 'IDEMPOTENCY_CONFLICT', '다른 생성 요청이에요. 다시 확인해주세요.')
                if previous['meeting_id'] is None:
                    missing_meeting()
                meeting = self.repository.find_meeting(connection, previous['meeting_id'])
                if not meeting:
                    missing_meeting()
                members, revision = self._members_and_revision(connection, meeting['id'])
                return meeting_data(meeting, members, revision)
            meeting = self.repository.insert_meeting(connection, (uuid4(), user_id, body.title))
            self.repository.insert_member(connection, (uuid4(), meeting['id'], user_id, 'organizer'))
            self.repository.insert_idempotency_key(connection, (user_id, 'meeting-create', key, fingerprint, meeting['id']))
            members, revision = self._members_and_revision(connection, meeting['id'])
            return meeting_data(meeting, members, revision)

    def listing(self, request, status, cursor, limit):
        if status is not None and status not in MEETING_STATUSES:
            raise AuthError(422, 'VALIDATION_ERROR', '약속 상태 값을 확인해주세요.')
        cursor_id, cursor_status = decode_cursor(cursor) if cursor is not None else (None, None)
        if cursor is not None and cursor_status != status:
            raise AuthError(422, 'VALIDATION_ERROR', '목록 필터가 바뀌면 이전 조회 위치를 재사용할 수 없어요. 처음부터 다시 조회해주세요.')
        with self.database.connect() as connection:
            user_id = self.identity.authenticate(connection, request)
            cursor_time = None
            if cursor_id is not None:
                boundary = self.repository.find_meeting_created_at(connection, cursor_id, user_id)
                if not boundary:
                    raise AuthError(422, 'VALIDATION_ERROR', '목록 조회 위치를 확인해주세요.')
                cursor_time = boundary['created_at']
            rows = self.repository.list_meetings(connection, user_id, status, cursor_id, cursor_time, limit)
            items = rows[:limit]
            members = self.repository.list_active_members(connection, [str(row['id']) for row in items]) if items else []
            revisions = self.repository.latest_revisions(connection, [str(row['id']) for row in items]) if items else []
            grouped = {}
            for member in members:
                grouped.setdefault(member['meeting_id'], []).append(member)
            revision_by_meeting = {row['meeting_id']: row for row in revisions}
            data = {'items': [meeting_data(row, grouped.get(row['id'], []), revision_by_meeting.get(row['id'])) for row in items],
                    'next_cursor': encode_cursor(rows[limit - 1]['id'], status) if len(rows) > limit else None}
        return data

    def detail(self, request, meeting_id):
        with self.database.connect() as connection:
            meeting, _ = self._entered(connection, request, meeting_id_value(meeting_id), write=False)
            members, revision = self._members_and_revision(connection, meeting['id'])
            return meeting_data(meeting, members, revision)

    def update(self, request, meeting_id, body):
        with self.database.connect() as connection:
            meeting, _ = self._entered(connection, request, meeting_id_value(meeting_id), write=True,
                                       organizer=True, lock=True)
            if meeting['status'] in ('completed', 'cancelled'):
                raise AuthError(409, 'MEETING_CLOSED', '종료되거나 취소된 약속은 변경할 수 없어요.')
            check_version(meeting, body.expected_version)
            meeting = self.repository.update_meeting_title(connection, meeting['id'], body.title)
            members, revision = self._members_and_revision(connection, meeting['id'])
            return meeting_data(meeting, members, revision)

    def confirm(self, request, meeting_id, body):
        with self.database.connect() as connection:
            meeting, member = self._entered(connection, request, meeting_id_value(meeting_id), write=True,
                                            organizer=True, lock=True)
            if meeting['status'] in ('completed', 'cancelled'):
                raise AuthError(409, 'MEETING_CLOSED', '종료되거나 취소된 약속은 확정할 수 없어요.')
            check_version(meeting, body.expected_version)
            if body.target_arrival_at <= self.repository.db_now(connection):
                raise AuthError(422, 'VALIDATION_ERROR', '목표 도착 시각은 미래 시각으로 보내주세요.')
            revision = self.repository.insert_revision(connection, (uuid4(), meeting['id'],
                                                                    self.repository.next_revision_no(connection, meeting['id']),
                                                                    body.target_arrival_at, body.timezone,
                                                                    body.destination.model_dump(), member['id']))
            meeting = self.repository.confirm_meeting(connection, meeting['id'])
            members, _ = self._members_and_revision(connection, meeting['id'])
            return {'meeting': meeting_data(meeting, members, revision), 'revision': revision_data(revision)}

    def transition(self, request, meeting_id, body):
        with self.database.connect() as connection:
            meeting, _ = self._entered(connection, request, meeting_id_value(meeting_id), write=True,
                                       organizer=True, lock=True)
            check_version(meeting, body.expected_version)
            if body.status == 'completed':
                if meeting['status'] == 'draft':
                    raise AuthError(409, 'MEETING_NOT_CONFIRMED', '먼저 약속 장소와 시각을 확정해주세요.')
                if meeting['status'] != 'confirmed':
                    raise AuthError(409, 'MEETING_CLOSED', '이미 종료되거나 취소된 약속이에요.')
            elif meeting['status'] in ('completed', 'cancelled'):
                raise AuthError(409, 'MEETING_CLOSED', '이미 종료되거나 취소된 약속이에요.')
            meeting = self.repository.close_meeting(connection, meeting['id'], body.status)
            members, revision = self._members_and_revision(connection, meeting['id'])
            return meeting_data(meeting, members, revision)

    def delete(self, request, meeting_id, expected_version):
        with self.database.connect() as connection:
            meeting, member = self._entered(connection, request, meeting_id_value(meeting_id), write=True,
                                            organizer=True, lock=True)
            check_version(meeting, expected_version)
            job = self.repository.insert_job(connection, (uuid4(), member['user_id']))
            self.repository.delete_meeting(connection, meeting['id'])
            self.repository.finish_job(connection, job['id'])
        return {'job_id': str(job['id'])}

    def issue_invite(self, request, meeting_id, body):
        key = checked_idempotency_key(request)
        fingerprint = body_fingerprint(body)
        with self.database.connect() as connection:
            user_id = self.identity.authenticate(connection, request, True)
            self.repository.delete_expired_keys(connection)
            self.repository.delete_expired_replays(connection)
            self.repository.advisory_lock(connection, 'meeting-invite:' + str(user_id) + ':' + key)
            previous = self.repository.find_idempotency_key(connection, user_id, 'invite-issue', key)
            if previous:
                if previous['body_hash'] != fingerprint:
                    raise AuthError(409, 'IDEMPOTENCY_CONFLICT', '다른 발급 요청이에요. 다시 확인해주세요.')
                # The encrypted cache can only reproduce a response while its invite stays usable.
                replay = self.repository.find_invite_replay(connection, user_id, key)
                invite = self.repository.find_invite_by_id(connection, replay['invite_id']) if replay else None
                if not replay or not invite or not invite_usable(invite, self.clock.now()):
                    raise AuthError(409, 'INVITE_RESPONSE_EXPIRED', '초대 응답을 다시 만들 수 없어요. 새 요청 키로 다시 발급해주세요.')
                return json.loads(replay['response_json'])
            meeting, member = self._entered(connection, request, meeting_id_value(meeting_id), write=True,
                                            organizer=True, lock=True)
            if meeting['status'] in ('completed', 'cancelled'):
                raise AuthError(409, 'MEETING_CLOSED', '종료되거나 취소된 약속은 초대를 발급할 수 없어요.')
            check_version(meeting, body.expected_version)
            if self.repository.count_active_members(connection, meeting['id']) >= meeting['max_members']:
                raise AuthError(409, 'MEETING_FULL', '참여 인원이 가득 찼어요.')
            self.repository.revoke_active_invites(connection, meeting['id'])
            self.repository.drop_meeting_invite_replays(connection, meeting['id'])
            token = self.tokens.issue()
            invite = self.repository.insert_invite(connection, (uuid4(), meeting['id'], member['id'], digest(token)))
            self.repository.insert_idempotency_key(connection, (user_id, 'invite-issue', key, fingerprint, None))
            meeting = self.repository.bump_meeting_version(connection, meeting['id'])
            response = {'invite_id': str(invite['id']), 'token': token, 'expires_at': iso(invite['expires_at']),
                        'meeting_version': meeting['version']}
            # Only the hash stays in the invite row; the replay cache holds the encrypted response.
            self.repository.insert_invite_replay(connection, (user_id, key, fingerprint, invite['id'],
                                                              json.dumps(response, sort_keys=True), invite['expires_at']))
            return response

    def revoke_invite(self, request, meeting_id, invite_id, expected_version):
        with self.database.connect() as connection:
            meeting, _ = self._entered(connection, request, meeting_id_value(meeting_id), write=True,
                                       organizer=True, lock=True)
            check_version(meeting, expected_version)
            invite = self.repository.find_invite(connection, meeting['id'], meeting_id_value(invite_id))
            if not invite or not invite_usable(invite, self.clock.now()):
                missing_invite()
            self.repository.revoke_invite(connection, invite['id'])
            self.repository.drop_invite_replays(connection, invite['id'])
            self.repository.bump_meeting_version(connection, meeting['id'])

    def preview(self, request, body):
        with self.database.connect() as connection:
            user_id = self.identity.authenticate(connection, request)
            self.identity.throttle(connection, 'meeting-invite-preview', str(user_id), 60, 10)
            invite = self.repository.find_invite_by_token(connection, digest(body.token))
            if not invite or not invite_usable(invite, self.clock.now()):
                missing_invite()
            meeting = self.repository.find_meeting(connection, invite['meeting_id'])
            if not meeting or meeting['status'] not in ('draft', 'confirmed'):
                missing_invite()
            members = self.repository.list_active_members(connection, [str(meeting['id'])])
            organizer = next(member for member in members if member['role'] == 'organizer')
            return {'title': meeting['title'], 'organizer_display_name': organizer['display_name'],
                    'member_count': len(members), 'max_members': meeting['max_members'],
                    'expires_at': iso(invite['expires_at'])}

    def accept(self, request, body):
        key = checked_idempotency_key(request)
        fingerprint = body_fingerprint(body)
        with self.database.connect() as connection:
            user_id = self.identity.authenticate(connection, request, True)
            self.repository.delete_expired_keys(connection)
            self.repository.delete_expired_replays(connection)
            self.repository.advisory_lock(connection, 'meeting-accept:' + str(user_id) + ':' + key)
            previous = self.repository.find_idempotency_key(connection, user_id, 'invite-accept', key)
            if previous and previous['body_hash'] != fingerprint:
                raise AuthError(409, 'IDEMPOTENCY_CONFLICT', '다른 수락 요청이에요. 다시 확인해주세요.')
            invite = self.repository.find_invite_by_token(connection, digest(body.token))
            if not invite:
                missing_invite()
            meeting_id = invite['meeting_id']
            self.repository.advisory_lock(connection, 'meeting-write:' + str(meeting_id))
            meeting = self.repository.find_meeting_for_update(connection, meeting_id)
            if not meeting:
                missing_invite()
            member = self.repository.find_member(connection, meeting_id, user_id)
            if member and member['participation_status'] == 'active':
                if invite['accepted_by_user_id'] != user_id:
                    missing_invite()
                # Same member re-accepting the same token is a deterministic replay.
                if not previous:
                    self.repository.insert_idempotency_key(connection, (user_id, 'invite-accept', key, fingerprint, meeting_id))
                member = self.repository.find_member_with_name(connection, member['id'])
                return {'meeting_id': str(meeting_id), 'member': member_data(member), 'meeting_version': meeting['version']}
            if meeting['status'] not in ('draft', 'confirmed') or not invite_usable(invite, self.clock.now()):
                missing_invite()
            if self.repository.count_active_members(connection, meeting_id) >= meeting['max_members']:
                raise AuthError(409, 'MEETING_FULL', '참여 인원이 가득 찼어요.')
            if member:
                member = self.repository.reactivate_member(connection, member['id'])
            else:
                member = self.repository.insert_member(connection, (uuid4(), meeting_id, user_id, 'participant'))
            self.repository.consume_invite(connection, invite['id'], user_id)
            self.repository.drop_invite_replays(connection, invite['id'])
            if not previous:
                self.repository.insert_idempotency_key(connection, (user_id, 'invite-accept', key, fingerprint, meeting_id))
            meeting = self.repository.bump_meeting_version(connection, meeting_id)
            member = self.repository.find_member_with_name(connection, member['id'])
            return {'meeting_id': str(meeting_id), 'member': member_data(member), 'meeting_version': meeting['version']}

    def leave(self, request, meeting_id, expected_version):
        with self.database.connect() as connection:
            meeting, member = self._entered(connection, request, meeting_id_value(meeting_id), write=True, lock=True)
            if member['role'] == 'organizer':
                raise AuthError(409, 'ORGANIZER_CANNOT_LEAVE', '주최자는 약속을 탈퇴할 수 없어요. 약속을 삭제하거나 종료해주세요.')
            if expected_version != member['version']:
                raise AuthError(409, 'VERSION_CONFLICT', '참여 정보가 다른 화면에서 변경됐어요. 새로 확인해주세요.',
                                details=[{'field': 'expected_version', 'current_version': member['version']}])
            self.repository.leave_member(connection, member['id'])
            self.repository.bump_meeting_version(connection, meeting['id'])

    def set_origin(self, request, meeting_id, body):
        with self.database.connect() as connection:
            meeting, member = self._entered(connection, request, meeting_id_value(meeting_id), write=True, lock=True)
            if meeting['status'] in ('completed', 'cancelled'):
                raise AuthError(409, 'MEETING_CLOSED', '종료되거나 취소된 약속은 출발지를 바꿀 수 없어요.')
            if body.expected_version != member['version']:
                raise AuthError(409, 'VERSION_CONFLICT', '참여 정보가 다른 화면에서 변경됐어요. 새로 확인해주세요.',
                                details=[{'field': 'expected_version', 'current_version': member['version']}])
            # saved_place is checked against the caller's own place and its current version.
            refs = []
            journeys.resolve(connection, member['user_id'], body.origin, refs)
            origin = body.origin.model_dump(mode='json')
            if refs:
                origin['location_version'] = refs[0]['location_version']
            row = self.repository.update_member_origin(connection, member['id'], origin, body.recommendation_consent)
            return {'private_origin': origin_data(row), 'member_version': row['version']}

    def get_origin(self, request, meeting_id):
        with self.database.connect() as connection:
            meeting, member = self._entered(connection, request, meeting_id_value(meeting_id), write=False)
            return {'private_origin': origin_data(member), 'member_version': member['version']}

    def set_sharing(self, request, meeting_id, body):
        with self.database.connect() as connection:
            meeting, member = self._entered(connection, request, meeting_id_value(meeting_id), write=True, lock=True)
            if meeting['status'] in ('completed', 'cancelled'):
                raise AuthError(409, 'MEETING_CLOSED', '종료된 약속은 공유 설정을 바꿀 수 없어요.')
            if body.expected_version != member['version']:
                raise AuthError(409, 'VERSION_CONFLICT', '참여 정보가 다른 화면에서 변경됐어요. 새로 확인해주세요.',
                                details=[{'field': 'expected_version', 'current_version': member['version']}])
            row = self.repository.update_member_sharing(connection, member['id'], body.enabled)
        return {'enabled': row['sharing_enabled'], 'member_version': row['version'],
                'updated_at': iso(row['sharing_updated_at'])}

    def shared_statuses(self, request, meeting_id):
        with self.database.connect() as connection:
            user_id = self.identity.authenticate(connection, request)
            meeting = self.repository.find_meeting(connection, meeting_id_value(meeting_id))
            if meeting is None:
                missing_meeting()
            member = self.repository.find_member(connection, meeting['id'], user_id)
            if member is None or member['participation_status'] != 'active':
                missing_meeting()
            rows = self.repository.list_active_members(connection, [meeting['id']])
            now = self.clock.now()
            items = [self.share_state(connection, row, meeting, now) for row in rows]
        return {'items': items}

    def share_state(self, connection, row, meeting, now):
        """SharedStatus for one active member; personal coordinates never leave this computation."""
        base = {'member_id': str(row['id']), 'version': row['version'],
                'updated_at': iso(row['sharing_updated_at'] or row['joined_at']),
                'state': 'unknown', 'source': 'none', 'reported_at': None,
                'estimated_arrival_at': None, 'eta_calculated_at': None, 'valid_until': None}
        if meeting['status'] != 'confirmed' or not row['sharing_enabled']:
            base['state'] = 'sharing_off'
            return base
        arrival = self.repository.find_latest_arrival(connection, row['id'])
        if arrival is not None:
            correction = arrival['correction'] or {}
            if not correction.get('excluded'):
                occurred = share_time(correction.get('occurred_at')) or arrival['occurred_at']
                updated = share_time(correction.get('received_at')) or arrival['received_at']
                return {**base, 'state': 'arrived', 'source': arrival['source'],
                        'reported_at': iso(occurred), 'updated_at': iso(updated)}
        summary = meeting_trip_summary(connection, meeting['id'], row['id'])
        if summary is not None:
            events = summary['events']
            latest = events[-1] if events else None
            if latest is not None and latest['type'] == 'arrived':
                return {**base, 'state': 'arrived', 'source': 'manual',
                        'reported_at': iso(latest['occurred_at']), 'updated_at': iso(latest['received_at'])}
            departed = next((e for e in events if e['type'] == 'departed'), None)
            if departed is not None and summary['trip']['status'] == 'active':
                boarded = next((e for e in events if e['type'] == 'boarded'), None)
                reported = boarded if boarded is not None else departed
                eta = share_eta(summary['trip']['snapshot'], now)
                state = 'in_transit' if boarded is not None else 'reported_departed'
                if eta is None:
                    return {**base, 'state': 'unavailable', 'source': 'manual',
                            'reported_at': iso(reported['occurred_at']), 'updated_at': iso(reported['received_at'])}
                return {**base, 'state': state, 'source': 'manual', 'reported_at': iso(reported['occurred_at']),
                        'estimated_arrival_at': iso(eta['estimated_arrival_at']),
                        'eta_calculated_at': iso(eta['eta_calculated_at']), 'valid_until': iso(eta['valid_until']),
                        'updated_at': iso(reported['received_at'])}
        return base

    def create_arrival(self, request, meeting_id, body):
        key = checked_idempotency_key(request)
        digest = share_event_digest(body)
        with self.database.connect() as connection:
            user_id = self.identity.authenticate(connection, request, True)
            self.repository.delete_expired_keys(connection)
            self.repository.advisory_lock(connection, 'meeting-arrival:' + str(user_id) + ':' + key)
            previous = self.repository.find_idempotency_key(connection, user_id, 'meeting-arrival', key)
            if previous is not None and previous['body_hash'] != digest:
                raise AuthError(409, 'IDEMPOTENCY_CONFLICT', '같은 도착 신고 키로 다른 내용을 보냈어요.')
            meeting, member = self._entered(connection, request, meeting_id_value(meeting_id), write=True)
            if meeting['status'] != 'confirmed':
                raise AuthError(409, 'MEETING_NOT_CONFIRMED', '먼저 약속 장소와 시각을 확정해주세요.')
            journey = self.repository.find_meeting_journey(connection, meeting_id_value(body.meeting_journey_id))
            if journey is None or journey['member_id'] != member['id']:
                raise AuthError(404, 'RESOURCE_NOT_FOUND', '안내 여정을 찾을 수 없어요.')
            event = self.repository.find_share_event_by_client(connection, member['id'],
                                                               meeting_id_value(body.client_event_id))
            if event is not None:
                if event['kind'] != 'arrival' or str(event['meeting_journey_id']) != body.meeting_journey_id \
                        or event['occurred_at'].astimezone(timezone.utc).isoformat() \
                        != body.occurred_at.astimezone(timezone.utc).isoformat() or event['source'] != body.source:
                    raise AuthError(409, 'IDEMPOTENCY_CONFLICT', '같은 도착 신고의 내용이 달라요.')
                return answer(request, {'arrival_id': str(event['id']), 'version': event['version'],
                                        'received_at': iso(event['received_at']), 'source': event['source']}, 200)
            summary = meeting_trip_summary(connection, meeting['id'], member['id'])
            trip = summary['trip'] if summary else None
            if trip is None or str(trip['meeting_journey_id'] or '') != body.meeting_journey_id:
                raise AuthError(404, 'RESOURCE_NOT_FOUND', '연결된 이동을 찾을 수 없어요.')
            if not any(e['type'] == 'departed' for e in summary['events']):
                raise AuthError(409, 'EVENT_ORDER_CONFLICT', '출발 확인 뒤에 도착을 기록할 수 있어요.')
            arrival = self.repository.insert_share_event(connection, (
                uuid4(), meeting['id'], member['id'], journey['id'], meeting_id_value(body.client_event_id),
                'arrival', body.occurred_at, body.source, False, None, None, 1))
            self.repository.insert_idempotency_key(connection, (user_id, 'meeting-arrival', key, digest, meeting['id']))
        return answer(request, {'arrival_id': str(arrival['id']), 'version': arrival['version'],
                                'received_at': iso(arrival['received_at']), 'source': arrival['source']}, 201)

    def correct_arrival(self, request, meeting_id, body):
        key = checked_idempotency_key(request)
        digest = share_event_digest(body)
        replay_id = uuid5(NAMESPACE_URL, 'meeting-correction:' + key)
        with self.database.connect() as connection:
            user_id = self.identity.authenticate(connection, request, True)
            self.repository.delete_expired_keys(connection)
            self.repository.advisory_lock(connection, 'meeting-correction:' + str(user_id) + ':' + key)
            previous = self.repository.find_idempotency_key(connection, user_id, 'meeting-correction', key)
            if previous is not None and previous['body_hash'] != digest:
                raise AuthError(409, 'IDEMPOTENCY_CONFLICT', '같은 정정 키로 다른 내용을 보냈어요.')
            replay = self.repository.find_share_event_by_client(connection, None, replay_id)
            meeting, member = self._entered(connection, request, meeting_id_value(meeting_id), write=True)
            if meeting['status'] == 'cancelled':
                raise AuthError(409, 'MEETING_CLOSED', '취소된 약속은 도착을 정정할 수 없어요.')
            if replay is not None:
                if replay['member_id'] != member['id']:
                    raise AuthError(404, 'RESOURCE_NOT_FOUND', '도착 기록을 찾을 수 없어요.')
                return answer(request, {'arrival_id': str(replay['corrects_event_id']), 'version': replay['version'],
                                        'received_at': iso(replay['received_at'])}, 200)
            arrival = self.repository.find_share_event(connection, meeting_id_value(body.arrival_id))
            if arrival is None or arrival['member_id'] != member['id'] or arrival['kind'] != 'arrival' \
                    or str(arrival['meeting_id']) != str(meeting['id']):
                raise AuthError(404, 'RESOURCE_NOT_FOUND', '도착 기록을 찾을 수 없어요.')
            if body.expected_version != arrival['version']:
                raise AuthError(409, 'VERSION_CONFLICT', '이미 다른 정정이 반영됐어요. 최신 기록을 확인해주세요.',
                                details=[{'field': 'expected_version', 'current_version': arrival['version']}])
            occurred_at = body.occurred_at if body.occurred_at is not None else arrival['occurred_at']
            latest = self.repository.find_latest_arrival(connection, member['id'])
            carried = bool((latest['correction'] or {}).get('excluded')) \
                if latest is not None and str(latest['id']) == str(arrival['id']) else False
            excluded = carried if body.excluded is None else body.excluded
            correction = self.repository.insert_share_event(connection, (
                uuid4(), meeting['id'], member['id'], arrival['meeting_journey_id'], replay_id, 'correction',
                occurred_at, arrival['source'], excluded, body.correction_reason, arrival['id'], arrival['version'] + 1))
            updated = self.repository.bump_arrival_version(connection, arrival['id'], arrival['version'] + 1)
            self.repository.insert_idempotency_key(connection, (user_id, 'meeting-correction', key, digest, meeting['id']))
        return answer(request, {'arrival_id': str(updated['id']), 'version': updated['version'],
                                'received_at': iso(correction['received_at'])}, 201)

    def job_result(self, request, job_id):
        """GET /jobs/{job_id} fallback for meeting deletion jobs; journey jobs stay in journeys."""
        with self.database.connect() as connection:
            user_id = self.identity.authenticate(connection, request)
            self.repository.delete_expired_jobs(connection)
            row = self.repository.find_job(connection, meeting_id_value(job_id), user_id)
        if not row:
            missing_job()
        expired = row['expires_at'] <= self.clock.now()
        return answer(request, {'job_id': str(row['id']), 'status': row['status'], 'error': row['error'],
                                'result_ref': None,
                                'finished_at': iso(row['finished_at']) if row['finished_at'] else None,
                                'expires_at': iso(row['expires_at']), 'result_expired': expired})
