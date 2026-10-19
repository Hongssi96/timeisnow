"""Owned PostgreSQL/ASGI settings; strict input, optimistic locking and derived guidance."""
import asyncio,json,unittest
from datetime import datetime,timedelta
from unittest.mock import patch
import test_auth as auth_tests
from test_auth import PASSWORD
import test_personal_walk as walk_tests
import test_connections as connection_tests
from test_personal_walk import output
from test_api_contract import request
from app.common.database import database
from app.common.errors import AuthError
from app.auth import profile_service
from app.ai import provider as ai
from app.guidance import walk_provider,service as guidance
from app.guidance.connections import evaluate


class ProfileSettingsTests(unittest.IsolatedAsyncioTestCase):
    setUp=auth_tests.AuthTests.setUp;tearDown=auth_tests.AuthTests.tearDown;call=walk_tests.PersonalWalkTests.call
    prepare=auth_tests.AuthTests.prepare;credentials=auth_tests.AuthTests.credentials;signup_login=auth_tests.AuthTests.signup_login
    saved=walk_tests.PersonalWalkTests.saved;create=walk_tests.PersonalWalkTests.create;search=walk_tests.PersonalWalkTests.search;completed=walk_tests.PersonalWalkTests.completed
    saved_search=walk_tests.PersonalWalkTests.saved_search;routine_body=walk_tests.PersonalWalkTests.routine_body;save=walk_tests.PersonalWalkTests.save
    ready=walk_tests.PersonalWalkTests.ready;refresh=walk_tests.PersonalWalkTests.refresh;path=walk_tests.PersonalWalkTests.path;mapped=walk_tests.PersonalWalkTests.mapped;estimate=walk_tests.PersonalWalkTests.estimate;details=walk_tests.PersonalWalkTests.details

    async def change(self,body,*,cookie=None,csrf=None):
        headers=[(b'origin',b'http://127.0.0.1:5173'),(b'content-type',b'application/json')]
        if cookie is not False:headers.append((b'cookie',(cookie or self.cookie).encode()))
        if csrf is not False:headers.append((b'x-csrf-token',(csrf or self.csrf).encode()))
        return await request('/api/v1/me/profile','PATCH',headers=headers,body=json.dumps(body).encode(),timeout=20)

    async def test_save_partial_noop_conflict_and_relogin(self):
        await self.signup_login()
        before=(await self.call('/me'))[2]['data']['profile']
        result=await self.change({'expected_version':1,'walking_preference':'slow','route_preference':'less_walking','first_boarding_buffer_seconds':0,'transfer_buffer_seconds':1800})
        self.assertEqual(result[0],200,result[2]);self.assertEqual(result[1][b'cache-control'],b'no-store')
        p=result[2]['data']['profile'];self.assertEqual(p['version'],2);self.assertEqual(p['walking_duration_factor'],before['walking_duration_factor']);self.assertEqual(p['timezone'],'Asia/Seoul')
        noop=await self.change({'expected_version':2,'first_boarding_buffer_seconds':0});self.assertEqual(noop[2]['data']['profile_version'],2)
        self.assertEqual((await self.change({'expected_version':1,'first_boarding_buffer_seconds':60}))[0],409)
        await self.call('/auth/logout',{});await self.prepare()
        login=await self.call('/auth/login',{'email':'member@example.invalid','password':PASSWORD})
        self.cookie=login[1][b'set-cookie'].decode().split(';')[0];self.csrf=login[2]['data']['csrf_token']
        self.assertEqual((await self.call('/me'))[2]['data']['profile'],p)

    async def test_input_auth_csrf_and_session_expiry(self):
        await self.signup_login()
        for changes in ({},{'first_boarding_buffer_seconds':-1},{'first_boarding_buffer_seconds':1801},{'transfer_buffer_seconds':1.5},{'transfer_buffer_seconds':True},{'transfer_buffer_seconds':'30'},{'route_preference':None},{'route_preference':'unknown'},{'walking_preference':'running'},{'walking_duration_factor':2},{'timezone':'UTC'},{'user_id':'other'}):
            with self.subTest(changes=changes):self.assertEqual((await self.change({'expected_version':1,**changes}))[0],422)
        self.assertEqual((await self.change({'expected_version':True,'transfer_buffer_seconds':1}))[0],422)
        body={'expected_version':1,'transfer_buffer_seconds':1}
        self.assertEqual((await self.change(body,csrf=False))[0],403)
        self.assertEqual((await self.change(body,cookie=False))[0],401)
        with database() as c:c.execute("UPDATE auth_sessions SET idle_expires_at=now()-interval '1 second'")
        self.assertEqual((await self.change(body))[0],401)

    async def test_owner_isolation_and_two_sessions_compete_for_one_version(self):
        registered=await self.signup_login();owner=registered[2]['data']['user_id'];first_cookie,first_csrf=self.cookie,self.csrf
        self.cookie=None;self.csrf=None;await self.prepare()
        login=await self.call('/auth/login',{'email':'member@example.invalid','password':PASSWORD})
        self.cookie=login[1][b'set-cookie'].decode().split(';')[0];self.csrf=login[2]['data']['csrf_token']
        results=await asyncio.gather(self.change({'expected_version':1,'first_boarding_buffer_seconds':60},cookie=first_cookie,csrf=first_csrf),self.change({'expected_version':1,'transfer_buffer_seconds':90}))
        self.assertEqual(sorted(r[0] for r in results),[200,409])
        with database() as c:self.assertEqual(c.execute('SELECT version FROM user_profiles WHERE user_id=%s',(owner,)).fetchone()['version'],2)
        self.cookie=None;self.csrf=None;await self.prepare();await self.call('/auth/register',self.credentials('second@example.invalid'))
        login=await self.call('/auth/login',{'email':'second@example.invalid','password':PASSWORD})
        self.cookie=login[1][b'set-cookie'].decode().split(';')[0];self.csrf=login[2]['data']['csrf_token']
        self.assertEqual((await self.change({'expected_version':1,'first_boarding_buffer_seconds':15}))[0],200)
        with database() as c:self.assertNotEqual(c.execute('SELECT first_boarding_buffer_seconds FROM user_profiles WHERE user_id=%s',(owner,)).fetchone()['first_boarding_buffer_seconds'],15)

    async def test_recalculation_failure_rolls_back_settings(self):
        await self.signup_login()
        with patch.object(profile_service,'recalculate',side_effect=AuthError(503,'SERVICE_UNAVAILABLE','잠시 후 다시 확인해주세요.')):
            self.assertEqual((await self.change({'expected_version':1,'first_boarding_buffer_seconds':600}))[0],503)
        p=(await self.call('/me'))[2]['data']['profile'];self.assertEqual(p['version'],1);self.assertEqual(p['first_boarding_buffer_seconds'],300)

    async def test_saved_buffers_refresh_guidance_and_walk_revision_without_provider_calls(self):
        await self.mapped()
        with patch.object(walk_provider,'fetch',return_value=self.details()),patch.object(ai,'fetch_estimate',side_effect=output):
            self.assertEqual((await self.estimate())[0],200)
        before=(await self.call(self.path(self.accepted)))[2]['data']['departure']
        with patch.object(ai,'fetch_estimate') as model,patch.object(walk_provider,'fetch') as walk:
            changed=await self.change({'expected_version':before['profile_version'],'first_boarding_buffer_seconds':600,'transfer_buffer_seconds':59,'walking_preference':'fast'})
            self.assertEqual(changed[0],200,changed[2])
            after=(await self.call(self.path(self.accepted)))[2]['data']['departure']
            self.assertEqual(after['buffer_seconds'],600);self.assertEqual(after['approach_seconds'],before['approach_seconds'])
            self.assertEqual(after['personal_walk']['profile_version'],changed[2]['data']['profile_version'])
            self.assertLessEqual(after['personal_walk']['expires_at'],before['personal_walk']['expires_at'])
            self.assertEqual(datetime.fromisoformat(after['recommended_departure_at'])-datetime.fromisoformat(before['recommended_departure_at']),timedelta(seconds=-300))
            with database() as c:owner=c.execute('SELECT user_id FROM user_profiles').fetchone()['user_id']
            saved=guidance.settings(owner);self.assertEqual(saved['transfer_buffer'],59)
            checker=connection_tests.ConnectionUnitTests();at,route,dep,_=checker.fixture()
            connected=evaluate(route,dep,saved,at,lambda leg:checker.evidence(at,leg,2000)).transfers[0]
            self.assertEqual(connected.transfer_buffer_seconds,59)
            self.assertEqual(connected.minimum_boarding_at-connected.estimated_alighting_at,timedelta(seconds=connected.transfer_walk_seconds+59))
            model.assert_not_called();walk.assert_not_called()


if __name__=='__main__':unittest.main()
