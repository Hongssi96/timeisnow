import React from 'react';
import { afterEach,beforeEach,expect,it,vi } from 'vitest';
import { render,screen,act,cleanup } from '@testing-library/react';
import FirstArrivals from '../../src/components/FirstArrivals';
import { getFirstDeparture } from '../../src/lib/departure';
import {activeTrip,confirmDeparture} from '../../src/lib/trips';
vi.mock('../../src/lib/trips',()=>({activeTrip:vi.fn().mockResolvedValue(null),confirmDeparture:vi.fn(),cancelTrip:vi.fn()}));
vi.mock('../../src/lib/departure',()=>({getFirstDeparture:vi.fn()}));
const start=Date.parse('2026-10-13T08:00:00Z');
let elapsed;
function response() {
  return {meta:{server_time:new Date(start).toISOString()},data:{status:'ready',valid_for_guidance:true,valid_until:new Date(start+120000).toISOString(),recommended_departure_at:new Date(start+180000).toISOString(),selected_departure_at:new Date(start+180000).toISOString(),vehicle_arrival_at:new Date(start+780000).toISOString(),arrival_candidate_id:'bus',approach_seconds:300,applied_duration_factor:1.1,buffer_seconds:300,slack_status:'meets_buffer',arrival_evidence:{status:'estimated',valid_for_guidance:true,timing_basis:'receipt_estimate',received_at:new Date(start).toISOString(),expires_at:new Date(start+120000).toISOString(),candidates:[{candidate_id:'bus',predicted_arrival_at:new Date(start+780000).toISOString()}]}}};
}
async function mount(){render(<FirstArrivals includeDeparture searchId="search" candidateId="candidate"/>);await act(async()=>{});}
beforeEach(()=>{elapsed=0;vi.useFakeTimers();vi.spyOn(performance,'now').mockImplementation(()=>elapsed);getFirstDeparture.mockReset();getFirstDeparture.mockResolvedValue(response());Object.defineProperty(document,'hidden',{configurable:true,value:false});});
afterEach(()=>{cleanup();vi.restoreAllMocks();vi.useRealTimers();});
it('shows same-stop transfer and separately fetched final walk when later vehicles are too early',async()=>{
 const r=response();r.data.connection_status='unavailable';r.data.transfers=[{connection_id:'link',feasibility:'unavailable',reasons:['NO_SUPPLIED_VEHICLE_AFTER_MINIMUM']}];
 r.data.supplemental_walks=[{role:'transfer',source:'same_stop',connection_id:'link',walking_seconds:0},{role:'egress',source:'walking_route',connection_id:null,walking_seconds:157}];
 getFirstDeparture.mockResolvedValue(r);await mount();
 expect(screen.getByText(/같은 정류소에서 환승/)).toBeTruthy();expect(screen.getByText(/마지막 도보 약 2분 37초/)).toBeTruthy();expect(screen.getByText(/현재 제공된 차량은 도착하기 전에 지나가요/)).toBeTruthy();expect(screen.getByText('3분')).toBeTruthy();
});
it('answers with a big minute countdown and no clock or coefficient',async()=>{
  await mount();expect(screen.getByText('언제이니?')).toBeTruthy();expect(screen.getByText('3분')).toBeTruthy();expect(screen.queryByText(/예상 출발/)).toBeNull();expect(screen.queryByText(/개인 계수/)).toBeNull();expect(screen.queryByText(/접근 약/)).toBeNull();expect(screen.getByText('수신 기준 예상')).toBeTruthy();expect(getFirstDeparture).toHaveBeenCalledTimes(1);
});
it('failed refresh cannot keep showing expired departure numbers',async()=>{
  await mount();getFirstDeparture.mockRejectedValue({code:'PROVIDER_TIMEOUT'});elapsed=121000;await act(async()=>{vi.advanceTimersByTime(121000);});
  expect(screen.queryByText('3분')).toBeNull();expect(screen.getByText(/출발 정보가 만료/)).toBeTruthy();
});
it('never fabricates numbers for missing approach evidence',async()=>{
  const r=response();r.data.status='insufficient_data';r.data.valid_for_guidance=false;getFirstDeparture.mockResolvedValue(r);await mount();expect(screen.queryByText('3분')).toBeNull();expect(screen.getByText(/접근 시간 또는 도착 근거/)).toBeTruthy();
});
it('warns when an already passed recommendation cannot assure the configured buffer',async()=>{
  const r=response();r.data.recommended_departure_at=new Date(start-10000).toISOString();r.data.selected_departure_at=new Date(start).toISOString();r.data.slack_status='below_buffer';r.data.vehicle_arrival_at=new Date(start+480000).toISOString();r.data.arrival_evidence.candidates[0].predicted_arrival_at=r.data.vehicle_arrival_at;getFirstDeparture.mockResolvedValue(r);
  await mount();expect(screen.getByText(/권장 출발 시각이 지났/)).toBeTruthy();expect(screen.getByText(/설정한 여유보다 적/)).toBeTruthy();
});
it('removes earlier recommendation when reaching the vehicle becomes impossible',async()=>{
  const r=response();r.data.vehicle_arrival_at=new Date(start+310000).toISOString();r.data.arrival_evidence.candidates[0].predicted_arrival_at=r.data.vehicle_arrival_at;getFirstDeparture.mockResolvedValue(r);
  await mount();elapsed=15000;await act(async()=>{vi.advanceTimersByTime(15000);});expect(screen.queryByText('3분')).toBeNull();expect(screen.getByText(/접근 시간이 부족/)).toBeTruthy();
});
it('search or profile conflict removes departure and blocks retries',async()=>{
  await mount();getFirstDeparture.mockRejectedValue({code:'VERSION_CONFLICT'});await act(async()=>{vi.advanceTimersByTime(60000);});expect(screen.queryByText('3분')).toBeNull();expect(screen.getByRole('alert')).toBeTruthy();
});

it('counts down in minutes even when departure belongs to a different Seoul day',async()=>{
  const r=response();r.data.selected_departure_at='2026-10-14T08:03:00Z';r.data.vehicle_arrival_at='2026-10-14T08:13:00Z';r.data.arrival_evidence.candidates[0].predicted_arrival_at=r.data.vehicle_arrival_at;getFirstDeparture.mockResolvedValue(r);await mount();expect(screen.getByText('1443분')).toBeTruthy();expect(screen.queryByText(/예상 출발/)).toBeNull();
});

it('shows estimated transfer times and keeps unknown later links without numbers',async()=>{
  const r=response();r.data.connection_status='unknown';r.data.transfers=[{connection_id:'one',feasibility:'estimated_feasible',minimum_boarding_at:'2026-10-13T08:24:00Z',next_boarding_at:'2026-10-13T08:25:00Z'},{connection_id:'two',feasibility:'unknown',minimum_boarding_at:null,next_boarding_at:null}];getFirstDeparture.mockResolvedValue(r);await mount();
  expect(screen.getByText(/환승 1 · 예상 연결 가능/)).toBeTruthy();expect(screen.getByText(/환승 2 · 연결 정보 확인 필요/)).toBeTruthy();expect(screen.getByText(/최소 승차 시각/)).toBeTruthy();expect(screen.getByText(/다음 차량 예상/)).toBeTruthy();
});
it('expired evidence removes earlier transfer timestamps',async()=>{
  const r=response();r.data.connection_status='estimated_feasible';r.data.transfers=[{connection_id:'one',feasibility:'estimated_feasible',minimum_boarding_at:'2026-10-13T08:24:00Z',next_boarding_at:'2026-10-13T08:25:00Z'}];getFirstDeparture.mockResolvedValue(r);await mount();getFirstDeparture.mockRejectedValue({code:'PROVIDER_TIMEOUT'});elapsed=121000;await act(async()=>{vi.advanceTimersByTime(121000);});
  expect(screen.queryByText(/다음 차량 예상/)).toBeNull();expect(screen.getByText(/환승 정보가 만료/)).toBeTruthy();
});

it('routine loader failure removes unexpired numbers and requires an explicit fresh query',async()=>{
 const initial=response(),loader=vi.fn().mockRejectedValue({code:'PROVIDER_TIMEOUT'});
 render(<FirstArrivals includeDeparture searchId="search" candidateId="candidate" loader={loader} initialResponse={initial}/>);await act(async()=>{});
 expect(screen.getByText('3분')).toBeTruthy();expect(loader).not.toHaveBeenCalled();
 elapsed=60000;await act(async()=>{vi.advanceTimersByTime(60000);});expect(screen.queryByText('3분')).toBeNull();
 elapsed=120000;await act(async()=>{vi.advanceTimersByTime(60000);});expect(loader).toHaveBeenCalledTimes(1);
});

it('displays departure countdown together with first stop slack',async()=>{
 await mount();expect(screen.getByText('3분')).toBeTruthy();expect(screen.getByText('그때 출발하면 정류장 도착 후 예상 5분 여유가 있어요.')).toBeTruthy();
 const refreshed=response();refreshed.meta.server_time=new Date(start+61000).toISOString();getFirstDeparture.mockResolvedValue(refreshed);elapsed=61000;await act(async()=>{vi.advanceTimersByTime(61000);});expect(screen.getByText('2분')).toBeTruthy();
});
it('past selected time recomputes current slack instead of preserving five minutes',async()=>{
 const r=response();r.data.selected_departure_at=new Date(start-10000).toISOString();r.data.recommended_departure_at=r.data.selected_departure_at;r.data.vehicle_arrival_at=new Date(start+480000).toISOString();r.data.arrival_evidence.candidates[0].predicted_arrival_at=r.data.vehicle_arrival_at;getFirstDeparture.mockResolvedValue(r);
 await mount();expect(screen.getByText('지금')).toBeTruthy();expect(screen.getByText('지금 출발 기준으로 다시 확인해주세요.')).toBeTruthy();expect(screen.getByText('지금 출발하면 정류장 도착 후 예상 3분 여유가 있어요.')).toBeTruthy();
 elapsed=15000;await act(async()=>{vi.advanceTimersByTime(15000);});expect(screen.getByText('지금 출발하면 정류장 도착 후 예상 2분 45초 여유가 있어요.')).toBeTruthy();
});
it('less than one minute is described without rounding a zero departure',async()=>{
 const r=response();r.data.selected_departure_at=new Date(start+30000).toISOString();getFirstDeparture.mockResolvedValue(r);await mount();expect(screen.getByText('1분')).toBeTruthy();expect(screen.getByText('이내')).toBeTruthy();
});
it('separates missing access time from a mapping failure without invented times',async()=>{
 const r=response();r.data.status='insufficient_data';r.data.valid_for_guidance=false;r.data.reasons=['ACCESS_TIME_UNCONFIRMED'];r.data.arrival_evidence={...r.data.arrival_evidence,status:'mapping_required',valid_for_guidance:false,candidates:[],reasons:['PUBLIC_MAPPING_UNCONFIRMED','NO_ROUTE_AT_BOARDING_STOP']};getFirstDeparture.mockResolvedValue(r);
  await mount();expect(screen.getByText(/도보 시간이 제공되지 않아/)).toBeTruthy();expect(screen.getByText(/해당 노선을 경기 교통 정보에서/)).toBeTruthy();expect(screen.queryByText('3분')).toBeNull();
});

it('unknown diagnostic content is never rendered as provider text',async()=>{
 const r=response();r.data.valid_for_guidance=false;r.data.arrival_evidence={...r.data.arrival_evidence,status:'mapping_required',valid_for_guidance:false,candidates:[],reasons:['constructor','secret raw response']};getFirstDeparture.mockResolvedValue(r);await mount();expect(screen.queryByText(/secret raw/)).toBeNull();expect(screen.getByText(/버스 정류소와 방향을 아직/)).toBeTruthy();
});

it('labels a separately queried boarding walk without calling it AI evidence',async()=>{
  const r=response();r.data.provider_approach_source='boarding_walk';getFirstDeparture.mockResolvedValue(r);await mount();expect(screen.getByText(/별도로 조회한 추정/)).toBeTruthy();expect(screen.queryByText(/AI 산정으로/)).toBeNull();
});
it('walk timeout remains a clear blocker without invented departure numbers',async()=>{
 const r=response();r.data.status='insufficient_data';r.data.valid_for_guidance=false;r.data.reasons=['ACCESS_TIME_UNCONFIRMED','ACCESS_WALK_TIMEOUT'];getFirstDeparture.mockResolvedValue(r);await mount();expect(screen.getByText(/도보 조회가 늦어/)).toBeTruthy();expect(screen.queryByText('3분')).toBeNull();
});

function withGoal(status='estimated_meets'){const r=response();r.data.target_evaluation={status,target_arrival_at:new Date(start+1500000).toISOString(),estimated_destination_arrival_at:new Date(start+1320000).toISOString(),margin_seconds:180,reasons:[]};return r;}
it('shows destination goal margin separately from first boarding buffer',async()=>{getFirstDeparture.mockResolvedValue(withGoal());await mount();expect(screen.getByText('목표 도착 평가')).toBeTruthy();expect(screen.getByText('목표 도착 기준 예상 3분 여유')).toBeTruthy();expect(screen.getByText(/정류장 도착 후 예상 5분 여유/)).toBeTruthy();});
it('late arrival is labelled late and never called goal slack',async()=>{const r=withGoal('estimated_late');r.data.target_evaluation.margin_seconds=-90;getFirstDeparture.mockResolvedValue(r);await mount();expect(screen.getByText('목표 도착 기준 예상 1분 30초 늦음')).toBeTruthy();});
it('unknown last walking leg cannot show destination numbers',async()=>{const r=withGoal('unknown');r.data.target_evaluation.reasons=['EGRESS_TIME_UNCONFIRMED'];getFirstDeparture.mockResolvedValue(r);await mount();expect(screen.getByText(/하차 후 목적지까지 도보 시간이 없어/)).toBeTruthy();expect(screen.queryByText(/예상 목적지 도착/)).toBeNull();});
it('expiry removes old goal destination and margin numbers',async()=>{getFirstDeparture.mockResolvedValue(withGoal());await mount();getFirstDeparture.mockRejectedValue({code:'PROVIDER_TIMEOUT'});elapsed=121000;await act(async()=>{vi.advanceTimersByTime(121000);});expect(screen.queryByText(/예상 목적지 도착/)).toBeNull();expect(screen.queryByText(/목표 도착 기준 예상/)).toBeNull();expect(screen.getByText(/목표 도착 평가가 만료/)).toBeTruthy();});

it('poll refresh displays the next supplied vehicle and the updated clock',async()=>{
 await mount();
 const r=response();r.meta.server_time=new Date(start+60000).toISOString();r.data.reasons=['NEXT_REACHABLE_VEHICLE'];
 r.data.vehicle_arrival_at=new Date(start+1080000).toISOString();r.data.recommended_departure_at=r.data.selected_departure_at=new Date(start+480000).toISOString();
 r.data.arrival_candidate_id='later';r.data.arrival_evidence.candidates=[{candidate_id:'early',predicted_arrival_at:new Date(start+90000).toISOString()},{candidate_id:'later',predicted_arrival_at:r.data.vehicle_arrival_at}];
 getFirstDeparture.mockResolvedValue(r);elapsed=60000;await act(async()=>{vi.advanceTimersByTime(60000);});
 expect(getFirstDeparture).toHaveBeenCalledTimes(2);expect(screen.queryByText('3분')).toBeNull();expect(screen.getByText('7분')).toBeTruthy();
 expect(screen.getByText(/접근 시간이 부족한 앞 차량/)).toBeTruthy();
});

it('shows half-time unconfirmed departure switch separately from unreachable access',async()=>{
 const r=response();r.data.reasons=['DEPARTURE_UNCONFIRMED_NEXT_VEHICLE'];getFirstDeparture.mockResolvedValue(r);await mount();
  expect(screen.getByText(/접근 시간의 절반이 지나/)).toBeTruthy();expect(screen.getByText('3분')).toBeTruthy();
});
it('no supplied next vehicle hides clocks and explains unconfirmed departure',async()=>{
 const r=response();r.data.valid_for_guidance=false;r.data.status='insufficient_data';r.data.reasons=['DEPARTURE_UNCONFIRMED_NO_NEXT'];getFirstDeparture.mockResolvedValue(r);await mount();
 expect(screen.queryByText(/예상 출발 17/)).toBeNull();expect(screen.getByText(/이용 가능한 다음 차량 정보가 없어/)).toBeTruthy();
});
it('reported departure hides pre-departure arrival, transfer and target numbers',async()=>{
 const r=response();r.data.departure_state='reported_departed';r.data.valid_for_guidance=false;r.data.connection_status='estimated_feasible';r.data.transfers=[{connection_id:'one',feasibility:'estimated_feasible',minimum_boarding_at:'2026-10-13T08:24:00Z',next_boarding_at:'2026-10-13T08:25:00Z'}];getFirstDeparture.mockResolvedValue(r);await mount();
 expect(screen.queryByText(/예상 출발 17/)).toBeNull();expect(screen.queryByText(/다음 차량 예상/)).toBeNull();expect(screen.queryByText(/수신 기준 예상/)).toBeNull();expect(screen.getByText(/출발 전 안내를 종료/)).toBeTruthy();
});

it('persisted manual departure immediately hides clocks and stops periodic departure requests',async()=>{
 activeTrip.mockResolvedValue(null);confirmDeparture.mockResolvedValue({trip_id:'t',guidance_id:'g',routine_id:'r',status:'active',version:1,departure_event:{event_id:'e'}});
 const r=response();r.data.guidance_id='g';getFirstDeparture.mockResolvedValue(r);const onReported=vi.fn();
 render(<FirstArrivals includeDeparture searchId="search" candidateId="candidate" routineId="r" onReported={onReported}/>);await act(async()=>{});
 await act(async()=>{screen.getByText('지금 출발했어요').click();});expect(screen.queryByText('예상 출발 17:03')).toBeNull();expect(onReported).toHaveBeenCalledTimes(1);
 elapsed=300000;await act(async()=>{vi.advanceTimersByTime(300000);});expect(getFirstDeparture).toHaveBeenCalledTimes(1);expect(screen.getByText(/출발 전 안내를 종료/)).toBeTruthy();
});
