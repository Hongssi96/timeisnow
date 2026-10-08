import React from 'react';
import { afterEach, expect, it, vi } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import PinPlaceSave from '../../src/components/PinPlaceSave';
import { apiRequest, ApiError } from '../../src/lib/api';
vi.mock('../../src/lib/api', async original => ({ ...await original(), apiRequest: vi.fn() }));
afterEach(() => vi.resetAllMocks());
const location = { latitude:37.5, longitude:127 };
const reply = data => ({ data, meta:{server_time:new Date().toISOString()}, status:201 });
const confirmation = () => reply({confirmation_id:'pin-confirmed', location, location_address:'서울 합성동', expires_at:new Date(Date.now()+599000).toISOString()});
const place = {place_id:'saved-pin',label:'출발지',location,location_version:1,location_source:'map_pin'};
function open(props={}) { return render(<PinPlaceSave location={location} initialLabel="출발지" onCreated={vi.fn()} onCancel={vi.fn()} {...props}/>); }
function setupConfirm() { apiRequest.mockResolvedValueOnce(reply({csrf_token:'csrf'})).mockResolvedValueOnce(confirmation()); }
it('saves chosen coordinates without search and notifies only after creation',async()=>{
  const created=vi.fn(); open({onCreated:created}); setupConfirm(); apiRequest.mockResolvedValueOnce(reply(place));
  expect(apiRequest).not.toHaveBeenCalled();
  await userEvent.click(screen.getByRole('button',{name:'저장하고 사용'}));
  await waitFor(()=>expect(created).toHaveBeenCalledWith(place));
  const call=apiRequest.mock.calls.find(([path])=>path==='/api/v1/places');
  expect(call[1].body).toEqual({source:'map_pin',label:'출발지',location,location_confirmation_id:'pin-confirmed'});
  expect(apiRequest.mock.calls.some(([path])=>path==='/api/v1/place-searches')).toBe(false);
});
it('retries uncertain saves with the same key/body and no second confirmation',async()=>{
  const created=vi.fn();open({onCreated:created}); setupConfirm();apiRequest.mockRejectedValueOnce(new ApiError('NETWORK_ERROR'));
  await userEvent.click(screen.getByRole('button',{name:'저장하고 사용'}));await screen.findByRole('alert');
  expect(created).not.toHaveBeenCalled();expect(screen.getByRole('textbox',{name:'장소 이름'}).disabled).toBe(true);
  apiRequest.mockResolvedValueOnce(reply({csrf_token:'new-csrf'})).mockResolvedValueOnce(reply(place));
  await userEvent.click(screen.getByRole('button',{name:'같은 요청으로 저장 재시도'}));await waitFor(()=>expect(created).toHaveBeenCalledOnce());
  const calls=apiRequest.mock.calls.filter(([path])=>path==='/api/v1/places');
  expect(calls[0][1].body).toEqual(calls[1][1].body);expect(calls[0][1].headers['Idempotency-Key']).toBe(calls[1][1].headers['Idempotency-Key']);
  expect(apiRequest.mock.calls.filter(([path])=>path==='/api/v1/place-location-confirmations')).toHaveLength(1);
});
it('aborts an in-flight save on exit and blocks cancel while saving',async()=>{
  const created=vi.fn(),cancel=vi.fn();const view=open({onCreated:created,onCancel:cancel});setupConfirm();
  let resolve;apiRequest.mockImplementationOnce(()=>new Promise(done=>{resolve=done;}));
  await userEvent.click(screen.getByRole('button',{name:'저장하고 사용'}));
  await waitFor(()=>expect(apiRequest.mock.calls.some(([path])=>path==='/api/v1/places')).toBe(true));
  expect(screen.getByRole('button',{name:'저장 취소'}).disabled).toBe(true);
  const signal=apiRequest.mock.calls.find(([path])=>path==='/api/v1/places')[1].signal;
  view.unmount();expect(signal.aborted).toBe(true);resolve(reply(place));await Promise.resolve();expect(created).not.toHaveBeenCalled();
});
it('requires explicit reconfirmation after expiry instead of retrying invalid confirmation forever',async()=>{
  open();setupConfirm();apiRequest.mockRejectedValueOnce(new ApiError('RESOURCE_NOT_FOUND'));
  await userEvent.click(screen.getByRole('button',{name:'저장하고 사용'}));await screen.findByRole('alert');
  expect(screen.getByRole('button',{name:'같은 요청으로 저장 재시도'}).disabled).toBe(true);
  await userEvent.click(screen.getByRole('button',{name:'위치 다시 확인'}));
  expect(screen.getByRole('textbox',{name:'장소 이름'}).disabled).toBe(false);
  expect(screen.getByRole('button',{name:'저장하고 사용'}).disabled).toBe(false);
});
it('reports expired login without sending a save request',async()=>{
  const auth=vi.fn(),created=vi.fn();open({onAuthError:auth,onCreated:created});
  apiRequest.mockRejectedValueOnce(new ApiError('SESSION_EXPIRED'));
  await userEvent.click(screen.getByRole('button',{name:'저장하고 사용'}));await waitFor(()=>expect(auth).toHaveBeenCalledOnce());
  expect(created).not.toHaveBeenCalled();expect(apiRequest.mock.calls.some(([path])=>path==='/api/v1/places')).toBe(false);
});
