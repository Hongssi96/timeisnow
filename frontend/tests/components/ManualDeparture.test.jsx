import React from 'react';
import {act,cleanup,fireEvent,render,screen} from '@testing-library/react';
import {afterEach,beforeEach,expect,it,vi} from 'vitest';
import ManualDeparture from '../../src/components/ManualDeparture';
vi.mock('../../src/components/SegmentWalking',()=>({default:()=>null}));
import {activeTrip,confirmDeparture,confirmProgress,cancelTrip} from '../../src/lib/trips';
vi.mock('../../src/lib/trips',()=>({activeTrip:vi.fn(),confirmDeparture:vi.fn(),confirmProgress:vi.fn(),cancelTrip:vi.fn()}));
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

it('server reported state refreshes manual recovery without creating another event',async()=>{
 const view=await mount();activeTrip.mockResolvedValue({...trip,departure_event:{event_id:'e'}});
 view.rerender(<ManualDeparture routineId="r" departure={{departure_state:'reported_departed',guidance_id:null}} available={false}/>);await act(async()=>{});
 expect(screen.getByText('출발 확인을 저장했어요.')).toBeTruthy();expect(confirmDeparture).not.toHaveBeenCalled();expect(activeTrip).toHaveBeenCalledTimes(2);
});
it('records approach then boarding and restores persisted progress',async()=>{
 const departed={...trip,departure_event:{event_id:'e'}};
 activeTrip.mockResolvedValue(departed);confirmProgress.mockResolvedValueOnce({...departed,approach_event:{event_id:'a'}}).mockResolvedValueOnce({...departed,approach_event:{event_id:'a'},boarding_event:{event_id:'b'}});
 await mount();await act(async()=>fireEvent.click(screen.getByText('정류장에 도착했어요')));
 expect(screen.getByText('정류장 도착 확인을 저장했어요.')).toBeTruthy();expect(screen.queryByText('첫 탑승 전 남은 경로 확인')).toBeNull();
 await act(async()=>fireEvent.click(screen.getByText('탑승했어요')));
 expect(screen.getByText(/탑승 확인을 저장했어요/)).toBeTruthy();expect(screen.queryByText('탑승했어요')).toBeNull();
 expect(confirmProgress.mock.calls.map(([op])=>op.type)).toEqual(['approach_arrived','boarded']);
});
it('uncertain boarding hides guidance and retries the same operation',async()=>{
 activeTrip.mockResolvedValue({...trip,departure_event:{event_id:'e'}});confirmProgress.mockRejectedValueOnce({code:'TIMEOUT'});
 await mount();await act(async()=>fireEvent.click(screen.getByText('탑승했어요')));
 const first=confirmProgress.mock.calls[0][0];expect(screen.getByText('정류장에 도착했어요').disabled).toBe(true);
 expect(screen.queryByText('첫 탑승 전 남은 경로 확인')).toBeNull();
 confirmProgress.mockResolvedValue({...trip,departure_event:{event_id:'e'},boarding_event:{event_id:'b'}});
 await act(async()=>fireEvent.click(screen.getByText('탑승했어요')));expect(confirmProgress.mock.calls[1][0]).toBe(first);
});
const stageTrip=(stage,actions,anchor='a')=>({...trip,departure_event:{event_id:'e'},boarding_event:{event_id:'b'},progress:{stage,actions,anchor_event_id:anchor,vehicle_name:'20번',boarding_stop:'환승 정류장',alighting_stop:'다음 하차'}});
it('onboard state has no invented ETA and alighting opens confirmed transfer guidance',async()=>{
 activeTrip.mockResolvedValue(stageTrip('onboard',{alighted:'bus1'}));
 confirmProgress.mockResolvedValue(stageTrip('transfer',{approach_arrived:'w2',boarded:'bus2'},'alight'));
 await mount();expect(screen.getByText(/탑승한 차량번호를 확인하면/)).toBeTruthy();
 expect(screen.queryByText('환승 중 남은 경로 확인')).toBeNull();
 await act(async()=>fireEvent.click(screen.getByText('이 차량에서 내렸어요')));
 expect(confirmProgress.mock.calls[0][0].type).toBe('alighted');
 expect(screen.getByText('환승 중 남은 경로 확인')).toBeTruthy();expect(screen.getByText('이 차량에 탑승했어요')).toBeTruthy();
});
it('saved final alighting does not claim destination arrival',async()=>{
 activeTrip.mockResolvedValue(stageTrip('transit_finished',{}));await mount();
 expect(screen.getByText(/목적지까지 이동한 뒤 도착을 직접 확인/)).toBeTruthy();expect(screen.queryByText('이 차량에 탑승했어요')).toBeNull();
});
it('saves explicit destination arrival then shows completed recovery and fresh-start action',async()=>{
 const before=stageTrip('transit_finished',{arrived:'last-walk'});activeTrip.mockResolvedValue(before);
 confirmProgress.mockResolvedValue({...before,status:'completed',version:2,progress:{...before.progress,stage:'completed',actions:{}}});
 const onCancelled=vi.fn();await mount({onCancelled});
 await act(async()=>fireEvent.click(screen.getByText('목적지에 도착했어요')));
 expect(confirmProgress.mock.calls[0][0].type).toBe('arrived');expect(screen.getByText(/이동을 완료했어요/)).toBeTruthy();
 expect(screen.queryByText('이 이동 취소')).toBeNull();
 fireEvent.click(screen.getByText('새 이동 준비'));expect(onCancelled).toHaveBeenCalledTimes(1);
});
it('missed save failure hides remaining numbers and retries the same terminal report',async()=>{
 const before=stageTrip('transfer',{boarded:'bus2',missed:'bus2'});activeTrip.mockResolvedValue(before);
 confirmProgress.mockRejectedValueOnce({code:'TIMEOUT'});await mount();
 await act(async()=>fireEvent.click(screen.getByText('놓침을 기록하고 이동 종료')));
 const pending=confirmProgress.mock.calls[0][0];expect(screen.queryByText('환승 중 남은 경로 확인')).toBeNull();
 expect(screen.getByText('이 차량에 탑승했어요').disabled).toBe(true);
 confirmProgress.mockResolvedValue({...before,status:'missed',version:2,progress:{...before.progress,stage:'missed',actions:{}}});
 await act(async()=>fireEvent.click(screen.getByText('놓침을 기록하고 이동 종료')));
 expect(confirmProgress.mock.calls[1][0]).toBe(pending);expect(screen.getByText(/이번 이동을 종료했어요/)).toBeTruthy();
});
it('preparing a new trip prevents polling from restoring the dismissed old completion',async()=>{
 vi.useFakeTimers();
 const saved={...stageTrip('completed',{}),status:'completed'};activeTrip.mockResolvedValue(saved);
 const view=await mount();fireEvent.click(screen.getByText('새 이동 준비'));
 view.rerender(<ManualDeparture routineId="r" departure={{guidance_id:'fresh'}} available/>);
 await act(async()=>vi.advanceTimersByTimeAsync(60000));
 expect(screen.queryByText(/이동을 완료했어요/)).toBeNull();expect(screen.getByText('지금 출발했어요')).toBeTruthy();
 vi.useRealTimers();
});
it('a concurrent cancellation recovered during a terminal retry clears the old active view',async()=>{
 const before=stageTrip('transfer',{missed:'bus2'});activeTrip.mockResolvedValue(before);
 confirmProgress.mockResolvedValue({...before,status:'cancelled',version:2});const onCancelled=vi.fn();
 await mount({onCancelled});await act(async()=>fireEvent.click(screen.getByText('놓침을 기록하고 이동 종료')));
 expect(screen.queryByText(/다음 차량:/)).toBeNull();expect(screen.queryByText('놓침을 기록하고 이동 종료')).toBeNull();expect(onCancelled).toHaveBeenCalledTimes(1);
});
