import React, { useState } from 'react';
import { Footprints, BusFront, TrainFront, ChevronDown, ChevronUp } from 'lucide-react';
import { formatJourneyTime, missingWalk, sortCandidates } from '../lib/journeys';

const kinds={BUS:'버스',SUBWAY:'지하철',BUS_AND_SUBWAY:'버스·지하철',WALKING:'도보'};
const roles={access:'접근 도보',transfer:'환승 도보',egress:'마지막 도보'};
const messages={ACCESS_WALK_MISSING:'출발지에서 승차 지점까지 도보 확인 필요',EGRESS_WALK_MISSING:'하차 지점에서 목적지까지 도보 확인 필요',
  TRANSFER_WALK_MISSING:'일부 환승 도보 확인 필요',TRANSFER_COUNT_MISMATCH:'공급자 환승 수와 교통 구간 수가 달라 확인 필요',
  DURATION_TOTAL_MISMATCH:'구간 시간 합계와 총 예상 시간이 달라 확인 필요',REGION_PATH_UNVERIFIED:'경로 중간의 지원 지역 확인 필요'};
const vehicleNames=leg=>[...new Set(leg.vehicles)].slice(0,3).join(' / ');
const vehicleDetails=leg=>[...new Set(leg.vehicle_options.map(v=>v.name+(v.provider_type?' ('+v.provider_type+')':'')))].slice(0,3).join(' / ');
const icon=kind=>kind==='BUS'?BusFront:kind==='SUBWAY'?TrainFront:Footprints;

export default function JourneyCandidates({ candidates, preference, onRecheck }) {
  const [expanded,setExpanded]=useState(null);
  return <div className="journey-candidates"><div className="section-heading"><h2>경로 후보 {candidates.length}개</h2><button className="text-button" onClick={onRecheck}>결과 다시 확인</button></div>
    <div className="info-box">카카오 예상 시간으로 비교해요. 운행 시간과 지금 이용 가능 여부는 확인이 필요해요. 실시간 도착·개인 도보 시간·출입구와 승강장 정보는 확인 중이에요. 출발 안내와 루틴 저장은 준비 중이에요.</div>
    <div className="candidate-grid">{sortCandidates(candidates,preference).map((c,index)=>{
      const open=expanded===c.candidate_id,TitleIcon=c.type==='SUBWAY'?TrainFront:BusFront;
      return <article className={'card route-candidate '+(open?'expanded':'')} key={c.candidate_id}>
        <div className="section-heading"><h3><TitleIcon size={20}/> {kinds[c.type]} 경로 {index+1}</h3><span className="tag">예상값</span></div>
        <dl className="candidate-metrics"><div><dt>총 예상 시간</dt><dd>약 {formatJourneyTime(c.total_seconds)}</dd></div><div><dt>환승</dt><dd>{c.transfer_count}회</dd></div><div><dt>{missingWalk(c)?'제공된 일부 도보':'제공된 도보'}</dt><dd>{missingWalk(c)&&c.walking_seconds===0?'확인 필요':`약 ${formatJourneyTime(c.walking_seconds)}`}</dd></div></dl>
        <p className="candidate-line">{c.ordered_legs.filter(leg=>leg.type!=='WALKING').map(leg=>vehicleNames(leg)).join(' → ')}</p>
        {missingWalk(c)&&<p className="candidate-note">빠진 도보 구간이 있어 전체 도보 시간은 확인이 필요해요.</p>}
        {c.missing_segments.includes('DURATION_TOTAL_MISMATCH')&&<p className="candidate-note">총 예상 시간은 다시 확인해야 해요.</p>}
        {c.transfer_count!==c.transfer_count_computed&&<p className="candidate-note">구간 기준 환승 {c.transfer_count_computed}회 · 횟수 확인 필요</p>}
        <button className="secondary wide" aria-expanded={open} aria-controls={'candidate-'+c.candidate_id} onClick={()=>setExpanded(open?null:c.candidate_id)}>{open?'구간 닫기':'구간 자세히'}{open?<ChevronUp size={17}/>:<ChevronDown size={17}/>}</button>
        {open&&<div id={'candidate-'+c.candidate_id} className="candidate-detail"><ol className="route-detail">{c.ordered_legs.map(leg=>{const Icon=icon(leg.type);return <li key={leg.leg_id}><span className="soft-icon"><Icon size={18}/></span><div><strong>{leg.type==='WALKING'?roles[leg.walking_role]:kinds[leg.type]+' · '+vehicleNames(leg)}</strong><p>약 {formatJourneyTime(leg.seconds)} · {leg.distance_meters.toLocaleString('ko-KR')}m</p>{leg.type!=='WALKING'&&<><p>{leg.boarding.name} → {leg.alighting.name}</p><p className="candidate-note">정류장 순서 기준 · 실제 운행 방향 확인 필요</p>{leg.vehicle_options.some(v=>v.provider_type)&&<p className="candidate-note">{vehicleDetails(leg)}</p>}</>}</div></li>;})}</ol>
          {c.connections.map(x=><div className="candidate-connection" key={x.connection_id}><strong>환승 연결</strong><p>{x.from_stop.name} → {x.to_stop.name}</p><p>{x.walking_seconds===null?'환승 도보 확인 필요':`제공된 환승 도보 약 ${formatJourneyTime(x.walking_seconds)}`} · 연결 가능 여부 확인 필요</p></div>)}
          {!!c.timing_breakdown.unallocated_seconds&&<p className="candidate-note">총 시간 중 약 {formatJourneyTime(c.timing_breakdown.unallocated_seconds)}은 구간별로 구분되지 않았어요. 대기나 여유 시간으로 확정하지 않아요.</p>}
          <ul className="candidate-reasons">{c.missing_segments.filter(reason=>messages[reason]).map(reason=><li key={reason}>{messages[reason]}</li>)}</ul>
          <p className="candidate-note">출입구·승강장과 실제 환승 가능 여부는 아직 확인되지 않았어요.</p>
        </div>}
      </article>;
    })}</div>
  </div>;
}
