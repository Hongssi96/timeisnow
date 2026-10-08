import React from 'react';

const reasons = {
  NO_ROUTE: '선택한 위치 사이의 대중교통 경로를 찾지 못했어요.',
  ENDPOINT_UNRESOLVED: '선택한 위치를 승하차 지점과 연결하지 못했어요. 가까운 정류장이나 역 주변으로 위치를 확인해주세요.',
  TRANSFER_LIMIT: '현재 지원하는 최대 2회 환승 안의 후보가 없어요.',
};

export default function JourneyUnavailable({ unsupported = false, codes = [], onOrigin, onDestination }) {
  const messages = [...new Set(codes)].filter(code => reasons[code]).map(code => reasons[code]);
  if (!messages.length || codes.some(code => !reasons[code])) messages.push('제공된 정보만으로 비교할 경로를 확인할 수 없어요. 위치를 확인하거나 잠시 후 다시 조회해주세요.');
  return <section className="card empty-state" role="status">
    <h2>{unsupported ? '서울·경기 안의 위치를 선택해주세요' : '지금 비교할 경로가 없어요'}</h2>
    {unsupported ? <p>현재 출발지와 도착지는 서울특별시·경기도만 지원해요.</p> : messages.map(message => <p key={message}>{message}</p>)}
    <div className="button-row"><button className="secondary" onClick={onOrigin}>출발지 다시 선택</button><button className="secondary" onClick={onDestination}>도착지 다시 선택</button></div>
  </section>;
}
