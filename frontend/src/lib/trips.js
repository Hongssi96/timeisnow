import {apiRequest,ApiError,isServerTime} from './api';
import {safeJourneyId} from './journeys';

const invalid=()=>{throw new ApiError('INVALID_RESPONSE');};
export function readEvent(event,tripId){
 if(!event||!['event_id','client_event_id','leg_id'].every(key=>safeJourneyId(event[key]))||event.trip_id!==tripId||event.type!=='departed'||event.source!=='manual'
  ||!isServerTime(event.occurred_at)||!isServerTime(event.received_at)||Date.parse(event.occurred_at)>Date.parse(event.received_at)
  ||!Number.isSafeInteger(event.input_delay_seconds)||event.input_delay_seconds<0||event.excluded!==false||event.version!==1)invalid();
 return event;
}
export function readTrip(value){
 if(!value||!safeJourneyId(value.trip_id)||!safeJourneyId(value.guidance_id)||(value.routine_id!==null&&!safeJourneyId(value.routine_id))
  ||!['active','cancelled'].includes(value.status)||!['assisted','baseline'].includes(value.measurement_mode)||!Number.isSafeInteger(value.version)||value.version<1
  ||!isServerTime(value.created_at)||!isServerTime(value.expires_at)||Date.parse(value.expires_at)<=Date.parse(value.created_at))invalid();
 if(value.departure_event!==null)readEvent(value.departure_event,value.trip_id);
 return value;
}
async function csrf(signal){const response=await apiRequest('/api/v1/auth/csrf',{signal});if(typeof response.data?.csrf_token!=='string')invalid();return response.data.csrf_token;}
export async function activeTrip(routineId,signal){
 if(!safeJourneyId(routineId))invalid();
 const response=await apiRequest(`/api/v1/trips?routine_id=${routineId}&status=active&limit=1`,{signal});
 if(!Array.isArray(response.data?.items)||response.data.items.length>1)invalid();
 const trip=response.data.items[0];if(trip){readTrip(trip);if(trip.routine_id!==routineId||trip.status!=='active')invalid();}
 return trip||null;
}
export async function confirmDeparture(operation,signal){
 if(!operation.trip){
  if(!safeJourneyId(operation.guidanceId))invalid();
  const token=await csrf(signal);
  const response=await apiRequest('/api/v1/trips',{method:'POST',signal,headers:{'X-CSRF-Token':token},body:{guidance_id:operation.guidanceId,measurement_mode:'assisted'}});
  const trip=readTrip(response.data);if(trip.guidance_id!==operation.guidanceId||trip.routine_id!==operation.routineId||trip.measurement_mode!=='assisted'||trip.status!=='active')invalid();
  operation.trip=trip;
 }
 const trip=operation.trip;
 if(trip.departure_event)return trip;
 const detail=await apiRequest(`/api/v1/trips/${trip.trip_id}`,{signal});
 const saved=readTrip(detail.data?.trip);
 const leg=detail.data?.guidance?.candidate?.ordered_legs?.[0]?.leg_id;
 if(saved.trip_id!==trip.trip_id||saved.guidance_id!==trip.guidance_id||saved.status!=='active'||!safeJourneyId(leg))invalid();
 if(saved.departure_event)return saved;
 const token=await csrf(signal);
 const body={client_event_id:operation.eventId,type:'departed',occurred_at:operation.occurredAt,leg_id:leg,source:'manual'};
 const response=await apiRequest(`/api/v1/trips/${trip.trip_id}/events`,{method:'POST',signal,headers:{'X-CSRF-Token':token},body});
 const event=readEvent(response.data,trip.trip_id);
 if(event.client_event_id!==operation.eventId||event.leg_id!==leg||Date.parse(event.occurred_at)!==Date.parse(operation.occurredAt))invalid();
 return {...saved,departure_event:event};
}
export async function cancelTrip(trip,signal){
 readTrip(trip);const token=await csrf(signal);
 const response=await apiRequest(`/api/v1/trips/${trip.trip_id}`,{method:'PATCH',signal,headers:{'X-CSRF-Token':token},body:{outcome:'cancelled',expected_version:trip.version}});
 const result=readTrip(response.data);if(result.trip_id!==trip.trip_id||result.status!=='cancelled')invalid();return result;
}
