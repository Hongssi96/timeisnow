import React, { useEffect, useRef, useState } from 'react';
import { apiRequest, ApiError, isServerTime } from '../lib/api';
import { getCurrentOrigin } from '../lib/currentOrigin';
import MapPinPicker from './MapPinPicker';
import OriginReview from './OriginReview';

const validLocation = value => Number.isFinite(value?.latitude) && Math.abs(value.latitude) <= 90
  && Number.isFinite(value?.longitude) && Math.abs(value.longitude) <= 180;
const validPlace = value => typeof value?.place_id === 'string' && typeof value.label === 'string'
  && validLocation(value.location) && Number.isInteger(value.location_version) && value.location_version >= 1;

export default function OriginSelector({ onSelect, onLogin, onAuthError }) {
  const [mode, setMode] = useState('current');
  const [phase, setPhase] = useState('loading');
  const [items, setItems] = useState([]);
  const [cursor, setCursor] = useState(null);
  const [message, setMessage] = useState('');
  const [location, setLocation] = useState({ latitude: 37.5665, longitude: 126.9780 });
  const [touched, setTouched] = useState(false);
  const [draft, setDraft] = useState(null);
  const [expired, setExpired] = useState(false);
  useEffect(() => {
    setExpired(false);
    if (!draft) return;
    const timer = setTimeout(() => {
      pending.current?.abort(); pending.current = null; setPhase('ready');
      setDraft(null); setMessage('출발지 확인 화면이 만료됐어요. 현재 위치를 다시 측정해주세요.');
    }, Math.max(0, draft.deadline - Date.now()));
    return () => clearTimeout(timer);
  }, [draft]);
  const pending = useRef(null);
  const busy = ['loading', 'locating', 'validating'].includes(phase);
  function authError(error) {
    pending.current?.abort(); setDraft(null); setItems([]); setCursor(null); setTouched(false);
    setLocation({ latitude: 37.5665, longitude: 126.9780 }); setMode('current');
    setPhase('anonymous'); setMessage(error.message); onAuthError?.();
  }
  async function run(operation, nextPhase) {
    if (pending.current) return;
    const controller = new AbortController(); pending.current = controller;
    setPhase(nextPhase); setMessage('');
    try { await operation(controller.signal); }
    catch (error) {
      if (controller.signal.aborted) return;
      if (['AUTH_REQUIRED', 'SESSION_EXPIRED'].includes(error.code)) { authError(error); return; }
      if (error.code?.startsWith('GEO_')) { setMode('map'); setTouched(false); }
      if (['VERSION_CONFLICT', 'RESOURCE_NOT_FOUND'].includes(error.code)) { setItems([]); setCursor(null); }
      setMessage(error.message || '다시 시도해주세요.'); setPhase('error');
    } finally { if (pending.current === controller) pending.current = null; }
  }
  function load(more = false) {
    return run(async signal => {
      const response = await apiRequest('/api/v1/places' + (more && cursor ? '?cursor=' + encodeURIComponent(cursor) : ''), { signal });
      if (!Array.isArray(response.data?.items) || !response.data.items.every(validPlace)
        || !(response.data.next_cursor === null || typeof response.data.next_cursor === 'string')) throw new ApiError('INVALID_RESPONSE');
      if (signal.aborted) return;
      setItems(previous => more ? [...previous, ...response.data.items] : response.data.items);
      setCursor(response.data.next_cursor);
      if (!more && response.data.items.length) setLocation(response.data.items[0].location);
      setTouched(false); setPhase('ready');
    }, 'loading');
  }
  useEffect(() => { load(); return () => { pending.current?.abort(); pending.current = null; }; }, []);
  function changeMode(next) {
    setDraft(null);
    pending.current?.abort(); pending.current = null; setMode(next); setTouched(false); setMessage('');
    setPhase(previous => previous === 'anonymous' ? previous : 'ready');
  }
  async function validate(origin, signal) {
    const csrf = await apiRequest('/api/v1/auth/csrf', { signal });
    if (typeof csrf.data?.csrf_token !== 'string') throw new ApiError('INVALID_RESPONSE');
    const response = await apiRequest('/api/v1/origin-validations', { method: 'POST', body: { origin }, signal,
      headers: { 'X-CSRF-Token': csrf.data.csrf_token } });
    const data = response.data;
    if (data?.origin?.type !== origin.type || typeof data.label !== 'string' || typeof data.location_address !== 'string'
      || !validLocation(data.location) || data.quality_status !== (origin.type === 'current_location' ? (origin.location_confirmed ? 'user_confirmed' : 'pending') : 'not_applicable')
      || !isServerTime(data.expires_at) || !isServerTime(response.meta.server_time)) throw new ApiError('INVALID_RESPONSE');
    if (origin.type === 'current_location' && (!validLocation(data.origin) || !isServerTime(data.origin.captured_at)
      || !Number.isFinite(data.origin.accuracy_meters) || data.origin.accuracy_meters < 0)) throw new ApiError('INVALID_RESPONSE');
    if (origin.type === 'saved_place' && (data.origin.place_id !== origin.place_id
      || !Number.isInteger(data.origin.location_version) || data.origin.location_version < 1)) throw new ApiError('INVALID_RESPONSE');
    const currentLocation = origin.type === 'current_location';
    if (data.quality?.numeric_policy !== 'deferred'
      || data.quality.assessment !== (currentLocation ? 'unassessed' : 'user_selected')
      || data.quality.confirmation !== (currentLocation ? (origin.location_confirmed ? 'reported' : 'required') : 'not_applicable')
      || !(currentLocation ? ['future', 'past_or_present'].includes(data.quality.time_relation) : data.quality.time_relation === 'not_applicable')
      || data.place_match?.status !== (origin.type === 'saved_place' ? 'selected_by_user' : 'unconfirmed')
      || (currentLocation && data.origin.location_confirmed !== Boolean(origin.location_confirmed))) throw new ApiError('INVALID_RESPONSE');
    const remaining = Date.parse(data.expires_at) - Date.parse(response.meta.server_time);
    if (remaining <= 0 || remaining > 600000) throw new ApiError('INVALID_RESPONSE');
    if (!signal.aborted) {
      const selection = { ...data, deadline: Date.now() + remaining };
      if (currentLocation && !origin.location_confirmed) { setDraft(selection); setPhase('ready'); }
      else onSelect(selection);
    }
  }
  function current() {
    setDraft(null);
    run(async signal => {
      // Recheck authentication before asking the device for sensitive location.
      await apiRequest('/api/v1/me', { signal });
      const origin = await getCurrentOrigin(signal);
      if (signal.aborted) return;
      setPhase('validating'); await validate(origin, signal);
    }, 'locating');
  }
  return <div className="origin-selector" aria-busy={busy}>
    <p className="muted">출발지를 선택해주세요. 실제 경로와 출발 시간 안내는 준비 중이에요.</p>
    {phase === 'anonymous' ? <><p role="alert">{message}</p><button className="primary wide" onClick={onLogin}>로그인하기</button></> : <>
      <div className="origin-methods" role="group" aria-label="출발지 선택 방법">{[['current','현재 위치'],['map','지도 선택'],['saved','저장 장소']].map(([key,label]) =>
        <button className="secondary" key={key} aria-pressed={mode === key} disabled={phase === 'loading'} onClick={() => changeMode(key)}>{label}</button>)}</div>
      {message && <p className="info-box" role="alert">{message}</p>}
      {busy && <p role="status">{phase === 'locating' ? '기기 위치 권한을 확인하고 있어요. 최대 15초 기다려요.' : phase === 'validating' ? '출발지를 확인하고 있어요.' : '내 장소를 확인하고 있어요.'}</p>}
      {mode === 'current' && <><p className="small muted">버튼을 누르면 기기 위치를 한 번 요청해요. 선택 좌표는 서울·경기 확인을 위해 카카오로 전달돼요. 위치 추적이나 자동 저장은 하지 않아요.</p>
        <p className="small muted">GPS 수치 기준은 보류 중이에요. 측정 후 지도에서 실제 출발 위치를 직접 확인해주세요. 저장 장소는 직접 선택해요.</p>
        <button className="secondary wide" disabled={busy} onClick={current}>{draft ? '현재 위치 다시 측정' : '현재 위치 확인'}</button>
        {draft && <OriginReview draft={draft} busy={busy} expired={expired} onAuthError={authError}
          onChange={point => { changeMode('map'); setLocation(point); setTouched(true); }}
          onConfirm={() => { if (Date.now() >= draft.deadline) { setExpired(true); return; }
            run(signal => validate({ ...draft.origin, location_confirmed: true }, signal), 'validating'); }}/>}</>}
      {mode === 'map' && <><MapPinPicker location={location} mapLabel="출발지 선택 지도"
        description="시작 핀은 현재 위치가 아니에요. 지도를 누르거나 핀을 옮겨 출발지를 직접 선택해주세요. 선택 위치가 카카오 지도에 표시돼요."
        disabled={busy} onAuthError={authError} onChange={point => { setLocation(point); setTouched(true); setMessage(''); }}/>
        <button className="primary wide" disabled={busy || !touched} onClick={() => run(signal => validate({ type: 'map_pin', ...location }, signal), 'validating')}>이 위치에서 출발</button></>}
      {mode === 'saved' && <><div className="origin-places">{items.map(item => <button className="secondary" key={item.place_id} disabled={busy}
        onClick={() => run(signal => validate({ type: 'saved_place', place_id: item.place_id, location_version: item.location_version }, signal), 'validating')}>
        <strong>{item.label}</strong><span>{item.location_address || item.address}</span></button>)}</div>
        {!busy && !items.length && <p>저장한 장소가 없어요. 내 설정에서 장소를 저장하거나 지도를 선택해주세요.</p>}
        {cursor && <button className="secondary wide" disabled={busy} onClick={() => load(true)}>장소 더 보기</button>}</>}
      {phase === 'error' && <button className="text-button" disabled={busy} onClick={() => load()}>목록 다시 확인</button>}
    </>}
  </div>;
}
