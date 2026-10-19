import React, { useEffect, useState,useRef } from 'react';
import { Clock3, Flag } from 'lucide-react';
import { getFirstArrivals } from '../lib/arrivals';
import { getFirstDeparture } from '../lib/departure';
import ManualDeparture from './ManualDeparture';
import DepartureDetails from './DepartureDetails';

const connectionText={estimated_feasible:'예상 연결 가능',unavailable:'현재 제공된 차량으로 연결 어려움',unknown:'연결 정보 확인 필요',not_checked:'환승 연결 확인 전',stale:'환승 정보 만료'};
const connectionTime=value=>new Intl.DateTimeFormat('ko-KR',{timeZone:'Asia/Seoul',month:'numeric',day:'numeric',hour:'2-digit',minute:'2-digit',hourCycle:'h23'}).format(new Date(value));
const bufferText=seconds=>seconds%60===0?`${seconds/60}분`:`${seconds>=60?`${Math.floor(seconds/60)}분 `:''}${seconds%60}초`;
const mappingMessages={
  MAPPING_CONTEXT_UNAVAILABLE:'정류소 확인에 필요한 검색 근거가 없어요. 최신 경로를 다시 조회해주세요.',
  MULTIPLE_VEHICLE_OPTIONS:'첫 버스 구간에 여러 노선이 포함돼 한 차량의 도착을 확인할 수 없어요.',
  STATION_CANDIDATES_UNCONFIRMED:'승차 정류소를 경기 교통 정보와 일치시키지 못했어요.',
  NO_ROUTE_AT_BOARDING_STOP:'이 정류소의 해당 노선을 경기 교통 정보에서 확인하지 못했어요. 미지원 노선일 수 있어요.',
  ROUTE_CANDIDATE_LIMIT:'일치할 수 있는 노선이 여러 개여서 확정하지 못했어요.',
  VISIT_CANDIDATE_LIMIT:'정류소 방문 후보가 여러 개여서 확정하지 못했어요.',
  ROUTE_MATCH_AMBIGUOUS:'일치하는 노선·정류소 방문이 여러 개여서 확정하지 못했어요.',
  ROUTE_SEQUENCE_UNCONFIRMED:'경로의 정류소 순서와 승하차 위치를 경기 교통 정보로 확인하지 못했어요.',
  ROUTE_INFO_UNCONFIRMED:'노선 상세 정보를 확인하지 못했어요.',
  TURNAROUND_UNCONFIRMED:'이 노선의 회차와 승차 방향을 확인하지 못했어요.',
  DIRECTION_MATCH_AMBIGUOUS:'승차 방향을 하나로 확정하지 못했어요.',
};
const mappingMessage=evidence=>Array.isArray(evidence?.reasons)?evidence.reasons.map(reason=>typeof reason==='string'&&Object.hasOwn(mappingMessages,reason)?mappingMessages[reason]:null).find(Boolean):null;
const walkFailure=departure=>departure?.reasons?.includes('ACCESS_WALK_MAPPING_REQUIRED')?'접근 도보를 조회할 승차 정류소가 아직 확인되지 않았어요.':departure?.reasons?.includes('ACCESS_WALK_TIMEOUT')?'승차 정류소까지 도보 조회가 늦어 출발 시각을 계산하지 못했어요.':departure?.reasons?.includes('ACCESS_WALK_UNAVAILABLE')?'승차 정류소까지 도보 경로를 얻지 못해 출발 시각을 계산할 수 없어요.':departure?.reasons?.includes('ACCESS_WALK_TIME_LIMIT')?'조회 시간이 부족해 접근 도보를 확인하지 못했어요. 다시 확인해주세요.':null;
const empty = { mapping_required:'이 경로의 버스 정류소와 방향을 아직 확인하지 못했어요.', unsupported:'이 첫 탑승 수단의 도착 조회는 아직 지원하지 않아요.', no_arrivals:'현재 제공된 도착 후보가 없어요.', insufficient_data:'현재 도착 시간을 추정할 근거가 부족해요.', expired:'도착 정보가 만료됐어요. 이전 예상 시간은 사용하지 않아요.' };

export default function FirstArrivals({ searchId, candidateId, includeDeparture=false, loader=null, initialResponse=null, routineId=null,onReported=null,onCancelled=null,compact=false,detailsContent=null }) {
  const [state, setState] = useState({ phase:'loading' });
  const [tick, setTick] = useState(0);
  const [localReported,setLocalReported]=useState(false),reportRef=useRef(false);
  function markReported(){reportRef.current=true;setLocalReported(true);onReported?.();}
  useEffect(() => {
    let disposed=false, controller=null, sequence=0, busy=false, terminal=false;
    reportRef.current=initialResponse?.data?.departure_state==='reported_departed';setLocalReported(reportRef.current);
    if(reportRef.current)onReported?.();
    if(initialResponse) setState({phase:'ready', evidence:initialResponse.data.arrival_evidence, departure:initialResponse.data, serverAt:Date.parse(initialResponse.meta.server_time), sampledAt:performance.now()});
    else setState({ phase:'loading' });
    async function load() {
      if (disposed || busy || terminal || document.hidden || reportRef.current) return;
      busy=true;controller=new AbortController();const seq=++sequence;
      try {
        const response=await (loader || (includeDeparture?getFirstDeparture:getFirstArrivals))(searchId,candidateId,controller.signal);
        if (!disposed && seq===sequence && !reportRef.current) {
          setState({ phase:'ready', evidence:includeDeparture?response.data.arrival_evidence:response.data, departure:includeDeparture?response.data:null, serverAt:Date.parse(response.meta.server_time), sampledAt:performance.now() });
          if(response.data.departure_state==='reported_departed')markReported();
        }
      } catch (error) {
        if (!disposed && seq===sequence && !reportRef.current && error.name!=='AbortError') {
          terminal=Boolean(loader)||['AUTH_REQUIRED','SESSION_EXPIRED','RESOURCE_NOT_FOUND','VERSION_CONFLICT','INVALID_RESPONSE'].includes(error.code);
          setState(old=>terminal ? {phase:'blocked',error:error.code} : {...old,phase:old.evidence?'ready':'error',error:true});
        }
      } finally { if (seq===sequence) busy=false; }
    }
    function visibility() {
      if (document.hidden) { sequence++;controller?.abort();busy=false; }
      else load();
    }
    if(!initialResponse)load();const polling=setInterval(load,60000);const clock=setInterval(()=>setTick(t=>t+1),1000);
    document.addEventListener('visibilitychange',visibility);
    return ()=>{disposed=true;sequence++;controller?.abort();clearInterval(polling);clearInterval(clock);document.removeEventListener('visibilitychange',visibility);};
  }, [searchId,candidateId,includeDeparture,loader,initialResponse,onReported]);
  const d=state.evidence;
  const departure=state.departure;
  const reported=localReported||departure?.departure_state==='reported_departed';
  const selectionFailure=departure?.reasons?.includes('DEPARTURE_UNCONFIRMED_NO_NEXT')?'출발 확인이 저장되지 않았고, 이용 가능한 다음 차량 정보가 없어 새 출발 시각을 안내할 수 없어요.':departure?.reasons?.includes('SELECTION_IDENTITY_UNCONFIRMED')?'안내한 차량을 대조할 근거가 부족해요. 최신 경로를 다시 확인해주세요.':departure?.reasons?.includes('SELECTION_HISTORY_LIMIT')?'현재 근거로 다음 차량을 계속 선택할 수 없어요. 잠시 후 다시 확인해주세요.':null;
  const now=d ? state.serverAt+Math.max(0,performance.now()-state.sampledAt) : 0;
  const expired=d && now>Date.parse(d.expires_at);
  const candidates=d?.valid_for_guidance && !expired ? d.candidates.filter(c=>c.predicted_arrival_at && Date.parse(c.predicted_arrival_at)>now) : [];
  const departureReachable=departure?.vehicle_arrival_at&&Date.parse(departure.vehicle_arrival_at)-now>=departure.approach_seconds*1000;
  const displaySlack=departure?.vehicle_arrival_at ? Math.floor((Date.parse(departure.vehicle_arrival_at)-Math.max(now,Date.parse(departure.selected_departure_at)))/1000-departure.approach_seconds) : null;
  const secondsToDeparture=departure?.selected_departure_at ? Math.ceil((Date.parse(departure.selected_departure_at)-now)/1000) : 0;
  const departureReady=departure?.valid_for_guidance&&departureReachable&&!expired&&now<=Date.parse(departure.valid_until)&&candidates.some(c=>c.candidate_id===departure.arrival_candidate_id);
  const goal=departure?.target_evaluation;
  const goalPassed=goal?.target_arrival_at&&now>Date.parse(goal.target_arrival_at);
  const age=d?.received_at ? Math.max(0,Math.floor((now-Date.parse(d.received_at))/1000)) : null;
  const connectionDetails=<>
      {includeDeparture&&departure?.connection_status&&<>
        {expired||now>Date.parse(departure.valid_until)?<p>환승 정보가 만료됐어요. 이전 연결 시각은 사용하지 않아요.</p>:<>
          <p><strong>{connectionText[departure.connection_status]}</strong></p>
          {!!departure.supplemental_walks?.length&&<div className="candidate-note" aria-label="보완한 도보 안내">
            {departure.supplemental_walks.map(w=><p key={w.connection_id||'egress'}>
              {w.source==='same_stop'?'같은 정류소에서 환승 · 환승 여유는 따로 반영해요.':`${w.role==='transfer'?'환승':'마지막'} 도보 약 ${bufferText(w.walking_seconds)} · 별도 조회한 도보 추정`}
            </p>)}
          </div>}
          {departure.reasons?.some(r=>typeof r==='string'&&r.startsWith('TRANSFER_WALK_'))&&<p>환승 도보를 아직 확인하지 못했어요. 최신 출발을 다시 확인해주세요.</p>}
          {departure.reasons?.some(r=>typeof r==='string'&&r.startsWith('EGRESS_WALK_'))&&<p>마지막 도보를 아직 확인하지 못했어요. 목적지 도착은 확인 전이에요.</p>}
          {!!departure.transfers?.length&&<ul>{departure.transfers.map((c,index)=><li key={c.connection_id}>
            환승 {index+1} · {connectionText[c.feasibility]}
            {c.minimum_boarding_at&&<p>최소 승차 시각 {connectionTime(c.minimum_boarding_at)}</p>}
            {c.next_boarding_at&&<p>다음 차량 예상 {connectionTime(c.next_boarding_at)}</p>}
            {c.reasons?.includes('NO_SUPPLIED_VEHICLE_AFTER_MINIMUM')&&<p>현재 제공된 차량은 도착하기 전에 지나가요. 이후 차량 정보는 다시 확인해야 해요.</p>}
          </li>)}</ul>}
          {!!departure.personal_segment_walks?.length&&<div className="info-box segment-walking">{departure.personal_segment_walks.map(w=><p key={w.kind+w.leg_id}>{w.kind==='station_internal'?'역 내부 구간':'환승 전체 구간'} · {w.label}: 본인 기록 기반 약 {w.estimate_seconds}초 · 최근 {w.sample_count}회{w.kind==='station_internal'?' (전체 도보와 중복 합산하지 않음)':''}</p>)}</div>}
          {!!departure.transfers?.length&&<p>환승 도보와 차량 시각은 추정값이에요. 실제 환승 성공을 보장하지 않아요.</p>}
        </>}
      </>}
  </>;
  const arrivalDetails=<>
      {age!==null && <p className="candidate-note">{age}초 전 조회</p>}
      {!!candidates.length ? <>
        <p><strong>{d.timing_basis==='receipt_estimate'?'수신 기준 예상':'생성시각 확인된 예측'}</strong></p>
        <ul>{candidates.map((c,i)=><li key={c.candidate_id}>{i===0?'첫 차량':'다음 차량'} · 약 {Math.ceil((Date.parse(c.predicted_arrival_at)-now)/60000)}분 뒤 도착 예상</li>)}</ul>
        {d.timing_basis==='receipt_estimate' && <p>원천 갱신 지연은 확인되지 않았어요. 실제 도착과 다를 수 있어요.</p>}
        {!includeDeparture&&<p>개인 접근 시간을 반영한 출발 시각은 아직 계산하지 않아요.</p>}
      </> : <p role="status">{expired?empty.expired:(d?.status==='mapping_required'&&mappingMessage(d)) || empty[d?.status] || '이전 도착 예상이 지났어요. 새 정보를 확인해주세요.'}</p>}
  </>;
  const goalDetails=<>
  {includeDeparture&&goal&&!reported&&<section className="info-box walking-guidance target-evaluation" aria-label="목표 도착 평가">
    <h3><Flag size={18}/>목표 도착 평가</h3>
    {goal.target_arrival_at&&<p>오늘 목표 도착 {connectionTime(goal.target_arrival_at)}</p>}
    {expired||now>Date.parse(departure.valid_until)?<p>목표 도착 평가가 만료됐어요. 이전 예상 도착은 사용하지 않아요.</p>:goal.status==='target_passed'||goalPassed?<p>오늘 목표 도착 시각이 지났어요. 다음 날로 자동 변경하지 않아요.</p>:['estimated_meets','estimated_late'].includes(goal.status)&&departureReady?<>
      <p><strong>{goal.status==='estimated_meets'?'현재 근거로는 목표 시각까지 도착할 것으로 예상해요.':'현재 근거로는 목표 시각보다 늦게 도착할 것으로 예상해요.'}</strong></p>
      <p>예상 목적지 도착 {connectionTime(goal.estimated_destination_arrival_at)}</p>
      <p>목표 도착 기준 예상 {bufferText(Math.abs(goal.margin_seconds))} {goal.status==='estimated_meets'?'여유':'늦음'}</p>
      <p className="candidate-note">환승과 마지막 도보를 포함한 공급자 기반 추정이에요. 실제 도착을 보장하지 않아요.</p>
    </>:goal.status==='not_configured'?<p>목표 도착 시각을 설정하면 현재 경로의 예상 도착을 비교할 수 있어요.</p>:<p>{goal.reasons?.includes('EGRESS_TIME_UNCONFIRMED')?'하차 후 목적지까지 도보 시간이 없어 목표 도착을 확인할 수 없어요.':goal.reasons?.includes('CONNECTIONS_UNCONFIRMED')?'환승 연결이 확인되지 않아 목표 도착을 확인할 수 없어요.':'현재 이동 근거로는 목표 도착을 확인할 수 없어요.'}</p>}
  </section>}
  </>;
  return <>
  <section className="info-box walking-guidance first-arrivals" aria-label={includeDeparture?'언제이니? 출발 안내':'첫 탑승 도착 정보'}>
    <h3><Clock3 size={18}/>{includeDeparture?'언제이니?':'첫 탑승 도착 예상'}</h3>
    {state.phase==='loading' && <p role="status">도착 정보를 확인하고 있어요.</p>}
    {state.phase==='blocked' && <p role="alert">{['AUTH_REQUIRED','SESSION_EXPIRED'].includes(state.error)?'로그인 후 다시 확인해주세요.':'경로를 다시 검색해 도착 정보를 확인해주세요.'}</p>}
    {state.error && state.phase!=='blocked' && <p role="alert">도착 정보를 다시 조회하지 못했어요. 이전 정보의 유효시간은 늘리지 않아요.</p>}
    {reported&&<p role="status">출발 확인이 저장되어 출발 전 안내를 종료했어요. 아래에서 현재 이동 구간을 확인해주세요.</p>}
    {d && !reported && <>
      {includeDeparture && <>
        {departureReady ? <>
          <div className="departure-countdown" aria-label="출발까지 남은 시간">
            <p className="departure-countdown-label"><Clock3 size={18} aria-hidden="true"/>출발까지 남은 시간</p>
            <p className="when-answer">{secondsToDeparture>0?<><strong>{Math.ceil(secondsToDeparture/60)}분</strong>{secondsToDeparture<60&&<span className="when-unit">이내</span>}</>:<strong>지금</strong>}</p>
            <p className="departure-countdown-caption">{secondsToDeparture>0?'뒤에 출발하세요':'출발할 시간이에요'}</p>
            <p className="departure-countdown-estimate">현재 교통 정보 기준 예상</p>
          </div>
          {departure.reasons?.includes('DEPARTURE_UNCONFIRMED_NEXT_VEHICLE')&&<p>출발 확인 없이 권장 시각에서 접근 시간의 절반이 지나, 다음 차량 기준으로 다시 계산했어요.</p>}
          {departure.reasons?.includes('NEXT_REACHABLE_VEHICLE')&&<p>접근 시간이 부족한 앞 차량을 제외하고 다음 차량 기준으로 계산했어요.</p>}
          {secondsToDeparture<=0&&<p role="status">지금 출발 기준으로 다시 확인해주세요.</p>}
          <p>{secondsToDeparture>0?'그때':'지금'} 출발하면 정류장 도착 후 예상 {bufferText(displaySlack)} 여유가 있어요.</p>
          {!compact&&<p className="candidate-note">{departure.provider_approach_source==='boarding_walk'?'정류소까지 도보는 별도로 조회한 추정이에요.':'공급자 접근 도보를 추정에 사용했어요.'}</p>}
          {now>Date.parse(departure.recommended_departure_at) && <p>권장 출발 시각이 지났어요. 설정 여유를 확보할 수 있는지 다시 확인해주세요.</p>}
          {displaySlack<departure.buffer_seconds && <p>지금 출발 기준 예상 여유가 설정한 여유보다 적어요.</p>}
        </> : <p role="status">{expired||now>Date.parse(departure?.valid_until)?'출발 정보가 만료됐어요. 이전 출발 시각은 사용하지 않아요.':departure?.status==='not_enough_time'||(departure?.valid_for_guidance&&!departureReachable)?'이 차량에 맞춰 출발하기에는 접근 시간이 부족해요.':selectionFailure||walkFailure(departure)|| (departure?.reasons?.includes('ACCESS_TIME_UNCONFIRMED')?'출발지에서 승차 지점까지 도보 시간이 제공되지 않아 출발 시각을 계산할 수 없어요.':'출발 시각을 계산할 접근 시간 또는 도착 근거가 부족해요.')}</p>}
      </>}
      {!compact&&<>{connectionDetails}{arrivalDetails}</>}
      {compact&&includeDeparture&&departure?.connection_status&&<p role="status">{expired||now>Date.parse(departure.valid_until)?'환승 정보가 만료됐어요. 이전 연결 시각은 사용하지 않아요.':connectionText[departure.connection_status]}</p>}
    </>}
    {routineId&&<ManualDeparture routineId={routineId} departure={departure} available={Boolean(departureReady&&!reported)} onReported={markReported} onCancelled={onCancelled}/>}
    {compact&&<DepartureDetails>
      <div className="walking-guidance">
        {state.phase==='loading'&&<p role="status">도착 정보를 확인하고 있어요.</p>}
        {state.phase==='blocked'&&<p role="alert">{['AUTH_REQUIRED','SESSION_EXPIRED'].includes(state.error)?'로그인 후 다시 확인해주세요.':'경로를 다시 검색해 도착 정보를 확인해주세요.'}</p>}
        {state.error&&state.phase!=='blocked'&&<p role="alert">도착 정보를 다시 조회하지 못했어요. 이전 정보의 유효시간은 늘리지 않아요.</p>}
        {d&&!reported&&<>
          {departureReady&&<p className="candidate-note">{departure.provider_approach_source==='boarding_walk'?'정류소까지 도보는 별도로 조회한 추정이에요.':'공급자 접근 도보를 추정에 사용했어요.'}</p>}
          {connectionDetails}{arrivalDetails}{goalDetails}
        </>}
        {reported&&<p>출발 전 안내는 종료됐어요. 현재 이동 구간은 메인 화면에서 확인해주세요.</p>}
        {detailsContent}
      </div>
    </DepartureDetails>}
  </section>
  {!compact&&goalDetails}
  {compact&&includeDeparture&&goal&&!reported&&goal.status!=='not_configured'&&<section className="info-box walking-guidance target-evaluation" aria-label="목표 도착 평가">
    <h3><Flag size={18}/>목표 도착 평가</h3>
    {expired||now>Date.parse(departure.valid_until)?<p role="status">목표 도착 평가가 만료됐어요. 이전 예상 도착은 사용하지 않아요.</p>:goal.status==='target_passed'||goalPassed?<p>오늘 목표 도착 시각이 지났어요. 다음 날로 자동 변경하지 않아요.</p>:['estimated_meets','estimated_late'].includes(goal.status)&&departureReady?<p>목표 도착 기준 예상 {bufferText(Math.abs(goal.margin_seconds))} {goal.status==='estimated_meets'?'여유':'늦음'}</p>:<p>목표 도착을 확인할 정보가 부족해요. 자세히 보기에서 확인해주세요.</p>}
  </section>}
  </>;
}
