"""Temporary origin validation with real auth/DB, synthetic coordinates only."""
import io
import logging
from datetime import datetime
from unittest.mock import patch
from uuid import uuid4
import unittest
import test_places
from app import auth, places


class OriginTests(unittest.IsolatedAsyncioTestCase):
    setUp = test_places.PlaceTests.setUp
    tearDown = test_places.PlaceTests.tearDown
    call = test_places.PlaceTests.call
    prepare = test_places.PlaceTests.prepare
    credentials = test_places.PlaceTests.credentials
    signup_login = test_places.PlaceTests.signup_login
    saved = test_places.PlaceTests.saved
    create = test_places.PlaceTests.create

    async def validate(self, selection, **options):
        with patch.object(places, 'region_for_location', return_value='서울특별시 합성동') as provider:
            result = await self.call('/origin-validations', {'origin':selection}, **options)
        return result, provider

    async def test_current_metadata_expiry_privacy_and_no_place_creation(self):
        await self.signup_login()
        origin = {'type':'current_location','latitude':37.51,'longitude':127.01,
                  'accuracy_meters':14.5,'captured_at':'2026-10-07T10:00:00+09:00'}
        from app.request_logging import logger, RequestJsonFormatter, RequestEventFilter
        output = io.StringIO()
        handler = logging.StreamHandler(output)
        handler.setFormatter(RequestJsonFormatter()); handler.addFilter(RequestEventFilter())
        previous, level = logger.handlers[:], logger.level
        logger.handlers[:] = [handler]; logger.setLevel(logging.INFO)
        try:
            result, provider = await self.validate(origin)
        finally:
            logger.handlers[:] = previous; logger.setLevel(level)
        self.assertEqual(result[0],200)
        self.assertEqual(result[1][b'cache-control'],b'no-store')
        data = result[2]['data']
        self.assertEqual(data['quality_status'],'pending')
        self.assertEqual(data['origin']['type'],'current_location')
        self.assertEqual(data['origin']['captured_at'],'2026-10-07T01:00:00Z')
        self.assertEqual(data['origin']['accuracy_meters'],14.5)
        ttl = datetime.fromisoformat(data['expires_at']) - datetime.fromisoformat(result[2]['meta']['server_time'])
        self.assertTrue(599 < ttl.total_seconds() <= 600)
        provider.assert_called_once()
        self.assertEqual((await self.call('/places'))[2]['data']['items'],[])
        line = output.getvalue()
        self.assertIn('/api/v1/origin-validations',line)
        self.assertIn(result[2]['meta']['request_id'],line)
        for private in ['37.51','127.01','14.5','captured_at','합성동',self.cookie,self.csrf]:
            self.assertNotIn(private,line)

    async def test_saved_ownership_location_version_and_current_label(self):
        await self.signup_login()
        _, created = await self.saved()
        place = created[2]['data']
        origin = {'type':'saved_place','place_id':place['place_id'],'location_version':1}
        with auth.database() as connection:
            connection.execute('UPDATE saved_places SET label=%s,version=version+1 WHERE id=%s',('새 이름',place['place_id']))
        result, provider = await self.validate(origin)
        self.assertEqual(result[0],200); provider.assert_not_called()
        self.assertEqual(result[2]['data']['label'],'새 이름')
        self.assertEqual(result[2]['data']['origin']['location_version'],1)
        self.assertEqual((await self.validate({**origin,'location_version':2}))[0][0],409)
        self.assertEqual((await self.validate({**origin,'place_id':str(uuid4())}))[0][0],404)
        old_cookie,old_csrf=self.cookie,self.csrf
        self.cookie=None;self.csrf=None
        await self.prepare()
        credentials=self.credentials('other@example.invalid')
        await self.call('/auth/register',credentials)
        logged=await self.call('/auth/login',{'email':credentials['email'],'password':credentials['password']})
        self.cookie=logged[1][b'set-cookie'].decode().split(';')[0];self.csrf=logged[2]['data']['csrf_token']
        self.assertEqual((await self.validate(origin))[0][0],404)
        self.cookie,self.csrf=old_cookie,old_csrf
        with auth.database() as connection:
            connection.execute('DELETE FROM saved_places WHERE id=%s',(place['place_id'],))
        self.assertEqual((await self.validate(origin))[0][0],404)

    async def test_auth_csrf_validation_and_map_region_failures(self):
        origin={'type':'map_pin','latitude':37.5,'longitude':127}
        self.assertEqual((await self.validate(origin))[0][0],401)
        await self.signup_login()
        self.assertEqual((await self.validate(origin,csrf=False))[0][0],403)
        self.assertEqual((await self.validate(origin,origin='http://evil.invalid'))[0][0],403)
        current={**origin,'type':'current_location','accuracy_meters':1,'captured_at':'2026-10-07T01:00:00Z'}
        for invalid in [{**origin,'latitude':91},{**origin,'extra':True},{**origin,'type':'unknown'},
                        {**current,'accuracy_meters':-1},{**current,'captured_at':'2026-10-07'},
                        {**current,'captured_at':123},{**current,'captured_at':'123'},
                        {**current,'captured_at':'2026-10-07T01:00:00'}]:
            result, provider=await self.validate(invalid)
            self.assertEqual(result[0],422);provider.assert_not_called()
        for status,code in [(422,'UNSUPPORTED_REGION'),(503,'PROVIDER_UNAVAILABLE'),(502,'PROVIDER_RESPONSE_INVALID')]:
            with patch.object(places,'region_for_location',side_effect=auth.AuthError(status,code,'synthetic')):
                result=await self.call('/origin-validations',{'origin':origin})
            self.assertEqual(result[0],status)
        result,_=await self.validate(origin)
        self.assertEqual(result[0],200);self.assertEqual(result[2]['data']['quality_status'],'not_applicable')

    async def test_limit_includes_failed_provider_calls(self):
        await self.signup_login()
        origin={'type':'map_pin','latitude':37.5,'longitude':127}
        with patch.object(places,'region_for_location',side_effect=auth.AuthError(503,'PROVIDER_UNAVAILABLE','synthetic')) as provider:
            for _ in range(10):
                self.assertEqual((await self.call('/origin-validations',{'origin':origin}))[0],503)
            result=await self.call('/origin-validations',{'origin':origin})
        self.assertEqual(result[0],429);self.assertIn(b'retry-after',result[1]);self.assertEqual(provider.call_count,10)
