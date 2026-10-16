import React from 'react';
import {render,screen,fireEvent,act,cleanup} from '@testing-library/react';
import {it,expect,vi,beforeEach,afterEach} from 'vitest';
import OnboardGuidance from '../../src/components/OnboardGuidance';
import {confirmOnboard,getOnboard} from '../../src/lib/onboard';
vi.mock('../../src/lib/onboard',()=>({confirmOnboard:vi.fn(),getOnboard:vi.fn()}));
const trip={trip_id:'t',version:1,progress:{stage:'onboard',current_leg_id:'bus',anchor_event_id:'e',vehicle_name:'20번',alighting_stop:'종점'}};
const reply=()=>({data:{status:'estimated',remaining_seconds:600,estimated_alighting_at:new Date(Date.now()+600000).toISOString()},serverMs:Date.now(),receivedMono:performance.now(),deadline:performance.now()+120000});
beforeEach(()=>{vi.useFakeTimers();confirmOnboard.mockReset();getOnboard.mockReset();Object.defineProperty(document,'visibilityState',{configurable:true,value:'visible'});});
afterEach(()=>{cleanup();vi.useRealTimers();});
async function apply(){fireEvent.change(screen.getByLabelText('탑승한 버스 차량번호 뒤 4자리'),{target:{value:'1234'}});await act(async()=>{fireEvent.click(screen.getByText('차량 확인하고 하차 예상 보기'));});}
it('does not infer a vehicle and explicitly applies only confirmed prediction',async()=>{
 confirmOnboard.mockResolvedValue(reply());render(<OnboardGuidance trip={trip}/>);expect(getOnboard).not.toHaveBeenCalled();expect(confirmOnboard).not.toHaveBeenCalled();
 await apply();expect(screen.getByText(/하차 정류소까지 약 10분/)).toBeTruthy();expect(confirmOnboard.mock.calls[0][1]).toBe('1234');
});
it('hides old numbers during failure/expiry and aborts late result after unmount',async()=>{
 confirmOnboard.mockResolvedValue(reply());const view=render(<OnboardGuidance trip={trip}/>);await apply();
 getOnboard.mockRejectedValue({code:'PROVIDER_UNAVAILABLE'});await act(async()=>{fireEvent.click(screen.getByText('차량 정보 다시 확인'));});expect(screen.queryByText(/하차 정류소까지 약/)).toBeNull();expect(screen.getByRole('alert')).toBeTruthy();
 let resolve;confirmOnboard.mockImplementation(()=>new Promise(r=>resolve=r));await apply();const signal=confirmOnboard.mock.calls.at(-1)[2];view.unmount();await act(async()=>{resolve(reply());});expect(signal.aborted).toBe(true);
});
it('expires using monotonic deadline and stops display while hidden',async()=>{
 const r=reply();r.deadline=performance.now()+1000;confirmOnboard.mockResolvedValue(r);render(<OnboardGuidance trip={trip}/>);await apply();
 await act(async()=>{vi.advanceTimersByTime(1000);});expect(screen.queryByText(/하차 정류소까지 약/)).toBeNull();
 Object.defineProperty(document,'visibilityState',{value:'hidden'});await act(async()=>document.dispatchEvent(new Event('visibilitychange')));expect(screen.queryByText(/하차 정류소까지 약/)).toBeNull();
});
it('revisiting restores the existing server confirmation without resubmitting a vehicle number',async()=>{
 getOnboard.mockResolvedValue(reply());render(<OnboardGuidance trip={trip}/>);
 await act(async()=>{fireEvent.click(screen.getByText('차량 정보 다시 확인'));});
 expect(screen.getByText(/하차 정류소까지 약 10분/)).toBeTruthy();expect(getOnboard).toHaveBeenCalledTimes(1);expect(confirmOnboard).not.toHaveBeenCalled();
});
