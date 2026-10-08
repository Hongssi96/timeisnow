import React from 'react';
import { afterEach, expect, it, vi } from 'vitest';
import { act, fireEvent, render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import OriginSelector from '../../src/components/OriginSelector';
import { apiRequest, ApiError } from '../../src/lib/api';
import { getCurrentOrigin } from '../../src/lib/currentOrigin';
vi.mock('../../src/lib/api', async original => ({...await original(),apiRequest:vi.fn()}));
vi.mock('../../src/lib/currentOrigin',()=>({getCurrentOrigin:vi.fn()}));
vi.mock('../../src/components/MapPinPicker',()=>({default:({onChange,disabled,onReady})=>{React.useEffect(()=>{onReady?.(true);},[onReady]);return <button disabled={disabled} onClick={()=>onChange({latitude:37.6,longitude:127})}>검증용 지도 선택</button>;}}));
afterEach(()=>{vi.resetAllMocks();vi.useRealTimers();});
const reply=data=>({data,meta:{server_time:new Date().toISOString()}});
const place={place_id:'p_test',label:'검증 집',location:{latitude:37.5,longitude:127},location_version:1,address:'서울 합성 주소'};
it('opens saved-place recovery directly without requesting GPS',async()=>{
  const selected=vi.fn();
  apiRequest.mockResolvedValueOnce(reply({items:[place],next_cursor:null}));
  render(<OriginSelector initialMode="saved" onSelect={selected}/>);
  const button=await screen.findByRole('button',{name:/검증 집/});
  expect(screen.queryByRole('button',{name:'현재 위치 확인'})).toBeNull();
  expect(screen.getByRole('button',{name:'저장 장소'}).getAttribute('aria-pressed')).toBe('true');
  apiRequest.mockResolvedValueOnce(reply({csrf_token:'csrf_test'})).mockResolvedValueOnce(result({type:'saved_place',place_id:place.place_id,location_version:1}));
  await userEvent.click(button);
  await waitFor(()=>expect(selected).toHaveBeenCalledOnce());
  expect(selected.mock.calls[0][0].origin.type).toBe('saved_place');
  expect(getCurrentOrigin).not.toHaveBeenCalled();
});
const current={type:'current_location',latitude:37.51,longitude:127.01,accuracy_meters:12,captured_at:'2026-10-07T01:00:00.000Z'};
function result(origin){const current=origin.type==='current_location';return reply({origin:current?{...origin,location_confirmed:Boolean(origin.location_confirmed)}:origin,label:'검증 출발',location:{latitude:37.51,longitude:127.01},location_address:'서울 합성동',quality_status:current?(origin.location_confirmed?'user_confirmed':'pending'):'not_applicable',quality:{assessment:current?'unassessed':'user_selected',confirmation:current?(origin.location_confirmed?'reported':'required'):'not_applicable',numeric_policy:'deferred',time_relation:current?'past_or_present':'not_applicable'},place_match:{status:origin.type==='saved_place'?'selected_by_user':'unconfirmed'},expires_at:new Date(Date.now()+599000).toISOString()});}
async function open(props={}) {
  apiRequest.mockResolvedValueOnce(reply({items:[place],next_cursor:null}));
  const view=render(<OriginSelector onSelect={vi.fn()} {...props}/>);
  await waitFor(()=>expect(screen.getByRole('button',{name:'현재 위치 확인'}).disabled).toBe(false));
  return {user:userEvent.setup(),...view};
}
it('does not request GPS on mount, validates measured data only after click',async()=>{
  const selected=vi.fn();const {user}=await open({onSelect:selected});expect(getCurrentOrigin).not.toHaveBeenCalled();
  getCurrentOrigin.mockResolvedValue(current);apiRequest.mockResolvedValueOnce(reply({})).mockResolvedValueOnce(reply({csrf_token:'csrf_test'})).mockResolvedValueOnce(result(current));
  await user.click(screen.getByRole('button',{name:'현재 위치 확인'}));await screen.findByRole('button',{name:'이 위치가 실제 출발 위치예요'});
  expect(selected).not.toHaveBeenCalled();
  apiRequest.mockResolvedValueOnce(reply({csrf_token:'csrf_test'})).mockResolvedValueOnce(result({...current,location_confirmed:true}));
  await user.click(screen.getByRole('button',{name:'이 위치가 실제 출발 위치예요'}));await waitFor(()=>expect(selected).toHaveBeenCalledOnce());
  expect(apiRequest.mock.calls.filter(([path])=>path==='/api/v1/origin-validations')[1][1].body.origin.location_confirmed).toBe(true);
  const call=apiRequest.mock.calls.find(([path])=>path==='/api/v1/origin-validations');expect(call[1].body).toEqual({origin:current});
  expect(call[1].headers['X-CSRF-Token']).toBe('csrf_test');
});
it('pin movement discards GPS review and becomes an explicit map selection',async()=>{
  const selected=vi.fn();const {user}=await open({onSelect:selected});
  getCurrentOrigin.mockResolvedValue(current);apiRequest.mockResolvedValueOnce(reply({})).mockResolvedValueOnce(reply({csrf_token:'csrf'})).mockResolvedValueOnce(result(current));
  await user.click(screen.getByRole('button',{name:'현재 위치 확인'}));await screen.findByRole('button',{name:'이 위치가 실제 출발 위치예요'});
  await user.click(screen.getByRole('button',{name:'검증용 지도 선택'}));
  expect(screen.queryByRole('button',{name:'이 위치가 실제 출발 위치예요'})).toBeNull();
  expect(screen.getByRole('button',{name:'이 위치에서 출발'}).disabled).toBe(false);expect(selected).not.toHaveBeenCalled();
});
it('confirmation failure keeps the review and never applies the origin',async()=>{
  const selected=vi.fn();const {user}=await open({onSelect:selected});
  getCurrentOrigin.mockResolvedValue(current);apiRequest.mockResolvedValueOnce(reply({})).mockResolvedValueOnce(reply({csrf_token:'csrf'})).mockResolvedValueOnce(result(current));
  await user.click(screen.getByRole('button',{name:'현재 위치 확인'}));await screen.findByRole('button',{name:'이 위치가 실제 출발 위치예요'});
  apiRequest.mockResolvedValueOnce(reply({csrf_token:'csrf'})).mockRejectedValueOnce(new ApiError('PROVIDER_UNAVAILABLE'));
  await user.click(screen.getByRole('button',{name:'이 위치가 실제 출발 위치예요'}));await screen.findByRole('alert');
  expect(selected).not.toHaveBeenCalled();expect(getCurrentOrigin).toHaveBeenCalledOnce();
});
it('unconfirmed or malformed quality responses cannot pass confirmation',async()=>{
  const selected=vi.fn();const {user}=await open({onSelect:selected});
  getCurrentOrigin.mockResolvedValue(current);apiRequest.mockResolvedValueOnce(reply({})).mockResolvedValueOnce(reply({csrf_token:'csrf'})).mockResolvedValueOnce(result(current));
  await user.click(screen.getByRole('button',{name:'현재 위치 확인'}));await screen.findByRole('button',{name:'이 위치가 실제 출발 위치예요'});
  apiRequest.mockResolvedValueOnce(reply({csrf_token:'csrf'})).mockResolvedValueOnce(result(current));
  await user.click(screen.getByRole('button',{name:'이 위치가 실제 출발 위치예요'}));await screen.findByRole('alert');expect(selected).not.toHaveBeenCalled();
});
it('review expiry requires a new measurement without requesting GPS automatically',async()=>{
  const selected=vi.fn();const {user}=await open({onSelect:selected});
  const response=result(current);response.data.expires_at=new Date(Date.parse(response.meta.server_time)+80).toISOString();
  getCurrentOrigin.mockResolvedValue(current);apiRequest.mockResolvedValueOnce(reply({})).mockResolvedValueOnce(reply({csrf_token:'csrf'})).mockResolvedValueOnce(response);
  await user.click(screen.getByRole('button',{name:'현재 위치 확인'}));
  await waitFor(()=>expect(screen.queryByRole('button',{name:'이 위치가 실제 출발 위치예요'})).toBeNull());
  expect((await screen.findByRole('alert')).textContent).toContain('만료');
  expect(selected).not.toHaveBeenCalled();expect(getCurrentOrigin).toHaveBeenCalledOnce();
});
it('expiry aborts an in-flight confirmation and ignores its late success',async()=>{
  const selected=vi.fn();await open({onSelect:selected});vi.useFakeTimers();
  getCurrentOrigin.mockResolvedValue(current);apiRequest.mockResolvedValueOnce(reply({})).mockResolvedValueOnce(reply({csrf_token:'csrf'})).mockResolvedValueOnce(result(current));
  await act(async()=>fireEvent.click(screen.getByRole('button',{name:'현재 위치 확인'})));
  let resolve;apiRequest.mockResolvedValueOnce(reply({csrf_token:'csrf'})).mockImplementationOnce(()=>new Promise(done=>{resolve=done;}));
  await act(async()=>fireEvent.click(screen.getByRole('button',{name:'이 위치가 실제 출발 위치예요'})));
  const signal=apiRequest.mock.calls.filter(([path])=>path==='/api/v1/origin-validations')[1][1].signal;
  await act(()=>vi.advanceTimersByTimeAsync(600000));expect(signal.aborted).toBe(true);
  await act(async()=>resolve(result({...current,location_confirmed:true})));
  expect(selected).not.toHaveBeenCalled();expect(screen.queryByRole('button',{name:'이 위치가 실제 출발 위치예요'})).toBeNull();
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
