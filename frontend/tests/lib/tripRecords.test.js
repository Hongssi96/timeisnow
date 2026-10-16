import {afterEach,expect,it,vi} from 'vitest';
import {records,mutateRecord} from '../../src/lib/tripRecords';
import {readEvent} from '../../src/lib/trips';
import {apiRequest} from '../../src/lib/api';
vi.mock('../../src/lib/api',async original=>({...await original(),apiRequest:vi.fn()}));
const id='00000000-0000-4000-8000-000000000001';
afterEach(()=>vi.resetAllMocks());
it('버전2의 학습 제외 이벤트를 수신하고 음수 버전은 거부한다',()=>{
 const event={event_id:id,client_event_id:id,leg_id:id,trip_id:id,type:'departed',source:'manual',occurred_at:'2026-10-16T00:00:00Z',received_at:'2026-10-16T00:00:01Z',input_delay_seconds:1,excluded:true,version:2};
 expect(readEvent(event,id)).toEqual(event);expect(()=>readEvent({...event,version:0},id)).toThrow();
});
it('유효하지 않은 페이지 커서와 대상은 API 호출 전에 차단한다',async()=>{
 await expect(records('../bad')).rejects.toThrow();await expect(mutateRecord({kind:'delete',tripId:'../bad',body:{}})).rejects.toThrow();expect(apiRequest).not.toHaveBeenCalled();
});
it('삭제 응답에 대상이나 학습 상태가 없으면 성공 처리하지 않는다',async()=>{
 apiRequest.mockResolvedValueOnce({data:{csrf_token:'token'}}).mockResolvedValueOnce({data:{trip_id:id,deleted:true}});
 await expect(mutateRecord({kind:'delete',tripId:id,body:{expected_version:1}})).rejects.toThrow();expect(apiRequest.mock.calls[1][1].method).toBe('DELETE');
});
