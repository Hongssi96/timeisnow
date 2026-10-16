"""Rule-level unit tests through injected test doubles: no database, no HTTP.

MeetingService는 추상 포트(MeetingRepository·Identity·Database·Clock)만 알기 때문에
같은 생성자에 메모리 구현체를 주입하면 도메인 규칙만 따로 검증할 수 있다.
HTTP 경로와 PostgreSQL 어댑터는 test_meetings.py가 함께 확인한다.
"""
import unittest
from contextlib import contextmanager
from datetime import datetime, timezone
from uuid import uuid4

from app.common.errors import AuthError
from app.common.ports import Clock, Database, Identity
from app.meetings.dto import MeetingUpdateInput, TransitionInput
from app.meetings.repository import MeetingRepository, PostgresMeetingRepository
from app.meetings.service import MeetingService


class InMemoryMeetingRepository(MeetingRepository):
    """Implements the operations these rules touch; the rest stays unused."""

    def __init__(self, meeting, member):
        self.meeting = meeting
        self.member = member
        self.locked = []

    def advisory_lock(self, connection, key):
        self.locked.append(key)

    def find_member(self, connection, meeting_id, user_id):
        if self.member and self.member['meeting_id'] == meeting_id:
            return self.member
        return None

    def find_meeting(self, connection, meeting_id):
        return self.meeting

    def find_meeting_for_update(self, connection, meeting_id):
        return self.meeting

    def _unused(self, *args, **kwargs):
        raise NotImplementedError('not exercised by these rule tests')

    db_now = _unused
    delete_expired_keys = _unused
    delete_expired_jobs = _unused
    find_idempotency_key = _unused
    insert_idempotency_key = _unused
    insert_meeting = _unused
    insert_member = _unused
    find_member_with_name = _unused
    count_active_members = _unused
    list_active_members = _unused
    find_meeting_created_at = _unused
    list_meetings = _unused
    latest_revision = _unused
    latest_revisions = _unused
    next_revision_no = _unused
    insert_revision = _unused
    update_meeting_title = _unused
    confirm_meeting = _unused
    close_meeting = _unused
    bump_meeting_version = _unused
    delete_meeting = _unused
    revoke_active_invites = _unused
    insert_invite = _unused
    find_invite = _unused
    find_invite_by_token = _unused
    find_invite_by_id = _unused
    consume_invite = _unused
    revoke_invite = _unused
    update_member_origin = _unused
    update_member_sharing = _unused
    find_reusable_journey = _unused
    insert_meeting_journey = _unused
    supersede_meeting_journeys = _unused
    update_journey_candidate = _unused
    find_meeting_journey = _unused
    insert_share_event = _unused
    find_share_event = _unused
    find_share_event_by_client = _unused
    find_latest_arrival = _unused
    bump_arrival_version = _unused
    find_invite_replay = _unused
    insert_invite_replay = _unused
    drop_invite_replays = _unused
    drop_meeting_invite_replays = _unused
    delete_expired_replays = _unused
    reactivate_member = _unused
    leave_member = _unused
    insert_job = _unused
    finish_job = _unused
    find_job = _unused


class FixedIdentity(Identity):
    def __init__(self, user_id):
        self.user_id = user_id
        self.write_calls = []

    def authenticate(self, connection, request, write=False):
        if write:
            self.write_calls.append(request)
        return self.user_id

    def throttle(self, connection, scope, value, seconds, maximum):
        return None


class ImmediateDatabase(Database):
    @contextmanager
    def connect(self):
        yield object()


class FrozenClock(Clock):
    def __init__(self, now):
        self.fixed = now

    def now(self):
        return self.fixed


def meeting_row(status='confirmed', version=3):
    return {'id': uuid4(), 'user_id': 'u1', 'title': '점심 약속', 'status': status, 'version': version,
            'max_members': 2, 'created_at': datetime(2026, 10, 14, 9, 0, tzinfo=timezone.utc),
            'updated_at': datetime(2026, 10, 14, 9, 0, tzinfo=timezone.utc)}


def member_row(meeting_id, role='organizer', status='active', version=1):
    return {'id': uuid4(), 'meeting_id': meeting_id, 'user_id': 'u1', 'display_name': '나', 'role': role,
            'participation_status': status, 'version': version}


def build_service(meeting, member, now=datetime(2026, 10, 14, 12, 0, tzinfo=timezone.utc)):
    repository = InMemoryMeetingRepository(meeting, member)
    identity = FixedIdentity('u1')
    service = MeetingService(repository=repository, database=ImmediateDatabase(),
                             identity=identity, clock=FrozenClock(now), tokens=None)
    return service, repository, identity


class PortContractTests(unittest.TestCase):
    def test_port_cannot_be_instantiated(self):
        with self.assertRaises(TypeError):
            MeetingRepository()

    def test_postgres_adapter_satisfies_port(self):
        self.assertIsInstance(PostgresMeetingRepository(), MeetingRepository)


class MeetingRuleTests(unittest.TestCase):
    def test_update_rejects_stale_version(self):
        meeting = meeting_row(version=3)
        member = member_row(meeting['id'])
        service, _, _ = build_service(meeting, member)
        with self.assertRaises(AuthError) as caught:
            service.update(object(), str(meeting['id']), MeetingUpdateInput(expected_version=2, title='새 제목'))
        self.assertEqual((caught.exception.status, caught.exception.code), (409, 'VERSION_CONFLICT'))
        self.assertEqual(caught.exception.details[0]['current_version'], 3)

    def test_closed_meeting_rejects_update(self):
        meeting = meeting_row(status='completed', version=5)
        member = member_row(meeting['id'])
        service, _, _ = build_service(meeting, member)
        with self.assertRaises(AuthError) as caught:
            service.update(object(), str(meeting['id']), MeetingUpdateInput(expected_version=5, title='새 제목'))
        self.assertEqual((caught.exception.status, caught.exception.code), (409, 'MEETING_CLOSED'))

    def test_draft_meeting_cannot_be_completed(self):
        meeting = meeting_row(status='draft', version=1)
        member = member_row(meeting['id'])
        service, _, _ = build_service(meeting, member)
        with self.assertRaises(AuthError) as caught:
            service.transition(object(), str(meeting['id']), TransitionInput(expected_version=1, status='completed'))
        self.assertEqual((caught.exception.status, caught.exception.code), (409, 'MEETING_NOT_CONFIRMED'))

    def test_organizer_cannot_leave(self):
        meeting = meeting_row(version=1)
        member = member_row(meeting['id'], role='organizer')
        service, repository, _ = build_service(meeting, member)
        with self.assertRaises(AuthError) as caught:
            service.leave(object(), str(meeting['id']), 1)
        self.assertEqual((caught.exception.status, caught.exception.code), (409, 'ORGANIZER_CANNOT_LEAVE'))
        self.assertEqual(repository.locked, ['meeting-write:' + str(meeting['id'])],
                         'member changes must take the meeting write lock first')

    def test_write_paths_authenticate_with_csrf(self):
        meeting = meeting_row(version=3)
        member = member_row(meeting['id'])
        service, _, identity = build_service(meeting, member)
        request = object()
        with self.assertRaises(AuthError):
            service.update(request, str(meeting['id']), MeetingUpdateInput(expected_version=2, title='새 제목'))
        self.assertEqual(identity.write_calls, [request],
                         'write endpoints must go through the CSRF-checked identity')
