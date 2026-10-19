import React from 'react';
import {beforeEach,afterEach,it,expect,vi} from 'vitest';
import {render,screen,fireEvent,waitFor,act,cleanup} from '@testing-library/react';
import ProfileSettingsCard from '../../src/components/ProfileSettingsCard';
import {getProfile,saveProfile} from '../../src/lib/profile';
vi.mock('../../src/lib/profile',()=>({getProfile:vi.fn(),saveProfile:vi.fn()}));
const profile={walking_preference:'normal',route_preference:'balanced',walking_duration_factor:1,first_boarding_buffer_seconds:301,transfer_buffer_seconds:120,timezone:'Asia/Seoul',version:1};
beforeEach(()=>{getProfile.mockReset();saveProfile.mockReset();getProfile.mockResolvedValue({owner:'member',profile:{...profile}});});
afterEach(cleanup);
async function mount(){const view=render(<ProfileSettingsCard onLogin={vi.fn()}/>);await screen.findByRole('button',{name:'설정 저장'});return view;}
const change=(label,value)=>fireEvent.change(screen.getByLabelText(label),{target:{value}});
it('loads exact seconds and explicitly saves changes, then restores server values on remount',async()=>{
 const view=await mount();expect(screen.getByLabelText('첫 탑승 여유 초').value).toBe('1');expect(screen.getByRole('button',{name:'설정 저장'}).disabled).toBe(true);
 change('첫 탑승 여유 분','0');change('첫 탑승 여유 초','0');change('환승 여유 초','59');
 const saved={...profile,version:2,first_boarding_buffer_seconds:0,transfer_buffer_seconds:179};saveProfile.mockResolvedValue(saved);
 fireEvent.click(screen.getByRole('button',{name:'설정 저장'}));await screen.findByText(/설정을 저장했어요/);
 expect(saveProfile).toHaveBeenCalledWith('member',1,{first_boarding_buffer_seconds:0,transfer_buffer_seconds:179},expect.any(AbortSignal));
 getProfile.mockResolvedValue({owner:'member',profile:saved});view.unmount();await mount();expect(screen.getByLabelText('환승 여유 초').value).toBe('59');
});
it('validates the complete 30 minute limit and prevents concurrent duplicate saves',async()=>{
 await mount();change('첫 탑승 여유 분','30');expect(screen.getByRole('button',{name:'설정 저장'}).disabled).toBe(true);change('첫 탑승 여유 초','0');
 let resolve;saveProfile.mockImplementation(()=>new Promise(r=>resolve=r));fireEvent.click(screen.getByRole('button',{name:'설정 저장'}));fireEvent.click(screen.getByRole('button',{name:'저장 중…'}));expect(saveProfile).toHaveBeenCalledTimes(1);
 await act(async()=>resolve({...profile,version:2,first_boarding_buffer_seconds:1800}));
});
it('preserves a failed draft and requires fresh settings after a version conflict',async()=>{
 await mount();change('환승 여유 분','3');saveProfile.mockRejectedValue({code:'NETWORK_ERROR'});fireEvent.click(screen.getByRole('button',{name:'설정 저장'}));await screen.findByRole('alert');expect(screen.getByLabelText('환승 여유 분').value).toBe('3');
 saveProfile.mockRejectedValue({code:'VERSION_CONFLICT'});fireEvent.click(screen.getByRole('button',{name:'설정 저장'}));await screen.findByRole('button',{name:'최신 설정 불러오기'});
 getProfile.mockResolvedValue({owner:'member',profile:{...profile,version:2,transfer_buffer_seconds:240}});fireEvent.click(screen.getByRole('button',{name:'최신 설정 불러오기'}));await waitFor(()=>expect(screen.getByLabelText('환승 여유 분').value).toBe('4'));
});
it('clears private form values when the authenticated account changes',async()=>{
 await mount();change('보행 선호','slow');saveProfile.mockRejectedValue({code:'SESSION_CHANGED'});fireEvent.click(screen.getByRole('button',{name:'설정 저장'}));await screen.findByText(/로그인 계정이 바뀌었어요/);expect(screen.queryByLabelText('보행 선호')).toBeNull();
});
it('announces authentication expiry and offers login rather than retaining form state',async()=>{
 await mount();change('보행 선호','fast');saveProfile.mockRejectedValue({code:'SESSION_EXPIRED'});fireEvent.click(screen.getByRole('button',{name:'설정 저장'}));await screen.findByRole('button',{name:'로그인하기'});expect(screen.queryByLabelText('첫 탑승 여유 분')).toBeNull();
});
it('aborts an in-flight save on leaving settings and ignores its late result',async()=>{
 const view=await mount();change('보행 선호','slow');let resolve;saveProfile.mockImplementation(()=>new Promise(r=>resolve=r));fireEvent.click(screen.getByRole('button',{name:'설정 저장'}));const signal=saveProfile.mock.calls[0][3];view.unmount();expect(signal.aborted).toBe(true);await act(async()=>resolve({...profile,version:2,walking_preference:'slow'}));expect(screen.queryByText(/설정을 저장했어요/)).toBeNull();
});
