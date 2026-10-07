# 지금이니? — 고정 장소 검색·저장 (F03-01)

- 기준: [Notion API v0.35](https://app.notion.com/p/3ebace1670c6806c8199cde33ebfbdfa) 02절·5.1.1절, 2026-10-07 저장 재조회 확인.
- 범위: 주소/키워드 검색 → 후보 선택 → 집·회사 등 이름 저장 → 본인 목록/상세 조회. 출입구·지도 핀 수정, 수정/삭제, 현재 위치는 F03-02~05 후속이다.

React ‘내 설정 → 내 장소’에서 로그인 후 등록한다. 실제 저장 장소는 PostgreSQL 원본이며 화면 체험 루틴의 가상 집/회사에는 자동 적용하지 않는다. 계정 모달을 열면 장소 카드와 요청을 제거하고 닫을 때 다시 조회하여 이전 계정의 화면 자료를 재사용하지 않는다.

## API

| API | 입력/응답 | 핵심 규칙 |
| --- | --- | --- |
| POST /api/v1/place-searches | query(공백 제거 후1~100자) → search_id/expires_at/candidates | 카카오 주소·키워드 각각 첫10건, 서울/경기 주소만, 중복 제거 최대20건, 사용자당10회/분 |
| POST /api/v1/places | label(1~30자), location, search_id, candidate_id, entrance_ref(null) →201 장소 | 본인 후보/600초 만료/좌표 일치. 선택 Idempotency-Key로24시간 중복 생성 방지 |
| GET /api/v1/places | limit(기본20/최대100), cursor? → items/next_cursor | 본인 UUID 내림차순 목록, 타인/없는 cursor404 |
| GET /api/v1/places/{place_id} | →200 장소 | 본인만, 타인/없는/잘못된 ID404 |

장소 객체: place_id, label, name, address, location(latitude/longitude), entrance_ref(null), version(1). 후보 객체: candidate_id, name, address, location. 서버가 후보/검색 ID를 발급하며 프론트는 후보 좌표를 바꾸지 않는다.

로그인 쿠키/POST Origin·CSRF/no-store 및 기존 공통 data/meta·error/meta·X-Request-ID를 유지한다. 검색은 서버 HTTPS로만 호출하며 외부 리다이렉트/자동 재시도를 하지 않는다. 공급자 원문·검색어·좌표·주소·키·쿠키는 실행 로그에 없다. 후보의 이름/주소/좌표만 임시 저장하고 사용자가 선택한 장소는 삭제/탈퇴까지 유지한다.

- 401 AUTH_REQUIRED/SESSION_EXPIRED, 403 CSRF_INVALID, 422 VALIDATION_ERROR, 404 RESOURCE_NOT_FOUND, 409 IDEMPOTENCY_CONFLICT, 429 RATE_LIMITED+Retry-After, 502 PROVIDER_RESPONSE_INVALID, 503 PROVIDER_UNAVAILABLE. DB 연결 실패는 기존 SERVICE_UNAVAILABLE.
- 후보는10분 후 접근 차단 및 다음 검색에서 청소. 멱등 결과는24시간 후 접근 차단 및 다음 생성에서 청소. 매일 청소 운영 스케줄은 F11 후속이다.
- 멱등 헤더는 영문/숫자/밑줄/하이픈1~128자. 동일 사용자/키/본문은 기존201, 변경된 본문은409. 세션/현재 소유권을 재검사하고 동시 세션 생성은 DB advisory lock으로 직렬화한다. 같은 본문 재시도는 후보가 만료돼도 기존 결과를 반환한다.
- UI는 검색/저장 중 비활성, 빈 결과, 재검색/재시도, 만료 안내, 세션 만료 시 화면 자료 제거, 페이지 이탈 요청 취소를 제공한다. 서버 시각과 expires_at 차이로 화면 만료를 계산하며 서버 최종 검사와 별개다.

## 저장소와 검증

0003_saved_places: saved_places(장소), place_searches(임시 후보), place_creation_keys(24시간 재시도). user_id FK와 소유권 조회, 좌표/라벨 CHECK 및 조회/만료 인덱스 포함. 공급자 원본·검색어는 저장하지 않는다.

실행: backend/.venv/Scripts/python.exe backend/migrate.py upgrade head. KAKAO_REST_API_KEY는 서버 .env에만 둔다. 기존 인증 설정/프론트 Vite 프록시를 사용한다. 마이그레이션 왕복은 임시 스키마에서만 수행한다.

2026-10-07: 백엔드68개·프론트35개·빌드 통과, 실제 개발 DB head 적용. 카카오 공개 강남역·공개 주소 검색 및 합성 테스트 계정으로 저장/새로고침 유지 확인. 데스크톱1440×1000·모바일390×844 검증. 상세 근거/한계는 development_log.md.

호환성: 기존 미구현 생성 초안에 search_id/candidate_id가 필수가 됐다. 지도 핀 직접 저장은 F03-02에서 계약 확장 예정이다. 기존 인증·health 계약 유지, 출입구 수정/경로 무효화/장소 삭제/탈퇴 청소 완료를 의미하지 않는다.
