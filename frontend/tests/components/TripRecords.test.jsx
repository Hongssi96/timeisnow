import React from 'react';
import {afterEach,expect,it,vi} from 'vitest';
import {cleanup,render,screen,waitFor,fireEvent} from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import TripRecords from '../../src/components/TripRecords';
import {records,record,observation,mutateRecord} from '../../src/lib/tripRecords';
vi.mock('../../src/lib/tripRecords',()=>({records:vi.fn(),record:vi.fn(),observation:vi.fn(),mutateRecord:vi.fn()}));
const trip={trip_id:'trip',created_at:'2026-10-16T01:00:00Z',status:'cancelled',version:2};
const event={event_id:'event',type:'approach_arrived',occurred_at:'2026-10-16T01:05:00Z',version:1,excluded:false};
const detail={trip,events:[event],corrections:[]};
const walk={observation_id:'observation',status:'valid',version:1,confirmation:{same_scope:true,condition:'normal'}};
const result={personalization:{factors:[{value:1}],sample_counts:{valid:4}}};
afterEach(()=>{cleanup();vi.resetAllMocks();});
async function mount(status='cancelled'){
 records.mockResolvedValue({items:[{...trip,status}],next_cursor:null});record.mockResolvedValue({...detail,trip:{...trip,status}});observation.mockResolvedValue(walk);
 render(<TripRecords onLogin={vi.fn()}/>);await screen.findByText(/본인 수동 기록/);await userEvent.click(screen.getByText(/본인 수동 기록/));await screen.findByRole('button',{name:'승차 지점 도착 기록 정정'});
}
it('정정과 학습 제외를 저장하고 갱신된 계수/표본 수를 표시한다',async()=>{
 await mount();mutateRecord.mockResolvedValue(result);await userEvent.click(screen.getByRole('button',{name:'승차 지점 도착 기록 정정'}));await userEvent.click(screen.getByRole('checkbox'));
 await userEvent.click(screen.getByRole('button',{name:'기록 정정하고 재학습'}));await screen.findByText(/현재 시간 계수 1.000배 · 유효 기록 4개/);
 expect(mutateRecord.mock.calls[0][0]).toMatchObject({kind:'event',eventId:'event',body:{expected_version:1,excluded:true}});
});
it('삭제 확인 전에는 요청하지 않고 실패 후 같은 UUID로 재시도한다',async()=>{
 await mount();mutateRecord.mockRejectedValueOnce({code:'TIMEOUT'}).mockResolvedValueOnce(result);
 await userEvent.click(screen.getByRole('button',{name:'이 이동 기록 삭제'}));expect(mutateRecord).not.toHaveBeenCalled();await userEvent.click(screen.getByRole('button',{name:'삭제하고 재학습'}));await screen.findByRole('alert');
 await userEvent.click(screen.getByRole('button',{name:'삭제하고 재학습'}));await screen.findByText(/이동 기록을 삭제했어요/);
 expect(mutateRecord.mock.calls[0][0]).toEqual(mutateRecord.mock.calls[1][0]);
});
it('진행 중인 이동의 정정은 차단하고 조건 정정도 관측 버전으로 보낸다',async()=>{
 await mount('active');expect(screen.getByRole('button',{name:'승차 지점 도착 기록 정정'}).disabled).toBe(true);
});
it('보행 조건 정정에 기준초나 계수를 보내지 않는다',async()=>{
 await mount();mutateRecord.mockResolvedValue(result);await userEvent.click(screen.getByRole('button',{name:'보행 조건 정정'}));await userEvent.selectOptions(screen.getByRole('combobox'),'running');
 await userEvent.click(screen.getByRole('button',{name:'보행 조건 정정하고 재학습'}));await screen.findByText(/정정을 저장했어요/);
 expect(mutateRecord.mock.calls[0][0].body).toEqual({client_request_id:expect.any(String),expected_version:1,same_scope:true,condition:'running'});
});
it('로그인/조회 실패에 가짜 빈 기록을 표시하지 않는다',async()=>{
 records.mockRejectedValue({code:'AUTH_REQUIRED'});render(<TripRecords onLogin={vi.fn()}/>);await screen.findByRole('button',{name:'로그인하고 기록 확인'});expect(screen.queryByText(/저장된 이동 기록이 없어요/)).toBeNull();
});
it('요청 중 중복 제출을 막고 화면을 떠나면 취소한다',async()=>{
 await mount();let signal;mutateRecord.mockImplementation((o,s)=>{signal=s;return new Promise(()=>{});});
 await userEvent.click(screen.getByRole('button',{name:'이 이동 기록 삭제'}));const button=screen.getByRole('button',{name:'삭제하고 재학습'});
 fireEvent.click(button);fireEvent.click(button);await waitFor(()=>expect(mutateRecord).toHaveBeenCalledTimes(1));expect(button.disabled).toBe(true);cleanup();expect(signal.aborted).toBe(true);
});
