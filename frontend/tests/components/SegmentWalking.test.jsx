import React from 'react';
import {act,render,screen,fireEvent,cleanup} from '@testing-library/react';
import {afterEach,beforeEach,expect,it,vi} from 'vitest';
import SegmentWalking from '../../src/components/SegmentWalking';
import {segments,mutateSegment} from '../../src/lib/segmentWalking';
vi.mock('../../src/lib/segmentWalking',()=>({segments:vi.fn(),mutateSegment:vi.fn()}));
const leg='leg',trip={trip_id:'trip',version:1,status:'active',progress:{anchor_event_id:'anchor'}};
const available={items:[],available:[{kind:'transfer',leg_id:leg,name:'하차 → 승차',variants:[]}]};
const item={measurement_id:'m',kind:'transfer',leg_id:leg,label:'2번 출구',status:'recording',version:1,reasons:['RECORDING'],predicted_seconds:null,predicted_arrival_at:null,can_finish:false};
beforeEach(()=>segments.mockResolvedValue(available));afterEach(()=>{cleanup();vi.resetAllMocks();});
async function mount(){const view=render(<SegmentWalking trip={trip}/>);await screen.findByText('하차 → 승차');return view;}
it('requires explicit boundary and label; retries an unknown failure with the same request',async()=>{
 await mount();const button=screen.getByText('이 구간 보행 시작');expect(button.disabled).toBe(true);
 fireEvent.change(screen.getByLabelText('환승 전체 보행 구간 이름'),{target:{value:'2번 출구'}});fireEvent.click(screen.getByRole('checkbox'));
 mutateSegment.mockRejectedValueOnce({code:'TIMEOUT'});await act(async()=>fireEvent.click(button));
 const operation=mutateSegment.mock.calls[0][1];expect(operation.body.start_boundary_confirmed).toBe(true);
 segments.mockResolvedValue({items:[item],available:[]});mutateSegment.mockResolvedValue(item);
 await act(async()=>fireEvent.click(button));expect(mutateSegment.mock.calls[1][1]).toBe(operation);
 expect(screen.getByText(/시작을 기록했어요/)).toBeTruthy();
});
it('finishes only after the existing arrival event and exposes the five-sample opt in',async()=>{
 segments.mockResolvedValue({items:[{...item,can_finish:true}],available:[]});render(<SegmentWalking trip={trip}/>);
 await screen.findByText('구간 기록 확인하고 반영');const checks=screen.getAllByRole('checkbox');fireEvent.click(checks[0]);fireEvent.click(checks[1]);
 mutateSegment.mockResolvedValue({...item,status:'valid'});segments.mockResolvedValue({items:[{...item,status:'valid',observed_seconds:20,sample_count:5,estimate_seconds:20}],available:[]});
 await act(async()=>fireEvent.click(screen.getByText('구간 기록 확인하고 반영')));
 expect(mutateSegment.mock.calls[0][1].body).toMatchObject({same_scope:true,apply_to_guidance:true,expected_version:1});
 expect(screen.getByText(/본인 기록 기반 추정 약 20초/)).toBeTruthy();expect(screen.queryByText('이 구간 학습에서 제외')).toBeNull();
});
it('ended history allows exclusion and unmount aborts a pending load',async()=>{
 segments.mockResolvedValue({items:[{...item,status:'valid',observed_seconds:20,sample_count:4,estimate_seconds:null}],available:[]});
 const view=render(<SegmentWalking trip={{...trip,status:'cancelled'}}/>);await screen.findByText('이 구간 학습에서 제외');
 mutateSegment.mockImplementation(()=>new Promise(()=>{}));fireEvent.click(screen.getByText('이 구간 학습에서 제외'));view.unmount();
 expect(mutateSegment.mock.calls[0][2].aborted).toBe(true);
});
