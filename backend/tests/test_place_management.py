import asyncio
import io
import json
import logging
import unittest
from uuid import uuid4
from unittest.mock import patch

import test_place_map_pin
from app import auth, places
from test_api_contract import request


class ManagementTests(unittest.IsolatedAsyncioTestCase):
    setUp = test_place_map_pin.PinTests.setUp
    tearDown = test_place_map_pin.PinTests.tearDown
    call = test_place_map_pin.PinTests.call
    prepare = test_place_map_pin.PinTests.prepare
    credentials = test_place_map_pin.PinTests.credentials
    signup_login = test_place_map_pin.PinTests.signup_login
    saved = test_place_map_pin.PinTests.saved
    create = test_place_map_pin.PinTests.create
    update = test_place_map_pin.PinTests.update
    confirmation = test_place_map_pin.PinTests.confirmation

    async def delete(self, place_id, csrf=True):
        headers=[(b'origin',b'http://127.0.0.1:5173')]
        if self.cookie:headers.append((b'cookie',self.cookie.encode()))
        if csrf and self.csrf:headers.append((b'x-csrf-token',self.csrf.encode()))
        return await request('/api/v1/places/' + place_id, 'DELETE',headers=headers)

    async def test_rename_keeps_location_basis_and_same_name_is_noop(self):
        await self.signup_login();_, saved=await self.saved()
        original=saved[2]['data'];place_id=original['place_id']
        with patch.object(places,'region_for_location') as provider:
            changed=await self.update(place_id,{'expected_version':1,'label':' 새 집 '})
            provider.assert_not_called()
        self.assertEqual(changed[0],200)
        data=changed[2]['data'];self.assertEqual(data['label'],'새 집')
        self.assertEqual(data['version'],2);self.assertEqual(data['location_version'],1)
        for field in ('location','address','name','entrance_note','location_source'):
            self.assertEqual(data[field],original[field])
        same=await self.update(place_id,{'expected_version':2,'label':'새 집'})
        self.assertEqual(same[2]['data']['version'],2)
        self.assertEqual((await self.update(place_id,{'expected_version':1,'label':'낡은 화면'}))[0],409)
        self.assertEqual((await self.call('/places'))[2]['data']['items'][0]['label'],'새 집')

    async def test_label_and_location_change_increment_their_versions(self):
        await self.signup_login();_, saved=await self.saved();confirmed=await self.confirmation()
        data=(await self.update(saved[2]['data']['place_id'],{'expected_version':1,'label':'회사',
            'location':confirmed['location'],'location_confirmation_id':confirmed['confirmation_id']}))[2]['data']
        self.assertEqual((data['version'],data['location_version']),(2,2))
        data=(await self.update(data['place_id'],{'expected_version':2,'label':'새 회사'}))[2]['data']
        self.assertEqual((data['version'],data['location_version']),(3,2))

    async def test_invalid_labels_and_csrf(self):
        await self.signup_login();_, saved=await self.saved();place_id=saved[2]['data']['place_id']
        for label in (None,'',' ','a'*31):
            response=await self.update(place_id,{'expected_version':1,'label':label})
            self.assertEqual(response[0],422);self.assertEqual(response[1][b'cache-control'],b'no-store')
        self.assertEqual((await self.update(place_id,{'expected_version':1,'label':'집2'},csrf=False))[0],403)
        self.assertEqual((await self.delete(place_id,csrf=False))[0],403)
        self.assertEqual((await self.call('/places/' + place_id))[0],200)

    async def test_delete_hides_detail_list_patch_and_repeat(self):
        await self.signup_login();_, saved=await self.saved();place_id=saved[2]['data']['place_id']
        deleted=await self.delete(place_id)
        self.assertEqual(deleted[0],204);self.assertIsNone(deleted[2])
        self.assertIn(b'x-request-id',deleted[1]);self.assertEqual(deleted[1][b'cache-control'],b'no-store')
        self.assertEqual((await self.call('/places'))[2]['data']['items'],[])
        self.assertEqual((await self.call('/places/' + place_id))[0],404)
        self.assertEqual((await self.update(place_id,{'expected_version':1,'label':'집2'}))[0],404)
        self.assertEqual((await self.delete(place_id))[0],404)
        with auth.database() as connection:
            self.assertEqual(connection.execute('SELECT count(*) AS n FROM saved_places').fetchone()['n'],0)

    async def test_deleted_create_key_does_not_resurrect_place(self):
        await self.signup_login();body,saved=await self.saved(key='saved-key');await self.delete(saved[2]['data']['place_id'])
        self.assertEqual((await self.create(body,'saved-key'))[0],404)
        self.assertEqual((await self.create({**body,'label':'회사'},'saved-key'))[0],409)
        with auth.database() as connection:
            key=connection.execute('SELECT * FROM place_creation_keys').fetchone()
            self.assertIsNone(key['place_id']);self.assertEqual(key['key'],'saved-key')
        self.assertEqual((await self.create(body,'new-explicit-key'))[0],201)

    async def test_delete_cannot_change_other_user_places_or_keys(self):
        await self.signup_login();_,saved=await self.saved(key='saved-key');place_id=saved[2]['data']['place_id']
        with auth.database() as connection:
            other=uuid4();connection.execute('INSERT INTO users(id,display_name) VALUES(%s,%s)',(other,'다른 합성 회원'))
            connection.execute('UPDATE auth_sessions SET user_id=%s WHERE token_hash=%s',(other,auth.digest(self.cookie.split('=')[1])))
        self.assertEqual((await self.delete(place_id))[0],404)
        self.assertEqual((await self.update(place_id,{'expected_version':1,'label':'다른 집'}))[0],404)
        with auth.database() as connection:
            self.assertEqual(connection.execute('SELECT label FROM saved_places').fetchone()['label'],'집')
            self.assertIsNotNone(connection.execute('SELECT place_id FROM place_creation_keys').fetchone()['place_id'])

    async def test_auth_bad_ids_and_concurrent_delete(self):
        self.assertEqual((await self.delete(str(uuid4())))[0],401)
        await self.signup_login();_,saved=await self.saved();place_id=saved[2]['data']['place_id']
        self.assertEqual((await self.delete('bad-id'))[0],404)
        first,second=await asyncio.gather(self.delete(place_id),self.delete(place_id))
        self.assertEqual(sorted([first[0],second[0]]),[204,404])

    async def test_concurrent_patch_delete_and_deleted_cursor(self):
        await self.signup_login();_,saved=await self.saved();place_id=saved[2]['data']['place_id']
        updated,deleted=await asyncio.gather(self.update(place_id,{'expected_version':1,'label':'새 이름'}),self.delete(place_id))
        self.assertIn(updated[0],(200,404));self.assertEqual(deleted[0],204)
        self.assertEqual((await self.call('/places/' + place_id))[0],404)
        self.assertEqual((await self.call('/places?cursor=' + place_id))[0],404)

    async def test_delete_does_not_clear_other_places_or_independent_searches(self):
        await self.signup_login();_,first=await self.saved(key='first-key');_,second=await self.saved(key='second-key')
        await self.confirmation();await self.delete(first[2]['data']['place_id'])
        self.assertEqual((await self.call('/places'))[2]['data']['items'],[second[2]['data']])
        with auth.database() as connection:
            self.assertEqual(connection.execute('SELECT count(*) AS n FROM place_searches').fetchone()['n'],2)
            self.assertEqual(connection.execute('SELECT count(*) AS n FROM place_location_confirmations').fetchone()['n'],1)

    async def test_rename_delete_logs_have_no_private_data(self):
        from app.request_logging import logger,RequestJsonFormatter,RequestEventFilter
        await self.signup_login();_,saved=await self.saved()
        output=io.StringIO();handler=logging.StreamHandler(output)
        handler.setFormatter(RequestJsonFormatter());handler.addFilter(RequestEventFilter())
        original_handlers,original_level=logger.handlers[:],logger.level
        logger.handlers[:]=[handler];logger.setLevel(logging.INFO)
        try:
            updated=await self.update(saved[2]['data']['place_id'],{'expected_version':1,'label':'private label'})
            deleted=await self.delete(saved[2]['data']['place_id'])
        finally:
            logger.handlers[:]=original_handlers;logger.setLevel(original_level)
        logs=output.getvalue()
        self.assertNotIn('private label',logs);self.assertNotIn(saved[2]['data']['place_id'],logs)
        entries=[json.loads(line) for line in logs.splitlines()]
        self.assertEqual([entry['status_code'] for entry in entries],[200,204])
        self.assertEqual(entries[0]['request_id'],updated[2]['meta']['request_id'])
        self.assertEqual(entries[1]['request_id'],deleted[1][b'x-request-id'].decode())
