import React, { useState } from 'react';
import MapPinPicker from './MapPinPicker';

export default function OriginReview({ draft, busy, expired, onAuthError, onChange, onConfirm }) {
  const [mapReady, setMapReady] = useState(false);
  return <div className="origin-review">
    <MapPinPicker location={draft.location} mapLabel="현재 위치 확인 지도" disabled={busy}
      description="핀을 보고 실제 출발 위치인지 확인해주세요. 핀을 옮기면 지도에서 직접 선택한 출발지로 바뀌어요."
      onAuthError={onAuthError} onReady={setMapReady} onChange={onChange}/>
    <p className="small muted">측정 시각 {new Date(draft.origin.captured_at).toLocaleString('ko-KR')} · 측정 정확도 약 {Math.round(draft.origin.accuracy_meters)}m</p>
    <p className="info-box">GPS 품질과 저장 장소 일치는 자동 판정하지 않아요. 이 핀이 실제 출발 위치인지 직접 확인해주세요.</p>
    {draft.quality.time_relation === 'future' && <p className="info-box">측정 시각이 서버 시각보다 앞서 있어요. 기기 시각과 실제 출발 위치를 확인해주세요.</p>}
    {expired && <p role="alert">출발지 확인 화면이 만료됐어요. 현재 위치를 다시 측정해주세요.</p>}
    <button className="primary wide" disabled={busy || expired || !mapReady} onClick={onConfirm}>이 위치가 실제 출발 위치예요</button>
  </div>;
}
