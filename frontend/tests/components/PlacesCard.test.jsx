import React from 'react';
import { afterEach, describe, expect, it, vi } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import PlacesCard from '../../src/components/PlacesCard';
import { apiRequest, ApiError } from '../../src/lib/api';
vi.mock('../../src/lib/api', async original => ({ ...await original(), apiRequest: vi.fn() }));
vi.mock('../../src/components/LocationConfirmation', () => ({default: ({onDraft,onConfirmed,initialLocation}) => <div><button type="button" onClick={() => {onDraft();onConfirmed(null);}}>검증용 핀 이동</button><button type="button" onClick={() => onConfirmed({confirmation_id:'confirm_test',location:{...initialLocation,latitude:37.5002},deadline:Date.now()+600000})}>검증용 핀 확인</button></div>}));
afterEach(() => vi.resetAllMocks());
const reply = data => ({ data, meta: { request_id:'req_test', server_time: new Date().toISOString() } });
const item = { candidate_id:'c_test', name:'합성 역', address:'서울 합성 주소', location:{latitude:37.5, longitude:127} };
const place = { ...item, place_id:'p_test', label:'집', version:1 };
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
  it('지도 핀이 바뀌면 확인 전 저장을 막고 확인 ID를 전송한다', async () => {
    const user=await open(); await search(user);
    await user.click(await screen.findByRole('button',{name:/합성 역.*서울 합성 주소/}));
    await user.click(screen.getByRole('button',{name:'지도에서 위치 확인'}));
    await user.click(screen.getByRole('button',{name:'검증용 핀 이동'}));
    expect(screen.getByRole('button',{name:'선택한 장소 저장'}).disabled).toBe(true);
    await user.click(screen.getByRole('button',{name:'검증용 핀 확인'}));
    await user.type(screen.getByLabelText('출입구 설명'),'정문');
    apiRequest.mockResolvedValueOnce(reply({csrf_token:'csrf_test'})).mockResolvedValueOnce(reply({...place,entrance_note:'정문'}));
    await user.click(screen.getByRole('button',{name:'선택한 장소 저장'}));
    await screen.findByText('장소를 저장했어요.');
    const saved=apiRequest.mock.calls.find(([path, options])=>path==='/api/v1/places'&&options?.method==='POST');
    expect(saved[1].body.location_confirmation_id).toBe('confirm_test');
    expect(saved[1].body.location.latitude).toBe(37.5002);
    expect(saved[1].body.entrance_note).toBe('정문');
  });
  it('저장된 장소의 출입구를 현재 버전으로 수정한다', async () => {
    apiRequest.mockResolvedValueOnce(reply({items:[place],next_cursor:null}));render(<PlacesCard onLogin={vi.fn()}/>);
    const user=userEvent.setup(); await user.click(await screen.findByRole('button',{name:'집 위치·출입구 확인'}));
    await user.type(screen.getByLabelText('출입구 설명'),'동문');
    apiRequest.mockResolvedValueOnce(reply({csrf_token:'csrf_test'})).mockResolvedValueOnce(reply({...place,version:2,entrance_note:'동문'}));
    await user.click(screen.getByRole('button',{name:'위치·출입구 저장'}));
    await screen.findByText('위치·출입구를 저장했어요.');
    const updated=apiRequest.mock.calls.find(([,options])=>options?.method==='PATCH');
    expect(updated[1].body).toEqual({expected_version:1,entrance_note:'동문'});
    expect(screen.getByText('출입구: 동문 · 직접 입력')).toBeTruthy();
  });
  it('버전 충돌이면 최신 장소를 재조회하고 다시 확인하게 한다', async () => {
    apiRequest.mockResolvedValueOnce(reply({items:[place],next_cursor:null}));render(<PlacesCard onLogin={vi.fn()}/>);
    const user=userEvent.setup(); await user.click(await screen.findByRole('button',{name:'집 위치·출입구 확인'}));
    apiRequest.mockResolvedValueOnce(reply({csrf_token:'csrf_test'})).mockRejectedValueOnce(new ApiError('VERSION_CONFLICT')).mockResolvedValueOnce(reply({...place,version:2,entrance_note:'다른 화면의 수정'}));
    await user.click(screen.getByRole('button',{name:'위치·출입구 저장'}));
    expect(await screen.findByText('장소가 변경됐어요. 최신 위치를 다시 확인해주세요.')).toBeTruthy();
    expect(screen.queryByRole('button',{name:'위치·출입구 저장'})).toBeNull();
    expect(screen.getByText('출입구: 다른 화면의 수정 · 직접 입력')).toBeTruthy();
  });
  it('이름만 수정할 때 지도 호출 없이 현재 버전과 이름을 전송한다',async()=>{
    apiRequest.mockResolvedValueOnce(reply({items:[place],next_cursor:null}));render(<PlacesCard onLogin={vi.fn()}/>);
    const user=userEvent.setup();await user.click(await screen.findByRole('button',{name:'집 이름 수정'}));
    await user.clear(screen.getByLabelText('장소 이름'));expect(screen.getByRole('button',{name:'이름 저장'}).disabled).toBe(true);
    await user.type(screen.getByLabelText('장소 이름'),'우리 집');
    apiRequest.mockResolvedValueOnce(reply({csrf_token:'csrf_test'})).mockResolvedValueOnce(reply({...place,label:'우리 집',version:2}));
    await user.click(screen.getByRole('button',{name:'이름 저장'}));await screen.findByText('장소 이름을 저장했어요.');
    const updated=apiRequest.mock.calls.find(([,options])=>options?.method==='PATCH');
    expect(updated[1].body).toEqual({label:'우리 집',expected_version:1});
    expect(apiRequest.mock.calls.some(([path])=>path.includes('map-config')||path.includes('location-confirmations'))).toBe(false);
    expect(screen.getByRole('button',{name:'우리 집 삭제'})).toBeTruthy();
  });
  it('삭제 확인을 취소하면 삭제 요청을 하지 않는다',async()=>{
    apiRequest.mockResolvedValueOnce(reply({items:[place],next_cursor:null}));render(<PlacesCard onLogin={vi.fn()}/>);
    const user=userEvent.setup();await user.click(await screen.findByRole('button',{name:'집 삭제'}));
    expect(screen.getByText('집을(를) 삭제할까요?')).toBeTruthy();
    await user.click(screen.getByRole('button',{name:'삭제 취소'}));
    expect(apiRequest.mock.calls.length).toBe(1);expect(screen.getByText('서울 합성 주소')).toBeTruthy();
  });
  it('삭제204 후 목록 첫 페이지를 다시 조회한다',async()=>{
    apiRequest.mockResolvedValueOnce(reply({items:[place],next_cursor:'cursor_test'}));render(<PlacesCard onLogin={vi.fn()}/>);
    const user=userEvent.setup();await user.click(await screen.findByRole('button',{name:'집 삭제'}));
    apiRequest.mockResolvedValueOnce(reply({csrf_token:'csrf_test'})).mockResolvedValueOnce({status:204,data:null}).mockResolvedValueOnce(reply({items:[],next_cursor:null}));
    await user.click(screen.getByRole('button',{name:'장소 삭제 확인'}));await screen.findByText('장소를 삭제했어요.');
    expect(screen.queryByText('서울 합성 주소')).toBeNull();expect(screen.queryByRole('button',{name:'장소 더 보기'})).toBeNull();
    const deleted=apiRequest.mock.calls.find(([,options])=>options?.method==='DELETE');expect(deleted[1].body).toBeUndefined();
    expect(apiRequest.mock.calls.at(-1)[0]).toBe('/api/v1/places');
  });
  it('삭제 실패 뒤 같은 대상의404 재시도는 이미 삭제된 상태로 처리한다',async()=>{
    apiRequest.mockResolvedValueOnce(reply({items:[place],next_cursor:null}));render(<PlacesCard onLogin={vi.fn()}/>);
    const user=userEvent.setup();await user.click(await screen.findByRole('button',{name:'집 삭제'}));
    apiRequest.mockResolvedValueOnce(reply({csrf_token:'csrf_test'})).mockRejectedValueOnce(new ApiError('NETWORK_ERROR'));
    await user.click(screen.getByRole('button',{name:'장소 삭제 확인'}));await screen.findByRole('alert');
    expect(screen.getByText('서울 합성 주소')).toBeTruthy();
    apiRequest.mockResolvedValueOnce(reply({csrf_token:'csrf_test'})).mockRejectedValueOnce(new ApiError('RESOURCE_NOT_FOUND')).mockResolvedValueOnce(reply({items:[],next_cursor:null}));
    await user.click(screen.getByRole('button',{name:'장소 삭제 확인'}));await screen.findByText('이미 삭제된 장소예요. 목록을 다시 확인했어요.');
    expect(screen.queryByText('서울 합성 주소')).toBeNull();
  });
  it('삭제 후 목록 조회만 실패하면 삭제한 장소를 복원하지 않는다',async()=>{
    apiRequest.mockResolvedValueOnce(reply({items:[place],next_cursor:null}));render(<PlacesCard onLogin={vi.fn()}/>);
    const user=userEvent.setup();await user.click(await screen.findByRole('button',{name:'집 삭제'}));
    apiRequest.mockResolvedValueOnce(reply({csrf_token:'csrf_test'})).mockResolvedValueOnce({status:204,data:null}).mockRejectedValueOnce(new ApiError('NETWORK_ERROR'));
    await user.click(screen.getByRole('button',{name:'장소 삭제 확인'}));await screen.findByText(/장소는 삭제됐어요/);
    expect(screen.queryByText('서울 합성 주소')).toBeNull();expect(screen.getByRole('button',{name:'목록 다시 확인'})).toBeTruthy();
  });
  it('삭제 요청 중 중복 실행을 막고 화면 이탈 시 취소한다',async()=>{
    apiRequest.mockResolvedValueOnce(reply({items:[place],next_cursor:null}));const view=render(<PlacesCard onLogin={vi.fn()}/>);
    const user=userEvent.setup();await user.click(await screen.findByRole('button',{name:'집 삭제'}));
    apiRequest.mockImplementation(()=>new Promise(()=>{}));await user.click(screen.getByRole('button',{name:'장소 삭제 확인'}));
    expect(screen.getByRole('button',{name:'삭제 중…'}).disabled).toBe(true);
    expect(screen.getByRole('button',{name:'삭제 취소'}).disabled).toBe(true);
    view.unmount();expect(apiRequest.mock.calls.at(-1)[1].signal.aborted).toBe(true);
  });
  it('다른 화면의 이름 수정과 충돌하면 최신 이름으로 재확인한다',async()=>{
    apiRequest.mockResolvedValueOnce(reply({items:[place],next_cursor:null}));render(<PlacesCard onLogin={vi.fn()}/>);
    const user=userEvent.setup();await user.click(await screen.findByRole('button',{name:'집 이름 수정'}));
    apiRequest.mockResolvedValueOnce(reply({csrf_token:'csrf_test'})).mockRejectedValueOnce(new ApiError('VERSION_CONFLICT')).mockResolvedValueOnce(reply({...place,label:'새 집',version:2}));
    await user.click(screen.getByRole('button',{name:'이름 저장'}));await screen.findByText('장소가 변경됐어요. 최신 위치를 다시 확인해주세요.');
    expect(screen.queryByRole('button',{name:'이름 저장'})).toBeNull();expect(screen.getByRole('button',{name:'새 집 이름 수정'})).toBeTruthy();
  });
  it('충돌 뒤 최신 조회에서 세션이 만료되면 이전 계정의 장소를 지운다',async()=>{
    apiRequest.mockResolvedValueOnce(reply({items:[place],next_cursor:null}));render(<PlacesCard onLogin={vi.fn()}/>);
    const user=userEvent.setup();await user.click(await screen.findByRole('button',{name:'집 이름 수정'}));
    apiRequest.mockResolvedValueOnce(reply({csrf_token:'csrf_test'})).mockRejectedValueOnce(new ApiError('VERSION_CONFLICT')).mockRejectedValueOnce(new ApiError('SESSION_EXPIRED'));
    await user.click(screen.getByRole('button',{name:'이름 저장'}));await screen.findByText('로그인이 만료됐어요. 다시 로그인해주세요.');
    expect(screen.queryByText('서울 합성 주소')).toBeNull();expect(screen.getByRole('button',{name:'로그인하고 장소 저장'})).toBeTruthy();
  });
});
