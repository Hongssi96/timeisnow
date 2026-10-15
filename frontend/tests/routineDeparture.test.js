import {it,expect,vi,beforeEach} from 'vitest';
import {apiRequest} from '../src/lib/api';
import {pollJourney} from '../src/lib/journeys';
import {readFirstDeparture} from '../src/lib/departure';
import {getRoutineDeparture,refreshRoutine,estimateRoutineWalk} from '../src/lib/routineDeparture';
vi.mock('../src/lib/api',async()=>({...await vi.importActual('../src/lib/api'),apiRequest:vi.fn()}));
vi.mock('../src/lib/journeys',async()=>({...await vi.importActual('../src/lib/journeys'),pollJourney:vi.fn()}));
vi.mock('../src/lib/departure',async()=>({...await vi.importActual('../src/lib/departure'),readFirstDeparture:vi.fn(r=>r)}));
const routine={routine_id:'r1',version:3};
const reply=()=>({status:200,meta:{server_time:'2026-10-14T01:00:00Z'},data:{model_version:'routine.departure.v1',routine_id:'r1',routine_version:3,search_id:'s1',status:'route_changed',candidate_id:null,departure:null,expires_at:'2026-10-14T01:05:00Z'}});
beforeEach(()=>{apiRequest.mockReset();pollJourney.mockReset();readFirstDeparture.mockClear();});
it('uses server routine/version only, csrf and idempotency then polls before departure',async()=>{apiRequest.mockResolvedValueOnce({data:{csrf_token:'csrf'}}).mockResolvedValueOnce({status:202,data:{routine_id:'r1',routine_version:3,search_id:'s1',job_id:'j1',status:'queued'}}).mockResolvedValueOnce(reply());pollJourney.mockResolvedValue({status:'succeeded',search_id:'s1',deadline:Date.now()+300000});await refreshRoutine(routine,new AbortController().signal);const call=apiRequest.mock.calls[1];expect(call[1].body).toEqual({expected_version:3});expect(call[1].headers['X-CSRF-Token']).toBe('csrf');expect(call[1].headers['Idempotency-Key']).toBeTruthy();expect(pollJourney).toHaveBeenCalledTimes(1);});
it('rejects mismatched routine, version, missing match and fake expiry extension',async()=>{for(const change of [{routine_id:'other'},{routine_version:2},{expires_at:'2026-10-14T01:10:00Z'},{status:'route_changed',candidate_id:'c1'}]){apiRequest.mockResolvedValue({...reply(),data:{...reply().data,...change}});await expect(getRoutineDeparture(routine,'s1')).rejects.toMatchObject({code:'INVALID_RESPONSE'});}});
it('validates nested departure using existing strict first departure contract',async()=>{const r=reply();r.data={...r.data,status:'ready',candidate_id:'c1',departure:{valid_until:'2026-10-14T01:02:00Z'}};apiRequest.mockResolvedValue(r);await getRoutineDeparture(routine,'s1');expect(readFirstDeparture).toHaveBeenCalledWith({...r,data:r.data.departure},'s1','c1');});
it('failed worker never calls departure endpoint',async()=>{apiRequest.mockResolvedValueOnce({data:{csrf_token:'csrf'}}).mockResolvedValueOnce({status:202,data:{routine_id:'r1',routine_version:3,search_id:'s1',job_id:'j1',status:'queued'}});pollJourney.mockResolvedValue({status:'failed',error:{code:'JOB_INTERRUPTED'}});await expect(refreshRoutine(routine,new AbortController().signal)).rejects.toMatchObject({code:'JOB_INTERRUPTED'});expect(apiRequest).toHaveBeenCalledTimes(2);});

it('explicit AI request sends only routine version/request ID with csrf and bounded timeout',async()=>{
 apiRequest.mockResolvedValueOnce({data:{csrf_token:'csrf'}}).mockResolvedValueOnce({status:200,data:{model_version:'routine.walking.v1',routine_id:'r1',search_id:'s1',status:'needs_data',estimate:null,reasons:['MAPPING_UNAVAILABLE']}});
 await estimateRoutineWalk(routine,'s1','id',new AbortController().signal);
 expect(apiRequest.mock.calls[1][1]).toMatchObject({method:'POST',timeoutMs:80000,body:{expected_version:3,client_request_id:'id'},headers:{'X-CSRF-Token':'csrf'}});
});
