import {apiRequest,ApiError} from './api';
import {safeJourneyId} from './journeys';
import {readTrip,readEvent} from './trips';
import {readPersonalization} from './personalization';
const invalid=()=>{throw new ApiError('INVALID_RESPONSE');};
export async function records(cursor,signal){
 if(cursor&&!safeJourneyId(cursor))invalid();
 const value=(await apiRequest('/api/v1/trips?limit=20'+(cursor?'&cursor='+cursor:''),{signal})).data;
 if(!Array.isArray(value?.items)||value.items.length>20||value.next_cursor!==null&&!safeJourneyId(value.next_cursor))invalid();
 return {...value,items:value.items.map(readTrip)};
}
export async function record(tripId,signal){
 if(!safeJourneyId(tripId))invalid();
 const value=(await apiRequest('/api/v1/trips/'+tripId,{signal})).data;
 if(readTrip(value?.trip).trip_id!==tripId||!Array.isArray(value.events)||!Array.isArray(value.corrections))invalid();
 value.events.forEach(e=>readEvent(e,tripId));return value;
}
export async function observation(tripId,signal){
 if(!safeJourneyId(tripId))invalid();
 const value=(await apiRequest(`/api/v1/trips/${tripId}/walking-observation`,{signal})).data;
 if(value!==null&&(!safeJourneyId(value.observation_id)||!Number.isSafeInteger(value.version)||value.version<1
  ||!['valid','excluded'].includes(value.status)))invalid();
 return value;
}
export async function mutateRecord(operation,signal){
 const {kind,tripId,eventId,body}=operation;
 if(!safeJourneyId(tripId)||!['event','conditions','delete'].includes(kind)||kind==='event'&&!safeJourneyId(eventId))invalid();
 const token=(await apiRequest('/api/v1/auth/csrf',{signal})).data?.csrf_token;if(typeof token!=='string')invalid();
 const suffix=kind==='event'?'/events/'+eventId:kind==='conditions'?'/walking-observation':'';
 const value=(await apiRequest('/api/v1/trips/'+tripId+suffix,{method:kind==='delete'?'DELETE':'PATCH',body,signal,headers:{'X-CSRF-Token':token}})).data;
 readPersonalization(value?.personalization);
 if(kind==='delete'&&(value.deleted!==true||value.trip_id!==tripId))invalid();
 if(kind==='event')readEvent(value.event,tripId);
 if(kind==='conditions'&&(!value.observation||!Number.isSafeInteger(value.observation.version)))invalid();
 return value;
}
