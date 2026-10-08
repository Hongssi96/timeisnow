import React from 'react';
import { afterEach, expect, it, vi } from 'vitest';
import { render, screen, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import App from '../../src/app/App';
import { apiRequest, ApiError } from '../../src/lib/api';

vi.mock('../../src/lib/api', async original => ({ ...await original(), apiRequest: vi.fn() }));
vi.mock('../../src/components/PlacesCard', () => ({ default: () => null }));
vi.mock('../../src/components/JourneyComparison', () => ({ default: ({ onRoutineSaved, onBack, routineToReplace }) => <><p>{routineToReplace ? '기존 루틴 경로 변경' : '경로 저장 화면'}</p><button onClick={() => onRoutineSaved(item('new', '추가한 루틴'))}>후보 저장 성공</button><button onClick={onBack}>홈 복귀</button></> }));
vi.mock('../../src/components/AccountForm', () => ({ default: ({ onSessionChange }) => <button onClick={onSessionChange}>검증용 계정 변경</button> }));
afterEach(() => vi.resetAllMocks());
const nav = name => within(screen.getByRole('navigation', { name: '주 메뉴' })).getByRole('button', { name });
const item = (id = 'one', name = '실제 출근') => ({ routine_id: id, name, origin_place: { place_id: 'home', label: '집', name: '집 이름', address: '서울' }, destination_place: { place_id: 'work', label: '회사', name: '회사 이름', address: '서울' }, route: { journey_plan_id: 'plan', type: 'BUS', total_seconds: 1200, transfer_count: 1 }, weekdays: [1, 3, 5], target_arrival_local_time: '08:30', timezone: 'Asia/Seoul', status: 'active', version: 1, created_at: '2026-10-08T00:00:00Z', updated_at: '2026-10-08T00:00:00Z' });
const reply = (data, status = 200) => ({ data, status, meta: { request_id: 'test' } });
function setup(initial = [item()]) {
  let items = initial;
  apiRequest.mockImplementation(async (path, options = {}) => {
    if (path === '/api/v1/auth/csrf') return reply({ csrf_token: 'csrf' });
    if (options.method === 'PATCH') {
      items = items.map(value => value.routine_id === path.split('/').at(-1) ? { ...value, ...options.body, version: value.version + 1 } : value);
      return reply(items.find(value => value.routine_id === path.split('/').at(-1)));
    }
    if (options.method === 'DELETE') { items = items.filter(value => value.routine_id !== path.split('/').at(-1)); return reply(null, 204); }
    return reply({ items, next_cursor: null });
  });
  return { set: values => { items = values; }, user: userEvent.setup() };
}
it('loads actual routines, selects one and survives a remount without demo rows', async () => {
  const { user } = setup([item(), item('two', '퇴근 루틴')]);
  const view = render(<App/>);
  expect(await screen.findByRole('heading', { name: '실제 출근' })).toBeTruthy();
  expect(screen.queryByText('평일 출근')).toBeNull();
  expect(screen.queryByRole('button', { name: '지금 출발할게요' })).toBeNull();
  await user.click(nav('내 루틴'));
  const card = screen.getByRole('heading', { name: '퇴근 루틴' }).closest('section');
  await user.click(within(card).getByRole('button', { name: '루틴 선택' }));
  expect(screen.getByRole('heading', { name: '퇴근 루틴' })).toBeTruthy();
  view.unmount(); render(<App/>);
  expect(await screen.findByRole('heading', { name: '실제 출근' })).toBeTruthy();
});
it('routes add to candidate search and refreshes the saved list after returning', async () => {
  const { user, set } = setup([]); render(<App/>);
  await screen.findByText('저장한 루틴이 없어요');
  await user.click(nav('내 루틴')); await user.click(screen.getByRole('button', { name: '루틴 추가' }));
  expect(screen.getByText('경로 저장 화면')).toBeTruthy();
  set([item('new', '추가한 루틴')]);
  await user.click(screen.getByRole('button', { name: '후보 저장 성공' }));
  await user.click(screen.getByRole('button', { name: '홈 복귀' }));
  expect(await screen.findByRole('heading', { name: '추가한 루틴' })).toBeTruthy();
});
it('edits the name, weekdays and clears the target via versioned PATCH', async () => {
  const { user } = setup(); render(<App/>); await screen.findByRole('heading', { name: '실제 출근' }); await user.click(nav('내 루틴'));
  await user.click(screen.getByRole('button', { name: '수정' }));
  await user.clear(screen.getByLabelText('루틴 이름')); await user.type(screen.getByLabelText('루틴 이름'), '수정한 출근');
  await user.click(screen.getByRole('button', { name: '수' }));
  await user.clear(screen.getByLabelText('목표 도착 시각 (선택)'));
  await user.click(screen.getByRole('button', { name: '변경 저장' }));
  expect(await screen.findByRole('heading', { name: '수정한 출근' })).toBeTruthy();
  expect(apiRequest.mock.calls.find(([, options]) => options?.method === 'PATCH')[1].body).toEqual({ expected_version: 1, name: '수정한 출근', weekdays: [1, 5], target_arrival_local_time: null });
});
it('requires deletion confirmation, supports cancel and shows empty after 204', async () => {
  const { user } = setup(); render(<App/>); await screen.findByRole('heading', { name: '실제 출근' }); await user.click(nav('내 루틴'));
  await user.click(screen.getByRole('button', { name: '삭제' }));
  expect(apiRequest.mock.calls.some(([, options]) => options?.method === 'DELETE')).toBe(false);
  await user.click(screen.getByRole('button', { name: '취소' }));
  await user.click(screen.getByRole('button', { name: '삭제' })); await user.click(screen.getByRole('button', { name: '삭제 확인' }));
  expect(await screen.findByText('저장한 루틴이 없어요')).toBeTruthy();
});
it('clears the previous account list immediately when the session changes', async () => {
  const { user, set } = setup(); render(<App/>); await screen.findByRole('heading', { name: '실제 출근' });
  await user.click(screen.getByRole('button', { name: /나의 하루/ }));
  expect(screen.queryByRole('heading', { name: '실제 출근' })).toBeNull();
  set([item('other', '다른 계정 루틴')]);
  await user.click(screen.getByRole('button', { name: '검증용 계정 변경' })); await user.click(screen.getByRole('button', { name: '닫기' }));
  expect(await screen.findByRole('heading', { name: '다른 계정 루틴' })).toBeTruthy();
  expect(screen.queryByRole('heading', { name: '실제 출근' })).toBeNull();
});
it('handles auth expiry, malformed replies and recovery by retry', async () => {
  apiRequest.mockRejectedValueOnce(new ApiError('SESSION_EXPIRED')); render(<App/>);
  expect(await screen.findByText('로그인하고 내 루틴을 확인해요')).toBeTruthy();
  apiRequest.mockResolvedValue(reply({ items: [{ name: 'broken' }], next_cursor: null }));
  await userEvent.click(nav('내 루틴')); await userEvent.click(screen.getByRole('button', { name: '루틴 다시 확인' }));
  expect(await screen.findByRole('alert')).toBeTruthy();
  apiRequest.mockResolvedValue(reply({ items: [item()], next_cursor: null }));
  await userEvent.click(screen.getAllByRole('button', { name: '루틴 다시 확인' })[0]);
  expect(await screen.findByRole('heading', { name: '실제 출근' })).toBeTruthy();
});
it('loads a further page and preserves already loaded rows', async () => {
  apiRequest.mockImplementation(async path => path.includes('cursor=') ? reply({ items: [item('two', '추가 페이지')], next_cursor: null }) : reply({ items: [item()], next_cursor: 'one' }));
  render(<App/>); await screen.findByRole('heading', { name: '실제 출근' });
  await userEvent.click(screen.getByRole('button', { name: '루틴 더 보기' }));
  expect(await screen.findByRole('button', { name: '추가 페이지' })).toBeTruthy();
  expect(apiRequest).toHaveBeenCalledWith('/api/v1/routines?cursor=one', expect.anything());
});
it('reports a version conflict without replacing the form or claiming success', async () => {
  const { user } = setup(); render(<App/>); await screen.findByRole('heading', { name: '실제 출근' }); await user.click(nav('내 루틴')); await user.click(screen.getByRole('button', { name: '수정' }));
  apiRequest.mockImplementation(async path => { if (path.endsWith('/csrf')) return reply({ csrf_token: 'csrf' }); throw new ApiError('VERSION_CONFLICT'); });
  await user.click(screen.getByRole('button', { name: '변경 저장' }));
  expect(await screen.findByRole('alert')).toHaveProperty('textContent', expect.stringContaining('루틴이 변경되거나 삭제됐어요'));
  expect(screen.getByLabelText('루틴 이름').value).toBe('실제 출근');
});

it('shows deleted places as attention needed and allows route replacement',async()=>{
  const broken={...item(),origin_place:null,status:'needs_attention'};
  const {user}=setup([broken]);render(<App/>);await screen.findByRole('heading',{name:'실제 출근'});
  expect(screen.getByText('삭제된 장소 → 회사')).toBeTruthy();
  await user.click(nav('내 루틴'));await user.click(screen.getByRole('button',{name:'경로 바꾸기'}));
  expect(screen.getByText('기존 루틴 경로 변경')).toBeTruthy();
});
