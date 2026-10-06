"""Real PostgreSQL/ASGI auth checks in owned temporary schemas only."""
import asyncio
import json
import os
from pathlib import Path
import sys
import unittest
from unittest.mock import patch
from uuid import uuid4

from alembic import command
from alembic.config import Config
from psycopg import sql
from sqlalchemy import create_engine, pool, text

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from app import auth
from app.database import connect_db
from test_api_contract import request

PASSWORD = 'Sample passphrase for testing 29!'


class AuthTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.schema = 'auth_test_' + uuid4().hex
        with connect_db() as connection:
            connection.execute(sql.SQL('CREATE SCHEMA {}').format(sql.Identifier(self.schema)))
        def isolated():
            connection = connect_db()
            connection.execute(sql.SQL('SET search_path TO {}').format(sql.Identifier(self.schema)))
            connection.commit()
            return connection
        engine = create_engine('postgresql+psycopg://', creator=isolated, poolclass=pool.NullPool)
        try:
            with engine.connect() as connection:
                config = Config(str(Path(__file__).resolve().parents[2] / 'alembic.ini'))
                config.attributes['connection'] = connection
                command.upgrade(config, 'head')
        finally:
            engine.dispose()
        self.db_patch = patch.object(auth, 'connect_db', isolated)
        self.db_patch.start()
        self.env_patch = patch.dict(os.environ, {'AUTH_RATE_LIMIT_SECRET':'synthetic-secret-for-testing-32-characters',
                                     'AUTH_ENV':'development', 'AUTH_PUBLIC_ORIGIN':'http://127.0.0.1:5173'})
        self.env_patch.start()
        self.cookie = None
        self.csrf = None

    def tearDown(self):
        self.db_patch.stop()
        self.env_patch.stop()
        with connect_db() as connection:
            connection.execute(sql.SQL('DROP SCHEMA {} CASCADE').format(sql.Identifier(self.schema)))

    async def call(self, path, body=None, origin='http://127.0.0.1:5173', csrf=True):
        headers = [(b'origin', origin.encode()), (b'content-type', b'application/json')]
        if self.cookie: headers.append((b'cookie', self.cookie.encode()))
        if csrf and self.csrf: headers.append((b'x-csrf-token', self.csrf.encode()))
        result = await request('/api/v1' + path, 'POST' if body is not None else 'GET',
                               headers=headers, body=json.dumps(body).encode() if body is not None else b'')
        if result[2]:
            self.assertEqual(result[1][b'x-request-id'].decode(), result[2]['meta']['request_id'])
        return result

    async def prepare(self):
        status, headers, body = await self.call('/auth/csrf')
        self.assertEqual(status, 200)
        self.cookie = headers[b'set-cookie'].decode().split(';')[0]
        self.csrf = body['data']['csrf_token']
        self.assertIn('HttpOnly', headers[b'set-cookie'].decode())
        self.assertEqual(headers[b'cache-control'], b'no-store')

    def credentials(self, email='Member@example.invalid'):
        return {'email':email, 'password':PASSWORD, 'display_name':'테스트 회원'}

    async def signup_login(self):
        await self.prepare()
        registered = await self.call('/auth/register', self.credentials())
        self.assertEqual(registered[0], 201)
        logged_in = await self.call('/auth/login', {'email':'member@example.invalid', 'password':PASSWORD})
        self.assertEqual(logged_in[0], 200)
        old = self.cookie
        self.cookie = logged_in[1][b'set-cookie'].decode().split(';')[0]
        self.csrf = logged_in[2]['data']['csrf_token']
        self.assertNotEqual(old, self.cookie)
        return registered

    async def test_signup_login_me_logout_and_storage(self):
        registered = await self.signup_login()
        self.assertEqual(set(registered[2]['data']), {'user_id'})
        status, _, body = await self.call('/me')
        self.assertEqual(status, 200)
        self.assertEqual(body['data']['display_name'], '테스트 회원')
        self.assertEqual(body['data']['profile']['first_boarding_buffer_seconds'], 300)
        self.assertEqual(body['data']['profile']['transfer_buffer_seconds'], 120)
        self.assertNotIn('email_verified', body['data'])
        with auth.database() as connection:
            cred = connection.execute('SELECT * FROM auth_credentials').fetchone()
            self.assertEqual(cred['email_normalized'], 'member@example.invalid')
            self.assertTrue(cred['password_hash'].startswith('$argon2id$'))
            session = connection.execute('SELECT * FROM auth_sessions').fetchone()
            self.assertNotIn(self.csrf, str(session))
            self.assertNotIn(self.cookie.split('=')[1], str(session))
        self.assertEqual((await self.call('/auth/logout', {}))[0], 204)
        self.assertEqual((await self.call('/me'))[0], 401)

    async def test_duplicate_is_case_normalized_and_atomic(self):
        await self.prepare()
        first = await self.call('/auth/register', self.credentials())
        duplicate = await self.call('/auth/register', self.credentials('  MEMBER@EXAMPLE.INVALID  '))
        self.assertEqual(first[0], 201)
        self.assertEqual(duplicate[0], 409)
        self.assertEqual(duplicate[2]['error']['code'], 'EMAIL_UNAVAILABLE')
        with auth.database() as connection:
            for table in ('users','auth_credentials','user_profiles'):
                self.assertEqual(connection.execute(f'SELECT count(*) AS n FROM {table}').fetchone()['n'], 1)

    async def test_concurrent_signup_unique(self):
        await self.prepare()
        results = await asyncio.gather(self.call('/auth/register', self.credentials()),
                                       self.call('/auth/register', self.credentials()))
        self.assertEqual(sorted(r[0] for r in results), [201,409])

    async def test_csrf_and_origin_required(self):
        await self.prepare()
        self.assertEqual((await self.call('/auth/register', self.credentials(), csrf=False))[0], 403)
        self.assertEqual((await self.call('/auth/register', self.credentials(), origin='https://foreign.invalid'))[0], 403)
        self.assertEqual((await self.call('/auth/register', self.credentials()))[0], 201)

    async def test_wrong_and_missing_member_are_same_and_rate_limited(self):
        await self.prepare()
        await self.call('/auth/register', self.credentials())
        wrong = await self.call('/auth/login', {'email':'member@example.invalid','password':'A different test password!'} )
        missing = await self.call('/auth/login', {'email':'missing@example.invalid','password':PASSWORD})
        self.assertEqual(wrong[0], 401)
        self.assertEqual(wrong[2]['error'], missing[2]['error'])
        for _ in range(4):
            self.assertEqual((await self.call('/auth/login', {'email':'member@example.invalid','password':'A different test password!'}))[0],401)
        limited = await self.call('/auth/login', {'email':'member@example.invalid','password':PASSWORD})
        self.assertEqual(limited[0],429)
        self.assertGreater(int(limited[1][b'retry-after']),0)

    async def test_session_expiry_and_rotation(self):
        await self.signup_login()
        with auth.database() as connection:
            connection.execute("UPDATE auth_sessions SET idle_expires_at=now()-interval '1 second'")
        expired = await self.call('/me')
        self.assertEqual(expired[0],401)
        self.assertEqual(expired[2]['error']['code'],'SESSION_EXPIRED')

    async def test_authenticated_csrf_refresh_and_logout(self):
        await self.signup_login()
        previous = self.csrf
        refreshed = await self.call('/auth/csrf')
        self.assertEqual(refreshed[0],200)
        self.assertIn(b'set-cookie',refreshed[1])
        self.assertEqual((await self.call('/auth/logout', {}))[0],403)
        self.csrf = refreshed[2]['data']['csrf_token']
        self.assertNotEqual(previous,self.csrf)
        self.assertEqual((await self.call('/auth/logout',{}))[0],204)

    async def test_invalid_inputs_and_registration_has_no_login(self):
        await self.prepare()
        for change in ({'password':'short'}, {'email':'bad@@invalid'}, {'display_name':'  '}):
            bad = {**self.credentials(), **change}
            result = await self.call('/auth/register', bad)
            self.assertEqual(result[0],422)
            self.assertNotIn(PASSWORD, json.dumps(result[2]))
        self.assertEqual((await self.call('/auth/register', self.credentials()))[0],201)
        self.assertEqual((await self.call('/me'))[0],401)

    async def test_registration_rate_limit(self):
        await self.prepare()
        for i in range(5):
            self.assertEqual((await self.call('/auth/register', self.credentials(f'test{i}@example.invalid')))[0],201)
        self.assertEqual((await self.call('/auth/register', self.credentials('next@example.invalid')))[0],429)

    async def test_production_settings_and_cookie(self):
        with patch.dict(os.environ,{'AUTH_ENV':'production','AUTH_PUBLIC_ORIGIN':'http://public.invalid'}):
            self.assertEqual((await self.call('/auth/csrf'))[0],503)
        with patch.dict(os.environ,{'AUTH_ENV':'production','AUTH_PUBLIC_ORIGIN':'https://public.invalid'}):
            result = await self.call('/auth/csrf')
            self.assertEqual(result[0],200)
            self.assertIn('__Host-timeisnow_session=', result[1][b'set-cookie'].decode())
            self.assertIn('Secure', result[1][b'set-cookie'].decode())

    async def test_database_failure_is_safe(self):
        from psycopg import OperationalError
        with patch.object(auth, 'connect_db', side_effect=OperationalError('private-db-secret')):
            result = await self.call('/auth/csrf')
        self.assertEqual(result[0],503)
        self.assertNotIn('private-db-secret',json.dumps(result[2]))

    async def test_old_session_is_invalid_and_members_are_separate(self):
        await self.prepare()
        anonymous = self.cookie
        await self.call('/auth/register',self.credentials())
        logged = await self.call('/auth/login',{'email':'member@example.invalid','password':PASSWORD})
        valid_cookie = logged[1][b'set-cookie'].decode().split(';')[0]
        self.cookie = anonymous
        self.assertEqual((await self.call('/me'))[0],401)
        self.cookie = valid_cookie
        first = (await self.call('/me'))[2]['data']['user_id']
        self.cookie = None
        await self.prepare()
        second = await self.call('/auth/register',self.credentials('second@example.invalid'))
        logged = await self.call('/auth/login',{'email':'second@example.invalid','password':PASSWORD})
        self.cookie = logged[1][b'set-cookie'].decode().split(';')[0]
        current = (await self.call('/me'))[2]['data']['user_id']
        self.assertEqual(current,second[2]['data']['user_id'])
        self.assertNotEqual(first,current)

    async def test_password_spaces_are_not_trimmed(self):
        await self.prepare()
        credentials = {**self.credentials(), 'password':'  spaced test passphrase  '}
        self.assertEqual((await self.call('/auth/register',credentials))[0],201)
        self.assertEqual((await self.call('/auth/login',{'email':credentials['email'],'password':credentials['password'].strip()}))[0],401)
        self.assertEqual((await self.call('/auth/login',{'email':credentials['email'],'password':credentials['password']}))[0],200)
