import React from 'react';
import { afterEach, describe, expect, it, vi } from 'vitest';
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import LocationConfirmation from '../../src/components/LocationConfirmation';
import { apiRequest, ApiError } from '../../src/lib/api';
vi.mock('../../src/lib/api',async original=>({...await original(),apiRequest:vi.fn()}));
vi.mock('../../src/components/MapPinPicker',()=>({default:({onChange,disabled})=><button type="button" disabled={disabled} onClick={()=>onChange({latitude:37.5002,longitude:127})}>핀 옮기기</button>}));
afterEach(()=>vi.resetAllMocks());
const location={latitude:37.5,longitude:127};
const reply=(data)=>({data,meta:{server_time:new Date().toISOString()}});
function setup() {
  const callbacks={onDraft:vi.fn(),onConfirmed:vi.fn(),onAuthError:vi.fn()};
  const view=render(<LocationConfirmation initialLocation={location} {...callbacks}/>);
  return {...callbacks,...view,user:userEvent.setup()};
}
function confirmation(point=location,lifetime=600000) {
  return {confirmation_id:'confirm_test',location:point,location_address:'서울 합성동',expires_at:new Date(Date.now()+lifetime).toISOString()};
}
describe('핀 위치 확인',()=>{
  it('선택한 좌표를 POST하고 확인 결과를 전달한다',async()=>{
    const state=setup();apiRequest.mockResolvedValueOnce(reply({csrf_token:'csrf_test'})).mockResolvedValueOnce(reply(confirmation()));
    await state.user.click(screen.getByRole('button',{name:'핀 위치 확인'}));
    await screen.findByText(/핀 위치를 확인했어요/);
    expect(state.onConfirmed).toHaveBeenCalledWith(expect.objectContaining({confirmation_id:'confirm_test',location}));
    expect(apiRequest.mock.calls[1][1].body).toEqual({location});
    await state.user.click(screen.getByRole('button',{name:'핀 옮기기'}));
    expect(state.onConfirmed).toHaveBeenLastCalledWith(null);expect(state.onDraft).toHaveBeenCalledTimes(2);
  });
  it('지원지역 밖 오류와 세션 만료를 처리한다',async()=>{
    const state=setup();apiRequest.mockResolvedValueOnce(reply({csrf_token:'csrf_test'})).mockRejectedValueOnce(new ApiError('UNSUPPORTED_REGION'));
    await state.user.click(screen.getByRole('button',{name:'핀 위치 확인'}));
    expect(await screen.findByRole('alert')).toHaveProperty('textContent','서울·경기 안에서 위치를 선택해주세요.');
    expect(state.onConfirmed.mock.calls.every(([value]) => value === null)).toBe(true);
    apiRequest.mockRejectedValueOnce(new ApiError('SESSION_EXPIRED'));
    await state.user.click(screen.getByRole('button',{name:'핀 위치 확인'}));
    await screen.findByText('로그인이 만료됐어요. 다시 로그인해주세요.');
    expect(state.onAuthError).toHaveBeenCalledOnce();
  });
  it('기한이 지나면 저장 확인을 해제한다',async()=>{
    const state=setup();apiRequest.mockResolvedValueOnce(reply({csrf_token:'csrf_test'})).mockResolvedValueOnce(reply(confirmation(location,100)));
    await state.user.click(screen.getByRole('button',{name:'핀 위치 확인'}));
    await screen.findByText(/위치 확인이 만료됐어요/);
    expect(state.onConfirmed).toHaveBeenLastCalledWith(null);
  });
  it('다른 좌표 응답을 확인 성공으로 처리하지 않는다',async()=>{
    const state=setup();apiRequest.mockResolvedValueOnce(reply({csrf_token:'csrf_test'})).mockResolvedValueOnce(reply(confirmation({latitude:38,longitude:127})));
    await state.user.click(screen.getByRole('button',{name:'핀 위치 확인'}));
    await screen.findByRole('alert');expect(state.onConfirmed.mock.calls.every(([value]) => value === null)).toBe(true);
  });
  it('확인 요청 중 이탈하면 요청을 취소한다',async()=>{
    const state=setup();apiRequest.mockImplementation(()=>new Promise(()=>{}));
    await state.user.click(screen.getByRole('button',{name:'핀 위치 확인'}));
    expect(screen.getByRole('button',{name:'위치 확인 중…'}).disabled).toBe(true);
    state.unmount();expect(apiRequest.mock.calls[0][1].signal.aborted).toBe(true);
  });
});
