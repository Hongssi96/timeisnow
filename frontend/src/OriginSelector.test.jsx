import React from 'react';
import { afterEach, expect, it, vi } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import OriginSelector from './OriginSelector';
import { apiRequest, ApiError } from './api';
import { getCurrentOrigin } from './currentOrigin';
vi.mock('./api', async original => ({...await original(),apiRequest:vi.fn()}));
vi.mock('./currentOrigin',()=>({getCurrentOrigin:vi.fn()}));
vi.mock('./MapPinPicker',()=>({default:({onChange,disabled})=><button disabled={disabled} onClick={()=>onChange({latitude:37.6,longitude:127})}>검증용 지도 선택</button>}));
afterEach(()=>vi.resetAllMocks());
const reply=data=>({data,meta:{server_time:new Date().toISOString()}});
const place={place_id:'p_test',label:'검증 집',location:{latitude:37.5,longitude:127},location_version:1,address:'서울 합성 주소'};
const current={type:'current_location',latitude:37.51,longitude:127.01,accuracy_meters:12,captured_at:'2026-10-07T01:00:00.000Z'};
function result(origin){return reply({origin,label:'검증 출발',location:{latitude:37.51,longitude:127.01},location_address:'서울 합성동',quality_status:origin.type==='current_location'?'pending':'not_applicable',expires_at:new Date(Date.now()+599000).toISOString()});}
async function open(props={}) {
  apiRequest.mockResolvedValueOnce(reply({items:[place],next_cursor:null}));
  const view=render(<OriginSelector onSelect={vi.fn()} {...props}/>);
  await waitFor(()=>expect(screen.getByRole('button',{name:'현재 위치 확인'}).disabled).toBe(false));
  return {user:userEvent.setup(),...view};
}
it('does not request GPS on mount, validates measured data only after click',async()=>{
  const selected=vi.fn();const {user}=await open({onSelect:selected});expect(getCurrentOrigin).not.toHaveBeenCalled();
  getCurrentOrigin.mockResolvedValue(current);apiRequest.mockResolvedValueOnce(reply({})).mockResolvedValueOnce(reply({csrf_token:'csrf_test'})).mockResolvedValueOnce(result(current));
  await user.click(screen.getByRole('button',{name:'현재 위치 확인'}));await waitFor(()=>expect(selected).toHaveBeenCalledOnce());
  const call=apiRequest.mock.calls.find(([path])=>path==='/api/v1/origin-validations');expect(call[1].body).toEqual({origin:current});
  expect(call[1].headers['X-CSRF-Token']).toBe('csrf_test');
});
it('denial opens map but never validates initial center',async()=>{
  const selected=vi.fn();const {user}=await open({onSelect:selected});apiRequest.mockResolvedValueOnce(reply({}));
  getCurrentOrigin.mockRejectedValue(Object.assign(new Error('위치 권한이 허용되지 않았어요.'),{code:'GEO_DENIED'}));
  await user.click(screen.getByRole('button',{name:'현재 위치 확인'}));expect((await screen.findByRole('alert')).textContent).toContain('권한');
  expect(screen.getByRole('button',{name:'이 위치에서 출발'}).disabled).toBe(true);
  await user.click(screen.getByRole('button',{name:'검증용 지도 선택'}));
  const origin={type:'map_pin',latitude:37.6,longitude:127};apiRequest.mockResolvedValueOnce(reply({csrf_token:'csrf'})).mockResolvedValueOnce(result(origin));
  await user.click(screen.getByRole('button',{name:'이 위치에서 출발'}));await waitFor(()=>expect(selected).toHaveBeenCalledOnce());
});
it('rechecks login before obtaining any GPS and removes private list on expiry',async()=>{
  const auth=vi.fn();const {user}=await open({onAuthError:auth});apiRequest.mockRejectedValueOnce(new ApiError('SESSION_EXPIRED'));
  await user.click(screen.getByRole('button',{name:'현재 위치 확인'}));await screen.findByRole('button',{name:'로그인하기'});
  expect(getCurrentOrigin).not.toHaveBeenCalled();expect(auth).toHaveBeenCalledOnce();expect(screen.queryByText('검증 집')).toBeNull();
});
it('saved place selection sends physical version; conflict requires fresh list',async()=>{
  const {user}=await open();await user.click(screen.getByRole('button',{name:'저장 장소'}));
  apiRequest.mockResolvedValueOnce(reply({csrf_token:'csrf'})).mockRejectedValueOnce(new ApiError('VERSION_CONFLICT'));
  await user.click(screen.getByRole('button',{name:/검증 집/}));await screen.findByRole('alert');
  expect(screen.queryByText('검증 집')).toBeNull();expect(getCurrentOrigin).not.toHaveBeenCalled();
  const call=apiRequest.mock.calls.find(([path])=>path==='/api/v1/origin-validations');expect(call[1].body.origin).toEqual({type:'saved_place',place_id:'p_test',location_version:1});
});
it('method change and unmount abort GPS and ignore late results',async()=>{
  const selected=vi.fn();const {user,unmount}=await open({onSelect:selected});apiRequest.mockResolvedValueOnce(reply({}));
  let resolve;getCurrentOrigin.mockImplementation(()=>new Promise(done=>{resolve=done;}));
  await user.click(screen.getByRole('button',{name:'현재 위치 확인'}));await waitFor(()=>expect(getCurrentOrigin).toHaveBeenCalledOnce());
  const signal=getCurrentOrigin.mock.calls[0][0];await user.click(screen.getByRole('button',{name:'지도 선택'}));expect(signal.aborted).toBe(true);
  resolve(current);await waitFor(()=>expect(screen.getByRole('button',{name:'이 위치에서 출발'}).disabled).toBe(true));
  expect(apiRequest.mock.calls.some(([path])=>path==='/api/v1/origin-validations')).toBe(false);expect(selected).not.toHaveBeenCalled();unmount();
});
