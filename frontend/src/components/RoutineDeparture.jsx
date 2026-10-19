import React,{useCallback,useEffect,useState,useRef} from 'react';
import {ApiError} from '../lib/api';
import {needsRoutineRecovery} from '../lib/routines';
import {refreshRoutine,getRoutineDeparture,routineDepartureError,estimateRoutineWalk} from '../lib/routineDeparture';
import FirstArrivals from './FirstArrivals';
import WalkingGuidance from './WalkingGuidance';

const unavailable={no_routes:'현재 조회된 경로가 없어요.',route_changed:'저장한 노선과 같은 경로를 찾지 못했어요. 경로를 다시 선택해주세요.',ambiguous_route:'같은 노선의 후보가 여러 개여서 출발 정보를 확정하지 못했어요. 경로를 다시 선택해주세요.'};
export default function RoutineDeparture({routine,onRouteChange}) {
  const [attempt,setAttempt]=useState(0),[state,setState]=useState({phase:'loading'});
  const [ai,setAi]=useState({phase:'idle'}),aiRequest=useRef(null);
  const reported=useRef(false),[hasReported,setHasReported]=useState(false);
  const onReported=useCallback(()=>{reported.current=true;setHasReported(true);aiRequest.current?.abort();},[]);
  const onCancelled=useCallback(()=>{reported.current=false;setHasReported(false);setAttempt(n=>n+1);},[]);
  const recovery=needsRoutineRecovery(routine);
  useEffect(()=>{
    let disposed=false,pending=null,timer=null,expired=false,failed=false;
    reported.current=false;setHasReported(false);
    setState({phase:'loading'});
    async function load(){
      if(disposed||recovery||document.hidden||pending||failed||reported.current)return;
      const controller=new AbortController();pending=controller;setState({phase:'loading'});
      try{
        const value=await refreshRoutine(routine,controller.signal);
        if(disposed||controller.signal.aborted)return;
        expired=false;setState({phase:'ready',...value,initial:value.response.data.departure?{...value.response,data:value.response.data.departure}:null});
        const delay=Math.max(0,value.search.deadline-Date.now());
        timer=setTimeout(()=>{if(reported.current)return;expired=true;setState({phase:'expired'});if(!document.hidden)load();},delay);
      }catch(error){if(!disposed&&!controller.signal.aborted){failed=true;setState({phase:'error',message:routineDepartureError(error)});}}
      finally{if(pending===controller)pending=null;}
    }
    function visibility(){if(document.hidden){pending?.abort();pending=null;}else if(expired||!timer)load();}
    load();document.addEventListener('visibilitychange',visibility);
    return()=>{disposed=true;pending?.abort();clearTimeout(timer);document.removeEventListener('visibilitychange',visibility);};
  },[routine.routine_id,routine.version,recovery,attempt]);
  const searchId=state.search?.search_id;
  useEffect(()=>{setAi({phase:'idle'});return()=>aiRequest.current?.abort();},[routine.routine_id,routine.version,searchId]);
  const personalExpiry=state.response?.data?.departure?.personal_walk?.expires_at;
  useEffect(()=>{
    if(!personalExpiry)return;
    const timer=setTimeout(()=>{
      setState(previous=>previous.response?.data?.departure?.personal_walk?.expires_at===personalExpiry?
        {...previous,response:{...previous.response,data:{...previous.response.data,departure:{...previous.response.data.departure,personal_walk:null}}}}:previous);
      setAi({phase:'expired'});
    },Math.max(0,Date.parse(personalExpiry)-Date.now()));
    return()=>clearTimeout(timer);
  },[personalExpiry]);
  async function applyWalk(){
    if(aiRequest.current||!searchId||reported.current)return;
    const controller=new AbortController();aiRequest.current=controller;setAi({phase:'loading'});
    try{
      const result=await estimateRoutineWalk(routine,searchId,crypto.randomUUID(),controller.signal);
      if(controller.signal.aborted)return;
      if(result.data.status!=='validated'){setAi({phase:'needs_data'});return;}
      const response=await getRoutineDeparture(routine,searchId,controller.signal);
      if(controller.signal.aborted)return;
      setState(previous=>({...previous,response,initial:{...response,data:response.data.departure}}));setAi({phase:'ready'});
    }catch(error){if(!controller.signal.aborted)setAi({phase:'error',code:error?.code});}
    finally{if(aiRequest.current===controller)aiRequest.current=null;}
  }
  const loader=useCallback(async(_,candidateId,signal)=>{
    const response=await getRoutineDeparture(routine,searchId,signal);
    if(response.data.status!=='ready'||response.data.candidate_id!==candidateId)throw new ApiError('VERSION_CONFLICT');
    if(!signal?.aborted)setState(previous=>({...previous,response}));
    return {...response,data:response.data.departure};
  },[routine.routine_id,routine.version,searchId]);
  if(recovery)return <><WalkingGuidance route={routine.route} source="routine" phase="expired"/><div className="info-box">루틴을 복구한 뒤 최신 출발 안내를 확인할 수 있어요.</div></>;
  const wrapper=state.response?.data;
  return <div aria-label="루틴 최신 출발 안내">
    {wrapper?.status==='ready'&&<FirstArrivals key={searchId} searchId={searchId} candidateId={wrapper.candidate_id} includeDeparture loader={loader}
      initialResponse={state.initial} routineId={routine.routine_id} onReported={onReported} onCancelled={onCancelled}/>}
    <WalkingGuidance route={routine.route} source="routine" phase={['error','expired'].includes(ai.phase)?ai.phase:'needs_data'} errorCode={ai.code} estimate={wrapper?.departure?.personal_walk}/>
    {wrapper?.status==='ready'&&!hasReported&&<div className="button-row"><button className="secondary" disabled={ai.phase==='loading'} onClick={applyWalk}>{ai.phase==='loading'?'개인 도보 산정 중…':'개인 도보 산정·저장값 적용'}</button></div>}
    {ai.phase==='needs_data'&&<p role="status">승차 지점과 보행 경로를 먼저 확인해야 개인 도보를 적용할 수 있어요.</p>}
    {state.phase==='loading'&&<p className="info-box" role="status">저장한 루틴의 최신 경로와 출발 정보를 확인하고 있어요…</p>}
    {state.phase==='expired'&&<p className="info-box" role="status">검색 정보가 만료됐어요. 최신 경로를 다시 확인해요.</p>}
    {state.phase==='error'&&<p className="info-box" role="alert">{state.message}</p>}
    {wrapper&&wrapper.status!=='ready'&&<div className="info-box" role="status"><p>{unavailable[wrapper.status]||'경로 검색이 아직 진행 중이에요.'}</p><button className="secondary" onClick={()=>onRouteChange(routine)}>경로 다시 선택</button></div>}
    <p className="candidate-note">저장한 장소에서 출발하는 첫 승차 기준 추정이에요. 목표 도착은 현재 선택 경로의 추정 평가예요. 출발할 때 수동 확인을 남길 수 있어요.</p>
    <button className="secondary" disabled={state.phase==='loading'} onClick={()=>setAttempt(n=>n+1)}>최신 출발 다시 확인</button>
  </div>;
}
