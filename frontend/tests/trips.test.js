import {afterEach,expect,it,vi} from 'vitest';
import {apiRequest} from '../src/lib/api';
import {activeTrip,confirmDeparture,cancelTrip,readTrip} from '../src/lib/trips';
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
