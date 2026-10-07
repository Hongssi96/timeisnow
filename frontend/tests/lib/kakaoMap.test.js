import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
beforeEach(()=>{vi.resetModules();delete window.kakao;});
afterEach(()=>{vi.useRealTimers();delete window.kakao;document.querySelectorAll('script[src^="https://dapi.kakao.com/v2/maps/sdk.js"]').forEach(script=>script.remove());});
describe('지도 SDK 로딩',()=>{
  it('동시 요청은 SDK 스크립트 한 개로 묶는다',async()=>{
    const {loadKakaoMap}=await import('../../src/lib/kakaoMap');
    const first=loadKakaoMap('public_synthetic');const second=loadKakaoMap('public_synthetic');
    expect(first).toBe(second);
    const script=document.querySelector('script');expect(document.querySelectorAll('script').length).toBe(1);
    window.kakao={maps:{Map:()=>{},load:callback=>callback()}};
    script.onload();expect(await first).toBe(window.kakao.maps);
  });
  it('로딩 오류 후 스크립트를 제거하고 재시도한다',async()=>{
    const {loadKakaoMap}=await import('../../src/lib/kakaoMap');const first=loadKakaoMap('public_synthetic');
    const failed=expect(first).rejects.toHaveProperty('code','MAP_UNAVAILABLE');
    document.querySelector('script').onerror();await failed;
    expect(document.querySelector('script')).toBeNull();
    const retry=loadKakaoMap('public_synthetic');
    window.kakao={maps:{Map:()=>{},load:callback=>callback()}};
    document.querySelector('script').onload();expect(await retry).toBe(window.kakao.maps);
  });
  it('10초 무응답을 성공으로 처리하지 않는다',async()=>{
    vi.useFakeTimers();const {loadKakaoMap}=await import('../../src/lib/kakaoMap');const request=loadKakaoMap('public_synthetic');
    const failed=expect(request).rejects.toHaveProperty('code','MAP_UNAVAILABLE');
    await vi.advanceTimersByTimeAsync(10000);await failed;expect(document.querySelector('script')).toBeNull();
  });
});
