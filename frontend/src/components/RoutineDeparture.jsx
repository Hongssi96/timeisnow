import React,{useCallback,useEffect,useState} from 'react';
import {ApiError} from '../lib/api';
import {needsRoutineRecovery} from '../lib/routines';
import {refreshRoutine,getRoutineDeparture,routineDepartureError} from '../lib/routineDeparture';
import FirstArrivals from './FirstArrivals';

const unavailable={no_routes:'현재 조회된 경로가 없어요.',route_changed:'저장한 노선과 같은 경로를 찾지 못했어요. 경로를 다시 선택해주세요.',ambiguous_route:'같은 노선의 후보가 여러 개여서 출발 정보를 확정하지 못했어요. 경로를 다시 선택해주세요.'};
export default function RoutineDeparture({routine,onRouteChange}) {
  const [attempt,setAttempt]=useState(0),[state,setState]=useState({phase:'loading'});
  const recovery=needsRoutineRecovery(routine);
  useEffect(()=>{
    let disposed=false,pending=null,timer=null,expired=false,failed=false;
    setState({phase:'loading'});
    async function load(){
      if(disposed||recovery||document.hidden||pending||failed)return;
      const controller=new AbortController();pending=controller;setState({phase:'loading'});
      try{
        const value=await refreshRoutine(routine,controller.signal);
        if(disposed||controller.signal.aborted)return;
        expired=false;setState({phase:'ready',...value,initial:value.response.data.departure?{...value.response,data:value.response.data.departure}:null});
        const delay=Math.max(0,value.search.deadline-Date.now());
        timer=setTimeout(()=>{expired=true;setState({phase:'expired'});if(!document.hidden)load();},delay);
      }catch(error){if(!disposed&&!controller.signal.aborted){failed=true;setState({phase:'error',message:routineDepartureError(error)});}}
      finally{if(pending===controller)pending=null;}
    }
    function visibility(){if(document.hidden){pending?.abort();pending=null;}else if(expired||!timer)load();}
    load();document.addEventListener('visibilitychange',visibility);
    return()=>{disposed=true;pending?.abort();clearTimeout(timer);document.removeEventListener('visibilitychange',visibility);};
  },[routine.routine_id,routine.version,recovery,attempt]);
  const searchId=state.search?.search_id;
  const loader=useCallback(async(_,candidateId,signal)=>{
    const response=await getRoutineDeparture(routine,searchId,signal);
    if(response.data.status!=='ready'||response.data.candidate_id!==candidateId)throw new ApiError('VERSION_CONFLICT');
    return {...response,data:response.data.departure};
  },[routine.routine_id,routine.version,searchId]);
  if(recovery)return <div className="info-box">루틴을 복구한 뒤 최신 출발 안내를 확인할 수 있어요.</div>;
  const wrapper=state.response?.data;
  return <div aria-label="루틴 최신 출발 안내">
    {state.phase==='loading'&&<p className="info-box" role="status">저장한 루틴의 최신 경로와 출발 정보를 확인하고 있어요…</p>}
    {state.phase==='expired'&&<p className="info-box" role="status">검색 정보가 만료됐어요. 최신 경로를 다시 확인해요.</p>}
    {state.phase==='error'&&<p className="info-box" role="alert">{state.message}</p>}
    {wrapper?.status==='ready'&&<FirstArrivals key={searchId} searchId={searchId} candidateId={wrapper.candidate_id} includeDeparture loader={loader}
      initialResponse={state.initial}/>}
    {wrapper&&wrapper.status!=='ready'&&<div className="info-box" role="status"><p>{unavailable[wrapper.status]||'경로 검색이 아직 진행 중이에요.'}</p><button className="secondary" onClick={()=>onRouteChange(routine)}>경로 다시 선택</button></div>}
    <p className="candidate-note">저장한 장소에서 출발하는 첫 승차 기준 추정이에요. 목표 도착 시각에 맞춘 출발과 실제 이동 시작은 아직 지원하지 않아요.</p>
    <button className="secondary" disabled={state.phase==='loading'} onClick={()=>setAttempt(n=>n+1)}>최신 출발 다시 확인</button>
  </div>;
}
