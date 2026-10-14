import React from 'react';
import { expect, it } from 'vitest';
import { render, screen } from '@testing-library/react';
import WalkingGuidance from '../../src/components/WalkingGuidance';

it('explains unconfirmed bus evidence even with no missing walking leg', () => {
  render(<WalkingGuidance route={{type:'BUS',missing_segments:[],ordered_legs:[]}}/>);
  expect(screen.getByText(/범위와 진행 방향/)).toBeTruthy();
  expect(screen.getByText(/AI 산정은 아직 실행하지/)).toBeTruthy();
  expect(screen.queryByText(/승강장/)).toBeNull();
});
it('distinguishes access, transfer and egress without displaying codes', () => {
  render(<WalkingGuidance route={{missing_segments:['ACCESS_WALK_MISSING','TRANSFER_WALK_MISSING','EGRESS_WALK_MISSING']}}/>);
  for (const text of ['승차 지점','환승 지점','목적지']) expect(screen.getByText(new RegExp(text))).toBeTruthy();
  expect(screen.queryByText(/ACCESS_WALK_MISSING/)).toBeNull();
});
it.each(['SUBWAY','BUS_AND_SUBWAY'])('explains indoor coverage for %s', type => {
  render(<WalkingGuidance route={{type}}/>);expect(screen.getByText(/입구부터 승강장/)).toBeTruthy();
});
it('uses an explicit indoor missing code even if the type is absent', () => {
  render(<WalkingGuidance route={{missing_segments:['ENTRANCE_PLATFORM_UNCONFIRMED']}}/>);
  expect(screen.getByText(/역 내부·환승/)).toBeTruthy();
});
it('does not treat a provider zero as a confirmed zero duration', () => {
  render(<WalkingGuidance route={{ordered_legs:[{type:'WALKING',seconds:0}]}}/>);
  expect(screen.getByText(/실제 이동이 없는 것으로 확정/)).toBeTruthy();
});
it('does not infer detailed segments from a routine summary', () => {
  render(<WalkingGuidance source="routine" route={{type:'BUS',total_seconds:600}}/>);
  expect(screen.getByText(/루틴 요약에 없어요/)).toBeTruthy();
  expect(screen.queryByText(/승차 지점까지 도보 구간이 부족/)).toBeNull();
});
it.each(['AI_OUTPUT_INVALID','PROMPT_RESOURCE_INVALID','PROVIDER_UNAVAILABLE','PROVIDER_TIMEOUT'])('uses safe fixed failure text for %s', errorCode => {
  render(<WalkingGuidance phase="error" errorCode={errorCode}/>);
  expect(screen.getByRole('alert')).toBeTruthy();
  expect(screen.queryByText(/산정은 아직 실행하지/)).toBeNull();
  expect(screen.queryByText(errorCode)).toBeNull();
});
it('never renders an unknown raw error', () => {
  render(<WalkingGuidance phase="error" errorCode="secret upstream raw body"/>);
  expect(screen.queryByText(/secret upstream/)).toBeNull();expect(screen.getByText(/경로를 다시 확인/)).toBeTruthy();
});
it('expired evidence hides all earlier durations and reasons', () => {
  render(<WalkingGuidance phase="expired" route={{total_seconds:123456,missing_segments:['ACCESS_WALK_MISSING']}}/>);
  expect(screen.getByText(/이전 경로의 시간을 사용하지/)).toBeTruthy();
  expect(screen.queryByText(/123456/)).toBeNull();expect(screen.queryByText(/승차 지점까지/)).toBeNull();
});

it.each(['toString','constructor','__proto__'])('safely ignores inherited property error %s', errorCode => {
  render(<WalkingGuidance phase="error" errorCode={errorCode}/>);
  expect(screen.getByText('도보 정보를 확인하지 못했어요. 경로를 다시 확인해주세요.')).toBeTruthy();
});

it('separates verified personal walking from approved provider departure estimation',()=>{
 render(<WalkingGuidance source="routine" route={{type:'BUS'}}/>);expect(screen.queryByText(/실제 출발 시간 안내는 준비 중/)).toBeNull();expect(screen.getByText(/접근 도보 시간에 개인 계수/)).toBeTruthy();
});
