import {apiRequest,ApiError,isServerTime} from './api';
import {safeJourneyId} from './journeys';
const invalid=()=>{throw new ApiError('INVALID_RESPONSE');};
export function readOnboard(response,trip){
 const d=response.data,server=response.meta?.server_time,p=trip.progress;
 if(response.status!==200||d?.model_version!=='trip.onboard.v1'||d.trip_id!==trip.trip_id||d.trip_version!==trip.version
  ||p?.stage!=='onboard'||d.current_leg_id!==p.current_leg_id||d.anchor_event_id!==p.anchor_event_id
  ||!safeJourneyId(d.current_leg_id)||!safeJourneyId(d.anchor_event_id)||!['estimated','needs_data'].includes(d.status)
  ||d.source!=='manual_vehicle_match'||d.timing_basis!=='receipt_estimate'||d.source_status!=='unknown'||d.generated_at!==null
  ||![server,d.expires_at].every(isServerTime)||Date.parse(d.expires_at)<=Date.parse(server)||Date.parse(d.expires_at)-Date.parse(server)>120000
  ||!Array.isArray(d.reasons)||!d.reasons.every(v=>typeof v==='string'&&/^[A-Z_]{1,64}$/.test(v)))invalid();
 if(d.status==='estimated'){
  if(![d.received_at,d.estimated_alighting_at].every(isServerTime)||Date.parse(d.received_at)>Date.parse(server)
   ||Date.parse(server)-Date.parse(d.received_at)>120000||Date.parse(d.expires_at)>Date.parse(d.received_at)+120000
   ||!Number.isSafeInteger(d.remaining_seconds)||d.remaining_seconds<=0||d.remaining_seconds>86400
   ||Math.abs(d.remaining_seconds-Math.floor((Date.parse(d.estimated_alighting_at)-Date.parse(server))/1000))>1)invalid();
 }else if(d.remaining_seconds!==null||d.estimated_alighting_at!==null)invalid();
 const serverMs=Date.parse(server),receivedMono=performance.now();
 return {...response,serverMs,receivedMono,deadline:receivedMono+Date.parse(d.expires_at)-serverMs};
}
export async function getOnboard(trip,signal){
 return readOnboard(await apiRequest(`/api/v1/trips/${trip.trip_id}/onboard-guidance?expected_version=${trip.version}`,{signal,timeoutMs:25000}),trip);
}
export async function confirmOnboard(trip,suffix,signal){
 if(!/^[0-9]{4}$/.test(suffix))throw new ApiError('VALIDATION_ERROR');
 const token=await apiRequest('/api/v1/auth/csrf',{signal});
 if(typeof token.data?.csrf_token!=='string')invalid();
 return readOnboard(await apiRequest(`/api/v1/trips/${trip.trip_id}/onboard-confirmations`,{method:'POST',signal,timeoutMs:25000,
  headers:{'X-CSRF-Token':token.data.csrf_token},body:{expected_version:trip.version,anchor_event_id:trip.progress.anchor_event_id,leg_id:trip.progress.current_leg_id,plate_suffix:suffix}}),trip);
}
