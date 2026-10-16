import React from 'react';
import {afterEach,expect,it,vi} from 'vitest';
import {render,screen,waitFor,cleanup} from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import PersonalizationCard from '../../src/components/PersonalizationCard';
import WalkingObservation from '../../src/components/WalkingObservation';
import {personalization,changePersonalization,learnWalking} from '../../src/lib/personalization';
vi.mock('../../src/lib/personalization',()=>({personalization:vi.fn(),changePersonalization:vi.fn(),learnWalking:vi.fn()}));
const value={status:'learning',profile_version:1,factors:[{type:'provider_mapped_access',value:1}],sample_counts:{valid:4,excluded:2},quality:{sample_count:4,baseline_mae_seconds:80,personalized_mae_seconds:60},can_restore:false};
afterEach(()=>{cleanup();vi.resetAllMocks();});
it('실제 집계와 계수를 표시하고 명시 확인 후에만 초기화한다',async()=>{
 personalization.mockResolvedValue(value);changePersonalization.mockResolvedValue({...value,profile_version:2,sample_counts:{valid:0,excluded:0}});
 render(<PersonalizationCard/>);await screen.findByText('4 / 5개');expect(screen.getByText('1.000배')).toBeTruthy();
 await userEvent.click(screen.getByRole('button',{name:'학습 초기화'}));expect(changePersonalization).not.toHaveBeenCalled();
 await userEvent.click(screen.getByRole('button',{name:'확인하고 적용'}));await screen.findByText(/계수를 초기화했어요/);
 expect(changePersonalization.mock.calls[0][1]).toMatchObject({expected_version:1});await screen.findByText('0 / 5개');
});
it('로그인과 실패 상태에 가짜 0개를 표시하지 않는다',async()=>{
 personalization.mockRejectedValue({code:'AUTH_REQUIRED'});render(<PersonalizationCard/>);
 await screen.findByText(/로그인하면 내 걸음/);expect(screen.queryByText('0 / 5개')).toBeNull();
});
it('저장 재시도에 같은 키와 버전을 유지한다',async()=>{
 personalization.mockResolvedValue(value);changePersonalization.mockRejectedValueOnce({code:'NETWORK_ERROR'}).mockResolvedValueOnce(value);
 render(<PersonalizationCard/>);await screen.findByText('4 / 5개');await userEvent.click(screen.getByRole('button',{name:'학습 초기화'}));
 await userEvent.click(screen.getByRole('button',{name:'확인하고 적용'}));await screen.findByRole('alert');
 await userEvent.click(screen.getByRole('button',{name:'확인하고 적용'}));await waitFor(()=>expect(changePersonalization).toHaveBeenCalledTimes(2));
 expect(changePersonalization.mock.calls[0][1]).toEqual(changePersonalization.mock.calls[1][1]);
});
it('구간 일치와 이동 상태만 전송하고 서버 판정을 표시한다',async()=>{
 learnWalking.mockResolvedValue({status:'valid',updated:true,sample_count:5,exclusion_reasons:[]});
 render(<WalkingObservation trip={{trip_id:'owned-trip'}}/>);await userEvent.click(screen.getByRole('checkbox'));
 await userEvent.click(screen.getByRole('button',{name:'보행 기록 확인하고 반영'}));await screen.findByText(/개인 계수를 갱신했어요/);
 expect(learnWalking.mock.calls[0].slice(0,2)).toEqual(['owned-trip',{same_scope:true,condition:'normal'}]);
});
it('늦은 입력은 제외 사유로 표시하고 실패 재시도 내용을 고정한다',async()=>{
 learnWalking.mockRejectedValueOnce({code:'NETWORK_ERROR'}).mockResolvedValueOnce({status:'excluded',updated:false,exclusion_reasons:['LATE_INPUT']});
 render(<WalkingObservation trip={{trip_id:'owned-trip'}}/>);await userEvent.selectOptions(screen.getByRole('combobox'),'late_input');
 await userEvent.click(screen.getByRole('button',{name:'보행 기록 확인하고 반영'}));await screen.findByRole('alert');expect(screen.getByRole('combobox').disabled).toBe(true);
 await userEvent.click(screen.getByRole('button',{name:'보행 기록 확인하고 반영'}));await screen.findByText(/학습 제외: 늦은 버튼 입력/);
 expect(learnWalking.mock.calls[0][1]).toEqual(learnWalking.mock.calls[1][1]);
});
