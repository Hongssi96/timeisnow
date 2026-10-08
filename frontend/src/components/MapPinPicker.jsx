import React, { useEffect, useRef, useState } from 'react';
import { apiRequest, ApiError } from '../lib/api';
import { loadKakaoMap } from '../lib/kakaoMap';

export default function MapPinPicker({ location, onChange, disabled = false, onAuthError, onReady, description = '지도에서 출입구를 누르거나 핀을 옮겨주세요. 카카오 지도에 선택 위치가 표시돼요.', mapLabel = '출입구 위치 지도' }) {
  const host = useRef(null);
  const mapRef = useRef(null);
  const markerRef = useRef(null);
  const changeRef = useRef(onChange);
  const authErrorRef = useRef(onAuthError);
  const readyRef = useRef(onReady);
  const pointRef = useRef(location);
  const disabledRef = useRef(disabled);
  const [phase, setPhase] = useState('loading');
  const [retry, setRetry] = useState(0);
  changeRef.current = onChange; authErrorRef.current = onAuthError;
  readyRef.current = onReady;
  pointRef.current = location; disabledRef.current = disabled;

  useEffect(() => {
    const controller = new AbortController();
    let dispose = () => {};
    setPhase('loading');
    readyRef.current?.(false);
    (async () => {
      try {
        const response = await apiRequest('/api/v1/map-config', { signal: controller.signal });
        if (typeof response.data?.javascript_key !== 'string' || !response.data.javascript_key) throw new ApiError('MAP_UNAVAILABLE');
        const maps = await loadKakaoMap(response.data.javascript_key);
        if (controller.signal.aborted) return;
        const point = new maps.LatLng(pointRef.current.latitude, pointRef.current.longitude);
        const map = new maps.Map(host.current, { center: point, level: 3 });
        map.setDraggable(!disabledRef.current); map.setZoomable(!disabledRef.current);
        const marker = new maps.Marker({ position: point, map, draggable: !disabledRef.current });
        mapRef.current = map; markerRef.current = marker;
        const select = latLng => {
          if (disabledRef.current) return;
          marker.setPosition(latLng);
          changeRef.current({ latitude: latLng.getLat(), longitude: latLng.getLng() });
        };
        const click = event => select(event.latLng);
        const drag = () => select(marker.getPosition());
        maps.event.addListener(map, 'click', click); maps.event.addListener(marker, 'dragend', drag);
        const observer = new ResizeObserver(() => { map.relayout(); });
        observer.observe(host.current);
        dispose = () => {
          observer.disconnect(); maps.event.removeListener(map, 'click', click); maps.event.removeListener(marker, 'dragend', drag);
          marker.setMap(null); mapRef.current = null; markerRef.current = null;
          host.current?.replaceChildren();
        };
        setPhase('ready');
        readyRef.current?.(true);
      } catch (error) {
        if (!controller.signal.aborted) {
          setPhase('error');
          if (['AUTH_REQUIRED', 'SESSION_EXPIRED'].includes(error.code)) authErrorRef.current?.(error);
        }
      }
    })();
    return () => { controller.abort(); dispose(); };
  }, [retry]);
  useEffect(() => {
    const marker = markerRef.current;
    if (!marker) return;
    const point = new window.kakao.maps.LatLng(location.latitude, location.longitude);
    marker.setPosition(point); marker.setDraggable(!disabled);
    mapRef.current.setDraggable(!disabled); mapRef.current.setZoomable(!disabled);
  }, [location, disabled]);

  function move(north, east) {
    const next = { latitude: location.latitude + north / 111320,
      longitude: location.longitude + east / (111320 * Math.cos(location.latitude * Math.PI / 180)) };
    onChange(next); mapRef.current?.panTo(new window.kakao.maps.LatLng(next.latitude, next.longitude));
  }
  return <div className="map-picker">
    <p className="small muted">{description}</p>
    <div ref={host} className="place-map" role="region" aria-label={mapLabel} aria-busy={phase === 'loading'}/>
    {phase === 'loading' && <p role="status">지도를 불러오고 있어요.</p>}
    {phase === 'error' && <div className="info-box" role="alert">지도를 불러올 수 없어요. 잠시 후 다시 시도해주세요.<button type="button" className="secondary wide" onClick={() => setRetry(value => value + 1)} disabled={disabled}>지도 다시 불러오기</button></div>}
    {phase === 'ready' && <div className="pin-controls" role="group" aria-label="핀 위치 조정">{[['북쪽',5,0],['남쪽',-5,0],['서쪽',0,-5],['동쪽',0,5]].map(([name,north,east]) => <button className="secondary" key={name} type="button" disabled={disabled} onClick={() => move(north,east)}>{name} 5m</button>)}</div>}
  </div>;
}
