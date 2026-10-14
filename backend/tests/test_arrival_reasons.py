"""Fixed mapping failure reasons, no new provider calls or private diagnostics."""
import unittest,json
from unittest.mock import patch
from test_arrival_mapping_connection import ConnectedArrivalTests
from app.arrivals import service,mapping,provider,cache
from app.guidance import service as departure
from app.common.database import database
from psycopg.types.json import Jsonb

class ArrivalReasonTests(unittest.IsolatedAsyncioTestCase):
    setUp=ConnectedArrivalTests.setUp;tearDown=ConnectedArrivalTests.tearDown
    setup_route=ConnectedArrivalTests.setup_route;call=ConnectedArrivalTests.call
    prepare=ConnectedArrivalTests.prepare;credentials=ConnectedArrivalTests.credentials;signup_login=ConnectedArrivalTests.signup_login
    saved=ConnectedArrivalTests.saved;create=ConnectedArrivalTests.create;search=ConnectedArrivalTests.search;completed=ConnectedArrivalTests.completed
    evidence_path=ConnectedArrivalTests.evidence_path

    async def test_safe_mapping_reason_reuses_failure_cache_without_extra_requests(self):
        await self.setup_route()
        def missing(context,expiry,diagnostics=None,**kwargs):
            diagnostics.update(reason='NO_ROUTE_AT_BOARDING_STOP',station_id='private',match_checks={'raw':'secret'})
            return None
        with patch.object(mapping,'resolve',side_effect=missing) as resolve,patch.object(provider,'fetch') as fetch:
            first=await self.call(self.path);second=await self.call(self.path)
        self.assertEqual((first[0],second[0],resolve.call_count,fetch.call_count),(200,200,1,0))
        self.assertEqual(first[2]['data']['reasons'],['PUBLIC_MAPPING_UNCONFIRMED','NO_ROUTE_AT_BOARDING_STOP'])
        self.assertEqual(first[2]['data'],second[2]['data'])
        for text in ('private','secret','station_id','match_checks'):self.assertNotIn(text,json.dumps(first[2]))

    async def test_raw_reason_is_ignored_without_relaxing_mapping_failure(self):
        await self.setup_route()
        def missing(context,expiry,diagnostics=None,**kwargs):diagnostics.update(reason='secret raw response');return None
        with patch.object(mapping,'resolve',side_effect=missing):reply=await self.call(self.path)
        self.assertEqual(reply[2]['data']['reasons'],['PUBLIC_MAPPING_UNCONFIRMED']);self.assertFalse(reply[2]['data']['valid_for_guidance'])

    async def test_missing_process_context_identifies_need_for_new_search_without_mapping_calls(self):
        await self.setup_route();cache.clear()
        with patch.object(mapping,'resolve') as resolve,patch.object(provider,'fetch') as fetch:reply=await self.call(self.path)
        self.assertIn('MAPPING_CONTEXT_UNAVAILABLE',reply[2]['data']['reasons']);resolve.assert_not_called();fetch.assert_not_called()

    async def test_multiple_bus_options_have_specific_reason_and_no_mapping_calls(self):
        await self.setup_route()
        with database() as connection:
            row=connection.execute('SELECT candidates FROM journey_searches WHERE id=%s',(self.search_id,)).fetchone();values=row['candidates']
            leg=next(x for x in values[0]['ordered_legs'] if x['type']=='BUS');leg['vehicles']=['합성1','합성2'];leg['vehicle_options']=[{'name':v,'provider_type':None} for v in leg['vehicles']]
            connection.execute('UPDATE journey_searches SET candidates=%s WHERE id=%s',(Jsonb(values),self.search_id))
        with patch.object(mapping,'resolve') as resolve:reply=await self.call(self.path)
        self.assertEqual(reply[0],200);self.assertIn('MULTIPLE_VEHICLE_OPTIONS',reply[2]['data']['reasons']);resolve.assert_not_called()

    def test_allowlist_never_returns_unknown_or_structured_diagnostic(self):
        for value in (None,{},['private'],'MAPPING_CONFIRMED','secret'):
            self.assertIsNone(mapping.safe_failure_reason({'reason':value}))
        self.assertEqual(mapping.safe_failure_reason({'reason':'ROUTE_SEQUENCE_UNCONFIRMED'}),'ROUTE_SEQUENCE_UNCONFIRMED')

del ConnectedArrivalTests
