import {beforeEach,it,expect,vi} from 'vitest';
import {apiRequest} from '../../src/lib/api';
import {getProfile,readProfile,saveProfile} from '../../src/lib/profile';
vi.mock('../../src/lib/api',async original=>({...await original(),apiRequest:vi.fn()}));
const profile={version:1,timezone:'Asia/Seoul',walking_preference:'normal',route_preference:'balanced',first_boarding_buffer_seconds:300,transfer_buffer_seconds:120,walking_duration_factor:1};
beforeEach(()=>apiRequest.mockReset());
it('rejects malformed profile values instead of displaying invented defaults',()=>{
 for(const value of [{...profile,version:0},{...profile,transfer_buffer_seconds:1801},{...profile,first_boarding_buffer_seconds:true},{...profile,walking_preference:'running'}])expect(()=>readProfile(value)).toThrow();
});
it('reads the authenticated owner and validates the server profile',async()=>{
 apiRequest.mockResolvedValue({data:{user_id:'member',profile}});expect(await getProfile()).toEqual({owner:'member',profile});
});
it('obtains CSRF then checks owner before writing only the expected version and settings',async()=>{
 apiRequest.mockResolvedValueOnce({data:{csrf_token:'csrf'}}).mockResolvedValueOnce({data:{user_id:'member',profile}}).mockResolvedValueOnce({data:{profile:{...profile,version:2,transfer_buffer_seconds:30},profile_version:2}});
 const saved=await saveProfile('member',1,{transfer_buffer_seconds:30});expect(saved.transfer_buffer_seconds).toBe(30);expect(apiRequest.mock.calls[2]).toEqual(['/api/v1/me/profile',expect.objectContaining({method:'PATCH',body:{expected_version:1,transfer_buffer_seconds:30},headers:{'X-CSRF-Token':'csrf'}})]);
});
it('never applies an old account draft after a cross-tab sign-in',async()=>{
 apiRequest.mockResolvedValueOnce({data:{csrf_token:'csrf'}}).mockResolvedValueOnce({data:{user_id:'other',profile}});
 await expect(saveProfile('member',1,{transfer_buffer_seconds:30})).rejects.toMatchObject({code:'SESSION_CHANGED'});expect(apiRequest).toHaveBeenCalledTimes(2);
});
