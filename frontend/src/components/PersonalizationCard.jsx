import React,{useEffect,useRef,useState} from 'react';
import {personalization,changePersonalization} from '../lib/personalization';
const message=e=>['AUTH_REQUIRED','SESSION_EXPIRED'].includes(e?.code)?'로그인하면 내 걸음 학습 상태를 볼 수 있어요.':e?.code==='VERSION_CONFLICT'?'개인 설정이 변경됐어요. 다시 확인해주세요.':'학습 상태를 확인하지 못했어요. 다시 시도해주세요.';
export default function PersonalizationCard(){
 const [state,setState]=useState({loading:true}),[retry,setRetry]=useState(0),[confirmation,setConfirmation]=useState(null);
 const pending=useRef(null),busy=useRef(false),controller=useRef(null);
 useEffect(()=>{const c=new AbortController();controller.current=c;busy.current=true;setState({loading:true});
  personalization(c.signal).then(value=>{if(!c.signal.aborted)setState({value});}).catch(e=>{if(!c.signal.aborted)setState({error:message(e)});}).finally(()=>{if(controller.current===c)busy.current=false;});
  return()=>{c.abort();controller.current?.abort();};},[retry]);
 async function change(kind){
  if(busy.current)return;busy.current=true;const c=new AbortController();controller.current=c;
  pending.current ||= {kind,body:{expected_version:state.value.profile_version,client_request_id:crypto.randomUUID()}};
  setState(s=>({...s,saving:true,error:null}));
  try{const value=await changePersonalization(kind,pending.current.body,c.signal);if(!c.signal.aborted){pending.current=null;setConfirmation(null);setState({value,notice:kind==='reset'?'계수를 초기화했어요. 지금 이후 출발한 기록부터 새로 학습해요.':'이전 계수를 새 버전으로 복구했어요.'});}}
  catch(e){if(!c.signal.aborted){if(['VERSION_CONFLICT','RESTORE_UNAVAILABLE'].includes(e.code))pending.current=null;setState(s=>({...s,saving:false,error:message(e)}));}}
  finally{if(controller.current===c)busy.current=false;}
 }
 const v=state.value;
 return <section className="card" aria-label="내 걸음 학습"><h2>내 걸음 학습</h2>
  {state.loading&&<p role="status">학습 상태를 확인하고 있어요.</p>}
  {state.error&&<><p role="alert">{state.error}</p>{!state.saving&&<button className="secondary" onClick={()=>{pending.current=null;setConfirmation(null);setRetry(n=>n+1);}}>학습 상태 다시 확인</button>}</>}
  {v&&<><p>유효 보행 기록 <strong>{v.sample_counts.valid} / 5개</strong></p><p>{v.status==='active'?'기록을 반영한 접근 시간을 사용 중이에요.':'유효 기록 5개부터 내 걸음을 반영해요.'}</p>
   <p>현재 시간 계수 <strong>{v.factors[0].value.toFixed(3)}배</strong> · 버전 {v.profile_version}</p>
   <p className="muted small">검증된 첫 버스 접근 경로와 직접 확인한 출발·정류장 도착 기록을 사용해요. 대기 시간은 제외하며 탑승 여유는 자동으로 줄이지 않아요.</p>
   <p className="small">학습 제외 {v.sample_counts.excluded}개</p>
   {v.quality.sample_count>0&&<p className="small">학습 전 예측 오차: 기본 {Math.round(v.quality.baseline_mae_seconds)}초 · 개인화 {Math.round(v.quality.personalized_mae_seconds)}초 (최근 {v.quality.sample_count}개)</p>}
   {!confirmation?<div className="button-row"><button className="secondary" disabled={state.saving} onClick={()=>setConfirmation('reset')}>학습 초기화</button>{v.can_restore&&<button className="secondary" disabled={state.saving} onClick={()=>setConfirmation('restore')}>이전 계수 복구</button>}</div>:<div className="info-box"><p>{confirmation==='reset'?'계수를 1배로 돌리고 이전 기록의 재학습을 막을까요? 이동 기록은 보존해요.':'직전 변경 이전의 계수를 복구할까요? 과거 안내는 보존해요.'}</p><div className="button-row"><button className="primary" disabled={state.saving} onClick={()=>change(confirmation)}>{state.saving?'저장 중…':'확인하고 적용'}</button><button className="secondary" disabled={state.saving||!!pending.current} onClick={()=>setConfirmation(null)}>취소</button></div></div>}
  </>}
  {state.notice&&<p role="status">{state.notice}</p>}
 </section>;
}
