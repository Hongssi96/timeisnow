# 지금이니? — 출발지 선택 (F03-04)

- 기준: [Notion v0.38 5.2.1절](https://app.notion.com/p/3ebace1670c6806c8199cde33ebfbdfa), 2026-10-07 저장 재조회 확인.
- 범위: 다른 곳에서 출발 → 로그인 확인 → 현재 위치1회/지도 핀/본인 저장 장소 선택 → 서버 확인 → 화면 메모리. 실제 경로/출발 시간은 F04~07 후속이다.

## POST /api/v1/origin-validations

로그인 쿠키·Origin/CSRF·no-store, 공통 data/meta 또는 error/meta. 사용자당10회/분과 Retry-After, 공급자 호출 전에 소비하여 실패도 포함한다. 장소/루틴/검색 자원을 만들지 않는 입력 확인 API로 생성 멱등 저장 대상이 아니다.

| origin.type | 입력 | 검증 |
| --- | --- | --- |
| current_location | latitude/longitude, accuracy_meters, captured_at | 유한 좌표 범위, 유한 정확도>=0, 시간대 있는 ISO8601 문자열을 UTC로 정규화, 서울/경기 지역 확인 |
| map_pin | latitude/longitude | 좌표 범위·서울/경기 지역 확인 |
| saved_place | place_id, location_version? | 본인/존재404·위치 버전 충돌409. 현재 저장 이름·출입구 위치, 공급자 재호출 없음 |

알 수 없는 종류/필드·잘못된 형식422 VALIDATION_ERROR. 지원지역 밖/바다422 UNSUPPORTED_REGION, 공급자 실패503 PROVIDER_UNAVAILABLE/잘못된 응답502 PROVIDER_RESPONSE_INVALID. 인증401·CSRF403·DB503·제한429은 기존 공통 계약이다.

200 data는 origin, label, location, location_address, expires_at, quality_status. saved_place origin은 현재 location_version을 포함한다. label은 현재 위치/지도 선택 위치/현재 저장 이름. expires_at은 서버 확인후600초, 프론트는 meta.server_time과 차이로 만료를 처리한다.

```json
{"origin":{"type":"current_location","latitude":37.5665,"longitude":126.978,"accuracy_meters":10,"captured_at":"2026-10-07T11:00:00+09:00"}}
```

위 공개 좌표 합성 입력은 current_location 그대로, captured_at=2026-10-07T02:00:00Z·quality_status=pending으로 반환한다. F03-04는 측정치 형식/전달만 구현하며 최신성/정확도 임계값·미래 시각·저장 장소/출입구 일치 여부는 F03-05에서 처리한다. 600초 선택 유효기간은 GPS 최신성 보장이 아니다. 근처라는 이유로 저장 집으로 변환하지 않는다.

## 화면과 개인정보

- 명시 버튼 클릭 후 인증을 재확인하고 getCurrentPosition 한 번 요청. high accuracy, maximumAge=0, native timeout10초, 권한 대기 포함 앱 전체15초. watchPosition/자동 요청/백그라운드 추적 없음.
- 거절·시간 초과·위치 불가·HTTPS/API 미지원이면 지도 선택/현재 위치 재시도 제공. 화면 이탈/방법 변경은 요청 취소, 늦은 GPS 콜백 무시.
- 지도 시작은 첫 본인 저장 장소 또는 공개 서울시청 중심이며 현재 위치로 간주하지 않는다. 지도 클릭·핀 이동·5m 방향 버튼으로 직접 선택한 뒤 확인한다. 기존 MapPinPicker·공개 SDK 키/서버 REST 키 분리를 유지한다.
- 저장 장소 목록은 기존20개 기본/더보기·빈목록·실패 재시도. 위치 버전 충돌/삭제 오류에는 이전 목록을 지우고 다시 확인한다.
- 출발지를 선택하면 기존 예시 경로·출발 시간·이동 시작을 숨기고 준비 중 카드를 제공. 품질pending은 실제 경로 계산 가능 상태가 아니다.
- 선택은 App 메모리에서만 유지한다. 새로고침/계정 모달/인증 만료 인지 시 제거, 600초 후 재선택 안내. DB/URL/localStorage/로그에 GPS 좌표·주소·정확도/시각 원문을 저장하지 않는다. 기존HMAC 요청 제한/세션 갱신만 기록한다.
- 선택 위치는 공식 카카오 지도 표시·지원지역 확인에 사용하며 AI에 전달하지 않는다. 후속 경로 API에서는 인증·소유권·위치 품질을 다시 확인한다.

## 실제 검증과 범위

백엔드94개·프론트73개·빌드, 실제 PostgreSQL/ASGI 소유권·버전/삭제·쿼터·로그 비노출 및 공개 좌표 로컬 HTTP200/no-store 확인. 실제 지도 방향 버튼·키보드 선택·1440×1000/390×844 화면과 새로고침 초기화 확인. GPS 성공/거절/시간 초과/미지원/취소는 모의 테스트이며 실제 사용자 위치/권한 승인·실제 휴대전화 측정은 수행하지 않았다. 상세 development_log.md의 F03-04 기록.
