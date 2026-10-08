import { afterEach, expect, it, vi } from 'vitest';
import fixtures from '../fixtures/journeys.json';
import { apiRequest } from '../../src/lib/api';
import { validCandidate, readJourney, pollJourney, sortCandidates, missingWalk, formatJourneyTime } from '../../src/lib/journeys';
vi.mock('../../src/lib/api',async original=>({...await original(),apiRequest:vi.fn()}));
afterEach(()=>{vi.restoreAllMocks();vi.resetAllMocks();vi.useRealTimers();});
const accepted={search_id:'search_test',job_id:'job_test'};
const response=(status='succeeded',extra={})=>({status:200,meta:{server_time:new Date().toISOString()},data:{...accepted,status,candidates:status==='succeeded'?[structuredClone(fixtures.mixed)]:[],unavailable_reasons:[],error:null,expires_at:new Date(Date.now()+290000).toISOString()},...extra});

it('accepts common model fixtures but rejects false references and unsupported versions',()=>{
  expect(validCandidate(fixtures.direct)).toBe(true);expect(validCandidate(fixtures.mixed)).toBe(true);
  for(const mutate of [c=>c.model_version='unknown',c=>c.connections[0].from_leg_id='wrong',c=>c.ordered_legs[0]=null,c=>c.connections[0]=null,c=>c.ordered_legs[0].walking_role='egress',c=>c.total_seconds=true,c=>c.timing_breakdown.unallocated_seconds=999]){
    const value=structuredClone(fixtures.mixed);mutate(value);expect(validCandidate(value)).toBe(false);
  }
});
it('checks ownership IDs, job status, and the five-minute result deadline',()=>{
  expect(readJourney(response(),accepted).candidates).toHaveLength(1);
  const wrong=response();wrong.data.search_id='foreign';expect(()=>readJourney(wrong,accepted)).toThrow();
  const old=response();old.data.expires_at=new Date(Date.now()-1000).toISOString();expect(()=>readJourney(old,accepted)).toThrowError(expect.objectContaining({code:'SEARCH_EXPIRED'}));
  const malformed=response('queued');malformed.data.candidates=[fixtures.direct];expect(()=>readJourney(malformed,accepted)).toThrow();
});
it('sorts the retrieved set without changing it or treating missing duration as zero',()=>{
  const data=[{candidate_id:'a',total_seconds:500,transfer_count:2,walking_seconds:100},{candidate_id:'b',total_seconds:700,transfer_count:0,walking_seconds:50}];
  expect(sortCandidates(data,'balanced')[0].candidate_id).toBe('a');expect(sortCandidates(data,'fewer_transfers')[0].candidate_id).toBe('b');
  expect(sortCandidates(data,'less_walking')[0].candidate_id).toBe('b');expect(data[0].candidate_id).toBe('a');
  expect(missingWalk({...fixtures.direct,missing_segments:['ACCESS_WALK_MISSING']})).toBe(true);
  expect(formatJourneyTime(null)).toBe('확인 필요');expect(formatJourneyTime(0)).toBe('0분');expect(formatJourneyTime(10)).toBe('1분 미만');
});
it('polls after 2/5/10 seconds, honors Retry-After, and never sends POST',async()=>{
  vi.useFakeTimers();apiRequest.mockResolvedValueOnce(response('running')).mockResolvedValueOnce(response('running',{retryAfterMs:7000})).mockResolvedValueOnce(response());
  const controller=new AbortController();const result=pollJourney(accepted,{signal:controller.signal,deadline:Date.now()+300000});
  await vi.advanceTimersByTimeAsync(1999);expect(apiRequest).not.toHaveBeenCalled();
  await vi.advanceTimersByTimeAsync(1);expect(apiRequest).toHaveBeenCalledTimes(1);
  await vi.advanceTimersByTimeAsync(4999);expect(apiRequest).toHaveBeenCalledTimes(1);
  await vi.advanceTimersByTimeAsync(1);expect(apiRequest).toHaveBeenCalledTimes(2);
  await vi.advanceTimersByTimeAsync(6999);expect(apiRequest).toHaveBeenCalledTimes(2);
  await vi.advanceTimersByTimeAsync(1);expect((await result).status).toBe('succeeded');
  expect(apiRequest.mock.calls.every(([path,options])=>path.includes('/journey-searches/search_test')&&!options.method)).toBe(true);
});
it('pauses in a hidden page and cancels a timer on unmount',async()=>{
  vi.useFakeTimers();const visibility=vi.spyOn(document,'visibilityState','get').mockReturnValue('hidden');
  apiRequest.mockResolvedValue(response());const controller=new AbortController();
  const result=pollJourney(accepted,{signal:controller.signal,deadline:Date.now()+300000});
  await vi.advanceTimersByTimeAsync(5000);expect(apiRequest).not.toHaveBeenCalled();
  visibility.mockReturnValue('visible');document.dispatchEvent(new Event('visibilitychange'));
  await vi.advanceTimersByTimeAsync(2000);await result;expect(apiRequest).toHaveBeenCalledOnce();
  const next=new AbortController();const cancelled=pollJourney(accepted,{signal:next.signal,deadline:Date.now()+300000}).catch(error=>error);
  next.abort();await vi.advanceTimersByTimeAsync(10000);expect((await cancelled).name).toBe('AbortError');expect(apiRequest).toHaveBeenCalledOnce();
});
it('aborts in-flight GET on hiding and resumes with the same search ID',async()=>{
  vi.useFakeTimers();const visibility=vi.spyOn(document,'visibilityState','get').mockReturnValue('visible');
  apiRequest.mockImplementationOnce((_,{signal})=>new Promise((_,reject)=>signal.addEventListener('abort',()=>reject(new DOMException('cancel','AbortError'))))).mockResolvedValueOnce(response());
  const controller=new AbortController();const result=pollJourney(accepted,{signal:controller.signal,deadline:Date.now()+300000});
  await vi.advanceTimersByTimeAsync(2000);visibility.mockReturnValue('hidden');document.dispatchEvent(new Event('visibilitychange'));
  await vi.advanceTimersByTimeAsync(5000);expect(apiRequest.mock.calls[0][1].signal.aborted).toBe(true);expect(apiRequest).toHaveBeenCalledOnce();
  visibility.mockReturnValue('visible');document.dispatchEvent(new Event('visibilitychange'));await vi.advanceTimersByTimeAsync(0);
  expect((await result).status).toBe('succeeded');expect(apiRequest).toHaveBeenCalledTimes(2);
});
it('does not publish a successful response that arrives beyond the input deadline',async()=>{
  vi.useFakeTimers();let resolve;apiRequest.mockImplementationOnce(()=>new Promise(done=>{resolve=done;}));
  const progress=vi.fn();const controller=new AbortController();
  const result=pollJourney(accepted,{signal:controller.signal,deadline:Date.now()+1000,onProgress:progress,immediate:true}).catch(error=>error);
  await vi.advanceTimersByTimeAsync(0);await vi.advanceTimersByTimeAsync(2000);resolve(response());
  expect((await result).code).toBe('SEARCH_EXPIRED');expect(progress).not.toHaveBeenCalled();
});
