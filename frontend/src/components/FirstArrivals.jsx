import React, { useEffect, useState } from 'react';
import { Clock3 } from 'lucide-react';
import { getFirstArrivals } from '../lib/arrivals';
import { getFirstDeparture } from '../lib/departure';

const connectionText={estimated_feasible:'예상 연결 가능',unavailable:'현재 제공된 차량으로 연결 어려움',unknown:'연결 정보 확인 필요',not_checked:'환승 연결 확인 전',stale:'환승 정보 만료'};
const connectionTime=value=>new Intl.DateTimeFormat('ko-KR',{timeZone:'Asia/Seoul',month:'numeric',day:'numeric',hour:'2-digit',minute:'2-digit',hourCycle:'h23'}).format(new Date(value));
const bufferText=seconds=>seconds%60===0?`${seconds/60}분`:`${seconds>=60?`${Math.floor(seconds/60)}분 `:''}${seconds%60}초`;
const empty = { mapping_required:'이 경로의 버스 정류소와 방향을 아직 확인하지 못했어요.', unsupported:'이 첫 탑승 수단의 도착 조회는 아직 지원하지 않아요.', no_arrivals:'현재 제공된 도착 후보가 없어요.', insufficient_data:'현재 도착 시간을 추정할 근거가 부족해요.', expired:'도착 정보가 만료됐어요. 이전 예상 시간은 사용하지 않아요.' };

export default function FirstArrivals({ searchId, candidateId, includeDeparture=false, loader=null, initialResponse=null }) {
  const [state, setState] = useState({ phase:'loading' });
  const [tick, setTick] = useState(0);
  useEffect(() => {
    let disposed=false, controller=null, sequence=0, busy=false, terminal=false;
    if(initialResponse) setState({phase:'ready', evidence:initialResponse.data.arrival_evidence, departure:initialResponse.data, serverAt:Date.parse(initialResponse.meta.server_time), sampledAt:performance.now()});
    else setState({ phase:'loading' });
    async function load() {
      if (disposed || busy || terminal || document.hidden) return;
      busy=true;controller=new AbortController();const seq=++sequence;
      try {
        const response=await (loader || (includeDeparture?getFirstDeparture:getFirstArrivals))(searchId,candidateId,controller.signal);
        if (!disposed && seq===sequence) setState({ phase:'ready', evidence:includeDeparture?response.data.arrival_evidence:response.data, departure:includeDeparture?response.data:null, serverAt:Date.parse(response.meta.server_time), sampledAt:performance.now() });
      } catch (error) {
        if (!disposed && seq===sequence && error.name!=='AbortError') {
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
  }, [searchId,candidateId,includeDeparture,loader,initialResponse]);
  const d=state.evidence;
  const departure=state.departure;
  const now=d ? state.serverAt+Math.max(0,performance.now()-state.sampledAt) : 0;
  const expired=d && now>Date.parse(d.expires_at);
  const candidates=d?.valid_for_guidance && !expired ? d.candidates.filter(c=>c.predicted_arrival_at && Date.parse(c.predicted_arrival_at)>now) : [];
  const departureReachable=departure?.vehicle_arrival_at&&Date.parse(departure.vehicle_arrival_at)-now>=departure.approach_seconds*1000;
  const departureReady=departure?.valid_for_guidance&&departureReachable&&!expired&&now<=Date.parse(departure.valid_until)&&candidates.some(c=>c.candidate_id===departure.arrival_candidate_id);
  const departureTime=departureReady?new Intl.DateTimeFormat('ko-KR',{timeZone:'Asia/Seoul',hour:'2-digit',minute:'2-digit',hourCycle:'h23'}).format(new Date(departure.selected_departure_at)):null;
  const dayFormat=new Intl.DateTimeFormat('sv-SE',{timeZone:'Asia/Seoul',year:'numeric',month:'2-digit',day:'2-digit'});
  const departureDay=departureReady&&dayFormat.format(new Date(departure.selected_departure_at))!==dayFormat.format(new Date(now))?new Intl.DateTimeFormat('ko-KR',{timeZone:'Asia/Seoul',month:'long',day:'numeric'}).format(new Date(departure.selected_departure_at))+' ':'';
  const age=d?.received_at ? Math.max(0,Math.floor((now-Date.parse(d.received_at))/1000)) : null;
  return <section className="info-box walking-guidance first-arrivals" aria-label={includeDeparture?'첫 탑승 출발 정보':'첫 탑승 도착 정보'}>
    <h3><Clock3 size={18}/>{includeDeparture?'첫 탑승 예상 출발':'첫 탑승 도착 예상'}</h3>
    {state.phase==='loading' && <p role="status">도착 정보를 확인하고 있어요.</p>}
    {state.phase==='blocked' && <p role="alert">{['AUTH_REQUIRED','SESSION_EXPIRED'].includes(state.error)?'로그인 후 다시 확인해주세요.':'경로를 다시 검색해 도착 정보를 확인해주세요.'}</p>}
    {state.error && state.phase!=='blocked' && <p role="alert">도착 정보를 다시 조회하지 못했어요. 이전 정보의 유효시간은 늘리지 않아요.</p>}
    {d && <>
      {includeDeparture && <>
        {departureReady ? <>
          <p><strong>예상 출발 {departureDay}{departureTime}</strong></p>
          <p>접근 약 {Math.ceil(departure.approach_seconds/60)}분 · 설정 여유 {bufferText(departure.buffer_seconds)}</p>
          <p className="candidate-note">공급자 접근 도보에 개인 계수 {departure.applied_duration_factor}를 적용한 추정이에요.</p>
          {now>Date.parse(departure.recommended_departure_at) && <p>권장 출발 시각이 지났어요. 설정 여유를 확보할 수 있는지 다시 확인해주세요.</p>}
          {departure.slack_status==='below_buffer' && <p>지금 출발 기준 예상 여유가 설정한 여유보다 적어요.</p>}
        </> : <p role="status">{expired||now>Date.parse(departure?.valid_until)?'출발 정보가 만료됐어요. 이전 출발 시각은 사용하지 않아요.':departure?.status==='not_enough_time'||(departure?.valid_for_guidance&&!departureReachable)?'이 차량에 맞춰 출발하기에는 접근 시간이 부족해요.':'출발 시각을 계산할 접근 시간 또는 도착 근거가 부족해요.'}</p>}
      </>}
      {includeDeparture&&departure?.connection_status&&<>
        {expired||now>Date.parse(departure.valid_until)?<p>환승 정보가 만료됐어요. 이전 연결 시각은 사용하지 않아요.</p>:<>
          <p><strong>{connectionText[departure.connection_status]}</strong></p>
          {!!departure.transfers?.length&&<ul>{departure.transfers.map((c,index)=><li key={c.connection_id}>
            환승 {index+1} · {connectionText[c.feasibility]}
            {c.minimum_boarding_at&&<p>최소 승차 시각 {connectionTime(c.minimum_boarding_at)}</p>}
            {c.next_boarding_at&&<p>다음 차량 예상 {connectionTime(c.next_boarding_at)}</p>}
          </li>)}</ul>}
          {!!departure.transfers?.length&&<p>환승 도보와 차량 시각은 추정값이에요. 실제 환승 성공을 보장하지 않아요.</p>}
        </>}
      </>}
      {age!==null && <p className="candidate-note">{age}초 전 조회</p>}
      {!!candidates.length ? <>
        <p><strong>{d.timing_basis==='receipt_estimate'?'수신 기준 예상':'생성시각 확인된 예측'}</strong></p>
        <ul>{candidates.map((c,i)=><li key={c.candidate_id}>{i===0?'첫 차량':'다음 차량'} · 약 {Math.ceil((Date.parse(c.predicted_arrival_at)-now)/60000)}분 뒤 도착 예상</li>)}</ul>
        {d.timing_basis==='receipt_estimate' && <p>원천 갱신 지연은 확인되지 않았어요. 실제 도착과 다를 수 있어요.</p>}
        {!includeDeparture&&<p>개인 접근 시간을 반영한 출발 시각은 아직 계산하지 않아요.</p>}
      </> : <p role="status">{expired?empty.expired:empty[d.status] || '이전 도착 예상이 지났어요. 새 정보를 확인해주세요.'}</p>}
    </>}
  </section>;
}
