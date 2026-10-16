import React,{useEffect,useRef,useState} from 'react';
import {learnWalking} from '../lib/personalization';
const reasons={MISSING_WALK_EVENTS:'출발·정류장 도착 기록 부족',UNVERIFIED_BASE:'검증된 기준 경로 없음',SCOPE_MISMATCH:'기준 구간과 다른 이동',INPUT_DELAY:'기록 입력 지연',PLACE_CHANGED:'장소 위치 변경',BEFORE_RESET:'초기화 이전 기록',RATIO_REVIEW_REQUIRED:'지원 계수 범위를 벗어나 확인 필요',INVALID_WALK_INTERVAL:'보행 시간 확인 필요',STALE_GUIDANCE:'출발 당시 안내 만료',RUNNING:'뛰어서 이동',DETOUR:'다른 경로 이용',ERRAND:'중간 용무',LATE_INPUT:'늦은 버튼 입력',EVENT_EXCLUDED:'제외된 이벤트'};
export default function WalkingObservation({trip}){
 const [same,setSame]=useState(false),[condition,setCondition]=useState('normal'),[state,setState]=useState({});
 const controller=useRef(null),pending=useRef(null),busy=useRef(false);
 useEffect(()=>()=>controller.current?.abort(),[]);
 async function save(){
  if(busy.current)return;busy.current=true;const c=new AbortController();controller.current=c;
  pending.current ||= {same_scope:same,condition};setState({saving:true});
  try{const result=await learnWalking(trip.trip_id,pending.current,c.signal);if(!c.signal.aborted)setState({result});}
  catch(e){if(!c.signal.aborted)setState({error:['AUTH_REQUIRED','SESSION_EXPIRED'].includes(e.code)?'로그인 후 다시 확인해주세요.':'기록을 반영하지 못했어요. 같은 내용으로 다시 시도해주세요.'});}
  finally{busy.current=false;}
 }
 return <div className="info-box" aria-label="이번 보행 학습"><h3>이번 보행 기록 학습</h3>
  {state.result?<p role="status">{state.result.status==='valid'?`유효 기록을 저장했어요. ${state.result.updated?'개인 계수를 갱신했어요.':`${state.result.sample_count} / 5개`}`:`학습 제외: ${state.result.exclusion_reasons.map(r=>reasons[r]||'확인 필요').join(', ')}`}</p>:<>
   <p>안내한 출발 지점에서 같은 경로로 정류장까지 걸었는지 확인해주세요. 다른 구간·뛰기·중간 용무·늦은 입력은 학습에서 제외해요. 본인 신고 기록이며 실제 이동 인증은 아니에요.</p>
   <label><input type="checkbox" checked={same} disabled={state.saving||!!pending.current} onChange={e=>setSame(e.target.checked)}/> 안내한 시작점·경로·방향·도착 지점이 같아요</label>
   <p><label>이번 이동 상태 <select value={condition} disabled={state.saving||!!pending.current} onChange={e=>setCondition(e.target.value)}><option value="normal">평소처럼 걸었고 버튼도 바로 눌렀어요</option><option value="running">뛰어서 이동했어요</option><option value="detour">다른 경로로 갔어요</option><option value="errand">중간에 다른 일을 했어요</option><option value="late_input">버튼을 늦게 눌렀어요</option></select></label></p>
   <button className="secondary" disabled={state.saving} onClick={save}>{state.saving?'기록 확인 중…':'보행 기록 확인하고 반영'}</button>
   {state.error&&<p role="alert">{state.error}</p>}
  </>}
 </div>;
}
