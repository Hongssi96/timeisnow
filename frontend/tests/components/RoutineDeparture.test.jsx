import React from 'react';
import {render,screen,act,cleanup,fireEvent} from '@testing-library/react';
import {afterEach,beforeEach,it,expect,vi} from 'vitest';
import RoutineDeparture from '../../src/components/RoutineDeparture';
import {refreshRoutine,getRoutineDeparture} from '../../src/lib/routineDeparture';
vi.mock('../../src/lib/routineDeparture',()=>({refreshRoutine:vi.fn(),getRoutineDeparture:vi.fn(),routineDepartureError:()=> '최신 안내 실패'}));
vi.mock('../../src/components/FirstArrivals',()=>({default:({initialResponse,onReported,onCancelled})=><><p>예상 출발 {initialResponse.data.selected_departure_at}</p><button onClick={onReported}>합성 출발 확인</button><button onClick={onCancelled}>합성 이동 취소</button></>}));
const routine={routine_id:'r1',version:1,status:'active',origin_place:{place_id:'p1'},destination_place:{place_id:'p2'}};
const value=(id='s1')=>({search:{search_id:id,deadline:Date.now()+300000},response:{meta:{server_time:new Date().toISOString()},data:{status:'ready',candidate_id:'c1',departure:{selected_departure_at:id}}}});
beforeEach(()=>{vi.useFakeTimers();refreshRoutine.mockReset();getRoutineDeparture.mockReset();Object.defineProperty(document,'hidden',{configurable:true,value:false});refreshRoutine.mockResolvedValue(value());});
afterEach(()=>{cleanup();vi.useRealTimers();});
async function mount(r=routine){const view=render(<RoutineDeparture key={r.routine_id+':'+r.version} routine={r} onRouteChange={()=>{}}/>);await act(async()=>{});return view;}
it('selecting routine shows fresh response instead of stored duration',async()=>{await mount();expect(screen.getByText('예상 출발 s1')).toBeTruthy();expect(refreshRoutine).toHaveBeenCalledTimes(1);});
it('search expires and refreshes route instead of extending stale search',async()=>{await mount();refreshRoutine.mockResolvedValue(value('s2'));await act(async()=>{vi.advanceTimersByTime(300000);});expect(screen.getByText('예상 출발 s2')).toBeTruthy();expect(refreshRoutine).toHaveBeenCalledTimes(2);});
it('manual refresh immediately removes old numbers and allows recovery after error',async()=>{await mount();refreshRoutine.mockRejectedValue({code:'TIMEOUT'});await act(async()=>{fireEvent.click(screen.getByText('최신 출발 다시 확인'));});expect(screen.queryByText('예상 출발 s1')).toBeNull();expect(screen.getByRole('alert')).toBeTruthy();refreshRoutine.mockResolvedValue(value('s3'));await act(async()=>{fireEvent.click(screen.getByText('최신 출발 다시 확인'));});expect(screen.getByText('예상 출발 s3')).toBeTruthy();});
it('ambiguous or changed route has no departure and provides explicit route selection',async()=>{const change=vi.fn();const v=value();v.response.data={status:'ambiguous_route',candidate_id:null,departure:null};refreshRoutine.mockResolvedValue(v);render(<RoutineDeparture routine={routine} onRouteChange={change}/>);await act(async()=>{});expect(screen.queryByText(/예상 출발 s/)).toBeNull();fireEvent.click(screen.getByText('경로 다시 선택'));expect(change).toHaveBeenCalledWith(routine);});
it('recovery routine never makes route or arrival request',async()=>{await mount({...routine,status:'needs_attention'});expect(refreshRoutine).not.toHaveBeenCalled();expect(screen.getByText(/루틴을 복구한 뒤/)).toBeTruthy();});
it('hidden expiry defers fresh search until returning',async()=>{await mount();Object.defineProperty(document,'hidden',{value:true});await act(async()=>{document.dispatchEvent(new Event('visibilitychange'));vi.advanceTimersByTime(300000);});expect(refreshRoutine).toHaveBeenCalledTimes(1);expect(screen.queryByText('예상 출발 s1')).toBeNull();Object.defineProperty(document,'hidden',{value:false});await act(async()=>{document.dispatchEvent(new Event('visibilitychange'));});expect(refreshRoutine).toHaveBeenCalledTimes(2);});
it('switching routine cancels request and ignores its late response',async()=>{let resolve;refreshRoutine.mockImplementationOnce(()=>new Promise(r=>resolve=r));const view=await mount();const signal=refreshRoutine.mock.calls[0][1];view.rerender(<RoutineDeparture key="r2:1" routine={{...routine,routine_id:'r2'}} onRouteChange={()=>{}}/>);await act(async()=>{resolve(value('old'));});expect(signal.aborted).toBe(true);expect(screen.queryByText('예상 출발 old')).toBeNull();});
it('failure does not trigger endless retries on visibility changes',async()=>{refreshRoutine.mockRejectedValue({code:'RATE_LIMITED'});await mount();await act(async()=>{document.dispatchEvent(new Event('visibilitychange'));vi.advanceTimersByTime(600000);});expect(refreshRoutine).toHaveBeenCalledTimes(1);});

it('confirmed departure stops search expiry refresh and cancellation starts a fresh query',async()=>{
 await mount();fireEvent.click(screen.getByText('합성 출발 확인'));await act(async()=>{vi.advanceTimersByTime(300000);});expect(refreshRoutine).toHaveBeenCalledTimes(1);
 refreshRoutine.mockResolvedValue(value('s2'));await act(async()=>{fireEvent.click(screen.getByText('합성 이동 취소'));});expect(refreshRoutine).toHaveBeenCalledTimes(2);expect(screen.getByText('예상 출발 s2')).toBeTruthy();
});
