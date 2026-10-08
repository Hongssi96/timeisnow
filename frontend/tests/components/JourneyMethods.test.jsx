import React from 'react';
import { expect, it, vi } from 'vitest';
import { fireEvent, render, screen, within } from '@testing-library/react';
import JourneyCandidates from '../../src/components/JourneyCandidates';
import { sortCandidates } from '../../src/lib/journeys';
import fixtures from '../fixtures/journeys.json';

const candidates=()=>[
  {...structuredClone(fixtures.direct),candidate_id:'bus',total_seconds:300},
  {...structuredClone(fixtures.mixed),candidate_id:'mixed',total_seconds:600},
  {...structuredClone(fixtures.direct),candidate_id:'subway',type:'SUBWAY',total_seconds:900},
];
const first=()=>within(screen.getAllByRole('article')[0]).getByRole('heading',{level:3}).textContent;

it('immediately puts each chosen method first and restores the default order with all',()=>{
  const original=candidates();render(<JourneyCandidates candidates={original} preference="balanced"/>);
  expect(first()).toContain('버스 경로 1');
  for(const [label,heading] of [['버스 + 지하철','버스·지하철'],['지하철','지하철'],['버스','버스']]){
    fireEvent.click(screen.getByRole('button',{name:label,exact:true}));
    expect(first()).toContain(heading+' 경로 1');
    expect(screen.getAllByRole('article')).toHaveLength(3);
    expect(screen.getByRole('button',{name:label,exact:true}).getAttribute('aria-pressed')).toBe('true');
  }
  fireEvent.click(screen.getByRole('button',{name:'전체',exact:true}));
  expect(first()).toContain('버스 경로 1');
  expect(original.map(c=>c.candidate_id)).toEqual(['bus','mixed','subway']);
});

it('keeps existing comparison criteria within matching and remaining groups',()=>{
  const data=[
    {candidate_id:'busSlow',type:'BUS',total_seconds:900,transfer_count:0,walking_seconds:10},
    {candidate_id:'subwaySlow',type:'SUBWAY',total_seconds:1200,transfer_count:0,walking_seconds:5},
    {candidate_id:'busFast',type:'BUS',total_seconds:300,transfer_count:1,walking_seconds:90},
    {candidate_id:'mixedFast',type:'BUS_AND_SUBWAY',total_seconds:600,transfer_count:2,walking_seconds:30},
  ];
  expect(sortCandidates(data,'balanced','BUS').map(c=>c.candidate_id)).toEqual(['busFast','busSlow','mixedFast','subwaySlow']);
  for(const preference of ['fewer_transfers','less_walking']) expect(sortCandidates(data,preference,'BUS').map(c=>c.candidate_id)).toEqual(['busSlow','busFast','subwaySlow','mixedFast']);
  expect(sortCandidates(data,'balanced','unknown')).toEqual(sortCandidates(data,'balanced'));
});

it('explains an unavailable method without hiding candidates',()=>{
  render(<JourneyCandidates candidates={[fixtures.direct]} preference="balanced"/>);
  fireEvent.click(screen.getByRole('button',{name:'지하철',exact:true}));
  expect(screen.getByRole('status').textContent).toContain('지하철 경로가 이번 검색 결과에 없어요');
  expect(first()).toContain('버스 경로 1');expect(screen.getAllByRole('article')).toHaveLength(1);
  fireEvent.click(screen.getByRole('button',{name:'버스',exact:true}));
  expect(screen.getByRole('status').textContent).not.toContain('없어요');
});

it('keeps expanded details and edited routine input bound to the candidate after moving it',()=>{
  const onSaved=vi.fn(), onRecheck=vi.fn();
  const {rerender}=render(<JourneyCandidates candidates={candidates()} preference="balanced" onSaved={onSaved} onSavedLocations={()=>'idle'} defaultRoutineName="출근" onRecheck={onRecheck}/>);
  const bus=screen.getAllByRole('article')[0];
  fireEvent.click(within(bus).getByRole('button',{name:'구간 자세히'}));
  fireEvent.click(within(bus).getByRole('button',{name:'이 경로를 루틴에 저장'}));
  fireEvent.change(within(bus).getByLabelText('루틴 이름'),{target:{value:'아침 버스'}});
  fireEvent.click(screen.getByRole('button',{name:'지하철',exact:true}));
  const moved=screen.getAllByRole('article')[1];
  expect(within(moved).getByRole('button',{name:'구간 닫기'}).getAttribute('aria-expanded')).toBe('true');
  expect(within(moved).getByLabelText('루틴 이름').value).toBe('아침 버스');
  expect(onSaved).not.toHaveBeenCalled();expect(onRecheck).not.toHaveBeenCalled();
  fireEvent.click(within(moved).getByRole('button',{name:'루틴 저장',exact:true}));
  expect(onSaved).toHaveBeenCalledWith('bus','아침 버스',[1,2,3,4,5],null);
  rerender(<JourneyCandidates candidates={candidates()} preference="less_walking"/>);
  expect(first()).toContain('지하철 경로 1');
});
