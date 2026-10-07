import React, { useEffect, useRef, useState } from 'react';
import { apiRequest, ApiError, isServerTime } from '../lib/api';
import MapPinPicker from './MapPinPicker';

export default function LocationConfirmation({ initialLocation, disabled, onDraft, onConfirmed, onAuthError }) {
  const [location, setLocation] = useState(initialLocation);
  const [phase, setPhase] = useState('ready');
  const [message, setMessage] = useState('');
  const [confirmation, setConfirmation] = useState(null);
  const pending = useRef(null);
  const callbacks = useRef({ onDraft, onConfirmed, onAuthError });
  callbacks.current = { onDraft, onConfirmed, onAuthError };
  const busy = disabled || phase === 'loading';
  useEffect(() => () => { pending.current?.abort(); }, []);
  useEffect(() => {
    if (!confirmation) return;
    const expire = () => { setConfirmation(null); callbacks.current.onConfirmed(null); setMessage('위치 확인이 만료됐어요. 핀 위치를 다시 확인해주세요.'); };
    const remaining = confirmation.deadline - Date.now();
    if (remaining <= 0) { expire(); return; }
    const timer = setTimeout(expire, remaining);
    return () => clearTimeout(timer);
  }, [confirmation]);
  function move(next) {
    pending.current?.abort(); pending.current = null;
    setLocation(next); setConfirmation(null); setMessage('핀 위치를 확인한 뒤 저장해주세요.'); setPhase('ready');
    callbacks.current.onDraft(); callbacks.current.onConfirmed(null);
  }
  async function confirm() {
    if (pending.current) return;
    const controller = new AbortController(); pending.current = controller;
    setPhase('loading'); setMessage(''); setConfirmation(null);
    callbacks.current.onDraft(); callbacks.current.onConfirmed(null);
    try {
      const csrf = await apiRequest('/api/v1/auth/csrf', { signal: controller.signal });
      if (typeof csrf.data?.csrf_token !== 'string') throw new ApiError('INVALID_RESPONSE');
      const response = await apiRequest('/api/v1/place-location-confirmations', { method:'POST', body:{location},
        headers:{'X-CSRF-Token':csrf.data.csrf_token}, signal:controller.signal });
      const data = response.data;
      if (typeof data?.confirmation_id !== 'string' || typeof data.location_address !== 'string'
        || !isServerTime(data.expires_at) || !isServerTime(response.meta.server_time)
        || data.location?.latitude !== location.latitude || data.location?.longitude !== location.longitude) throw new ApiError('INVALID_RESPONSE');
      if (controller.signal.aborted) return;
      const confirmed = { ...data, deadline: Date.now() + Date.parse(data.expires_at) - Date.parse(response.meta.server_time) };
      setConfirmation(confirmed); callbacks.current.onConfirmed(confirmed);
      setMessage('핀 위치를 확인했어요. ' + data.location_address + ' · 10분 안에 저장해주세요.'); setPhase('ready');
    } catch (error) {
      if (!controller.signal.aborted) {
        setMessage(error.message); setPhase('error');
        if (['AUTH_REQUIRED', 'SESSION_EXPIRED'].includes(error.code)) callbacks.current.onAuthError(error);
      }
    } finally { if (pending.current === controller) pending.current = null; }
  }
  return <div className="location-confirmation" aria-busy={phase === 'loading'}>
    <MapPinPicker location={location} onChange={move} disabled={busy} onAuthError={onAuthError}/>
    <div className="pin-actions"><button type="button" className="secondary" disabled={busy} onClick={() => move(initialLocation)}>처음 위치로</button><button type="button" className="primary" disabled={busy} onClick={confirm}>{phase === 'loading' ? '위치 확인 중…' : '핀 위치 확인'}</button></div>
    {message && <p role={phase === 'error' ? 'alert' : 'status'}>{message}</p>}
  </div>;
}
