"""F12 personal meeting flows: private origin, invite replay cache, per-member guidance."""
from datetime import datetime, timezone
from unittest.mock import patch
from uuid import UUID, uuid4

from test_first_arrivals import mapping
from test_journeys import route
from test_meetings import MeetingTests

from app.arrivals import provider as arrivals_provider
from app.arrivals import mapping as public_mapping
from app.journeys import provider as journey_provider
from app.places import provider as places_provider


def resolve_any(context, expires_at, **kwargs):
    """Map every synthetic boarding leg so first departure evidence stays fresh."""
    return mapping(UUID(context['first_leg_id']))


class MeetingFlowTests(MeetingTests):
    """혼자 가는 일정, 개인 출발지, 초대 응답 캐시, 개인별 출발 안내를 검증한다."""

    async def solo_confirmed(self):
        await self.signin('main', 'main@example.invalid')
        created = await self.make_meeting()
        meeting_id = created['meeting_id']
        confirmed = await self.confirm_meeting(meeting_id)
        self.assertEqual(confirmed[0], 201)
        data = confirmed[2]['data']
        origin = await self.call(f"/meetings/{meeting_id}/members/me/origin", method='PUT', user='main',
                                 body={'origin': {'type': 'map_pin', 'latitude': 37.4979, 'longitude': 127.0276},
                                       'recommendation_consent': False, 'expected_version': 1})
        self.assertEqual(origin[0], 200, origin)
        return {'meeting_id': meeting_id, 'version': data['meeting']['version'],
                'current_revision_id': data['revision']['revision_id'],
                'member_id': created['organizer_member_id']}, origin[2]['data']

    async def guidance(self, meeting_id, revision_id, key='guidance-key', basis='recommended',
                       origin_override=None, extra=None, user='main'):
        body = {'meeting_revision_id': revision_id, 'departure_basis': basis}
        if origin_override is not None:
            body['origin_override'] = origin_override
        if extra:
            body.update(extra)
        with patch.object(places_provider, 'region_for_location', return_value='서울 합성동'), \
             patch.object(journey_provider, 'fetch_routes', return_value={'status': 'OK', 'routes': [route(walking=300)]}), \
             patch.object(public_mapping, 'resolve', side_effect=resolve_any), \
             patch.object(arrivals_provider, 'fetch', return_value=[('123', 780)]):
            return await self.call(f'/meetings/{meeting_id}/guidance-queries', body, key=key, user=user)

    async def test_origin_rules_and_privacy(self):
        meeting, _ = await self.solo_confirmed()
        detail = await self.call(f"/meetings/{meeting['meeting_id']}", user='main')
        row = next(m for m in detail[2]['data']['members'] if m['member_id'] == meeting['member_id'])
        self.assertTrue(row['origin_ready'])
        mine = await self.call(f"/meetings/{meeting['meeting_id']}/members/me/origin", user='main')
        self.assertEqual(mine[0], 200)
        self.assertEqual(mine[2]['data']['private_origin']['origin']['type'], 'map_pin')
        self.assertEqual(mine[2]['data']['member_version'], 2)
        stale = await self.call(f"/meetings/{meeting['meeting_id']}/members/me/origin", method='PUT', user='main',
                                body={'origin': {'type': 'map_pin', 'latitude': 37.5, 'longitude': 127.0},
                                      'recommendation_consent': True, 'expected_version': 1})
        self.assertEqual(stale[0], 409)
        self.assertEqual(stale[2]['error']['code'], 'VERSION_CONFLICT')
        update = await self.call(f"/meetings/{meeting['meeting_id']}/members/me/origin", method='PUT', user='main',
                                 body={'origin': {'type': 'current_location', 'latitude': 37.5, 'longitude': 127.0,
                                                  'accuracy_meters': 15,
                                                  'captured_at': datetime.now(timezone.utc).isoformat(),
                                                  'location_confirmed': True},
                                       'recommendation_consent': True, 'expected_version': 2})
        self.assertEqual(update[0], 200)
        self.assertEqual(update[2]['data']['private_origin']['origin']['type'], 'current_location')
        rejected = await self.call(f"/meetings/{meeting['meeting_id']}/members/me/origin", method='PUT', user='main',
                                   body={'origin': {'type': 'current_location', 'latitude': 37.5, 'longitude': 127.0,
                                                    'accuracy_meters': 15,
                                                    'captured_at': datetime.now(timezone.utc).isoformat(),
                                                    'location_confirmed': False},
                                         'recommendation_consent': False, 'expected_version': 3})
        self.assertEqual(rejected[0], 422)
        await self.signin('other', 'other@example.invalid')
        stranger = await self.call(f"/meetings/{meeting['meeting_id']}/members/me/origin", method='PUT', user='other',
                                   body={'origin': {'type': 'map_pin', 'latitude': 37.5, 'longitude': 127.0},
                                         'recommendation_consent': False, 'expected_version': 1})
        self.assertEqual(stranger[0], 404)
        peek = await self.call(f"/meetings/{meeting['meeting_id']}/members/me/origin", user='other')
        self.assertEqual(peek[0], 404)

    async def test_invite_replay_cache_after_consume(self):
        await self.signin('main', 'main@example.invalid')
        await self.signin('invitee', 'invitee@example.invalid')
        meeting = await self.make_meeting()
        issued = await self.invite(meeting['meeting_id'], key='consume-key')
        token = issued[2]['data']['token']
        accepted = await self.accept_invite(token, 'invitee', 'accept-key')
        self.assertEqual(accepted[0], 200)
        replay = await self.invite(meeting['meeting_id'], key='consume-key')
        self.assertEqual(replay[0], 409)
        self.assertEqual(replay[2]['error']['code'], 'INVITE_RESPONSE_EXPIRED')

    async def test_guidance_requires_confirmation_revision_and_origin(self):
        await self.signin('main', 'main@example.invalid')
        created = await self.make_meeting()
        meeting_id = created['meeting_id']
        draft = await self.guidance(meeting_id, str(uuid4()))
        self.assertEqual(draft[0], 409)
        self.assertEqual(draft[2]['error']['code'], 'MEETING_NOT_CONFIRMED')
        confirmed = await self.confirm_meeting(meeting_id)
        self.assertEqual(confirmed[0], 201)
        revision_id = confirmed[2]['data']['revision']['revision_id']
        none = await self.guidance(meeting_id, revision_id)
        self.assertEqual(none[0], 409)
        self.assertEqual(none[2]['error']['code'], 'ORIGIN_REQUIRED')
        await self.call(f"/meetings/{meeting_id}/members/me/origin", method='PUT', user='main',
                        body={'origin': {'type': 'map_pin', 'latitude': 37.4979, 'longitude': 127.0276},
                              'recommendation_consent': False, 'expected_version': 1})
        stale = await self.guidance(meeting_id, str(uuid4()))
        self.assertEqual(stale[0], 409)
        self.assertEqual(stale[2]['error']['code'], 'MEETING_REVISION_CHANGED')
        await self.signin('other', 'other@example.invalid')
        stranger = await self.guidance(meeting_id, revision_id, key='stranger-guidance', user='other')
        self.assertEqual(stranger[0], 404)

    async def test_solo_guidance_trip_link_and_active_trip(self):
        meeting, _ = await self.solo_confirmed()
        revision_id = meeting['current_revision_id']
        first = await self.guidance(meeting['meeting_id'], revision_id)
        self.assertEqual(first[0], 200, first)
        data = first[2]['data']
        self.assertEqual(data['model_version'], 'meeting.departure.v1')
        self.assertEqual(data['meeting_revision_id'], revision_id)
        self.assertTrue(data['meeting_journey_id'])
        self.assertEqual(data['guidance']['status'], 'ready')
        self.assertTrue(data['guidance']['valid_for_guidance'])
        self.assertIsNotNone(data['guidance']['guidance_id'])
        self.assertIsNotNone(data['meeting_arrival_slack_seconds'])
        again = await self.guidance(meeting['meeting_id'], revision_id, key='guidance-key-2')
        self.assertEqual(again[0], 200)
        self.assertEqual(again[2]['data']['meeting_journey_id'], data['meeting_journey_id'])
        created = await self.call('/trips', user='main', key='trip-key-1',
                                  body={'guidance_id': data['guidance']['guidance_id'], 'measurement_mode': 'assisted'})
        self.assertEqual(created[0], 201, created)
        trip = created[2]['data']
        self.assertEqual(trip['meeting_journey_id'], data['meeting_journey_id'])
        self.assertIsNone(trip['routine_id'])
        blocked_source = await self.guidance(meeting['meeting_id'], revision_id, key='guidance-key-3')
        self.assertEqual(blocked_source[0], 200)
        self.assertNotEqual(blocked_source[2]['data']['guidance']['guidance_id'], data['guidance']['guidance_id'])
        blocked = await self.call('/trips', user='main', key='trip-key-2',
                                  body={'guidance_id': blocked_source[2]['data']['guidance']['guidance_id'],
                                        'measurement_mode': 'assisted'})
        self.assertEqual(blocked[0], 409)
        self.assertEqual(blocked[2]['error']['code'], 'ACTIVE_TRIP_EXISTS')

    async def test_guidance_without_routes_returns_insufficient_status(self):
        meeting, _ = await self.solo_confirmed()
        revision_id = meeting['current_revision_id']
        with patch.object(places_provider, 'region_for_location', return_value='서울 합성동'), \
             patch.object(journey_provider, 'fetch_routes', return_value={'status': 'OK', 'routes': []}):
            reply = await self.call(f'/meetings/{meeting["meeting_id"]}/guidance-queries', user='main', key='empty-key',
                                    body={'meeting_revision_id': revision_id, 'departure_basis': 'now'})
        self.assertEqual(reply[0], 200, reply)
        data = reply[2]['data']
        self.assertEqual(data['guidance']['status'], 'insufficient_data')
        self.assertIn('ROUTE_UNAVAILABLE', data['guidance']['reasons'])
        self.assertIsNone(data['meeting_arrival_slack_seconds'])

    async def test_guidance_origin_override_and_trip_validation(self):
        meeting, _ = await self.solo_confirmed()
        revision_id = meeting['current_revision_id']
        override = await self.guidance(meeting['meeting_id'], revision_id, key='override-key',
                                       origin_override={'type': 'map_pin', 'latitude': 37.5, 'longitude': 127.0})
        self.assertEqual(override[0], 200, override)
        created = await self.call('/trips', user='main', key='trip-key-3',
                                  body={'guidance_id': override[2]['data']['guidance']['guidance_id'],
                                        'measurement_mode': 'assisted'})
        self.assertEqual(created[0], 201)
        trip_id = created[2]['data']['trip_id']
        linked = await self.guidance(meeting['meeting_id'], revision_id, key='linked-key', extra={'trip_id': trip_id})
        self.assertEqual(linked[0], 200)
        alien = await self.guidance(meeting['meeting_id'], revision_id, key='alien-key',
                                    extra={'trip_id': str(uuid4())})
        self.assertEqual(alien[0], 404)

    async def test_meeting_change_during_calculation_never_succeeds(self):
        meeting, _ = await self.solo_confirmed()
        revision_id = meeting['current_revision_id']
        from app.common.database import database

        def mutate(_):
            with database() as connection:
                connection.execute('UPDATE meetings SET version=version+1 WHERE id=%s', (meeting['meeting_id'],))
            return [('123', 780)]

        with patch.object(places_provider, 'region_for_location', return_value='서울 합성동'), \
             patch.object(journey_provider, 'fetch_routes', return_value={'status': 'OK', 'routes': [route(walking=300)]}), \
             patch.object(public_mapping, 'resolve', side_effect=resolve_any), \
             patch.object(arrivals_provider, 'fetch', side_effect=mutate):
            reply = await self.call(f'/meetings/{meeting["meeting_id"]}/guidance-queries', user='main',
                                    key='racing-key',
                                    body={'meeting_revision_id': revision_id, 'departure_basis': 'recommended'})
        self.assertEqual(reply[0], 409)
        self.assertEqual(reply[2]['error']['code'], 'VERSION_CONFLICT')
        with database() as connection:
            rows = connection.execute('SELECT id FROM meeting_journeys').fetchall()
        self.assertEqual(len(rows), 1)
