import { apiRequest, ApiError, isServerTime } from './api';

const integer = value => Number.isSafeInteger(value) && value >= 0;
const name = value => typeof value === 'string' && value.trim().length > 0 && value.length <= 200;
export const safeJourneyId = value => typeof value === 'string' && /^[A-Za-z0-9_-]{1,128}$/.test(value);
const code = value => typeof value === 'string' && /^[A-Z_]{1,64}$/.test(value);
const list = (value,max) => Array.isArray(value) && value.length <= max;
const stop = value => name(value?.name) && value.public_id === null && value.entrance_ref === null && value.platform_ref === null;
const sameStop = (a,b) => stop(a) && stop(b) && a.name === b.name;
const equal = (a,b) => Array.isArray(a) && a.length === b.length && a.every((value,index)=>value === b[index]);

export function validCandidate(c) {
  if (c?.model_version !== 'journey.v1' || !safeJourneyId(c.candidate_id) || c.validity !== 'insufficient_data'
    || c.estimated_arrival_at !== null || !equal(c.time_sources,['provider_estimate'])
    || !integer(c.total_seconds) || !integer(c.total_distance_meters) || !integer(c.walking_seconds)
    || !integer(c.transfer_count) || c.transfer_count > 2 || !integer(c.transfer_count_computed) || c.transfer_count_computed > 2
    || !list(c.ordered_legs,500) || !c.ordered_legs.length || !c.ordered_legs.every(leg=>leg&&typeof leg==='object') || !list(c.missing_segments,32)
    || !c.missing_segments.every(code) || !c.missing_segments.includes('PUBLIC_DIRECTION_UNVERIFIED')) return false;
  const legs=c.ordered_legs, transit=legs.filter(leg=>['BUS','SUBWAY'].includes(leg.type));
  if (!transit.length || new Set(legs.map(leg=>leg.leg_id)).size !== legs.length
    || c.transfer_count_computed !== transit.length-1) return false;
  const kinds=new Set(transit.map(leg=>leg.type));
  if (c.type !== (kinds.size === 2 ? 'BUS_AND_SUBWAY' : transit[0].type)) return false;
  for (const [index,leg] of legs.entries()) {
    if (!safeJourneyId(leg.leg_id) || leg.sequence !== index || !integer(leg.seconds) || !integer(leg.distance_meters)
      || leg.time_source !== 'provider_estimate' || !list(leg.stops,500) || !leg.stops.every(name)
      || !list(leg.vehicles,500) || !leg.vehicles.every(name) || !list(leg.vehicle_options,500)
      || leg.direction?.public_direction_id !== null) return false;
    if (leg.type === 'WALKING') {
      const expected=index<transit[0].sequence?'access':index>transit.at(-1).sequence?'egress':'transfer';
      if (leg.walking_role !== expected || leg.boarding !== null || leg.alighting !== null || leg.stops.length || leg.vehicles.length
        || leg.vehicle_options.length || leg.direction.source !== 'unknown' || leg.direction.from_stop_name !== null || leg.direction.to_stop_name !== null) return false;
    } else if (!['BUS','SUBWAY'].includes(leg.type) || leg.walking_role !== null || leg.stops.length < 2 || !leg.vehicles.length
      || !stop(leg.boarding) || !stop(leg.alighting) || leg.boarding.name !== leg.stops[0] || leg.alighting.name !== leg.stops.at(-1)
      || leg.direction.source !== 'provider_stop_order' || leg.direction.from_stop_name !== leg.boarding.name || leg.direction.to_stop_name !== leg.alighting.name
      || !equal(leg.vehicle_options.map(v=>v?.name),leg.vehicles) || !leg.vehicle_options.every(v=>v.provider_type === null || (name(v.provider_type) && v.provider_type.length <= 80))) return false;
  }
  if (!list(c.connections,2) || c.connections.length !== transit.length-1 || !c.connections.every(x=>x&&typeof x==='object') || new Set(c.connections.map(x=>x.connection_id)).size !== c.connections.length) return false;
  for (const [index,x] of c.connections.entries()) {
    const before=transit[index],after=transit[index+1],walks=legs.slice(before.sequence+1,after.sequence);
    if (!safeJourneyId(x.connection_id) || x.from_leg_id !== before.leg_id || x.to_leg_id !== after.leg_id
      || !sameStop(x.from_stop,before.alighting) || !sameStop(x.to_stop,after.boarding)
      || !equal(x.walking_leg_ids,walks.map(leg=>leg.leg_id)) || x.walking_seconds !== (walks.length ? walks.reduce((sum,leg)=>sum+leg.seconds,0) : null)
      || x.feasibility !== 'unknown' || x.physical_stop_match !== 'unconfirmed' || x.time_source !== 'provider_estimate') return false;
  }
  const walking=legs.filter(leg=>leg.type==='WALKING').reduce((sum,leg)=>sum+leg.seconds,0);
  const vehicle=transit.reduce((sum,leg)=>sum+leg.seconds,0),difference=c.total_seconds-walking-vehicle,t=c.timing_breakdown;
  if (!integer(walking+vehicle) || c.walking_seconds !== walking || t?.walking_seconds !== walking || t.in_vehicle_seconds !== vehicle
    || t.legs_total_seconds !== walking+vehicle || t.provider_total_seconds !== c.total_seconds
    || t.unallocated_seconds !== (difference >= 0 ? difference : null)
    || t.status !== (difference === 0 ? 'consistent' : difference > 0 ? 'unallocated' : 'inconsistent')) return false;
  const needed=[];
  if (transit[0].sequence===0) needed.push('ACCESS_WALK_MISSING');
  if (transit.at(-1).sequence===legs.length-1) needed.push('EGRESS_WALK_MISSING');
  if (c.connections.some(x=>x.walking_seconds===null)) needed.push('TRANSFER_WALK_MISSING');
  if (c.transfer_count!==c.transfer_count_computed) needed.push('TRANSFER_COUNT_MISMATCH');
  if (difference<0) needed.push('DURATION_TOTAL_MISMATCH');
  return needed.every(reason=>c.missing_segments.includes(reason));
}

export function readJourney(response, accepted) {
  const data=response.data;
  if (response.status !== 200 || data?.search_id !== accepted.search_id || data.job_id !== accepted.job_id
    || !['queued','running','succeeded','failed'].includes(data.status) || !isServerTime(data.expires_at) || !isServerTime(response.meta?.server_time)
    || !list(data.candidates,20) || !data.candidates.every(validCandidate)
    || new Set(data.candidates.map(c=>c.candidate_id)).size !== data.candidates.length
    || !list(data.unavailable_reasons,64) || !data.unavailable_reasons.every(code)
    || (data.status !== 'succeeded' && data.candidates.length)
    || (data.status === 'failed' ? !code(data.error?.code) : data.error !== null)) throw new ApiError('INVALID_RESPONSE');
  const remaining=Date.parse(data.expires_at)-Date.parse(response.meta.server_time);
  if (remaining<=0) throw new ApiError('SEARCH_EXPIRED');
  if (remaining>300000) throw new ApiError('INVALID_RESPONSE');
  return {...data,deadline:Date.now()+remaining};
}

export const formatJourneyTime = seconds => seconds===null?'확인 필요':seconds===0?'0분':seconds<60?'1분 미만':`${Math.ceil(seconds/60)}분`;
export const missingWalk = c => ['ACCESS_WALK_MISSING','TRANSFER_WALK_MISSING','EGRESS_WALK_MISSING'].some(reason=>c.missing_segments.includes(reason));
export function sortCandidates(candidates, preference) {
  const first=c=>preference==='fewer_transfers'?c.transfer_count:preference==='less_walking'?c.walking_seconds:c.total_seconds;
  return [...candidates].sort((a,b)=>first(a)-first(b)||a.total_seconds-b.total_seconds||a.transfer_count-b.transfer_count||a.walking_seconds-b.walking_seconds);
}

export function journeyError(error) {
  return ({AUTH_REQUIRED:'로그인이 필요해요.',SESSION_EXPIRED:'로그인이 만료됐어요. 다시 로그인해주세요.',
    VERSION_CONFLICT:'저장 장소 위치가 바뀌었어요. 출발·도착지를 다시 선택해주세요.',RESOURCE_NOT_FOUND:'검색 결과가 만료됐거나 장소를 사용할 수 없어요. 다시 선택해주세요.',
    SEARCH_EXPIRED:'위치 또는 검색 결과가 만료됐어요. 위치를 확인하고 다시 조회해주세요.',
    PROVIDER_TIMEOUT:'경로 서비스 응답이 늦어요. 잠시 후 다시 시도해주세요.',PROVIDER_UNAVAILABLE:'경로 서비스에 연결할 수 없어요. 잠시 후 다시 시도해주세요.',
    JOB_INTERRUPTED:'경로 검색이 중단됐어요. 새로 조회해주세요.',UNSUPPORTED_REGION:'서울·경기 안의 위치를 선택해주세요.',
    RATE_LIMITED:'요청이 많아요. 잠시 기다린 뒤 다시 확인해주세요.',INVALID_RESPONSE:'경로 정보를 확인할 수 없어요. 다시 확인해주세요.',
    PROVIDER_RESPONSE_INVALID:'경로 구간을 확인할 수 없어요. 새로 조회해주세요.',NETWORK_ERROR:'서버에 연결할 수 없어요. 잠시 후 다시 확인해주세요.',
    TIMEOUT:'응답이 늦어 확인을 멈췄어요. 다시 확인해주세요.'})[error?.code] || '경로를 확인하지 못했어요. 다시 시도해주세요.';
}

const cancelled=()=>new DOMException('Cancelled','AbortError');
function visible(signal) {
  if (signal.aborted) return Promise.reject(cancelled());
  if (document.visibilityState!=='hidden') return Promise.resolve();
  return new Promise((resolve,reject)=>{
    const clean=()=>{document.removeEventListener('visibilitychange',change);signal.removeEventListener('abort',abort);};
    const change=()=>{if(document.visibilityState!=='hidden'){clean();resolve();}};
    const abort=()=>{clean();reject(cancelled());};
    document.addEventListener('visibilitychange',change);signal.addEventListener('abort',abort,{once:true});
  });
}
function delay(ms,signal) {
  if(signal.aborted)return Promise.reject(cancelled());
  return new Promise((resolve,reject)=>{
    const abort=()=>{clearTimeout(timer);reject(cancelled());};
    const timer=setTimeout(()=>{signal.removeEventListener('abort',abort);resolve();},ms);
    signal.addEventListener('abort',abort,{once:true});
  });
}
export async function pollJourney(accepted,{signal,deadline,onProgress,immediate=false}) {
  let attempt=0,next=immediate?0:2000;
  while(true){
    await visible(signal);if(next)await delay(next,signal);await visible(signal);
    if(Date.now()>=deadline)throw new ApiError('SEARCH_EXPIRED');
    const request=new AbortController();const abort=()=>request.abort();
    const hide=()=>{if(document.visibilityState==='hidden')request.abort();};
    signal.addEventListener('abort',abort,{once:true});document.addEventListener('visibilitychange',hide);
    if(signal.aborted)request.abort();
    let response;
    try{response=await apiRequest('/api/v1/journey-searches/'+encodeURIComponent(accepted.search_id),{signal:request.signal});}
    catch(error){if(request.signal.aborted&&!signal.aborted){next=0;continue;}throw error;}
    finally{signal.removeEventListener('abort',abort);document.removeEventListener('visibilitychange',hide);}
    if(signal.aborted)throw cancelled();
    const data=readJourney(response,accepted);deadline=Math.min(deadline,data.deadline);
    if(Date.now()>=deadline)throw new ApiError('SEARCH_EXPIRED');
    onProgress?.({...data,deadline});
    if(['succeeded','failed'].includes(data.status))return {...data,deadline};
    attempt++;next=response.retryAfterMs??[2000,5000,10000,30000][Math.min(attempt,3)];
  }
}
