import React from 'react';
import {afterEach,expect,it,vi} from 'vitest';
import {render,screen,cleanup} from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import TripExport from '../../src/components/TripExport';
import {exportRecords} from '../../src/lib/tripExports';
vi.mock('../../src/lib/tripExports',()=>({exportRecords:vi.fn()}));
afterEach(()=>{cleanup();vi.resetAllMocks();});
it('선택한 기간을 내려받고 빈 결과를 안내한다',async()=>{
 exportRecords.mockResolvedValue(0);render(<TripExport/>);
 await userEvent.selectOptions(screen.getByRole('combobox'),'7');
 await userEvent.click(screen.getByRole('button',{name:'JSON 다운로드'}));
 expect(exportRecords.mock.calls[0][0]).toBe('7');await screen.findByText(/0개 기록.*저장된 기록이 없어요/);
});
it('진행 중 중복 전송을 막고 이탈 시 취소한다',async()=>{
 exportRecords.mockImplementation(()=>new Promise(()=>{}));const view=render(<TripExport/>);
 await userEvent.click(screen.getByRole('button',{name:'JSON 다운로드'}));
 expect(screen.getByRole('button',{name:'파일 준비 중…'}).disabled).toBe(true);
 const signal=exportRecords.mock.calls[0][1];view.unmount();expect(signal.aborted).toBe(true);
});
it('실패 후 재시도와 로그인 안내를 제공한다',async()=>{
 const login=vi.fn();exportRecords.mockRejectedValueOnce({code:'AUTH_REQUIRED'}).mockResolvedValueOnce(2);
 render(<TripExport onLogin={login}/>);await userEvent.click(screen.getByRole('button',{name:'JSON 다운로드'}));
 await screen.findByRole('alert');await userEvent.click(screen.getByRole('button',{name:'로그인'}));expect(login).toHaveBeenCalledOnce();
 await userEvent.click(screen.getByRole('button',{name:'JSON 다운로드'}));await screen.findByText(/2개 기록/);
});
