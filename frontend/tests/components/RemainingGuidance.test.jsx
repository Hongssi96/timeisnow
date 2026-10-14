import React from 'react';
import {render,screen,fireEvent,act,cleanup} from '@testing-library/react';
import {beforeEach,afterEach,expect,it,vi} from 'vitest';
import RemainingGuidance from '../../src/components/RemainingGuidance';
import {refreshRemaining,getRemaining} from '../../src/lib/remaining';
vi.mock('../../src/lib/remaining',()=>({refreshRemaining:vi.fn(),getRemaining:vi.fn()}));
vi.mock('../../src/components/OriginSelector',()=>({default:({onSelect,currentPointOnly})=><button onClick={()=>onSelect({origin:{type:'map_pin',latitude:37.5,longitude:127}})}>{currentPointOnly?'지금 위치 선택':'전체 위치 선택'}</button>}));
const trip={trip_id:'t',version:1};
function response(){return {data:{search_id:'s',status:'ready',valid_for_guidance:true,remaining_approach_seconds:120,slack_seconds:480,buffer_seconds:300,
 vehicle_arrival_at:new Date(Date.now()+600000).toISOString(),timing_basis:'receipt_estimate',connection_status:'unknown',target_evaluation:null},deadline:performance.now()+120000,serverMs:Date.now(),receivedMono:performance.now()};}
beforeEach(()=>{refreshRemaining.mockImplementation(async()=>{const r=response();getRemaining.mockResolvedValue(r);return r;});});
afterEach(()=>{cleanup();vi.resetAllMocks();vi.useRealTimers();Object.defineProperty(document,'visibilityState',{configurable:true,value:'visible'});});
async function open(){render(<RemainingGuidance trip={trip}/>);fireEvent.click(screen.getByText('첫 탑승 전 남은 경로 확인'));fireEvent.click(screen.getByText('지금 위치 선택'));}
async function start(){await open();fireEvent.click(screen.getByRole('checkbox'));await act(async()=>fireEvent.click(screen.getByText('남은 경로 조회')));}
it('requires current point and before boarding confirmation before the query',async()=>{
 await open();expect(screen.getByText('남은 경로 조회').disabled).toBe(true);expect(refreshRemaining).not.toHaveBeenCalled();
 fireEvent.click(screen.getByRole('checkbox'));await act(async()=>fireEvent.click(screen.getByText('남은 경로 조회')));
 expect(refreshRemaining.mock.calls[0][1].origin.type).toBe('map_pin');expect(screen.getByText('승차 지점까지 남은 도보 약 2분')).toBeTruthy();
 expect(screen.queryByText(/예상 출발/)).toBeNull();
});
it('clears numbers on failure and never keeps previous margin',async()=>{
 vi.useFakeTimers();await start();getRemaining.mockRejectedValue({code:'PROVIDER_UNAVAILABLE'});
 await act(async()=>vi.advanceTimersByTimeAsync(60000));expect(screen.queryByText(/예상 여유/)).toBeNull();expect(screen.getByRole('alert')).toBeTruthy();
});
it('expires confirmed point without automatically searching from original origin',async()=>{
 vi.useFakeTimers();await start();await act(async()=>vi.advanceTimersByTimeAsync(120000));
 expect(screen.queryByText(/예상 여유/)).toBeNull();expect(screen.getByText(/위치 확인 기한이 끝났어요/)).toBeTruthy();expect(refreshRemaining).toHaveBeenCalledTimes(1);
});
it('boarding or stopping aborts and removes all moving numbers',async()=>{
 await start();const signal=refreshRemaining.mock.calls[0][2];fireEvent.click(screen.getByText('탑승했거나 안내 멈추기'));
 expect(signal.aborted).toBe(true);expect(screen.queryByText(/예상 여유/)).toBeNull();
});
it('resetting position ignores a late query response',async()=>{
 let finish;refreshRemaining.mockImplementation(()=>new Promise(r=>finish=r));await open();fireEvent.click(screen.getByRole('checkbox'));fireEvent.click(screen.getByText('남은 경로 조회'));
 fireEvent.click(screen.getByText('현재 위치 다시 확인'));await act(async()=>finish(response()));expect(screen.queryByText(/예상 여유/)).toBeNull();expect(screen.getByText('지금 위치 선택')).toBeTruthy();
});
it('hidden in-flight query is aborted without restoring numbers on late completion',async()=>{
 let finish;refreshRemaining.mockImplementation(()=>new Promise(r=>finish=r));await open();fireEvent.click(screen.getByRole('checkbox'));fireEvent.click(screen.getByText('남은 경로 조회'));
 Object.defineProperty(document,'visibilityState',{configurable:true,value:'hidden'});fireEvent(document,new Event('visibilitychange'));
 await act(async()=>finish(response()));expect(refreshRemaining.mock.calls[0][2].aborted).toBe(true);expect(screen.queryByText(/예상 여유/)).toBeNull();
});
