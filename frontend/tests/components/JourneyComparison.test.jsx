import React from 'react';
import { afterEach, expect, it, vi } from 'vitest';
import { act, fireEvent, render, screen, within } from '@testing-library/react';
import JourneyComparison from '../../src/components/JourneyComparison';
import { apiRequest, ApiError } from '../../src/lib/api';
import fixtures from '../fixtures/journeys.json';
vi.mock('../../src/lib/api',async original=>({...await original(),apiRequest:vi.fn()}));
vi.mock('../../src/components/OriginSelector',()=>({default:({purpose,onSelect})=><button onClick={()=>onSelect({label:purpose==='origin'?'출발 검증역':'도착 검증역',location_address:'서울 공개 검증 위치',origin:{type:'saved_place',place_id:purpose==='origin'?'place_origin':'place_destination',location_version:1},deadline:Date.now()+600000})}>검증 위치 적용</button>}));
afterEach(()=>{vi.resetAllMocks();vi.useRealTimers();});
const accepted={search_id:'search_test',job_id:'job_test',status:'queued'};
const reply=(data,status=200)=>({data,status,meta:{server_time:new Date().toISOString()}});
const result=(candidates=[fixtures.direct,fixtures.mixed],status='succeeded')=>reply({...accepted,status,candidates:structuredClone(candidates),unavailable_reasons:[],error:status==='failed'?{code:'PROVIDER_TIMEOUT',message:'private upstream'}:null,expires_at:new Date(Date.now()+290000).toISOString()});
function mockApi(get=()=>result(),post=()=>reply(accepted,202),preference='balanced'){
  apiRequest.mockImplementation((path)=>path==='/api/v1/me'?Promise.resolve(reply({user_id:'member',profile:{walking_preference:'normal',route_preference:preference,walking_duration_factor:1,first_boarding_buffer_seconds:300,transfer_buffer_seconds:120,timezone:'Asia/Seoul',version:1}})):path==='/api/v1/auth/csrf'?Promise.resolve(reply({csrf_token:'csrf_test'})):path==='/api/v1/journey-searches'?Promise.resolve(post()):Promise.resolve(get()));
}
async function open(props={}){
  vi.useFakeTimers();const user={click:async node=>{await act(async()=>fireEvent.click(node));},selectOptions:async(node,value)=>{await act(async()=>fireEvent.change(node,{target:{value}}));}};render(<JourneyComparison {...props}/>);
  await user.click(screen.getByRole('button',{name:'출발지 선택'}));await user.click(screen.getByRole('button',{name:'검증 위치 적용'}));
  await user.click(screen.getByRole('button',{name:'도착지 선택'}));await user.click(screen.getByRole('button',{name:'검증 위치 적용'}));return user;
}
async function search(user){await user.click(screen.getByRole('button',{name:'경로 후보 조회'}));await act(()=>vi.advanceTimersByTimeAsync(2000));}

it('only submits after explicit endpoints and click; shows estimates and safe detail',async()=>{
  mockApi();const user=await open();expect(apiRequest.mock.calls.some(([path])=>path==='/api/v1/journey-searches')).toBe(false);
  await search(user);expect(screen.getByRole('heading',{name:'경로 후보 2개'})).toBeTruthy();
  const post=apiRequest.mock.calls.find(([path])=>path==='/api/v1/journey-searches')[1];
  expect(post.body.origin.place_id).toBe('place_origin');expect(post.body.destination.place_id).toBe('place_destination');expect(post.headers['Idempotency-Key']).toBeTruthy();
  const articles=screen.getAllByRole('article');await user.click(within(articles[1]).getByRole('button',{name:'구간 자세히'}));
  expect(within(articles[1]).getByText('환승 도보')).toBeTruthy();expect(within(articles[1]).getByText(/연결 가능 여부 확인 필요/)).toBeTruthy();
  expect(screen.queryByRole('button',{name:'지금 출발할게요'})).toBeNull();
  await user.selectOptions(screen.getByLabelText('비교 기준'),'fewer_transfers');expect(apiRequest.mock.calls.filter(([path])=>path==='/api/v1/journey-searches')).toHaveLength(1);
});
it('missing access and egress do not show a false zero-minute walking time',async()=>{
  const value=structuredClone(fixtures.direct);value.ordered_legs=[value.ordered_legs[1]];value.ordered_legs[0].sequence=0;value.walking_seconds=0;
  value.missing_segments.push('ACCESS_WALK_MISSING','EGRESS_WALK_MISSING');value.timing_breakdown={walking_seconds:0,in_vehicle_seconds:500,legs_total_seconds:500,provider_total_seconds:value.total_seconds,unallocated_seconds:value.total_seconds-500,status:'unallocated'};
  mockApi(()=>result([value]));const user=await open();await search(user);
  expect(screen.getByText('확인 필요')).toBeTruthy();expect(screen.queryByText('약 0분')).toBeNull();
});
it('GET retry does not create another search or reuse malformed candidates',async()=>{
  let get=0;mockApi(()=>{if(get++===0)throw new ApiError('NETWORK_ERROR');return result();});const user=await open();await search(user);
  expect(screen.queryByRole('article')).toBeNull();await user.click(screen.getByRole('button',{name:'결과 다시 확인'}));
  expect(screen.getAllByRole('article')).toHaveLength(2);expect(apiRequest.mock.calls.filter(([path])=>path==='/api/v1/journey-searches')).toHaveLength(1);
});
it('unknown POST outcome retries the same body and idempotency key',async()=>{
  let posts=0;mockApi(()=>result(),()=>{if(posts++===0)throw new ApiError('NETWORK_ERROR');return reply(accepted,202);});const user=await open();await search(user);
  await user.click(screen.getByRole('button',{name:'같은 요청 다시 확인'}));await act(()=>vi.advanceTimersByTimeAsync(2000));
  const calls=apiRequest.mock.calls.filter(([path])=>path==='/api/v1/journey-searches');expect(calls).toHaveLength(2);
  expect(calls[0][1].body).toEqual(calls[1][1].body);expect(calls[0][1].headers['Idempotency-Key']).toBe(calls[1][1].headers['Idempotency-Key']);
});
it('result expiry removes candidates and detailed content',async()=>{
  mockApi();const user=await open();await search(user);await user.click(screen.getAllByRole('button',{name:'구간 자세히'})[0]);
  await act(()=>vi.advanceTimersByTimeAsync(300000));expect(screen.queryByRole('article')).toBeNull();expect(screen.getByRole('alert').textContent).toContain('만료');
});
it('authentication expiry clears selected endpoints and returns to login',async()=>{
  const auth=vi.fn();mockApi(()=>{throw new ApiError('SESSION_EXPIRED');});const user=await open({onAuthError:auth});await search(user);
  expect(screen.getByRole('button',{name:'로그인하기'})).toBeTruthy();expect(screen.queryByText('출발 검증역')).toBeNull();expect(auth).toHaveBeenCalledOnce();
});
it('normal empty and worker failure are distinct; raw errors are never displayed',async()=>{
  let gets=0;mockApi(()=>gets++===0?result([]):result([],'failed'));const user=await open();await search(user);
  expect(screen.getByRole('heading',{name:'지금 비교할 경로가 없어요'})).toBeTruthy();await search(user);
  expect(screen.getByRole('alert').textContent).toContain('응답이 늦어요');expect(screen.queryByText('private upstream')).toBeNull();
});
it('changing an endpoint cancels pending GET and ignores late completion',async()=>{
  let resolve;mockApi(()=>new Promise(done=>{resolve=done;}));const user=await open();await search(user);
  const request=apiRequest.mock.calls.find(([path])=>path.includes('/journey-searches/'))[1];await user.click(screen.getByRole('button',{name:'출발지 변경'}));
  expect(request.signal.aborted).toBe(true);await act(async()=>resolve(result()));expect(screen.queryByRole('article')).toBeNull();
});

it('endpoint and transfer reasons appear together and reselecting starts a new request',async()=>{
  mockApi(()=>{const value=result([]);value.data.unavailable_reasons=['ENDPOINT_UNRESOLVED','TRANSFER_LIMIT','FUTURE_REASON'];return value;});
  const user=await open();await search(user);
  expect(screen.getByText(/승하차 지점과 연결하지 못했어요/)).toBeTruthy();expect(screen.getByText(/최대 2회 환승 안/)).toBeTruthy();
  expect(screen.queryByText('FUTURE_REASON')).toBeNull();expect(screen.getByText(/제공된 정보만으로/)).toBeTruthy();
  await user.click(screen.getByRole('button',{name:'도착지 다시 선택'}));await user.click(screen.getByRole('button',{name:'검증 위치 적용'}));await search(user);
  const posts=apiRequest.mock.calls.filter(([path])=>path==='/api/v1/journey-searches');expect(posts).toHaveLength(2);
  expect(posts[0][1].headers['Idempotency-Key']).not.toBe(posts[1][1].headers['Idempotency-Key']);
});

it('unsupported region clears inputs and offers reselect without a false expiry',async()=>{
  mockApi(()=>result(),()=>{throw new ApiError('UNSUPPORTED_REGION');});const user=await open();await search(user);
  expect(screen.getByRole('heading',{name:'서울·경기 안의 위치를 선택해주세요'})).toBeTruthy();
  expect(screen.queryByText('출발 검증역')).toBeNull();expect(screen.queryByText(/만료됐어요/)).toBeNull();
  expect(screen.getByRole('button',{name:'경로 후보 조회'}).disabled).toBe(true);
  await user.click(screen.getByRole('button',{name:'출발지 다시 선택'}));expect(screen.getByRole('button',{name:'검증 위치 적용'})).toBeTruthy();
  expect(apiRequest.mock.calls.filter(([path])=>path==='/api/v1/journey-searches')).toHaveLength(1);
});

it('insufficient candidates remain visible and unknown missing reasons stay safe',async()=>{
  const value=structuredClone(fixtures.direct);value.missing_segments.push('FUTURE_MISSING');mockApi(()=>result([value]));const user=await open();await search(user);
  expect(screen.getByText(/구간 정보 확인 필요 ·/)).toBeTruthy();await user.click(screen.getByRole('button',{name:'구간 자세히'}));
  expect(screen.getByText('추가 구간 정보 확인 필요')).toBeTruthy();expect(screen.queryByText('FUTURE_MISSING')).toBeNull();
  expect(screen.getByText('공공 노선의 실제 운행 방향 확인 필요')).toBeTruthy();expect(screen.getAllByRole('article')).toHaveLength(1);
});

it('accepted worker region failure offers reselect rather than repeating the same invalid search',async()=>{
  mockApi(()=>{const value=result([],'failed');value.data.error.code='UNSUPPORTED_REGION';return value;});const user=await open();await search(user);
  expect(screen.getByRole('heading',{name:'서울·경기 안의 위치를 선택해주세요'})).toBeTruthy();
  expect(screen.queryByText('도착 검증역')).toBeNull();expect(screen.queryByRole('button',{name:'경로 후보 다시 조회'})).toBeNull();
  await user.click(screen.getByRole('button',{name:'도착지 다시 선택'}));expect(screen.getByRole('button',{name:'검증 위치 적용'})).toBeTruthy();
});

it('shows indoor walking evidence without starting an AI request',async()=>{
  mockApi(()=>result([fixtures.mixed]));const user=await open();await search(user);
  await user.click(screen.getByRole('button',{name:'구간 자세히'}));
  expect(screen.getByRole('heading',{name:'개인 도보 시간은 아직 확인 전이에요'})).toBeTruthy();
  expect(screen.getByText(/입구부터 승강장까지/)).toBeTruthy();
  expect(apiRequest.mock.calls.filter(([path])=>path==='/api/v1/journey-searches')).toHaveLength(1);
  expect(apiRequest.mock.calls.some(([path])=>path.includes('walking-estimates'))).toBe(false);
});
it('shows safe AI validation failure while announcing the existing error once',async()=>{
  mockApi(()=>{throw new ApiError('AI_OUTPUT_INVALID');});const user=await open();await search(user);
  expect(screen.getByText(/AI 산정 결과를 검증하지 못했어요/)).toBeTruthy();expect(screen.getAllByRole('alert')).toHaveLength(1);
  expect(screen.getByRole('button',{name:'결과 다시 확인'})).toBeTruthy();
});
it('hides candidate times and shows walking recovery when results expire',async()=>{
  mockApi();const user=await open();await search(user);
  await act(()=>vi.advanceTimersByTimeAsync(290000));
  expect(screen.queryByRole('article')).toBeNull();expect(screen.getByText(/이전 경로의 시간을 사용하지/)).toBeTruthy();
});

it('initializes comparison with the saved route preference while allowing an explicit override',async()=>{
 mockApi(undefined,undefined,'less_walking');const user=await open();expect(screen.getByLabelText('비교 기준').value).toBe('less_walking');
 await user.selectOptions(screen.getByLabelText('비교 기준'),'fewer_transfers');await search(user);
 expect(apiRequest.mock.calls.find(([path])=>path==='/api/v1/journey-searches')[1].body.preferences.route_preference).toBe('fewer_transfers');
});
