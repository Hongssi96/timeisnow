"""Real DB ownership/expiry/retry checks, with synthetic upstream candidates."""
import json
import asyncio
import io
import logging
import os
import unittest
from unittest.mock import patch
from uuid import uuid4

import test_auth
from app.auth import security as auth
from app.common.database import database
from app.places import dto as places_dto, provider as places_provider


def candidate():
    return {'candidate_id': str(uuid4()), 'name': '합성 역', 'address': '서울 합성 주소',
            'location': {'latitude': 37.5, 'longitude': 127.0}}


class PlaceTests(unittest.IsolatedAsyncioTestCase):
    setUp = test_auth.AuthTests.setUp
    tearDown = test_auth.AuthTests.tearDown
    async def call(self, path, body=None, **options):
        if '?' not in path:
            return await test_auth.AuthTests.call(self, path, body, **options)
        from test_api_contract import request
        path, query = path.split('?', 1)
        return await request('/api/v1' + path, query=query.encode(), headers=[(b'cookie', self.cookie.encode())])
    prepare = test_auth.AuthTests.prepare
    credentials = test_auth.AuthTests.credentials
    signup_login = test_auth.AuthTests.signup_login

    async def saved(self, label='집', key=None):
        item = candidate()
        with patch.object(places_provider, 'search_candidates', return_value=[item]):
            result = await self.call('/place-searches', {'query': '합성 장소'})
        self.assertEqual(result[0], 200)
        body = {'label': label, 'search_id': result[2]['data']['search_id'],
                'candidate_id': item['candidate_id'], 'location': item['location']}
        return body, await self.create(body, key)

    async def create(self, body, key=None):
        from test_api_contract import request
        headers = [(b'origin', b'http://127.0.0.1:5173'), (b'cookie', self.cookie.encode()),
                   (b'x-csrf-token', self.csrf.encode()), (b'content-type', b'application/json')]
        if key: headers.append((b'idempotency-key', key.encode()))
        return await request('/api/v1/places', 'POST', headers=headers, body=json.dumps(body).encode())

    async def test_storage_detail_and_relogin(self):
        await self.signup_login()
        _, saved = await self.saved(' 회사 ')
        self.assertEqual(saved[0], 201)
        data = saved[2]['data']
        self.assertEqual(data['label'], '회사')
        self.assertEqual(data['version'], 1)
        self.assertEqual(saved[1][b'cache-control'], b'no-store')
        detail = await self.call('/places/' + data['place_id'])
        self.assertEqual(detail[2]['data'], data)
        await self.call('/auth/logout', {})
        await self.prepare()
        logged = await self.call('/auth/login', {'email': 'member@example.invalid', 'password': self.credentials()['password']})
        self.cookie = logged[1][b'set-cookie'].decode().split(';')[0]
        self.csrf = logged[2]['data']['csrf_token']
        self.assertEqual((await self.call('/places'))[2]['data']['items'], [data])

    async def test_place_logs_exclude_address_coordinates_and_ids(self):
        from app.common.request_logging import logger, RequestJsonFormatter, RequestEventFilter
        await self.signup_login()
        output = io.StringIO()
        handler = logging.StreamHandler(output)
        handler.setFormatter(RequestJsonFormatter())
        handler.addFilter(RequestEventFilter())
        previous_handlers, previous_level = logger.handlers[:], logger.level
        logger.handlers[:] = [handler]
        logger.setLevel(logging.INFO)
        try:
            body, saved = await self.saved('private-label')
            await self.call('/places/' + saved[2]['data']['place_id'])
        finally:
            logger.handlers[:] = previous_handlers
            logger.setLevel(previous_level)
        logs = output.getvalue()
        for private in ('private-label', '합성 장소', '서울 합성 주소', '"latitude"', '"longitude"', body['search_id'], saved[2]['data']['place_id']):
            self.assertNotIn(private, logs)
        entries = [json.loads(line) for line in logs.splitlines()]
        self.assertEqual([entry['status_code'] for entry in entries], [200, 201, 200])
        self.assertEqual(entries[-1]['route'], '/api/v1/places/{place_id}')
        self.assertEqual(entries[1]['request_id'], saved[2]['meta']['request_id'])

    async def test_ownership_search_detail_and_cursor(self):
        await self.signup_login()
        body, saved = await self.saved()
        await self.prepare()
        await self.call('/auth/register', self.credentials('other@example.invalid'))
        logged = await self.call('/auth/login', {'email':'other@example.invalid', 'password':self.credentials()['password']})
        self.cookie = logged[1][b'set-cookie'].decode().split(';')[0]
        self.csrf = logged[2]['data']['csrf_token']
        self.assertEqual((await self.create(body))[0], 404)
        self.assertEqual((await self.call('/places/' + saved[2]['data']['place_id']))[0], 404)
        self.assertEqual((await self.call('/places?cursor=' + saved[2]['data']['place_id']))[0], 404)
        self.assertEqual((await self.call('/places'))[2]['data']['items'], [])

    async def test_expiry_tampering_and_unknown_candidate(self):
        await self.signup_login()
        body, _ = await self.saved()
        self.assertEqual((await self.create({**body, 'location': {'latitude':38, 'longitude':127}}))[0], 422)
        self.assertEqual((await self.create({**body, 'candidate_id':str(uuid4())}))[0], 404)
        with database() as connection:
            connection.execute('UPDATE place_searches SET expires_at=now()')
        self.assertEqual((await self.create(body))[0], 404)

    async def test_idempotency_after_expiry_conflict_and_scope(self):
        await self.signup_login()
        body, saved = await self.saved(key='retry_key')
        with database() as connection:
            connection.execute("UPDATE place_searches SET expires_at=now()-interval '5 seconds'")
        again = await self.create(body, 'retry_key')
        self.assertEqual(again[0], 201)
        self.assertEqual(again[2]['data'], saved[2]['data'])
        conflict = await self.create({**body, 'label':'회사'}, 'retry_key')
        self.assertEqual(conflict[0], 409)
        self.assertEqual(conflict[2]['error']['code'], 'IDEMPOTENCY_CONFLICT')
        with database() as connection:
            self.assertEqual(connection.execute('SELECT count(*) AS n FROM saved_places').fetchone()['n'], 1)
            connection.execute("UPDATE place_creation_keys SET expires_at=now()-interval '5 seconds'")
        self.assertEqual((await self.create(body, 'retry_key'))[0], 404)

    async def test_concurrent_sessions_create_one_place_for_same_key(self):
        from test_api_contract import request
        await self.signup_login()
        body, _ = await self.saved()
        with database() as connection:
            user_id = connection.execute('SELECT id FROM users').fetchone()['id']
            raw, csrf, _ = auth.create_session(connection, user_id)
        headers = [(b'origin', b'http://127.0.0.1:5173'), (b'cookie', ('timeisnow_dev_session=' + raw).encode()),
                   (b'x-csrf-token', csrf.encode()), (b'idempotency-key', b'concurrent-key'), (b'content-type', b'application/json')]
        first, second = await asyncio.gather(self.create(body, 'concurrent-key'),
            request('/api/v1/places', 'POST', headers=headers, body=json.dumps(body).encode()))
        self.assertEqual((first[0], second[0]), (201, 201))
        self.assertEqual(first[2]['data']['place_id'], second[2]['data']['place_id'])
        with database() as connection:
            self.assertEqual(connection.execute('SELECT count(*) AS n FROM saved_places').fetchone()['n'], 2)

    async def test_auth_csrf_validation_and_no_provider_call(self):
        with patch.object(places_provider, 'search_candidates') as upstream:
            self.assertEqual((await self.call('/place-searches', {'query':'강남역'}))[0], 401)
            await self.signup_login()
            self.assertEqual((await self.call('/place-searches', {'query':'강남역'}, csrf=False))[0], 403)
            self.assertEqual((await self.call('/place-searches', {'query':'  '}))[0], 422)
            self.assertEqual((await self.call('/place-searches', {'query':'a'*101}))[0], 422)
            self.assertEqual((await self.call('/place-searches', {'query':'a', 'user_id':str(uuid4())}))[0], 422)
            upstream.assert_not_called()

    async def test_quota_empty_cleanup_and_safe_provider_error(self):
        await self.signup_login()
        with database() as connection:frozen=auth.repository.clock_now(connection)
        with patch.object(auth.repository,'clock_now',return_value=frozen), patch.object(places_provider, 'search_candidates', return_value=[]):
            for _ in range(10):
                result = await self.call('/place-searches', {'query':'합성'})
                self.assertEqual(result[0], 200)
                self.assertEqual(result[2]['data']['candidates'], [])
            limited = await self.call('/place-searches', {'query':'합성'})
        self.assertEqual(limited[0], 429)
        self.assertIn(b'retry-after', limited[1])
        with database() as connection:
            connection.execute('DELETE FROM auth_rate_limit_buckets')
            connection.execute('UPDATE place_searches SET expires_at=now()')
        with patch.object(places_provider, 'search_candidates', side_effect=auth.AuthError(503, 'PROVIDER_UNAVAILABLE', '검색 불가')):
            self.assertEqual((await self.call('/place-searches', {'query':'합성'}))[0], 503)
        with database() as connection:
            self.assertEqual(connection.execute('SELECT count(*) AS n FROM place_searches').fetchone()['n'], 0)
            self.assertEqual(connection.execute("SELECT count FROM auth_rate_limit_buckets WHERE scope='place-search'").fetchone()['count'], 1)

    async def test_pagination_invalid_ids_and_bounds(self):
        await self.signup_login()
        await self.saved('집')
        await self.saved('회사')
        first = (await self.call('/places?limit=1'))[2]['data']
        second = (await self.call('/places?limit=1&cursor=' + first['next_cursor']))[2]['data']
        self.assertNotEqual(first['items'][0]['place_id'], second['items'][0]['place_id'])
        self.assertIsNone(second['next_cursor'])
        self.assertEqual((await self.call('/places?limit=101'))[0], 422)
        self.assertEqual((await self.call('/places?cursor=bad'))[0], 404)
        self.assertEqual((await self.call('/places/bad'))[0], 404)


class ProviderTests(unittest.TestCase):
    def test_address_first_dedup_and_supported_region(self):
        docs = [dict(address_name='서울 강남구', x='127', y='37.5', road_address={'building_name':'합성'}),
                dict(address_name='부산 동구', x='129', y='35')]
        with patch.object(places_provider, 'provider_search', return_value=docs), patch.dict(os.environ, {'KAKAO_REST_API_KEY':'synthetic'}):
            rows = places_provider.search_candidates('합성')
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]['name'], '합성')

    def test_invalid_coordinate_rejected(self):
        with patch.object(places_provider, 'provider_search', return_value=[dict(address_name='경기도 합성', x='NaN', y='37')]), patch.dict(os.environ, {'KAKAO_REST_API_KEY':'synthetic'}):
            with self.assertRaises(auth.AuthError) as error:
                places_provider.search_candidates('합성')
        self.assertEqual(error.exception.code, 'PROVIDER_RESPONSE_INVALID')

    def test_transport_and_invalid_payload_do_not_expose_exception(self):
        for exception, code in [(TimeoutError('secret'), 'PROVIDER_UNAVAILABLE'), (ValueError('secret'), 'PROVIDER_RESPONSE_INVALID')]:
            with patch('urllib.request.build_opener') as opener:
                opener.return_value.open.side_effect = exception
                with self.assertRaises(auth.AuthError) as error:
                    places_provider.provider_search('address', '합성', 'secret')
            self.assertEqual(error.exception.code, code)
            self.assertNotIn('secret', error.exception.message)
