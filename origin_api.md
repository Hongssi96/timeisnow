# 지금이니? — 출발지 선택 (F03-04·F03-05a)

- 기준: [Notion v0.39 5.2.1~2절](https://app.notion.com/p/3ebace1670c6806c8199cde33ebfbdfa), 2026-10-07 저장 재조회 확인.
- 범위: 다른 곳에서 출발 → 로그인 확인 → 현재 위치1회/지도 핀/본인 저장 장소 선택 → 서버 확인 → 화면 메모리. 실제 경로/출발 시간은 F04~07 후속이다.

## POST /api/v1/origin-validations

로그인 쿠키·Origin/CSRF·no-store, 공통 data/meta 또는 error/meta. 사용자당10회/분과 Retry-After, 공급자 호출 전에 소비하여 실패도 포함한다. 장소/루틴/검색 자원을 만들지 않는 입력 확인 API로 생성 멱등 저장 대상이 아니다.

| origin.type | 입력 | 검증 |
| --- | --- | --- |
| current_location | latitude/longitude, accuracy_meters, captured_at | 유한 좌표 범위, 유한 정확도>=0, 시간대 있는 ISO8601 문자열을 UTC로 정규화, 서울/경기 지역 확인 |
| map_pin | latitude/longitude | 좌표 범위·서울/경기 지역 확인 |
| saved_place | place_id, location_version? | 본인/존재404·위치 버전 충돌409. 현재 저장 이름·출입구 위치, 공급자 재호출 없음 |

알 수 없는 종류/필드·잘못된 형식422 VALIDATION_ERROR. 지원지역 밖/바다422 UNSUPPORTED_REGION, 공급자 실패503 PROVIDER_UNAVAILABLE/잘못된 응답502 PROVIDER_RESPONSE_INVALID. 인증401·CSRF403·DB503·제한429은 기존 공통 계약이다.

200 data는 origin, label, location, location_address, expires_at, quality_status, quality, place_match. saved_place origin은 현재 location_version을 포함한다. label은 현재 위치/지도 선택 위치/현재 저장 이름. expires_at은 서버 확인후600초, 프론트는 meta.server_time과 차이로 만료를 처리한다.

## F03-05a 수동 확인 — 사용자 결정 2026-10-07

GPS 수치는 보류하고 수동 확인만 구현한다. 경과 시간/정확도/미래 시각 허용폭·저장 장소 근접 반경을 임의로 정하지 않는다. 형식·유한 값·서울/경기 검사는 기존대로 유지한다.

- current_location에 location_confirmed 선택 boolean(default false, 엄격한 자료형)을 추가한다. false는 pending, true는 user_confirmed. true는 사용자 보고이며 서버가 실제 GPS 정확성을 검증했다는 뜻이 아니다. 지도/저장 장소에 이 필드를 넣으면422.
- quality.assessment: 현재 위치 unassessed, 지도/저장 장소 user_selected. quality.confirmation: 현재 false required/true reported, 나머지 not_applicable. quality.numeric_policy는 모두 deferred.
- quality.time_relation: 현재 captured_at이 서버 처리 시각보다 앞서면 future, 나머지는 past_or_present. 지도/저장 장소는 not_applicable. 자동 거절/승인 기준으로 사용하지 않는다.
- place_match.status: 현재/지도 unconfirmed, 저장 장소 selected_by_user. 저장 장소 선택도 실제 현장/출입구와 GPS가 일치한다는 보증이 아니다.
- 현재 위치 첫 응답은 지도·시각·정확도 미리보기만 표시한다. 지도 로딩 성공 후 ‘이 위치가 실제 출발 위치예요’를 누르면 동일 측정치에 location_confirmed:true를 보내고 성공 응답 후 적용한다. 확인 실패/잘못된 응답은 적용하지 않는다.
- 핀 이동은 map_pin 수동 선택으로 전환한다. 방법 전환/재측정/화면 이탈/인증 만료는 확인 초안을 제거한다. 600초 초안 만료 시 재측정을 요구하며 자동으로 GPS를 다시 요청하지 않는다. 확인 요청도 기존10회/분 제한에 포함한다.
- 기존 클라이언트의 필드 없는 요청은 false/pending으로 호환한다. 새 응답 필드는 추가이며 user_confirmed는 true를 보낸 새 요청에서만 발생한다. 후속 경로 API는 품질/소유권을 다시 검사해야 한다.
- GPS 수치/자동 일치 판정은 F03-05 보류이며 상위 TODO를 완료로 표시하지 않는다.

```json
{"origin":{"type":"current_location","latitude":37.5665,"longitude":126.978,"accuracy_meters":10,"captured_at":"2026-10-07T11:00:00+09:00"}}
```

위 공개 좌표 합성 입력은 current_location 그대로, captured_at=2026-10-07T02:00:00Z·location_confirmed=false·quality_status=pending으로 반환한다. location_confirmed:true를 추가해 다시 보내면 user_confirmed이며 quality.assessment=unassessed·place_match.status=unconfirmed를 유지한다. 600초 선택 유효기간은 GPS 최신성 보장이 아니다. 근처라는 이유로 저장 집으로 변환하지 않는다.

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

## F03-02a 지도 핀 저장 확장 — 2026-10-08

OriginSelector의 지도 선택에서 핀을 직접 정한 후 저장하고 사용을 제공한다. 기존 map_pin 단발 origin-validations 흐름은 유지한다. 명시 저장은 place-location-confirmations와 POST places source=map_pin을 거쳐 기존 created 흐름으로 saved_place 검증/자동 선택한다. 이미 비교 화면에서 선택한 지도 지점도 새 장소 저장에 initialLocation으로 전달해 재검색하지 않는다. 생성 실패/선택 검증 실패를 구분하고 재시도 시 중복 저장하지 않는다. Notion v0.51·place_api.md 기준.
