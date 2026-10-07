import React from 'react';
import { afterEach, expect, it, vi } from 'vitest';
import { act, fireEvent, render, screen, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import App from './App';
vi.mock('./PlacesCard',()=>({default:()=>null}));
vi.mock('./AccountForm',()=>({default:()=> <p>검증용 계정</p>}));
vi.mock('./OriginSelector',()=>({default:({onSelect})=><button onClick={()=>onSelect({label:'지도 선택 위치',location_address:'서울 합성동',origin:{type:'map_pin'},deadline:Date.now()+600000})}>검증용 출발지 확인</button>}));
afterEach(()=>vi.useRealTimers());
async function select(){
  render(<App/>);const user=userEvent.setup();await user.click(screen.getByRole('button',{name:/다른 곳에서 출발/}));
  await user.click(screen.getByRole('button',{name:'검증용 출발지 확인'}));return user;
}
it('real selection hides synthetic route/time and blocks demo even after switching routine',async()=>{
  const user=await select();expect(screen.getByText('지도 선택 위치에서 출발 준비')).toBeTruthy();
  expect(screen.queryByRole('button',{name:'지금 출발할게요'})).toBeNull();expect(screen.queryByText('오늘의 이동 경로')).toBeNull();
  await user.click(screen.getByRole('button',{name:'학교 학교 가는 길'}));expect(screen.queryByRole('button',{name:'지금 출발할게요'})).toBeNull();
  await user.click(screen.getByRole('button',{name:'예시 화면으로 돌아가기'}));expect(screen.getByRole('button',{name:'지금 출발할게요'})).toBeTruthy();
});
it('expires after ten minutes while keeping example departure blocked',async()=>{
  vi.useFakeTimers();render(<App/>);
  fireEvent.click(screen.getByRole('button',{name:/다른 곳에서 출발/}));
  fireEvent.click(screen.getByRole('button',{name:'검증용 출발지 확인'}));
  await act(()=>vi.advanceTimersByTimeAsync(600000));
  expect(screen.getByText('출발지를 다시 확인해주세요')).toBeTruthy();expect(screen.queryByRole('button',{name:'지금 출발할게요'})).toBeNull();
});
it('entering account modal clears earlier private selection',async()=>{
  const user=await select();await user.click(within(screen.getByRole('navigation',{name:'주 메뉴'})).getByRole('button',{name:'내 설정'}));
  await user.click(screen.getByRole('button',{name:'회원가입 · 로그인'}));await user.click(screen.getByRole('button',{name:'닫기'}));
  await user.click(within(screen.getByRole('navigation',{name:'주 메뉴'})).getByRole('button',{name:'오늘의 출발'}));
  expect(screen.queryByText('서울 합성동')).toBeNull();expect(screen.getByRole('button',{name:'지금 출발할게요'})).toBeTruthy();
});
