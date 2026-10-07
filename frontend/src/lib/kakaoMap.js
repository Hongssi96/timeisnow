import { ApiError } from './api';

let loading;
export function loadKakaoMap(key) {
  if (window.kakao?.maps?.Map) return Promise.resolve(window.kakao.maps);
  if (loading) return loading;
  loading = new Promise((resolve, reject) => {
    const script = document.createElement('script');
    let settled = false;
    const finish = (error) => {
      if (settled) return;
      settled = true; clearTimeout(timer); script.onload = null; script.onerror = null;
      if (error) { script.remove(); reject(new ApiError('MAP_UNAVAILABLE')); }
      else resolve(window.kakao.maps);
    };
    const timer = setTimeout(() => finish(true), 10000);
    script.src = 'https://dapi.kakao.com/v2/maps/sdk.js?autoload=false&appkey=' + encodeURIComponent(key);
    script.async = true;
    script.onerror = () => finish(true);
    script.onload = () => {
      if (!window.kakao?.maps?.load) return finish(true);
      window.kakao.maps.load(() => finish(!window.kakao?.maps?.Map));
    };
    document.head.appendChild(script);
  }).catch(error => { loading = null; throw error; });
  return loading;
}
