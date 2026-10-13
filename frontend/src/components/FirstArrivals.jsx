import React, { useEffect, useState } from 'react';
import { Clock3 } from 'lucide-react';
import { getFirstArrivals } from '../lib/arrivals';

const empty = { mapping_required:'이 경로의 버스 정류소와 방향을 아직 확인하지 못했어요.', unsupported:'이 첫 탑승 수단의 도착 조회는 아직 지원하지 않아요.', no_arrivals:'현재 제공된 도착 후보가 없어요.', insufficient_data:'현재 도착 시간을 추정할 근거가 부족해요.', expired:'도착 정보가 만료됐어요. 이전 예상 시간은 사용하지 않아요.' };

export default function FirstArrivals({ searchId, candidateId }) {
  const [state, setState] = useState({ phase:'loading' });
  const [tick, setTick] = useState(0);
  useEffect(() => {
    let disposed=false, controller=null, sequence=0, busy=false, terminal=false;
    setState({ phase:'loading' });
    async function load() {
      if (disposed || busy || terminal || document.hidden) return;
      busy=true;controller=new AbortController();const seq=++sequence;
      try {
        const response=await getFirstArrivals(searchId,candidateId,controller.signal);
        if (!disposed && seq===sequence) setState({ phase:'ready', evidence:response.data, serverAt:Date.parse(response.meta.server_time), sampledAt:performance.now() });
      } catch (error) {
        if (!disposed && seq===sequence && error.name!=='AbortError') {
          terminal=['AUTH_REQUIRED','SESSION_EXPIRED','RESOURCE_NOT_FOUND','VERSION_CONFLICT','INVALID_RESPONSE'].includes(error.code);
          setState(old=>terminal ? {phase:'blocked',error:error.code} : {...old,phase:old.evidence?'ready':'error',error:true});
        }
      } finally { if (seq===sequence) busy=false; }
    }
    function visibility() {
      if (document.hidden) { sequence++;controller?.abort();busy=false; }
      else load();
    }
    load();const polling=setInterval(load,60000);const clock=setInterval(()=>setTick(t=>t+1),1000);
    document.addEventListener('visibilitychange',visibility);
    return ()=>{disposed=true;sequence++;controller?.abort();clearInterval(polling);clearInterval(clock);document.removeEventListener('visibilitychange',visibility);};
  }, [searchId,candidateId]);
  const d=state.evidence;
  const now=d ? state.serverAt+Math.max(0,performance.now()-state.sampledAt) : 0;
  const expired=d && now>Date.parse(d.expires_at);
  const candidates=d?.valid_for_guidance && !expired ? d.candidates.filter(c=>c.predicted_arrival_at && Date.parse(c.predicted_arrival_at)>now) : [];
  const age=d?.received_at ? Math.max(0,Math.floor((now-Date.parse(d.received_at))/1000)) : null;
  return <section className="info-box walking-guidance first-arrivals" aria-label="첫 탑승 도착 정보">
    <h3><Clock3 size={18}/>첫 탑승 도착 예상</h3>
    {state.phase==='loading' && <p role="status">도착 정보를 확인하고 있어요.</p>}
    {state.phase==='blocked' && <p role="alert">{['AUTH_REQUIRED','SESSION_EXPIRED'].includes(state.error)?'로그인 후 다시 확인해주세요.':'경로를 다시 검색해 도착 정보를 확인해주세요.'}</p>}
    {state.error && state.phase!=='blocked' && <p role="alert">도착 정보를 다시 조회하지 못했어요. 이전 정보의 유효시간은 늘리지 않아요.</p>}
    {d && <>
      {age!==null && <p className="candidate-note">{age}초 전 조회</p>}
      {!!candidates.length ? <>
        <p><strong>{d.timing_basis==='receipt_estimate'?'수신 기준 예상':'생성시각 확인된 예측'}</strong></p>
        <ul>{candidates.map((c,i)=><li key={c.candidate_id}>{i===0?'첫 차량':'다음 차량'} · 약 {Math.ceil((Date.parse(c.predicted_arrival_at)-now)/60000)}분 뒤 도착 예상</li>)}</ul>
        {d.timing_basis==='receipt_estimate' && <p>원천 갱신 지연은 확인되지 않았어요. 실제 도착과 다를 수 있어요.</p>}
        <p>개인 접근 시간을 반영한 출발 시각은 아직 계산하지 않아요.</p>
      </> : <p role="status">{expired?empty.expired:empty[d.status] || '이전 도착 예상이 지났어요. 새 정보를 확인해주세요.'}</p>}
    </>}
  </section>;
}
