import React from 'react';
import { Footprints } from 'lucide-react';

const missingMessages = {
  ACCESS_WALK_MISSING: '출발지에서 승차 지점까지 도보 구간이 부족해요.',
  TRANSFER_WALK_MISSING: '환승 지점 사이의 도보 구간이 부족해요.',
  EGRESS_WALK_MISSING: '하차 지점에서 목적지까지 도보 구간이 부족해요.',
};
const failures = {
  AI_OUTPUT_INVALID: 'AI 산정 결과를 검증하지 못했어요. 확인되지 않은 시간은 사용하지 않아요.',
  PROMPT_RESOURCE_INVALID: '개인 도보 산정을 준비하지 못했어요. 잠시 후 경로를 다시 확인해주세요.',
  PROVIDER_TIMEOUT: '시간 정보를 확인하는 응답이 늦어졌어요. 잠시 후 다시 확인해주세요.',
  PROVIDER_UNAVAILABLE: '시간 정보에 연결하지 못했어요. 잠시 후 다시 확인해주세요.',
};

export default function WalkingGuidance({ route, source = 'candidate', phase = 'needs_data', errorCode, announce = true }) {
  const codes = Array.isArray(route?.missing_segments) ? route.missing_segments : [];
  const indoor = ['SUBWAY', 'BUS_AND_SUBWAY'].includes(route?.type) || codes.includes('ENTRANCE_PLATFORM_UNCONFIRMED');
  const zero = Array.isArray(route?.ordered_legs) && route.ordered_legs.some(leg => leg.type === 'WALKING' && leg.seconds === 0);
  const messages = Object.entries(missingMessages).filter(([code]) => codes.includes(code)).map(([,text]) => text);
  const failed = phase === 'error', expired = phase === 'expired';
  return <div className="info-box walking-guidance" role={announce ? (failed ? 'alert' : 'status') : undefined}>
    <h3><Footprints size={19} aria-hidden="true"/>{failed ? '도보 시간을 확인하지 못했어요' : expired ? '도보 정보를 다시 확인해주세요' : '개인 도보 시간은 아직 확인 전이에요'}</h3>
    {failed ? <><p>{typeof errorCode === 'string' && Object.hasOwn(failures, errorCode) ? failures[errorCode] : '도보 정보를 확인하지 못했어요. 경로를 다시 확인해주세요.'}</p><p>조회 실패를 실제 이동 시간이나 출발 가능 여부로 판단하지 않아요.</p></> : expired ?
      <p>이전 경로의 시간을 사용하지 않아요. 최신 장소와 경로를 다시 선택해주세요.</p> : <>
        <p>{source === 'routine' ? '저장된 경로는 공급자 예상값이에요.' : '현재 후보는 공급자 예상값이에요.'} 개인 도보 AI 산정은 아직 실행하지 않았어요.</p>
        <ul><li>도보의 실제 범위와 진행 방향 확인이 필요해요.</li>
          {messages.map(message => <li key={message}>{message}</li>)}
          {source === 'routine' && <li>접근·환승·마지막 도보의 상세 근거는 현재 루틴 요약에 없어요.</li>}
          {zero && <li>공급자 도보0초 표기는 실제 이동이 없는 것으로 확정할 수 없어요.</li>}
          {indoor && <li>지하철 입구부터 승강장까지, 역 내부·환승 이동 시간이 확인되지 않았어요.</li>}
        </ul>
        <p>확인되지 않은 도보 시간은 임의로 채우지 않아요. 예상 출발은 제공된 접근 도보 시간과 차량 도착 근거가 있을 때 안내해요.</p>
      </>}
  </div>;
}
