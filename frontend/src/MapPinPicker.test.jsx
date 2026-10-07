import React from 'react';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import MapPinPicker from './MapPinPicker';
import { apiRequest, ApiError } from './api';
import { loadKakaoMap } from './kakaoMap';
vi.mock('./api',async original=>({...await original(),apiRequest:vi.fn()}));
vi.mock('./kakaoMap',()=>({loadKakaoMap:vi.fn()}));
const listeners=new Map();
class Point {constructor(lat,lon){this.lat=lat;this.lon=lon;}getLat(){return this.lat;}getLng(){return this.lon;}}
const map={relayout:vi.fn(),setDraggable:vi.fn(),setZoomable:vi.fn(),panTo:vi.fn()};
const marker={setPosition:vi.fn(),setDraggable:vi.fn(),setMap:vi.fn(),getPosition:()=>new Point(37.501,127)};
const maps={LatLng:Point,Map:vi.fn(function(){return map;}),Marker:vi.fn(function(){return marker;}),
  event:{addListener:vi.fn((target,name,callback)=>listeners.set(name,callback)),removeListener:vi.fn()}};
beforeEach(()=>{
  vi.stubGlobal('ResizeObserver',class {observe(){}disconnect(){}});
  window.kakao={maps};apiRequest.mockResolvedValue({data:{javascript_key:'public_synthetic'}});loadKakaoMap.mockResolvedValue(maps);
});
afterEach(()=>{vi.resetAllMocks();vi.unstubAllGlobals();delete window.kakao;listeners.clear();});
describe('지도 핀',()=>{
  it('방향 버튼·지도 클릭·마커 이동을 좌표 변경으로 전달한다',async()=>{
    const change=vi.fn();const view=render(<MapPinPicker location={{latitude:37.5,longitude:127}} onChange={change}/>);
    await userEvent.click(await screen.findByRole('button',{name:'북쪽 5m'}));
    expect(change.mock.calls[0][0].latitude).toBeGreaterThan(37.5);
    listeners.get('click')({latLng:new Point(37.502,127.001)});
    expect(change).toHaveBeenLastCalledWith({latitude:37.502,longitude:127.001});
    listeners.get('dragend')();expect(change).toHaveBeenLastCalledWith({latitude:37.501,longitude:127});
    view.unmount();expect(maps.event.removeListener).toHaveBeenCalledTimes(2);expect(marker.setMap).toHaveBeenCalledWith(null);
  });
  it('SDK 실패 시 재시도 후 지도를 표시한다',async()=>{
    loadKakaoMap.mockRejectedValueOnce(new ApiError('MAP_UNAVAILABLE')).mockResolvedValueOnce(maps);
    render(<MapPinPicker location={{latitude:37.5,longitude:127}} onChange={vi.fn()}/>);
    await userEvent.click(await screen.findByRole('button',{name:'지도 다시 불러오기'}));
    expect(await screen.findByRole('button',{name:'북쪽 5m'})).toBeTruthy();
  });
  it('비활성 중에는 지도 클릭/마커 변경을 반영하지 않는다',async()=>{
    const change=vi.fn();render(<MapPinPicker disabled location={{latitude:37.5,longitude:127}} onChange={change}/>);
    expect((await screen.findByRole('button',{name:'북쪽 5m'})).disabled).toBe(true);
    expect(map.setDraggable).toHaveBeenCalledWith(false);expect(map.setZoomable).toHaveBeenCalledWith(false);
    listeners.get('click')({latLng:new Point(37.502,127.001)});listeners.get('dragend')();expect(change).not.toHaveBeenCalled();
  });
});
