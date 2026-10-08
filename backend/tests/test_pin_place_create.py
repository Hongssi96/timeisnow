import copy
import unittest
from unittest.mock import patch
from uuid import uuid4

import test_places
from app.common.database import database
from app.places import provider


class PinCreateTests(unittest.IsolatedAsyncioTestCase):
    setUp = test_places.PlaceTests.setUp
    tearDown = test_places.PlaceTests.tearDown
    call = test_places.PlaceTests.call
    prepare = test_places.PlaceTests.prepare
    credentials = test_places.PlaceTests.credentials
    signup_login = test_places.PlaceTests.signup_login
    create = test_places.PlaceTests.create
    saved = test_places.PlaceTests.saved

    async def pin(self):
        location = {'latitude': 37.5, 'longitude': 127.0}
        with patch.object(provider, 'region_for_location', return_value='서울 합성동'):
            response = await self.call('/place-location-confirmations', {'location': location})
        self.assertEqual(response[0], 200)
        return {'source': 'map_pin', 'label': '집', 'location': location,
                'location_confirmation_id': response[2]['data']['confirmation_id']}

    async def test_pin_without_search_and_expired_confirmation_replay(self):
        await self.signup_login(); body = await self.pin()
        with patch.object(provider, 'search_candidates') as search:
            first = await self.create(body, 'pin-key'); search.assert_not_called()
        self.assertEqual(first[0], 201)
        place = first[2]['data']
        self.assertEqual((place['name'], place['address'], place['location_source']), ('집', '서울 합성동', 'map_pin'))
        self.assertEqual(place['location'], body['location'])
        self.assertEqual(place['location_version'], 1)
        with database() as c:
            c.execute("UPDATE place_location_confirmations SET expires_at=now()-interval '1 second'")
        self.assertEqual((await self.create(body, 'pin-key'))[2]['data'], place)
        self.assertEqual((await self.create(body, 'new-key'))[0], 404)
        self.assertEqual((await self.create({**body, 'label': '회사'}, 'pin-key'))[0], 409)
        self.assertEqual((await self.call('/places/'+place['place_id']))[2]['data'], place)
        with database() as c:
            self.assertEqual(c.execute('SELECT count(*) AS n FROM saved_places').fetchone()['n'], 1)

    async def test_input_and_coordinate_confirmation_guards(self):
        await self.signup_login(); body = await self.pin()
        for change in [{'source':'unknown'}, {'location_confirmation_id':None}, {'search_id':str(uuid4())},
                       {'candidate_id':str(uuid4())}, {'label':''}, {'name':'합성'}, {'address':'합성'}]:
            self.assertEqual((await self.create({**body, **change}))[0], 422)
        changed = copy.deepcopy(body); changed['location']['latitude'] = 37.6
        self.assertEqual((await self.create(changed))[0], 422)
        self.assertEqual((await self.create({**body, 'location_confirmation_id':str(uuid4())}))[0], 404)
        self.assertEqual((await self.call('/places', body, csrf=False))[0], 403)

    async def test_foreign_confirmation_and_deleted_retry(self):
        await self.signup_login(); body = await self.pin()
        created = await self.create(body, 'delete-key'); place_id = created[2]['data']['place_id']
        with database() as c: c.execute('DELETE FROM saved_places WHERE id=%s', (place_id,))
        self.assertEqual((await self.create(body, 'delete-key'))[0], 404)
        self.cookie = None; self.csrf = None; await self.prepare()
        credentials = self.credentials('other@example.invalid')
        await self.call('/auth/register', credentials)
        logged = await self.call('/auth/login', {'email':credentials['email'], 'password':credentials['password']})
        self.cookie = logged[1][b'set-cookie'].decode().split(';')[0]; self.csrf = logged[2]['data']['csrf_token']
        self.assertEqual((await self.create(body))[0], 404)

    async def test_default_search_source_preserves_old_retry_hash(self):
        await self.signup_login()
        body, created = await self.saved(key='search-compatible')
        explicit = await self.create({**body, 'source':'search'}, 'search-compatible')
        self.assertEqual(explicit[2]['data'], created[2]['data'])
        self.assertEqual((await self.create({'label':'집', 'location':body['location']}))[0], 422)
