import { afterEach, expect, it, vi } from 'vitest';
import { getFirstArrivals } from '../src/lib/arrivals';
const search='s',candidate='c';
function data() {return {model_version:'arrival.evidence.v2',search_id:search,candidate_id:candidate,status:'estimated',source_status:'unknown',timing_basis:'receipt_estimate',received_at:'2026-10-13T08:00:00Z',generated_at:null,expires_at:'2026-10-13T08:02:00Z',valid_for_guidance:true,candidates:[{candidate_id:'vehicle',provider_prediction_seconds:300,predicted_arrival_at:'2026-10-13T08:05:00Z'}]};}
function mock(value) {vi.stubGlobal('fetch',vi.fn().mockResolvedValue(new Response(JSON.stringify({data:value,meta:{request_id:'synthetic',server_time:'2026-10-13T08:00:00Z'}}),{status:200})));}
afterEach(()=>vi.unstubAllGlobals());
it('calls the owned API route and accepts explicitly labelled estimates',async()=>{
  mock(data());const result=await getFirstArrivals(search,candidate);
  expect(fetch.mock.calls[0][0]).toBe('/api/v1/journey-searches/s/candidates/c/first-arrivals');expect(result.data.timing_basis).toBe('receipt_estimate');
});
it.each(['version','unlabelled','timestamp','identity'])('rejects invalid %s evidence',async kind=>{
  const d=data();if(kind==='version')d.model_version='arrival.evidence.v1';if(kind==='unlabelled')d.timing_basis='none';if(kind==='timestamp')d.generated_at='bad';if(kind==='identity')d.candidate_id='other';mock(d);
  await expect(getFirstArrivals(search,candidate)).rejects.toMatchObject({code:'INVALID_RESPONSE'});
});
