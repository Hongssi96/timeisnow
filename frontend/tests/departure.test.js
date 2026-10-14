import { afterEach,expect,it,vi } from 'vitest';
import { getFirstDeparture } from '../src/lib/departure';
function data(){const arrival={model_version:'arrival.evidence.v2',search_id:'s',candidate_id:'c',first_leg_id:'leg',status:'estimated',source_status:'unknown',timing_basis:'receipt_estimate',received_at:'2026-10-13T08:00:00Z',generated_at:null,expires_at:'2026-10-13T08:02:00Z',valid_for_guidance:true,candidates:[{candidate_id:'bus',provider_prediction_seconds:780,predicted_arrival_at:'2026-10-13T08:13:00Z'}]};return {model_version:'first.departure.v1',search_id:'s',candidate_id:'c',first_leg_id:'leg',status:'ready',valid_for_guidance:true,departure_basis:'recommended',calculated_at:'2026-10-13T08:00:00Z',valid_until:arrival.expires_at,profile_version:1,buffer_seconds:300,slack_status:'meets_buffer',slack_seconds:300,approach_basis:'provider_personalized',approach_seconds:300,provider_approach_seconds:300,applied_duration_factor:1,timing_basis:'receipt_estimate',recommended_departure_at:'2026-10-13T08:03:00Z',selected_departure_at:'2026-10-13T08:03:00Z',vehicle_arrival_at:'2026-10-13T08:13:00Z',arrival_candidate_id:'bus',arrival_evidence:arrival};}
function mock(d){vi.stubGlobal('fetch',vi.fn().mockResolvedValue(new Response(JSON.stringify({data:d,meta:{request_id:'synthetic',server_time:'2026-10-13T08:00:00Z'}}),{status:200})));}
afterEach(()=>vi.unstubAllGlobals());
it('uses one owned departure GET for both arrival and calculation',async()=>{mock(data());const result=await getFirstDeparture('s','c');expect(fetch).toHaveBeenCalledTimes(1);expect(fetch.mock.calls[0][0]).toBe('/api/v1/journey-searches/s/candidates/c/first-departure?include_connections=true');expect(result.data.approach_seconds).toBe(300);});
it.each(['wrong_formula','wrong_identity','expiry_extension','factor','unlabelled'])('rejects %s',async kind=>{const d=data();if(kind==='wrong_formula')d.approach_seconds=100;if(kind==='wrong_identity')d.arrival_candidate_id='other';if(kind==='expiry_extension')d.valid_until='2026-10-13T08:03:00Z';if(kind==='factor')d.applied_duration_factor=3;if(kind==='unlabelled')d.approach_basis=null;mock(d);await expect(getFirstDeparture('s','c')).rejects.toMatchObject({code:'INVALID_RESPONSE'});});

it('rejects a transfer claiming success before minimum boarding time',async()=>{
  const d=data();d.connection_status='estimated_feasible';d.transfers=[{connection_id:'link',from_leg_id:'one',to_leg_id:'two',feasibility:'estimated_feasible',time_source:'receipt_estimate',transfer_buffer_seconds:120,transfer_walk_seconds:100,estimated_alighting_at:'2026-10-13T08:20:00Z',minimum_boarding_at:'2026-10-13T08:24:00Z',next_boarding_at:'2026-10-13T08:23:00Z'}];mock(d);
  await expect(getFirstDeparture('s','c')).rejects.toMatchObject({code:'INVALID_RESPONSE'});
});

it('accepts a separate boarding walk source with original receipt and bounded expiry',async()=>{
 const d=data();d.provider_approach_source='boarding_walk';d.approach_fetched_at=d.calculated_at;d.approach_valid_until='2026-10-13T08:05:00Z';mock(d);expect((await getFirstDeparture('s','c')).data.provider_approach_source).toBe('boarding_walk');
});
it('rejects missing, future or expired separate walking evidence',async()=>{
 for(const changes of [{approach_fetched_at:null},{approach_fetched_at:'2026-10-13T08:01:00Z'},{approach_valid_until:'2026-10-13T08:01:00Z'},{provider_approach_source:'invented'}]){
  const d={...data(),provider_approach_source:'boarding_walk',approach_fetched_at:'2026-10-13T08:00:00Z',approach_valid_until:'2026-10-13T08:05:00Z',...changes};mock(d);await expect(getFirstDeparture('s','c')).rejects.toMatchObject({code:'INVALID_RESPONSE'});
 }
});

function goalData(){const d=data();d.connection_status='estimated_feasible';d.transfers=[];d.estimated_final_alighting_at='2026-10-13T08:20:00Z';d.target_evaluation={model_version:'target.arrival.v1',scope:'selected_routine_candidate',status:'estimated_meets',evaluated_at:d.calculated_at,target_arrival_at:'2026-10-13T08:25:00Z',estimated_destination_arrival_at:'2026-10-13T08:22:00Z',margin_seconds:180,egress_seconds:120,timing_basis:'provider_timeline',reasons:[]};return d;}
it('accepts a target evaluation anchored to final alighting and egress',async()=>{mock(goalData());expect((await getFirstDeparture('s','c')).data.target_evaluation.margin_seconds).toBe(180);});
it('rejects goal formula, classification and missing final leg contradictions',async()=>{for(const change of [{margin_seconds:300},{status:'estimated_late'},{egress_seconds:0},{estimated_destination_arrival_at:'2026-10-13T08:21:00Z'}]){const d=goalData();d.target_evaluation={...d.target_evaluation,...change};mock(d);await expect(getFirstDeparture('s','c')).rejects.toMatchObject({code:'INVALID_RESPONSE'});}});
it('unknown target states cannot carry fabricated arrival or margin numbers',async()=>{const d=goalData();d.target_evaluation.status='unknown';mock(d);await expect(getFirstDeparture('s','c')).rejects.toMatchObject({code:'INVALID_RESPONSE'});});
