import React from 'react';
import { expect, it, vi } from 'vitest';
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import OriginReview from '../../src/components/OriginReview';
vi.mock('../../src/components/MapPinPicker',()=>({default:({onReady})=><><button onClick={()=>onReady(true)}>합성 지도 성공</button><button onClick={()=>onReady(false)}>합성 지도 실패</button></>}));
it('only allows manual confirmation after the map loads; map retry blocks it again',async()=>{
  const confirm=vi.fn();const user=userEvent.setup();
  render(<OriginReview draft={{location:{latitude:37.5665,longitude:126.978},origin:{captured_at:'2099-01-01T00:00:00Z',accuracy_meters:5000},quality:{time_relation:'future'}}} onConfirm={confirm}/>);
  const button=screen.getByRole('button',{name:'이 위치가 실제 출발 위치예요'});
  expect(button.disabled).toBe(true);
  expect(screen.getByText(/측정 시각이 서버 시각보다/)).toBeTruthy();
  await user.click(screen.getByRole('button',{name:'합성 지도 성공'}));await user.click(button);expect(confirm).toHaveBeenCalledOnce();
  await user.click(screen.getByRole('button',{name:'합성 지도 실패'}));expect(button.disabled).toBe(true);
});
