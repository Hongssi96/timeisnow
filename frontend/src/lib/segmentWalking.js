import {apiRequest,ApiError,isServerTime} from './api';
import {safeJourneyId} from './journeys';
const invalid=()=>{throw new ApiError('INVALID_RESPONSE');};
const kind=v=>['station_internal','transfer'].includes(v);
const stats=v=>Number.isInteger(v.sample_count)&&v.sample_count>=0&&v.sample_count<=20
 &&(v.estimate_seconds===null||Number.isInteger(v.estimate_seconds)&&v.estimate_seconds>=1&&v.estimate_seconds<=7200&&v.sample_count>=5);
export function readSegment(v){
 if(!v||!safeJourneyId(v.measurement_id)||!safeJourneyId(v.leg_id)||!kind(v.kind)||typeof v.label!=='string'||v.label.length<1||v.label.length>60
  ||!['recording','valid','excluded'].includes(v.status)||!Number.isInteger(v.version)||v.version<1||!isServerTime(v.started_at)
  ||v.finished_at!==null&&!isServerTime(v.finished_at)||!stats(v)||!Array.isArray(v.reasons)||!v.reasons.every(r=>typeof r==='string'&&r.length<80)
  ||typeof v.can_finish!=='boolean'||typeof v.apply_to_guidance!=='boolean'
  ||v.status==='valid'&&(!Number.isFinite(v.observed_seconds)||v.observed_seconds<1||v.observed_seconds>7200)
  ||(v.predicted_seconds===null)!==(v.predicted_arrival_at===null)
  ||v.predicted_seconds!==null&&Date.parse(v.predicted_arrival_at)!==Date.parse(v.started_at)+v.predicted_seconds*1000
  ||v.predicted_seconds!==null&&(!Number.isInteger(v.predicted_seconds)||v.predicted_seconds<1||v.predicted_seconds>7200)
  ||v.predicted_arrival_at!==null&&!isServerTime(v.predicted_arrival_at))invalid();return v;
}
export async function segments(tripId,signal){
 if(!safeJourneyId(tripId))invalid();const v=(await apiRequest(`/api/v1/trips/${tripId}/walking-segments`,{signal})).data;
 if(!Array.isArray(v?.items)||v.items.length>5||!Array.isArray(v.available)||v.available.length>2)invalid();v.items.forEach(readSegment);
 for(const a of v.available)if(!kind(a.kind)||!safeJourneyId(a.leg_id)||typeof a.name!=='string'||a.name.length>460
  ||!Array.isArray(a.variants)||a.variants.length>20||a.variants.some(v=>typeof v.label!=='string'||v.label.length>60||!stats(v)))invalid();return v;
}
export async function mutateSegment(tripId,operation,signal){
 if(!safeJourneyId(tripId)||!['start','confirm','exclude'].includes(operation.kind)||operation.kind!=='start'&&!safeJourneyId(operation.id))invalid();
 const token=(await apiRequest('/api/v1/auth/csrf',{signal})).data?.csrf_token;if(typeof token!=='string')invalid();
 const suffix=operation.kind==='start'?'':'/'+operation.id+(operation.kind==='confirm'?'/confirm':'');
 return readSegment((await apiRequest(`/api/v1/trips/${tripId}/walking-segments${suffix}`,{signal,
  method:operation.kind==='exclude'?'PATCH':'POST',headers:{'X-CSRF-Token':token},body:operation.body})).data);
}
