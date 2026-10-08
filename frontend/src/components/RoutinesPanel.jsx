import React, { useEffect, useRef, useState } from 'react';
import { ArrowRight, Repeat2, Trash2 } from 'lucide-react';
import { apiRequest, ApiError } from '../lib/api';
import { WEEKDAYS, placeLabel, validRoutine, needsRoutineRecovery, routineRecoveryMessage } from '../lib/routines';
import { formatJourneyTime } from '../lib/journeys';

export function RoutineSummary({ routine }) {
  const recovery=needsRoutineRecovery(routine);
  return <><p>{placeLabel(routine.origin_place)} → {placeLabel(routine.destination_place)}</p>
    <div className="day-list" aria-label="반복 요일">{WEEKDAYS.map((day, index) => <span key={day} className={routine.weekdays.includes(index + 1) ? 'on' : ''}>{day}</span>)}</div>
    <div className="routine-details"><span>목표 도착 <strong>{routine.target_arrival_local_time || '설정 안 함'}</strong></span>{!recovery&&<span>환승 <strong>{routine.route.transfer_count}회</strong></span>}</div>
    {recovery?<div className="info-box routine-recovery-notice"><strong>루틴 복구가 필요해요</strong><p>{routineRecoveryMessage(routine)}</p><p>이전 경로의 예상 시간은 사용하지 않아요. 이름과 반복 일정은 유지돼요.</p></div>:<p className="candidate-note">공급자 예상 약 {formatJourneyTime(routine.route.total_seconds)} · 실제 운행·도보 확인 필요</p>}</>;
}
export function RoutineStatus({ state, onRetry, onLogin, onAdd }) {
  if (state.phase === 'loading') return <p role="status" className="info-box">루틴을 불러오고 있어요…</p>;
  if (state.phase === 'anonymous') return <div className="empty-state"><Repeat2 size={32}/><h2>로그인하고 내 루틴을 확인해요</h2><p>저장한 경로와 반복 일정을 불러올 수 있어요.</p><button className="primary" onClick={onLogin}>로그인하기</button></div>;
  if (state.phase === 'error') return <div className="info-box" role="alert"><p>{state.message}</p><button className="secondary" onClick={onRetry}>루틴 다시 확인</button></div>;
  if (!state.items.length) return <div className="empty-state"><Repeat2 size={32}/><h2>저장한 루틴이 없어요</h2><p>출발·도착 장소를 고르고 경로를 루틴에 저장해보세요.</p><button className="primary" onClick={onAdd}>경로 찾아 루틴 추가 <ArrowRight size={16}/></button></div>;
  return null;
}
export default function RoutinesPanel({ state, onRetry, onMore, onLogin, onAdd, onSelect, onRouteChange, onChanged, onAuthError }) {
  const [editing, setEditing] = useState(null), [deleting, setDeleting] = useState(null), [feedback, setFeedback] = useState(null);
  const [busy, setBusy] = useState(false);
  const pending = useRef(null);
  useEffect(() => () => pending.current?.abort(), []);
  useEffect(() => { setEditing(null); setDeleting(null); setFeedback(null); }, [state.items]);
  async function mutate(routine, method, body) {
    if (pending.current) return;
    const controller = new AbortController(); pending.current = controller; setBusy(true); setFeedback(null);
    try {
      const csrf = await apiRequest('/api/v1/auth/csrf', { signal: controller.signal });
      if (typeof csrf.data?.csrf_token !== 'string') throw new ApiError('INVALID_RESPONSE');
      const response = await apiRequest('/api/v1/routines/' + routine.routine_id, { method, body,
        signal: controller.signal, headers: { 'X-CSRF-Token': csrf.data.csrf_token } });
      if (controller.signal.aborted) return;
      if (method === 'DELETE' ? response.status !== 204 : response.status !== 200 || !validRoutine(response.data) || response.data.routine_id !== routine.routine_id || response.data.version !== routine.version + 1) throw new ApiError('INVALID_RESPONSE');
      setEditing(null); setDeleting(null); onChanged(method === 'DELETE' ? '루틴을 삭제했어요.' : '루틴을 수정했어요.');
    } catch (error) {
      if (!controller.signal.aborted) {
        if (['AUTH_REQUIRED', 'SESSION_EXPIRED'].includes(error.code)) { setEditing(null); setDeleting(null); onAuthError(); }
        else setFeedback(['VERSION_CONFLICT', 'RESOURCE_NOT_FOUND'].includes(error.code)
          ? '루틴이 변경되거나 삭제됐어요. 루틴 다시 확인을 눌러 최신 내용을 불러와주세요.' : error.message);
      }
    } finally { if (pending.current === controller) { pending.current = null; setBusy(false); } }
  }
  return <div className="routines-panel" aria-busy={busy}>
    <div className="section-heading"><h2>저장한 루틴 <span className="count">{state.items.length}</span></h2><div className="button-row"><button className="secondary" disabled={busy || state.phase === 'loading'} onClick={onRetry}>루틴 다시 확인</button><button className="primary compact" disabled={busy} onClick={onAdd}>루틴 추가</button></div></div>
    <RoutineStatus state={state} onRetry={onRetry} onLogin={onLogin} onAdd={onAdd}/>
    {feedback && <p className="info-box" role="alert">{feedback}</p>}
    <div className="routine-grid">{state.items.map(routine => <section className="card routine-card" key={routine.routine_id}>
      <span className="soft-icon"><Repeat2/></span><h2>{routine.name}</h2><RoutineSummary routine={routine}/>
      {editing === routine.routine_id ? <RoutineEditor key={routine.routine_id + ':' + routine.version} routine={routine} busy={busy}
        onCancel={() => { setEditing(null); setFeedback(null); }} onSave={body => mutate(routine, 'PATCH', body)}/> :
      deleting === routine.routine_id ? <div className="place-delete-confirm"><p>‘{routine.name}’ 루틴을 삭제할까요?</p><div className="button-row"><button autoFocus className="secondary" disabled={busy} onClick={() => setDeleting(null)}>취소</button><button className="primary" disabled={busy} onClick={() => mutate(routine, 'DELETE')}>삭제 확인</button></div></div> :
      <div className="routine-actions"><button className="secondary" disabled={busy} onClick={() => { setEditing(routine.routine_id); setFeedback(null); }}>수정</button>
        <button className="text-button" disabled={busy} onClick={() => onRouteChange(routine)}>{needsRoutineRecovery(routine)?'루틴 복구하기':'경로 바꾸기'}</button>
        <button className="text-button" disabled={busy} onClick={() => { setDeleting(routine.routine_id); setFeedback(null); }}><Trash2 size={16}/>삭제</button>
        <button className="primary" disabled={busy} onClick={() => onSelect(routine)}>루틴 선택 <ArrowRight size={16}/></button></div>}
    </section>)}</div>
    {state.next && <button className="secondary wide" disabled={busy || state.phase === 'more'} onClick={onMore}>{state.phase === 'more' ? '더 불러오는 중…' : '루틴 더 보기'}</button>}
  </div>;
}
function RoutineEditor({ routine, busy, onCancel, onSave }) {
  const [name, setName] = useState(routine.name), [days, setDays] = useState(routine.weekdays), [target, setTarget] = useState(routine.target_arrival_local_time || '');
  return <form className="routine-name-panel" onSubmit={event => { event.preventDefault(); if (!busy && name.trim() && days.length) onSave({ expected_version: routine.version, name: name.trim(), weekdays: days, target_arrival_local_time: target || null }); }}>
    <label>루틴 이름<input autoFocus required maxLength={30} disabled={busy} value={name} onChange={event => setName(event.target.value)}/></label>
    <fieldset className="routine-days"><legend>반복 요일</legend><div className="day-list selectable">{WEEKDAYS.map((day, index) => <button key={day} type="button" disabled={busy} className={days.includes(index + 1) ? 'on' : ''} aria-pressed={days.includes(index + 1)} onClick={() => setDays(values => values.includes(index + 1) ? values.filter(value => value !== index + 1) : [...values, index + 1].sort())}>{day}</button>)}</div></fieldset>
    <label>목표 도착 시각 (선택)<input type="time" disabled={busy} value={target} onChange={event => setTarget(event.target.value)}/></label>
    <div className="routine-name-actions"><button className="primary" type="submit" disabled={busy || !name.trim() || !days.length}>{busy ? '저장 중…' : '변경 저장'}</button><button className="secondary" type="button" disabled={busy} onClick={onCancel}>취소</button></div>
  </form>;
}
