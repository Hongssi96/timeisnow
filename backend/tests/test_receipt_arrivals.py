import unittest
from datetime import datetime,timedelta,timezone
from unittest.mock import patch
from uuid import uuid4
from test_first_arrivals import mapping
from test_arrival_mapping_connection import ConnectedArrivalTests
from app.arrivals import service,provider
from app.common.errors import AuthError

class ReceiptPolicyTests(unittest.TestCase):
    def evidence(self,elapsed=0,seconds=300,generation=None,search_seconds=300):
        at=datetime.now(timezone.utc);received=at-timedelta(seconds=elapsed)
        m=mapping();m.verified_at=received-timedelta(seconds=1)
        return service.normalize(m,[('123',seconds)],received,at,uuid4(),uuid4(),at+timedelta(seconds=search_seconds),generation)

    def test_receipt_estimate_never_claims_verified_generation(self):
        value=self.evidence(elapsed=40)
        self.assertEqual(value.model_version,'arrival.evidence.v2')
        self.assertEqual((value.status,value.source_status,value.timing_basis),('estimated','unknown','receipt_estimate'))
        self.assertIsNone(value.generated_at);self.assertTrue(value.valid_for_guidance)
        self.assertEqual(value.candidates[0].predicted_arrival_at,value.received_at+timedelta(seconds=300))
        self.assertEqual(value.candidates[0].remaining_seconds,260)
        self.assertIn('RECEIPT_BASED_ESTIMATE',value.reasons)

    def test_120_second_boundary_not_extended_by_projection(self):
        value=self.evidence(elapsed=120)
        self.assertTrue(value.valid_for_guidance)
        expired=service.project(value,value.received_at+timedelta(seconds=120.001))
        self.assertEqual(expired.status,'expired');self.assertFalse(expired.valid_for_guidance)
        self.assertEqual(expired.candidates,[]);self.assertEqual(expired.expires_at,value.expires_at)

    def test_countdown_reuses_original_anchor_and_identity(self):
        value=self.evidence();at=value.received_at+timedelta(seconds=10.2)
        updated=service.project(value,at)
        self.assertEqual(updated.candidates[0].remaining_seconds,290)
        self.assertEqual(updated.candidates[0].candidate_id,value.candidates[0].candidate_id)
        self.assertEqual(updated.candidates[0].provider_prediction_seconds,300)
        self.assertEqual(updated.received_at,value.received_at)
        self.assertEqual(updated.expires_at,value.expires_at)
        self.assertEqual(value.candidates[0].remaining_seconds,300)

    def test_passed_predictions_are_removed_without_boarding_claim(self):
        for elapsed in (30,31):
            value=self.evidence(elapsed=elapsed,seconds=30)
            self.assertEqual(value.candidates,[]);self.assertFalse(value.valid_for_guidance)
            self.assertEqual(value.status,'insufficient_data')
            self.assertIn('PREDICTION_UNCONFIRMED',value.reasons)

    def test_search_mapping_expiry_cap_receipt(self):
        value=self.evidence(search_seconds=12)
        self.assertLess(value.expires_at,value.received_at+timedelta(seconds=120))
        self.assertEqual(service.project(value,value.expires_at+timedelta(microseconds=1)).status,'expired')

    def test_clock_reversal_and_invalid_generation_never_fall_back(self):
        value=self.evidence(elapsed=-1)
        self.assertEqual(value.source_status,'clock_mismatch');self.assertFalse(value.valid_for_guidance)
        for generation in (datetime.now(),datetime.now(timezone.utc)+timedelta(seconds=5)):
            value=self.evidence(generation=generation)
            self.assertEqual(value.timing_basis,'none');self.assertFalse(value.valid_for_guidance)
            self.assertTrue(all(c.predicted_arrival_at is None for c in value.candidates))

class ReceiptCacheTests(unittest.IsolatedAsyncioTestCase):
    setUp=ConnectedArrivalTests.setUp
    tearDown=ConnectedArrivalTests.tearDown
    setup_route=ConnectedArrivalTests.setup_route
    call=ConnectedArrivalTests.call
    prepare=ConnectedArrivalTests.prepare
    credentials=ConnectedArrivalTests.credentials
    signup_login=ConnectedArrivalTests.signup_login
    saved=ConnectedArrivalTests.saved
    create=ConnectedArrivalTests.create
    search=ConnectedArrivalTests.search
    completed=ConnectedArrivalTests.completed
    evidence_path=ConnectedArrivalTests.evidence_path
    entry=ConnectedArrivalTests.entry

    async def test_cached_get_projects_remaining_without_upstream_or_new_receipt(self):
        await self.setup_route()
        with patch.object(service.public_mapping,'resolve',return_value=self.mapping),patch.object(provider,'fetch',return_value=[('123',30)]) as fetch:
            first=await self.call(self.path);value=self.entry().evidence
            with patch.object(service,'now',return_value=value.received_at+timedelta(seconds=15)):
                second=await self.call(self.path)
            with patch.object(service,'now',return_value=value.received_at+timedelta(seconds=30)):
                passed=await self.call(self.path)
        self.assertEqual(fetch.call_count,1)
        self.assertEqual(first[2]['data']['received_at'],second[2]['data']['received_at'])
        self.assertEqual(first[2]['data']['expires_at'],second[2]['data']['expires_at'])
        self.assertEqual(second[2]['data']['candidates'][0]['remaining_seconds'],15)
        self.assertEqual(passed[2]['data']['candidates'],[]);self.assertFalse(passed[2]['data']['valid_for_guidance'])

    async def test_failed_refresh_never_renews_old_cache(self):
        await self.setup_route()
        with patch.object(service.public_mapping,'resolve',return_value=self.mapping),patch.object(provider,'fetch',return_value=[('123',300)]):
            await self.call(self.path)
        entry=self.entry();before=entry.evidence.model_dump();attempted=entry.attempted_at
        later=entry.evidence.received_at+timedelta(seconds=61)
        with patch.object(service,'now',return_value=later),patch.object(provider,'fetch',side_effect=AuthError(504,'PROVIDER_TIMEOUT','safe')):
            response=await self.call(self.path)
        self.assertEqual(response[0],504)
        self.assertEqual(entry.evidence.model_dump(),before);self.assertEqual(entry.attempted_at,attempted)

del ConnectedArrivalTests

if __name__=='__main__':unittest.main()
