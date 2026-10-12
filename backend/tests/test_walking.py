"""Owned evidence API, real PostgreSQL and synthetic route evidence."""
import copy
import json
import unittest
from unittest.mock import patch
from uuid import uuid4

import test_places
import test_journeys
from app.common.database import database
from app.journeys import provider

BODY, route = test_journeys.BODY, test_journeys.route


class WalkingTests(unittest.IsolatedAsyncioTestCase):
    setUp = test_places.PlaceTests.setUp
    tearDown = test_places.PlaceTests.tearDown
    call = test_places.PlaceTests.call
    prepare = test_places.PlaceTests.prepare
    credentials = test_places.PlaceTests.credentials
    signup_login = test_places.PlaceTests.signup_login
    saved = test_places.PlaceTests.saved
    create = test_places.PlaceTests.create
    search = test_journeys.JourneyTests.search
    completed = test_journeys.JourneyTests.completed

    async def evidence_path(self, body=BODY, data=None):
        accepted, result, _ = await self.completed(body=body, data=data)
        search_id = accepted[2]['data']['search_id']
        candidate_id = result[2]['data']['candidates'][0]['candidate_id']
        return f'/journey-searches/{search_id}/candidates/{candidate_id}/walking-evidence', search_id

    async def test_values_stable_read_only_and_private(self):
        await self.signup_login()
        path, identifier = await self.evidence_path()
        with database() as c:
            before = c.execute('SELECT * FROM journey_searches WHERE id=%s', (identifier,)).fetchone()
        with patch.object(provider, 'fetch_routes') as upstream:
            first, second = await self.call(path), await self.call(path)
            upstream.assert_not_called()
        self.assertEqual(first[0], 200)
        self.assertEqual(first[1][b'cache-control'], b'no-store')
        self.assertEqual(first[2]['data'], second[2]['data'])
        data = first[2]['data']
        self.assertFalse(data['ready_for_estimation']); self.assertFalse(data['reusable'])
        self.assertEqual(data['status'], 'needs_data')
        self.assertEqual([s['role'] for s in data['segments']], ['access', 'egress'])
        self.assertEqual([s['provider_duration_seconds'] for s in data['segments']], [100, 50])
        self.assertEqual(data['segments'][0]['from_ref'], {'type': 'search_origin'})
        self.assertEqual(data['segments'][-1]['to_ref'], {'type': 'search_destination'})
        for segment in data['segments']:
            self.assertEqual(segment['source'], 'provider_estimate')
            self.assertEqual(segment['missing_segments'], ['PHYSICAL_ENDPOINTS_UNCONFIRMED'])
        for private in ['latitude', 'longitude', '127.0276', '37.4979', 'path', 'entrance_ref']:
            self.assertNotIn(private, json.dumps(data))
        with database() as c:
            after = c.execute('SELECT * FROM journey_searches WHERE id=%s', (identifier,)).fetchone()
        self.assertEqual(before, after)

    async def test_missing_and_zero_are_distinct_including_transfers(self):
        await self.signup_login()
        raw = route(transfers=1)
        bus = raw['steps'][1]
        raw['steps'] = [bus, copy.deepcopy(bus)]
        path, _ = await self.evidence_path(data={'status': 'OK', 'routes': [raw]})
        segments = (await self.call(path))[2]['data']['segments']
        self.assertEqual([s['role'] for s in segments], ['access', 'transfer', 'egress'])
        for segment in segments:
            self.assertIsNone(segment['provider_duration_seconds'])
            self.assertIsNone(segment['provider_distance_meters'])
            self.assertEqual(segment['walking_leg_ids'], [])
            self.assertIn('PROVIDER_WALK_MISSING', segment['missing_segments'])
        self.assertIsNotNone(segments[1]['connection_id'])
        raw = route(walking=0)
        path, _ = await self.evidence_path(data={'status': 'OK', 'routes': [raw]})
        access = (await self.call(path))[2]['data']['segments'][0]
        self.assertEqual(access['provider_duration_seconds'], 0)
        self.assertEqual(access['source'], 'provider_estimate')
        self.assertIn('WALK_DURATION_ZERO', access['missing_segments'])
        self.assertNotIn('PROVIDER_WALK_MISSING', access['missing_segments'])

    async def test_consecutive_walks_transfer_and_subway_scope(self):
        await self.signup_login()
        raw = route(transfers=1, kind='BUS_AND_SUBWAY', seconds=2000)
        walking, bus, egress = raw['steps']
        subway = copy.deepcopy(bus); subway['properties']['type'] = 'SUBWAY'
        raw['steps'] = [walking, copy.deepcopy(walking), bus, copy.deepcopy(walking), subway, egress]
        path, _ = await self.evidence_path(data={'status': 'OK', 'routes': [raw]})
        segments = (await self.call(path))[2]['data']['segments']
        self.assertEqual(segments[0]['provider_duration_seconds'], 200)
        self.assertEqual(segments[0]['provider_distance_meters'], 200)
        self.assertEqual(len(segments[0]['walking_leg_ids']), 2)
        self.assertEqual(segments[1]['provider_duration_seconds'], 100)
        self.assertNotIn('ENTRANCE_PLATFORM_UNCONFIRMED', segments[0]['missing_segments'])
        for segment in segments[1:]:
            self.assertIn('ENTRANCE_PLATFORM_UNCONFIRMED', segment['missing_segments'])

    async def test_auth_ownership_bad_ids_and_candidate(self):
        path = f'/journey-searches/{uuid4()}/candidates/{uuid4()}/walking-evidence'
        self.assertEqual((await self.call(path))[0], 401)
        await self.signup_login()
        self.assertEqual((await self.call(path))[0], 404)
        own_path, identifier = await self.evidence_path()
        for suffix in [f'{uuid4()}/walking-evidence', 'invalid/walking-evidence']:
            self.assertEqual((await self.call(f'/journey-searches/{identifier}/candidates/{suffix}'))[0], 404)
        self.assertEqual((await self.call(own_path.replace(identifier, 'invalid')))[0], 404)
        self.cookie = None; self.csrf = None; await self.prepare()
        credentials = self.credentials('other@example.invalid')
        await self.call('/auth/register', credentials)
        logged = await self.call('/auth/login', {'email': credentials['email'], 'password': credentials['password']})
        self.cookie = logged[1][b'set-cookie'].decode().split(';')[0]
        self.assertEqual((await self.call(own_path))[0], 404)

    async def test_expiry_status_and_corruption(self):
        await self.signup_login()
        path, identifier = await self.evidence_path()
        for status in ['queued', 'running', 'failed']:
            with database() as c:
                c.execute('UPDATE journey_searches SET status=%s WHERE id=%s', (status, identifier))
            self.assertEqual((await self.call(path))[0], 404)
        with database() as c:
            c.execute("UPDATE journey_searches SET status='succeeded',expires_at=now()-interval '5 seconds' WHERE id=%s", (identifier,))
        self.assertEqual((await self.call(path))[0], 404)
        path, identifier = await self.evidence_path()
        with database() as c:
            c.execute("UPDATE journey_searches SET candidates='[{}]' WHERE id=%s", (identifier,))
        self.assertEqual((await self.call(path))[2]['error']['code'], 'PROVIDER_RESPONSE_INVALID')

    async def test_saved_place_version_and_deleted_reference(self):
        await self.signup_login()
        _, created = await self.saved(); place = created[2]['data']
        body = {**BODY, 'origin': {'type': 'saved_place', 'place_id': place['place_id'], 'location_version': 1}}
        path, _ = await self.evidence_path(body=body)
        self.assertEqual((await self.call(path))[0], 200)
        with database() as c:
            c.execute('UPDATE saved_places SET label=%s,version=version+1 WHERE id=%s', ('합성 변경', place['place_id']))
        self.assertEqual((await self.call(path))[0], 200)
        with database() as c:
            c.execute('UPDATE saved_places SET location_version=location_version+1 WHERE id=%s', (place['place_id'],))
        self.assertEqual((await self.call(path))[2]['error']['code'], 'VERSION_CONFLICT')
        with database() as c:
            c.execute('DELETE FROM saved_places WHERE id=%s', (place['place_id'],))
        self.assertEqual((await self.call(path))[0], 404)

    def test_openapi_declares_evidence_envelope(self):
        from app.main import app
        operation = app.openapi()['paths']['/api/v1/journey-searches/{search_id}/candidates/{candidate_id}/walking-evidence']['get']
        self.assertEqual(operation['responses']['200']['content']['application/json']['schema']['$ref'],
                         '#/components/schemas/EvidenceEnvelope')
