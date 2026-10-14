import copy,unittest
from datetime import datetime,timedelta,timezone
from unittest.mock import patch
from uuid import uuid4
from test_first_arrivals import ArrivalApiTests,mapping
from app.arrivals import service as arrivals,provider
from app.guidance import service
from app.common.database import database
from app.common.errors import AuthError
from psycopg.types.json import Jsonb

class DepartureCalculationTests(unittest.TestCase):
    def fixture(self,seconds=780):
        at=datetime.now(timezone.utc)
        evidence=arrivals.normalize(mapping(),[('123',seconds)],at,at,uuid4(),uuid4(),at+timedelta(seconds=300))
        profile={'factor':1.,'buffer':300,'version':1}
        return at,evidence,profile

    def test_thirteen_minutes_minus_five_walk_and_five_buffer(self):
        at,e,p=self.fixture();value=service.calculate(e,300,300,p,at)
        self.assertEqual(value.status,'ready');self.assertTrue(value.valid_for_guidance)
        self.assertEqual(value.recommended_departure_at,at+timedelta(seconds=180))
        self.assertEqual(value.selected_departure_at,value.recommended_departure_at)
        self.assertEqual(value.slack_seconds,300);self.assertEqual(value.slack_status,'meets_buffer')
        self.assertEqual(value.timing_basis,'receipt_estimate');self.assertIsNone(value.arrival_evidence.generated_at)

    def test_now_retains_recommended_time_with_eight_minutes_slack(self):
        at,e,p=self.fixture();value=service.calculate(e,300,300,p,at,'now')
        self.assertEqual(value.selected_departure_at,at);self.assertEqual(value.slack_seconds,480)
        self.assertEqual(value.recommended_departure_at,at+timedelta(seconds=180))

    def test_past_recommendation_uses_now_without_claiming_full_buffer(self):
        at,e,p=self.fixture(480);value=service.calculate(e,300,300,p,at)
        self.assertEqual(value.selected_departure_at,at);self.assertLess(value.recommended_departure_at,at)
        self.assertEqual(value.slack_seconds,180);self.assertEqual(value.slack_status,'below_buffer')
        self.assertIn('BUFFER_NOT_MET',value.reasons)

    def test_negative_slack_is_not_clamped_or_replaced_with_next_vehicle(self):
        at,e,p=self.fixture(120);value=service.calculate(e,300,300,p,at)
        self.assertEqual(value.slack_seconds,-180);self.assertEqual(value.status,'not_enough_time')
        self.assertFalse(value.valid_for_guidance);self.assertEqual(value.slack_status,'unreachable')

    def test_missing_access_and_arrival_never_make_departure_numbers(self):
        at,e,p=self.fixture()
        for evidence,base,walking in ((e,None,None),(e.model_copy(update={'status':'insufficient_data','valid_for_guidance':False}),300,300)):
            value=service.calculate(evidence,base,walking,p,at)
            self.assertIsNone(value.recommended_departure_at);self.assertIsNone(value.slack_seconds)
            self.assertFalse(value.valid_for_guidance)

    def test_expiry_and_past_vehicle_remove_numbers(self):
        at,e,p=self.fixture(30)
        for observed in (at+timedelta(seconds=30),at+timedelta(seconds=120.001)):
            value=service.calculate(e,300,300,p,observed)
            self.assertIsNone(value.vehicle_arrival_at);self.assertIsNone(value.recommended_departure_at)
            self.assertFalse(value.valid_for_guidance)
        self.assertEqual(service.calculate(e,300,300,p,at+timedelta(seconds=120.001)).status,'stale')

    def test_access_personalization_rounds_up_and_excludes_other_legs(self):
        route={'missing_segments':[],'ordered_legs':[{'type':'WALKING','walking_role':'access','seconds':101}, {'type':'WALKING','walking_role':'access','seconds':100}, {'type':'BUS'}, {'type':'WALKING','walking_role':'egress','seconds':999}]}
        self.assertEqual(service.approach(route,1.1),(201,222))
        for field,value in (('seconds',0),('walking_role','transfer')):
            invalid=copy.deepcopy(route);invalid['ordered_legs'][0][field]=value
            self.assertEqual(service.approach(invalid,1.),(None,None))
        route['missing_segments']=['ACCESS_WALK_MISSING'];self.assertEqual(service.approach(route,1.),(None,None))

    def test_clock_error_is_not_accepted_as_receipt_estimate(self):
        at,e,p=self.fixture();value=service.calculate(e,300,300,p,at-timedelta(seconds=1))
        self.assertFalse(value.valid_for_guidance);self.assertIsNone(value.recommended_departure_at)

    def test_overflow_is_insufficient_instead_of_crashing(self):
        at,e,p=self.fixture();value=service.calculate(e,10**100,10**100,p,at)
        self.assertFalse(value.valid_for_guidance);self.assertIsNone(value.approach_seconds)

class DepartureApiTests(unittest.IsolatedAsyncioTestCase):
    setUp=ArrivalApiTests.setUp
    tearDown=ArrivalApiTests.tearDown
    setup_route=ArrivalApiTests.setup_route
    call=ArrivalApiTests.call
    prepare=ArrivalApiTests.prepare
    credentials=ArrivalApiTests.credentials
    signup_login=ArrivalApiTests.signup_login
    saved=ArrivalApiTests.saved
    create=ArrivalApiTests.create
    search=ArrivalApiTests.search
    completed=ArrivalApiTests.completed
    evidence_path=ArrivalApiTests.evidence_path

    async def ready(self):
        await self.setup_route();self.path=self.path.replace('first-arrivals','first-departure')
        return patch.object(arrivals.public_mapping,'resolve',return_value=self.mapping)

    async def test_owned_get_uses_profile_and_original_access_without_db_writes(self):
        guard=await self.ready()
        with database() as c:
            before=c.execute('SELECT * FROM journey_searches WHERE id=%s',(self.search_id,)).fetchone()
            c.execute('UPDATE user_profiles SET walking_duration_factor=1.1,version=2 WHERE user_id=%s',(self.owner,))
        with guard,patch.object(provider,'fetch',return_value=[('123',1800)]) as fetch:
            one=await self.call(self.path);two=await self.call(self.path)
        self.assertEqual((one[0],two[0],fetch.call_count),(200,200,1))
        value=one[2]['data'];self.assertEqual(value['model_version'],'first.departure.v1')
        self.assertEqual(value['profile_version'],2);self.assertEqual(value['applied_duration_factor'],1.1)
        self.assertEqual(value['buffer_seconds'],300);self.assertTrue(value['valid_for_guidance'])
        self.assertEqual(value['arrival_evidence']['received_at'],two[2]['data']['arrival_evidence']['received_at'])
        self.assertEqual(one[1][b'cache-control'],b'no-store')
        with database() as c:self.assertEqual(before,c.execute('SELECT * FROM journey_searches WHERE id=%s',(self.search_id,)).fetchone())

    async def test_coefficient_recalculation_reuses_arrival_without_ai(self):
        guard=await self.ready()
        with guard,patch.object(provider,'fetch',return_value=[('123',1800)]) as fetch:
            one=await self.call(self.path)
            with database() as c:c.execute('UPDATE user_profiles SET walking_duration_factor=2,version=version+1 WHERE user_id=%s',(self.owner,))
            two=await self.call(self.path)
        self.assertEqual(fetch.call_count,1)
        self.assertEqual(two[2]['data']['approach_seconds'],one[2]['data']['provider_approach_seconds']*2)
        self.assertNotEqual(one[2]['data']['approach_seconds'],two[2]['data']['approach_seconds'])

    async def test_profile_changes_during_fetch_reject_old_calculation(self):
        guard=await self.ready()
        def changed(_):
            with database() as c:c.execute('UPDATE user_profiles SET version=version+1 WHERE user_id=%s',(self.owner,))
            return [('123',1800)]
        with guard,patch.object(provider,'fetch',side_effect=changed):
            value=await self.call(self.path)
        self.assertEqual(value[0],409);self.assertEqual(value[2]['error']['code'],'VERSION_CONFLICT')

    async def test_invalid_basis_and_owner_never_fetch(self):
        await self.ready()
        from test_api_contract import request
        from app.main import app
        with patch.object(provider,'fetch') as fetch:
            status,_,_=await request('/api/v1'+self.path)
            self.assertEqual(status,401)
            with self.assertRaises(AuthError):service.first_departure(uuid4(),self.search_id,self.candidate_id)
            with self.assertRaises(AuthError):service.first_departure(self.owner,self.search_id,self.candidate_id,'invalid')
            invalid=await request('/api/v1'+self.path,query=b'departure_basis=bad',headers=[(b'cookie',self.cookie.encode())])
            self.assertEqual(invalid[0],422)
            fetch.assert_not_called()
        with patch.object(arrivals.public_mapping,'resolve',return_value=self.mapping),patch.object(provider,'fetch',return_value=[('123',1800)]):
            value=await request('/api/v1'+self.path,query=b'departure_basis=now',headers=[(b'cookie',self.cookie.encode())])
        self.assertEqual(value[0],200);self.assertEqual(value[2]['data']['departure_basis'],'now')
        self.assertTrue(value[2]['data']['valid_for_guidance'])

    async def test_missing_mapping_returns_insufficient_without_departure(self):
        await self.ready()
        with patch.object(provider,'fetch') as fetch:value=await self.call(self.path)
        self.assertEqual(value[0],200);self.assertEqual(value[2]['data']['status'],'insufficient_data')
        self.assertIsNone(value[2]['data']['recommended_departure_at']);fetch.assert_not_called()

    async def test_profile_factor_database_bounds_and_defaults(self):
        await self.ready()
        with database() as c:
            row=c.execute('SELECT walking_duration_factor FROM user_profiles WHERE user_id=%s',(self.owner,)).fetchone()
        self.assertEqual(row['walking_duration_factor'],1.)
        from psycopg.errors import CheckViolation
        from app.common import database as common_database
        for factor in (.49,2.01,float('nan'),float('inf')):
            with self.assertRaises(CheckViolation),common_database.connect_db() as c:
                c.execute('UPDATE user_profiles SET walking_duration_factor=%s WHERE user_id=%s',(factor,self.owner))

del ArrivalApiTests
if __name__=='__main__':unittest.main()
