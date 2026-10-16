import React,{useEffect,useRef,useState} from 'react';
import {segments,mutateSegment} from '../lib/segmentWalking';
const title={station_internal:'역 내부 보행',transfer:'환승 전체 보행'};
const reasons={MISSING_WALK_EVENTS:'시작·도착 누락',INVALID_WALK_INTERVAL:'시각 확인 필요',EVENT_EXCLUDED:'원본 학습 제외',INPUT_DELAY:'입력 지연',BEFORE_RESET:'초기화 이전',MANUALLY_EXCLUDED:'사용자 제외',SCOPE_MISMATCH:'다른 범위',RUNNING:'뛰어서 이동',DETOUR:'다른 경로',ERRAND:'중간 용무',LATE_INPUT:'늦은 입력'};
export default function SegmentWalking({trip,onBusy}){
 const [value,setValue]=useState(null),[draft,setDraft]=useState({}),[state,setState]=useState({}),[retry,setRetry]=useState(0);
 const controller=useRef(null),pending=useRef(null),busy=useRef(false),alive=useRef(true),anchor=trip.progress?.anchor_event_id;
 useEffect(()=>{alive.current=true;const c=new AbortController();controller.current=c;
  segments(trip.trip_id,c.signal).then(v=>{if(!c.signal.aborted){setValue(v);setState({});}}).catch(()=>{if(!c.signal.aborted)setState({error:'구간 기록을 불러오지 못했어요.'});});
  return()=>{alive.current=false;c.abort();controller.current?.abort();onBusy?.(false);};
 },[trip.trip_id,trip.version,anchor,retry]);
 const change=(key,field,v)=>setDraft(old=>({...old,[key]:{...old[key],[field]:v}}));
 async function save(key,kind,item){
  if(busy.current)return;const d=draft[key]||{};
  if(!pending.current){let body={client_request_id:crypto.randomUUID()};
   if(kind==='start')body={...body,kind:item.kind,leg_id:item.leg_id,label:(d.label||'').trim(),occurred_at:new Date().toISOString(),start_boundary_confirmed:!!d.boundary};
   else if(kind==='confirm')body={...body,expected_version:item.version,same_scope:!!d.same,condition:d.condition||'normal',apply_to_guidance:!!d.apply};
   else body={...body,expected_version:item.version,excluded:!item.reasons.includes('MANUALLY_EXCLUDED')};pending.current={kind,id:item.measurement_id,body,key};}
  if(pending.current.key!==key||pending.current.kind!==kind)return;
  busy.current=true;onBusy?.(true);setState({saving:key});const c=new AbortController();controller.current=c;
  try{await mutateSegment(trip.trip_id,pending.current,c.signal);if(!alive.current||c.signal.aborted)return;
   pending.current=null;const v=await segments(trip.trip_id,c.signal);if(!c.signal.aborted){setValue(v);setState({});}}
  catch(e){if(!c.signal.aborted&&alive.current){if(['VALIDATION_ERROR','VERSION_CONFLICT','RESOURCE_NOT_FOUND','INVALID_EVENT_ORDER','CSRF_INVALID'].includes(e.code))pending.current=null;
   setState({error:e.code==='VALIDATION_ERROR'?'시작 위치·구간 이름·승차 지점 도착 기록을 확인해주세요.':e.code==='VERSION_CONFLICT'?'기록이 바뀌었어요. 최신 기록을 확인해주세요.':'기록을 저장하지 못했어요. 같은 요청을 다시 시도해주세요.'});}}
  finally{busy.current=false;onBusy?.(false);}
 }
 const locked=!!state.saving||!!pending.current;
 const blocked=(key,kind)=>!!state.saving||!!pending.current&&(pending.current.key!==key||pending.current.kind!==kind);
 if(!value&&!state.error||value?.items.length===0&&value.available.length===0&&!state.error)return null;
 return <div className="info-box segment-walking" aria-label="구간별 본인 보행 기록"><h3>역 내부·환승 보행 기록</h3>
  <p>같은 구간의 수동 기록 5회부터 최근 20회 중앙값으로 추정해요. 본인 기록 기반 추정이며 위치·동선 인증이 아니에요.</p>
  {state.error&&<div role="alert"><p>{state.error}</p><button className="secondary" disabled={!!state.saving} onClick={()=>{pending.current=null;setRetry(x=>x+1);}}>구간 기록 다시 확인</button></div>}
  {value?.available.map(a=>{const key=a.kind+a.leg_id,d=draft[key]||{};return <div key={key} className="card"><strong>{title[a.kind]}</strong><p>{a.name}</p>
   <p><label>구간 이름 <input aria-label={`${title[a.kind]} 구간 이름`} maxLength={60} value={d.label||''} disabled={locked} placeholder="예: 2번 입구 → 잠실 방면" onChange={e=>change(key,'label',e.target.value)}/></label></p>
   {!!a.variants.length&&<p><label>이전 구간 선택 <select aria-label={`${title[a.kind]} 이전 구간 선택`} value="" disabled={locked} onChange={e=>change(key,'label',e.target.value)}><option value="">구간 이름을 선택하세요</option>{a.variants.map(v=><option key={v.label} value={v.label}>{v.label} · {v.sample_count}회{v.estimate_seconds===null?'':` · 약 ${v.estimate_seconds}초`}</option>)}</select></label></p>}
   <p><label><input type="checkbox" checked={!!d.boundary} disabled={locked} onChange={e=>change(key,'boundary',e.target.checked)}/>{a.kind==='station_internal'?'지금 역 입구에서 시작해요. 같은 입구·승강장·방향을 구분했어요.':'지금 직전 하차 지점에서 다음 승차 지점까지 전체 구간을 시작해요.'}</label></p>
   <button className="secondary" disabled={blocked(key,'start')||!d.boundary||!d.label?.trim()} onClick={()=>save(key,'start',a)}>이 구간 보행 시작</button></div>;})}
  {value?.items.map(m=>{const key=m.measurement_id,d=draft[key]||{};return <div className="card" key={key}><strong>{title[m.kind]} · {m.label}</strong>
   {m.status==='recording'?<><p role="status">시작을 기록했어요. 실제 승차 지점에서 기존 ‘승차 지점에 도착했어요’ 버튼을 눌러주세요.</p>
    {m.predicted_seconds!==null&&<p>본인 기록 기반 약 {m.predicted_seconds}초 · 예상 도착 {new Date(m.predicted_arrival_at).toLocaleTimeString('ko-KR')}</p>}
    {m.can_finish&&<><p><label><input type="checkbox" checked={!!d.same} disabled={locked} onChange={e=>change(key,'same',e.target.checked)}/>같은 입구·경로·방향·승차 지점으로 이동했어요.</label></p>
     <p><label>이번 구간 상태 <select aria-label={`${m.label} 이동 상태`} value={d.condition||'normal'} disabled={locked} onChange={e=>change(key,'condition',e.target.value)}><option value="normal">평소 걸음·즉시 기록</option><option value="running">뛰어서 이동</option><option value="detour">다른 경로</option><option value="errand">중간 용무</option><option value="late_input">늦은 입력</option></select></label></p>
     <p><label><input type="checkbox" checked={!!d.apply} disabled={locked} onChange={e=>change(key,'apply',e.target.checked)}/>5회 이상 모이면 이 구간 추정을 안내에 사용해요.</label></p>
     <button className="primary" disabled={blocked(key,'confirm')} onClick={()=>save(key,'confirm',m)}>구간 기록 확인하고 반영</button></>}
   </>:<><p role="status">{m.status==='valid'?`유효 기록 · ${Math.round(m.observed_seconds)}초`:`학습 제외: ${m.reasons.map(r=>reasons[r]||'확인 필요').join(', ')}`}</p>
    <p>{m.estimate_seconds===null?`${m.sample_count} / 5회 · 추정 준비 중`:`본인 기록 기반 추정 약 ${m.estimate_seconds}초 · 최근 ${m.sample_count}회`}</p>
    {trip.status!=='active'&&<button className="secondary" disabled={blocked(key,'exclude')} onClick={()=>save(key,'exclude',m)}>{m.reasons.includes('MANUALLY_EXCLUDED')?'구간 학습 제외 해제':'이 구간 학습에서 제외'}</button>}</>}
  </div>;})}
  <p>역 내부 시간은 전체 접근·환승 시간과 중복 합산하지 않아요. 대기·탑승 시간으로 보행을 추측하지 않아요.</p></div>;
}
