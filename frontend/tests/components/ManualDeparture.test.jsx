import React from 'react';
import {act,cleanup,fireEvent,render,screen} from '@testing-library/react';
import {afterEach,beforeEach,expect,it,vi} from 'vitest';
import ManualDeparture from '../../src/components/ManualDeparture';
import {activeTrip,confirmDeparture,cancelTrip} from '../../src/lib/trips';
vi.mock('../../src/lib/trips',()=>({activeTrip:vi.fn(),confirmDeparture:vi.fn(),cancelTrip:vi.fn()}));
const trip={trip_id:'t',guidance_id:'g',routine_id:'r',version:1,status:'active',departure_event:null};
beforeEach(()=>{activeTrip.mockResolvedValue(null);confirmDeparture.mockResolvedValue({...trip,departure_event:{event_id:'e'}});cancelTrip.mockResolvedValue({...trip,status:'cancelled'});});
afterEach(()=>{cleanup();vi.resetAllMocks();});
async function mount(props={}){const view=render(<ManualDeparture routineId="r" departure={{guidance_id:'g'}} available {...props}/>);await act(async()=>{});return view;}
it('waits for persisted departure before showing success and blocks double clicks',async()=>{
 let finish;confirmDeparture.mockImplementation(()=>new Promise(resolve=>finish=resolve));await mount();
 fireEvent.click(screen.getByText('지금 출발했어요'));fireEvent.click(screen.getByText('출발 확인 저장 중…'));
 expect(confirmDeparture).toHaveBeenCalledTimes(1);expect(screen.queryByText('출발 확인을 저장했어요.')).toBeNull();
 await act(async()=>finish({...trip,departure_event:{event_id:'e'}}));expect(screen.getByText('출발 확인을 저장했어요.')).toBeTruthy();
});
it('failed save preserves event id and occurrence time on retry',async()=>{
 confirmDeparture.mockRejectedValueOnce({code:'TIMEOUT'});await mount();await act(async()=>fireEvent.click(screen.getByText('지금 출발했어요')));
 const first=confirmDeparture.mock.calls[0][0];expect(screen.getByRole('alert')).toBeTruthy();
 await act(async()=>fireEvent.click(screen.getByText('지금 출발했어요')));expect(confirmDeparture.mock.calls[1][0]).toBe(first);expect(screen.getByText('출발 확인을 저장했어요.')).toBeTruthy();
});
it('unmount aborts the pending save',async()=>{
 confirmDeparture.mockImplementation(()=>new Promise(()=>{}));const view=await mount();fireEvent.click(screen.getByText('지금 출발했어요'));
 const signal=confirmDeparture.mock.calls[0][1];view.unmount();expect(signal.aborted).toBe(true);
});
it('recovers departed record even without a current valid guidance',async()=>{
 activeTrip.mockResolvedValue({...trip,departure_event:{event_id:'e'}});await mount({available:false,departure:null});
 expect(screen.getByText('출발 확인을 저장했어요.')).toBeTruthy();expect(screen.queryByText('지금 출발했어요')).toBeNull();
 await act(async()=>fireEvent.click(screen.getByText('이 이동 취소')));expect(cancelTrip).toHaveBeenCalledWith(expect.objectContaining({trip_id:'t'}),expect.any(AbortSignal));expect(screen.queryByText('출발 확인을 저장했어요.')).toBeNull();
});
it('no valid guidance cannot create a new session',async()=>{await mount({available:false});expect(screen.queryByText('지금 출발했어요')).toBeNull();});
it('cancelled guidance cannot start again until a fresh guidance token arrives',async()=>{
 activeTrip.mockResolvedValue({...trip,departure_event:{event_id:'e'}});const view=await mount();
 await act(async()=>fireEvent.click(screen.getByText('이 이동 취소')));expect(screen.queryByText('지금 출발했어요')).toBeNull();expect(screen.getByText(/최신 출발을 다시 확인하면/)).toBeTruthy();
 view.rerender(<ManualDeparture routineId="r" departure={{guidance_id:'fresh'}} available/>);expect(screen.getByText('지금 출발했어요')).toBeTruthy();
});
