import {expect,it,vi,afterEach} from 'vitest';
import {readRemaining,getRemaining} from '../src/lib/remaining';
const trip={trip_id:'t',version:1};
function response(){
 return {status:200,meta:{request_id:'synthetic',server_time:'2026-10-14T08:00:00Z'},data:{model_version:'trip.remaining.v1',trip_id:'t',trip_version:1,search_id:'s',candidate_id:'c',
  status:'ready',calculated_at:'2026-10-14T08:00:00Z',valid_until:'2026-10-14T08:02:00Z',valid_for_guidance:true,remaining_approach_seconds:120,buffer_seconds:300,
  vehicle_arrival_at:'2026-10-14T08:10:00Z',slack_seconds:480,slack_status:'meets_buffer',timing_basis:'receipt_estimate',connection_status:'not_checked',transfers:[],target_evaluation:null,reasons:['CONFIRMED_POINT_ESTIMATE']}};
}
afterEach(()=>vi.unstubAllGlobals());
it('accepts only the current point remaining formula with bounded expiry',()=>{expect(readRemaining(response(),trip,'s').data.remaining_approach_seconds).toBe(120);});
it.each(['trip','formula','expiry','blocked','unknown','target'])('rejects invalid %s rather than exposing invented numbers',kind=>{
 const r=response();if(kind==='trip')r.data.trip_id='other';if(kind==='formula')r.data.slack_seconds=999;
 if(kind==='expiry')r.data.valid_until='2026-10-14T08:02:01Z';if(kind==='blocked')r.data.valid_for_guidance=false;
 if(kind==='unknown')r.data.timing_basis='none';if(kind==='target')r.data.target_evaluation={model_version:'target.arrival.v1',scope:'selected_routine_candidate',evaluated_at:r.data.calculated_at,status:'estimated_meets',target_arrival_at:r.data.calculated_at,estimated_destination_arrival_at:r.data.calculated_at,margin_seconds:100};
 expect(()=>readRemaining(r,trip,'s')).toThrow();
});
it('GET stays bound to trip version and never sends client walking seconds',async()=>{
 const r=response();vi.stubGlobal('fetch',vi.fn().mockResolvedValue(new Response(JSON.stringify({data:r.data,meta:r.meta}),{status:200})));
 expect((await getRemaining(trip,'s')).data.slack_seconds).toBe(480);expect(fetch.mock.calls[0][0]).toBe('/api/v1/trips/t/remaining-searches/s/guidance?expected_version=1');
});
