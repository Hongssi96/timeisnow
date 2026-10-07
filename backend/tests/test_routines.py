"""Routine storage over owned searches: ownership, idempotency and place detachment."""
import asyncio
import io
import json
import logging
import unittest
from unittest.mock import patch
from uuid import uuid4

import test_auth
import test_journeys
import test_places
from test_api_contract import request
from app import auth


class RoutineTests(unittest.IsolatedAsyncioTestCase):
    setUp = test_places.PlaceTests.setUp
    tearDown = test_places.PlaceTests.tearDown
    call = test_places.PlaceTests.call
    prepare = test_auth.AuthTests.prepare
    credentials = test_auth.AuthTests.credentials
    signup_login = test_auth.AuthTests.signup_login
    saved = test_places.PlaceTests.saved
    create = test_places.PlaceTests.create
    search = test_journeys.JourneyTests.search
    completed = test_journeys.JourneyTests.completed

    async def saved_search(self):
        _, home = await self.saved('집')
        _, work = await self.saved('회사')
        body = {'origin': {'type': 'saved_place', 'place_id': home[2]['data']['place_id'], 'location_version': 1},
                'destination': {'type': 'saved_place', 'place_id': work[2]['data']['place_id'], 'location_version': 1},
                'timing': {'mode': 'depart_now', 'timezone': 'Asia/Seoul'}}
        accepted, result, _ = await self.completed(body)
        return home[2]['data'], work[2]['data'], accepted[2]['data']['search_id'], result[2]['data']['candidates'][0]

    async def ready(self):
        await self.signup_login()
        return await self.saved_search()

    def routine_body(self, home, work, search_id, candidate, name='아침 출근'):
        return {'name': name, 'origin_place_id': home['place_id'], 'destination_place_id': work['place_id'],
                'search_id': search_id, 'candidate_id': candidate['candidate_id']}

    async def save(self, body, key=None, csrf=True):
        headers = [(b'origin', b'http://127.0.0.1:5173'), (b'content-type', b'application/json')]
        if self.cookie: headers.append((b'cookie', self.cookie.encode()))
        if csrf and self.csrf: headers.append((b'x-csrf-token', self.csrf.encode()))
        if key is not None: headers.append((b'idempotency-key', key.encode()))
        return await request('/api/v1/routines', 'POST', headers=headers, body=json.dumps(body).encode())

    async def test_create_detail_relogin_and_stored_snapshot(self):
        home, work, search_id, candidate = await self.ready()
        created = await self.save(self.routine_body(home, work, search_id, candidate), key='routine-key')
        self.assertEqual(created[0], 201)
        self.assertEqual(created[1][b'cache-control'], b'no-store')
        data = created[2]['data']
        self.assertEqual(data['name'], '아침 출근')
        self.assertEqual(data['status'], 'active')
        self.assertEqual(data['version'], 1)
        self.assertEqual(data['origin_place']['place_id'], home['place_id'])
        self.assertEqual(data['origin_place']['label'], '집')
        self.assertEqual(data['destination_place']['place_id'], work['place_id'])
        self.assertEqual(data['route']['type'], candidate['type'])
        self.assertEqual(data['route']['total_seconds'], candidate['total_seconds'])
        self.assertEqual(data['route']['transfer_count'], candidate['transfer_count'])
        self.assertNotIn('latitude', json.dumps(created[2]))
        detail = await self.call('/routines/' + data['routine_id'])
        self.assertEqual(detail[0], 200)
        self.assertEqual(detail[1][b'cache-control'], b'no-store')
        self.assertEqual(detail[2]['data'], data)
        with auth.database() as connection:
            plan = connection.execute('SELECT * FROM journey_plans').fetchone()
            self.assertEqual(plan['model_version'], 'journey.v1')
            self.assertEqual(plan['candidate']['candidate_id'], candidate['candidate_id'])
            self.assertNotIn('37.4979', json.dumps(plan['candidate']))
            self.assertNotIn('127.0276', json.dumps(plan['candidate']))
        await self.call('/auth/logout', {})
        await self.prepare()
        logged = await self.call('/auth/login', {'email': 'member@example.invalid', 'password': self.credentials()['password']})
        self.cookie = logged[1][b'set-cookie'].decode().split(';')[0]
        self.csrf = logged[2]['data']['csrf_token']
        self.assertEqual((await self.call('/routines/' + data['routine_id']))[2]['data'], data)

    async def test_inputs_ownership_versions_and_search_refs(self):
        home, work, search_id, candidate = await self.ready()
        body = self.routine_body(home, work, search_id, candidate)
        cookie, csrf_token = self.cookie, self.csrf
        self.cookie = None; self.csrf = None
        self.assertEqual((await self.save(body))[0], 401)
        self.cookie, self.csrf = cookie, csrf_token
        self.assertEqual((await self.save(body, csrf=False))[0], 403)
        self.assertEqual((await self.save({**body, 'name': '   '}))[0], 422)
        self.assertEqual((await self.save({**body, 'name': '가' * 31}))[0], 422)
        self.assertEqual((await self.save({**body, 'extra': 'x'}))[0], 422)
        self.assertEqual((await self.save({**body, 'destination_place_id': home['place_id']}))[0], 422)
        self.assertEqual((await self.save({**body, 'search_id': str(uuid4())}))[0], 404)
        self.assertEqual((await self.save({**body, 'candidate_id': str(uuid4())}))[0], 404)
        # A candidate from a different search does not belong to this search.
        _, other, _ = await self.completed()
        other_candidate = other[2]['data']['candidates'][0]
        self.assertEqual((await self.save({**body, 'candidate_id': other_candidate['candidate_id']}))[0], 404)
        # Saved places do not match a search that used map pins only.
        _, pin_result, _ = await self.completed()
        pin_search_id = pin_result[2]['data']['search_id']
        pin_candidate = pin_result[2]['data']['candidates'][0]['candidate_id']
        self.assertEqual((await self.save({**body, 'search_id': pin_search_id, 'candidate_id': pin_candidate}))[0], 422)
        with auth.database() as connection:
            connection.execute('UPDATE journey_searches SET expires_at=now() WHERE id=%s', (search_id,))
        self.assertEqual((await self.save(body))[0], 404)
        # A moved place no longer matches the search that referenced it.
        home2, work2, fresh_id, fresh_candidate = await self.saved_search()
        with auth.database() as connection:
            connection.execute('UPDATE saved_places SET location_version=location_version+1 WHERE id=%s', (home2['place_id'],))
        moved = self.routine_body(home2, work2, fresh_id, fresh_candidate)
        conflict = await self.save(moved)
        self.assertEqual(conflict[0], 409)
        self.assertEqual(conflict[2]['error']['code'], 'VERSION_CONFLICT')
        # Another member cannot save or read any of it.
        self.cookie = None; self.csrf = None
        await self.prepare()
        credentials = self.credentials('other@example.invalid')
        await self.call('/auth/register', credentials)
        logged = await self.call('/auth/login', {'email': 'other@example.invalid', 'password': credentials['password']})
        self.cookie = logged[1][b'set-cookie'].decode().split(';')[0]
        self.csrf = logged[2]['data']['csrf_token']
        foreign = {'name': '다른 회원 루틴', 'origin_place_id': home['place_id'],
                   'destination_place_id': work['place_id'], 'search_id': pin_search_id,
                   'candidate_id': pin_candidate}
        self.assertEqual((await self.save(foreign))[0], 404)

    async def test_idempotent_replay_conflict_and_deleted_marker(self):
        home, work, search_id, candidate = await self.ready()
        body = self.routine_body(home, work, search_id, candidate)
        first = await self.save(body, key='save-key')
        self.assertEqual(first[0], 201)
        again = await self.save(body, key='save-key')
        self.assertEqual(again[0], 201)
        self.assertEqual(again[2]['data'], first[2]['data'])
        conflict = await self.save({**body, 'name': '다른 이름'}, key='save-key')
        self.assertEqual(conflict[0], 409)
        self.assertEqual(conflict[2]['error']['code'], 'IDEMPOTENCY_CONFLICT')
        # The same button retried from two sessions creates exactly one routine.
        with auth.database() as connection:
            user_id = connection.execute('SELECT id FROM users WHERE display_name=%s', ('테스트 회원',)).fetchone()['id']
            raw, csrf, _ = auth.create_session(connection, user_id)
        headers = [(b'origin', b'http://127.0.0.1:5173'), (b'cookie', ('timeisnow_dev_session=' + raw).encode()),
                   (b'x-csrf-token', csrf.encode()), (b'idempotency-key', b'concurrent-key'), (b'content-type', b'application/json')]
        payload = json.dumps(self.routine_body(home, work, search_id, candidate, name='여유 등교')).encode()
        left, right = await asyncio.gather(self.save({**body, 'name': '여유 등교'}, key='concurrent-key'),
            request('/api/v1/routines', 'POST', headers=headers, body=payload))
        self.assertEqual((left[0], right[0]), (201, 201))
        self.assertEqual(left[2]['data']['routine_id'], right[2]['data']['routine_id'])
        with auth.database() as connection:
            self.assertEqual(connection.execute("SELECT count(*) AS n FROM routines WHERE name='여유 등교'").fetchone()['n'], 1)
        # Deleting the routine keeps the 24h retry marker, so the same key cannot recreate it.
        with auth.database() as connection:
            connection.execute('DELETE FROM routines')
        self.assertEqual((await self.save({**body, 'name': '여유 등교'}, key='concurrent-key'))[0], 404)

    async def test_same_candidate_shares_one_plan(self):
        home, work, search_id, candidate = await self.ready()
        body = self.routine_body(home, work, search_id, candidate)
        first = await self.save(body, key='one')
        second = await self.save({**body, 'name': '여유 등교'}, key='two')
        self.assertEqual((first[0], second[0]), (201, 201))
        self.assertNotEqual(first[2]['data']['routine_id'], second[2]['data']['routine_id'])
        self.assertEqual(first[2]['data']['route']['journey_plan_id'], second[2]['data']['route']['journey_plan_id'])
        with auth.database() as connection:
            self.assertEqual(connection.execute('SELECT count(*) AS n FROM journey_plans').fetchone()['n'], 1)

    async def test_place_deletion_detaches_routine_refs(self):
        home, work, search_id, candidate = await self.ready()
        data = (await self.save(self.routine_body(home, work, search_id, candidate)))[2]['data']
        headers = [(b'origin', b'http://127.0.0.1:5173'), (b'cookie', self.cookie.encode()), (b'x-csrf-token', self.csrf.encode())]
        deleted = await request('/api/v1/places/' + home['place_id'], 'DELETE', headers=headers)
        self.assertEqual(deleted[0], 204)
        after = (await self.call('/routines/' + data['routine_id']))[2]['data']
        self.assertEqual(after['status'], 'needs_attention')
        self.assertIsNone(after['origin_place'])
        self.assertIsNotNone(after['destination_place'])
        self.assertEqual(after['version'], 2)
        deleted = await request('/api/v1/places/' + work['place_id'], 'DELETE', headers=headers)
        self.assertEqual(deleted[0], 204)
        after = (await self.call('/routines/' + data['routine_id']))[2]['data']
        self.assertIsNone(after['origin_place'])
        self.assertIsNone(after['destination_place'])
        self.assertEqual(after['status'], 'needs_attention')
        self.assertEqual(after['version'], 3)
        self.assertEqual(after['route']['journey_plan_id'], data['route']['journey_plan_id'])
        # A new place with the same label never restores the old references.
        await self.saved('집')
        after = (await self.call('/routines/' + data['routine_id']))[2]['data']
        self.assertIsNone(after['origin_place'])

    async def test_logs_exclude_names_and_references(self):
        from app.request_logging import logger, RequestJsonFormatter, RequestEventFilter
        home, work, search_id, candidate = await self.ready()
        output = io.StringIO()
        handler = logging.StreamHandler(output)
        handler.setFormatter(RequestJsonFormatter())
        handler.addFilter(RequestEventFilter())
        previous_handlers, previous_level = logger.handlers[:], logger.level
        logger.handlers[:] = [handler]
        logger.setLevel(logging.INFO)
        try:
            created = await self.save(self.routine_body(home, work, search_id, candidate, name='비밀 루틴'))
            await self.call('/routines/' + created[2]['data']['routine_id'])
        finally:
            logger.handlers[:] = previous_handlers
            logger.setLevel(previous_level)
        logs = output.getvalue()
        for private in ('비밀 루틴', home['place_id'], work['place_id'], search_id, candidate['candidate_id']):
            self.assertNotIn(private, logs)
        entries = [json.loads(line) for line in logs.splitlines()]
        self.assertEqual([entry['route'] for entry in entries], ['/api/v1/routines', '/api/v1/routines/{routine_id}'])
