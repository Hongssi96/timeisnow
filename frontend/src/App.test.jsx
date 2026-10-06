import React from 'react';
import { describe, it, expect, vi, afterEach } from 'vitest';
import { render, screen, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import App from './App';
vi.spyOn(console, 'info').mockImplementation(() => {});
const nav = (label) => within(screen.getByRole('navigation', { name: '주 메뉴' })).getByRole('button', { name: label });
describe('화면 체험의 주요 사용자 흐름', () => {
  it('정보가 만료되면 출발 동작을 숨기고 확인 불가로 안내한다', async () => {
    render(<App/>); const u = userEvent.setup();
    await u.click(screen.getByRole('button', {name:'정보 만료'}));
    expect(screen.queryByRole('button', {name:'지금 출발할게요'})).toBeNull();
    expect(screen.getByText('현재 여유 시간을 확인할 수 없어요.')).toBeTruthy();
    await u.click(screen.getByRole('button', {name:'안내 다시 확인하기'}));
    expect(screen.getByRole('button', {name:'지금 출발할게요'})).toBeTruthy();
  });
  it('지금 출발의 여유를 8분으로 표시하고 도착과 탑승을 분리한다', async () => {
    render(<App/>); const u = userEvent.setup();
    await u.click(screen.getByRole('button', {name:'지금 출발할게요'}));
    expect(screen.getByText('지금 출발 기준 예상 여유 8분')).toBeTruthy();
    await u.click(screen.getByRole('button', {name:'정류장에 도착했어요'}));
    expect(screen.getByRole('button', {name:'버스를 탔어요'})).toBeTruthy();
    await u.click(screen.getByRole('button', {name:'버스를 탔어요'}));
    await u.click(screen.getByRole('button', {name:'목적지 정류장에서 내렸어요'}));
    await u.click(screen.getByRole('button', {name:'목적지에 도착했어요'}));
    expect(screen.getByText('1번의 화면 체험')).toBeTruthy();
    expect(screen.getByText('이동 완료')).toBeTruthy();
  });
  it('루틴을 추가하고 해당 루틴의 홈으로 이동한다', async () => {
    render(<App/>); const u=userEvent.setup(); await u.click(nav('내 루틴'));
    await u.click(screen.getByRole('button', {name:'루틴 추가'}));
    await u.type(screen.getByLabelText('루틴 이름'), '오후 등교');
    await u.selectOptions(screen.getByLabelText('도착지'), '학교');
    await u.click(screen.getByRole('button',{name:'루틴 저장'}));
    const card=screen.getByRole('heading',{name:'오후 등교'}).closest('section');
    await u.click(within(card).getByRole('button',{name:'출발 확인'}));
    expect(screen.getByText('오후 등교 · 예시')).toBeTruthy();
    expect(screen.getByText('약 47분 · 환승 1회')).toBeTruthy();
  });
  it('여유 설정을 바꾸면 출발과 전체 이동 예시가 함께 바뀐다', async () => {
    render(<App/>); const u=userEvent.setup(); await u.click(nav('내 설정'));
    await u.click(screen.getByRole('button',{name:'여유 1분 늘리기'}));
    await u.click(nav('오늘의 출발'));
    expect(screen.getByText('약 6분의 여유')).toBeTruthy();
    expect(screen.getByText('약 33분 · 환승 0회')).toBeTruthy();
  });
  it('환승 예시에서는 하차·승강장 도착·지하철 탑승을 별도로 확인한다', async () => {
    render(<App/>); const u=userEvent.setup();
    await u.click(screen.getByRole('button',{name:'학교 학교 가는 길'}));
    await u.click(screen.getByRole('button',{name:'지금 출발할게요'}));
    for (const label of ['정류장에 도착했어요','버스를 탔어요','환승 정류장에서 내렸어요','승강장에 도착했어요','지하철을 탔어요','목적지 역에서 내렸어요','목적지에 도착했어요']) {
      await u.click(screen.getByRole('button',{name:label}));
    }
    expect(screen.getByText('1번의 화면 체험')).toBeTruthy();
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
    expect(fetchMock).toHaveBeenCalledWith('/api/v1/health');
    expect(await screen.findByText(/연결됨 · 확인 시각/)).toBeTruthy();
  });
  it('서버에 연결하지 못하면 실패를 안내하고 다시 확인할 수 있다', async () => {
    vi.stubGlobal('fetch', vi.fn(async () => { throw new TypeError('네트워크 실패'); }));
    render(<App/>); const u = userEvent.setup();
    await u.click(nav('내 설정'));
    await u.click(screen.getByRole('button', { name: '서버 연결 확인' }));
    expect(await screen.findByText('서버에 연결할 수 없어요. 백엔드가 실행 중인지 확인하고 다시 시도해주세요.')).toBeTruthy();
    expect(screen.getByRole('button', { name: '다시 확인하기' })).toBeTruthy();
  });
});
