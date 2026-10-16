import {afterEach,expect,it,vi} from 'vitest';
import {apiRequest} from '../../src/lib/api';
import {exportRecords} from '../../src/lib/tripExports';
vi.mock('../../src/lib/api',async original=>({...await original(),apiRequest:vi.fn()}));
const id='00000000-0000-4000-8000-000000000001';
const job={job_id:id,status:'succeeded',result_ref:`/api/v1/trip-exports/${id}/download`,download_expires_at:new Date(Date.now()+600000).toISOString()};
const file={schema_version:'trip-export.v1',generated_at:new Date().toISOString(),range:{from:new Date(Date.now()-86400000).toISOString(),to:new Date().toISOString()},records:[]};
afterEach(()=>{vi.restoreAllMocks();vi.resetAllMocks();vi.unstubAllGlobals();});
it('CSRF로 생성하고 같은 서버 경로만 다운로드하며 임시 URL을 회수한다',async()=>{
 vi.useFakeTimers();const create=vi.fn(()=> 'blob:owned'),revoke=vi.fn();
 vi.stubGlobal('URL',Object.assign(URL,{createObjectURL:create,revokeObjectURL:revoke}));
 const click=vi.spyOn(HTMLAnchorElement.prototype,'click').mockImplementation(()=>{});
 apiRequest.mockResolvedValueOnce({data:{csrf_token:'token'}}).mockResolvedValueOnce({data:job}).mockResolvedValueOnce({data:file});
 expect(await exportRecords(90)).toBe(0);
 const body=apiRequest.mock.calls[1][1].body;expect(Date.parse(body.to)-Date.parse(body.from)).toBe(90*86400000);
 expect(apiRequest.mock.calls[1][1].headers['X-CSRF-Token']).toBe('token');expect(click).toHaveBeenCalledOnce();
 await vi.runAllTimersAsync();expect(revoke).toHaveBeenCalledWith('blob:owned');expect(document.querySelector('a[download]')).toBeNull();vi.useRealTimers();
});
it('외부 링크와 만료된 링크는 열지 않는다',async()=>{
 for(const bad of [{...job,result_ref:'https://foreign.invalid/private'},{...job,download_expires_at:'2000-01-01T00:00:00Z'}]){
  apiRequest.mockReset();apiRequest.mockResolvedValueOnce({data:{csrf_token:'token'}}).mockResolvedValueOnce({data:bad});
  await expect(exportRecords(7)).rejects.toMatchObject({code:'INVALID_RESPONSE'});expect(apiRequest).toHaveBeenCalledTimes(2);
 }
});
it('이탈 취소 또는 유효하지 않은 파일은 성공 처리하지 않는다',async()=>{
 apiRequest.mockResolvedValueOnce({data:{csrf_token:'token'}}).mockResolvedValueOnce({data:job}).mockResolvedValueOnce({data:{...file,records:null}});
 await expect(exportRecords(30)).rejects.toMatchObject({code:'INVALID_RESPONSE'});
 await expect(exportRecords(1)).rejects.toMatchObject({code:'VALIDATION_ERROR'});
});
