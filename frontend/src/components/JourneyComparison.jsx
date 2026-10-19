import WalkingGuidance from './WalkingGuidance';
import {getProfile} from '../lib/profile';
import React, { useEffect, useRef, useState } from 'react';
import { ArrowLeft, MapPin, ArrowRight } from 'lucide-react';
import { apiRequest, ApiError } from '../lib/api';
import { pollJourney, safeJourneyId, journeyError } from '../lib/journeys';
import OriginSelector from './OriginSelector';
import JourneyCandidates from './JourneyCandidates';
import JourneyUnavailable from './JourneyUnavailable';
import { needsRoutineRecovery, routineRecoveryMessage } from '../lib/routines';

function placeRef(origin) {
  if (!origin || origin.origin?.type !== 'saved_place') return null;
  return { place_id: origin.origin.place_id, location_version: origin.origin.location_version };
}

function selection(value) {
  const origin=value?.origin;
  if (!Number.isFinite(value?.deadline) || typeof value?.label !== 'string') return false;
  if (origin?.type==='saved_place') return safeJourneyId(origin.place_id) && Number.isInteger(origin.location_version) && origin.location_version>=1;
  return ['map_pin','current_location'].includes(origin?.type) && Number.isFinite(origin.latitude) && Math.abs(origin.latitude)<=90
    && Number.isFinite(origin.longitude) && Math.abs(origin.longitude)<=180
    && (origin.type==='map_pin' || origin.location_confirmed===true);
}

// ISO weekdays 1(Mon)..7(Sun) and an optional HH:MM target arrival.
const ISO_WEEKDAYS=new Set([1,2,3,4,5,6,7]);
const SAVED_PLACE_REQUIRED='루틴을 저장하려면 출발지와 도착지를 내 저장 장소에서 선택해주세요.';
function validSchedule(weekdays,target) {
  return Array.isArray(weekdays)&&weekdays.length>=1&&weekdays.length<=7&&new Set(weekdays).size===weekdays.length
    &&weekdays.every(day=>ISO_WEEKDAYS.has(day))
    &&(target===null||/^([01]\d|2[0-3]):[0-5]\d$/.test(target));
}

export default function JourneyComparison({ initialOrigin, onBack, onLogin, onAuthError, onRoutineSaved, onRoutineReload, routineToReplace }) {
  const [origin,setOrigin]=useState(()=>!routineToReplace&&selection(initialOrigin)&&initialOrigin.deadline>Date.now()?initialOrigin:null);
  const [destination,setDestination]=useState(null);
  const [editing,setEditing]=useState(null);
  const [editingMode,setEditingMode]=useState('current');
  const [editingBusy,setEditingBusy]=useState(false);
  const [saveMessage,setSaveMessage]=useState(null);
  const [reloadNeeded,setReloadNeeded]=useState(false);
  const [preference,setPreference]=useState('balanced');
  const preferenceEdited=useRef(false);
  useEffect(()=>{
    const controller=new AbortController();
    getProfile(controller.signal).then(value=>{if(!controller.signal.aborted&&!preferenceEdited.current)setPreference(value.profile.route_preference);}).catch(()=>{});
    return()=>controller.abort();
  },[]);
  const [state,setState]=useState({phase:'idle'});
  const [saves,setSaves]=useState({});
  const pending=useRef(null),snapshot=useRef(null),saver=useRef(null),saveAttempts=useRef({});
  const busy=['loading','waiting'].includes(state.phase);
  const canSave=!!placeRef(origin)&&!!placeRef(destination)&&origin.origin.place_id!==destination.origin.place_id;
  function stop(){pending.current?.abort();pending.current=null;}
  function stopSaving(){saver.current?.abort();saver.current=null;}
  function reset(){stop();snapshot.current=null;setState({phase:'idle'});}
  function resetSaves(){stopSaving();saveAttempts.current={};setSaves({});setSaveMessage(null);}
  function expire(){
    stop();snapshot.current=null;setEditing(null);
    setOrigin(value=>value?.deadline>Date.now()?value:null);setDestination(value=>value?.deadline>Date.now()?value:null);
    setState({phase:'expired',message:journeyError({code:'SEARCH_EXPIRED'})});
  }
  function authFailure(){
    stop();resetSaves();snapshot.current=null;setOrigin(null);setDestination(null);setEditing(null);
    setState({phase:'anonymous',message:'로그인이 필요해요. 다시 로그인하고 위치를 선택해주세요.'});onAuthError?.();
  }
  useEffect(()=>()=>{pending.current?.abort();saver.current?.abort();},[]);
  useEffect(()=>{
    const deadlines=[origin?.deadline,destination?.deadline].filter(Number.isFinite);
    if(!deadlines.length)return;
    const timer=setTimeout(expire,Math.max(0,Math.min(...deadlines)-Date.now()));return()=>clearTimeout(timer);
  },[origin,destination]);
  useEffect(()=>{
    if(!state.deadline)return;
    const timer=setTimeout(expire,Math.max(0,state.deadline-Date.now()));return()=>clearTimeout(timer);
  },[state.deadline]);
  useEffect(()=>{
    if(!state.retryAt)return;
    const timer=setTimeout(()=>setState(value=>({...value,retryAt:null})),Math.max(0,state.retryAt-Date.now()));return()=>clearTimeout(timer);
  },[state.retryAt]);
  function failure(error){
    if(['AUTH_REQUIRED','SESSION_EXPIRED'].includes(error.code)){authFailure();return;}
    if(error.code==='SEARCH_EXPIRED'){expire();return;}
    if(error.code==='UNSUPPORTED_REGION'){
      stop();resetSaves();snapshot.current=null;setOrigin(null);setDestination(null);setEditing(null);
      setState({phase:'unsupported'});return;
    }
    if(['VERSION_CONFLICT','RESOURCE_NOT_FOUND','VALIDATION_ERROR','UNSUPPORTED_TIMING'].includes(error.code)){
      snapshot.current=null;resetSaves();setOrigin(null);setDestination(null);setEditing(null);
      setState({phase:'expired',message:journeyError(error)});return;
    }
    setState({phase:'error',code:error.code,message:journeyError(error),deadline:snapshot.current?.deadline,
      retryAt:error.code==='RATE_LIMITED'?Date.now()+(error.retryAfterMs||2000):null});
  }
  async function run(retry=false,readOnly=false){
    if(pending.current)return;
    preferenceEdited.current=true;
    if(!origin||!destination||Math.min(origin.deadline,destination.deadline)<=Date.now()){expire();return;}
    const controller=new AbortController();pending.current=controller;
    if(!retry||!snapshot.current){
      snapshot.current={body:{origin:origin.origin,destination:destination.origin,
        timing:{mode:'depart_now',timezone:'Asia/Seoul'},preferences:{route_preference:preference}},
        key:crypto.randomUUID(),deadline:Math.min(origin.deadline,destination.deadline,Date.now()+300000)};
    }
    const current=snapshot.current;
    setState({phase:current.accepted?'waiting':'loading',deadline:current.deadline});
    try{
      if(!current.accepted){
        if(readOnly)throw new ApiError('INVALID_RESPONSE');
        const csrf=await apiRequest('/api/v1/auth/csrf',{signal:controller.signal});
        if(typeof csrf.data?.csrf_token!=='string')throw new ApiError('INVALID_RESPONSE');
        const response=await apiRequest('/api/v1/journey-searches',{method:'POST',body:current.body,signal:controller.signal,
          headers:{'X-CSRF-Token':csrf.data.csrf_token,'Idempotency-Key':current.key}});
        if(controller.signal.aborted)return;
        if(response.status!==202||response.data?.status!=='queued'||!safeJourneyId(response.data.search_id)||!safeJourneyId(response.data.job_id))throw new ApiError('INVALID_RESPONSE');
        current.accepted=response.data;
      }
      if(controller.signal.aborted)return;
      setState({phase:'waiting',deadline:current.deadline});
      const result=await pollJourney(current.accepted,{signal:controller.signal,deadline:current.deadline,immediate:readOnly,
        onProgress:data=>{if(!controller.signal.aborted){current.deadline=Math.min(current.deadline,data.deadline);setState({phase:'waiting',deadline:current.deadline});}}});
      if(controller.signal.aborted)return;
      current.deadline=Math.min(current.deadline,result.deadline);
      if(Date.now()>=current.deadline){expire();return;}
      if(result.status==='failed'&&result.error?.code==='UNSUPPORTED_REGION'){failure(result.error);return;}
      setState(result.status==='failed'?{phase:'failed',code:result.error?.code,message:journeyError(result.error),deadline:current.deadline}
        :{phase:result.candidates.length?'ready':'empty',candidates:result.candidates,reasons:result.unavailable_reasons,deadline:current.deadline});
    }catch(error){if(!controller.signal.aborted)failure(error);}
    finally{if(pending.current===controller)pending.current=null;}
  }
  function edit(purpose,mode=routineToReplace?'saved':'current'){reset();resetSaves();setEditingMode(mode);setEditing(purpose);}
  function choose(value){
    if(!selection(value)||value.deadline<=Date.now()){failure(new ApiError('INVALID_RESPONSE'));return;}
    reset();resetSaves();if(editing==='origin')setOrigin(value);else setDestination(value);setEditing(null);
  }
  async function saveRoutine(candidateId,name,weekdays,targetArrival){
    if(reloadNeeded)return;
    if(saver.current)return;
    if(saves[candidateId]==='saved')return;
    if(!validSchedule(weekdays,targetArrival)){setSaveMessage('반복 요일과 목표 도착 시각을 확인해주세요.');return;}
    const refs=[placeRef(origin),placeRef(destination)];
    if(!refs[0]||!refs[1]){setSaveMessage(SAVED_PLACE_REQUIRED);return;}
    if(refs[0].place_id===refs[1].place_id){setSaveMessage('출발지와 도착지는 서로 다른 저장 장소를 선택해주세요.');return;}
    if(!snapshot.current?.accepted||Date.now()>=state.deadline){expire();return;}
    if(!state.candidates?.some(c=>c.candidate_id===candidateId)){failure(new ApiError('INVALID_RESPONSE'));return;}
    const controller=new AbortController();saver.current=controller;
    const body={name,origin_place_id:refs[0].place_id,destination_place_id:refs[1].place_id,
      search_id:snapshot.current.accepted.search_id,candidate_id:candidateId,weekdays,target_arrival_local_time:targetArrival,
      ...(routineToReplace ? {expected_version:routineToReplace.version} : {})};
    const signature=JSON.stringify(body);
    let attempt=saveAttempts.current[candidateId];
    if(!attempt||attempt.signature!==signature)attempt=saveAttempts.current[candidateId]={signature,key:crypto.randomUUID()};
    const key=attempt.key;
    setSaveMessage(null);
    setSaves(previous=>({...previous,[candidateId]:'saving'}));
    try{
      const csrf=await apiRequest('/api/v1/auth/csrf',{signal:controller.signal});
      if(typeof csrf.data?.csrf_token!=='string')throw new ApiError('INVALID_RESPONSE');
      const response=await apiRequest('/api/v1/routines'+(routineToReplace?'/'+routineToReplace.routine_id:''),{method:routineToReplace?'PATCH':'POST',
        body,
        signal:controller.signal,headers:{'X-CSRF-Token':csrf.data.csrf_token,'Idempotency-Key':key}});
      if(controller.signal.aborted)return;
      const data=response.data;
      if(response.status!==(routineToReplace?200:201)||!safeJourneyId(data?.routine_id)||typeof data.name!=='string'||data.name.length<1||data.name.length>30
        ||!safeJourneyId(data.route?.journey_plan_id)||typeof data.route.type!=='string'
        ||!Number.isSafeInteger(data.route.total_seconds)||data.route.total_seconds<0
        ||!Number.isSafeInteger(data.route.transfer_count)||data.route.transfer_count<0||data.route.transfer_count>2
        ||!['active','needs_attention'].includes(data.status)||!Number.isInteger(data.version)||data.version<1
        ||typeof data.origin_place?.label!=='string'||typeof data.destination_place?.label!=='string'
        ||!validSchedule(data.weekdays,data.target_arrival_local_time)||data.timezone!=='Asia/Seoul'
        ||routineToReplace&&(data.routine_id!==routineToReplace.routine_id||data.version!==routineToReplace.version+1||data.status!=='active'))throw new ApiError('INVALID_RESPONSE');
      setSaves(previous=>({...previous,[candidateId]:'saved'}));
      onRoutineSaved?.(data);
    }catch(error){
      if(controller.signal.aborted)return;
      setSaves(previous=>({...previous,[candidateId]:'error'}));
      if(routineToReplace&&['VERSION_CONFLICT','RESOURCE_NOT_FOUND'].includes(error.code)){
        stop();resetSaves();snapshot.current=null;setOrigin(null);setDestination(null);setEditing(null);setReloadNeeded(true);
        setState({phase:'expired',message:'루틴이나 장소가 변경됐거나 검색 결과가 만료됐어요. 최신 루틴을 확인한 뒤 다시 시도해주세요.'});return;
      }
      failure(error);
    }finally{if(saver.current===controller)saver.current=null;}
  }
  return <div className="journey-comparison">
    <button className="text-button comparison-back" onClick={onBack}><ArrowLeft size={18}/>오늘의 출발로 돌아가기</button>
    {routineToReplace&&<div className="info-box"><strong>‘{routineToReplace.name}’ {needsRoutineRecovery(routineToReplace)?'루틴을 복구해요':'경로를 바꿔요'}</strong>{needsRoutineRecovery(routineToReplace)&&<p>{routineRecoveryMessage(routineToReplace)}</p>}<ol><li>출발·도착 저장 장소를 다시 선택해요. 새 장소도 저장할 수 있어요.</li><li>현재 장소로 경로 후보를 조회하고 이동 구간을 확인해요.</li><li>이 경로로 루틴 변경을 눌러 이름·반복 일정과 함께 변경 저장해요.</li></ol><p>변경 저장 전까지 기존 루틴과 일정은 유지돼요.</p></div>}
    {reloadNeeded&&<div className="info-box" role="alert"><p>최신 목록에서 루틴과 장소를 다시 확인해주세요.</p><button className="secondary" onClick={onRoutineReload||onBack}>최신 루틴 다시 확인</button></div>}
    <div className="page-heading"><div><p className="eyebrow">COMPARE YOUR ROUTE</p><h1>내 이동 경로를 비교해요<span>.</span></h1><p>출발·도착지를 직접 고르고 예상 시간과 구간을 확인해요.</p></div></div>
    <section className="card comparison-form"><h2>어디에서 어디로 갈까요?</h2>
      <div className="comparison-endpoints">{[['origin','출발지',origin],['destination','도착지',destination]].map(([key,label,value])=><div className="comparison-endpoint" key={key}><span className="soft-icon"><MapPin size={20}/></span><div><h3>{label}</h3><p>{value?value.label:'위치를 선택해주세요'}</p>{value&&<p className="candidate-note">{value.location_address}</p>}<button className="secondary" disabled={editingBusy} onClick={()=>edit(key)}>{label} {value?'변경':'선택'}</button></div></div>)}</div>
      {editing&&<div className="comparison-editor"><div className="section-heading"><h2>{editing==='origin'?'출발지':'도착지'} 선택</h2><button className="text-button" disabled={editingBusy} onClick={()=>setEditing(null)}>위치 선택 취소</button></div><OriginSelector key={editing+':'+editingMode} purpose={editing} initialMode={editingMode}
        initialLocation={editingMode==='new' && (editing==='origin'?origin:destination)?.origin?.type==='map_pin' ? (editing==='origin'?origin:destination).location : null}
        onSelect={choose} onLogin={onLogin} onAuthError={authFailure} onBusyChange={setEditingBusy}/></div>}
      {origin&&destination&&!canSave&&<div className="info-box routine-save-help"><p>{placeRef(origin)&&placeRef(destination)?'출발지와 도착지는 서로 다른 저장 장소를 선택해주세요.':SAVED_PLACE_REQUIRED}</p><p>새 장소를 이 화면에서 저장하고 선택할 수 있어요. 장소를 선택한 뒤 경로를 다시 조회해주세요.</p><div className="button-row"><button className="secondary" disabled={editingBusy} onClick={()=>edit('origin','saved')}>출발지 저장 장소 선택</button><button className="secondary" disabled={editingBusy} onClick={()=>edit('destination','saved')}>도착지 저장 장소 선택</button><button className="secondary" disabled={editingBusy} onClick={()=>edit('origin','new')}>출발 장소 새로 저장</button><button className="secondary" disabled={editingBusy} onClick={()=>edit('destination','new')}>도착 장소 새로 저장</button></div></div>}
      <label className="comparison-sort">비교 기준<select value={preference} disabled={busy} onChange={event=>{preferenceEdited.current=true;setPreference(event.target.value);if(!['ready','empty','failed'].includes(state.phase))reset();}}><option value="balanced">전체 예상 시간순</option><option value="fewer_transfers">환승 적은 순</option><option value="less_walking">제공된 도보 시간순</option></select></label>
      <p className="candidate-note">조회된 후보 안에서 정렬해요. 빠진 도보 구간과 실제 운행 방향은 따로 확인해야 해요.</p>
      <button className="primary" disabled={reloadNeeded||busy||!!editing||!origin||!destination||!!state.retryAt} onClick={()=>state.phase==='error'&&snapshot.current?run(true,!!snapshot.current.accepted):run()}>{busy?'경로 확인 중…':state.phase==='error'&&snapshot.current?(snapshot.current.accepted?'결과 다시 확인':'같은 요청 다시 확인'):state.phase==='failed'?'경로 후보 다시 조회':'경로 후보 조회'}<ArrowRight size={18}/></button>
    </section>
    {busy&&<div className="info-box" role="status">{state.phase==='loading'?'경로 검색을 접수하고 있어요.':'경로 후보를 확인하고 있어요. 잠시 기다려주세요.'}</div>}
    {state.message&&<div className="info-box" role="alert">{state.message}{state.retryAt&&<p>잠시 기다리면 다시 확인할 수 있어요.</p>}</div>}
    {['error','failed','expired'].includes(state.phase)&&<WalkingGuidance announce={false} phase={state.phase==='expired'?'expired':'error'} errorCode={state.code}/>}
    {saveMessage&&<div className="info-box" role="alert">{saveMessage}</div>}
    {state.phase==='anonymous'&&<button className="primary" onClick={onLogin}>로그인하기</button>}
    {['empty','unsupported'].includes(state.phase)&&<JourneyUnavailable unsupported={state.phase==='unsupported'} codes={state.reasons} onOrigin={()=>edit('origin')} onDestination={()=>edit('destination')}/>}
    {state.phase==='ready'&&<JourneyCandidates searchId={snapshot.current?.accepted?.search_id} key={snapshot.current?.accepted?.search_id} candidates={state.candidates} preference={preference} onRecheck={()=>run(true,true)} onSavedLocations={candidateId=>saves[candidateId]} onSaved={canSave?saveRoutine:undefined} defaultRoutineName={routineToReplace?.name||(origin&&destination?`${origin.label} → ${destination.label} 통근`:'')} defaultWeekdays={routineToReplace?.weekdays} defaultTarget={routineToReplace?.target_arrival_local_time} replacing={!!routineToReplace}/>}
  </div>;
}
