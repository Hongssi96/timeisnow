import {expect,it} from 'vitest';
import {readSegment} from '../../src/lib/segmentWalking';
const id='00000000-0000-4000-8000-000000000001';
const v={measurement_id:id,leg_id:id,kind:'transfer',label:'같은 구간',status:'valid',version:2,started_at:'2026-10-16T01:00:00Z',finished_at:'2026-10-16T01:00:20Z',observed_seconds:20,sample_count:5,estimate_seconds:20,reasons:[],can_finish:false,apply_to_guidance:true,predicted_seconds:20,predicted_arrival_at:'2026-10-16T01:00:20Z'};
it('accepts a manual estimate and rejects malformed or inconsistent predictions',()=>{
 expect(readSegment(v)).toBe(v);
 for(const change of [{observed_seconds:null},{sample_count:4},{predicted_arrival_at:null},{predicted_seconds:30},{kind:'access'},{label:''}])expect(()=>readSegment({...v,...change})).toThrow();
});
