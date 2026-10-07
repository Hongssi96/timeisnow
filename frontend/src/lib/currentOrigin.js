const messages = {
  GEO_DENIED: '위치 권한이 허용되지 않았어요. 지도에서 출발지를 선택해주세요.',
  GEO_TIMEOUT: '위치 확인이 늦어 중지했어요. 지도에서 선택하거나 다시 시도해주세요.',
  GEO_UNAVAILABLE: '현재 위치를 확인할 수 없어요. 지도에서 출발지를 선택해주세요.',
  GEO_UNSUPPORTED: '이 환경에서는 현재 위치를 사용할 수 없어요. 지도에서 출발지를 선택해주세요.',
};
export function getCurrentOrigin(signal) {
  return new Promise((resolve, reject) => {
    let settled = false;
    let timer;
    const finish = (value, error = false) => {
      if (settled) return;
      settled = true; clearTimeout(timer); signal?.removeEventListener('abort', cancel);
      (error ? reject : resolve)(value);
    };
    const fail = code => finish(Object.assign(new Error(messages[code]), { code }), true);
    const cancel = () => finish(new DOMException('Cancelled', 'AbortError'), true);
    if (signal?.aborted) { cancel(); return; }
    signal?.addEventListener('abort', cancel, { once: true });
    if (!window.isSecureContext || !navigator.geolocation) { fail('GEO_UNSUPPORTED'); return; }
    timer = setTimeout(() => fail('GEO_TIMEOUT'), 15000);
    try {
      navigator.geolocation.getCurrentPosition(position => {
        const { latitude, longitude, accuracy } = position.coords;
        if (!Number.isFinite(latitude) || Math.abs(latitude) > 90 || !Number.isFinite(longitude) || Math.abs(longitude) > 180
          || !Number.isFinite(accuracy) || accuracy < 0 || !Number.isFinite(position.timestamp)
          || !Number.isFinite(new Date(position.timestamp).getTime())) { fail('GEO_UNAVAILABLE'); return; }
        finish({ type: 'current_location', latitude, longitude, accuracy_meters: accuracy,
          captured_at: new Date(position.timestamp).toISOString() });
      }, error => fail(error.code === 1 ? 'GEO_DENIED' : error.code === 3 ? 'GEO_TIMEOUT' : 'GEO_UNAVAILABLE'),
      { enableHighAccuracy: true, maximumAge: 0, timeout: 10000 });
    } catch { fail('GEO_UNAVAILABLE'); }
  });
}
