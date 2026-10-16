import {apiRequest,ApiError} from './api';
import {safeJourneyId} from './journeys';
const invalid=()=>{throw new ApiError('INVALID_RESPONSE');};
export function readPersonalization(value){
 if(!value||!['learning','active'].includes(value.status)||!Number.isSafeInteger(value.profile_version)||value.profile_version<1
  ||!Array.isArray(value.factors)||value.factors.length!==1||value.factors[0].type!=='provider_mapped_access'
  ||!Number.isFinite(value.factors[0].value)||value.factors[0].value<.5||value.factors[0].value>2
  ||!['valid','excluded'].every(k=>Number.isSafeInteger(value.sample_counts?.[k])&&value.sample_counts[k]>=0)
  ||typeof value.can_restore!=='boolean'||value.policy_version!=='manual-walking.v1'
  ||!value.quality||!['baseline_mae_seconds','personalized_mae_seconds'].every(k=>value.quality[k]===null||Number.isFinite(value.quality[k])&&value.quality[k]>=0))invalid();
 return value;
}
export async function personalization(signal){return readPersonalization((await apiRequest('/api/v1/me/personalization',{signal})).data);}
async function post(path,body,signal){
 const token=(await apiRequest('/api/v1/auth/csrf',{signal})).data?.csrf_token;
 if(typeof token!=='string')invalid();
 return (await apiRequest(path,{method:'POST',body,headers:{'X-CSRF-Token':token},signal})).data;
}
export async function changePersonalization(kind,operation,signal){
 if(!['reset','restore'].includes(kind))invalid();
 return readPersonalization(await post('/api/v1/me/personalization/'+kind,operation,signal));
}
export async function learnWalking(tripId,body,signal){
 if(!safeJourneyId(tripId))invalid();
 const value=await post(`/api/v1/trips/${tripId}/walking-observation`,body,signal);
 if(!value||!safeJourneyId(value.observation_id)||!['valid','excluded'].includes(value.status)
  ||!Array.isArray(value.exclusion_reasons)||!value.exclusion_reasons.every(r=>typeof r==='string')
  ||typeof value.updated!=='boolean'||!Number.isSafeInteger(value.sample_count)||value.sample_count<0
  ||!Number.isSafeInteger(value.profile_version)||value.profile_version<1)invalid();
 return value;
}
