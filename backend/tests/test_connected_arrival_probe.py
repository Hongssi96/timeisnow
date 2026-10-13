import unittest,urllib.error,urllib.request,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from check_arrival_connection import Budget,eligible,PUBLIC_BODY

class ConnectedProbeTests(unittest.TestCase):
    def test_budget_stops_before_an_extra_transmission(self):
        budget=Budget(2)
        budget.before('https://dapi.kakao.com/v2/routing/publictraffic')
        budget.before(urllib.request.Request('https://apis.data.go.kr/6410000/busstationservice/v2/getBusStationListv2'))
        with self.assertRaises(urllib.error.URLError):budget.before('https://apis.data.go.kr/6410000/busarrivalservice/v2/getBusArrivalItemv2')
        self.assertEqual(budget.count,2);self.assertTrue(budget.exhausted)

    def test_http_redirect_host_credentials_and_nonstandard_ports_are_rejected(self):
        budget=Budget(10)
        for url in ['http://apis.data.go.kr/', 'https://example.org/', 'https://apis.data.go.kr:444/',
                    'https://private@apis.data.go.kr/', 'https://apis.data.go.kr.example.org/']:
            with self.assertRaises(urllib.error.URLError):budget.before(url)
        self.assertEqual(budget.count,0)
        for value in [0,11,True,None]:
            with self.assertRaises(ValueError):Budget(value)

    def test_selection_requires_direct_first_bus_and_single_vehicle(self):
        def item(kind='BUS',transfers=0,vehicles=1):
            return {'transfer_count':transfers,'ordered_legs':[{'type':'WALKING'}, {'type':kind,'vehicles':[{}]*vehicles}]}
        chosen=item()
        self.assertIs(eligible([item('SUBWAY'),item(transfers=1),item(vehicles=2),chosen]),chosen)
        self.assertIsNone(eligible([item('SUBWAY')]))

    def test_public_fixture_has_no_user_saved_place_or_override_parameters(self):
        self.assertEqual(PUBLIC_BODY['origin']['type'],'map_pin')
        self.assertEqual(PUBLIC_BODY['origin']['longitude'],127.11119217)
        self.assertEqual(PUBLIC_BODY['destination']['longitude'],127.12628814)
        self.assertNotIn('place_id',str(PUBLIC_BODY))

class OfflineProbeTests(unittest.IsolatedAsyncioTestCase):
    async def test_full_probe_uses_isolated_schema_and_reuses_evidence_without_network(self):
        import check_arrival_connection as probe
        import test_arrival_mapping_connection as fixtures
        import test_walking as walking
        from unittest.mock import patch
        from app.places import provider as places
        from app.journeys import provider as journeys
        from app.arrivals import mapping,provider
        from test_auth import connect_db
        def counts():
            with connect_db() as connection:
                root=connection.execute('SELECT count(*) FROM public.users').fetchone()[0]
                temporary=connection.execute("SELECT count(*) FROM pg_namespace WHERE nspname LIKE 'auth_test_%'").fetchone()[0]
                return root,temporary
        before=counts()
        with patch.object(places,'region_for_location',return_value='경기도 합성동'), \
             patch.object(journeys,'fetch_routes',return_value={'status':'OK','routes':[walking.route()]}), \
             patch.object(mapping,'query',side_effect=fixtures.query_fixture), \
             patch.object(provider,'fetch',return_value=[('123',300)]), \
             patch.object(urllib.request.OpenerDirector,'open',side_effect=AssertionError('No external request')) as network:
            result=await probe.run(10)
            network.assert_not_called()
        self.assertEqual(result['status'],'connection_verified')
        self.assertEqual(result['request_count'],0)
        self.assertEqual(result['source_status'],'unknown')
        self.assertTrue(result['valid_for_guidance'])
        self.assertTrue(result['second_get_no_upstream'])
        self.assertTrue(result['second_get_same_evidence'])
        self.assertTrue(result['stored_search_unchanged'])
        self.assertEqual(before,counts())

    async def test_failed_source_attempt_is_counted_and_never_prints_raw_error(self):
        import check_arrival_connection as probe
        from unittest.mock import patch
        from app.places import provider as places
        from app.common.errors import AuthError
        def region(_):
            try:urllib.request.build_opener().open('https://dapi.kakao.com/',timeout=1)
            except TimeoutError:raise AuthError(504,'PROVIDER_TIMEOUT','응답이 늦어요.')
        with patch.object(places,'region_for_location',side_effect=region), \
             patch.object(urllib.request.OpenerDirector,'open',side_effect=TimeoutError('private-url-and-key')):
            result=await probe.run(10)
        self.assertEqual(result['status'],'search_failed')
        self.assertEqual(result['request_count'],1)
        self.assertNotIn('private',str(result))

if __name__=='__main__':unittest.main()
