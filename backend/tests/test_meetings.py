"""Meeting core checks against real PostgreSQL/ASGI in owned temporary schemas."""
import json
import os
from datetime import datetime, timedelta, timezone
from pathlib import Path
import sys
import unittest
from unittest.mock import patch
from uuid import uuid4

from alembic import command
from alembic.config import Config
from psycopg import sql
from sqlalchemy import create_engine, pool, text

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from app.common import database as common_database
from app.common.database import connect_db, database
from test_api_contract import request

PASSWORD = 'Sample passphrase for testing 29!'
TARGET = (datetime.now(timezone.utc) + timedelta(hours=3)).isoformat()
DESTINATION = {'name': '합정역 5번 출구', 'latitude': 37.549467, 'longitude': 126.913831,
               'provider': None, 'place_ref': None}


class MeetingTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.schema = 'meeting_test_' + uuid4().hex
        with connect_db() as connection:
            connection.execute(sql.SQL('CREATE SCHEMA {}').format(sql.Identifier(self.schema)))

        def isolated():
            connection = connect_db()
            connection.execute(sql.SQL('SET search_path TO {}').format(sql.Identifier(self.schema)))
            connection.commit()
            return connection

        engine = create_engine('postgresql+psycopg://', creator=isolated, poolclass=pool.NullPool)
        try:
            with engine.connect() as connection:
                config = Config(str(Path(__file__).resolve().parents[2] / 'alembic.ini'))
                config.attributes['connection'] = connection
                command.upgrade(config, 'head')
        finally:
            engine.dispose()
        self.db_patch = patch.object(common_database, 'connect_db', isolated)
        self.db_patch.start()
        self.env_patch = patch.dict(os.environ, {'AUTH_RATE_LIMIT_SECRET': 'synthetic-secret-for-testing-32-characters',
                                                 'AUTH_ENV': 'development', 'AUTH_PUBLIC_ORIGIN': 'http://127.0.0.1:5173'})
        self.env_patch.start()
        self.sessions = {}

    def tearDown(self):
        self.db_patch.stop()
        self.env_patch.stop()
        with connect_db() as connection:
            connection.execute(sql.SQL('DROP SCHEMA {} CASCADE').format(sql.Identifier(self.schema)))

    async def call(self, path, body=None, method=None, user=None, key=None,
                   origin='http://127.0.0.1:5173', csrf=True):
        method = method or ('POST' if body is not None else 'GET')
        headers = [(b'origin', origin.encode()), (b'content-type', b'application/json')]
        session = self.sessions.get(user)
        if session:
            headers.append((b'cookie', session['cookie'].encode()))
            if csrf:
                headers.append((b'x-csrf-token', session['csrf'].encode()))
        if key is not None:
            headers.append((b'idempotency-key', key.encode()))
        payload = json.dumps(body).encode() if body is not None else b''
        query = b''
        if '?' in path:
            path, _, raw = path.partition('?')
            query = raw.encode()
        result = await request('/api/v1' + path, method, query=query, headers=headers, body=payload)
        if result[2]:
            self.assertEqual(result[1][b'x-request-id'].decode(), result[2]['meta']['request_id'])
        return result

    async def signin(self, user, email):
        status, headers, body = await self.call('/auth/csrf', user=user)
        self.assertEqual(status, 200)
        self.sessions[user] = {'cookie': headers[b'set-cookie'].decode().split(';')[0],
                               'csrf': body['data']['csrf_token']}
        self.assertEqual((await self.call('/auth/register', {'email': email, 'password': PASSWORD,
                                                             'display_name': user + '표시이름'}, user=user))[0], 201)
        logged = await self.call('/auth/login', {'email': email, 'password': PASSWORD}, user=user)
        self.assertEqual(logged[0], 200)
        self.sessions[user]['cookie'] = logged[1][b'set-cookie'].decode().split(';')[0]
        self.sessions[user]['csrf'] = logged[2]['data']['csrf_token']

    async def make_meeting(self, user='main', key='create-meeting-key', title='퇴근 후 저녁 약속'):
        status, _, body = await self.call('/meetings', {'title': title}, user=user, key=key)
        self.assertEqual(status, 201, body)
        return body['data']

    async def confirm_meeting(self, meeting_id, user='main', version=1, arrival=TARGET, destination=None, tz='Asia/Seoul'):
        body = {'expected_version': version, 'target_arrival_at': arrival, 'timezone': tz,
                'destination': destination or DESTINATION}
        return await self.call(f'/meetings/{meeting_id}/confirmations', body, user=user)

    async def invite(self, meeting_id, user='main', version=1, key=None):
        return await self.call(f'/meetings/{meeting_id}/invites', {'expected_version': version},
                               user=user, key=key or 'invite-key-' + uuid4().hex[:8])

    async def accept_invite(self, token, user, key):
        return await self.call('/meeting-invite-acceptances', {'token': token}, user=user, key=key)

    async def join(self, meeting, version, user='other'):
        invite = await self.invite(meeting['meeting_id'], version=version)
        accepted = await self.accept_invite(invite[2]['data']['token'], user, 'join-' + uuid4().hex[:8])
        self.assertEqual(accepted[0], 200, accepted[2])
        return accepted[2]['data']

    async def test_create_meeting_and_replay(self):
        await self.signin('main', 'main@example.invalid')
        meeting = await self.make_meeting()
        self.assertEqual(meeting['status'], 'draft')
        self.assertEqual(meeting['version'], 1)
        self.assertEqual(meeting['max_members'], 2)
        self.assertEqual(meeting['member_count'], 1)
        self.assertIsNone(meeting['current_revision'])
        self.assertEqual(meeting['members'][0]['role'], 'organizer')
        self.assertEqual(meeting['members'][0]['participation_status'], 'active')
        self.assertFalse(meeting['members'][0]['origin_ready'])
        self.assertEqual(meeting['members'][0]['display_name'], 'main표시이름')
        self.assertTrue(meeting['created_at'].endswith('Z'))
        replay = await self.make_meeting(key='create-meeting-key')
        self.assertEqual(replay['meeting_id'], meeting['meeting_id'])
        conflict = await self.call('/meetings', {'title': '다른 제목'}, user='main', key='create-meeting-key')
        self.assertEqual(conflict[0], 409)
        self.assertEqual(conflict[2]['error']['code'], 'IDEMPOTENCY_CONFLICT')
        missing_key = await self.call('/meetings', {'title': '제목'}, user='main')
        self.assertEqual(missing_key[0], 422)
        bad_key = await self.call('/meetings', {'title': '제목'}, user='main', key='space in key')
        self.assertEqual(bad_key[0], 422)
        empty = await self.call('/meetings', {'title': '   '}, user='main', key='other-key')
        self.assertEqual(empty[0], 422)
        with database() as connection:
            self.assertEqual(connection.execute('SELECT count(*) AS n FROM meetings').fetchone()['n'], 1)
            self.assertEqual(connection.execute("SELECT count(*) AS n FROM meeting_members WHERE role='organizer'").fetchone()['n'], 1)
        anonymous = await self.call('/meetings', {'title': '제목'}, key='anon-key')
        self.assertEqual(anonymous[0], 401)

    async def test_listing_cursor_and_filters(self):
        await self.signin('main', 'main@example.invalid')
        await self.signin('other', 'other@example.invalid')
        created = [await self.make_meeting(key=f'key-{i}', title=f'약속 {i}') for i in range(3)]
        confirmed = await self.confirm_meeting(created[0]['meeting_id'])
        self.assertEqual(confirmed[0], 201)
        status, _, body = await self.call('/meetings', user='main')
        self.assertEqual(status, 200)
        self.assertIsNone(body['data']['next_cursor'])
        self.assertEqual([item['title'] for item in body['data']['items']], ['약속 2', '약속 1', '약속 0'])
        status, _, body = await self.call('/meetings?status=confirmed', user='main')
        self.assertEqual([item['meeting_id'] for item in body['data']['items']], [created[0]['meeting_id']])
        status, _, body = await self.call('/meetings?limit=1', user='main')
        self.assertEqual(len(body['data']['items']), 1)
        first_cursor = body['data']['next_cursor']
        status, _, body = await self.call('/meetings?limit=1&cursor=' + first_cursor, user='main')
        self.assertEqual(body['data']['items'][0]['title'], '약속 1')
        reused = await self.call('/meetings?limit=1&status=draft&cursor=' + first_cursor, user='main')
        self.assertEqual(reused[0], 422)
        garbage = await self.call('/meetings?cursor=not-a-cursor', user='main')
        self.assertEqual(garbage[0], 422)
        bad_status = await self.call('/meetings?status=archived', user='main')
        self.assertEqual(bad_status[0], 422)
        stranger = await self.call('/meetings', user='other')
        self.assertEqual(stranger[2]['data']['items'], [])

    async def test_detail_access_rules(self):
        await self.signin('main', 'main@example.invalid')
        await self.signin('other', 'other@example.invalid')
        meeting = await self.make_meeting()
        detail = await self.call('/meetings/' + meeting['meeting_id'], user='main')
        self.assertEqual(detail[0], 200)
        self.assertEqual(detail[2]['data']['organizer_member_id'], meeting['organizer_member_id'])
        stranger = await self.call('/meetings/' + meeting['meeting_id'], user='other')
        self.assertEqual(stranger[0], 404)
        self.assertEqual(stranger[2]['error']['code'], 'RESOURCE_NOT_FOUND')
        invalid = await self.call('/meetings/not-a-uuid', user='main')
        self.assertEqual(invalid[0], 404)
        anonymous = await self.call('/meetings/' + meeting['meeting_id'])
        self.assertEqual(anonymous[0], 401)

    async def test_update_rules(self):
        await self.signin('main', 'main@example.invalid')
        await self.signin('other', 'other@example.invalid')
        meeting = await self.make_meeting()
        renamed = await self.call('/meetings/' + meeting['meeting_id'],
                                  {'expected_version': 1, 'title': '  새로운 약속 제목  '}, method='PATCH', user='main')
        self.assertEqual(renamed[0], 200)
        self.assertEqual(renamed[2]['data']['title'], '새로운 약속 제목')
        self.assertEqual(renamed[2]['data']['version'], 2)
        stale = await self.call('/meetings/' + meeting['meeting_id'], {'expected_version': 1, 'title': '다시'},
                                method='PATCH', user='main')
        self.assertEqual(stale[0], 409)
        self.assertEqual(stale[2]['error']['code'], 'VERSION_CONFLICT')
        self.assertEqual(stale[2]['error']['details'][0]['current_version'], 2)
        await self.join(meeting, 2)
        forbidden = await self.call('/meetings/' + meeting['meeting_id'], {'expected_version': 4, 'title': '참여자 시도'},
                                    method='PATCH', user='other')
        self.assertEqual(forbidden[0], 403)
        self.assertEqual(forbidden[2]['error']['code'], 'MEETING_ROLE_REQUIRED')
        too_long = await self.call('/meetings/' + meeting['meeting_id'], {'expected_version': 4, 'title': '가' * 101},
                                   method='PATCH', user='main')
        self.assertEqual(too_long[0], 422)
        await self.call(f'/meetings/{meeting["meeting_id"]}/transitions', {'expected_version': 4, 'status': 'cancelled'},
                        user='main')
        closed = await self.call('/meetings/' + meeting['meeting_id'], {'expected_version': 5, 'title': '종결 후 수정'},
                                 method='PATCH', user='main')
        self.assertEqual(closed[0], 409)
        self.assertEqual(closed[2]['error']['code'], 'MEETING_CLOSED')

    async def test_confirmation_rules(self):
        await self.signin('main', 'main@example.invalid')
        await self.signin('other', 'other@example.invalid')
        meeting = await self.make_meeting()
        await self.join(meeting, 1)
        participant = await self.confirm_meeting(meeting['meeting_id'], user='other')
        self.assertEqual(participant[0], 403)
        self.assertEqual(participant[2]['error']['code'], 'MEETING_ROLE_REQUIRED')
        confirmed = await self.confirm_meeting(meeting['meeting_id'], version=3)
        self.assertEqual(confirmed[0], 201)
        self.assertEqual(confirmed[2]['data']['meeting']['status'], 'confirmed')
        self.assertEqual(confirmed[2]['data']['meeting']['version'], 4)
        revision = confirmed[2]['data']['revision']
        self.assertEqual(revision['revision_no'], 1)
        self.assertEqual(revision['timezone'], 'Asia/Seoul')
        self.assertEqual(revision['destination']['name'], '합정역 5번 출구')
        self.assertEqual(revision['destination']['provider'], None)
        self.assertEqual(confirmed[2]['data']['meeting']['current_revision']['revision_id'], revision['revision_id'])
        again = await self.confirm_meeting(meeting['meeting_id'], version=4)
        self.assertEqual(again[0], 201)
        self.assertEqual(again[2]['data']['revision']['revision_no'], 2)
        past = await self.confirm_meeting(meeting['meeting_id'], version=5,
                                          arrival=(datetime.now(timezone.utc) - timedelta(minutes=1)).isoformat())
        self.assertEqual(past[0], 422)
        naive = await self.confirm_meeting(meeting['meeting_id'], version=5,
                                           arrival=datetime.now(timezone.utc).replace(tzinfo=None).isoformat())
        self.assertEqual(naive[0], 422)
        wrong_tz = await self.confirm_meeting(meeting['meeting_id'], version=5,
                                              arrival=TARGET.replace('+00:00', '+09:00'), tz='UTC')
        self.assertEqual(wrong_tz[0], 422)
        await self.call('/meetings/' + meeting['meeting_id'], {'expected_version': 5, 'title': '제목'},
                        method='PATCH', user='main')
        out_of_range = await self.confirm_meeting(meeting['meeting_id'], version=6,
                                                  destination={**DESTINATION, 'latitude': 91})
        self.assertEqual(out_of_range[0], 422)
        provider_ref = await self.confirm_meeting(meeting['meeting_id'], version=6,
                                                  destination={**DESTINATION, 'provider': 'kakao'})
        self.assertEqual(provider_ref[0], 422)
        stale = await self.confirm_meeting(meeting['meeting_id'], version=2)
        self.assertEqual(stale[0], 409)
        self.assertEqual(stale[2]['error']['details'][0]['current_version'], 6)
        extra = await self.call(f'/meetings/{meeting["meeting_id"]}/confirmations',
                                {'expected_version': 6, 'target_arrival_at': TARGET, 'timezone': 'Asia/Seoul',
                                 'destination': DESTINATION, 'recommendation_id': str(uuid4())}, user='main')
        self.assertEqual(extra[0], 422)

    async def test_transition_rules(self):
        await self.signin('main', 'main@example.invalid')
        meeting = await self.make_meeting()
        early = await self.call(f'/meetings/{meeting["meeting_id"]}/transitions',
                                {'expected_version': 1, 'status': 'completed'}, user='main')
        self.assertEqual(early[0], 409)
        self.assertEqual(early[2]['error']['code'], 'MEETING_NOT_CONFIRMED')
        await self.confirm_meeting(meeting['meeting_id'])
        cancelled = await self.call(f'/meetings/{meeting["meeting_id"]}/transitions',
                                    {'expected_version': 2, 'status': 'cancelled'}, user='main')
        self.assertEqual(cancelled[0], 200)
        self.assertEqual(cancelled[2]['data']['status'], 'cancelled')
        self.assertIsNotNone(cancelled[2]['data']['current_revision'])
        again = await self.call(f'/meetings/{meeting["meeting_id"]}/transitions',
                                {'expected_version': 3, 'status': 'completed'}, user='main')
        self.assertEqual(again[0], 409)
        self.assertEqual(again[2]['error']['code'], 'MEETING_CLOSED')
        stale = await self.call(f'/meetings/{meeting["meeting_id"]}/transitions',
                                {'expected_version': 2, 'status': 'cancelled'}, user='main')
        self.assertEqual(stale[0], 409)
        bad_status = await self.call(f'/meetings/{meeting["meeting_id"]}/transitions',
                                     {'expected_version': 3, 'status': 'paused'}, user='main')
        self.assertEqual(bad_status[0], 422)

    async def test_invite_issue_and_revoke(self):
        await self.signin('main', 'main@example.invalid')
        await self.signin('other', 'other@example.invalid')
        meeting = await self.make_meeting()
        issued = await self.invite(meeting['meeting_id'], key='first-invite-key')
        self.assertEqual(issued[0], 201)
        token = issued[2]['data']['token']
        self.assertRegex(token, r'^[A-Za-z0-9_-]{43}$')
        self.assertEqual(issued[2]['data']['meeting_version'], 2)
        expires = datetime.fromisoformat(issued[2]['data']['expires_at'].replace('Z', '+00:00'))
        self.assertLess(expires - datetime.now(timezone.utc), timedelta(hours=24, minutes=1))
        self.assertGreater(expires - datetime.now(timezone.utc), timedelta(hours=23, minutes=59))
        replay = await self.invite(meeting['meeting_id'], key='first-invite-key')
        self.assertEqual(replay[0], 409)
        self.assertEqual(replay[2]['error']['code'], 'INVITE_RESPONSE_EXPIRED')
        different = await self.invite(meeting['meeting_id'], version=2, key='first-invite-key')
        self.assertEqual(different[0], 409)
        self.assertEqual(different[2]['error']['code'], 'IDEMPOTENCY_CONFLICT')
        second = await self.invite(meeting['meeting_id'], version=2)
        self.assertEqual(second[0], 201)
        self.assertNotEqual(second[2]['data']['invite_id'], issued[2]['data']['invite_id'])
        old_preview = await self.call('/meeting-invite-previews', {'token': token}, user='other')
        self.assertEqual(old_preview[0], 404)
        self.assertEqual(old_preview[2]['error']['code'], 'INVITE_UNAVAILABLE')
        missing_key = await self.call(f'/meetings/{meeting["meeting_id"]}/invites', {'expected_version': 3}, user='main')
        self.assertEqual(missing_key[0], 422)
        second_meeting = await self.make_meeting(key='create-second', title='둘째 약속')
        second_invite = await self.invite(second_meeting['meeting_id'], key='second-invite-key')
        self.assertEqual((await self.accept_invite(second_invite[2]['data']['token'], 'other', 'other-join'))[0], 200)
        forbidden = await self.invite(second_meeting['meeting_id'], user='other', version=3)
        self.assertEqual(forbidden[0], 403)
        self.assertEqual(forbidden[2]['error']['code'], 'MEETING_ROLE_REQUIRED')
        invite_id = second[2]['data']['invite_id']
        revoked = await self.call(f'/meetings/{meeting["meeting_id"]}/invites/{invite_id}?expected_version=3',
                                  method='DELETE', user='main')
        self.assertEqual(revoked[0], 204)
        self.assertIsNone(revoked[2])
        again = await self.call(f'/meetings/{meeting["meeting_id"]}/invites/{invite_id}?expected_version=4',
                                method='DELETE', user='main')
        self.assertEqual(again[0], 404)
        self.assertEqual(again[2]['error']['code'], 'INVITE_UNAVAILABLE')
        stranger_revoke = await self.call(f'/meetings/{meeting["meeting_id"]}/invites/{invite_id}?expected_version=4',
                                          method='DELETE', user='other')
        self.assertEqual(stranger_revoke[0], 404)
        expired = await self.invite(meeting['meeting_id'], version=4)
        with database() as connection:
            connection.execute("UPDATE meeting_invites SET expires_at=now()-interval '1 second'")
        expired_revoke = await self.call(
            f'/meetings/{meeting["meeting_id"]}/invites/{expired[2]["data"]["invite_id"]}?expected_version=5',
            method='DELETE', user='main')
        self.assertEqual(expired_revoke[0], 404)

    async def test_preview_rules(self):
        await self.signin('main', 'main@example.invalid')
        await self.signin('invitee', 'invitee@example.invalid')
        meeting = await self.make_meeting(title='공원 산책 약속')
        issued = await self.invite(meeting['meeting_id'])
        token = issued[2]['data']['token']
        preview = await self.call('/meeting-invite-previews', {'token': token}, user='invitee')
        self.assertEqual(preview[0], 200)
        self.assertEqual(preview[2]['data'], {'title': '공원 산책 약속', 'organizer_display_name': 'main표시이름',
                                              'member_count': 1, 'max_members': 2,
                                              'expires_at': issued[2]['data']['expires_at']})
        unknown = await self.call('/meeting-invite-previews', {'token': 'x' * 43}, user='invitee')
        self.assertEqual(unknown[0], 404)
        self.assertEqual(unknown[2]['error']['code'], 'INVITE_UNAVAILABLE')
        accepted = await self.accept_invite(token, 'invitee', 'accept-key')
        self.assertEqual(accepted[0], 200)
        consumed = await self.call('/meeting-invite-previews', {'token': token}, user='invitee')
        self.assertEqual(consumed[0], 404)
        anonymous = await self.call('/meeting-invite-previews', {'token': token})
        self.assertEqual(anonymous[0], 401)

    async def test_preview_rate_limit(self):
        await self.signin('main', 'main@example.invalid')
        await self.signin('visitor', 'visitor@example.invalid')
        meeting = await self.make_meeting()
        issued = await self.invite(meeting['meeting_id'])
        token = issued[2]['data']['token']
        fixed_window = datetime.now(timezone.utc) + timedelta(minutes=1)
        with patch('app.auth.repository.clock_now', return_value=fixed_window):
            for _ in range(10):
                status, _, _ = await self.call('/meeting-invite-previews', {'token': token}, user='visitor')
                self.assertEqual(status, 200)
            limited = await self.call('/meeting-invite-previews', {'token': token}, user='visitor')
        self.assertEqual(limited[0], 429)
        self.assertEqual(limited[2]['error']['code'], 'RATE_LIMITED')

    async def test_acceptance_flow(self):
        await self.signin('main', 'main@example.invalid')
        await self.signin('invitee', 'invitee@example.invalid')
        await self.signin('third', 'third@example.invalid')
        meeting = await self.make_meeting()
        issued = await self.invite(meeting['meeting_id'])
        token = issued[2]['data']['token']
        missing_key = await self.call('/meeting-invite-acceptances', {'token': token}, user='invitee')
        self.assertEqual(missing_key[0], 422)
        accepted = await self.accept_invite(token, 'invitee', 'accept-once')
        self.assertEqual(accepted[0], 200)
        data = accepted[2]['data']
        self.assertEqual(data['meeting_id'], meeting['meeting_id'])
        self.assertEqual(data['member']['role'], 'participant')
        self.assertEqual(data['member']['display_name'], 'invitee표시이름')
        self.assertEqual(data['meeting_version'], 3)
        member_id = data['member']['member_id']
        again = await self.accept_invite(token, 'invitee', 'accept-once')
        self.assertEqual(again[0], 200)
        self.assertEqual(again[2]['data']['member']['member_id'], member_id)
        self.assertEqual(again[2]['data']['meeting_version'], 3)
        stranger = await self.accept_invite(token, 'third', 'accept-stranger')
        self.assertEqual(stranger[0], 404)
        detail = await self.call('/meetings/' + meeting['meeting_id'], user='main')
        self.assertEqual(detail[2]['data']['member_count'], 2)
        self.assertEqual(len(detail[2]['data']['members']), 2)
        no_csrf = await self.call('/meeting-invite-acceptances', {'token': token}, user='third',
                                  key='accept-no-csrf', csrf=False)
        self.assertEqual(no_csrf[0], 403)
        conflict = await self.call('/meeting-invite-acceptances', {'token': 'y' * 43}, user='invitee',
                                   key='accept-once')
        self.assertEqual(conflict[0], 409)
        self.assertEqual(conflict[2]['error']['code'], 'IDEMPOTENCY_CONFLICT')

    async def test_acceptance_full_meeting(self):
        await self.signin('main', 'main@example.invalid')
        await self.signin('invitee', 'invitee@example.invalid')
        await self.signin('third', 'third@example.invalid')
        meeting = await self.make_meeting()
        issued = await self.invite(meeting['meeting_id'])
        token = issued[2]['data']['token']
        with database() as connection:
            user_id = connection.execute("SELECT id FROM users WHERE display_name='third표시이름'").fetchone()['id']
            connection.execute("INSERT INTO meeting_members(id,meeting_id,user_id,role) VALUES(%s,%s,%s,'participant')",
                               (uuid4(), meeting['meeting_id'], user_id))
        full = await self.accept_invite(token, 'invitee', 'accept-full')
        self.assertEqual(full[0], 409)
        self.assertEqual(full[2]['error']['code'], 'MEETING_FULL')

    async def test_rejoin_after_leaving(self):
        await self.signin('main', 'main@example.invalid')
        await self.signin('invitee', 'invitee@example.invalid')
        meeting = await self.make_meeting()
        issued = await self.invite(meeting['meeting_id'])
        member = (await self.accept_invite(issued[2]['data']['token'], 'invitee', 'join-1'))[2]['data']['member']
        left = await self.call(f'/meetings/{meeting["meeting_id"]}/members/me?expected_version=1',
                               method='DELETE', user='invitee')
        self.assertEqual(left[0], 204)
        hidden = await self.call('/meetings/' + meeting['meeting_id'], user='invitee')
        self.assertEqual(hidden[0], 404)
        listing = await self.call('/meetings', user='invitee')
        self.assertEqual(listing[2]['data']['items'], [])
        organizer_view = await self.call('/meetings/' + meeting['meeting_id'], user='main')
        self.assertEqual(organizer_view[2]['data']['member_count'], 1)
        second = await self.invite(meeting['meeting_id'], version=4)
        rejoined = await self.accept_invite(second[2]['data']['token'], 'invitee', 'join-2')
        self.assertEqual(rejoined[0], 200)
        self.assertEqual(rejoined[2]['data']['member']['member_id'], member['member_id'])
        self.assertEqual(rejoined[2]['data']['member']['participation_status'], 'active')
        self.assertEqual(rejoined[2]['data']['member']['version'], 3)

    async def test_leave_rules(self):
        await self.signin('main', 'main@example.invalid')
        await self.signin('invitee', 'invitee@example.invalid')
        meeting = await self.make_meeting()
        organizer_leave = await self.call(f'/meetings/{meeting["meeting_id"]}/members/me?expected_version=1',
                                          method='DELETE', user='main')
        self.assertEqual(organizer_leave[0], 409)
        self.assertEqual(organizer_leave[2]['error']['code'], 'ORGANIZER_CANNOT_LEAVE')
        issued = await self.invite(meeting['meeting_id'])
        await self.accept_invite(issued[2]['data']['token'], 'invitee', 'join')
        stale = await self.call(f'/meetings/{meeting["meeting_id"]}/members/me?expected_version=99',
                                method='DELETE', user='invitee')
        self.assertEqual(stale[0], 409)
        self.assertEqual(stale[2]['error']['details'][0]['current_version'], 1)
        left = await self.call(f'/meetings/{meeting["meeting_id"]}/members/me?expected_version=1',
                               method='DELETE', user='invitee')
        self.assertEqual(left[0], 204)
        stranger = await self.call(f'/meetings/{meeting["meeting_id"]}/members/me?expected_version=1',
                                   method='DELETE')
        self.assertEqual(stranger[0], 401)

    async def test_delete_meeting_and_job_lookup(self):
        await self.signin('main', 'main@example.invalid')
        await self.signin('invitee', 'invitee@example.invalid')
        meeting = await self.make_meeting()
        issued = await self.invite(meeting['meeting_id'])
        await self.accept_invite(issued[2]['data']['token'], 'invitee', 'join')
        forbidden = await self.call(f'/meetings/{meeting["meeting_id"]}?expected_version=3',
                                    method='DELETE', user='invitee')
        self.assertEqual(forbidden[0], 403)
        self.assertEqual(forbidden[2]['error']['code'], 'MEETING_ROLE_REQUIRED')
        stale = await self.call(f'/meetings/{meeting["meeting_id"]}?expected_version=1',
                                method='DELETE', user='main')
        self.assertEqual(stale[0], 409)
        missing_query = await self.call(f'/meetings/{meeting["meeting_id"]}', method='DELETE', user='main')
        self.assertEqual(missing_query[0], 422)
        deleted = await self.call(f'/meetings/{meeting["meeting_id"]}?expected_version=3',
                                  method='DELETE', user='main')
        self.assertEqual(deleted[0], 202)
        job_id = deleted[2]['data']['job_id']
        gone = await self.call('/meetings/' + meeting['meeting_id'], user='main')
        self.assertEqual(gone[0], 404)
        gone_for_invitee = await self.call('/meetings/' + meeting['meeting_id'], user='invitee')
        self.assertEqual(gone_for_invitee[0], 404)
        job = await self.call('/jobs/' + job_id, user='main')
        self.assertEqual(job[0], 200)
        self.assertEqual(job[2]['data']['status'], 'succeeded')
        self.assertIsNone(job[2]['data']['result_ref'])
        self.assertIsNotNone(job[2]['data']['finished_at'])
        stranger_job = await self.call('/jobs/' + job_id, user='invitee')
        self.assertEqual(stranger_job[0], 404)
        unknown_job = await self.call('/jobs/' + uuid4().hex, user='main')
        self.assertEqual(unknown_job[0], 404)
        with database() as connection:
            self.assertEqual(connection.execute('SELECT count(*) AS n FROM meetings').fetchone()['n'], 0)
            self.assertEqual(connection.execute('SELECT count(*) AS n FROM meeting_members').fetchone()['n'], 0)
            self.assertEqual(connection.execute('SELECT count(*) AS n FROM meeting_invites').fetchone()['n'], 0)
            self.assertEqual(connection.execute("SELECT count(*) AS n FROM jobs WHERE type='meeting_delete'").fetchone()['n'], 1)

    async def test_closed_meeting_blocks_invites(self):
        await self.signin('main', 'main@example.invalid')
        meeting = await self.make_meeting()
        await self.call(f'/meetings/{meeting["meeting_id"]}/transitions',
                        {'expected_version': 1, 'status': 'cancelled'}, user='main')
        closed = await self.invite(meeting['meeting_id'], version=2)
        self.assertEqual(closed[0], 409)
        self.assertEqual(closed[2]['error']['code'], 'MEETING_CLOSED')
        confirm_closed = await self.confirm_meeting(meeting['meeting_id'], version=2)
        self.assertEqual(confirm_closed[0], 409)


if __name__ == '__main__':
    unittest.main()
