import {apiRequest,ApiError} from './api';
import {safeJourneyId} from './journeys';

export const walkingPreferences=['slow','normal','fast'];
export const routePreferences=['balanced','fewer_transfers','less_walking'];
export function readProfile(value){
  if(!value||!Number.isSafeInteger(value.version)||value.version<1||value.timezone!=='Asia/Seoul'
    ||!walkingPreferences.includes(value.walking_preference)||!routePreferences.includes(value.route_preference)
    ||!['first_boarding_buffer_seconds','transfer_buffer_seconds'].every(key=>Number.isSafeInteger(value[key])&&value[key]>=0&&value[key]<=1800)
    ||!Number.isFinite(value.walking_duration_factor)||value.walking_duration_factor<.5||value.walking_duration_factor>2)throw new ApiError('INVALID_RESPONSE');
  return value;
}
export async function getProfile(signal){
  const {data}=await apiRequest('/api/v1/me',{signal});
  if(!safeJourneyId(data?.user_id))throw new ApiError('INVALID_RESPONSE');
  return {owner:data.user_id,profile:readProfile(data.profile)};
}
export async function saveProfile(owner,version,changes,signal){
  const csrf=(await apiRequest('/api/v1/auth/csrf',{signal})).data?.csrf_token;
  if(typeof csrf!=='string')throw new ApiError('INVALID_RESPONSE');
  // Bind an open draft to the account that loaded it, including cross-tab sign-ins.
  if((await getProfile(signal)).owner!==owner)throw new ApiError('SESSION_CHANGED');
  const {data}=await apiRequest('/api/v1/me/profile',{method:'PATCH',signal,
    headers:{'X-CSRF-Token':csrf},body:{expected_version:version,...changes}});
  const profile=readProfile(data?.profile);
  if(data.profile_version!==profile.version||![version,version+1].includes(profile.version)
    ||Object.entries(changes).some(([key,value])=>profile[key]!==value))throw new ApiError('INVALID_RESPONSE');
  return profile;
}
