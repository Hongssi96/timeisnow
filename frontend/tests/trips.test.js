import {afterEach,expect,it,vi} from 'vitest';
import {apiRequest} from '../src/lib/api';
import {activeTrip,confirmDeparture,confirmProgress,cancelTrip,readTrip} from '../src/lib/trips';
vi.mock('../src/lib/api',async()=>({...await vi.importActual('../src/lib/api'),apiRequest:vi.fn()}));
const at='2026-10-14T04:00:00Z';
function trip(){return {trip_id:'t1',guidance_id:'g1',routine_id:'r1',measurement_mode:'assisted',status:'active',version:1,created_at:at,expires_at:'2027-01-12T04:00:00Z',departure_event:null};}
const event=()=>({event_id:'e1',trip_id:'t1',client_event_id:'ce1',leg_id:'l1',type:'departed',source:'manual',occurred_at:at,received_at:at,input_delay_seconds:0,excluded:false,version:1});
const reply=data=>({data,status:200,meta:{server_time:at}});
const detail=()=>reply({trip:trip(),guidance:{candidate:{ordered_legs:[{leg_id:'l1'}]}}});
afterEach(()=>vi.resetAllMocks());
it('recovers only an owned active routine trip',async()=>{apiRequest.mockResolvedValue(reply({items:[trip()]}));expect((await activeTrip('r1')).trip_id).toBe('t1');expect(apiRequest.mock.calls[0][0]).toBe('/api/v1/trips?routine_id=r1&status=active&limit=1');});
it('rejects foreign routine and unsupported movement claims',async()=>{apiRequest.mockResolvedValue(reply({items:[{...trip(),routine_id:'other'}]}));await expect(activeTrip('r1')).rejects.toMatchObject({code:'INVALID_RESPONSE'});expect(()=>readTrip({...trip(),departure_event:{...event(),source:'gps'}})).toThrow();});
it('creates session then reports the saved first leg using manual confirmation',async()=>{
 apiRequest.mockResolvedValueOnce(reply({csrf_token:'csrf'})).mockResolvedValueOnce(reply(trip())).mockResolvedValueOnce(detail()).mockResolvedValueOnce(reply({csrf_token:'csrf2'})).mockResolvedValueOnce(reply(event()));
 const op={routineId:'r1',guidanceId:'g1',eventId:'ce1',occurredAt:at};const result=await confirmDeparture(op);
 expect(result.departure_event.event_id).toBe('e1');expect(op.trip.trip_id).toBe('t1');
 expect(apiRequest.mock.calls[1][1].body).toEqual({guidance_id:'g1',measurement_mode:'assisted'});
 expect(apiRequest.mock.calls[4][1].body).toEqual({client_event_id:'ce1',type:'departed',occurred_at:at,leg_id:'l1',source:'manual'});
});
it('event retry reuses the saved session and the same id and occurrence time',async()=>{
 const op={trip:trip(),routineId:'r1',guidanceId:'g1',eventId:'ce1',occurredAt:at};
 apiRequest.mockResolvedValueOnce(detail()).mockResolvedValueOnce(reply({csrf_token:'csrf'})).mockRejectedValueOnce({code:'TIMEOUT'});
 await expect(confirmDeparture(op)).rejects.toMatchObject({code:'TIMEOUT'});
 apiRequest.mockResolvedValueOnce(detail()).mockResolvedValueOnce(reply({csrf_token:'csrf'})).mockResolvedValueOnce(reply(event()));await confirmDeparture(op);
 expect(apiRequest.mock.calls.filter(([url])=>url==='/api/v1/trips')).toHaveLength(0);
 expect(apiRequest.mock.calls[2][1].body).toEqual(apiRequest.mock.calls[5][1].body);
});
it('existing departed record is recovered without sending a second event',async()=>{
 apiRequest.mockResolvedValue(reply({trip:{...trip(),departure_event:event()},guidance:{candidate:{ordered_legs:[{leg_id:'l1'}]}}}));
 expect((await confirmDeparture({trip:trip()})).departure_event.event_id).toBe('e1');expect(apiRequest).toHaveBeenCalledTimes(1);
});
it('cancel uses server trip version and checks the saved cancelled state',async()=>{
 apiRequest.mockResolvedValueOnce(reply({csrf_token:'csrf'})).mockResolvedValueOnce(reply({...trip(),status:'cancelled',version:2}));
 await cancelTrip(trip());expect(apiRequest.mock.calls[1][1].body).toEqual({outcome:'cancelled',expected_version:1});
});
it('progress resolves saved approach and first vehicle legs and preserves departure',async()=>{
 const departed={...trip(),departure_event:event()};
 for(const [type,leg_id,field] of [['approach_arrived','l1','approach_event'],['boarded','bus1','boarding_event']]){
  const progress={...event(),type,leg_id};
  apiRequest.mockResolvedValueOnce(reply({trip:departed,guidance:{candidate:{ordered_legs:[{leg_id:'l1',type:'WALKING'},{leg_id:'bus1',type:'BUS'}]}}})).mockResolvedValueOnce(reply({csrf_token:'csrf'})).mockResolvedValueOnce(reply(progress));
  const result=await confirmProgress({trip:departed,type,eventId:'ce1',occurredAt:at});
  expect(result[field]).toEqual(progress);expect(result.departure_event).toEqual(event());
  expect(apiRequest.mock.calls.at(-1)[1].body).toMatchObject({type,leg_id,source:'manual'});
 }
});
it('progress retry recovers a saved event without a second POST',async()=>{
 const boarding={...event(),type:'boarded',leg_id:'bus1'};
 apiRequest.mockResolvedValue(reply({trip:{...trip(),departure_event:event(),boarding_event:boarding}}));
 expect((await confirmProgress({trip:trip(),type:'boarded'})).boarding_event).toEqual(boarding);expect(apiRequest).toHaveBeenCalledTimes(1);
});
it('rejects incorrect event types in trip summary fields',()=>{
 expect(()=>readTrip({...trip(),departure_event:{...event(),type:'boarded'}})).toThrow();
 expect(()=>readTrip({...trip(),boarding_event:event()})).toThrow();
});
it('recovers boarding from another tab while retrying an approach report',async()=>{
 const saved={...trip(),departure_event:event(),boarding_event:{...event(),type:'boarded',leg_id:'bus1'}};
 apiRequest.mockResolvedValue(reply({trip:saved}));
 expect(await confirmProgress({trip:trip(),type:'approach_arrived'})).toEqual(saved);expect(apiRequest).toHaveBeenCalledTimes(1);
});
const progress=(stage,actions,anchor='a1')=>({stage,actions,anchor_event_id:anchor,current_leg_id:'bus2',next_leg_id:stage==='onboard'?null:'bus2',boarding_stop:'환승 승차',alighting_stop:'다음 하차',vehicle_name:'20번'});
it('second boarding uses progress action rather than replaying the first boarding summary',async()=>{
 const current={...trip(),departure_event:event(),boarding_event:{...event(),type:'boarded'},progress:progress('transfer',{boarded:'bus2'})};
 const boarded={...event(),type:'boarded',leg_id:'bus2'};
 const saved={...current,progress:progress('onboard',{alighted:'bus2'},'e2')};
 apiRequest.mockResolvedValueOnce(reply({trip:current})).mockResolvedValueOnce(reply({csrf_token:'csrf'})).mockResolvedValueOnce(reply(boarded)).mockResolvedValueOnce(reply({trip:saved}));
 expect(await confirmProgress({trip:current,type:'boarded',eventId:'ce1',occurredAt:at})).toEqual(saved);
 expect(apiRequest.mock.calls[2][1].body.leg_id).toBe('bus2');
});
it('changed progress anchor recovers current stage without sending a stale action',async()=>{
 const current={...trip(),departure_event:event(),progress:progress('onboard',{alighted:'bus2'})};
 const saved={...current,progress:progress('transfer',{boarded:'bus3'},'new')};
 apiRequest.mockResolvedValue(reply({trip:saved}));
 expect(await confirmProgress({trip:current,type:'alighted'})).toEqual(saved);expect(apiRequest).toHaveBeenCalledTimes(1);
});
function ended(status='completed'){
 return {...trip(),status,version:2,departure_event:event(),terminal_event:{...event(),type:status==='completed'?'arrived':'missed'},progress:progress(status,{},'end')};
}
it('recovers a persisted terminal event after a lost POST response without writing again',async()=>{
 apiRequest.mockResolvedValue(reply({trip:ended()}));
 expect((await confirmProgress({trip:{...trip(),departure_event:event()},type:'arrived'})).status).toBe('completed');
 expect(apiRequest).toHaveBeenCalledTimes(1);
});
it('routine recovery can include completed and missed trips but rejects invalid terminal claims',async()=>{
 apiRequest.mockResolvedValue(reply({items:[ended('missed')]}));
 expect((await activeTrip('r1',undefined,true)).status).toBe('missed');
 expect(apiRequest.mock.calls[0][0]).toBe('/api/v1/trips?routine_id=r1&limit=1');
 expect(()=>readTrip({...ended(),terminal_event:null})).toThrow();
 expect(()=>readTrip({...ended(),terminal_event:{...event(),type:'missed'}})).toThrow();
});
