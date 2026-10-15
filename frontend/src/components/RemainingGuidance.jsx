import React,{useEffect,useRef,useState} from 'react';
import OriginSelector from './OriginSelector';
import {getRemaining,refreshRemaining} from '../lib/remaining';
import {formatJourneyTime} from '../lib/journeys';

const preciseTime=seconds=>seconds<60?`${seconds}초`:`${Math.floor(seconds/60)}분${seconds%60?` ${seconds%60}초`:''}`;
const messages={no_routes:'현재 위치에서 남은 경로가 제공되지 않았어요.',route_changed:'남은 경로가 저장한 노선과 달라요. 현재 위치와 경로를 다시 확인해주세요.',
 ambiguous_route:'같은 노선의 후보가 여러 개여서 남은 경로를 확정할 수 없어요.',insufficient_data:'남은 도보 또는 도착 근거가 부족해 여유를 계산할 수 없어요.',
 not_enough_time:'제공된 차량까지 남은 접근 시간이 부족해요.',stale:'남은 경로 정보가 만료됐어요.',unsupported:'이 구간의 이동 중 안내는 아직 지원하지 않아요.'};
export default function RemainingGuidance({trip}){
 const transfer=['transfer','transfer_waiting'].includes(trip.progress?.stage);
 const title=transfer?'환승 중 남은 경로':'첫 탑승 전 남은 경로';
 const [open,setOpen]=useState(false),[position,setPosition]=useState(null),[confirmed,setConfirmed]=useState(false);
 const [state,setState]=useState({phase:'idle',response:null}),[clock,setClock]=useState(performance.now());
 const controller=useRef(null),alive=useRef(false),busy=useRef(false),generation=useRef(0);
 function clear(){generation.current++;controller.current?.abort();busy.current=false;setState({phase:'idle',response:null});setPosition(null);setConfirmed(false);}
 useEffect(()=>{alive.current=true;return()=>{alive.current=false;generation.current++;controller.current?.abort();};},[trip.trip_id,trip.version]);
 useEffect(()=>{
  const hide=()=>{if(document.visibilityState==='hidden'&&busy.current){generation.current++;controller.current?.abort();busy.current=false;setState({phase:'expired',response:null});}};
  document.addEventListener('visibilitychange',hide);return()=>document.removeEventListener('visibilitychange',hide);
 },[]);
 async function run(refresh=false){
  if(busy.current||document.visibilityState==='hidden')return;
  const previous=state.response,epoch=generation.current,request=new AbortController();controller.current=request;busy.current=true;
  setState({phase:'loading',response:previous});
  try{
   const response=refresh?await refreshRemaining(trip,position,request.signal):await getRemaining(trip,previous.data.search_id,request.signal);
   if(!refresh)response.deadline=Math.min(response.deadline,previous.deadline);
   if(alive.current&&!request.signal.aborted&&epoch===generation.current)setState({phase:'ready',response});
  }catch(error){if(alive.current&&!request.signal.aborted&&epoch===generation.current)setState({phase:'error',response:null,message:
   ['RESOURCE_NOT_FOUND','SEARCH_EXPIRED','VERSION_CONFLICT'].includes(error.code)?'위치 확인 또는 이동 정보가 바뀌었어요. 현재 위치를 다시 확인해주세요.':
   ['AUTH_REQUIRED','SESSION_EXPIRED'].includes(error.code)?'로그인 후 남은 경로를 다시 확인해주세요.':'남은 경로를 확인하지 못했어요. 현재 위치를 다시 확인해주세요.'});}
  finally{if(controller.current===request)busy.current=false;}
 }
 useEffect(()=>{
  if(!state.response)return;
  const tick=setInterval(()=>{const now=performance.now();setClock(now);if(now>=state.response.deadline){controller.current?.abort();busy.current=false;setState({phase:'expired',response:null});}},1000);
  const poll=setInterval(()=>run(false),60000);
  const visibility=()=>{if(document.visibilityState==='hidden'){controller.current?.abort();busy.current=false;}else run(false);};
  document.addEventListener('visibilitychange',visibility);
  return()=>{clearInterval(tick);clearInterval(poll);document.removeEventListener('visibilitychange',visibility);};
 },[state.response]);
 const r=state.response,d=state.phase==='ready'?r?.data:null;
 const now=r?r.serverMs+Math.max(0,clock-r.receivedMono):0;
 const slack=d?.valid_for_guidance?Math.min(d.slack_seconds,Math.floor((Date.parse(d.vehicle_arrival_at)-now)/1000-d.remaining_approach_seconds)):null;
 const valid=d?.valid_for_guidance&&clock<r.deadline&&slack>=0;
 return <div aria-label={`${title} 안내`}>
  {!open?<button className="secondary" onClick={()=>setOpen(true)}>{title} 확인</button>:<>
   <h3>{title}</h3>
   <p className="small muted">{transfer?'확인한 현재 위치에서 다음 승차 지점까지의 추정이에요. 이미 지난 차량과 도보는 다시 포함하지 않아요.':'확인한 현재 위치에서 첫 승차 지점까지의 추정이에요.'} 차량 안에서는 사용하지 마세요. 이동하거나 탑승하면 안내를 멈추고 위치를 다시 확인해주세요.</p>
   {!position&&<OriginSelector currentPointOnly onSelect={value=>{clear();setPosition(value);}} onAuthError={clear}/>}
   {position&&state.phase==='idle'&&<>
    <p>현재 위치를 선택했어요.</p>
    <label className="small"><input type="checkbox" checked={confirmed} onChange={e=>setConfirmed(e.target.checked)}/>{transfer?' 이전 차량에서 내렸고 다음 차량에 타기 전이며, 확인한 위치에 있어요.':' 아직 첫 차량에 타기 전이고, 확인한 위치에 있어요.'}</label>
    <div className="button-row"><button className="primary" disabled={!confirmed} onClick={()=>run(true)}>남은 경로 조회</button><button className="secondary" onClick={clear}>위치 다시 확인</button></div>
   </>}
   {state.phase==='loading'&&<p role="status">현재 위치에서 남은 경로를 확인하고 있어요.</p>}
   {state.phase==='error'&&<p className="info-box" role="alert">{state.message}</p>}
   {state.phase==='expired'&&<p className="info-box" role="status">위치 확인 기한이 끝났어요. 현재 위치를 다시 확인해주세요.</p>}
   {d&&<RemainingInfo data={d} valid={valid} slack={slack}/>}
   <div className="button-row">{state.phase!=='idle'&&<button className="secondary" onClick={clear}>현재 위치 다시 확인</button>}
    <button className="secondary" onClick={()=>{clear();setOpen(false);}}>탑승했거나 안내 멈추기</button></div>
  </>}
 </div>;
}

export function RemainingInfo({data:d,valid,slack}){
 return <div className="info-box" role="status">
    {valid?<>
     <strong>승차 지점까지 남은 도보 약 {formatJourneyTime(d.remaining_approach_seconds)}</strong>
     <p>확인한 위치 기준 정류장 도착 후 예상 여유 {preciseTime(slack)}</p>
     <p>{slack<d.buffer_seconds?'설정한 탑승 여유보다 부족해요.':'설정한 탑승 여유를 확보하는 추정이에요.'} 설정 여유 {preciseTime(d.buffer_seconds)}</p>
     <p>{d.timing_basis==='receipt_estimate'?'수신 기준 도착 추정이에요.':'공급자 시각 기준 도착 추정이에요.'} 실제 탑승을 보장하지 않아요.</p>
     <p>{d.connection_status==='estimated_feasible'?'이후 환승 연결은 가능 추정이에요.':d.connection_status==='unavailable'?'이후 환승 연결이 어려운 추정이에요.':'이후 환승 연결은 확인이 필요해요.'}</p>
     {['estimated_meets','estimated_late'].includes(d.target_evaluation?.status)&&<p>{d.target_evaluation.status==='estimated_meets'?'오늘 목표 도착 충족 추정':'오늘 목표 도착보다 늦는 추정'} · 예상 도착 {new Date(d.target_evaluation.estimated_destination_arrival_at).toLocaleTimeString('ko-KR',{timeZone:'Asia/Seoul',hour:'2-digit',minute:'2-digit'})}</p>}
    </>:<p>{messages[d.status]||'현재 시점의 여유를 안내할 수 없어요. 위치를 다시 확인해주세요.'}</p>}
   </div>;
}
