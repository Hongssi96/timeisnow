import React from 'react';
import { beforeEach, afterEach, expect, it, vi } from 'vitest';
import { act, render, screen, cleanup } from '@testing-library/react';
import FirstArrivals from '../../src/components/FirstArrivals';
import { getFirstArrivals } from '../../src/lib/arrivals';
vi.mock('../../src/lib/arrivals',()=>({getFirstArrivals:vi.fn()}));
const start=Date.parse('2026-10-13T08:00:00Z');
let elapsed;
function response(seconds=300) {
  return {meta:{server_time:new Date(start).toISOString()},data:{status:'estimated',source_status:'unknown',timing_basis:'receipt_estimate',generated_at:null,received_at:new Date(start).toISOString(),expires_at:new Date(start+120000).toISOString(),valid_for_guidance:true,candidates:[{candidate_id:'synthetic',predicted_arrival_at:new Date(start+seconds*1000).toISOString()}]}};
}
async function mount() {render(<FirstArrivals searchId="search" candidateId="candidate"/>);await act(async()=>{});}
beforeEach(()=>{elapsed=0;vi.useFakeTimers();vi.spyOn(performance,'now').mockImplementation(()=>elapsed);getFirstArrivals.mockReset();getFirstArrivals.mockResolvedValue(response());Object.defineProperty(document,'hidden',{configurable:true,value:false});});
afterEach(()=>{cleanup();vi.restoreAllMocks();vi.useRealTimers();});
it('labels receipt estimates without claiming freshness or departure',async()=>{
  await mount();expect(screen.getByText('수신 기준 예상')).toBeTruthy();expect(screen.getByText(/0초 전 조회/)).toBeTruthy();
  expect(screen.getByText(/약 5분 뒤/)).toBeTruthy();expect(screen.getByText(/원천 갱신 지연/)).toBeTruthy();expect(screen.getByText(/출발 시각은 아직/)).toBeTruthy();
});
it('counts down and removes passed predictions without another fetch',async()=>{
  getFirstArrivals.mockResolvedValue(response(30));await mount();elapsed=30000;
  await act(async()=>{vi.advanceTimersByTime(30000);});
  expect(screen.queryByText(/첫 차량/)).toBeNull();expect(screen.getByText(/이전 도착 예상이 지났/)).toBeTruthy();expect(getFirstArrivals).toHaveBeenCalledTimes(1);
});
it('refreshes after 60 seconds, failure cannot renew receipt or expiry',async()=>{
  await mount();getFirstArrivals.mockRejectedValue({code:'PROVIDER_TIMEOUT'});elapsed=60000;
  await act(async()=>{vi.advanceTimersByTime(60000);});expect(getFirstArrivals).toHaveBeenCalledTimes(2);expect(screen.getByText(/60초 전 조회/)).toBeTruthy();
  elapsed=120001;await act(async()=>{vi.advanceTimersByTime(61000);});expect(screen.getByText(/도착 정보가 만료/)).toBeTruthy();expect(screen.queryByText(/첫 차량/)).toBeNull();
});
it('stops hidden polling and refreshes on return',async()=>{
  await mount();Object.defineProperty(document,'hidden',{configurable:true,value:true});
  await act(async()=>{document.dispatchEvent(new Event('visibilitychange'));vi.advanceTimersByTime(60000);});expect(getFirstArrivals).toHaveBeenCalledTimes(1);
  Object.defineProperty(document,'hidden',{configurable:true,value:false});await act(async()=>{document.dispatchEvent(new Event('visibilitychange'));});expect(getFirstArrivals).toHaveBeenCalledTimes(2);
});
it('authentication or search failure immediately removes old numbers',async()=>{
  await mount();getFirstArrivals.mockRejectedValue({code:'AUTH_REQUIRED'});
  await act(async()=>{vi.advanceTimersByTime(60000);});expect(screen.queryByText(/첫 차량/)).toBeNull();expect(screen.getByText(/로그인 후/)).toBeTruthy();
  await act(async()=>{vi.advanceTimersByTime(60000);});expect(getFirstArrivals).toHaveBeenCalledTimes(2);
});
it('unmount aborts pending lookup and clears polling',async()=>{
  getFirstArrivals.mockImplementation(()=>new Promise(()=>{}));const page=render(<FirstArrivals searchId="search" candidateId="candidate"/>);
  const signal=getFirstArrivals.mock.calls[0][2];page.unmount();expect(signal.aborted).toBe(true);
  await act(async()=>{vi.advanceTimersByTime(60000);});expect(getFirstArrivals).toHaveBeenCalledTimes(1);
});
it.each(['mapping_required','unsupported','no_arrivals','insufficient_data'])('renders %s without numbers',async status=>{
  const value=response();value.data.status=status;value.data.valid_for_guidance=false;value.data.candidates=[];getFirstArrivals.mockResolvedValue(value);
  await mount();expect(screen.queryByText(/첫 차량/)).toBeNull();expect(screen.getByRole('status')).toBeTruthy();
});
