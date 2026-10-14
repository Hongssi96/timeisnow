import {apiRequest,ApiError,isServerTime} from './api';
import {safeJourneyId,pollJourney} from './journeys';
import {readTrip} from './trips';

const invalid=()=>{throw new ApiError('INVALID_RESPONSE');};
export function readRemaining(response,trip,searchId){
 const d=response.data,server=response.meta?.server_time;
 if(response.status!==200||d?.model_version!=='trip.remaining.v1'||d.trip_id!==trip.trip_id||d.trip_version!==trip.version||d.search_id!==searchId
  ||!['searching','ready','no_routes','route_changed','ambiguous_route','insufficient_data','not_enough_time','stale','unsupported'].includes(d.status)
  ||![server,d.calculated_at,d.valid_until].every(isServerTime)||Date.parse(d.calculated_at)>Date.parse(server)+1000
  ||Date.parse(d.valid_until)<=Date.parse(server)||Date.parse(d.valid_until)-Date.parse(server)>120000
  ||typeof d.valid_for_guidance!=='boolean'||!Number.isInteger(d.buffer_seconds)||d.buffer_seconds<0||d.buffer_seconds>1800
  ||!(d.candidate_id===null||safeJourneyId(d.candidate_id))
  ||!['meets_buffer','below_buffer','unreachable','unknown'].includes(d.slack_status)||!['none','source_generation','receipt_estimate'].includes(d.timing_basis)
  ||!['not_checked','estimated_feasible','unavailable','unknown','stale'].includes(d.connection_status)
  ||!Array.isArray(d.reasons)||!d.reasons.every(x=>typeof x==='string'&&/^[A-Z_]{1,64}$/.test(x))
  ||!Array.isArray(d.transfers)||d.transfers.length>2)invalid();
 if(d.valid_for_guidance){
  if(d.status!=='ready'||!safeJourneyId(d.candidate_id)||!Number.isSafeInteger(d.remaining_approach_seconds)||d.remaining_approach_seconds<=0
   ||!isServerTime(d.vehicle_arrival_at)||Date.parse(d.vehicle_arrival_at)<=Date.parse(server)||d.timing_basis==='none'
   ||!Number.isSafeInteger(d.slack_seconds)||d.slack_seconds<0
   ||d.slack_seconds!==Math.floor((Date.parse(d.vehicle_arrival_at)-Date.parse(d.calculated_at))/1000-d.remaining_approach_seconds)
   ||d.slack_status!==(d.slack_seconds>=d.buffer_seconds?'meets_buffer':'below_buffer'))invalid();
 }else if([d.remaining_approach_seconds,d.vehicle_arrival_at,d.slack_seconds,d.target_evaluation].some(x=>x!==null)||d.transfers.length||d.slack_status!=='unknown'||d.timing_basis!=='none')invalid();
 for(const t of d.transfers){
  if(!['connection_id','from_leg_id','to_leg_id'].every(k=>safeJourneyId(t[k]))||!['estimated_feasible','unavailable','unknown'].includes(t.feasibility)
   ||!['none','source_generation','receipt_estimate'].includes(t.time_source)||!Number.isSafeInteger(t.transfer_buffer_seconds)||t.transfer_buffer_seconds<0||t.transfer_buffer_seconds>1800
   ||(t.transfer_walk_seconds!==null&&(!Number.isSafeInteger(t.transfer_walk_seconds)||t.transfer_walk_seconds<=0))
   ||[t.estimated_alighting_at,t.minimum_boarding_at,t.next_boarding_at].some(x=>x!==null&&!isServerTime(x))
   ||(t.feasibility==='estimated_feasible'&&(!isServerTime(t.next_boarding_at)||!isServerTime(t.minimum_boarding_at)||Date.parse(t.next_boarding_at)<Date.parse(t.minimum_boarding_at))))invalid();
 }
 const t=d.target_evaluation;
 if(t!==null){
  if(t.model_version!=='target.arrival.v1'||t.scope!=='selected_routine_candidate'||!isServerTime(t.evaluated_at)
   ||!['not_configured','estimated_meets','estimated_late','target_passed','unknown','stale'].includes(t.status))invalid();
  if(['estimated_meets','estimated_late'].includes(t.status)&&(!isServerTime(t.target_arrival_at)||!isServerTime(t.estimated_destination_arrival_at)
   ||!Number.isSafeInteger(t.margin_seconds)||t.margin_seconds!==Math.floor((Date.parse(t.target_arrival_at)-Date.parse(t.estimated_destination_arrival_at))/1000)
   ||(t.status==='estimated_meets')!==(t.margin_seconds>=0)))invalid();
  if(!['estimated_meets','estimated_late'].includes(t.status)&&(t.margin_seconds!==null||t.estimated_destination_arrival_at!==null))invalid();
 }
 return {...response,deadline:performance.now()+Date.parse(d.valid_until)-Date.parse(server),serverMs:Date.parse(server),receivedMono:performance.now()};
}
export async function getRemaining(trip,searchId,signal){
 return readRemaining(await apiRequest(`/api/v1/trips/${trip.trip_id}/remaining-searches/${searchId}/guidance?expected_version=${trip.version}`,{signal,timeoutMs:25000}),trip,searchId);
}
export async function refreshRemaining(trip,position,signal){
 readTrip(trip);
 const csrf=await apiRequest('/api/v1/auth/csrf',{signal});if(typeof csrf.data?.csrf_token!=='string')invalid();
 const r=await apiRequest(`/api/v1/trips/${trip.trip_id}/remaining-searches`,{method:'POST',signal,
  headers:{'X-CSRF-Token':csrf.data.csrf_token,'Idempotency-Key':crypto.randomUUID()},
  body:{expected_version:trip.version,stage:'before_first_boarding',position_confirmed:true,origin:position.origin}});
 const d=r.data;
 if(r.status!==202||d?.trip_id!==trip.trip_id||d.trip_version!==trip.version||!safeJourneyId(d.search_id)||!safeJourneyId(d.job_id)||d.status!=='queued'
  ||!isServerTime(d.position_valid_until)||!isServerTime(r.meta?.server_time))invalid();
 const remaining=Date.parse(d.position_valid_until)-Date.parse(r.meta.server_time);if(remaining<=0||remaining>120000)invalid();
 const search=await pollJourney(d,{signal,deadline:Date.now()+remaining,immediate:true});
 if(search.status==='failed')throw new ApiError(search.error?.code||'PROVIDER_UNAVAILABLE');
 return getRemaining(trip,search.search_id,signal);
}
