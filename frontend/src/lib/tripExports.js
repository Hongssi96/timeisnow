import {apiRequest,ApiError,isServerTime} from './api';
import {safeJourneyId} from './journeys';

export async function exportRecords(days,signal){
 if(![7,30,90].includes(Number(days)))throw new ApiError('VALIDATION_ERROR');
 const at=Date.now(),from=new Date(at-Number(days)*86400000).toISOString(),to=new Date(at).toISOString();
 const csrf=(await apiRequest('/api/v1/auth/csrf',{signal})).data?.csrf_token;
 if(typeof csrf!=='string')throw new ApiError('INVALID_RESPONSE');
 const job=(await apiRequest('/api/v1/trip-exports',{method:'POST',signal,
  headers:{'X-CSRF-Token':csrf},body:{from,to,format:'json'}})).data;
 if(!safeJourneyId(job?.job_id)||job.status!=='succeeded'
  ||job.result_ref!==`/api/v1/trip-exports/${job.job_id}/download`
  ||!isServerTime(job.download_expires_at)||Date.parse(job.download_expires_at)<=Date.now())throw new ApiError('INVALID_RESPONSE');
 const data=(await apiRequest(job.result_ref,{signal,cache:'no-store'})).data;
 if(data?.schema_version!=='trip-export.v1'||!isServerTime(data.generated_at)
  ||!Array.isArray(data.records)||data.records.length>500
  ||!isServerTime(data.range?.from)||!isServerTime(data.range?.to))throw new ApiError('INVALID_RESPONSE');
 if(signal?.aborted)throw new DOMException('Cancelled','AbortError');
 const url=URL.createObjectURL(new Blob([JSON.stringify(data,null,2)],{type:'application/json;charset=utf-8'}));
 const link=document.createElement('a');
 try{link.href=url;link.download='timeisnow-trip-records.json';document.body.appendChild(link);link.click();}
 finally{link.remove();setTimeout(()=>URL.revokeObjectURL(url),1000);}
 return data.records.length;
}
