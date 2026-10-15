import {apiRequest,ApiError,isServerTime} from './api';
import {safeJourneyId,pollJourney} from './journeys';
import {readFirstDeparture,validPersonalWalk} from './departure';

export async function refreshRoutine(routine,signal) {
  const csrf=await apiRequest('/api/v1/auth/csrf',{signal});
  if(typeof csrf.data?.csrf_token!=='string')throw new ApiError('INVALID_RESPONSE');
  const response=await apiRequest(`/api/v1/routines/${routine.routine_id}/departure-searches`,{method:'POST',
    signal,headers:{'X-CSRF-Token':csrf.data.csrf_token,'Idempotency-Key':crypto.randomUUID()},body:{expected_version:routine.version}});
  const d=response.data;
  if(response.status!==202||d?.routine_id!==routine.routine_id||d.routine_version!==routine.version||!safeJourneyId(d.search_id)||!safeJourneyId(d.job_id)||d.status!=='queued')throw new ApiError('INVALID_RESPONSE');
  const search=await pollJourney(d,{signal,deadline:Date.now()+300000,immediate:true});
  if(search.status==='failed')throw new ApiError(search.error?.code||'PROVIDER_UNAVAILABLE');
  return {search,response:await getRoutineDeparture(routine,search.search_id,signal)};
}
export async function getRoutineDeparture(routine,searchId,signal) {
  const response=await apiRequest(`/api/v1/routines/${routine.routine_id}/departure-searches/${searchId}/first-departure?expected_version=${routine.version}`,{signal,timeoutMs:25000});
  const d=response.data;
  if(response.status!==200||d?.model_version!=='routine.departure.v1'||d.routine_id!==routine.routine_id||d.routine_version!==routine.version||d.search_id!==searchId
    ||!['searching','ready','no_routes','route_changed','ambiguous_route'].includes(d.status)||!isServerTime(d.expires_at)||!isServerTime(response.meta?.server_time)
    ||Date.parse(d.expires_at)<=Date.parse(response.meta.server_time)||Date.parse(d.expires_at)-Date.parse(response.meta.server_time)>300000)throw new ApiError('INVALID_RESPONSE');
  if(d.status==='ready'){
    if(!safeJourneyId(d.candidate_id)||!d.departure||Date.parse(d.departure.valid_until)>Date.parse(d.expires_at))throw new ApiError('INVALID_RESPONSE');
    readFirstDeparture({...response,data:d.departure},searchId,d.candidate_id);
  }else if(d.candidate_id!==null||d.departure!==null)throw new ApiError('INVALID_RESPONSE');
  return response;
}
export const routineDepartureError=error=>['AUTH_REQUIRED','SESSION_EXPIRED'].includes(error?.code)?'로그인 후 루틴 출발 안내를 다시 확인해주세요.':
  ['VERSION_CONFLICT','RESOURCE_NOT_FOUND'].includes(error?.code)?'루틴이나 장소가 바뀌었거나 검색이 만료됐어요. 루틴을 다시 확인해주세요.':
  error?.code==='RATE_LIMITED'?'조회가 많아요. 잠시 기다린 뒤 다시 확인해주세요.':'최신 출발 정보를 확인하지 못했어요. 다시 확인해주세요.';

export async function estimateRoutineWalk(routine,searchId,clientRequestId,signal){
  const csrf=await apiRequest('/api/v1/auth/csrf',{signal});
  if(typeof csrf.data?.csrf_token!=='string')throw new ApiError('INVALID_RESPONSE');
  const response=await apiRequest(`/api/v1/routines/${routine.routine_id}/departure-searches/${searchId}/walking-estimates`,{
    method:'POST',signal,timeoutMs:80000,headers:{'X-CSRF-Token':csrf.data.csrf_token},
    body:{expected_version:routine.version,client_request_id:clientRequestId}});
  const d=response.data;
  if(response.status!==200||d?.model_version!=='routine.walking.v1'||d.routine_id!==routine.routine_id||d.search_id!==searchId
    ||!['validated','needs_data'].includes(d.status)||!Array.isArray(d.reasons)
    ||(d.status==='validated'?!validPersonalWalk(d.estimate,response.meta?.server_time):d.estimate!==null))throw new ApiError('INVALID_RESPONSE');
  return response;
}
