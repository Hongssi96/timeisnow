"""F12 personal meeting flows: private origin, invite replay cache, per-member guidance."""
from datetime import datetime, timedelta, timezone
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

    def _no_egress_routes(self):
        single = route(walking=300)
        single['steps'] = single['steps'][:2]
        return {'status': 'OK', 'routes': [single]}

    async def report_departed(self, trip_id, key='departed-key', event_type='departed'):
        async def send(kind, leg_id, event_key):
            return await self.call(f'/trips/{trip_id}/events', method='POST', user='main', key=event_key,
                                   body={'client_event_id': str(uuid4()), 'type': kind, 'source': 'manual',
                                         'occurred_at': datetime.now(timezone.utc).isoformat(), 'leg_id': leg_id})
        detail = await self.call(f'/trips/{trip_id}', user='main')
        progress = detail[2]['data']['trip']['progress']
        if event_type == 'boarded':
            approach = await send('approach_arrived', progress['actions']['approach_arrived'], 'approach-' + key)
            self.assertEqual(approach[0], 201, approach)
            progress = (await self.call(f'/trips/{trip_id}', user='main'))[2]['data']['trip']['progress']
        event = await send(event_type, progress['actions'][event_type], key)
        self.assertEqual(event[0], 201, event)
        return event

    async def set_sharing(self, meeting_id, enabled=True, expected_version=2):
        return await self.call(f'/meetings/{meeting_id}/members/me/sharing', method='PATCH', user='main',
                               body={'enabled': enabled, 'expected_version': expected_version})

    async def statuses(self, meeting_id):
        return await self.call(f'/meetings/{meeting_id}/shared-statuses', user='main')

    async def test_sharing_toggle_and_trip_event_states(self):
        meeting, _ = await self.solo_confirmed()
        meeting_id = meeting['meeting_id']
        states = await self.statuses(meeting_id)
        self.assertEqual(states[0], 200)
        self.assertEqual(states[2]['data']['items'][0]['state'], 'sharing_off')
        enabled = await self.set_sharing(meeting_id)
        self.assertEqual(enabled[0], 200, enabled)
        self.assertTrue(enabled[2]['data']['enabled'])
        self.assertEqual(enabled[2]['data']['member_version'], 3)
        states = await self.statuses(meeting_id)
        self.assertEqual(states[2]['data']['items'][0]['state'], 'unknown')
        stale = await self.set_sharing(meeting_id, expected_version=2)
        self.assertEqual(stale[0], 409)
        self.assertEqual(stale[2]['error']['code'], 'VERSION_CONFLICT')
        guidance = await self.guidance(meeting_id, meeting['current_revision_id'])
        trip = await self.call('/trips', user='main', key='status-trip-key',
                               body={'guidance_id': guidance[2]['data']['guidance']['guidance_id'],
                                     'measurement_mode': 'assisted'})
        self.assertEqual(trip[0], 201, trip)
        trip_id = trip[2]['data']['trip_id']
        states = await self.statuses(meeting_id)
        self.assertEqual(states[2]['data']['items'][0]['state'], 'unknown')
        await self.report_departed(trip_id, key='departed-key')
        row = (await self.statuses(meeting_id))[2]['data']['items'][0]
        self.assertEqual(row['state'], 'reported_departed')
        self.assertEqual(row['source'], 'manual')
        self.assertIsNotNone(row['reported_at'])
        self.assertIsNotNone(row['estimated_arrival_at'])
        self.assertIsNotNone(row['eta_calculated_at'])
        self.assertIsNotNone(row['valid_until'])
        await self.report_departed(trip_id, key='boarded-key', event_type='boarded')
        row = (await self.statuses(meeting_id))[2]['data']['items'][0]
        self.assertEqual(row['state'], 'in_transit')
        arrival = await self.call(f'/meetings/{meeting_id}/arrivals', method='POST', user='main', key='arrival-key',
                                  body={'meeting_journey_id': guidance[2]['data']['meeting_journey_id'],
                                        'client_event_id': str(uuid4()),
                                        'occurred_at': datetime.now(timezone.utc).isoformat(), 'source': 'manual'})
        self.assertEqual(arrival[0], 201, arrival)
        row = (await self.statuses(meeting_id))[2]['data']['items'][0]
        self.assertEqual(row['state'], 'arrived')

    async def test_departed_without_eta_shows_unavailable(self):
        meeting, _ = await self.solo_confirmed()
        meeting_id = meeting['meeting_id']
        await self.set_sharing(meeting_id)
        with patch.object(places_provider, 'region_for_location', return_value='서울 합성동'), \
             patch.object(journey_provider, 'fetch_routes', return_value=self._no_egress_routes()), \
             patch.object(public_mapping, 'resolve', side_effect=resolve_any), \
             patch.object(arrivals_provider, 'fetch', return_value=[('123', 780)]):
            guidance = await self.call(f'/meetings/{meeting_id}/guidance-queries', user='main', key='no-egress-key',
                                       body={'meeting_revision_id': meeting['current_revision_id'],
                                             'departure_basis': 'recommended'})
        self.assertEqual(guidance[0], 200, guidance)
        self.assertIsNone(guidance[2]['data']['meeting_arrival_slack_seconds'])
        trip = await self.call('/trips', user='main', key='no-egress-trip-key',
                               body={'guidance_id': guidance[2]['data']['guidance']['guidance_id'],
                                     'measurement_mode': 'assisted'})
        self.assertEqual(trip[0], 201, trip)
        await self.report_departed(trip[2]['data']['trip_id'], key='no-egress-departed-key')
        row = (await self.statuses(meeting_id))[2]['data']['items'][0]
        self.assertEqual(row['state'], 'unavailable')
        self.assertEqual(row['source'], 'manual')
        self.assertIsNotNone(row['reported_at'])
        self.assertIsNone(row['estimated_arrival_at'])
        self.assertIsNone(row['valid_until'])

    async def test_arrival_reports_corrections_and_idempotency(self):
        meeting, _ = await self.solo_confirmed()
        meeting_id = meeting['meeting_id']
        guidance = await self.guidance(meeting_id, meeting['current_revision_id'])
        journey_id = guidance[2]['data']['meeting_journey_id']
        trip = await self.call('/trips', user='main', key='arrival-trip-key',
                               body={'guidance_id': guidance[2]['data']['guidance']['guidance_id'],
                                     'measurement_mode': 'assisted'})
        self.assertEqual(trip[0], 201, trip)
        trip_id = trip[2]['data']['trip_id']
        enabled = await self.set_sharing(meeting_id, expected_version=2)
        self.assertEqual(enabled[0], 200)
        early = await self.call(f'/meetings/{meeting_id}/arrivals', method='POST', user='main', key='early-arrival-key',
                                body={'meeting_journey_id': journey_id, 'client_event_id': str(uuid4()),
                                      'occurred_at': datetime.now(timezone.utc).isoformat(), 'source': 'manual'})
        self.assertEqual(early[0], 409)
        self.assertEqual(early[2]['error']['code'], 'EVENT_ORDER_CONFLICT')
        await self.report_departed(trip_id, key='arrival-departed-key')
        client_id = str(uuid4())
        occurred = datetime.now(timezone.utc).isoformat()
        arrival = await self.call(f'/meetings/{meeting_id}/arrivals', method='POST', user='main', key='arrival-key',
                                  body={'meeting_journey_id': journey_id, 'client_event_id': client_id,
                                        'occurred_at': occurred, 'source': 'manual'})
        self.assertEqual(arrival[0], 201, arrival)
        data = arrival[2]['data']
        self.assertEqual(data['version'], 1)
        self.assertEqual(data['source'], 'manual')
        replay = await self.call(f'/meetings/{meeting_id}/arrivals', method='POST', user='main', key='arrival-key',
                                 body={'meeting_journey_id': journey_id, 'client_event_id': client_id,
                                       'occurred_at': occurred, 'source': 'manual'})
        self.assertEqual(replay[0], 200)
        self.assertEqual(replay[2]['data']['arrival_id'], data['arrival_id'])
        conflict = await self.call(f'/meetings/{meeting_id}/arrivals', method='POST', user='main', key='arrival-key',
                                   body={'meeting_journey_id': journey_id, 'client_event_id': client_id,
                                         'occurred_at': datetime.now(timezone.utc).isoformat(), 'source': 'manual'})
        self.assertEqual(conflict[0], 409)
        self.assertEqual(conflict[2]['error']['code'], 'IDEMPOTENCY_CONFLICT')
        row = (await self.statuses(meeting_id))[2]['data']['items'][0]
        self.assertEqual(row['state'], 'arrived')
        before = row['reported_at']
        missing_field = await self.call(f'/meetings/{meeting_id}/arrival-corrections', method='POST', user='main',
                                        key='missing-field-key',
                                        body={'arrival_id': data['arrival_id'], 'expected_version': 1,
                                              'correction_reason': 'wrong_time'})
        self.assertEqual(missing_field[0], 422)
        wrong_version = await self.call(f'/meetings/{meeting_id}/arrival-corrections', method='POST', user='main',
                                        key='wrong-version-key',
                                        body={'arrival_id': data['arrival_id'], 'expected_version': 2,
                                              'occurred_at': occurred, 'correction_reason': 'wrong_time'})
        self.assertEqual(wrong_version[0], 409)
        self.assertEqual(wrong_version[2]['error']['code'], 'VERSION_CONFLICT')
        corrected_at = (datetime.now(timezone.utc) + timedelta(seconds=90)).isoformat()
        corrected = await self.call(f'/meetings/{meeting_id}/arrival-corrections', method='POST', user='main',
                                    key='correct-time-key',
                                    body={'arrival_id': data['arrival_id'], 'expected_version': 1,
                                          'occurred_at': corrected_at,
                                          'correction_reason': 'wrong_time'})
        self.assertEqual(corrected[0], 201, corrected)
        self.assertEqual(corrected[2]['data']['arrival_id'], data['arrival_id'])
        self.assertEqual(corrected[2]['data']['version'], 2)
        row = (await self.statuses(meeting_id))[2]['data']['items'][0]
        self.assertEqual(row['state'], 'arrived')
        self.assertNotEqual(row['reported_at'], before)
        replay = await self.call(f'/meetings/{meeting_id}/arrival-corrections', method='POST', user='main',
                                 key='correct-time-key',
                                 body={'arrival_id': data['arrival_id'], 'expected_version': 1,
                                       'occurred_at': corrected_at,
                                       'correction_reason': 'wrong_time'})
        self.assertEqual(replay[0], 200)
        self.assertEqual(replay[2]['data']['version'], 2)
        excluded = await self.call(f'/meetings/{meeting_id}/arrival-corrections', method='POST', user='main',
                                   key='exclude-key',
                                   body={'arrival_id': data['arrival_id'], 'expected_version': 2, 'excluded': True,
                                         'correction_reason': 'wrong_action'})
        self.assertEqual(excluded[0], 201)
        row = (await self.statuses(meeting_id))[2]['data']['items'][0]
        self.assertEqual(row['state'], 'reported_departed')
        await self.signin('other', 'other@example.invalid')
        foreign = await self.call(f'/meetings/{meeting_id}/arrival-corrections', method='POST', user='other',
                                  key='foreign-key',
                                  body={'arrival_id': data['arrival_id'], 'expected_version': 2,
                                        'occurred_at': corrected_at,
                                        'correction_reason': 'wrong_time'})
        self.assertEqual(foreign[0], 404)

    async def test_draft_meeting_sharing_stays_off(self):
        await self.signin('main', 'main@example.invalid')
        meeting = await self.make_meeting()
        enabled = await self.call(f"/meetings/{meeting['meeting_id']}/members/me/sharing", method='PATCH', user='main',
                                  body={'enabled': True, 'expected_version': 1})
        self.assertEqual(enabled[0], 200)
        row = (await self.statuses(meeting['meeting_id']))[2]['data']['items'][0]
        self.assertEqual(row['state'], 'sharing_off')
