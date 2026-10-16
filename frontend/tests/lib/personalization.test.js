import {afterEach,expect,it,vi} from 'vitest';
import {readPersonalization,learnWalking,changePersonalization} from '../../src/lib/personalization';
import {apiRequest} from '../../src/lib/api';
vi.mock('../../src/lib/api',async original=>({...await original(),apiRequest:vi.fn()}));
const state={status:'learning',profile_version:1,factors:[{type:'provider_mapped_access',value:1}],sample_counts:{valid:0,excluded:0},quality:{sample_count:0,baseline_mae_seconds:null,personalized_mae_seconds:null},can_restore:false,policy_version:'manual-walking.v1'};
afterEach(()=>vi.resetAllMocks());
it('잘못된 서버 계수와 집계는 차단한다',()=>{
 expect(readPersonalization(state)).toEqual(state);
 for(const changed of [{factors:[{type:'provider_mapped_access',value:3}]},{sample_counts:{valid:-1,excluded:0}},{profile_version:0},{quality:null}])expect(()=>readPersonalization({...state,...changed})).toThrow();
});
it('잘못된 이동 ID를 공급자 호출 전에 차단한다',async()=>{await expect(learnWalking('../private',{})).rejects.toThrow();expect(apiRequest).not.toHaveBeenCalled();});
it('CSRF 토큰과 멱등 요청을 앱 서버로 보낸다',async()=>{
 apiRequest.mockResolvedValueOnce({data:{csrf_token:'token'}}).mockResolvedValueOnce({data:state});const body={expected_version:1,client_request_id:'req'};
 expect(await changePersonalization('reset',body)).toEqual(state);expect(apiRequest.mock.calls[1][1]).toMatchObject({method:'POST',body,headers:{'X-CSRF-Token':'token'}});
});
