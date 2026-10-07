# 지금이니? — F04-01 대중교통 경로 후보 조회

기준: [Notion v0.40](https://app.notion.com/p/3ebace1670c6806c8199cde33ebfbdfa). 현재는 API 구현이며 후보 비교 화면은 F04-03 후속이다.

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

## 실행 예시

```json
{"origin":{"type":"map_pin","latitude":37.4979,"longitude":127.0276},"destination":{"type":"map_pin","latitude":37.5547,"longitude":126.9726},"timing":{"mode":"depart_now","timezone":"Asia/Seoul"}}
```

접수 응답 search_id로 GET /api/v1/journey-searches/{search_id}를 조회한다. job_id는 GET /api/v1/jobs/{job_id} 상태 조회에 사용한다. 로그인 쿠키와 최신 CSRF 토큰을 유지하며 Idempotency-Key는 사용자가 새 검색을 시작할 때 새로 만든다. raw 본문/쿠키/키를 터미널에 출력하지 않는다.

마이그레이션: `backend/.venv/Scripts/python.exe backend/migrate.py upgrade head`. 최신 head0006_journey_searches는 기존 회원/장소를 보존한다. 카카오 키는 기존 서버 .env를 사용하고 프론트에 전달하지 않는다. [카카오 공식 REST 문서](https://developers.kakao.com/docs/ko/kakaomap/rest-api)의 대중교통 경로 스키마를 따른다.

실제 검증: 백엔드106개·프론트79개·빌드 통과. 공개 강남역→서울역 카카오 후보15개, 로컬202/200·no-store·요청ID·멱등 재현 확인. 실제 기기 GPS/휴대전화·AI 도보·실시간·목표 도착·비교 화면/완전한 방향·역 내부 검증은 수행하지 않았다. 상세 development_log.md.
