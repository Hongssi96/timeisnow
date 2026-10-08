import React from 'react';
import { afterEach, expect, it, vi } from 'vitest';
import { act, fireEvent, render, screen } from '@testing-library/react';
import JourneyComparison from '../../src/components/JourneyComparison';
import { apiRequest, ApiError } from '../../src/lib/api';
import fixtures from '../fixtures/journeys.json';

vi.mock('../../src/lib/api', async original => ({ ...await original(), apiRequest: vi.fn() }));
vi.mock('../../src/components/MapPinPicker', () => ({ default: () => <p>검증 지도</p> }));
afterEach(() => { vi.resetAllMocks(); vi.useRealTimers(); });
const reply = (data, status = 200) => ({ data, status, meta: { request_id: 'inline_test', server_time: new Date().toISOString() } });
const until = () => new Date(Date.now() + 600000).toISOString();
const accepted = { search_id: 'inline_search', job_id: 'inline_job', status: 'queued' };
function setup({ saveFailure = false, validationFailure = false, pendingSave = false, authFailure = false } = {}) {
  vi.useFakeTimers();
  const places = []; let candidate, saveAttempts = 0, validationAttempts = 0, release;
  const onSaved = vi.fn(), onAuthError = vi.fn();
  apiRequest.mockImplementation(async (path, options = {}) => {
    if (path === '/api/v1/auth/csrf') return reply({ csrf_token: 'csrf_inline' });
    if (path === '/api/v1/places' && options.method !== 'POST') return reply({ items: places, next_cursor: null });
    if (path === '/api/v1/place-searches') {
      candidate = { candidate_id: 'candidate_' + (places.length + 1), name: '검색한 역', address: '서울 합성 주소', location: { latitude: 37.5 + places.length / 100, longitude: 127 } };
      return reply({ search_id: 'place_search', expires_at: until(), candidates: [candidate] });
    }
    if (path === '/api/v1/places') {
      if (authFailure) throw new ApiError('SESSION_EXPIRED');
      if (saveFailure && saveAttempts++ === 0) throw new ApiError('NETWORK_ERROR');
      const place = { ...candidate, place_id: 'place_' + (places.length + 1), label: options.body.label, version: 1, location_version: 1 };
      if (pendingSave) await new Promise(resolve => { release = resolve; });
      places.push(place); return reply(place, 201);
    }
    if (path === '/api/v1/origin-validations') {
      if (validationFailure && validationAttempts++ === 0) throw new ApiError('NETWORK_ERROR');
      const origin = options.body.origin, place = places.find(item => item.place_id === origin.place_id);
      return reply({ origin, label: place.label, location: place.location, location_address: place.address, quality_status: 'not_applicable',
        quality: { assessment: 'user_selected', confirmation: 'not_applicable', numeric_policy: 'deferred', time_relation: 'not_applicable' },
        place_match: { status: 'selected_by_user' }, expires_at: until() });
    }
    if (path === '/api/v1/journey-searches') return reply(accepted, 202);
    if (path === '/api/v1/routines') return reply({ routine_id: 'routine_inline', name: options.body.name,
      origin_place: places[0], destination_place: places[1], route: { journey_plan_id: 'plan_inline', type: 'BUS', total_seconds: 600, transfer_count: 0 },
      weekdays: options.body.weekdays, target_arrival_local_time: options.body.target_arrival_local_time, timezone: 'Asia/Seoul', status: 'active', version: 1 }, 201);
    return reply({ ...accepted, status: 'succeeded', candidates: [structuredClone(fixtures.direct)], unavailable_reasons: [], error: null, expires_at: new Date(Date.now() + 290000).toISOString() });
  });
  render(<JourneyComparison onRoutineSaved={onSaved} onAuthError={onAuthError}/>);
  return { places, onSaved, onAuthError, release: () => release?.() };
}
const click = async node => { await act(async () => fireEvent.click(node)); };
const change = async (label, value) => { await act(async () => fireEvent.change(screen.getByLabelText(label), { target: { value } })); };
async function newPlace(purpose, submit = true) {
  await click(screen.getByRole('button', { name: purpose + '지 선택', exact: true }));
  await click(screen.getByRole('button', { name: '장소 저장', exact: true }));
  await change('주소 또는 장소 이름', '합성 ' + purpose);
  await click(screen.getByRole('button', { name: '주소 검색' }));
  expect(apiRequest.mock.calls.some(([path, options]) => path === '/api/v1/places' && options?.method === 'POST')).toBe(purpose === '도착');
  await click(screen.getByRole('button', { name: /검색한 역.*서울 합성 주소/ }));
  expect(screen.getByLabelText('저장할 이름').value).toBe(purpose + '지');
  if (submit) await click(screen.getByRole('button', { name: '선택한 장소 저장' }));
}
it('creates both endpoint places inline, preserves the first and then saves a routine', async () => {
  const { places, onSaved } = setup();
  await newPlace('출발'); expect(screen.getByText('출발지', { selector: 'p' })).toBeTruthy();
  await newPlace('도착'); expect(places).toHaveLength(2);
  expect(screen.getByText('출발지', { selector: 'p' })).toBeTruthy();
  expect(screen.getByText('도착지', { selector: 'p' })).toBeTruthy();
  expect(apiRequest.mock.calls.some(([path]) => path === '/api/v1/routines')).toBe(false);
  await click(screen.getByRole('button', { name: '경로 후보 조회' }));
  await act(() => vi.advanceTimersByTimeAsync(2000));
  const search = apiRequest.mock.calls.find(([path]) => path === '/api/v1/journey-searches')[1].body;
  expect(search.origin).toEqual({ type: 'saved_place', place_id: 'place_1', location_version: 1 });
  expect(search.destination).toEqual({ type: 'saved_place', place_id: 'place_2', location_version: 1 });
  await click(screen.getByRole('button', { name: '이 경로를 루틴에 저장' }));
  await click(screen.getByRole('button', { name: '루틴 저장' }));
  expect(onSaved).toHaveBeenCalledOnce();
});
it('offers creation from an empty saved list and cancels without a write', async () => {
  const { places } = setup();
  await click(screen.getByRole('button', { name: '출발지 선택' }));
  await click(screen.getByRole('button', { name: '저장 장소', exact: true }));
  expect(screen.getByText(/여기에서 새 장소를 저장/)).toBeTruthy();
  await click(screen.getByRole('button', { name: '새 장소 저장하고 선택' }));
  expect(screen.getByLabelText('주소 또는 장소 이름')).toBeTruthy();
  await click(screen.getByRole('button', { name: '장소 저장 취소' }));
  expect(places).toHaveLength(0);
  expect(apiRequest.mock.calls.some(([path, options]) => options?.method === 'POST')).toBe(false);
});
it('retries a failed creation with the same idempotency key and keeps the form', async () => {
  const { places } = setup({ saveFailure: true }); await newPlace('출발');
  expect(screen.getByRole('alert').textContent).toContain('서버에 연결');
  expect(screen.getByLabelText('저장할 이름').value).toBe('출발지');
  await click(screen.getByRole('button', { name: '선택한 장소 저장' }));
  const writes = apiRequest.mock.calls.filter(([path, options]) => path === '/api/v1/places' && options?.method === 'POST');
  expect(writes).toHaveLength(2);
  expect(writes[0][1].headers['Idempotency-Key']).toBe(writes[1][1].headers['Idempotency-Key']);
  expect(places).toHaveLength(1);
});
it('keeps a persisted place after selection validation fails and retries only validation', async () => {
  const { places } = setup({ validationFailure: true }); await newPlace('출발');
  expect(screen.getByRole('alert').textContent).toContain('장소는 저장됐어요');
  await click(screen.getByRole('button', { name: /출발지.*서울 합성 주소/ }));
  expect(screen.getByText('출발지', { selector: 'p' })).toBeTruthy();
  expect(places).toHaveLength(1);
  expect(apiRequest.mock.calls.filter(([path, options]) => path === '/api/v1/places' && options?.method === 'POST')).toHaveLength(1);
});
it('disables mode changes and cancellation during creation and permits one write', async () => {
  const fixture = setup({ pendingSave: true }); await newPlace('출발', false);
  await click(screen.getByRole('button', { name: '선택한 장소 저장' }));
  expect(screen.getByRole('button', { name: '장소 저장 취소' }).disabled).toBe(true);
  expect(screen.getByRole('button', { name: '위치 선택 취소' }).disabled).toBe(true);
  expect(screen.getByRole('button', { name: '저장 장소', exact: true }).disabled).toBe(true);
  await act(async () => fixture.release());
  expect(fixture.places).toHaveLength(1);
});
it('clears the inline form on session expiry and exposes login', async () => {
  const { onAuthError } = setup({ authFailure: true }); await newPlace('출발');
  expect(screen.queryByLabelText('주소 또는 장소 이름')).toBeNull();
  expect(screen.getByRole('button', { name: '로그인하기' })).toBeTruthy();
  expect(onAuthError).toHaveBeenCalledOnce();
});
