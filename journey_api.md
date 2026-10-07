# 지금이니? — F04-01~03 대중교통 후보·구간 모델·비교 화면

기준: [Notion v0.42](https://app.notion.com/p/3ebace1670c6806c8199cde33ebfbdfa). 홈 ‘경로 후보 비교’에서 실제 후보 조회·정렬·구간 상세를 사용할 수 있다. AI/실시간/실제 출발 안내·루틴 저장은 후속이다.

### 5.2.3 F04-01 대중교통 경로 후보 조회 (구현 단계 계약)
- 범위: 로그인 사용자의 출발/도착 입력으로 카카오 대중교통 후보를 비동기 조회한다. 이번 단계는 depart_now(Asia/Seoul)만 실행하며 arrive_by는422 UNSUPPORTED_TIMING으로 명시한다. 목표 도착 검색·AI 도보 산정·실시간 도착·비교 화면·루틴 저장은 후속이며 기존 설계에서 삭제하지 않는다.
- POST /journey-searches: 쿠키·Origin/CSRF·no-store, origin/destination은 saved_place(place_id, location_version 선택), map_pin(latitude/longitude), current_location(기존 좌표/측정치 및 location_confirmed:true 필수). 현재 위치는 본인 보고만 사용하며 GPS 수치/자동 일치 판정은 보류한다. timing={mode:depart_now,timezone:Asia/Seoul}, preferences.route_preference 선택 balanced/fewer_transfers/less_walking. 없는 선호는 본인 프로필 사용. 알 수 없는 필드/형식422. 양 끝 위치 서울/경기 확인, 본인 장소404·위치 버전409, 이름 변경은 유효 유지.
- Idempotency-Key 선택(1~128자 ASCII 영문/숫자/밑줄/하이픈): 사용자+경로+키와 비밀키 HMAC 본문 해시만24시간 보관, 같은 본문202 동일 search_id/job_id/queued 응답·현재 권한/위치 버전 재검사, 다른 본문409 IDEMPOTENCY_CONFLICT. 키 없이 새 검색이다. 사용자10회/분(실패 포함), 동시 진행 최대2개/사용자·전체8개로429 Retry-After. 중복 재현은 새 공급자 호출 없음.
- 접수202 data={search_id,job_id,status:queued}. worker는 running→succeeded/failed로 전환하며 본인 장소 위치를 작업 전/후 다시 검사한다. 개별 공급자10초·지역 확인3초/회, 전체 작업60초 제한. 재시작/60초 초과 미완료 작업은 조회/새 요청에서 failed JOB_INTERRUPTED 처리, 사용자 좌표는 재실행하지 않는다. 실행 중 작업은 DB 상태/기한 조건으로 최종 결과를 반영하므로 늦은 응답이 실패 상태를 되돌리지 않는다.
- GET /journey-searches/{search_id}: 본인만200, 없거나타인/검색5분 만료404. status queued/running/succeeded/failed, candidates[], unavailable_reasons[], error(null 또는 공통code/message/details), expires_at 및 job_id. 진행 중 Retry-After:2; 후속 클라이언트는2/5/10/최대30초 및 비활성 중지 규칙 적용. 후보는 candidate_id,type,validity:insufficient_data,ordered_legs,transfer_count,total_seconds,total_distance_meters,walking_seconds,estimated_arrival_at:null,time_sources,missing_segments를 포함한다. 경로 ID는 본인 검색 안에서만 유효.
- ordered_legs는 최소 WALKING/BUS/SUBWAY 종류·순서·공급자 seconds/meters·정류장명/차량명만 정리한다. 시간 출처는 provider_estimate이며 접근/환승/마지막 도보의 AI 산정·실시간/미래 환승·역 출입구/플랫폼·중간 지역 범위는 미확인으로 명시한다. 후보 총 시간을 현재 시각에 더해 실제 도착 시각으로 만들지 않는다. 지도 geometry/공공 ID 매핑·완전한 방향/내부 이동은 F04-02~05 후속이다.
- 최대2회 환승을 적용해 제외 사유 TRANSFER_LIMIT를 기록한다. 후보는 최대20개, balanced 총 소요시간·fewer_transfers 환승수·less_walking 공급자 도보시간 우선으로 정렬하며 동률은총시간/환승수/도보시간·공급자순서로 결정한다. 이 순서는 실시간 탑승 가능/최적 경로 보증이 아니다.
- 정상 무결과/EQUAL_POINTS/출발·도착 노드 없음은 succeeded/candidates[]/NO_ROUTE 또는 ENDPOINT_UNRESOLVED 사유, 공급자 장애는 failed PROVIDER_UNAVAILABLE, 시간초과 failed PROVIDER_TIMEOUT, 잘못된 응답 failed PROVIDER_RESPONSE_INVALID. failed 조회 자체는200, 접수 전 입력/권한/DB/제한 오류는 공통 HTTP 오류. 예상 밖 worker 오류는 안전한 INTERNAL_ERROR, 원문/스택 미노출.
- GET /jobs/{job_id}: 본인 작업 상태·종료/error/result_ref/결과 만료 여부만 조회, 후보/입력 좌표는 포함하지 않는다. 작업 상태는 종료 후24시간, 진행기한초과는failed 처리. 검색 결과는 생성부터300초, 선택/재현 시 별도 만료·장소 존재/위치 버전 검사. 만료 검색은 재실행하지 않고 새 요청을 요구한다.
- PostgreSQL0006_journey_searches: 소유자·검색/작업ID·상태/기한·saved_place 최소참조(place_id/location_version)·정규화 후보만 저장한다. 최초/재현 응답과 HMAC 키는24시간, 후보는300초 이후 사용 차단/요청 시 삭제. GPS/지도 입력 좌표·측정시각/정확도·원본공급자응답/geometry/landingURL/원문guidance·키·주소/본문 로그/DB 저장 없음. 좌표는 worker 메모리에서 공급자 요청에만 사용하고AI에 전달하지 않는다. 별도 매일 청소 스케줄은 후속이며 요청 시 만료 자료를 정리한다.
- 호환성: 기존 미구현 여정 설계를 단계적으로 구체화한 신규 API. F03/auth/장소 API 유지, F03-05a 수동 확인 변경은 별도 브랜치의 구현을 중복 포함하지 않는다. F04-01 완료는 F04 전체·GPS 정책·도보/실시간/출발 안내 완료가 아니다.

### 5.2.4 F04-02 공통 구간 모델 (journey.v1)
- 구현/검증(2026-10-07): 최신main9670281에서codex/journey-segments 구현. 백엔드115개·프론트79개·빌드 통과. 직접 버스/지하철·버스↔버스/버스↔지하철/지하철↔지하철 및연속도보는합성모델검증, 실제공개강남역→서울역15후보의구간/연결17개·GET재조회ID안정성·스키마 일치 확인. 실제응답의도보17개는환승만포함하며접근/마지막도보는누락표시한다. 실제기기GPS·물리방향/실시간환승/역내부/AI/비교화면은미검증, 합성계정/작업/후보제거. 근거 `development_log.md`, `journey_api.md`. UI/DB DDL 변경 없음.
- F04-01 경로/인증/입력/202 작업·본인 조회/멱등/만료/정렬/최대2회환승/300초·24시간 보관을 유지한다. 이번 변경은 후보 응답의 추가 필드이며 UI 비교/선택·실시간/AI/목표 도착·GPS 수치 정책은 변경하지 않는다.
- 후보 model_version=journey.v1. 기존 candidate_id/type/validity/ordered_legs/transfer_count/total_seconds/total_distance_meters/walking_seconds/estimated_arrival_at/time_sources/missing_segments는 유지한다. 새 transfer_count_computed는 BUS/SUBWAY 단계 수-1, provider 값과 다르면 TRANSFER_COUNT_MISMATCH로 미확인 표시한다. 공급자 환승수 또는 교통 단계 기반 수가2를넘으면TRANSFER_LIMIT로제외하며계산수를실제물리적환승인증으로해석하지않는다. route type과 실제 교통수단 종류 모순·순서/ID 중복·잘못된 값은 PROVIDER_RESPONSE_INVALID로 안전하게 거절한다.
- WALKING 구간에 walking_role=access/transfer/egress: 첫 교통수단 전 접근, 교통수단 사이 환승, 마지막 교통수단 뒤 마지막 도보. 연속 도보 단계도 공급자 순서를 유지하며 같은 역할로 분류한다. BUS/SUBWAY walking_role은null. 어느 도보 구간도 AI 산정이나 내부 동선 인증으로 바꾸지 않는다.
- 모든 leg에 boarding/alighting/direction/vehicle_options 추가. BUS/SUBWAY boarding/alighting은 stops 첫/마지막 name 및 public_id/entrance_ref/platform_ref:null. direction=\{source:provider_stop_order,from_stop_name,to_stop_name,public_direction_id:null\}. 이는 공급자 정류장 순서만 의미하며 공공 노선 운행방향/물리적으로 같은 승강장 확인이 아니다. WALKING은boarding/alighting:null, direction.source=unknown·이름/공공ID:null,vehicle_options\[\].
- vehicle_options는 \[\{name,provider_type\}\]이며 provider_type은 공급자가 제공한 버스/지하철 분류 문자열 또는null. 미등록 새로운 세부 문자열도 허용하되 문자열 형식/길이를 검사한다. 기존 vehicles\[\] 문자열은 그대로 유지하고 노선 ID로 해석하지 않는다.
- 후보 connections\[\]는 연속 교통 단계 사이의 connection_id/from_leg_id/to_leg_id/from_stop/to_stop/walking_leg_ids/walking_seconds/feasibility:unknown/time_source:provider_estimate/physical_stop_match:unconfirmed를 포함한다. 순서만 연결하고 버스↔버스·버스↔지하철·지하철↔지하철을 같은 모델로 다룬다. 명시 도보 단계가 없으면 walking_seconds:null/TRANSFER_WALK_MISSING, 실제0초 도보가 제공된 경우만0을 유지한다. 정류장 이름이 같아도 일치/환승 가능을 확정하지 않는다.
- 접근/마지막 도보가 공급자 단계에 없으면 ACCESS_WALK_MISSING/EGRESS_WALK_MISSING, 공공 방향은 PUBLIC_DIRECTION_UNVERIFIED로 표시한다. 기존 AI/실시간·출입구/플랫폼·중간지역 미확인 사유를 유지하며 후보 validity=insufficient_data/estimated_arrival_at:null을 유지한다.
- timing_breakdown=\{walking_seconds,in_vehicle_seconds,legs_total_seconds,provider_total_seconds,unallocated_seconds,status\}. 합계가 공급자 총시간 이하이면 unallocated_seconds=차이/status=unallocated, 동일하면0/status=consistent. 차이를 실시간 대기·환승 여유로 단정하지 않는다. 단계 합계가 총시간을 넘으면 unallocated_seconds:null/status=inconsistent 및 DURATION_TOTAL_MISMATCH로 표시하고 공급자 total_seconds는 바꾸지 않는다.
- `app/journey_models.py` 공통 모델로 새 공급자 정규화와 GET 결과를 검증하며 GET200 OpenAPI SearchEnvelope/Candidate/Leg/Connection/Breakdown 스키마를 노출한다. 정수초/미터(음수·bool 거절), 이름/목록/순서·연결 참조/일관성을 확인하며 좌표/원문guidance/landingURL 등 미정 필드가 응답으로 유입되지 않게 한다. 신형 JSONB 후보는 저장 전 검증한다. 이전 F04-01 후보는 GET 시 기존leg ID/순서/시간/정류장명으로 보강하고 차량 세부종류는null, connection_id는 candidate_id+교통legID 기반으로 안정적으로 생성한다. 재조회마다 ID가 바뀌지 않고 새 공급자 호출/입력좌표 저장/DB migration은 없다.
- 호환성: 기존 필드/ID/시간값과 선택/작업 계약 유지, 추가 필드를 무시하는 클라이언트는 계속 동작한다. 신형 모델 검증 실패는502 PROVIDER_RESPONSE_INVALID, worker 단계 실패는 기존failed/data.error이다. F04-02 모델 완료와 실제 물리 방향/환승·내부이동·사용자 비교 화면 검증 완료는 구분한다.

### 5.2.5 F04-03 경로 후보 비교 화면
- 구현/검증(2026-10-07): 최신main63674ac에서codex/journey-comparison 구현. 프론트97개·빌드1899모듈·백엔드115개 회귀 통과. 실제합성계정/공개강남역→서울역 위치직접선택→POST202/GET200→15후보 비교/로컬정렬·상세/정류장순서·누락도보·키보드 Enter를확인했다. PC1440×1000/모바일390×844 카드·상세/하단메뉴·홈/설정/계정 회귀·가로넘침없음/콘솔error0, 자연검색만료시후보/상세제거 확인. 숨김/재시도/빈결과/실패/인증만료/늦은응답은 모의검증, 실제GPS권한/측정·실시간/운행시간표·AI/출발안내·루틴저장은미검증. 합성계정/장소/검색/작업/세션제거. 근거 `development_log.md`.
- 홈 '경로 후보 비교' 진입으로 기존 내비게이션/미색·초록 디자인을 유지한 비교 페이지를 제공한다. 아직 유효한 홈 출발지는 초기값으로 사용할 수 있으며 출발/도착은 기존 current_location/map_pin/saved_place 확인 흐름을 재사용한다. 도착 위치도 목적을 표시해 직접 선택한다. 로그인 전 기기 위치를 요청하지 않고 GPS 수동 확인/수치 보류를 유지한다.
- 출발/도착·선호를 명시 선택한 뒤 '경로 후보 조회'를 누를 때만 기존 POST /journey-searches를 호출한다. depart_now/AsiaSeoul 및balanced/fewer_transfers/less_walking만사용하며현재시각·주소원문을임의로입력하지않는다. 최초 접수에 새 Idempotency-Key, 접수 응답을 못 받은 네트워크/시간초과 재시도는 동일 본문/키를 유지한다. 입력 변경/새 검색은 새 키, 접수된 검색의 조회 실패는 GET만 재시도하며 POST 자동 재전송 없음.
- queued/running 접수는 완료로 표시하지 않는다. 최초2초→5→10→최대30초 간격으로 GET 결과 조회, 유효한 Retry-After 초 헤더를 우선하고1\~3600초 범위를 처리한다. 비활성 화면은 새 조회를 멈추며 진행 중 GET을 취소, 복귀 시 같은 search_id를 이어서 조회한다. 페이지 이탈/방법·입력 변경/로그인 모달·인증 만료 인지/입력600초 및검색300초 기한은 타이머·요청을 취소하고 늦은 응답을 무시한다. meta.server_time/expires_at 차이로 만료를 계산하며 입력 선택 유효기한보다 연장하지 않는다.
- 화면 상태: 위치 미선택/로그인 필요·접수/조회중·succeeded 후보/정상무결과·failed 안전한오류·네트워크조회재시도·권한/장소버전충돌·만료/재선택. 인증 실패는 좌표/목록/후보를 제거하고로그인행동,409 VERSION_CONFLICT는입력재선택,404 결과조회는만료/재검색. 숨겨진 화면/새로고침/계정변경에서 URL/DB/localStorage로 개인 위치/후보를 복원하지 않는다.
- 비교 카드: 카카오 예상 total_seconds·transfer_count·교통구간수기반차이가있으면횟수확인필요·제공된 walking_seconds 및누락여부. 접근/환승/마지막 도보가 빠지면0분으로확정하지않고‘도보 확인 필요/일부 도보·미확인 구간 있음’으로표시한다. DURATION_TOTAL_MISMATCH는총시간확인필요,unallocated_seconds는대기/여유로채우지않는다. 도착시각·출발까지카운트다운·탑승보장 없음. 실제응답에심야노선이포함될수있으므로 운행시간과지금이용가능여부는확인필요로표시하고시간표를추정해제외/인증하지않는다.
- 전체 예상 시간/환승수/제공된 도보시간 기준으로 로컬 정렬하며새 공급자요청을자동발생시키지않는다. 상세보기는화면메모리의한후보구간을펼치는동작이며실제이동/루틴저장이아니다. WALKING 역할과seconds/meters, BUS/SUBWAY 차량명·선택적세부분류/승하차 정류장순서를표시한다. 운행방향/공공ID·물리정류장일치·연결 feasibility는검증되지않았음을쉬운문구로표시한다. 연결 도보null과0을구분하며빠진접근/마지막도보·AI/실시간/출입구/플랫폼·중간지역·미정GPS 근거를안내한다.
- 프론트는journey.v1 후보/순서/ID/시간분해/연결참조·응답ID/기한·상태를검증하고깨진형식/미지원모델버전은성공으로표시하지않는다. 공급자/서버오류원문·주소·키/본문·좌표/후보를로그에출력하지않는다. React 텍스트출력·기존lucide/카드/버튼/CSS 변수·44px 행동·키보드 상세보기·모바일 줄바꿈을 유지한다.
- 기존API경로·입출력/권한/DB DDL·작업/보관·지도공급자 계약은 유지한다. 공통클라이언트는Retry-After 파싱 결과만 추가노출하고 자동재시도는추가하지않는다. API모델의실시간/AI/목표도착 미구현 상태를화면에서검증됨으로바꾸지않는다.

## 실행 예시

```json
{"origin":{"type":"map_pin","latitude":37.4979,"longitude":127.0276},"destination":{"type":"map_pin","latitude":37.5547,"longitude":126.9726},"timing":{"mode":"depart_now","timezone":"Asia/Seoul"}}
```

접수 응답 search_id로 GET /api/v1/journey-searches/{search_id}를 조회한다. job_id는 GET /api/v1/jobs/{job_id} 상태 조회에 사용한다. 로그인 쿠키와 최신 CSRF 토큰을 유지하며 Idempotency-Key는 사용자가 새 검색을 시작할 때 새로 만든다. raw 본문/쿠키/키를 터미널에 출력하지 않는다.

마이그레이션: `backend/.venv/Scripts/python.exe backend/migrate.py upgrade head`. 최신 head0006_journey_searches는 기존 회원/장소를 보존한다. 카카오 키는 기존 서버 .env를 사용하고 프론트에 전달하지 않는다. [카카오 공식 REST 문서](https://developers.kakao.com/docs/ko/kakaomap/rest-api)의 대중교통 경로 스키마를 따른다.

실제 검증: 백엔드106개·프론트79개·빌드 통과. 공개 강남역→서울역 카카오 후보15개, 로컬202/200·no-store·요청ID·멱등 재현 확인. 실제 기기 GPS/휴대전화·AI 도보·실시간·목표 도착·비교 화면/완전한 방향·역 내부 검증은 수행하지 않았다. 상세 development_log.md.
