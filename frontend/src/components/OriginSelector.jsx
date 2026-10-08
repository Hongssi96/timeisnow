import React, { useEffect, useRef, useState } from 'react';
import { apiRequest, ApiError, isServerTime } from '../lib/api';
import { getCurrentOrigin } from '../lib/currentOrigin';
import MapPinPicker from './MapPinPicker';
import OriginReview from './OriginReview';
import PlacesCard from './PlacesCard';
import PinPlaceSave from './PinPlaceSave';

const validLocation = value => Number.isFinite(value?.latitude) && Math.abs(value.latitude) <= 90
  && Number.isFinite(value?.longitude) && Math.abs(value.longitude) <= 180;
const validPlace = value => typeof value?.place_id === 'string' && typeof value.label === 'string'
  && validLocation(value.location) && Number.isInteger(value.location_version) && value.location_version >= 1;

export default function OriginSelector({ onSelect, onLogin, onAuthError, onBusyChange, purpose = 'origin', initialMode = 'current', initialLocation = null }) {
  const noun = purpose === 'destination' ? '도착' : '출발';
  const [mode, setMode] = useState(initialMode);
  const [phase, setPhase] = useState('loading');
  const [items, setItems] = useState([]);
  const [cursor, setCursor] = useState(null);
  const [message, setMessage] = useState('');
  const [location, setLocation] = useState({ latitude: 37.5665, longitude: 126.9780 });
  const [touched, setTouched] = useState(false);
  const [draft, setDraft] = useState(null);
  const [expired, setExpired] = useState(false);
  const [creatingBusy, setCreatingBusy] = useState(false);
  const [pinSaving, setPinSaving] = useState(false);
  const [newPin, setNewPin] = useState(() => validLocation(initialLocation) ? initialLocation : null);
  useEffect(() => {
    setExpired(false);
    if (!draft) return;
    const timer = setTimeout(() => {
      pending.current?.abort(); pending.current = null; setPhase('ready');
      setDraft(null); setMessage(`${noun}지 확인 화면이 만료됐어요. 현재 위치를 다시 측정해주세요.`);
    }, Math.max(0, draft.deadline - Date.now()));
    return () => clearTimeout(timer);
  }, [draft]);
  const pending = useRef(null);
  const busy = ['loading', 'locating', 'validating'].includes(phase);
  useEffect(() => { onBusyChange?.(creatingBusy); }, [creatingBusy, onBusyChange]);
  useEffect(() => () => onBusyChange?.(false), [onBusyChange]);
  function authError(error) {
    setPinSaving(false); setNewPin(null);
    pending.current?.abort(); setDraft(null); setItems([]); setCursor(null); setTouched(false);
    setLocation({ latitude: 37.5665, longitude: 126.9780 }); setMode('current');
    setPhase('anonymous'); setMessage(error.message); onAuthError?.();
  }
  async function run(operation, nextPhase, failurePrefix = '') {
    if (pending.current) return;
    const controller = new AbortController(); pending.current = controller;
    setPhase(nextPhase); setMessage('');
    try { await operation(controller.signal); }
    catch (error) {
      if (controller.signal.aborted) return;
      if (['AUTH_REQUIRED', 'SESSION_EXPIRED'].includes(error.code)) { authError(error); return; }
      if (error.code?.startsWith('GEO_')) { setMode('map'); setTouched(false); }
      if (['VERSION_CONFLICT', 'RESOURCE_NOT_FOUND'].includes(error.code)) { setItems([]); setCursor(null); }
      setMessage(failurePrefix + (error.message || '다시 시도해주세요.')); setPhase('error');
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
    if (next === 'new' && mode === 'map' && touched) setNewPin({ ...location });
    setPinSaving(false);
    setDraft(null);
    pending.current?.abort(); pending.current = null; setMode(next); setTouched(false); setMessage('');
    setPhase(previous => previous === 'anonymous' ? previous : 'ready');
  }
  function created(place) {
    changeMode('saved');
    if (!validPlace(place)) {
      setPhase('error'); setMessage('장소는 저장됐어요. 목록 다시 확인을 눌러 선택해주세요.'); return;
    }
    setItems(previous => [place, ...previous.filter(item => item.place_id !== place.place_id)]);
    run(signal => validate({ type: 'saved_place', place_id: place.place_id, location_version: place.location_version }, signal), 'validating', '장소는 저장됐어요. 선택을 다시 확인해주세요. ');
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
    <p className="muted">{noun}지를 선택해주세요. 출발 시간 안내는 준비 중이에요.</p>
    {phase === 'anonymous' ? <><p role="alert">{message}</p><button className="primary wide" onClick={onLogin}>로그인하기</button></> : <>
      <div className="origin-methods" role="group" aria-label={`${noun}지 선택 방법`}>{[['current','현재 위치'],['map','지도 선택'],['saved','저장 장소'],['new','장소 저장']].map(([key,label]) =>
        <button className="secondary" key={key} aria-pressed={mode === key} disabled={phase === 'loading' || creatingBusy} onClick={() => changeMode(key)}>{label}</button>)}</div>
      {message && <p className="info-box" role="alert">{message}</p>}
      {busy && <p role="status">{phase === 'locating' ? '기기 위치 권한을 확인하고 있어요. 최대 15초 기다려요.' : phase === 'validating' ? `${noun}지를 확인하고 있어요.` : '내 장소를 확인하고 있어요.'}</p>}
      {mode === 'new' && <div className="origin-place-create"><p className="info-box">이 화면에서 장소를 저장하면 바로 {noun}지로 선택해요.</p>{newPin ? <>
        <MapPinPicker location={newPin} mapLabel={`${noun}지 저장 지도`} disabled={creatingBusy}
          onAuthError={authError} onChange={setNewPin} description="앞에서 선택한 지도 위치를 그대로 가져왔어요. 필요하면 핀을 옮겨주세요."/>
        <PinPlaceSave key={`${newPin.latitude}:${newPin.longitude}`} location={newPin} initialLabel={`${noun}지`}
          onCreated={created} onAuthError={authError} onBusyChange={setCreatingBusy} onCancel={() => changeMode('saved')}/>
      </> : <><PlacesCard creationOnly initialLabel={`${noun}지`} title={`${noun} 장소 저장`} onLogin={onLogin} onAuthError={authError} onCreated={created} onBusyChange={setCreatingBusy}/><button className="secondary wide" disabled={creatingBusy} onClick={() => changeMode('saved')}>장소 저장 취소</button></>}</div>}
      {mode === 'current' && <><p className="small muted">버튼을 누르면 기기 위치를 한 번 요청해요. 선택 좌표는 서울·경기 확인을 위해 카카오로 전달돼요. 위치 추적이나 자동 저장은 하지 않아요.</p>
        <p className="small muted">GPS 수치 기준은 보류 중이에요. 측정 후 지도에서 실제 {noun} 위치를 직접 확인해주세요. 저장 장소는 직접 선택해요.</p>
        <button className="secondary wide" disabled={busy} onClick={current}>{draft ? '현재 위치 다시 측정' : '현재 위치 확인'}</button>
        {draft && <OriginReview purpose={purpose} draft={draft} busy={busy} expired={expired} onAuthError={authError}
          onChange={point => { changeMode('map'); setLocation(point); setTouched(true); }}
          onConfirm={() => { if (Date.now() >= draft.deadline) { setExpired(true); return; }
            run(signal => validate({ ...draft.origin, location_confirmed: true }, signal), 'validating'); }}/>}</>}
      {mode === 'map' && <><MapPinPicker location={location} mapLabel={`${noun}지 선택 지도`}
        description={`시작 핀은 현재 위치가 아니에요. 지도를 누르거나 핀을 옮겨 ${noun}지를 직접 선택해주세요. 선택 위치가 카카오 지도에 표시돼요.`}
        disabled={busy || creatingBusy || pinSaving} onAuthError={authError} onChange={point => { setLocation(point); setTouched(true); setMessage(''); }}/>
        {pinSaving ? <PinPlaceSave location={location} initialLabel={`${noun}지`} onCreated={created}
          onCancel={() => setPinSaving(false)} onAuthError={authError} onBusyChange={setCreatingBusy}/> : <>
          <button className="primary wide" disabled={busy || !touched} onClick={() => setPinSaving(true)}>이 위치 저장하고 사용</button>
          <button className="secondary wide" disabled={busy || !touched} onClick={() => run(signal => validate({ type: 'map_pin', ...location }, signal), 'validating')}>{purpose === 'destination' ? '이 위치로 도착' : '이 위치에서 출발'}</button></>}</>}
      {mode === 'saved' && <><div className="origin-places">{items.map(item => <button className="secondary" key={item.place_id} disabled={busy}
        onClick={() => run(signal => validate({ type: 'saved_place', place_id: item.place_id, location_version: item.location_version }, signal), 'validating')}>
        <strong>{item.label}</strong><span>{item.location_address || item.address}</span></button>)}</div>
        {!busy && !items.length && <p>저장한 장소가 없어요. 여기에서 새 장소를 저장하고 선택할 수 있어요.</p>}
        <button className="secondary wide" disabled={busy} onClick={() => changeMode('new')}>새 장소 저장하고 선택</button>
        {cursor && <button className="secondary wide" disabled={busy} onClick={() => load(true)}>장소 더 보기</button>}</>}
      {phase === 'error' && <button className="text-button" disabled={busy} onClick={() => load()}>목록 다시 확인</button>}
    </>}
  </div>;
}
