import React, { useEffect, useRef, useState } from 'react';
import { ArrowLeft, MapPin, ArrowRight } from 'lucide-react';
import { apiRequest, ApiError } from '../lib/api';
import { pollJourney, safeJourneyId, journeyError } from '../lib/journeys';
import OriginSelector from './OriginSelector';
import JourneyCandidates from './JourneyCandidates';

function selection(value) {
  const origin=value?.origin;
  if (!Number.isFinite(value?.deadline) || typeof value?.label !== 'string') return false;
  if (origin?.type==='saved_place') return safeJourneyId(origin.place_id) && Number.isInteger(origin.location_version) && origin.location_version>=1;
  return ['map_pin','current_location'].includes(origin?.type) && Number.isFinite(origin.latitude) && Math.abs(origin.latitude)<=90
    && Number.isFinite(origin.longitude) && Math.abs(origin.longitude)<=180
    && (origin.type==='map_pin' || origin.location_confirmed===true);
}

export default function JourneyComparison({ initialOrigin, onBack, onLogin, onAuthError }) {
  const [origin,setOrigin]=useState(()=>selection(initialOrigin)&&initialOrigin.deadline>Date.now()?initialOrigin:null);
  const [destination,setDestination]=useState(null);
  const [editing,setEditing]=useState(null);
  const [preference,setPreference]=useState('balanced');
  const [state,setState]=useState({phase:'idle'});
  const pending=useRef(null),snapshot=useRef(null);
  const busy=['loading','waiting'].includes(state.phase);
  function stop(){pending.current?.abort();pending.current=null;}
  function reset(){stop();snapshot.current=null;setState({phase:'idle'});}
  function expire(){
    stop();snapshot.current=null;setEditing(null);
    setOrigin(value=>value?.deadline>Date.now()?value:null);setDestination(value=>value?.deadline>Date.now()?value:null);
    setState({phase:'expired',message:journeyError({code:'SEARCH_EXPIRED'})});
  }
  function authFailure(){
    stop();snapshot.current=null;setOrigin(null);setDestination(null);setEditing(null);
    setState({phase:'anonymous',message:'로그인이 필요해요. 다시 로그인하고 위치를 선택해주세요.'});onAuthError?.();
  }
  useEffect(()=>()=>{pending.current?.abort();},[]);
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
    if(['VERSION_CONFLICT','RESOURCE_NOT_FOUND','VALIDATION_ERROR','UNSUPPORTED_REGION','UNSUPPORTED_TIMING'].includes(error.code)){
      snapshot.current=null;setOrigin(null);setDestination(null);setEditing(null);
      setState({phase:'expired',message:journeyError(error)});return;
    }
    setState({phase:'error',message:journeyError(error),deadline:snapshot.current?.deadline,
      retryAt:error.code==='RATE_LIMITED'?Date.now()+(error.retryAfterMs||2000):null});
  }
  async function run(retry=false,readOnly=false){
    if(pending.current)return;
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
      setState(result.status==='failed'?{phase:'failed',message:journeyError(result.error),deadline:current.deadline}
        :{phase:result.candidates.length?'ready':'empty',candidates:result.candidates,reasons:result.unavailable_reasons,deadline:current.deadline});
    }catch(error){if(!controller.signal.aborted)failure(error);}
    finally{if(pending.current===controller)pending.current=null;}
  }
  function edit(purpose){reset();setEditing(purpose);}
  function choose(value){
    if(!selection(value)||value.deadline<=Date.now()){failure(new ApiError('INVALID_RESPONSE'));return;}
    reset();if(editing==='origin')setOrigin(value);else setDestination(value);setEditing(null);
  }
  return <div className="journey-comparison">
    <button className="text-button comparison-back" onClick={onBack}><ArrowLeft size={18}/>오늘의 출발로 돌아가기</button>
    <div className="page-heading"><div><p className="eyebrow">COMPARE YOUR ROUTE</p><h1>내 이동 경로를 비교해요<span>.</span></h1><p>출발·도착지를 직접 고르고 예상 시간과 구간을 확인해요.</p></div></div>
    <section className="card comparison-form"><h2>어디에서 어디로 갈까요?</h2>
      <div className="comparison-endpoints">{[['origin','출발지',origin],['destination','도착지',destination]].map(([key,label,value])=><div className="comparison-endpoint" key={key}><span className="soft-icon"><MapPin size={20}/></span><div><h3>{label}</h3><p>{value?value.label:'위치를 선택해주세요'}</p>{value&&<p className="candidate-note">{value.location_address}</p>}<button className="secondary" onClick={()=>edit(key)}>{label} {value?'변경':'선택'}</button></div></div>)}</div>
      {editing&&<div className="comparison-editor"><div className="section-heading"><h2>{editing==='origin'?'출발지':'도착지'} 선택</h2><button className="text-button" onClick={()=>setEditing(null)}>위치 선택 취소</button></div><OriginSelector key={editing} purpose={editing} onSelect={choose} onLogin={onLogin} onAuthError={authFailure}/></div>}
      <label className="comparison-sort">비교 기준<select value={preference} disabled={busy} onChange={event=>{setPreference(event.target.value);if(!['ready','empty','failed'].includes(state.phase))reset();}}><option value="balanced">전체 예상 시간순</option><option value="fewer_transfers">환승 적은 순</option><option value="less_walking">제공된 도보 시간순</option></select></label>
      <p className="candidate-note">조회된 후보 안에서 정렬해요. 빠진 도보 구간과 실제 운행 방향은 따로 확인해야 해요.</p>
      <button className="primary" disabled={busy||!!editing||!origin||!destination||!!state.retryAt} onClick={()=>state.phase==='error'&&snapshot.current?run(true,!!snapshot.current.accepted):run()}>{busy?'경로 확인 중…':state.phase==='error'&&snapshot.current?(snapshot.current.accepted?'결과 다시 확인':'같은 요청 다시 확인'):state.phase==='failed'?'경로 후보 다시 조회':'경로 후보 조회'}<ArrowRight size={18}/></button>
    </section>
    {busy&&<div className="info-box" role="status">{state.phase==='loading'?'경로 검색을 접수하고 있어요.':'경로 후보를 확인하고 있어요. 잠시 기다려주세요.'}</div>}
    {state.message&&<div className="info-box" role="alert">{state.message}{state.retryAt&&<p>잠시 기다리면 다시 확인할 수 있어요.</p>}</div>}
    {state.phase==='anonymous'&&<button className="primary" onClick={onLogin}>로그인하기</button>}
    {state.phase==='empty'&&<section className="card empty-state"><h2>지금 비교할 경로가 없어요</h2><p>{state.reasons.includes('TRANSFER_LIMIT')?'현재 지원하는 최대 2회 환승 안의 후보가 없어요.':'이 위치에서 이용할 경로를 찾지 못했어요.'}</p><p>위치를 다시 선택하거나 잠시 후 새로 조회해주세요.</p></section>}
    {state.phase==='ready'&&<JourneyCandidates key={snapshot.current?.accepted?.search_id} candidates={state.candidates} preference={preference} onRecheck={()=>run(true,true)}/>}
  </div>;
}
