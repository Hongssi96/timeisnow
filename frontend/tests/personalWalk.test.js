import {it,expect} from 'vitest';
import {validPersonalWalk} from '../src/lib/departure';
const at='2026-10-15T07:00:00Z';
const p={estimate_id:'e1',revision_id:'r1',base_seconds:436,applied_duration_factor:1.1,estimated_seconds:480,profile_version:2,source:'profile_recalculation',reused:false,expires_at:'2026-10-15T07:05:00Z'};
it('accepts one precise coefficient application with ceiling',()=>{expect(validPersonalWalk(p,at)).toBe(true);});
it('rejects forged math, unsupported source, zero profile, missing identity, and expiry',()=>{
 for(const change of [{estimated_seconds:479},{applied_duration_factor:3},{source:'unknown'},{profile_version:0},{estimate_id:''},{reused:'false'},{expires_at:at}])expect(validPersonalWalk({...p,...change},at)).toBe(false);
});
