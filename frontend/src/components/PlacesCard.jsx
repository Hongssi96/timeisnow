import React, { useEffect, useRef, useState } from 'react';
import { Home, MapPin, Plus, RefreshCw, Pencil, Trash2 } from 'lucide-react';
import { apiRequest, ApiError, isServerTime } from '../lib/api';
import LocationConfirmation from './LocationConfirmation';

const validLocation = value => Number.isFinite(value?.latitude) && Math.abs(value.latitude) <= 90
  && Number.isFinite(value?.longitude) && Math.abs(value.longitude) <= 180;
const validCandidate = value => typeof value?.candidate_id === 'string' && typeof value.name === 'string'
  && typeof value.address === 'string' && validLocation(value.location);
const validPlace = value => typeof value?.place_id === 'string' && typeof value.label === 'string'
  && typeof value.name === 'string' && typeof value.address === 'string' && validLocation(value.location)
  && Number.isInteger(value.version) && value.version >= 1;

export default function PlacesCard({ onLogin, onCreated, onAuthError, onBusyChange, creationOnly = false, initialLabel = '집', title }) {
  const [items, setItems] = useState([]);
  const [cursor, setCursor] = useState(null);
  const [phase, setPhase] = useState(creationOnly ? 'ready' : 'loading');
  const [message, setMessage] = useState('');
  const [editing, setEditing] = useState(creationOnly);
  const [query, setQuery] = useState('');
  const [label, setLabel] = useState(initialLabel);
  const [result, setResult] = useState(null);
  const [selected, setSelected] = useState(null);
  const [expired, setExpired] = useState(false);
  const [mapOpen, setMapOpen] = useState(false);
  const [editPlace, setEditPlace] = useState(null);
  const [entranceNote, setEntranceNote] = useState('');
  const [pinPending, setPinPending] = useState(false);
  const [pinSelection, setPinSelection] = useState(null);
  const [renamePlace, setRenamePlace] = useState(null);
  const [renameLabel, setRenameLabel] = useState('');
  const [deletePlace, setDeletePlace] = useState(null);
  const pending = useRef(null);
  const creation = useRef(null);
  const busy = ['loading', 'searching', 'saving', 'deleting'].includes(phase);
  useEffect(() => { onBusyChange?.(busy); }, [busy, onBusyChange]);
  useEffect(() => () => onBusyChange?.(false), [onBusyChange]);

  function resetPin() { setMapOpen(false); setEntranceNote(''); setPinPending(false); setPinSelection(null); }
  function authError(error) {
    pending.current?.abort(); setItems([]); setCursor(null); setResult(null); setSelected(null);
    setEditing(false); setEditPlace(null); resetPin(); creation.current = null;
    setRenamePlace(null); setDeletePlace(null); setRenameLabel('');
    setPhase('anonymous'); setMessage(error.message);
    onAuthError?.(error);
  }

  async function run(operation, nextPhase) {
    if (pending.current) return;
    const controller = new AbortController(); pending.current = controller;
    setPhase(nextPhase); setMessage('');
    try { await operation(controller.signal); }
    catch (error) {
      if (!controller.signal.aborted) {
        if (['AUTH_REQUIRED', 'SESSION_EXPIRED'].includes(error.code)) {
          authError(error);
        } else {
          setPhase('error');
          if (error.code === 'RESOURCE_NOT_FOUND') { setExpired(true); setSelected(null); creation.current = null; }
          const changedPlace = editPlace || renamePlace;
          if (error.code === 'RESOURCE_NOT_FOUND' && changedPlace) {
            setItems(previous => previous.filter(item => item.place_id !== changedPlace.place_id));
            setEditPlace(null); setRenamePlace(null); setCursor(null); resetPin();
          }
          if (error.code === 'VERSION_CONFLICT' && changedPlace) {
            setEditPlace(null); setRenamePlace(null); resetPin();
            try {
              const response = await apiRequest('/api/v1/places/' + encodeURIComponent(changedPlace.place_id), {signal:controller.signal});
              if (!validPlace(response.data)) throw new ApiError('INVALID_RESPONSE');
              if (!controller.signal.aborted) setItems(previous => previous.map(item => item.place_id === response.data.place_id ? response.data : item));
            } catch (refreshError) {
              if (controller.signal.aborted) return;
              if (['AUTH_REQUIRED','SESSION_EXPIRED'].includes(refreshError.code)) {authError(refreshError);return;}
              if (refreshError.code === 'RESOURCE_NOT_FOUND') {
                setItems(previous => previous.filter(item => item.place_id !== changedPlace.place_id)); setCursor(null);
              }
              setMessage('장소가 변경됐어요. 목록 다시 확인을 눌러 최신 상태를 확인해주세요.'); return;
            }
          }
        }
        setMessage(error.message || '다시 시도해주세요.');
      }
    } finally { if (pending.current === controller) pending.current = null; }
  }

  function load(more = false) {
    return run(async signal => {
      const response = await apiRequest('/api/v1/places' + (more && cursor ? '?cursor=' + encodeURIComponent(cursor) : ''), { signal });
      if (!Array.isArray(response.data?.items) || !response.data.items.every(validPlace)
        || !(response.data.next_cursor === null || typeof response.data.next_cursor === 'string')) throw new ApiError('INVALID_RESPONSE');
      if (signal.aborted) return;
      setItems(previous => more ? [...previous, ...response.data.items] : response.data.items);
      setCursor(response.data.next_cursor); setPhase('ready');
    }, 'loading');
  }
  useEffect(() => { if (!creationOnly) load(); return () => { pending.current?.abort(); pending.current = null; }; }, []);
  useEffect(() => {
    if (!result) return;
    const remaining = result.deadline - Date.now();
    if (remaining <= 0) { setExpired(true); return; }
    const timer = setTimeout(() => setExpired(true), remaining);
    return () => clearTimeout(timer);
  }, [result]);

  async function write(path, body, signal, headers = {}, method = 'POST') {
    const csrf = await apiRequest('/api/v1/auth/csrf', { signal });
    if (typeof csrf.data?.csrf_token !== 'string') throw new ApiError('INVALID_RESPONSE');
    return apiRequest(path, { method, body, signal, headers: { 'X-CSRF-Token': csrf.data.csrf_token, ...headers } });
  }
  function search(event) {
    event.preventDefault(); setResult(null); setSelected(null); setExpired(false); resetPin(); creation.current = null;
    run(async signal => {
      const response = await write('/api/v1/place-searches', { query: query.trim() }, signal);
      if (typeof response.data?.search_id !== 'string' || !isServerTime(response.data.expires_at)
        || !isServerTime(response.meta.server_time) || !Array.isArray(response.data.candidates)
        || !response.data.candidates.every(validCandidate)) throw new ApiError('INVALID_RESPONSE');
      if (signal.aborted) return;
      const remaining = Date.parse(response.data.expires_at) - Date.parse(response.meta.server_time);
      setResult({ ...response.data, deadline: Date.now() + remaining }); setExpired(remaining <= 0); setPhase('ready');
    }, 'searching');
  }
  function save(event) {
    event.preventDefault();
    if (!selected || !result || expired || Date.now() >= result.deadline) { setExpired(true); return; }
    if (pinPending && (!pinSelection || Date.now() >= pinSelection.deadline)) return;
    const body = { label: label.trim(), location: pinSelection?.location || selected.location, search_id: result.search_id, candidate_id: selected.candidate_id,
      ...(pinSelection ? {location_confirmation_id:pinSelection.confirmation_id} : {}), ...(entranceNote.trim() ? {entrance_note:entranceNote.trim()} : {}) };
    const signature = JSON.stringify(body);
    if (creation.current?.signature !== signature) creation.current = { signature, key: crypto.randomUUID() };
    run(async signal => {
      const response = await write('/api/v1/places', body, signal, { 'Idempotency-Key': creation.current.key });
      if (!validPlace(response.data) || (creationOnly && (!Number.isInteger(response.data.location_version) || response.data.location_version < 1))) throw new ApiError('INVALID_RESPONSE');
      if (signal.aborted) return;
      setItems(previous => [response.data, ...previous.filter(item => item.place_id !== response.data.place_id)]);
      setResult(null); setSelected(null); setQuery(''); setEditing(false); resetPin(); creation.current = null;
      setMessage('장소를 저장했어요.'); setPhase('ready');
      onCreated?.(response.data);
    }, 'saving');
  }

  function edit(item) {
    setRenamePlace(null); setDeletePlace(null);
    setEditing(false); setSelected(null); setResult(null); resetPin();
    setEditPlace(item); setEntranceNote(item.entrance_note || ''); setMessage('');
  }
  function update(event) {
    event.preventDefault();
    if (pinPending && (!pinSelection || Date.now() >= pinSelection.deadline)) return;
    const body = { expected_version:editPlace.version, entrance_note:entranceNote.trim() || null,
      ...(pinSelection ? {location:pinSelection.location,location_confirmation_id:pinSelection.confirmation_id} : {}) };
    run(async signal => {
      const response = await write('/api/v1/places/' + encodeURIComponent(editPlace.place_id), body, signal, {}, 'PATCH');
      if (!validPlace(response.data)) throw new ApiError('INVALID_RESPONSE');
      if (signal.aborted) return;
      setItems(previous => previous.map(item => item.place_id === response.data.place_id ? response.data : item));
      setEditPlace(null); resetPin(); setMessage('위치·출입구를 저장했어요.'); setPhase('ready');
    }, 'saving');
  }
  function rename(item) {
    setEditPlace(null); setEditing(false); resetPin(); setDeletePlace(null);
    setRenamePlace(item); setRenameLabel(item.label); setMessage('');
  }
  function renameSave(event) {
    event.preventDefault();
    run(async signal => {
      const response = await write('/api/v1/places/' + encodeURIComponent(renamePlace.place_id),
        {label:renameLabel.trim(), expected_version:renamePlace.version}, signal, {}, 'PATCH');
      if (!validPlace(response.data)) throw new ApiError('INVALID_RESPONSE');
      if (signal.aborted) return;
      setItems(previous => previous.map(item => item.place_id === response.data.place_id ? response.data : item));
      setRenamePlace(null); setRenameLabel(''); setMessage('장소 이름을 저장했어요.'); setPhase('ready');
    }, 'saving');
  }
  function askDelete(item) {
    setEditPlace(null); setEditing(false); resetPin(); setRenamePlace(null);
    setDeletePlace(item); setMessage('');
  }
  function remove() {
    const target = deletePlace;
    run(async signal => {
      let alreadyMissing = false;
      try {
        const response = await write('/api/v1/places/' + encodeURIComponent(target.place_id), undefined, signal, {}, 'DELETE');
        if (response.status !== 204) throw new ApiError('INVALID_RESPONSE');
      } catch (error) {
        if (error.code !== 'RESOURCE_NOT_FOUND') throw error;
        alreadyMissing = true;
      }
      if (signal.aborted) return;
      setItems(previous => previous.filter(item => item.place_id !== target.place_id));
      setCursor(null); setDeletePlace(null); setEditing(false); setResult(null); setSelected(null);
      const success = alreadyMissing ? '이미 삭제된 장소예요. 목록을 다시 확인했어요.' : '장소를 삭제했어요.';
      try {
        const response = await apiRequest('/api/v1/places', {signal});
        if (!Array.isArray(response.data?.items) || !response.data.items.every(validPlace)
          || !(response.data.next_cursor === null || typeof response.data.next_cursor === 'string')) throw new ApiError('INVALID_RESPONSE');
        if (signal.aborted) return;
        setItems(response.data.items); setCursor(response.data.next_cursor); setMessage(success); setPhase('ready');
      } catch (error) {
        if (signal.aborted) return;
        if (['AUTH_REQUIRED','SESSION_EXPIRED'].includes(error.code)) {authError(error);return;}
        setMessage('장소는 삭제됐어요. 목록을 다시 불러오지 못했어요. 목록 다시 확인을 눌러주세요.'); setPhase('error');
      }
    }, 'deleting');
  }
  const pinProps = { disabled:busy, onDraft:() => setPinPending(true),
    onConfirmed:value => {setPinSelection(value); setPinPending(true);}, onAuthError:authError };

  return <section className="card places-card" aria-busy={busy}>
    <div className="section-heading"><h2>{title || (creationOnly ? '새 장소 저장' : '내 장소')}</h2>{!creationOnly && phase !== 'anonymous' && <button className="text-button" disabled={busy} onClick={() => { setEditing(value => !value); setEditPlace(null); setRenamePlace(null); setDeletePlace(null); resetPin(); setMessage(''); }}><Plus size={17}/>장소 추가</button>}</div>
    <p className="muted small">집·회사 주소를 검색해 내 계정에 저장해요. 서울·경기를 지원해요.</p>
    {message && <p role={phase === 'error' || phase === 'anonymous' ? 'alert' : 'status'}>{message}</p>}
    {phase === 'anonymous' ? <button className="primary" onClick={onLogin}>로그인하고 장소 저장</button> : <>
      {phase === 'loading' && <p role="status">저장된 장소를 확인하고 있어요.</p>}
      {!creationOnly && !items.length && phase === 'ready' && <p className="muted">아직 저장한 장소가 없어요. 집이나 회사를 추가해주세요.</p>}
      {!creationOnly && items.map(item => <div className="saved-place" key={item.place_id}><div className="place-row"><span className="soft-icon">{item.label === '집' ? <Home size={20}/> : <MapPin size={20}/>}</span><span><strong>{item.label}</strong><small>{item.name}</small><small>{item.address}</small>{item.location_source === 'map_pin' && <small>지도 핀 · {item.location_address}</small>}{item.entrance_note && <small>출입구: {item.entrance_note} · 직접 입력</small>}</span></div><div className="place-actions"><button className="text-button" disabled={busy} aria-label={item.label + ' 위치·출입구 확인'} onClick={() => edit(item)}><MapPin size={17}/>위치·출입구 확인</button><button className="text-button" disabled={busy} aria-label={item.label + ' 이름 수정'} onClick={() => rename(item)}><Pencil size={17}/>이름 수정</button><button className="text-button" disabled={busy} aria-label={item.label + ' 삭제'} onClick={() => askDelete(item)}><Trash2 size={17}/>삭제</button></div></div>)}
      {renamePlace && <form className="place-form" onSubmit={renameSave}><h3>{renamePlace.label} 이름 수정</h3><label>장소 이름<input autoFocus required maxLength={30} disabled={busy} value={renameLabel} onChange={event => setRenameLabel(event.target.value)}/></label><p className="muted small">이름을 바꿔도 저장된 위치와 출입구는 유지돼요.</p><div className="pin-actions"><button type="button" className="secondary" disabled={busy} onClick={() => setRenamePlace(null)}>이름 수정 취소</button><button type="submit" className="primary" disabled={busy || !renameLabel.trim()}>{phase === 'saving' ? '저장 중…' : '이름 저장'}</button></div></form>}
      {deletePlace && <div className="place-delete-confirm" role="group" aria-label="장소 삭제 확인"><h3>{deletePlace.label}을(를) 삭제할까요?</h3><p>저장한 위치와 출입구 설명이 삭제돼요. 다시 사용하려면 장소를 새로 추가해주세요.</p><div className="pin-actions"><button type="button" className="secondary" autoFocus disabled={busy} onClick={() => setDeletePlace(null)}>삭제 취소</button><button type="button" className="primary" disabled={busy} onClick={remove}>{phase === 'deleting' ? '삭제 중…' : '장소 삭제 확인'}</button></div></div>}
      {editPlace && <form className="place-form" onSubmit={update}><h3>{editPlace.label} 위치·출입구</h3><LocationConfirmation key={editPlace.place_id} initialLocation={editPlace.location} {...pinProps}/><label>출입구 설명<input maxLength={100} disabled={busy} value={entranceNote} onChange={event => setEntranceNote(event.target.value)} placeholder="예: 건물 정문, 동쪽 출입구"/></label><p className="muted small">직접 입력한 설명이에요. 위치 변경 후에는 이동 시간을 다시 확인해야 해요.</p><div className="pin-actions"><button type="button" className="secondary" disabled={busy} onClick={() => {setEditPlace(null);resetPin();}}>수정 취소</button><button className="primary" type="submit" disabled={busy || (pinPending && !pinSelection)}>{phase === 'saving' ? '저장 중…' : '위치·출입구 저장'}</button></div></form>}
      {cursor && <button className="secondary" disabled={busy} onClick={() => load(true)}>장소 더 보기</button>}
      {phase === 'error' && <button className="text-button" disabled={busy} onClick={() => load()}><RefreshCw size={17}/>목록 다시 확인</button>}
      {editing && <div className="place-form">
        <form onSubmit={search}><label>주소 또는 장소 이름<input autoFocus={creationOnly} required maxLength={100} value={query} disabled={busy} onChange={event => { setQuery(event.target.value); setResult(null); setSelected(null); resetPin(); creation.current = null; }} placeholder="예: 강남역, 도로명 주소"/></label><button className="secondary wide" type="submit" disabled={busy || !query.trim()}>{phase === 'searching' ? '검색 중…' : '주소 검색'}</button></form>
        {result && !expired && <><p className="muted small">검색 결과는 10분 동안 선택할 수 있어요.</p>{!result.candidates.length && <p role="status">검색 결과가 없어요. 서울·경기 주소나 다른 이름으로 검색해주세요.</p>}<div className="place-candidates" role="group" aria-label="검색 결과">{result.candidates.map(candidate => <button className={'place-candidate ' + (selected?.candidate_id === candidate.candidate_id ? 'selected' : '')} type="button" key={candidate.candidate_id} disabled={busy} aria-pressed={selected?.candidate_id === candidate.candidate_id} onClick={() => { setSelected(candidate); resetPin(); creation.current = null; }}><strong>{candidate.name}</strong><span>{candidate.address}</span></button>)}</div></>}
        {expired && <p role="status" className="info-box">검색 결과가 만료됐어요. 주소를 다시 검색해주세요.</p>}
        {selected && !expired && <><button type="button" className="secondary wide" disabled={busy} onClick={() => setMapOpen(true)}><MapPin size={17}/>지도에서 위치 확인</button>{mapOpen && <LocationConfirmation key={selected.candidate_id} initialLocation={selected.location} {...pinProps}/>}<form onSubmit={save}><label>저장할 이름<input required maxLength={30} value={label} disabled={busy} onChange={event => setLabel(event.target.value)} placeholder="예: 집, 회사"/></label><label>출입구 설명<input maxLength={100} disabled={busy} value={entranceNote} onChange={event => setEntranceNote(event.target.value)} placeholder="예: 건물 정문 (선택)"/></label><p className="info-box">{selected.name}<br/>{selected.address}<br/>검색 위치를 저장하거나 지도에서 출입구를 확인해주세요.</p><button className="primary wide" type="submit" disabled={busy || !label.trim() || (pinPending && !pinSelection)}>{phase === 'saving' ? '저장 중…' : '선택한 장소 저장'}</button></form></>}
      </div>}
    </>}
  </section>;
}
