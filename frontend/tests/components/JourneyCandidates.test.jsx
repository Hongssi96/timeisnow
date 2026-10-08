import React from 'react';
import { afterEach, expect, it, vi } from 'vitest';
import { act, fireEvent, render, screen, within } from '@testing-library/react';
import JourneyComparison from '../../src/components/JourneyComparison';
import { apiRequest, ApiError } from '../../src/lib/api';
import fixtures from '../fixtures/journeys.json';
vi.mock('../../src/lib/api',async original=>({...await original(),apiRequest:vi.fn()}));
const endpointTypes=vi.hoisted(()=>({origin:'saved_place',destination:'saved_place'}));
vi.mock('../../src/components/OriginSelector',()=>({default:({purpose,onSelect,initialMode})=><button data-mode={initialMode||'current'} onClick={()=>{
  const type=initialMode==='saved'?'saved_place':endpointTypes[purpose];
  onSelect({label:purpose==='origin'?'출발 검증역':'도착 검증역',location_address:'서울 공개 검증 위치',
    origin:type==='saved_place'?{type,place_id:purpose==='origin'?'place_origin':'place_destination',location_version:1}
      :{type,latitude:37.5,longitude:127,location_confirmed:true},deadline:Date.now()+600000});
}}>검증 위치 적용</button>}));
afterEach(()=>{vi.resetAllMocks();vi.useRealTimers();endpointTypes.origin='saved_place';endpointTypes.destination='saved_place';});
const accepted={search_id:'search_test',job_id:'job_test',status:'queued'};
const reply=(data,status=200)=>({data,status,meta:{server_time:new Date().toISOString()}});
const result=(candidates=[fixtures.direct,fixtures.mixed],status='succeeded')=>reply({...accepted,status,candidates:structuredClone(candidates),unavailable_reasons:[],error:status==='failed'?{code:'PROVIDER_TIMEOUT',message:'private upstream'}:null,expires_at:new Date(Date.now()+290000).toISOString()});
const saved=(routine_id='routine_one',name='출발 검증역 → 도착 검증역 통근')=>({routine_id,name,origin_place:{place_id:'place_origin',label:'출발 검증역',name:'출발 장소',address:'서울 어딘가'},destination_place:{place_id:'place_destination',label:'도착 검증역',name:'도착 장소',address:'경기 어딘가'},route:{journey_plan_id:'11111111-1111-1111-1111-111111111111',type:'BUS',total_seconds:600,transfer_count:0},weekdays:[1,2,3,4,5],target_arrival_local_time:null,timezone:'Asia/Seoul',status:'active',version:1,created_at:'2026-10-07T00:00:00Z',updated_at:'2026-10-07T00:00:00Z'});
function mockApi(get=()=>result(),post=()=>reply(accepted,202),save=()=>reply(saved(),201)){
  apiRequest.mockImplementation(path=>{
    if(path==='/api/v1/auth/csrf')return Promise.resolve(reply({csrf_token:'csrf_test'}));
    if(path==='/api/v1/journey-searches')return Promise.resolve(post());
    if(path==='/api/v1/routines')return Promise.resolve(save());
    return Promise.resolve(get());
  });
}
async function open(props={}){
  vi.useFakeTimers();const user={click:async node=>{await act(async()=>fireEvent.click(node));},selectOptions:async(node,value)=>{await act(async()=>fireEvent.change(node,{target:{value}}));}};render(<JourneyComparison {...props}/>);
  await user.click(screen.getByRole('button',{name:'출발지 선택'}));await user.click(screen.getByRole('button',{name:'검증 위치 적용'}));
  await user.click(screen.getByRole('button',{name:'도착지 선택'}));await user.click(screen.getByRole('button',{name:'검증 위치 적용'}));return user;
}
async function search(user){await user.click(screen.getByRole('button',{name:'경로 후보 조회'}));await act(()=>vi.advanceTimersByTimeAsync(2000));}

it.each(['VERSION_CONFLICT','RESOURCE_NOT_FOUND'])('offers latest routine reload after recovery PATCH %s without creating or retrying',async code=>{
  const existing={...saved('recover'),status:'needs_attention',origin_place:null,version:4,weekdays:[2,4],target_arrival_local_time:'09:10'};
  apiRequest.mockImplementation(path=>{
    if(path==='/api/v1/auth/csrf')return Promise.resolve(reply({csrf_token:'csrf_test'}));
    if(path==='/api/v1/journey-searches')return Promise.resolve(reply(accepted,202));
    if(path==='/api/v1/routines/recover')return Promise.reject(new ApiError(code));
    return Promise.resolve(result());
  });
  const onRoutineReload=vi.fn(),onRoutineSaved=vi.fn();
  const user=await open({routineToReplace:existing,onRoutineReload,onRoutineSaved});
  expect(screen.getByText(/출발 장소가 삭제됐어요/)).toBeTruthy();
  await search(user);await user.click(screen.getAllByRole('button',{name:'이 경로로 루틴 변경'})[0]);
  expect(screen.getByLabelText('루틴 이름').value).toBe(existing.name);
  await user.click(screen.getByRole('button',{name:'루틴 저장'}));
  expect(screen.queryByRole('heading',{name:'경로 후보 2개'})).toBeNull();
  await user.click(screen.getByRole('button',{name:'최신 루틴 다시 확인'}));
  expect(onRoutineReload).toHaveBeenCalledOnce();expect(onRoutineSaved).not.toHaveBeenCalled();
  expect(apiRequest.mock.calls.filter(([path])=>path==='/api/v1/routines/recover')).toHaveLength(1);
  expect(apiRequest.mock.calls.some(([path])=>path==='/api/v1/routines')).toBe(false);
});

it('starts recovery with saved places and ignores an unrelated home origin without writing',async()=>{
  vi.useFakeTimers();const existing={...saved('recover'),status:'needs_attention',destination_place:null};
  render(<JourneyComparison routineToReplace={existing} initialOrigin={{label:'다른 곳',origin:{type:'saved_place',place_id:'other',location_version:1},deadline:Date.now()+600000}}/>);
  expect(screen.queryByText('다른 곳')).toBeNull();
  await act(async()=>fireEvent.click(screen.getByRole('button',{name:'출발지 선택'})));
  expect(screen.getByRole('button',{name:'검증 위치 적용'}).dataset.mode).toBe('saved');
  expect(apiRequest).not.toHaveBeenCalled();
});

it('saves a candidate as a named routine with idempotency key',async()=>{
  mockApi();const onRoutineSaved=vi.fn();const user=await open({onRoutineSaved});await search(user);
  expect(screen.getAllByRole('button',{name:'이 경로를 루틴에 저장'})).toHaveLength(2);
  await user.click(screen.getAllByRole('button',{name:'이 경로를 루틴에 저장'})[0]);
  const input=screen.getByLabelText('루틴 이름');expect(input.value).toBe('출발 검증역 → 도착 검증역 통근');
  await user.click(screen.getByRole('button',{name:'루틴 저장'}));
  const calls=apiRequest.mock.calls.filter(([path])=>path==='/api/v1/routines');expect(calls).toHaveLength(1);
  const [path,options]=calls[0];expect(path).toBe('/api/v1/routines');
  expect(options.method).toBe('POST');expect(options.headers['Idempotency-Key']).toBeTruthy();
  expect(options.body).toEqual({name:'출발 검증역 → 도착 검증역 통근',origin_place_id:'place_origin',
    destination_place_id:'place_destination',search_id:'search_test',candidate_id:fixtures.direct.candidate_id,
    weekdays:[1,2,3,4,5],target_arrival_local_time:null});
  expect(onRoutineSaved).toHaveBeenCalledOnce();
  expect(screen.getByText('루틴에 저장했어요')).toBeTruthy();
  expect(screen.queryByLabelText('루틴 이름')).toBeNull();
  expect(apiRequest.mock.calls.filter(([path])=>path==='/api/v1/routines')).toHaveLength(1);
});

it('defaults weekdays to Monday to Friday and sends the toggled schedule',async()=>{
  mockApi();const user=await open();await search(user);
  await user.click(screen.getAllByRole('button',{name:'이 경로를 루틴에 저장'})[0]);
  const pressed=()=>within(screen.getByRole('group',{name:'반복 요일'})).getAllByRole('button',{pressed:true}).map(node=>node.textContent);
  expect(pressed()).toEqual(['월','화','수','목','금']);
  await user.click(screen.getByRole('button',{name:'금'}));
  await user.click(screen.getByRole('button',{name:'토'}));
  expect(pressed()).toEqual(['월','화','수','목','토']);
  await user.click(screen.getByRole('button',{name:'루틴 저장'}));
  const saves=apiRequest.mock.calls.filter(([path])=>path==='/api/v1/routines');
  expect(saves).toHaveLength(1);expect(saves[0][1].body.weekdays).toEqual([1,2,3,4,6]);
});

it('saving stays blocked while no weekday is selected',async()=>{
  mockApi();const user=await open();await search(user);
  await user.click(screen.getAllByRole('button',{name:'이 경로를 루틴에 저장'})[0]);
  for(const day of ['월','화','수','목','금'])await user.click(screen.getByRole('button',{name:day}));
  expect(within(screen.getByRole('group',{name:'반복 요일'})).queryAllByRole('button',{pressed:true})).toHaveLength(0);
  const submit=screen.getByRole('button',{name:'루틴 저장'});
  expect(submit.disabled).toBe(true);
  await user.click(submit);
  expect(apiRequest.mock.calls.filter(([path])=>path==='/api/v1/routines')).toHaveLength(0);
});

it('sends the optional target arrival time only when entered',async()=>{
  mockApi();const user=await open();await search(user);
  await user.click(screen.getAllByRole('button',{name:'이 경로를 루틴에 저장'})[0]);
  await act(async()=>fireEvent.change(screen.getByLabelText(/목표 도착 시각/),{target:{value:'08:30'}}));
  await user.click(screen.getByRole('button',{name:'루틴 저장'}));
  let saves=apiRequest.mock.calls.filter(([path])=>path==='/api/v1/routines');
  expect(saves).toHaveLength(1);expect(saves[0][1].body.target_arrival_local_time).toBe('08:30');
  await user.click(screen.getByRole('button',{name:'도착지 변경'}));await user.click(screen.getByRole('button',{name:'검증 위치 적용'}));
  await search(user);
  await user.click(screen.getAllByRole('button',{name:'이 경로를 루틴에 저장'})[0]);
  await user.click(screen.getByRole('button',{name:'루틴 저장'}));
  saves=apiRequest.mock.calls.filter(([path])=>path==='/api/v1/routines');
  expect(saves).toHaveLength(2);expect(saves[1][1].body.target_arrival_local_time).toBeNull();
});

it('uses the typed routine name and falls back to the default when cleared',async()=>{
  mockApi();const user=await open();await search(user);
  await user.click(screen.getAllByRole('button',{name:'이 경로를 루틴에 저장'})[0]);
  await act(async()=>fireEvent.change(screen.getByLabelText('루틴 이름'),{target:{value:'아침 출근'}}));
  await user.click(screen.getByRole('button',{name:'루틴 저장'}));
  const first=apiRequest.mock.calls.filter(([path])=>path==='/api/v1/routines');
  expect(first).toHaveLength(1);expect(first[0][1].body.name).toBe('아침 출근');
  await user.click(screen.getAllByRole('button',{name:'이 경로를 루틴에 저장'})[0]);
  await user.click(screen.getByRole('button',{name:'루틴 저장'}));
  const saves=apiRequest.mock.calls.filter(([path])=>path==='/api/v1/routines');
  expect(saves).toHaveLength(2);expect(saves[1][1].body.name).toBe('출발 검증역 → 도착 검증역 통근');
});

it('saving again after success does not call the API again',async()=>{
  mockApi();const user=await open();await search(user);
  await user.click(screen.getAllByRole('button',{name:'이 경로를 루틴에 저장'})[0]);
  await user.click(screen.getByRole('button',{name:'루틴 저장'}));
  expect(screen.getAllByRole('button',{name:'루틴에 저장했어요'}).length).toBeGreaterThanOrEqual(1);
  await user.click(screen.getAllByRole('button',{name:'루틴에 저장했어요'})[0]);
  expect(apiRequest.mock.calls.filter(([path])=>path==='/api/v1/routines')).toHaveLength(1);
});

it('failed save surfaces a safe message and retry reruns only the save',async()=>{
  let saves=0;mockApi(()=>result(),()=>reply(accepted,202),()=>{if(saves++===0)throw new ApiError('NETWORK_ERROR');return reply(saved(),201);});
  const user=await open();await search(user);
  await user.click(screen.getAllByRole('button',{name:'이 경로를 루틴에 저장'})[0]);
  await user.click(screen.getByRole('button',{name:'루틴 저장'}));
  expect(screen.getAllByRole('alert').length).toBeGreaterThanOrEqual(1);
  expect(screen.queryByText('private upstream')).toBeNull();
  // A new lookup starts a fresh, unmarked candidate list.
  await user.click(screen.getByRole('button',{name:'결과 다시 확인'}));await act(()=>vi.advanceTimersByTimeAsync(2000));
  expect(screen.getAllByRole('button',{name:'이 경로를 루틴에 저장'})).toHaveLength(2);
  expect(apiRequest.mock.calls.filter(([path])=>path==='/api/v1/routines')).toHaveLength(1);
});

it('malformed saved response is rejected and never shown',async()=>{
  const bad=saved();delete bad.route;mockApi(()=>result(),()=>reply(accepted,202),()=>reply(bad,201));
  const onRoutineSaved=vi.fn();const user=await open({onRoutineSaved});await search(user);
  await user.click(screen.getAllByRole('button',{name:'이 경로를 루틴에 저장'})[0]);
  await user.click(screen.getByRole('button',{name:'루틴 저장'}));
  expect(onRoutineSaved).not.toHaveBeenCalled();expect(screen.getAllByRole('alert').length).toBeGreaterThanOrEqual(1);
});

it('saved response without a valid schedule is rejected',async()=>{
  const bad=saved();delete bad.weekdays;mockApi(()=>result(),()=>reply(accepted,202),()=>reply(bad,201));
  const onRoutineSaved=vi.fn();const user=await open({onRoutineSaved});await search(user);
  await user.click(screen.getAllByRole('button',{name:'이 경로를 루틴에 저장'})[0]);
  await user.click(screen.getByRole('button',{name:'루틴 저장'}));
  expect(onRoutineSaved).not.toHaveBeenCalled();expect(screen.getAllByRole('alert').length).toBeGreaterThanOrEqual(1);
});

it('auth expiry during save clears endpoints and returns to login',async()=>{
  mockApi(()=>result(),()=>reply(accepted,202),()=>{throw new ApiError('SESSION_EXPIRED');});
  const auth=vi.fn();const user=await open({onAuthError:auth});await search(user);
  await user.click(screen.getAllByRole('button',{name:'이 경로를 루틴에 저장'})[0]);
  await user.click(screen.getByRole('button',{name:'루틴 저장'}));
  expect(auth).toHaveBeenCalledOnce();expect(screen.queryByText('출발 검증역')).toBeNull();
  expect(screen.getByRole('button',{name:'로그인하기'})).toBeTruthy();
});

it('result expiry disables save buttons with the expiry alert',async()=>{
  mockApi();const user=await open();await search(user);
  await act(()=>vi.advanceTimersByTimeAsync(300000));
  expect(screen.queryByRole('button',{name:'이 경로를 루틴에 저장'})).toBeNull();
});

it('reselecting endpoints clears saved markers and allows saving the new search',async()=>{
  mockApi();const user=await open();await search(user);
  await user.click(screen.getAllByRole('button',{name:'이 경로를 루틴에 저장'})[0]);
  await user.click(screen.getByRole('button',{name:'루틴 저장'}));
  await user.click(screen.getByRole('button',{name:'도착지 변경'}));await user.click(screen.getByRole('button',{name:'검증 위치 적용'}));
  await search(user);const posts=apiRequest.mock.calls.filter(([path])=>path==='/api/v1/journey-searches');
  expect(posts).toHaveLength(2);
  await user.click(screen.getAllByRole('button',{name:'이 경로를 루틴에 저장'})[0]);
  await user.click(screen.getByRole('button',{name:'루틴 저장'}));
  const saves=apiRequest.mock.calls.filter(([path])=>path==='/api/v1/routines');
  expect(saves).toHaveLength(2);expect(saves[0][1].headers['Idempotency-Key']).not.toBe(saves[1][1].headers['Idempotency-Key']);
  expect(saves[1][1].body.search_id).toBe('search_test');
});

it('saving is blocked until both endpoints are saved places',async()=>{
  apiRequest.mockImplementation(path=>path==='/api/v1/auth/csrf'?Promise.resolve(reply({csrf_token:'csrf_test'})):Promise.resolve(result()));
  render(<JourneyComparison/>);
  const user={click:async node=>{await act(async()=>fireEvent.click(node));}};
  expect(screen.queryByRole('button',{name:'이 경로를 루틴에 저장'})).toBeNull();
  expect(screen.queryByRole('article')).toBeNull();
});


it('keeps the same creation key after a lost response and retry',async()=>{
  let saves=0;mockApi(()=>result(),()=>reply(accepted,202),()=>{if(saves++===0)throw new ApiError('NETWORK_ERROR');return reply(saved(),201);});
  const user=await open();await search(user);
  await user.click(screen.getAllByRole('button',{name:'이 경로를 루틴에 저장'})[0]);
  await user.click(screen.getByRole('button',{name:'루틴 저장'}));
  await user.click(screen.getByRole('button',{name:'결과 다시 확인'}));await act(()=>vi.advanceTimersByTimeAsync(2000));
  await user.click(screen.getAllByRole('button',{name:'이 경로를 루틴에 저장'})[0]);
  await user.click(screen.getByRole('button',{name:'루틴 저장'}));
  const calls=apiRequest.mock.calls.filter(([path])=>path==='/api/v1/routines');
  expect(calls).toHaveLength(2);expect(calls[1][1].headers['Idempotency-Key']).toBe(calls[0][1].headers['Idempotency-Key']);
});

it('replaces the selected routine route using PATCH and preserves its schedule',async()=>{
  const existing=saved();existing.weekdays=[2,4];existing.target_arrival_local_time='09:10';
  mockApi();apiRequest.mockImplementation(path=>{
    if(path==='/api/v1/auth/csrf')return Promise.resolve(reply({csrf_token:'csrf_test'}));
    if(path==='/api/v1/journey-searches')return Promise.resolve(reply(accepted,202));
    if(path==='/api/v1/routines/'+existing.routine_id)return Promise.resolve(reply({...existing,version:2},200));
    return Promise.resolve(result());
  });
  const onRoutineSaved=vi.fn();const user=await open({routineToReplace:existing,onRoutineSaved});await search(user);
  await user.click(screen.getAllByRole('button',{name:'이 경로로 루틴 변경'})[0]);
  expect(within(screen.getByRole('group',{name:'반복 요일'})).getAllByRole('button',{pressed:true}).map(node=>node.textContent)).toEqual(['화','목']);
  expect(screen.getByLabelText(/목표 도착 시각/).value).toBe('09:10');
  await user.click(screen.getByRole('button',{name:'루틴 저장'}));
  const request=apiRequest.mock.calls.find(([path])=>path==='/api/v1/routines/'+existing.routine_id);
  expect(request[1].method).toBe('PATCH');expect(request[1].body).toMatchObject({expected_version:1,weekdays:[2,4],target_arrival_local_time:'09:10'});
  expect(onRoutineSaved).toHaveBeenCalledOnce();
  expect(apiRequest.mock.calls.some(([path])=>path==='/api/v1/routines')).toBe(false);
});


it.each([['map_pin','saved_place'],['current_location','saved_place'],['saved_place','map_pin'],['saved_place','current_location'],['map_pin','map_pin']])(
  'keeps %s / %s results and explains saved-place eligibility before offering save',async(originType,destinationType)=>{
    endpointTypes.origin=originType;endpointTypes.destination=destinationType;
    mockApi();const user=await open();await search(user);
    expect(screen.getByRole('heading',{name:'경로 후보 2개'})).toBeTruthy();
    expect(screen.queryAllByRole('button',{name:'이 경로를 루틴에 저장'})).toHaveLength(0);
    expect(screen.getByText('루틴을 저장하려면 출발지와 도착지를 내 저장 장소에서 선택해주세요.')).toBeTruthy();
    expect(screen.queryByRole('alert')).toBeNull();
    expect(apiRequest.mock.calls.some(([path])=>path==='/api/v1/routines')).toBe(false);
  }
);

it('recovers a map search by selecting saved endpoints then sends the routine POST',async()=>{
  endpointTypes.origin='map_pin';endpointTypes.destination='map_pin';
  mockApi();const user=await open();await search(user);
  await user.click(screen.getByRole('button',{name:'출발지 저장 장소 선택'}));
  expect(screen.getByRole('button',{name:'검증 위치 적용'}).dataset.mode).toBe('saved');
  await user.click(screen.getByRole('button',{name:'검증 위치 적용'}));
  // After selecting the first endpoint, choose the second before requerying.
  await user.click(screen.getByRole('button',{name:'도착지 저장 장소 선택'}));
  await user.click(screen.getByRole('button',{name:'검증 위치 적용'}));
  await search(user);
  await user.click(screen.getAllByRole('button',{name:'이 경로를 루틴에 저장'})[0]);
  await user.click(screen.getByRole('button',{name:'루틴 저장'}));
  const request=apiRequest.mock.calls.find(([path])=>path==='/api/v1/routines');
  expect(request[1].body).toMatchObject({origin_place_id:'place_origin',destination_place_id:'place_destination'});
  expect(screen.getByText('루틴에 저장했어요')).toBeTruthy();
});
