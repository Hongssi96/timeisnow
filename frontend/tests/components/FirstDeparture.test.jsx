import React from 'react';
import { afterEach,beforeEach,expect,it,vi } from 'vitest';
import { render,screen,act,cleanup } from '@testing-library/react';
import FirstArrivals from '../../src/components/FirstArrivals';
import { getFirstDeparture } from '../../src/lib/departure';
vi.mock('../../src/lib/departure',()=>({getFirstDeparture:vi.fn()}));
const start=Date.parse('2026-10-13T08:00:00Z');
let elapsed;
function response() {
  return {meta:{server_time:new Date(start).toISOString()},data:{status:'ready',valid_for_guidance:true,valid_until:new Date(start+120000).toISOString(),recommended_departure_at:new Date(start+180000).toISOString(),selected_departure_at:new Date(start+180000).toISOString(),vehicle_arrival_at:new Date(start+780000).toISOString(),arrival_candidate_id:'bus',approach_seconds:300,applied_duration_factor:1.1,buffer_seconds:300,slack_status:'meets_buffer',arrival_evidence:{status:'estimated',valid_for_guidance:true,timing_basis:'receipt_estimate',received_at:new Date(start).toISOString(),expires_at:new Date(start+120000).toISOString(),candidates:[{candidate_id:'bus',predicted_arrival_at:new Date(start+780000).toISOString()}]}}};
}
async function mount(){render(<FirstArrivals includeDeparture searchId="search" candidateId="candidate"/>);await act(async()=>{});}
beforeEach(()=>{elapsed=0;vi.useFakeTimers();vi.spyOn(performance,'now').mockImplementation(()=>elapsed);getFirstDeparture.mockReset();getFirstDeparture.mockResolvedValue(response());Object.defineProperty(document,'hidden',{configurable:true,value:false});});
afterEach(()=>{cleanup();vi.restoreAllMocks();vi.useRealTimers();});
it('shows an approximate departure clock and disclosed access basis',async()=>{
  await mount();expect(screen.getByText('예상 출발 17:03')).toBeTruthy();expect(screen.getByText(/접근 약 5분/)).toBeTruthy();expect(screen.getByText(/개인 계수 1.1/)).toBeTruthy();expect(screen.getByText('수신 기준 예상')).toBeTruthy();expect(getFirstDeparture).toHaveBeenCalledTimes(1);
});
it('failed refresh cannot keep showing expired departure numbers',async()=>{
  await mount();getFirstDeparture.mockRejectedValue({code:'PROVIDER_TIMEOUT'});elapsed=121000;await act(async()=>{vi.advanceTimersByTime(121000);});
  expect(screen.queryByText('예상 출발 17:03')).toBeNull();expect(screen.getByText(/출발 정보가 만료/)).toBeTruthy();
});
it('never fabricates numbers for missing approach evidence',async()=>{
  const r=response();r.data.status='insufficient_data';r.data.valid_for_guidance=false;getFirstDeparture.mockResolvedValue(r);await mount();expect(screen.queryByText(/예상 출발 17/)).toBeNull();expect(screen.getByText(/접근 시간 또는 도착 근거/)).toBeTruthy();
});
it('warns when an already passed recommendation cannot assure the configured buffer',async()=>{
  const r=response();r.data.recommended_departure_at=new Date(start-10000).toISOString();r.data.selected_departure_at=new Date(start).toISOString();r.data.slack_status='below_buffer';getFirstDeparture.mockResolvedValue(r);
  await mount();expect(screen.getByText(/권장 출발 시각이 지났/)).toBeTruthy();expect(screen.getByText(/설정한 여유보다 적/)).toBeTruthy();
});
it('removes earlier recommendation when reaching the vehicle becomes impossible',async()=>{
  const r=response();r.data.vehicle_arrival_at=new Date(start+310000).toISOString();r.data.arrival_evidence.candidates[0].predicted_arrival_at=r.data.vehicle_arrival_at;getFirstDeparture.mockResolvedValue(r);
  await mount();elapsed=15000;await act(async()=>{vi.advanceTimersByTime(15000);});expect(screen.queryByText(/예상 출발 17/)).toBeNull();expect(screen.getByText(/접근 시간이 부족/)).toBeTruthy();
});
it('search or profile conflict removes departure and blocks retries',async()=>{
  await mount();getFirstDeparture.mockRejectedValue({code:'VERSION_CONFLICT'});await act(async()=>{vi.advanceTimersByTime(60000);});expect(screen.queryByText(/예상 출발 17/)).toBeNull();expect(screen.getByRole('alert')).toBeTruthy();
});

it('shows the date when departure belongs to a different Seoul day',async()=>{
  const r=response();r.data.selected_departure_at='2026-10-14T08:03:00Z';getFirstDeparture.mockResolvedValue(r);await mount();expect(screen.getByText('예상 출발 10월 14일 17:03')).toBeTruthy();
});

it('does not round the configured seconds up to a full minute',async()=>{
  const r=response();r.data.buffer_seconds=30;getFirstDeparture.mockResolvedValue(r);await mount();expect(screen.getByText(/설정 여유 30초/)).toBeTruthy();
});

it('shows estimated transfer times and keeps unknown later links without numbers',async()=>{
  const r=response();r.data.connection_status='unknown';r.data.transfers=[{connection_id:'one',feasibility:'estimated_feasible',minimum_boarding_at:'2026-10-13T08:24:00Z',next_boarding_at:'2026-10-13T08:25:00Z'},{connection_id:'two',feasibility:'unknown',minimum_boarding_at:null,next_boarding_at:null}];getFirstDeparture.mockResolvedValue(r);await mount();
  expect(screen.getByText(/환승 1 · 예상 연결 가능/)).toBeTruthy();expect(screen.getByText(/환승 2 · 연결 정보 확인 필요/)).toBeTruthy();expect(screen.getByText(/최소 승차 시각/)).toBeTruthy();expect(screen.getByText(/다음 차량 예상/)).toBeTruthy();
});
it('expired evidence removes earlier transfer timestamps',async()=>{
  const r=response();r.data.connection_status='estimated_feasible';r.data.transfers=[{connection_id:'one',feasibility:'estimated_feasible',minimum_boarding_at:'2026-10-13T08:24:00Z',next_boarding_at:'2026-10-13T08:25:00Z'}];getFirstDeparture.mockResolvedValue(r);await mount();getFirstDeparture.mockRejectedValue({code:'PROVIDER_TIMEOUT'});elapsed=121000;await act(async()=>{vi.advanceTimersByTime(121000);});
  expect(screen.queryByText(/다음 차량 예상/)).toBeNull();expect(screen.getByText(/환승 정보가 만료/)).toBeTruthy();
});
