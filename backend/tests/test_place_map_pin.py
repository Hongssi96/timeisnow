import asyncio
import json
import os
import unittest
from unittest.mock import patch
from uuid import uuid4

import test_places
from app.auth import security as auth
from app.common.database import database
from app.places import dto as places_dto, provider as places_provider
from test_api_contract import request


class PinTests(unittest.IsolatedAsyncioTestCase):
    setUp = test_places.PlaceTests.setUp
    tearDown = test_places.PlaceTests.tearDown
    call = test_places.PlaceTests.call
    prepare = test_places.PlaceTests.prepare
    credentials = test_places.PlaceTests.credentials
    signup_login = test_places.PlaceTests.signup_login
    saved = test_places.PlaceTests.saved
    create = test_places.PlaceTests.create

    async def confirmation(self, location=None):
        location = location or {'latitude':37.5002, 'longitude':127.0002}
        with patch.object(places_provider, 'region_for_location', return_value='서울특별시 합성동'):
            response = await self.call('/place-location-confirmations', {'location':location})
        self.assertEqual(response[0], 200)
        return response[2]['data']

    async def update(self, place_id, body, csrf=True):
        headers = [(b'origin',b'http://127.0.0.1:5173'), (b'cookie', self.cookie.encode()), (b'content-type',b'application/json')]
        if csrf: headers.append((b'x-csrf-token',self.csrf.encode()))
        return await request('/api/v1/places/' + place_id, 'PATCH', headers=headers, body=json.dumps(body).encode())

    async def test_confirmed_creation_preserves_original_address_and_note(self):
        await self.signup_login()
        body, _ = await self.saved()
        confirmation = await self.confirmation()
        created = await self.create({**body, 'location':confirmation['location'],
            'location_confirmation_id':confirmation['confirmation_id'], 'entrance_note':' 동쪽 출입구 '})
        self.assertEqual(created[0], 201)
        data = created[2]['data']
        self.assertEqual(data['location'], confirmation['location'])
        self.assertEqual(data['location_source'], 'map_pin')
        self.assertEqual(data['entrance_note'], '동쪽 출입구')
        self.assertEqual(data['address'], '서울 합성 주소')
        self.assertEqual(data['location_address'], '서울특별시 합성동')

    async def test_update_versions_noop_note_clear_and_stale_basis(self):
        await self.signup_login()
        _, saved = await self.saved()
        place_id = saved[2]['data']['place_id']
        confirmation = await self.confirmation()
        payload = {'expected_version':1, 'location':confirmation['location'],
                   'location_confirmation_id':confirmation['confirmation_id'], 'entrance_note':'정문'}
        updated = await self.update(place_id, payload)
        self.assertEqual(updated[0], 200)
        self.assertEqual(updated[2]['data']['version'], 2)
        self.assertEqual((await self.update(place_id, payload))[0], 409)
        self.assertEqual((await self.update(place_id, {**payload, 'expected_version':2}))[2]['data']['version'], 2)
        cleared = await self.update(place_id, {'expected_version':2, 'entrance_note':None})
        self.assertEqual(cleared[2]['data']['version'], 3)
        self.assertIsNone(cleared[2]['data']['entrance_note'])
        self.assertEqual((await self.call('/places/' + place_id))[2]['data']['location'], confirmation['location'])

    async def test_confirmation_expiry_tampering_and_missing_id(self):
        await self.signup_login()
        body, saved = await self.saved()
        confirmation = await self.confirmation()
        payload = {**body, 'location':confirmation['location'], 'location_confirmation_id':confirmation['confirmation_id']}
        self.assertEqual((await self.create({**payload, 'location':{'latitude':38, 'longitude':127}}))[0], 422)
        self.assertEqual((await self.create({**payload, 'location_confirmation_id':str(uuid4())}))[0], 404)
        with database() as connection:
            connection.execute('UPDATE place_location_confirmations SET expires_at=now()')
        self.assertEqual((await self.create(payload))[0], 404)
        self.assertEqual((await self.update(saved[2]['data']['place_id'], {'expected_version':1,
            'location':confirmation['location'], 'location_confirmation_id':confirmation['confirmation_id']}))[0], 404)
        self.assertEqual((await self.call('/places/' + saved[2]['data']['place_id']))[2]['data']['version'], 1)

    async def test_foreign_confirmation_and_place_are_hidden(self):
        await self.signup_login()
        body, saved = await self.saved()
        confirmation = await self.confirmation()
        with database() as connection:
            other = uuid4()
            connection.execute('INSERT INTO users(id,display_name) VALUES(%s,%s)',(other,'다른 합성 회원'))
            connection.execute('UPDATE auth_sessions SET user_id=%s WHERE token_hash=%s',(other,auth.digest(self.cookie.split('=')[1])))
        self.assertEqual((await self.update(saved[2]['data']['place_id'], {'expected_version':1,'entrance_note':'정문'}))[0],404)
        # Own search candidates do not permit using another user's confirmation.
        own_body, _ = await self.saved()
        self.assertEqual((await self.create({**own_body,'location':confirmation['location'],
            'location_confirmation_id':confirmation['confirmation_id']}))[0],404)

    async def test_validation_and_csrf(self):
        await self.signup_login()
        _, saved = await self.saved()
        place_id = saved[2]['data']['place_id']
        for body in ({'expected_version':0,'entrance_note':'정문'}, {'expected_version':True,'entrance_note':'정문'},
                     {'expected_version':1}, {'expected_version':1,'location':None},
                     {'expected_version':1,'location':{'latitude':37,'longitude':127}},
                     {'expected_version':1,'entrance_note':' '}, {'expected_version':1,'entrance_note':'a'*101},
                     {'expected_version':1,'name':'회사','entrance_note':'정문'}):
            response = await self.update(place_id, body)
            self.assertEqual(response[0],422)
            self.assertEqual(response[1][b'cache-control'],b'no-store')
        self.assertEqual((await self.update(place_id, {'expected_version':1,'entrance_note':'정문'},False))[0],403)
        with patch.object(places_provider,'region_for_location') as provider:
            self.assertEqual((await self.call('/place-location-confirmations',{'location':{'latitude':91,'longitude':127}}))[0],422)
            provider.assert_not_called()

    async def test_config_public_key_only_and_missing_configuration(self):
        self.assertEqual((await self.call('/map-config'))[0],401)
        await self.signup_login()
        with patch.dict(os.environ, {'KAKAO_JAVASCRIPT_KEY':'public_synthetic','KAKAO_REST_API_KEY':'private_synthetic'}):
            response = await self.call('/map-config')
            self.assertEqual(response[2]['data'],{'javascript_key':'public_synthetic'})
            self.assertEqual(response[1][b'cache-control'],b'no-store')
        with patch.dict(os.environ, {'KAKAO_JAVASCRIPT_KEY':''}):
            self.assertEqual((await self.call('/map-config'))[2]['error']['code'],'MAP_UNAVAILABLE')

    async def test_map_confirmation_and_update_logs_are_private(self):
        import io
        import logging
        from app.common.request_logging import logger, RequestJsonFormatter, RequestEventFilter
        await self.signup_login()
        _, saved = await self.saved()
        output=io.StringIO();handler=logging.StreamHandler(output)
        handler.setFormatter(RequestJsonFormatter());handler.addFilter(RequestEventFilter())
        original_handlers, original_level=logger.handlers[:],logger.level
        logger.handlers[:]=[handler];logger.setLevel(logging.INFO)
        try:
            with patch.dict(os.environ,{'KAKAO_JAVASCRIPT_KEY':'synthetic-public-key'}):
                await self.call('/map-config')
            confirmed=await self.confirmation()
            updated=await self.update(saved[2]['data']['place_id'], {'expected_version':1,'entrance_note':'private entrance',
                'location':confirmed['location'],'location_confirmation_id':confirmed['confirmation_id']})
        finally:
            logger.handlers[:]=original_handlers;logger.setLevel(original_level)
        logs=output.getvalue()
        for value in ('synthetic-public-key','private entrance','서울특별시 합성동','"latitude"','"longitude"',confirmed['confirmation_id']):
            self.assertNotIn(value,logs)
        entries=[json.loads(line) for line in logs.splitlines()]
        self.assertEqual([entry['status_code'] for entry in entries],[200,200,200])
        self.assertEqual(entries[-1]['request_id'],updated[2]['meta']['request_id'])

    async def test_outside_region_failure_cleanup_and_quota(self):
        await self.signup_login()
        await self.confirmation()
        with database() as connection:
            connection.execute('UPDATE place_location_confirmations SET expires_at=now()')
        with patch.object(places_provider,'region_for_location',side_effect=auth.AuthError(422,'UNSUPPORTED_REGION','지원지역 밖')):
            self.assertEqual((await self.call('/place-location-confirmations', {'location':{'latitude':35,'longitude':129}}))[0],422)
        with database() as connection:
            self.assertEqual(connection.execute('SELECT count(*) AS n FROM place_location_confirmations').fetchone()['n'],0)
        for _ in range(8): await self.confirmation()
        with patch.object(places_provider,'region_for_location') as upstream:
            response = await self.call('/place-location-confirmations', {'location':{'latitude':37,'longitude':127}})
        self.assertEqual(response[0],429)
        self.assertIn(b'retry-after',response[1]); upstream.assert_not_called()

    async def test_concurrent_updates_with_same_version_only_one_succeeds(self):
        await self.signup_login()
        _, saved = await self.saved()
        first, second = await asyncio.gather(self.update(saved[2]['data']['place_id'], {'expected_version':1,'entrance_note':'동문'}),
            self.update(saved[2]['data']['place_id'], {'expected_version':1,'entrance_note':'서문'}))
        self.assertEqual(sorted([first[0],second[0]]),[200,409])
        self.assertEqual((await self.call('/places/' + saved[2]['data']['place_id']))[2]['data']['version'],2)

    async def test_legacy_retry_hash_is_compatible(self):
        import hashlib
        await self.signup_login()
        body, saved = await self.saved()
        canonical = places_dto.PlaceInput(**body).model_dump(mode='json')
        canonical.pop('source')  # Reproduce the pre-source F03-01 request hash.
        canonical.pop('entrance_note'); canonical.pop('location_confirmation_id')
        with database() as connection:
            user_id = connection.execute('SELECT id FROM users').fetchone()['id']
            fingerprint = hashlib.sha256(json.dumps(canonical,sort_keys=True).encode()).hexdigest()
            connection.execute("INSERT INTO place_creation_keys VALUES(%s,%s,%s,%s,now()+interval '24 hours')",(user_id,'legacy-key',fingerprint,saved[2]['data']['place_id']))
        self.assertEqual((await self.create(body,'legacy-key'))[2]['data']['place_id'],saved[2]['data']['place_id'])


class RegionTests(unittest.TestCase):
    def test_supported_region_and_outside_or_sea(self):
        location=places_dto.Location(latitude=37.5,longitude=127)
        for documents in ([],[{'region_type':'B','region_1depth_name':'부산광역시','address_name':'부산 합성동'}]):
            with patch.object(places_provider,'provider_documents',return_value=documents):
                with self.assertRaises(auth.AuthError) as error: places_provider.region_for_location(location)
                self.assertEqual(error.exception.code,'UNSUPPORTED_REGION')
        with patch.object(places_provider,'provider_documents',return_value=[{'region_type':'B','region_1depth_name':'경기도','address_name':'경기도 합성동'}]):
            self.assertEqual(places_provider.region_for_location(location),'경기도 합성동')

    def test_malformed_region_is_not_supported_guess(self):
        with patch.object(places_provider,'provider_documents',return_value=[{'region_type':'B'}]):
            with self.assertRaises(auth.AuthError) as error: places_provider.region_for_location(places_dto.Location(latitude=37.5,longitude=127))
        self.assertEqual(error.exception.code,'PROVIDER_RESPONSE_INVALID')
