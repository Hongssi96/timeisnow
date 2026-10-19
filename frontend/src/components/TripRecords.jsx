import React,{useEffect,useRef,useState} from 'react';
import {records,record,observation,mutateRecord} from '../lib/tripRecords';
import TripExport from './TripExport';
import SegmentWalking from './SegmentWalking';
const names={departed:'출발',approach_arrived:'승차 지점 도착',boarded:'탑승',alighted:'하차',missed:'놓침',arrived:'목적지 도착'};
const states={active:'진행 중',completed:'도착 완료',cancelled:'취소',missed:'놓침 종료'};
const reasons={timestamp_error:'시각 입력 오류',accidental_input:'잘못 누른 기록',learning_exclusion:'학습에서 제외',learning_restore:'학습 제외 해제'};
const showTime=s=>new Date(s).toLocaleString('ko-KR',{timeZone:'Asia/Seoul'});
const localTime=s=>{const d=new Date(s);return new Date(d.getTime()-d.getTimezoneOffset()*60000).toISOString().slice(0,-1);};
const message=e=>['AUTH_REQUIRED','SESSION_EXPIRED'].includes(e?.code)?'로그인 후 내 이동 기록을 확인해주세요.':e?.code==='VERSION_CONFLICT'?'기록이 변경됐어요. 최신 기록을 다시 확인해주세요.':e?.code==='ACTIVE_TRIP_EDIT_FORBIDDEN'?'진행 중인 이동을 종료하거나 취소한 뒤 정정해주세요.':e?.code==='VALIDATION_ERROR'?'정정 시각과 앞뒤 기록 순서를 확인해주세요.':'기록을 확인하지 못했어요. 같은 요청을 다시 시도하거나 최신 기록을 확인해주세요.';
export default function TripRecords({onLogin}){
 const [list,setList]=useState({items:[],loading:true}),[selected,setSelected]=useState(null),[edit,setEdit]=useState(null),[condition,setCondition]=useState(null),[remove,setRemove]=useState(false),[state,setState]=useState({}),[retry,setRetry]=useState(0);
 const controller=useRef(null),pending=useRef(null),busy=useRef(false);
 useEffect(()=>{const c=new AbortController();controller.current=c;busy.current=true;
  setList({items:[],loading:true});setSelected(null);setState({});
  records(null,c.signal).then(v=>{if(!c.signal.aborted)setList(v);}).catch(e=>{if(!c.signal.aborted)setState({error:message(e),auth:['AUTH_REQUIRED','SESSION_EXPIRED'].includes(e.code)});}).finally(()=>{if(controller.current===c){busy.current=false;setList(v=>({...v,loading:false}));}});
  return()=>{c.abort();controller.current?.abort();};},[retry]);
 async function open(tripId){
  if(busy.current)return;busy.current=true;const c=new AbortController();controller.current=c;setState({loading:true});setEdit(null);setCondition(null);setRemove(false);pending.current=null;
  try{const [detail,walk]=await Promise.all([record(tripId,c.signal),observation(tripId,c.signal)]);if(!c.signal.aborted){setSelected({...detail,walk});setState({});}}
  catch(e){if(!c.signal.aborted)setState({error:message(e)});}finally{busy.current=false;}
 }
 async function more(){
  if(busy.current)return;busy.current=true;const c=new AbortController();controller.current=c;setState({loading:true});
  try{const next=await records(list.next_cursor,c.signal);if(!c.signal.aborted){setList(v=>({...next,items:[...v.items,...next.items.filter(n=>!v.items.some(o=>o.trip_id===n.trip_id))]}));setState({});}}
  catch(e){if(!c.signal.aborted)setState({error:message(e)});}finally{busy.current=false;}
 }
 async function save(kind){
  if(busy.current)return;
  if(!pending.current){
   let body={client_request_id:crypto.randomUUID()};
   if(kind==='event'){
    const at=new Date(edit.time);if(!Number.isFinite(at.getTime())){setState({error:'정정할 시각을 확인해주세요.'});return;}
    body={...body,expected_version:edit.event.version,occurred_at:at.toISOString(),excluded:edit.excluded,correction_reason:edit.reason};
   }else if(kind==='conditions')body={...body,expected_version:selected.walk.version,...condition};
   else body={...body,expected_version:selected.trip.version};
   pending.current={kind,tripId:selected.trip.trip_id,eventId:edit?.event.event_id,body};
  }
  busy.current=true;const c=new AbortController();controller.current=c;setState({saving:true});
  try{
   const result=await mutateRecord(pending.current,c.signal);if(c.signal.aborted)return;
   const v=await records(null,c.signal);if(c.signal.aborted)return;setList(v);
   if(kind==='delete')setSelected(null);
   else {const [detail,walk]=await Promise.all([record(selected.trip.trip_id,c.signal),observation(selected.trip.trip_id,c.signal)]);if(c.signal.aborted)return;setSelected({...detail,walk});}
   pending.current=null;setEdit(null);setCondition(null);setRemove(false);
   setState({notice:`${kind==='delete'?'이동 기록을 삭제했어요.':'정정을 저장했어요.'} 현재 시간 계수 ${result.personalization.factors[0].value.toFixed(3)}배 · 유효 기록 ${result.personalization.sample_counts.valid}개`});
  }catch(e){if(!c.signal.aborted){if(['VALIDATION_ERROR','VERSION_CONFLICT','RESOURCE_NOT_FOUND','ACTIVE_TRIP_EDIT_FORBIDDEN','CSRF_INVALID'].includes(e.code))pending.current=null;setState({error:message(e)});}}finally{busy.current=false;}
 }
 const locked=!!state.loading||!!state.saving||!!pending.current;
 return <section aria-label="내 이동 기록">
  <TripExport onLogin={onLogin}/>
  {(list.loading||state.loading)&&<p role="status">이동 기록을 확인하고 있어요.</p>}
  {state.error&&<div className="info-box" role="alert"><p>{state.error}</p>{state.auth&&<button className="secondary" onClick={onLogin}>로그인하고 기록 확인</button>}<button className="secondary" onClick={()=>{pending.current=null;setRetry(n=>n+1);}}>최신 기록 다시 확인</button></div>}
  {state.notice&&<p className="info-box" role="status">{state.notice}</p>}
  {!list.loading&&!state.error&&!state.auth&&!list.items.length&&<p className="info-box">저장된 이동 기록이 없어요. 루틴에서 출발과 정류장 도착을 기록해주세요.</p>}
  {list.items.map(t=><button key={t.trip_id} className="card place-row" disabled={locked} onClick={()=>open(t.trip_id)}><span>{showTime(t.created_at)}<small>{states[t.status]} · 본인 수동 기록</small></span></button>)}
  {list.next_cursor&&<button className="secondary" disabled={locked} onClick={more}>이동 기록 더 보기</button>}
  {selected&&<section className="card" aria-label="선택한 이동 기록"><h2>{showTime(selected.trip.created_at)}</h2><p>{states[selected.trip.status]} · 버전 {selected.trip.version}</p>
   <SegmentWalking trip={selected.trip}/>
   {selected.trip.status==='active'&&<p className="info-box">진행 중에는 정정할 수 없어요. 출발 화면에서 이동을 종료하거나 취소해주세요.</p>}
   {selected.events.map(e=><div key={e.event_id} className="place-row trip-progress-actions"><span><strong>{names[e.type]}</strong><small>{showTime(e.occurred_at)} · 버전 {e.version}{e.excluded?' · 학습 제외':''}</small></span><button className="secondary" disabled={locked||selected.trip.status==='active'} onClick={()=>{setEdit({event:e,time:localTime(e.occurred_at),excluded:e.excluded,reason:'timestamp_error'});setCondition(null);setRemove(false);}}>{names[e.type]} 기록 정정</button></div>)}
   {selected.walk&&<div className="info-box"><p>보행 학습: {selected.walk.status==='valid'?'유효':'제외'} · 버전 {selected.walk.version}</p><button className="secondary" disabled={locked||selected.trip.status==='active'} onClick={()=>{setCondition(selected.walk.confirmation||{same_scope:false,condition:'normal'});setEdit(null);setRemove(false);}}>보행 조건 정정</button></div>}
   {edit&&<form onSubmit={e=>{e.preventDefault();save('event');}}><h3>{names[edit.event.type]} 기록 정정</h3><label>정정할 시각 <input type="datetime-local" step="0.001" value={edit.time} disabled={locked} onChange={e=>setEdit(v=>({...v,time:e.target.value}))}/></label><p><label><input type="checkbox" checked={edit.excluded} disabled={locked} onChange={e=>setEdit(v=>({...v,excluded:e.target.checked}))}/> 이 기록을 보행 학습에서 제외</label></p><label>정정 사유 <select value={edit.reason} disabled={locked} onChange={e=>setEdit(v=>({...v,reason:e.target.value}))}>{Object.entries(reasons).map(([k,v])=><option key={k} value={k}>{v}</option>)}</select></label><p className="small">앞뒤 기록 순서와 최초 버튼 수신시각을 넘길 수 없어요. 입력 지연이 크면 학습에서 제외해요.</p><button className="primary" disabled={state.saving||state.loading}>기록 정정하고 재학습</button></form>}
   {condition&&<div className="info-box"><label><input type="checkbox" checked={condition.same_scope} disabled={locked} onChange={e=>setCondition(v=>({...v,same_scope:e.target.checked}))}/> 안내한 시작점·경로·방향·도착 지점이 같아요</label><p><label>정정할 이동 상태 <select value={condition.condition} disabled={locked} onChange={e=>setCondition(v=>({...v,condition:e.target.value}))}><option value="normal">평소 걸음·즉시 기록</option><option value="running">뛰어서 이동</option><option value="detour">다른 경로</option><option value="errand">중간 용무</option><option value="late_input">늦은 입력</option></select></label></p><button className="primary" disabled={state.saving||state.loading} onClick={()=>save('conditions')}>보행 조건 정정하고 재학습</button></div>}
   {!!selected.corrections.length&&<div className="info-box"><h3>최근 정정 이력</h3>{selected.corrections.slice(0,5).map(h=><p key={h.correction_id}>{reasons[h.reason]||'기록 정정'} · {showTime(h.corrected_at)}</p>)}</div>}
   {!remove?<button className="secondary" disabled={locked} onClick={()=>{setRemove(true);setEdit(null);setCondition(null);}}>이 이동 기록 삭제</button>:<div className="info-box"><p>이 이동·이벤트·보행 관측과 정정 이력을 삭제하고 남은 기록으로 다시 학습해요. 삭제한 원본은 복원할 수 없어요.</p><div className="button-row"><button className="primary" disabled={state.saving||state.loading} onClick={()=>save('delete')}>삭제하고 재학습</button><button className="secondary" disabled={locked} onClick={()=>setRemove(false)}>삭제 취소</button></div></div>}
  </section>}
 </section>;
}
