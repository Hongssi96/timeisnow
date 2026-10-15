import {it,expect,vi,afterEach} from 'vitest';
import {readOnboard,confirmOnboard} from '../src/lib/onboard';
const trip={trip_id:'t',version:1,progress:{stage:'onboard',current_leg_id:'bus',anchor_event_id:'event'}};
export const response=()=>({status:200,meta:{server_time:'2026-10-15T07:00:01Z'},data:{model_version:'trip.onboard.v1',trip_id:'t',trip_version:1,current_leg_id:'bus',anchor_event_id:'event',status:'estimated',source:'manual_vehicle_match',timing_basis:'receipt_estimate',source_status:'unknown',generated_at:null,received_at:'2026-10-15T07:00:00Z',expires_at:'2026-10-15T07:02:00Z',estimated_alighting_at:'2026-10-15T07:10:00Z',remaining_seconds:599,reasons:['SAME_VEHICLE_PROVIDER_ESTIMATE']}});
afterEach(()=>vi.unstubAllGlobals());
it('accepts matched current vehicle with original receipt expiry',()=>{expect(readOnboard(response(),trip).data.remaining_seconds).toBe(599);});
it.each([{anchor_event_id:'old'},{current_leg_id:'other'},{remaining_seconds:999},{expires_at:'2026-10-15T07:04:00Z'},{source_status:'fresh'},{status:'needs_data'},{received_at:'2026-10-15T07:00:02Z'}])('rejects mismatched or manufactured evidence %j',change=>{const r=response();r.data={...r.data,...change};expect(()=>readOnboard(r,trip)).toThrow();});
it('sends only typed vehicle suffix/current anchor with csrf, never coordinates',async()=>{
 const meta={request_id:'req_test',server_time:'2026-10-15T07:00:01Z'};
 const fetch=vi.fn().mockResolvedValueOnce({ok:true,status:200,json:async()=>({data:{csrf_token:'csrf'},meta})}).mockResolvedValueOnce({ok:true,status:200,json:async()=>({...response(),meta})});vi.stubGlobal('fetch',fetch);
 await confirmOnboard(trip,'1234');const options=fetch.mock.calls[1][1];
 expect(JSON.parse(options.body)).toEqual({expected_version:1,anchor_event_id:'event',leg_id:'bus',plate_suffix:'1234'});expect(options.headers.get('X-CSRF-Token')).toBe('csrf');
});
