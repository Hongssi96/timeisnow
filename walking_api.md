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

## F05-05 같은 조건의 저장값 재사용 — 2026-10-12

Notion v0.55. 내부 estimate_and_store(..., cache_sources=[...])를 확장한다. 서버가 먼저 검증한 candidate_id, provider, provider_path_ref, path_version, origin_entrance_ref, destination_entrance_ref, condition_version만 받는다. 식별자는 ASCII1~200자, 중복 후보/추가 필드/미확인 unknown·unconfirmed·none·null을 거부한다. 출입구 적용이 없을 때만 not_applicable을 명시한다. 클라이언트가 만든 플래그를 물리 검증으로 받아서는 안 된다. 미제공 또는0010 이전 이력은 캐시를 추정하지 않고 기존 산정 흐름을 따른다.

캐시 키는 사용자별 장소/location_version·양끝 물리 참조·방향·범위/필요범위·공급자 경로/버전·양끝 출입구·조건 버전·기준 거리/시간/기개인화 여부·거리 기준일 때 속도·정책/공통/작업 프롬프트/모델 버전이다. 일시적인 candidate/evidence/request ID는 제외한다. 현재 근거가 유효·준비된 후보만 저장된 유효 검증 revision을 검색한다. 프로필 전체 스냅샷이 같아야 하고, 물리 조건은 같지만 프로필만 변경됐으면409 PROFILE_RECALCULATION_REQUIRED로 AI 없이 차단한다. 계수 재계산은F05-06 후속이다.

전체/부분 적중을 지원하며 누락 후보만AI에 전달한다. 원본 기준/계수/최종 정수초를현재입력으로 다시 검산하고 현재candidate/evidence ID로 결과를 연결한다. 기준 실수는F05-03과같은 rel_tol=1e-12/abs_tol=1e-9, 최종초/계수는정확히일치해야 한다. DB NUMERIC에는 Decimal(str(검증값))으로 전달해 긴 계수를 보존한다. 내부 estimates는 candidate_id,estimate_id,revision_id,reused,expires_at이다. 적중은원본ID·계산시각·revision을유지하고 effective expires_at=min(원본기한,현재근거기한)으로반환한다. 원본만료연장/새numeric revision 없음. 기존GET은단순조회이므로reused=false유지한다.

전체 입력/Context/cache_sources 및 원본 연결로 멱등 재실행을 검사한다. ai_executions.reused_estimates에 candidate/estimate/revision/effective expiry만 보존한다. 전부적중이면 모델/지연/사용량null, 부분적중은실제누락호출의메타데이터만기록한다. 원본연결삭제/만료 후 재실행은404, 실행ID내용변경409. 사용자/request_id와정렬된사용자/물리키 세션잠금으로 다른실행ID의동시호출도409 EXECUTION_IN_PROGRESS. 호출중장소변경/원본만료는저장전재확인해 전체롤백한다. 일반로그에이름/정밀좌표/키/원문추가없음.

0010_walking_cache: walking_paths.cache_key/cache_identity(nullable 쌍) 및회원/키/기한인덱스, ai_executions.reused_estimates(기본빈배열). 이전이력백필없음. 신규공개API/UI없음. 실제walking.evidence는needs_data·reusable=false를유지하므로실사용재사용/출발안내연결은후속이다.

## F05-06 개인 계수 변경 재계산 — 2026-10-13

Notion v0.56. 내부 estimate_and_store는 같은 물리 키의 유효 원본에서 profile.version/validated_duration_factor만 바뀌면 AI와 지도 호출 없이 재계산한다. 저장된 양수 base_seconds에 새 계수(기본1.0·허용0.5~2.0)를 곱하고 Decimal로 올림한다. 이전 최종값에 계수를 다시 적용하지 않는다. 이미 개인화된 공급자 시간은 계수1로 유지한다. 거리/속도 소수 기준도 저장된 십진 초를 그대로 사용하므로 올림 경계에서는 원래 거리/속도를 다시 나눈 계산과1초 차이가 날 수 있다. 재계산은 원본 기준의 표현을 일관되게 사용하는 계약이다.

예: 기준300초·기존 계수1.2/360초 → 새 계수1.1/330초. 같은 estimate에 새 revision_no·profile_version·parent_revision_id·candidate_id·source=profile_recalculation·calculated_at을 저장한다. 부모/원본 경로/현재 Context 중 이른 expires_at을 유지하고 품질 retained_until도 원본을 넘기지 않는다. 최초 AI 근거 버전과 숫자 이력은 보존한다. 재사용/재계산/새 산정이 섞이면 새 후보만AI에 전달하고, 모델 실행 없는 이력의 model/지연/사용량은null이다. 같은 실행 재요청 또는 다음 동일 프로필 조회는 같은 revision을 반환하며 중복 보정/새 이력 생성을 막는다.

호출 전후 회원/프로필/본인 장소 버전·물리 키·원본 수치/연결/기한을 재검사한다. 만료/변경은 현재 검증 근거를 제공받아 새 산정으로 처리한다. 오래된 Context/위치 버전은404/409이며 미확인 실제 근거는needs_data이다. 물리 키가 같으나 프로필 다른 필드도 변경됐으면409 PROFILE_RECALCULATION_REQUIRED로 차단한다. 실제 공급자 경로 재조회와 물리 근거 확인은 호출 서비스의 선행 조건이며 이번 내부 모듈이 미확인 값을 인증하지 않는다.

GET 상세는 인증/no-store/기존 필드/reused=false를 유지하고 source enum에 profile_recalculation을 추가한다. 최신 revision의 계수/초/계산 시각을 반환한다. 내부 estimates도 source를 추가한다. 프론트는 해당GET을 아직 쓰지 않아 UI 변경은 없지만 신규 소비자는 source 두 값을 처리해야 한다.0011_walking_recalculation은 부모 revision의 회원/estimate 복합FK·candidate_id·source 제약을 추가하며 기존AI revision의 부모는null이다. downgrade는 파생 revision만 제거하고 원본을 보존하므로 실제 개발DB에서 수행하지 않는다.

F09 계수 학습·실제 물리 근거 확보/사용자 생성 연결·F07 출발 안내는 후속이다. 현재 walking.evidence의 needs_data/ready_for_estimation=false/reusable=false를 유지한다.

## F05-07 도보 상태 화면 안내 — 2026-10-13

Notion v0.57. 루틴 선택 카드와 유효 후보 상세에 WalkingGuidance를 표시한다. 실제 개인 도보 AI는 해당 루틴/후보에서 아직 실행하지 않았음을 명시한다. 루틴 요약에는 세부 근거가 없으므로 접근/환승/마지막 구간 누락 여부를 추측하지 않는다. 후보는 기존 missing_segments로 누락을 구분하고 지하철/혼합·실내 누락 코드로 입구부터 승강장까지 확인 필요를 안내한다. 공급자0초도 실제 이동 없음으로 확정하지 않는다.

조회 실패/만료는 기존 재시도·위치/경로 재선택 동작을 유지하면서 확인되지 않은 시간을 사용하지 않음을 설명한다. 알려진 AI 검증/준비 실패 코드와 공급자 연결/시간초과 코드는 고정 문구로 표시하고 원문·키·주소·코드·요청ID를 공통 안내에 출력하지 않는다. 공급자 오류를 AI 실행 증거로 표시하지 않는다. 기존 alert는 한 번만 알리고 보조 설명은 중복 알림을 만들지 않는다. 추가 HTTP/API/AI 호출 없이 기존 응답 상태만 사용한다. 현재 실제 AI 생성 공개 API 연결은 후속이며 이번 검증은 합성 오류 응답을 사용했다. 계산·근거 준비/재사용·보관·인증 계약 변경 없음.
