import React from 'react';
import { afterEach, describe, expect, it, vi } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import PlacesCard from './PlacesCard';
import { apiRequest, ApiError } from './api';
vi.mock('./api', async original => ({ ...await original(), apiRequest: vi.fn() }));
afterEach(() => vi.resetAllMocks());
const reply = data => ({ data, meta: { request_id:'req_test', server_time: new Date().toISOString() } });
const item = { candidate_id:'c_test', name:'합성 역', address:'서울 합성 주소', location:{latitude:37.5, longitude:127} };
const place = { ...item, place_id:'p_test', label:'집' };
async function open() {
  apiRequest.mockResolvedValueOnce(reply({items:[], next_cursor:null}));
  render(<PlacesCard onLogin={vi.fn()}/>);
  await screen.findByText(/아직 저장한 장소/);
  const user = userEvent.setup(); await user.click(screen.getByRole('button', {name:'장소 추가'}));
  return user;
}
async function search(user, candidates = [item], lifetime = 600000) {
  await user.type(screen.getByLabelText('주소 또는 장소 이름'), '합성');
  apiRequest.mockResolvedValueOnce(reply({csrf_token:'csrf_test'})).mockResolvedValueOnce(reply({search_id:'s_test', expires_at: new Date(Date.now()+lifetime).toISOString(), candidates}));
  await user.click(screen.getByRole('button', {name:'주소 검색'}));
}
describe('장소 검색과 저장', () => {
  it('로그인 누락 안내와 로그인 행동을 제공한다', async () => {
    const login = vi.fn(); apiRequest.mockRejectedValueOnce(new ApiError('AUTH_REQUIRED'));
    render(<PlacesCard onLogin={login}/>);
    const button = await screen.findByRole('button',{name:'로그인하고 장소 저장'});
    await userEvent.click(button); expect(login).toHaveBeenCalledOnce();
    expect(screen.queryByLabelText('주소 또는 장소 이름')).toBeNull();
  });
  it('선택한 후보를 저장하고 실제 장소를 표시한다', async () => {
    const user = await open(); await search(user);
    await user.click(await screen.findByRole('button',{name:/합성 역.*서울 합성 주소/}));
    apiRequest.mockResolvedValueOnce(reply({csrf_token:'csrf_test'})).mockResolvedValueOnce(reply(place));
    await user.click(screen.getByRole('button',{name:'선택한 장소 저장'}));
    expect(await screen.findByText('장소를 저장했어요.')).toBeTruthy();
    expect(screen.getByText('서울 합성 주소')).toBeTruthy();
    const saved = apiRequest.mock.calls.find(([path, options]) => path === '/api/v1/places' && options?.method === 'POST');
    expect(saved[1].body).toEqual({label:'집', location:item.location, search_id:'s_test', candidate_id:'c_test'});
    expect(saved[1].headers['Idempotency-Key']).toBeTruthy();
  });
  it('검색 실패와 빈 결과를 구분한다', async () => {
    const user = await open(); await search(user, []);
    expect(await screen.findByText(/검색 결과가 없어요/)).toBeTruthy();
    apiRequest.mockResolvedValueOnce(reply({csrf_token:'csrf_test'})).mockRejectedValueOnce(new ApiError('PROVIDER_UNAVAILABLE'));
    await user.click(screen.getByRole('button',{name:'주소 검색'}));
    expect(await screen.findByRole('alert')).toHaveProperty('textContent', expect.stringContaining('장소 검색에 연결할 수 없어요'));
  });
  it('만료된 결과에서 저장을 제공하지 않는다', async () => {
    const user = await open(); await search(user, [item], -1000);
    expect(await screen.findByText(/검색 결과가 만료됐어요/)).toBeTruthy();
    expect(screen.queryByRole('button',{name:'선택한 장소 저장'})).toBeNull();
  });
  it('검색어를 변경하면 선택한 후보를 제거한다', async () => {
    const user = await open(); await search(user);
    await user.click(await screen.findByRole('button',{name:/합성 역.*서울 합성 주소/}));
    await user.type(screen.getByLabelText('주소 또는 장소 이름'),'역');
    expect(screen.queryByRole('button',{name:'선택한 장소 저장'})).toBeNull();
  });
  it('응답을 받지 못한 저장 재시도에 같은 멱등 키를 사용한다', async () => {
    const user = await open(); await search(user);
    await user.click(await screen.findByRole('button',{name:/합성 역.*서울 합성 주소/}));
    apiRequest.mockResolvedValueOnce(reply({csrf_token:'csrf_test'})).mockRejectedValueOnce(new ApiError('NETWORK_ERROR'));
    await user.click(screen.getByRole('button',{name:'선택한 장소 저장'}));
    await screen.findByRole('alert');
    apiRequest.mockResolvedValueOnce(reply({csrf_token:'csrf_test'})).mockResolvedValueOnce(reply(place));
    await user.click(screen.getByRole('button',{name:'선택한 장소 저장'}));
    await screen.findByText('장소를 저장했어요.');
    const calls = apiRequest.mock.calls.filter(([path, options]) => path === '/api/v1/places' && options?.method === 'POST');
    expect(calls[0][1].headers['Idempotency-Key']).toBe(calls[1][1].headers['Idempotency-Key']);
  });
  it('세션 만료 시 이전 계정의 장소와 후보를 지운다', async () => {
    apiRequest.mockResolvedValueOnce(reply({items:[place], next_cursor:null})); render(<PlacesCard onLogin={vi.fn()}/>);
    await screen.findByText('서울 합성 주소'); const user=userEvent.setup();
    await user.click(screen.getByRole('button',{name:'장소 추가'}));
    await user.type(screen.getByLabelText('주소 또는 장소 이름'),'합성');
    apiRequest.mockRejectedValueOnce(new ApiError('SESSION_EXPIRED'));
    await user.click(screen.getByRole('button',{name:'주소 검색'}));
    await screen.findByRole('button',{name:'로그인하고 장소 저장'});
    expect(screen.queryByText('서울 합성 주소')).toBeNull();
  });
  it('StrictMode에서 목록 로딩이 끝나고 언마운트 요청을 취소한다', async () => {
    apiRequest.mockResolvedValue(reply({items:[], next_cursor:null}));
    const view=render(<React.StrictMode><PlacesCard onLogin={vi.fn()}/></React.StrictMode>);
    await screen.findByText(/아직 저장한 장소/); view.unmount();
    expect(apiRequest.mock.calls[0][1].signal.aborted).toBe(true);
    apiRequest.mockImplementation(() => new Promise(() => {}));
    const pendingView = render(<PlacesCard onLogin={vi.fn()}/>);
    pendingView.unmount();
    expect(apiRequest.mock.calls.at(-1)[1].signal.aborted).toBe(true);
  });
});
