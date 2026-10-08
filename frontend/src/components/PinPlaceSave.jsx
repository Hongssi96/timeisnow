import React, { useEffect, useRef, useState } from 'react';
import { apiRequest, ApiError, isServerTime } from '../lib/api';

export default function PinPlaceSave({ location, initialLabel, onCreated, onCancel, onAuthError, onBusyChange }) {
  const [label, setLabel] = useState(initialLabel);
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState('');
  const [reconfirm, setReconfirm] = useState(false);
  const pending = useRef(null);
  const attempt = useRef(null);
  const input = useRef(null);
  useEffect(() => { input.current?.focus(); return () => { pending.current?.abort(); onBusyChange?.(false); }; }, []);
  async function save(event) {
    event.preventDefault();
    if (pending.current || !label.trim()) return;
    const controller = new AbortController(); pending.current = controller;
    setBusy(true); onBusyChange?.(true); setMessage('');
    try {
      const csrf = await apiRequest('/api/v1/auth/csrf', { signal: controller.signal });
      if (typeof csrf.data?.csrf_token !== 'string') throw new ApiError('INVALID_RESPONSE');
      const headers = { 'X-CSRF-Token': csrf.data.csrf_token };
      if (!attempt.current) {
        const response = await apiRequest('/api/v1/place-location-confirmations', {
          method: 'POST', body: { location }, headers, signal: controller.signal });
        const data = response.data;
        const remaining = Date.parse(data?.expires_at) - Date.parse(response.meta?.server_time);
        if (typeof data?.confirmation_id !== 'string' || typeof data.location_address !== 'string'
          || data.location?.latitude !== location.latitude || data.location?.longitude !== location.longitude
          || !isServerTime(data.expires_at) || !isServerTime(response.meta?.server_time)
          || remaining <= 0 || remaining > 600000) throw new ApiError('INVALID_RESPONSE');
        if (controller.signal.aborted) return;
        attempt.current = { key: crypto.randomUUID(), body: { source: 'map_pin', label: label.trim(),
          location: { ...location }, location_confirmation_id: data.confirmation_id } };
      }
      const response = await apiRequest('/api/v1/places', { method: 'POST', body: attempt.current.body,
        headers: { ...headers, 'Idempotency-Key': attempt.current.key }, signal: controller.signal });
      if (controller.signal.aborted) return;
      const place = response.data;
      if (response.status !== 201 || typeof place?.place_id !== 'string' || place.label !== attempt.current.body.label
        || place.location?.latitude !== location.latitude || place.location?.longitude !== location.longitude
        || place.location_source !== 'map_pin' || !Number.isInteger(place.location_version) || place.location_version < 1)
        throw new ApiError('INVALID_RESPONSE');
      onCreated(place);
    } catch (error) {
      if (controller.signal.aborted) return;
      if (['AUTH_REQUIRED', 'SESSION_EXPIRED'].includes(error.code)) { onAuthError?.(error); return; }
      setReconfirm(error.code === 'RESOURCE_NOT_FOUND');
      setMessage(error.code === 'RESOURCE_NOT_FOUND'
        ? '위치 확인이 만료됐거나 저장 정보를 찾을 수 없어요. 위치를 다시 확인해주세요.'
        : error.message || '저장하지 못했어요. 다시 시도해주세요.');
    } finally {
      if (pending.current === controller) { pending.current = null; setBusy(false); onBusyChange?.(false); }
    }
  }
  return <form className="place-form" onSubmit={save} aria-busy={busy}>
    <p className="info-box">지도에서 선택한 위치를 그대로 저장해요. 주소나 장소 이름으로 다시 검색할 필요가 없어요.</p>
    <label>장소 이름<input ref={input} value={label} maxLength={30} disabled={busy || Boolean(attempt.current)}
      onChange={event => setLabel(event.target.value)} required /></label>
    <p className="small muted">주소는 선택 위치의 법정동으로 표시해요. 정확한 위치는 지도 핀을 기준으로 해요.</p>
    {message && <p role="alert" className="info-box">{message}</p>}
    {busy && <p role="status">선택한 위치를 확인하고 저장하고 있어요.</p>}
    <div className="button-row">
      <button className="primary" disabled={busy || !label.trim() || reconfirm}>{attempt.current ? '같은 요청으로 저장 재시도' : '저장하고 사용'}</button>
      {reconfirm && <button type="button" className="secondary" disabled={busy} onClick={() => {
        attempt.current = null; setReconfirm(false); setMessage(''); }}>위치 다시 확인</button>}
      <button type="button" className="secondary" disabled={busy} onClick={onCancel}>저장 취소</button>
    </div>
  </form>;
}
