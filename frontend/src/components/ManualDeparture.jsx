import React,{useEffect,useRef,useState} from 'react';
import {activeTrip,confirmDeparture,confirmProgress,cancelTrip} from '../lib/trips';
import RemainingGuidance from './RemainingGuidance';

const failure=error=>['AUTH_REQUIRED','SESSION_EXPIRED'].includes(error?.code)?'로그인 후 이동 기록을 다시 확인해주세요.':error?.code==='ACTIVE_TRIP_EXISTS'?'다른 이동이 진행 중이에요. 기존 이동을 먼저 확인하거나 취소해주세요.':['VERSION_CONFLICT','RESOURCE_NOT_FOUND'].includes(error?.code)?'안내가 바뀌었거나 만료됐어요. 최신 출발을 다시 확인해주세요.':'출발 확인을 저장하지 못했어요. 다시 시도해주세요.';
export default function ManualDeparture({routineId,departure,available,onReported=null,onCancelled=null}){
 const [state,setState]=useState({phase:'loading',trip:null}),[retry,setRetry]=useState(0);
 const operation=useRef(null),controller=useRef(null),busy=useRef(false),alive=useRef(false),cancelledGuidance=useRef(null);
 useEffect(()=>{
  alive.current=true;const request=new AbortController();controller.current=request;busy.current=true;operation.current=null;
  setState({phase:'loading',trip:null});
  activeTrip(routineId,request.signal).then(trip=>{if(alive.current&&!request.signal.aborted){setState({phase:'ready',trip});if(trip?.departure_event)onReported?.();}}).catch(error=>{if(alive.current&&!request.signal.aborted)setState({phase:'error',trip:null,error:failure(error)});}).finally(()=>{if(controller.current===request)busy.current=false;});
  return()=>{alive.current=false;controller.current?.abort();busy.current=false;};
 },[routineId,retry,departure?.departure_state]);
 async function save(cancel=false,type='departed'){
  if(busy.current)return;busy.current=true;const request=new AbortController();controller.current=request;
  const previous=state.trip;setState(old=>({...old,phase:'saving',error:null}));
  try{
   if(cancel){await cancelTrip(previous,request.signal);cancelledGuidance.current=previous.guidance_id;operation.current=null;if(alive.current&&!request.signal.aborted){setState({phase:'ready',trip:null});onCancelled?.();}}
   else{
    operation.current ||= {type,trip:previous,guidanceId:departure?.guidance_id,routineId,eventId:crypto.randomUUID(),occurredAt:new Date().toISOString()};
    const trip=await (type==='departed'?confirmDeparture:confirmProgress)(operation.current,request.signal);
    if(alive.current&&!request.signal.aborted){operation.current=null;setState({phase:'ready',trip});if(type==='departed')onReported?.();}
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
   {state.trip?.boarding_event&&<p role="status">탑승 확인을 저장했어요. 차량 안 안내는 준비 중이에요.</p>}
   {!state.trip&&cancelledGuidance.current===departure?.guidance_id&&<p role="status">이동을 취소했어요. 최신 출발을 다시 확인하면 새 이동을 기록할 수 있어요.</p>}
   <div className="button-row trip-progress-actions">
    {!state.trip?.departure_event&&(state.trip||available&&departure?.guidance_id&&departure.guidance_id!==cancelledGuidance.current)&&<button className="primary" disabled={state.phase==='saving'} onClick={()=>save()}>{state.phase==='saving'?'출발 확인 저장 중…':'지금 출발했어요'}</button>}
    {state.trip?.departure_event&&!state.trip.boarding_event&&<>
     {!state.trip.approach_event&&<button className="secondary" disabled={state.phase==='saving'||!!operation.current&&operation.current.type!=='approach_arrived'} onClick={()=>save(false,'approach_arrived')}>정류장에 도착했어요</button>}
     <button className="primary" disabled={state.phase==='saving'||!!operation.current&&operation.current.type!=='boarded'} onClick={()=>save(false,'boarded')}>탑승했어요</button>
    </>}
    {state.trip&&<button className="secondary" disabled={state.phase==='saving'} onClick={()=>save(true)}>이 이동 취소</button>}
   </div>
   {state.trip?.departure_event&&!state.trip.approach_event&&!state.trip.boarding_event&&state.phase!=='saving'&&!state.error&&<RemainingGuidance key={state.trip.trip_id} trip={state.trip}/>}
  </>}
 </div>;
}
