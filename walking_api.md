# F05-01 도보 근거 수집

2026-10-08 · Notion v0.50 · `walking.evidence.v1`

선택한 검색 후보에 공급자가 제공한 접근·환승·마지막 도보를 구분한다. 물리적 출입구·승강장·보행 가능 범위는 미확인이므로 AI 산정 준비나 재사용 완료로 취급하지 않는다. F04-04와 GPS 자동 판정 보류를 유지한다.

## 조회 계약

`GET /api/v1/journey-searches/{search_id}/candidates/{candidate_id}/walking-evidence`

- 쿠키 인증, 본인 성공 검색과 후보만 허용. GET은 CSRF 불필요, 응답은 `Cache-Control: no-store`.
- 잘못된 UUID·없음·타인·미완료·검색 300초 만료는 404 `RESOURCE_NOT_FOUND`. 참조 장소 삭제도 404, 위치 버전 변경은 409 `VERSION_CONFLICT`, 손상된 후보는 502 `PROVIDER_RESPONSE_INVALID`.
- 검색 후보를 읽고 기존 `place_refs`의 소유권/위치 버전을 확인한다. 검색/근거 쓰기·보관 연장·추가 지도/AI 호출은 없다. 인증 세션 활동 기한은 기존 규칙대로 갱신한다. 새 DDL 없음.
- 검색 저장소는 저장 장소 참조의 출발/도착 역할을 기록하지 않는다. 잘못 연결하지 않도록 양 끝은 좌표 없는 검색 지점 참조로 반환한다.

200은 기존 `{data, meta}` 형식이다. `data`:

| 필드 | 값/규칙 |
| --- | --- |
| model_version | `walking.evidence.v1` |
| search_id, candidate_id | 조회 대상 UUID |
| expires_at | 기존 검색 만료 시각, 연장 없음 |
| status | `needs_data` |
| ready_for_estimation, reusable | 둘 다 `false` |
| segments | 접근 1개 → 각 환승 연결 1개 → 마지막 1개 |

각 segment:

| 필드 | 값/규칙 |
| --- | --- |
| segment_id | 검색·후보·역할·연결 기반 안정적인 UUID |
| role | `access`, `transfer`, `egress` |
| connection_id | 환승 연결 UUID, 나머지는 `null` |
| walking_leg_ids | 제공 도보 leg UUID 배열, 누락은 `[]` |
| from_ref, to_ref | `{type: search_origin/search_destination}` 또는 `{type: transit_stop, leg_id, stop_name}` |
| provider_duration_seconds, provider_distance_meters | 연속 도보 제공값 합계. 누락은 `null`, 명시 0은 `0` |
| source | `provider_estimate` 또는 `missing` |
| scope | `provider_walking_segment` 또는 `unknown` |
| physical_endpoints | `unconfirmed` |
| missing_segments | 아래 사유 코드 배열 |

모든 구간에 `PHYSICAL_ENDPOINTS_UNCONFIRMED`를 남긴다. 도보 미제공은 `PROVIDER_WALK_MISSING`, 제공 0초는 `WALK_DURATION_ZERO`, 인접 지하철이 있으면 `ENTRANCE_PLATFORM_UNCONFIRMED`를 추가한다. 정밀 좌표·출입구 설명·공급자 원문은 응답/일반 로그에 포함하지 않는다. 총 경로 시간의 남는 값을 도보·대기·여유로 배분하지 않는다.

## 구현과 검증

`backend/app/walking`은 router(HTTP) → service(소유권·만료·근거 구분) → repository(검색 읽기), dto(응답 계약)로 나눈다. 기존 journey.v1 모델과 장소 참조 검증을 재사용한다.

`backend/tests/test_walking.py` 7개 및 전체 백엔드 137개 통과. 실제 PostgreSQL 임시 스키마/ASGI와 합성 공급자 결과로 제공·누락·0초·연속 도보·환승·지하철·반복 조회 무변경·소유권·만료·버전·손상 응답을 확인했다. 실서비스 공급자의 물리 범위 검증과 AI 호출은 수행하지 않았다. 프론트 변경 없음.

다음은 F05-02 프롬프트 블록/버전 로딩이다. F05-03 AI 입력으로 넘기기 전 보행 가능 범위·방향·출입구/승강장 검증을 해결해야 하며 이 응답만으로 유효 산정값을 저장하면 안 된다.

## F05-04 산정값·근거 이력 저장 — 2026-10-12

Notion v0.54. backend/app/walking/history_service.py의 persist는 F05-03 입력·결과를 다시 검산하고 Context(place_refs·verified_at·valid_until) 및 ExecutionMetadata(model_version·latency_ms?·usage?)로 불변 스냅샷을 저장한다. 공개 생성 API는 없다. Context는 서버가 보행 가능/방향/범위·소유권을 확인한 뒤 내부에서만 만들며 임의 클라이언트 플래그를 검증 근거로 받아서는 안 된다. 현재 walking.evidence는 미확인 상태라 유효 산정값 저장을 차단한다.

estimate_and_store는 모델 호출 전후 회원/프로필/장소 버전·물리 근거 기한을 재확인하고 F05-03 검증 결과를 원자 저장한다. 같은 사용자/request_id·입력·Context 재요청은 기존 실행을 반환해 AI 중복 호출을 막는다. 같은 실행 ID로 내용 변경은409, 실패한 실행은 같은 ID로 반복 호출하지 않고 기록된 안전한 오류를 반환한다. 이는 내부 실행90일 보관 동안의 재요청 처리이며 F05-05의 같은 장소/방향 조건 캐시 재사용과 다르다.

walking_paths(최소 후보/근거·장소 참조·방향/범위·확인/산정/만료 시각), walking_estimates(본인 산정 자원), walking_estimate_revisions(기준 초·계수·최종 초·profile/policy/prompt/model 실행 연결), ai_executions(최소 입력·Context·구조화 상태·검증/실패코드·실측 지연/알려진 사용량)의4개테이블을0009_walking_history로 추가한다. user_id와 부모 ID의 복합 FK로 타인 산정/실행 연결을 거부한다. 과거 숫자는 새 실행으로 덮어쓰지 않는다. 모델 자유문 reason·원문·정밀 좌표·이름·메모·키·내부 사고 과정은 저장하지 않는다. 기록하지 않은 지연/사용량은 null이며 없던 AI 호출의 모델명/지연도 null이다. 내부 검증 프로필 계수 스냅샷만 저장하며 실제 학습 계수 저장소 연결은 F09 후속이다.

유효한 ok만 path/estimate/revision을 만든다. needs_data/unsupported는 실행 상태만 보관한다. record_failure는 허용된 실패 코드와 최소 입력만 보관하고 산정값/손상 출력은 저장하지 않는다. 저장은 기존 회원 routine-write 잠금→회원/프로필→정렬된 장소 참조 순서, 실패 시 전체 롤백한다.

GET /api/v1/walking-estimates/{estimate_id}는 본인 쿠키 인증·no-store, CSRF 불필요.5.6의 요약 필드를 반환하며 source=ai_estimate·reused=false이다. 일반 조회를 캐시 재사용으로 표시하지 않는다. 잘못된UUID/없음/타인/산정 또는 근거 만료/참조 장소 삭제는404, 장소 위치 또는 프로필 버전 변경은409. 이름만 수정하면 위치 근거를 유지한다. 모델 호출·산정 쓰기·기한 연장 없이 읽고 기존 세션 활동 갱신은 유지한다. 내부 품질 자료는 응답하지 않는다.

산정 유효기간은 생성+30일과 Context.valid_until 중 이른 시각, 품질 이력은90일. 장소 변경/삭제 후 숫자 조회를 차단하며 과거 품질 이력은 보존한다. 회원 삭제는4테이블 CASCADE, purge_expired_history(user_id)는 해당 회원의90일 만료 이력을 정리한다. 자동 매일 실행/배포 스케줄은 후속이다. 재산정/계수만 변경/F05-05 캐시/출발 안내/사용자 생성 연결 및 실제 물리 근거 확보는 아직 후속이다.

동시 실행 보강: estimate_and_store는 사용자/request_id별DB 세션advisory 잠금으로 두 번째 AI 호출을 차단하고 내부409 EXECUTION_IN_PROGRESS를 반환한다. 완료한 동일 실행은 모델 재호출 없이 조회한다. 장소 수정 잠금은 모델 호출 동안 유지하지 않고 저장 전 위치 버전을 다시 검사한다.
