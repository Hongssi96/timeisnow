# 지금이니? — 고정 장소 검색·저장·지도 핀 (F03-01~02)

- 기준: [Notion API v0.36](https://app.notion.com/p/3ebace1670c6806c8199cde33ebfbdfa) 02절·5.1.1~2절, 2026-10-07 저장 재조회 확인.
- 범위: 주소/키워드 검색 → 후보 선택 → 지도 핀 확인·출입구 설명 → 집·회사 등 이름 저장 → 본인 목록/상세 및 위치·출입구 수정. 라벨 수정/삭제·현재 위치는 F03-03~05 후속이다.

React ‘내 설정 → 내 장소’에서 로그인 후 등록한다. 실제 저장 장소는 PostgreSQL 원본이며 화면 체험 루틴의 가상 집/회사에는 자동 적용하지 않는다. 계정 모달을 열면 장소 카드와 요청을 제거하고 닫을 때 다시 조회하여 이전 계정의 화면 자료를 재사용하지 않는다.

## API

| API | 입력/응답 | 핵심 규칙 |
| --- | --- | --- |
| POST /api/v1/place-searches | query(공백 제거 후1~100자) → search_id/expires_at/candidates | 카카오 주소·키워드 각각 첫10건, 서울/경기 주소만, 중복 제거 최대20건, 사용자당10회/분 |
| POST /api/v1/places | label(1~30자), location, search_id, candidate_id, entrance_ref(null), location_confirmation_id?, entrance_note? →201 장소 | 본인 후보/600초 만료/좌표 일치 또는 본인 핀 확인. 선택 Idempotency-Key로24시간 중복 생성 방지 |
| GET /api/v1/places | limit(기본20/최대100), cursor? → items/next_cursor | 본인 UUID 내림차순 목록, 타인/없는 cursor404 |
| GET /api/v1/places/{place_id} | →200 장소 | 본인만, 타인/없는/잘못된 ID404 |

장소 객체: place_id, label, name, address, location(latitude/longitude), entrance_ref(null), version(1). 후보 객체: candidate_id, name, address, location. 서버가 후보/검색 ID를 발급하며 프론트는 후보 좌표를 바꾸지 않는다.

F03-02부터 장소 응답에 entrance_note(null/string), location_source(search/map_pin), location_address(null/법정동 명칭)를 추가한다. version은 수정 시 증가한다. 검색 후보 원래 좌표는 그대로 두고 다른 핀 좌표는 본인 위치 확인 ID와 함께 전달한다. 원래 검색 name/address와 선택한 핀의 법정동 명칭을 구분한다.

로그인 쿠키/POST Origin·CSRF/no-store 및 기존 공통 data/meta·error/meta·X-Request-ID를 유지한다. 검색은 서버 HTTPS로만 호출하며 외부 리다이렉트/자동 재시도를 하지 않는다. 공급자 원문·검색어·좌표·주소·키·쿠키는 실행 로그에 없다. 후보의 이름/주소/좌표만 임시 저장하고 사용자가 선택한 장소는 삭제/탈퇴까지 유지한다.

- 401 AUTH_REQUIRED/SESSION_EXPIRED, 403 CSRF_INVALID, 422 VALIDATION_ERROR, 404 RESOURCE_NOT_FOUND, 409 IDEMPOTENCY_CONFLICT, 429 RATE_LIMITED+Retry-After, 502 PROVIDER_RESPONSE_INVALID, 503 PROVIDER_UNAVAILABLE. DB 연결 실패는 기존 SERVICE_UNAVAILABLE.
- 후보는10분 후 접근 차단 및 다음 검색에서 청소. 멱등 결과는24시간 후 접근 차단 및 다음 생성에서 청소. 매일 청소 운영 스케줄은 F11 후속이다.
- 멱등 헤더는 영문/숫자/밑줄/하이픈1~128자. 동일 사용자/키/본문은 기존201, 변경된 본문은409. 세션/현재 소유권을 재검사하고 동시 세션 생성은 DB advisory lock으로 직렬화한다. 같은 본문 재시도는 후보가 만료돼도 기존 결과를 반환한다.
- UI는 검색/저장 중 비활성, 빈 결과, 재검색/재시도, 만료 안내, 세션 만료 시 화면 자료 제거, 페이지 이탈 요청 취소를 제공한다. 서버 시각과 expires_at 차이로 화면 만료를 계산하며 서버 최종 검사와 별개다.

## 저장소와 검증

0003_saved_places: saved_places(장소), place_searches(임시 후보), place_creation_keys(24시간 재시도). user_id FK와 소유권 조회, 좌표/라벨 CHECK 및 조회/만료 인덱스 포함. 공급자 원본·검색어는 저장하지 않는다.

실행: backend/.venv/Scripts/python.exe backend/migrate.py upgrade head. KAKAO_REST_API_KEY는 서버 .env에만 둔다. 기존 인증 설정/프론트 Vite 프록시를 사용한다. 마이그레이션 왕복은 임시 스키마에서만 수행한다.

2026-10-07: 백엔드68개·프론트35개·빌드 통과, 실제 개발 DB head 적용. 카카오 공개 강남역·공개 주소 검색 및 합성 테스트 계정으로 저장/새로고침 유지 확인. 데스크톱1440×1000·모바일390×844 검증. 상세 근거/한계는 development_log.md.

호환성: 기존 미구현 생성 초안에 search_id/candidate_id가 필수가 됐다. 지도 핀 저장은 아래 F03-02에서 계약 확장/구현했다. 기존 인증·health 계약 유지, 경로 산정 무효화/장소 삭제/탈퇴 청소 완료를 의미하지 않는다.

## F03-02 지도 핀·출입구 확인/수정 (2026-10-07)

검색한 후보에서 ‘지도에서 위치 확인’, 저장 장소에서 ‘위치·출입구 확인’을 누른다. 카카오 지도 클릭/마커 드래그·방향 버튼5m 이동·처음 위치로를 지원한다. 현재 GPS 권한은 요청하지 않는다. 출입구 설명은 사용자가 입력한1~100자 또는 null이며 공식 출입구 ID/실내 이동 인증이 아니다. 기존 entrance_ref는 null이다.

| API | 입력/응답 | 규칙 |
| --- | --- | --- |
| GET /api/v1/map-config | → javascript_key | 로그인·no-store. 등록 도메인 제한용 공개 SDK 키만 반환, REST 키 제외. 미설정503 MAP_UNAVAILABLE |
| POST /api/v1/place-location-confirmations | location → confirmation_id/location/location_address/expires_at | 로그인·CSRF·사용자당10회/분. 서버 coord2regioncode로 서울/경기 법정동 확인,10분 유효. 범위 밖/바다422 UNSUPPORTED_REGION |
| PATCH /api/v1/places/{place_id} | expected_version>=1, location?, location_confirmation_id?, entrance_note? → 장소 | 본인 행 잠금·버전409·최소 변경 필드1개·위치에는 확인 ID 필수. 타인/없는/만료404, 확인과 좌표 불일치422 |

생성 시 기존 검색 후보 좌표 저장은 유지한다. 다른 좌표 또는 map_pin 출처로 저장하려면 본인 확인 ID가 필요하며, 검색 후보 검사도 유지한다. 신규 선택 입력이 null/생략이면 F03-01의 기존 멱등 요청 해시를 유지한다. 수정은 좌표/출처/설명 변경에만 version+1, 동일 값은 유지, 설명 null은 제거다. 기존 검색 주소/라벨은 이번 PATCH에서 바꾸지 않는다. 기존 클라이언트 호환 유지.

지도는 https://dapi.kakao.com/v2/maps/sdk.js 공식 SDK에서만 로딩(10초 타임아웃/실패 재시도), 저장된 KAKAO_JAVASCRIPT_KEY를 공개용으로 사용한다. SDK 도메인에 http://localhost:5173·http://127.0.0.1:5173 및 실제 운영 HTTPS origin을 등록하고 카카오맵 API를 활성화해야 한다. REST/AI 키는 서버 전용이다. 공식 [지도 가이드](https://apis.map.kakao.com/web/guide/)·[좌표→지역 API](https://developers.kakao.com/docs/ko/local/dev-guide) 기준.

핀 이동/확인 재요청/10분 만료는 이전 확인을 제거하여 저장을 막는다. 수정409는 최신 장소 재조회 후 다시 확인, 로그인 만료는 자료 제거, 이탈은 요청 취소. 서버에서 지원지역 확인 실패를 추측해 성공으로 바꾸지 않는다. SDK 또는 공급자 오류·빈 지역 결과·키 미설정도 표시한다.

0004_place_map_pin: 기존 장소에 설명/출처/법정동 컬럼을 추가하고 place_location_confirmations를 생성한다. 확인은10분 후 접근 차단 및 다음 확인에서 만료행 청소. 매일 청소는 F11 후속. 실제 도보/경로 저장소는 미구현이며 place_id/version 불일치에 따른 산정 재사용 제외는 F04/F05에서 구현/검증한다. 이번 기능은 버전 증가·이전 버전409·동시 충돌·동일 값 유지까지 검증했다.

검증: 백엔드80개(새 핀12개 포함)·프론트49개·빌드 통과.0003의 기존 장소 보존/0004↔0003 왕복, 실제 Kakao SDK 렌더링·클릭/드래그/방향 버튼·서울 법정동 확인·생성/수정/새로고침 유지, 데스크톱1440×1000·모바일390×844 확인. SDK 오류/10초 타임아웃·재시도·만료·충돌은 자동 테스트로 검증. 공급자 전체 조건/지도 위치 정확도/실제 휴대전화·실내 출입구·GPS·이전 도보 산정값 재사용은 미검증이다.
