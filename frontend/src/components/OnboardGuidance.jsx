import React,{useEffect,useRef,useState} from 'react';
import {confirmOnboard,getOnboard} from '../lib/onboard';

const messages={VEHICLE_CONFIRMATION_REQUIRED:'탑승한 차량번호를 확인하면 하차 정류소의 도착 예상을 조회할 수 있어요.',
 ONBOARD_MAPPING_REQUIRED:'이 이동의 공식 승하차 매핑이 없어요. 새 출발 안내에서 시작한 지원 버스 이동이 필요해요.',
 ONBOARD_MAPPING_UNCONFIRMED:'공식 승하차 지점과 진행 방향을 확인하지 못했어요.',
 VEHICLE_UNCONFIRMED:'같은 번호의 차량을 현재 구간에서 하나로 확인하지 못했어요. 번호와 차량을 다시 확인해주세요.',
 SAME_VEHICLE_ARRIVAL_MISSING:'현재 차량의 하차 정류소 예측이 아직 제공되지 않았어요.',ONBOARD_EVIDENCE_EXPIRED:'조회 정보가 만료됐어요. 차량 정보를 다시 확인해주세요.'};
export default function OnboardGuidance({trip}){
 const [suffix,setSuffix]=useState(''),[state,setState]=useState({phase:'idle'}),[clock,setClock]=useState(performance.now());
 const pending=useRef(null),alive=useRef(false),latest=useRef(null),generation=useRef(0);
 useEffect(()=>{
  alive.current=true;latest.current=null;setState({phase:'idle'});setSuffix('');
  return()=>{alive.current=false;generation.current++;pending.current?.abort();pending.current=null;};
 },[trip.trip_id,trip.version,trip.progress.anchor_event_id]);
 async function run(confirm=false){
  if(pending.current||document.visibilityState==='hidden')return;
  const request=new AbortController(),epoch=generation.current;pending.current=request;setState({phase:'loading'});
  try{
   const r=await (confirm?confirmOnboard(trip,suffix,request.signal):getOnboard(trip,request.signal));
   if(alive.current&&!request.signal.aborted&&epoch===generation.current){latest.current=r;setClock(performance.now());setState({phase:'ready',response:r});if(confirm)setSuffix('');}
  }catch(error){if(alive.current&&!request.signal.aborted&&epoch===generation.current){latest.current=null;setState({phase:'error',message:['RESOURCE_NOT_FOUND','VERSION_CONFLICT'].includes(error.code)?'이동이나 탑승 구간이 바뀌었어요. 이동 기록을 다시 확인해주세요.':'차량 정보를 확인하지 못했어요. 잠시 후 다시 확인해주세요.'});}}
  finally{if(pending.current===request)pending.current=null;}
 }
 useEffect(()=>{
  const tick=setInterval(()=>setClock(performance.now()),1000);
  const poll=setInterval(()=>{if(latest.current)run();},60000);
  const visibility=()=>{
   if(document.visibilityState==='hidden'){generation.current++;pending.current?.abort();pending.current=null;setState({phase:'hidden'});}
   else if(latest.current)run();else setState({phase:'idle'});
  };
  document.addEventListener('visibilitychange',visibility);
  return()=>{clearInterval(tick);clearInterval(poll);document.removeEventListener('visibilitychange',visibility);};
 },[trip.trip_id,trip.version,trip.progress.anchor_event_id]);
 const r=state.response,d=state.phase==='ready'?r?.data:null;
 const remaining=d?.status==='estimated'&&clock<r.deadline?Math.min(d.remaining_seconds,Math.floor((Date.parse(d.estimated_alighting_at)-r.serverMs-Math.max(0,clock-r.receivedMono))/1000)):null;
 const seconds=remaining>0?remaining:null;
 const reason=d?.status==='needs_data'?d.reasons.find(v=>messages[v]):null;
 return <section className="info-box" aria-label="탑승 차량 하차 예상">
  <strong>{trip.progress.vehicle_name} 탑승 중</strong><p>하차 지점: {trip.progress.alighting_stop}</p>
  {seconds!==null?<div role="status"><p>하차 정류소까지 약 {seconds<60?`${seconds}초`:`${Math.floor(seconds/60)}분${seconds%60?` ${seconds%60}초`:''}`}</p><p className="candidate-note">수신 기준 예상 · 차량번호는 직접 확인한 정보예요. 원천 갱신 지연과 실제 하차 시각은 확인되지 않았어요.</p></div>:
   <p role="status">{state.phase==='loading'?'차량과 하차 예측을 확인하고 있어요…':state.phase==='hidden'?'화면에 돌아오면 차량 정보를 다시 확인해요.':reason?messages[reason]:d?.status==='estimated'?'조회 정보가 만료됐어요. 최신 차량 정보를 다시 확인해주세요.':messages.VEHICLE_CONFIRMATION_REQUIRED}</p>}
  {state.phase==='error'&&<p role="alert">{state.message}</p>}
  <form className="routine-name-panel" onSubmit={e=>{e.preventDefault();run(true);}}>
   <label>탑승한 버스 차량번호 뒤 4자리<input inputMode="numeric" autoComplete="off" pattern="[0-9]{4}" maxLength={4} value={suffix} onChange={e=>setSuffix(e.target.value.replace(/[^0-9]/g,''))} disabled={state.phase==='loading'}/></label>
   <div className="button-row trip-progress-actions"><button className="secondary" disabled={state.phase==='loading'||suffix.length!==4}>차량 확인하고 하차 예상 보기</button>{latest.current&&<button type="button" className="secondary" disabled={state.phase==='loading'} onClick={()=>run()}>차량 정보 다시 확인</button>}</div>
  </form>
  <p className="candidate-note">실제로 내린 뒤 하차를 확인해주세요. 차량번호는 이 구간 확인에만 사용해요.</p>
 </section>;
}
