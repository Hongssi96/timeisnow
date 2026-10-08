import { useEffect, useRef, useState } from 'react';
import { apiRequest, ApiError, isServerTime } from './api';
import { safeJourneyId } from './journeys';

export const WEEKDAYS = ['월', '화', '수', '목', '금', '토', '일'];
export const placeLabel = value => value ? value.label : '삭제된 장소';
export const needsRoutineRecovery = routine => routine.status === 'needs_attention' || !routine.origin_place || !routine.destination_place;
export function routineRecoveryMessage(routine) {
  const missing=[!routine.origin_place&&'출발',!routine.destination_place&&'도착'].filter(Boolean);
  return missing.length ? `${missing.join('·')} 장소가 삭제됐어요. 저장 장소를 다시 선택하고 경로를 조회해주세요.`
    : '장소 위치·출입구 또는 경로 정보를 다시 확인해야 해요. 현재 장소로 경로를 다시 조회해주세요.';
}
const place = value => value === null || (safeJourneyId(value?.place_id) && ['label', 'name', 'address'].every(key => typeof value[key] === 'string'));
export function validRoutine(value) {
  return safeJourneyId(value?.routine_id) && typeof value.name === 'string' && value.name.trim().length >= 1 && value.name.length <= 30
    && place(value.origin_place) && place(value.destination_place)
    && safeJourneyId(value.route?.journey_plan_id) && ['BUS', 'SUBWAY', 'BUS_AND_SUBWAY', 'WALKING'].includes(value.route.type)
    && Number.isSafeInteger(value.route.total_seconds) && value.route.total_seconds >= 0
    && Number.isInteger(value.route.transfer_count) && value.route.transfer_count >= 0 && value.route.transfer_count <= 2
    && Array.isArray(value.weekdays) && value.weekdays.length >= 1 && value.weekdays.length <= 7
    && new Set(value.weekdays).size === value.weekdays.length && value.weekdays.every(day => Number.isInteger(day) && day >= 1 && day <= 7)
    && (value.target_arrival_local_time === null || typeof value.target_arrival_local_time === 'string' && /^([01]\d|2[0-3]):[0-5]\d$/.test(value.target_arrival_local_time))
    && value.timezone === 'Asia/Seoul' && ['active', 'needs_attention'].includes(value.status)
    && Number.isInteger(value.version) && value.version >= 1 && isServerTime(value.created_at) && isServerTime(value.updated_at);
}
export function useRoutines(enabled, revision) {
  const [state, setState] = useState({ phase: 'loading', items: [], next: null });
  const pending = useRef(null);
  async function load(more = false) {
    if (more && pending.current) return;
    pending.current?.abort();
    const controller = new AbortController(); pending.current = controller;
    const cursor = more ? state.next : null;
    if (more && !cursor) { pending.current = null; return; }
    setState(previous => ({ ...previous, phase: more ? 'more' : 'loading', ...(more ? {} : { items: [], next: null }), message: null }));
    try {
      const response = await apiRequest('/api/v1/routines' + (cursor ? '?cursor=' + encodeURIComponent(cursor) : ''), { signal: controller.signal });
      if (controller.signal.aborted) return;
      const data = response.data;
      if (!Array.isArray(data?.items) || data.items.length > 20 || !data.items.every(validRoutine)
        || new Set(data.items.map(item => item.routine_id)).size !== data.items.length
        || !(data.next_cursor === null || safeJourneyId(data.next_cursor)) || cursor !== null && data.next_cursor === cursor
        || data.next_cursor !== null && data.items.at(-1)?.routine_id !== data.next_cursor) throw new ApiError('INVALID_RESPONSE');
      setState(previous => ({ phase: 'ready', items: more ? [...previous.items, ...data.items.filter(item => !previous.items.some(existing => existing.routine_id === item.routine_id))] : data.items, next: data.next_cursor }));
    } catch (error) {
      if (!controller.signal.aborted) setState(previous => ({ ...previous,
        phase: ['AUTH_REQUIRED', 'SESSION_EXPIRED'].includes(error.code) ? 'anonymous' : 'error',
        ...(['AUTH_REQUIRED', 'SESSION_EXPIRED'].includes(error.code) ? { items: [], next: null } : {}), message: error.message }));
    } finally { if (pending.current === controller) pending.current = null; }
  }
  useEffect(() => {
    if (enabled) load();
    return () => { pending.current?.abort(); pending.current = null; };
  }, [enabled, revision]);
  function clear() { pending.current?.abort(); pending.current = null; setState({ phase: 'anonymous', items: [], next: null }); }
  return { state, load, clear };
}
