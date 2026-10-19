import React from 'react';
import { describe, it, expect, vi, afterEach } from 'vitest';
import { render, screen, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import App from '../../src/app/App';
vi.spyOn(console, 'info').mockImplementation(() => {});
const nav = (label) => within(screen.getByRole('navigation', { name: '주 메뉴' })).getByRole('button', { name: label });
vi.mock('../../src/lib/routines',async original=>({...await original(),useRoutines:()=>({state:{phase:'ready',items:[],next:null},load:vi.fn(),clear:vi.fn()})}));
// 장소 API는 PlacesCard.test.jsx에서 별도로 검증한다.
vi.mock('../../src/components/PlacesCard', () => ({ default: () => <section><h2>내 장소</h2></section> }));
vi.mock('../../src/components/ProfileSettingsCard',()=>({default:()=> <section><h2>이동 설정</h2></section>}));
// 학습 API/실패/초기화는 Personalization.test.jsx에서 독립 검증한다.
vi.mock('../../src/components/PersonalizationCard', () => ({default:()=> <section><h2>내 걸음 학습</h2></section>}));
vi.mock('../../src/components/OriginSelector', () => ({ default: ({ purpose, onSelect }) => <button onClick={() => onSelect({ label: purpose === 'origin' ? '출발 검증역' : '도착 검증역', location_address: '서울 공개 검증 위치', origin: { type: 'saved_place', place_id: purpose === 'origin' ? 'place_origin' : 'place_destination', location_version: 1 }, deadline: Date.now() + 600000 })}>검증 위치 적용</button> }));
describe('경로 비교 화면의 계정 모달', () => {
  afterEach(() => vi.unstubAllGlobals());
  it('계정 모달을 열었다 닫아도 출발지·도착지 선택이 유지된다', async () => {
    vi.stubGlobal('fetch', vi.fn(async () => ({ ok: false, status: 401, headers: new Headers(), json: async () => ({ error: { code: 'AUTH_REQUIRED', message: '로그인이 필요해요' }, meta: { request_id: 'req_anon', server_time: '2026-10-07T00:00:00Z' } }) })));
    render(<App/>); const u = userEvent.setup();
    await u.click(screen.getByRole('button', { name: '경로 후보 비교' }));
    expect(screen.getByRole('button', { name: '경로 후보 조회' })).toBeTruthy();
    await u.click(screen.getByRole('button', { name: '출발지 선택' }));
    await u.click(screen.getByRole('button', { name: '검증 위치 적용' }));
    await u.click(screen.getByRole('button', { name: '도착지 선택' }));
    await u.click(screen.getByRole('button', { name: '검증 위치 적용' }));
    const profile = screen.getByRole('button', { name: /회원가입 · 로그인/ });
    await u.click(profile);
    expect(screen.getByRole('dialog')).toBeTruthy();
    expect(screen.getByRole('button', { name: '로그인하기' })).toBeTruthy();
    expect(screen.getByRole('button', { name: '경로 후보 조회' })).toBeTruthy();
    await u.click(screen.getByRole('button', { name: '닫기' }));
    expect(screen.getByText('출발 검증역')).toBeTruthy();
    expect(screen.getByText('도착 검증역')).toBeTruthy();
    expect(screen.getByRole('button', { name: '경로 후보 조회' })).toBeTruthy();
  });
});
describe('서버 연결 확인', () => {
  afterEach(() => vi.unstubAllGlobals());
  it('정상 응답이면 연결됨과 확인 시각을 표시한다', async () => {
    const fetchMock = vi.fn(async () => ({ ok: true, status: 200, json: async () => ({ data: { status: 'ok', server_time: '2026-10-02T00:09:00Z' }, meta: { request_id: 'req_test_1', server_time: '2026-10-02T00:09:00Z' } }) }));
    vi.stubGlobal('fetch', fetchMock);
    render(<App/>); const u = userEvent.setup();
    await u.click(nav('내 설정'));
    await u.click(screen.getByRole('button', { name: '서버 연결 확인' }));
    expect(fetchMock).toHaveBeenCalledWith('/api/v1/health', expect.objectContaining({ credentials: 'same-origin', signal: expect.any(AbortSignal) }));
    expect(await screen.findByText(/연결됨 · 확인 시각/)).toBeTruthy();
    expect(screen.getByText('req_test_1')).toBeTruthy();
  });
  it('서버에 연결하지 못하면 실패를 안내하고 다시 확인할 수 있다', async () => {
    vi.stubGlobal('fetch', vi.fn(async () => { throw new TypeError('네트워크 실패'); }));
    render(<App/>); const u = userEvent.setup();
    await u.click(nav('내 설정'));
    await u.click(screen.getByRole('button', { name: '서버 연결 확인' }));
    expect(await screen.findByText('서버에 연결할 수 없어요. 백엔드가 실행 중인지 확인하고 다시 시도해주세요.')).toBeTruthy();
    expect(screen.getByRole('button', { name: '다시 확인하기' })).toBeTruthy();
  });
  it('응답을 기다리는 동안 중복 클릭을 막고 로딩을 표시한다', async () => {
    let resolve;
    const fetchMock = vi.fn(() => new Promise(done => { resolve = done; }));
    vi.stubGlobal('fetch', fetchMock);
    render(<App/>); const u = userEvent.setup();
    await u.click(nav('내 설정'));
    const button = screen.getByRole('button', { name: '서버 연결 확인' });
    await u.click(button);
    expect(screen.getByText('서버에 연결하는 중…')).toBeTruthy();
    expect(button.disabled).toBe(true);
    await u.click(button); expect(fetchMock).toHaveBeenCalledTimes(1);
    resolve({ ok: true, status: 200, json: async () => ({ data: { status: 'ok', server_time: '2026-10-06T00:00:00Z' }, meta: { request_id: 'req_wait', server_time: '2026-10-06T00:00:00Z' } }) });
    expect(await screen.findByText('req_wait')).toBeTruthy();
  });
  it('서버 오류의 요청 ID를 표시하고 재시도에서 새 ID로 바꾼다', async () => {
    const fetchMock = vi.fn()
      .mockResolvedValueOnce({ ok: false, status: 500, headers: new Headers({ 'X-Request-ID': 'req_failed' }), json: async () => ({ error: { code: 'INTERNAL_ERROR', message: 'secret-value' }, meta: { request_id: 'req_failed' } }) })
      .mockResolvedValueOnce({ ok: true, status: 200, json: async () => ({ data: { status: 'ok', server_time: '2026-10-06T00:00:00Z' }, meta: { request_id: 'req_retry', server_time: '2026-10-06T00:00:00Z' } }) });
    vi.stubGlobal('fetch', fetchMock);
    render(<App/>); const u = userEvent.setup();
    await u.click(nav('내 설정')); await u.click(screen.getByRole('button', { name: '서버 연결 확인' }));
    expect(await screen.findByText('req_failed')).toBeTruthy();
    expect(screen.queryByText('secret-value')).toBeNull();
    await u.click(screen.getByRole('button', { name: '다시 확인하기' }));
    expect(await screen.findByText('req_retry')).toBeTruthy();
    expect(screen.queryByText('req_failed')).toBeNull();
  });
  it('잘못된 health 데이터는 연결됨으로 표시하지 않는다', async () => {
    vi.stubGlobal('fetch', vi.fn(async () => ({ ok: true, status: 200, json: async () => ({ data: { status: 'ok', server_time: 'bad' }, meta: { request_id: 'req_bad', server_time: '2026-10-06T00:00:00Z' } }) })));
    render(<App/>); const u = userEvent.setup();
    await u.click(nav('내 설정')); await u.click(screen.getByRole('button', { name: '서버 연결 확인' }));
    expect(await screen.findByText('서버 응답을 확인할 수 없어요. 다시 시도해주세요.')).toBeTruthy();
    expect(screen.queryByText(/연결됨 ·/)).toBeNull();
  });
  it('설정 화면을 떠나면 요청을 취소한다', async () => {
    let signal;
    vi.stubGlobal('fetch', vi.fn((_, options) => new Promise((_, reject) => {
      signal = options.signal;
      signal.addEventListener('abort', () => reject(new DOMException('aborted', 'AbortError')));
    })));
    render(<App/>); const u = userEvent.setup();
    await u.click(nav('내 설정')); await u.click(screen.getByRole('button', { name: '서버 연결 확인' }));
    await u.click(nav('오늘의 출발')); expect(signal.aborted).toBe(true);
    await u.click(nav('내 설정'));
    expect(screen.getByText('아직 확인하지 않았어요.')).toBeTruthy();
  });
});
