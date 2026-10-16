import React,{useEffect,useRef,useState} from 'react';
import {activeTrip,confirmDeparture,confirmProgress,cancelTrip} from '../lib/trips';
import RemainingGuidance from './RemainingGuidance';
import OnboardGuidance from './OnboardGuidance';
import WalkingObservation from './WalkingObservation';

const failure=error=>['AUTH_REQUIRED','SESSION_EXPIRED'].includes(error?.code)?'로그인 후 이동 기록을 다시 확인해주세요.':error?.code==='ACTIVE_TRIP_EXISTS'?'다른 이동이 진행 중이에요. 기존 이동을 먼저 확인하거나 취소해주세요.':['VERSION_CONFLICT','RESOURCE_NOT_FOUND'].includes(error?.code)?'안내가 바뀌었거나 만료됐어요. 최신 출발을 다시 확인해주세요.':'출발 확인을 저장하지 못했어요. 다시 시도해주세요.';
export default function ManualDeparture({routineId,departure,available,onReported=null,onCancelled=null}){
 const [state,setState]=useState({phase:'loading',trip:null}),[retry,setRetry]=useState(0);
 const operation=useRef(null),controller=useRef(null),busy=useRef(false),alive=useRef(false),cancelledGuidance=useRef(null);
 const progress=state.trip?.progress;
 useEffect(()=>{
  alive.current=true;const request=new AbortController();controller.current=request;busy.current=true;operation.current=null;
  setState({phase:'loading',trip:null});
  activeTrip(routineId,request.signal,true).then(trip=>{if(alive.current&&!request.signal.aborted){if(trip?.guidance_id===cancelledGuidance.current&&trip.status!=='active')trip=null;setState({phase:'ready',trip});if(trip?.status==='active'&&trip.departure_event)onReported?.();}}).catch(error=>{if(alive.current&&!request.signal.aborted)setState({phase:'error',trip:null,error:failure(error)});}).finally(()=>{if(controller.current===request)busy.current=false;});
  let recovery=null;
  const recover=async()=>{
   if(!alive.current||busy.current||operation.current||document.visibilityState==='hidden')return;
   busy.current=true;recovery=new AbortController();const signal=recovery.signal;
   try{let trip=await activeTrip(routineId,signal,true);if(alive.current&&!signal.aborted){if(trip?.guidance_id===cancelledGuidance.current&&trip.status!=='active')trip=null;setState({phase:'ready',trip});if(trip?.status==='active'&&trip.departure_event)onReported?.();}}
   catch(error){if(alive.current&&!signal.aborted)setState({phase:'error',trip:null,error:failure(error)});}
   finally{busy.current=false;}
  };
  const visible=()=>{if(document.visibilityState==='hidden')recovery?.abort();else recover();};
  const timer=setInterval(recover,60000);document.addEventListener('visibilitychange',visible);
  return()=>{alive.current=false;clearInterval(timer);document.removeEventListener('visibilitychange',visible);recovery?.abort();controller.current?.abort();busy.current=false;};
 },[routineId,retry,departure?.departure_state]);
 async function save(cancel=false,type='departed'){
  if(busy.current)return;busy.current=true;const request=new AbortController();controller.current=request;
  const previous=state.trip;setState(old=>({...old,phase:'saving',error:null}));
  try{
   if(cancel){await cancelTrip(previous,request.signal);cancelledGuidance.current=previous.guidance_id;operation.current=null;if(alive.current&&!request.signal.aborted){setState({phase:'ready',trip:null});onCancelled?.();}}
   else{
    operation.current ||= {type,trip:previous,guidanceId:departure?.guidance_id,routineId,eventId:crypto.randomUUID(),occurredAt:new Date().toISOString()};
    const trip=await (type==='departed'?confirmDeparture:confirmProgress)(operation.current,request.signal);
    if(alive.current&&!request.signal.aborted){operation.current=null;if(trip.status==='cancelled'){cancelledGuidance.current=trip.guidance_id;setState({phase:'ready',trip:null});onCancelled?.();}else{setState({phase:'ready',trip});if(type==='departed')onReported?.();}}
   }
  }catch(error){if(alive.current&&!request.signal.aborted){if(['RESOURCE_NOT_FOUND','VERSION_CONFLICT'].includes(error.code)&&!operation.current?.trip)operation.current=null;setState(old=>({...old,phase:'ready',error:type==='departed'||cancel?failure(error):'이동 기록을 확인하지 못했어요. 같은 기록을 다시 시도해주세요.',trip:operation.current?.trip||previous}));}}
  finally{if(controller.current===request)busy.current=false;}
 }
 return <div aria-label="수동 출발 확인">
  <h3>출발 확인</h3>
  {state.phase==='loading'&&<p role="status">진행 중인 이동을 확인하고 있어요.</p>}
  {state.phase==='error'&&<><p role="alert">{state.error}</p><button className="secondary" onClick={()=>setRetry(n=>n+1)}>이동 기록 다시 확인</button></>}
  {state.phase!=='loading'&&state.phase!=='error'&&<>
   {state.error&&<p role="alert">{state.error}</p>}
   {state.trip?.departure_event?<p role="status">출발 확인을 저장했어요.</p>:state.trip?<p>진행 중인 이동에 출발 확인을 남길 수 있어요.</p>:null}
   {state.trip?.approach_event&&<p role="status">정류장 도착 확인을 저장했어요.</p>}
   {state.trip?.approach_event&&<WalkingObservation key={state.trip.trip_id} trip={state.trip}/>}
   {state.trip?.boarding_event&&!progress&&<p role="status">탑승 확인을 저장했어요. 차량 안 안내는 준비 중이에요.</p>}
   {progress?.stage==='onboard'&&state.phase==='ready'&&!state.error&&<OnboardGuidance key={`${state.trip.trip_id}:${progress.anchor_event_id}`} trip={state.trip}/>}
   {['transfer','transfer_waiting'].includes(progress?.stage)&&<div className="info-box" role="status"><strong>다음 차량: {progress.vehicle_name}</strong><p>승차 지점: {progress.boarding_stop}</p><p>하차 후 현재 위치를 확인하면 다음 차량까지 남은 경로를 조회할 수 있어요.</p></div>}
   {progress?.stage==='transit_finished'&&<p role="status">마지막 차량 하차를 저장했어요. 목적지까지 이동한 뒤 도착을 직접 확인해주세요.</p>}
   {state.trip?.status==='completed'&&<p className="info-box" role="status">목적지 도착 확인을 저장하고 이동을 완료했어요. 사용자가 직접 남긴 기록이에요.</p>}
   {state.trip?.status==='missed'&&<p className="info-box" role="status">놓침 기록을 저장하고 이번 이동을 종료했어요. 다음 차량은 최신 출발 안내에서 새 이동으로 시작해주세요.</p>}
   {!state.trip&&cancelledGuidance.current===departure?.guidance_id&&<p role="status">이동을 취소했어요. 최신 출발을 다시 확인하면 새 이동을 기록할 수 있어요.</p>}
   <div className="button-row trip-progress-actions">
    {!state.trip?.departure_event&&(state.trip||available&&departure?.guidance_id&&departure.guidance_id!==cancelledGuidance.current)&&<button className="primary" disabled={state.phase==='saving'} onClick={()=>save()}>{state.phase==='saving'?'출발 확인 저장 중…':'지금 출발했어요'}</button>}
    {state.trip?.status==='active'&&state.trip.departure_event&&progress&&Object.keys(progress.actions).filter(type=>type!=='departed').map(type=><button key={type} className={['boarded','arrived'].includes(type)?'primary':'secondary'} disabled={state.phase==='saving'||!!operation.current&&operation.current.type!==type} onClick={()=>save(false,type)}>{{approach_arrived:'승차 지점에 도착했어요',boarded:'이 차량에 탑승했어요',alighted:'이 차량에서 내렸어요',missed:'놓침을 기록하고 이동 종료',arrived:'목적지에 도착했어요'}[type]}</button>)}
    {state.trip?.departure_event&&!progress&&!state.trip.boarding_event&&<>
     {!state.trip.approach_event&&<button className="secondary" disabled={state.phase==='saving'||!!operation.current&&operation.current.type!=='approach_arrived'} onClick={()=>save(false,'approach_arrived')}>정류장에 도착했어요</button>}
     <button className="primary" disabled={state.phase==='saving'||!!operation.current&&operation.current.type!=='boarded'} onClick={()=>save(false,'boarded')}>탑승했어요</button>
    </>}
    {state.trip?.status==='active'&&<button className="secondary" disabled={state.phase==='saving'} onClick={()=>save(true)}>이 이동 취소</button>}
    {['completed','missed'].includes(state.trip?.status)&&<button className="secondary" onClick={()=>{cancelledGuidance.current=state.trip.guidance_id;operation.current=null;setState({phase:'ready',trip:null});onCancelled?.();}}>새 이동 준비</button>}
   </div>
   {state.trip?.status==='active'&&state.trip.departure_event&&state.phase!=='saving'&&!state.error&&(
    progress?['approaching','transfer','transfer_waiting'].includes(progress.stage):!state.trip.approach_event&&!state.trip.boarding_event
   )&&<RemainingGuidance key={`${state.trip.trip_id}:${progress?.anchor_event_id||'first'}`} trip={state.trip}/>}
  </>}
 </div>;
}
