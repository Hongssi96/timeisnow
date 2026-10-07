import React, { useEffect, useRef, useState } from 'react';
import { Home, MapPin, Plus, RefreshCw } from 'lucide-react';
import { apiRequest, ApiError, isServerTime } from './api';

const validLocation = value => Number.isFinite(value?.latitude) && Math.abs(value.latitude) <= 90
  && Number.isFinite(value?.longitude) && Math.abs(value.longitude) <= 180;
const validCandidate = value => typeof value?.candidate_id === 'string' && typeof value.name === 'string'
  && typeof value.address === 'string' && validLocation(value.location);
const validPlace = value => typeof value?.place_id === 'string' && typeof value.label === 'string'
  && typeof value.name === 'string' && typeof value.address === 'string' && validLocation(value.location);

export default function PlacesCard({ onLogin }) {
  const [items, setItems] = useState([]);
  const [cursor, setCursor] = useState(null);
  const [phase, setPhase] = useState('loading');
  const [message, setMessage] = useState('');
  const [editing, setEditing] = useState(false);
  const [query, setQuery] = useState('');
  const [label, setLabel] = useState('집');
  const [result, setResult] = useState(null);
  const [selected, setSelected] = useState(null);
  const [expired, setExpired] = useState(false);
  const pending = useRef(null);
  const creation = useRef(null);
  const busy = ['loading', 'searching', 'saving'].includes(phase);

  async function run(operation, nextPhase) {
    if (pending.current) return;
    const controller = new AbortController(); pending.current = controller;
    setPhase(nextPhase); setMessage('');
    try { await operation(controller.signal); }
    catch (error) {
      if (!controller.signal.aborted) {
        if (['AUTH_REQUIRED', 'SESSION_EXPIRED'].includes(error.code)) {
          setItems([]); setCursor(null); setResult(null); setSelected(null); setEditing(false);
          creation.current = null; setPhase('anonymous');
        } else {
          setPhase('error');
          if (error.code === 'RESOURCE_NOT_FOUND') { setExpired(true); setSelected(null); creation.current = null; }
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
  useEffect(() => { load(); return () => { pending.current?.abort(); pending.current = null; }; }, []);
  useEffect(() => {
    if (!result) return;
    const remaining = result.deadline - Date.now();
    if (remaining <= 0) { setExpired(true); return; }
    const timer = setTimeout(() => setExpired(true), remaining);
    return () => clearTimeout(timer);
  }, [result]);

  async function write(path, body, signal, headers = {}) {
    const csrf = await apiRequest('/api/v1/auth/csrf', { signal });
    if (typeof csrf.data?.csrf_token !== 'string') throw new ApiError('INVALID_RESPONSE');
    return apiRequest(path, { method: 'POST', body, signal, headers: { 'X-CSRF-Token': csrf.data.csrf_token, ...headers } });
  }
  function search(event) {
    event.preventDefault(); setResult(null); setSelected(null); setExpired(false); creation.current = null;
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
    const body = { label: label.trim(), location: selected.location, search_id: result.search_id, candidate_id: selected.candidate_id };
    const signature = JSON.stringify(body);
    if (creation.current?.signature !== signature) creation.current = { signature, key: crypto.randomUUID() };
    run(async signal => {
      const response = await write('/api/v1/places', body, signal, { 'Idempotency-Key': creation.current.key });
      if (!validPlace(response.data)) throw new ApiError('INVALID_RESPONSE');
      if (signal.aborted) return;
      setItems(previous => [response.data, ...previous.filter(item => item.place_id !== response.data.place_id)]);
      setResult(null); setSelected(null); setQuery(''); setEditing(false); creation.current = null;
      setMessage('장소를 저장했어요.'); setPhase('ready');
    }, 'saving');
  }

  return <section className="card places-card" aria-busy={busy}>
    <div className="section-heading"><h2>내 장소</h2>{phase !== 'anonymous' && <button className="text-button" disabled={busy} onClick={() => { setEditing(value => !value); setMessage(''); }}><Plus size={17}/>장소 추가</button>}</div>
    <p className="muted small">집·회사 주소를 검색해 내 계정에 저장해요. 서울·경기를 지원해요.</p>
    {message && <p role={phase === 'error' || phase === 'anonymous' ? 'alert' : 'status'}>{message}</p>}
    {phase === 'anonymous' ? <button className="primary" onClick={onLogin}>로그인하고 장소 저장</button> : <>
      {phase === 'loading' && <p role="status">저장된 장소를 확인하고 있어요.</p>}
      {!items.length && phase === 'ready' && <p className="muted">아직 저장한 장소가 없어요. 집이나 회사를 추가해주세요.</p>}
      {items.map(item => <div className="place-row" key={item.place_id}><span className="soft-icon">{item.label === '집' ? <Home size={20}/> : <MapPin size={20}/>}</span><span><strong>{item.label}</strong><small>{item.name}</small><small>{item.address}</small></span></div>)}
      {cursor && <button className="secondary" disabled={busy} onClick={() => load(true)}>장소 더 보기</button>}
      {phase === 'error' && <button className="text-button" disabled={busy} onClick={() => load()}><RefreshCw size={17}/>목록 다시 확인</button>}
      {editing && <div className="place-form">
        <form onSubmit={search}><label>주소 또는 장소 이름<input required maxLength={100} value={query} disabled={busy} onChange={event => { setQuery(event.target.value); setResult(null); setSelected(null); creation.current = null; }} placeholder="예: 강남역, 도로명 주소"/></label><button className="secondary wide" type="submit" disabled={busy || !query.trim()}>{phase === 'searching' ? '검색 중…' : '주소 검색'}</button></form>
        {result && !expired && <><p className="muted small">검색 결과는 10분 동안 선택할 수 있어요.</p>{!result.candidates.length && <p role="status">검색 결과가 없어요. 서울·경기 주소나 다른 이름으로 검색해주세요.</p>}<div className="place-candidates" role="group" aria-label="검색 결과">{result.candidates.map(candidate => <button className={'place-candidate ' + (selected?.candidate_id === candidate.candidate_id ? 'selected' : '')} type="button" key={candidate.candidate_id} disabled={busy} aria-pressed={selected?.candidate_id === candidate.candidate_id} onClick={() => { setSelected(candidate); creation.current = null; }}><strong>{candidate.name}</strong><span>{candidate.address}</span></button>)}</div></>}
        {expired && <p role="status" className="info-box">검색 결과가 만료됐어요. 주소를 다시 검색해주세요.</p>}
        {selected && !expired && <form onSubmit={save}><label>저장할 이름<input required maxLength={30} value={label} disabled={busy} onChange={event => setLabel(event.target.value)} placeholder="예: 집, 회사"/></label><p className="info-box">{selected.name}<br/>{selected.address}<br/>검색된 위치를 저장해요. 출입구·지도 핀 확인은 준비 중이에요.</p><button className="primary wide" type="submit" disabled={busy || !label.trim()}>{phase === 'saving' ? '저장 중…' : '선택한 장소 저장'}</button></form>}
      </div>}
    </>}
  </section>;
}
