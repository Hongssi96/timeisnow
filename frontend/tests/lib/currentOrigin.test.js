import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { getCurrentOrigin } from '../../src/lib/currentOrigin';
let success, failure;
beforeEach(() => {
  vi.stubGlobal('isSecureContext', true);
  Object.defineProperty(navigator, 'geolocation', { configurable: true, value: { getCurrentPosition: vi.fn((ok, fail) => {success=ok;failure=fail;}) } });
});
afterEach(() => { vi.useRealTimers(); vi.unstubAllGlobals(); delete navigator.geolocation; });
describe('one explicit device position', () => {
  it('requests fresh high accuracy and forwards measured metadata', async () => {
    const promise=getCurrentOrigin();
    expect(navigator.geolocation.getCurrentPosition).toHaveBeenCalledOnce();
    expect(navigator.geolocation.getCurrentPosition.mock.calls[0][2]).toEqual({enableHighAccuracy:true,maximumAge:0,timeout:10000});
    success({coords:{latitude:37.5,longitude:127,accuracy:12},timestamp:Date.parse('2026-10-07T01:00:00Z')});
    expect(await promise).toEqual({type:'current_location',latitude:37.5,longitude:127,accuracy_meters:12,captured_at:'2026-10-07T01:00:00.000Z'});
  });
  it.each([[1,'GEO_DENIED'],[2,'GEO_UNAVAILABLE'],[3,'GEO_TIMEOUT']])('maps device error %s without exposing raw messages', async (code, expected) => {
    const promise=getCurrentOrigin(); const check=expect(promise).rejects.toMatchObject({code:expected});
    failure({code,message:'private device message'}); await check;
  });
  it('bounds permission waiting to 15 seconds and ignores late success', async () => {
    vi.useFakeTimers();const promise=getCurrentOrigin();const check=expect(promise).rejects.toMatchObject({code:'GEO_TIMEOUT'});
    await vi.advanceTimersByTimeAsync(15000);await check;
    success({coords:{latitude:37.5,longitude:127,accuracy:12},timestamp:Date.now()});
    expect(vi.getTimerCount()).toBe(0);
  });
  it('cancels while native permission remains pending', async () => {
    const controller=new AbortController();const promise=getCurrentOrigin(controller.signal);
    const check=expect(promise).rejects.toMatchObject({name:'AbortError'});controller.abort();await check;
    failure({code:1});
  });
  it('rejects insecure or missing APIs before requesting position', async () => {
    vi.stubGlobal('isSecureContext',false);await expect(getCurrentOrigin()).rejects.toMatchObject({code:'GEO_UNSUPPORTED'});
    expect(navigator.geolocation.getCurrentPosition).not.toHaveBeenCalled();
    vi.stubGlobal('isSecureContext',true);delete navigator.geolocation;
    await expect(getCurrentOrigin()).rejects.toMatchObject({code:'GEO_UNSUPPORTED'});
  });
  it('rejects malformed measured positions', async () => {
    const promise=getCurrentOrigin();const check=expect(promise).rejects.toMatchObject({code:'GEO_UNAVAILABLE'});
    success({coords:{latitude:91,longitude:127,accuracy:-1},timestamp:NaN});await check;
  });
});
