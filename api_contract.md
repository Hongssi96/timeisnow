# 지금이니? API 설계 초안
- 문서 버전: 0.30 · 작성일: 2026-09-30 · 수정일: 2026-10-06 (사용자 요청으로 F01 별도 공급자 검증 단계 삭제)
- 프론트엔드: React · 백엔드: Python FastAPI
- 상태: **설계 검토용 / 핵심 서비스 기능 미구현**. GET /health와 React 서버 연결 확인은 구현되어 있으며 나머지 구현 상태는 `todo.md`를 따른다. 아래 미구현 경로·필드·정책은 구현 전에 조정할 수 있다.
- 기준: 대화에서 확정한 요구사항 및 프로젝트 `C:/projects/timeisnow` 폴더의 `planning.md`, `feature_breakdown.md`, `personalization.md`, `logging.md`, `ai_prompts.md`.
- 이 페이지는 수동 관리하는 설계 문서다. 코드와 자동 동기화되는 상태가 아니다.
<table_of_contents/>
## 1. 읽는 방법
API는 React가 FastAPI에 요청하는 약속이다. GET은 조회, POST는 생성·처리 요청, PATCH는 일부 수정, DELETE는 삭제에 사용한다. 경로의 중괄호는 실제 ID로 바꾸는 자리다.
**필수 기능:** 회원가입·개인 저장, 현재 위치와 집·회사, 환승, AI 도보 산정, 저장값 재사용, 초기 5분 여유, 실제 관측과 개인화, 품질 이력과 로깅.
**확정:** DB는 PostgreSQL, 로컬 개발 DB는 Docker Compose 컨테이너와 영속 볼륨으로 운영한다. React는 DB에 직접 접근하지 않고 FastAPI를 통한다.
**인증 확정:** 이메일·비밀번호. 소셜 로그인은 후속 검토.
**확정:** 지원 지역은 서울특별시·경기도, 카카오맵 사용. **미정:** 메일·실시간 교통 공급자, 배포 주소. 최대 환승은 첫 출시 2회로 확정(20절). AI 공급자는 OpenAI, 모델은 GPT-5.6 Luna (`gpt-5.6-luna`)로 사용자 확정. 사용자가 승인한 커스텀 AI 서버로 최소 연결 확인 완료. 예산·데이터 전달 조건·실제 서비스 품질 검증은 미완료. 카카오맵 선정과 실시간 ID 매핑·저장/AI 전달·실호출 검증 완료는 구분하며 상세 상태는 18절을 따른다.
## 2. 공통 규칙
- API 기본 경로: `/api/v1`. 아래 표는 이 접두사를 생략한다. 실제 서버 URL은 미정이다.
- 요청·응답: JSON, 필드명 snake_case. ID 예시는 가상 값이며 실제 ID는 불투명 문자열로 취급한다.
- 절대 시각: 시간대가 포함된 ISO 8601. 저장·로그는 UTC, 화면은 사용자 시간대. 길이는 초, 거리는 미터.
- 성공: `{"data": ..., "meta": {"request_id": "...", "server_time": "..."}}`. 204는 본문 없이 X-Request-ID 헤더만 반환한다.
- 목록: `data.items`와 `data.next_cursor`. limit 기본 20, 최대 100으로 확정한다.
- 오류: error.code, error.message, error.details 및 meta. 잘못된 입력 전문·토큰·주소를 오류 메시지에 되돌려주지 않는다.
- 자원 수정에는 expected_version을 사용한다. 현재 버전과 다르면 409 VERSION_CONFLICT.
- 인증된 사용자는 서버에서 결정한다. user_id를 요청 본문으로 받아 소유자를 선택하지 않는다.
- 다른 사용자의 자원은 404로 처리한다. 인증 누락·만료는 401.
- 생성·이벤트·재산정 요청은 Idempotency-Key를 지원하는 설계다. 사용자+경로+키로 중복을 방지하고 다른 본문에 같은 키를 쓰면 409. 중복 결과 보관 24시간으로 확정(현재 권한 재검사).
- 비동기 202는 완료가 아니다. job status는 queued/running/succeeded/failed. 작업 상태 조회는 초기2초, 미완료 시5·10·최대30초로 늘리고 비활성 화면에서 중지한다. 서버 Retry-After를 우선한다. 이 조회는 교통 공급자60초 조회와 별개다. 완료 전 다음 의존 작업을 진행하지 않는다.
- JSON 본문 좌표는 위도 -90\~90, 경도 -180\~180. 초는 유한한 숫자, 기간·여유는 음수 금지. 정책별 상한은 공급자·화면 설계 시 확정한다.
### F00-03 공통 호출·요청 ID 연결 (2026-10-06)
- 현재 구현 범위: health 확인과 공통 HTTP 응답/프론트 클라이언트. 회원/교통/AI 업무 API 추가 없음. 공통 클라이언트는 같은 출처의 `/api/v1/` 경로만 호출하고 수동 재시도·요청 취소·기본10초 타임아웃을 처리한다. 자동 재전송 없음, 202는 접수 상태·204는 본문 없음으로 구분한다.
- 서버는 모든 요청에서 request_id를 생성하고 응답 X-Request-ID와 JSON meta에 일치시킨다. 클라이언트가 보낸 임의 X-Request-ID를 신뢰하지 않는다. 오류도 meta.server_time과 같은 ID를 반환한다.
- 미존재 경로404 RESOURCE_NOT_FOUND, 방식 불일치405 METHOD_NOT_ALLOWED(Allow 헤더 유지), 입력 검증422 VALIDATION_ERROR, 예상 밖 오류500 INTERNAL_ERROR를 기존 공통 error/meta 형식으로 정규화한다. 입력 값·예외 상세·주소/키를 오류 메시지에 반사하지 않는다. 검증 details는 안전한 필드명/일반 사유만 반환한다.
- 화면은 기존 서버 연결 카드의 로딩·성공·실패/재확인 상태와 지원 문의용 요청 ID를 표시한다. ID가 없는 네트워크/시간초과 오류에는 서버 ID를 만들지 않는다. 응답 JSON/공통 형식/health 데이터가 잘못되면 정상 연결로 표시하지 않는다. 화면 이탈 시 요청을 취소하고 오래된 결과를 반영하지 않는다.
- F00-03 구현/검증 완료: 프론트 테스트20개·빌드, 백엔드 응답 계약6개·기존 진단27개 통과. 실제 로컬 health200/404/405 및 데스크톱·390×844 모바일 로딩/성공/500 실패/재시도 요청 ID 확인. 프론트 원문 URL/요청·응답/키·예외 로그 없음. 업무 API 미구현, 요청 완료/예상 밖 오류 구조화 로그는 F00-04로 구현했다.
## 3. 인증 방식 결정
첫 버전은 사용자 요청에 따라 이메일·비밀번호 로그인으로 한다. 소셜 로그인은 테스트 이후 배포 확대 시 재검토한다. 서버 저장 세션·HttpOnly 쿠키, CSRF, 이메일 확인·복구·재인증 계약은 17절의 상세 초안을 따른다. 인증 구현과 메일 공급자 선택은 아직 미완료다.
## 4. 기능별 API 목록
GET /health는 구현되어 있으며 그 외 아래 항목은 **미구현**이다. 성공 응답 열은 공통 data 내부 필드를 요약한다.
### 01. 시스템·계정
<table header-row="true">
<tr>
<td>방식·경로</td>
<td>인증</td>
<td>입력</td>
<td>성공 응답</td>
<td>처리 규칙</td>
</tr>
<tr>
<td>`GET /health`</td>
<td>불필요</td>
<td>없음</td>
<td>200: status, server_time</td>
<td>서버 연결 확인. DB·키 등 내부 정보는 노출하지 않음</td>
</tr>
<tr>
<td>`GET /me`</td>
<td>필요</td>
<td>없음</td>
<td>200: user_id, display_name, profile, email_verified</td>
<td>로그인 사용자 확인</td>
</tr>
<tr>
<td>`PATCH /me/profile`</td>
<td>필요</td>
<td>walking_preference, first_boarding_buffer_seconds, transfer_buffer_seconds, route_preference 중 변경값과 expected_version</td>
<td>200: profile, profile_version</td>
<td>첫 탑승 여유 기본 300초. 계수는 클라이언트가 수정하지 않음</td>
</tr>
<tr>
<td>`DELETE /me`</td>
<td>필요</td>
<td>CSRF 및 5분 내 비밀번호 재인증 필요 (17절)</td>
<td>202: job_id, deletion_receipt, receipt_expires_at</td>
<td>계정과 개인 데이터 삭제 작업. 세션 즉시 폐기, 영수증 조회는 17절</td>
</tr>
<tr>
<td>`GET /jobs/{job_id}`</td>
<td>필요</td>
<td>경로: job_id</td>
<td>200: status, result_ref, error</td>
<td>본인 비동기 작업 확인. 계정 삭제 상태 조회는 17절의 X-Deletion-Receipt 헤더 사용</td>
</tr>
</table>
### 02. 장소·출발 위치
<table header-row="true">
<tr>
<td>방식·경로</td>
<td>인증</td>
<td>입력</td>
<td>성공 응답</td>
<td>처리 규칙</td>
</tr>
<tr>
<td>`POST /place-searches`</td>
<td>필요</td>
<td>query: 검색어</td>
<td>200: candidates\[\]</td>
<td>주소가 URL·접근 로그에 남지 않도록 본문 전달. 검색 본문도 로깅 제외</td>
</tr>
<tr>
<td>`GET /places`</td>
<td>필요</td>
<td>cursor?, limit?</td>
<td>200: items\[\], next_cursor</td>
<td>내 고정 장소 목록</td>
</tr>
<tr>
<td>`POST /places`</td>
<td>필요</td>
<td>label, location, entrance_ref?</td>
<td>201: place</td>
<td>집·회사 등록. 좌표·검색 결과 확인</td>
</tr>
<tr>
<td>`GET /places/{place_id}`</td>
<td>필요</td>
<td>경로: place_id</td>
<td>200: place</td>
<td>본인 장소 상세</td>
</tr>
<tr>
<td>`PATCH /places/{place_id}`</td>
<td>필요</td>
<td>label?, location?, entrance_ref?, expected_version</td>
<td>200: place</td>
<td>위치·출입구 변경 시 관련 산정값 무효화</td>
</tr>
<tr>
<td>`DELETE /places/{place_id}`</td>
<td>필요</td>
<td>없음</td>
<td>204: 본문 없음</td>
<td>연관 루틴은 needs_attention 상태로 전환</td>
</tr>
</table>
### 03. 경로·AI 도보
<table header-row="true">
<tr>
<td>방식·경로</td>
<td>인증</td>
<td>입력</td>
<td>성공 응답</td>
<td>처리 규칙</td>
</tr>
<tr>
<td>`POST /journey-searches`</td>
<td>필요</td>
<td>origin, destination, timing, preferences?</td>
<td>202: search_id, job_id</td>
<td>직행·환승 후보 조회와 필요한 AI 도보 산정을 비동기 실행</td>
</tr>
<tr>
<td>`GET /journey-searches/{search_id}`</td>
<td>필요</td>
<td>경로: search_id</td>
<td>200: status, candidates\[\], unavailable_reasons\[\]</td>
<td>완료·진행·실패 구분. 실시간/시간표 근거 표시</td>
</tr>
<tr>
<td>`GET /walking-estimates/{estimate_id}`</td>
<td>필요</td>
<td>경로: estimate_id</td>
<td>200: estimate_id, revision_id, base_seconds, estimated_seconds, source, reused, calculated_at, expires_at</td>
<td>본인 도보 산정값 및 근거 요약</td>
</tr>
<tr>
<td>`POST /walking-estimates/{estimate_id}/recalculations`</td>
<td>필요</td>
<td>reason: user_requested</td>
<td>202: job_id</td>
<td>재산정 요청 제한·중복 방지. 계수만 변경되면 AI 재호출 없이 계산</td>
</tr>
</table>
### 04. 루틴
<table header-row="true">
<tr>
<td>방식·경로</td>
<td>인증</td>
<td>입력</td>
<td>성공 응답</td>
<td>처리 규칙</td>
</tr>
<tr>
<td>`GET /routines`</td>
<td>필요</td>
<td>cursor?, limit?</td>
<td>200: items\[\], next_cursor</td>
<td>출근·퇴근 루틴 목록</td>
</tr>
<tr>
<td>`POST /routines`</td>
<td>필요</td>
<td>name, origin_place_id, destination_place_id, search_id, candidate_id, weekdays, target_arrival_local_time?, timezone</td>
<td>201: routine</td>
<td>본인 검색의 유효 후보만 저장. 실시간 도착 시각을 영구 경로로 저장하지 않음</td>
</tr>
<tr>
<td>`GET /routines/{routine_id}`</td>
<td>필요</td>
<td>경로: routine_id</td>
<td>200: routine</td>
<td>루틴 상세</td>
</tr>
<tr>
<td>`PATCH /routines/{routine_id}`</td>
<td>필요</td>
<td>변경 필드, expected_version; 경로 변경 시 search_id, candidate_id</td>
<td>200: routine</td>
<td>요일·이름·목표 시각·경로 변경</td>
</tr>
<tr>
<td>`DELETE /routines/{routine_id}`</td>
<td>필요</td>
<td>없음</td>
<td>204: 본문 없음</td>
<td>기존 이동 기록은 당시 스냅샷 유지, 삭제된 루틴 참조는 표시용으로만 사용</td>
</tr>
</table>
약속·초대·중간 추천·채팅·공유 API의 입력/응답/권한/이벤트 상세는 이 페이지 16절에 있다. 모든 신규 API는 미구현 설계 초안이다.
### 05. 출발 안내
<table header-row="true">
<tr>
<td>방식·경로</td>
<td>인증</td>
<td>입력</td>
<td>성공 응답</td>
<td>처리 규칙</td>
</tr>
<tr>
<td>`POST /guidance-queries`</td>
<td>필요</td>
<td>routine_id, departure_basis, origin_override?, trip_id?</td>
<td>200: guidance</td>
<td>최신 교통+저장 도보로 출발·환승·여유 계산. 상세 예시 참조</td>
</tr>
</table>
### 06. 이동·관측
<table header-row="true">
<tr>
<td>방식·경로</td>
<td>인증</td>
<td>입력</td>
<td>성공 응답</td>
<td>처리 규칙</td>
</tr>
<tr>
<td>`POST /trips`</td>
<td>필요</td>
<td>guidance_id, measurement_mode: assisted 또는 baseline</td>
<td>201: trip</td>
<td>당시 안내 버전을 연결. baseline도 측정 세션만 생성하고 추천 따르기는 요구하지 않음</td>
</tr>
<tr>
<td>`GET /trips`</td>
<td>필요</td>
<td>cursor?, limit?, from?, to?</td>
<td>200: items\[\], next_cursor</td>
<td>본인 이동 목록</td>
</tr>
<tr>
<td>`GET /trips/{trip_id}`</td>
<td>필요</td>
<td>경로: trip_id</td>
<td>200: trip, events\[\], outcome</td>
<td>진행 중 이동 복구</td>
</tr>
<tr>
<td>`POST /trips/{trip_id}/events`</td>
<td>필요</td>
<td>client_event_id, type, occurred_at, leg_id, source, note_code?</td>
<td>201: event; 동일 이벤트 재전송 200</td>
<td>출발·접근 완료·탑승 등 구분; 중복 방지</td>
</tr>
<tr>
<td>`PATCH /trips/{trip_id}/events/{event_id}`</td>
<td>필요</td>
<td>occurred_at?, excluded?, correction_reason, expected_version</td>
<td>200: event</td>
<td>정정 이력 유지. 영향받는 개인 계수 재생성</td>
</tr>
<tr>
<td>`PATCH /trips/{trip_id}`</td>
<td>필요</td>
<td>outcome: completed/missed/cancelled, expected_version</td>
<td>200: trip</td>
<td>이동 종료 또는 취소</td>
</tr>
<tr>
<td>`DELETE /trips/{trip_id}`</td>
<td>필요</td>
<td>없음</td>
<td>202: job_id</td>
<td>관측·개인화 파생값 정리 후 삭제 완료</td>
</tr>
<tr>
<td>`POST /trip-exports`</td>
<td>필요</td>
<td>from?, to?, format: json</td>
<td>202: job_id</td>
<td>자기 기록만 내보내기. 결과는 인증된 짧은 유효기간 다운로드로 제공</td>
</tr>
</table>
### 07. 개인화·품질
<table header-row="true">
<tr>
<td>방식·경로</td>
<td>인증</td>
<td>입력</td>
<td>성공 응답</td>
<td>처리 규칙</td>
</tr>
<tr>
<td>`GET /me/personalization`</td>
<td>필요</td>
<td>없음</td>
<td>200: status, factors\[\], sample_counts, policy_version</td>
<td>학습 상태와 계수, 순수 보폭 측정값이 아님</td>
</tr>
<tr>
<td>`POST /me/personalization/reset`</td>
<td>필요</td>
<td>없음</td>
<td>202: job_id</td>
<td>계수 기본화, reset 이후 기록만 새 학습에 사용; 과거 기록 재학습 방지</td>
</tr>
<tr>
<td>`GET /me/quality-summary`</td>
<td>필요</td>
<td>from?, to?</td>
<td>200: sample_count, mae_seconds, underprediction_rate, wait_summary</td>
<td>관측 부족 시 숫자를 만들지 않고 null 반환</td>
</tr>
<tr>
<td>`GET /guidance/{guidance_id}/quality`</td>
<td>필요</td>
<td>경로: guidance_id</td>
<td>200: prediction_summary, observation_summary, versions</td>
<td>본인 안내·실제 결과 비교. AI 원문·내부 사고 과정 노출 안 함</td>
</tr>
</table>
## 5. 핵심 요청·응답 예시
아래 값은 합성 예시다. 실제 API를 호출한 결과가 아니다.
### 5.1 집·회사 등록
`POST /api/v1/places`
```json
{
  "label": "집",
  "location": {"latitude": 37.5001, "longitude": 127.0001},
  "entrance_ref": "entrance_demo_01"
}
```
```json
{
  "data": {
    "place_id": "place_demo_01",
    "label": "집",
    "location": {"latitude": 37.5001, "longitude": 127.0001},
    "entrance_ref": "entrance_demo_01",
    "version": 1
  },
  "meta": {"request_id": "req_demo_01", "server_time": "2026-09-30T00:00:00Z"}
}
```
장소 좌표는 필요한 인증 응답에는 포함되지만 일반 실행 로그에는 남기지 않는다.
### 5.2 현재 위치에서 경로 검색
`POST /api/v1/journey-searches`
```json
{
  "origin": {
    "type": "current_location",
    "latitude": 37.5001,
    "longitude": 127.0001,
    "accuracy_meters": 15,
    "captured_at": "2026-09-30T00:00:00Z"
  },
  "destination": {"type": "saved_place", "place_id": "place_work_demo"},
  "timing": {"mode": "depart_now", "timezone": "Asia/Seoul"},
  "preferences": {"route_preference": "fewer_transfers"}
}
```
```json
{
  "data": {"search_id": "search_demo_01", "job_id": "job_demo_01", "status": "queued"},
  "meta": {"request_id": "req_demo_02", "server_time": "2026-09-30T00:00:00Z"}
}
```
origin/destination은 saved_place 또는 좌표 출발 객체다. 권한 거절 시 지도 선택은 type=map_pin과 좌표를 전달한다. 현재 위치의 최신성·정확도가 부족하면 재확인 상태를 반환한다.
목표 도착 검색은 timing.mode=arrive_by와 timing.arrive_by의 절대 시각을 필수로 전달한다. 루틴의 반복 목표는 local time과 timezone으로 별도 저장한다.
후보는 candidate_id, validity, ordered_legs, transfer_count, total_seconds, estimated_arrival_at, time_sources, missing_segments를 포함한다. 후보 ID는 해당 사용자의 search_id 안에서만 유효하다.
### 5.3 도보 결과
`GET /api/v1/walking-estimates/estimate_demo_01`의 data 예시:
```json
{
  "estimate_id": "estimate_demo_01",
  "revision_id": "revision_demo_01",
  "base_seconds": 300,
  "applied_duration_factor": 1.0,
  "estimated_seconds": 300,
  "scope": "place_entrance_to_stop",
  "source": "ai_estimate",
  "reused": true,
  "calculated_at": "2026-09-29T23:00:00Z",
  "expires_at": "2026-10-29T23:00:00Z",
  "prompt_version": "walking_estimate.v1",
  "policy_version": "walk-policy.v1"
}
```
`source`는 산정 방식이고 `reused`는 이번 조회에서 저장값을 사용했는지를 뜻한다. source는 ai_estimate 또는 profile_recalculation이다. reused=true여도 실시간 교통 정보까지 저장값이라는 뜻은 아니다.
### 5.4 출발·여유 안내
`POST /api/v1/guidance-queries`
```json
{
  "routine_id": "routine_demo_01",
  "departure_basis": "recommended"
}
```
```json
{
  "data": {
    "guidance_id": "guidance_demo_01",
    "status": "ready",
    "departure_basis": "recommended",
    "selected_departure_at": "2026-09-30T00:03:00Z",
    "recommended_departure_at": "2026-09-30T00:03:00Z",
    "vehicle_arrival_at": "2026-09-30T00:13:00Z",
    "approach_seconds": 300,
    "buffer_seconds": 300,
    "slack_seconds": 300,
    "slack_status": "meets_buffer",
    "summary": "3분 뒤 출발",
    "message": "3분 뒤 출발하세요. 그때 출발하면 정류장 도착 후 약 5분의 여유가 있어요.",
    "walking_estimate_revision_id": "revision_demo_01",
    "traffic_fetched_at": "2026-09-30T00:00:00Z",
    "valid_until": "2026-09-30T00:01:00Z",
    "transfers": []
  },
  "meta": {"request_id": "req_demo_03", "server_time": "2026-09-30T00:00:00Z"}
}
```
departure_basis=now라면 selected_departure_at은 현재 시각이고 같은 조건의 slack_seconds는 480초다. 원래 권장 시각은 별도 필드로 유지한다.
status는 ready/insufficient_data/no_feasible_journey/stale. 부족하거나 만료된 정보에 slack_seconds를 임의로 채우지 않고 null과 사유를 반환한다. 정상적인 ‘경로 없음’은 200 상태 결과이며 공급자 장애로 처리를 못한 경우는 503이다.
origin_override에는 현재 위치 또는 지도 핀 객체를 전달한다. 이동 중 trip_id가 있으면 남은 경로를 산정해야 하며 전체 도보 시간을 다시 빼지 않는다.
transfers의 각 항목은 leg_id, estimated_alighting_at, transfer_walk_seconds, transfer_buffer_seconds, next_boarding_at, feasibility, time_source를 포함한다. 실시간 근거가 없는 연결은 estimated 또는 unknown으로 표시한다.
### 5.5 실제 이동 이벤트
`POST /api/v1/trips/trip_demo_01/events`
```json
{
  "client_event_id": "client_event_demo_01",
  "type": "approach_arrived",
  "occurred_at": "2026-09-30T00:08:00Z",
  "leg_id": "leg_demo_walk_01",
  "source": "manual"
}
```
type은 departed/approach_arrived/boarded/alighted. 각 이벤트가 가리키는 실제 여정 구간과 순서를 검증한다. 클라이언트 occurred_at 외에 서버 received_at도 저장하고 시계 차이·입력 지연은 품질 판정에 반영한다.
같은 client_event_id와 같은 본문의 재전송은 기존 결과, 같은 ID에 다른 본문은 409다. 관측 정정은 이전 값을 보존하고 학습 파생값을 갱신한다.
출발→접근 완료는 이동 시간, 접근 완료→탑승은 대기 시간이다. 출발→탑승만으로 보행 속도를 학습하지 않는다.
사용자 확정(2026-10-06): 지하철 역 내부 이동의 안내 결과는 역 근처에 도착한 뒤 사용자가 탑승 여부·놓침을 직접 확인하는 수동 기록으로 검증한다. GPS 좌표·고도·근접만으로 승강장 도착이나 탑승을 확정하지 않는다. 기존 boarded 이벤트는 source=manual의 본인 탑승 확인이며 특정 열차에 대한 자동 인증이 아니다. 탑승 시각에는 대기가 섞일 수 있어 접근 완료 기록 없이 역 내부 이동 시간을 역산하거나 보행 학습에 넣지 않는다. 분 단위 시간 입력은 필수가 아니며 기존 출발·접근 완료·탑승 이벤트와 구간 범위를 유지한다. 수동 기록의 입력 지연·누락·정정 및 품질 제외 정책은 기존 규칙을 따른다.
## 6. 계산과 저장 정책
- 첫 탑승 기본 여유: 300초. 접근 시간과 따로 관리하고 개인화 후 자동 축소하지 않는다.
- 출발 권장 시각 = 차량 예상 도착 시각 − 개인 접근 시간 − 설정 여유.
- 특정 출발 시각의 예상 여유 = 차량 예상 도착 시각 − (선택 출발 시각 + 개인 접근 시간).
- 음수 여유는 부족 상태, 60초 미만은 ‘1분 미만’, 정보 부족은 확인 불가로 표시한다.
- 같은 구간·방향·출입구·개인 계수 버전의 유효한 도보 기록은 재사용한다.
- 계수만 변경되면 기준 시간을 재사용해 서버에서 재계산한다. 경로 자체 변경·만료 때만 필요한 지도·AI 조회를 한다.
- AI 결과의 수치·근거 ID·구간 범위를 검증한다. 일반 텍스트로 만든 시간을 무조건 채택하지 않는다.
- 개인화는 유효 관측 5개부터 최근 최대 20개의 관측/기준 시간 비율 중앙값을 사용한다. 새 계수 = 0.8×이전 계수 + 0.2×중앙값, 첫 출시 지원 범위 0.5\~2.0 확정. 세부 정책은 로컬 `personalization.md` 기준.
- 여정 안내가 사용한 산정 버전은 이후 값이 바뀌어도 유지한다. 과거 예측을 현재 계수로 덮어쓰지 않는다.
- 이동 기록 삭제·정정·계정 탈퇴 시 연결된 품질 이력과 개인화 파생값의 정리를 포함한다.
### 출발 확인이 없는 경우 다음 차량 안내 (2026-10-06)
- 사용자 결정: 수동 출발 확인을 받으며, 출발 안내 시각에서 예상 접근 이동시간의 절반을 초과하도록 출발 확인이 없으면 다음 차량 기준으로 안내를 다시 계산한다. 이 기준은 도착정보의 만료 기준이 아니다.
- 계산 기준: W는 정류소/승강장까지 개인화된 예상 접근 시간(역 내부 이동 포함 시 그 시간), B는 별도 탑승 여유다. 현재 안내한 권장 출발 시각 s를 기준으로 `now - s > W / 2`이고 유효한 departed 확인이 없는 경우 적용한다. 전체 대중교통 이동시간/여유 B를 절반 계산에 포함하지 않는다. 기준 시점 s는 이번 요구의 출발 안내 시각으로 해석했다.
- 예: s=12:00, W=600초이면 12:05까지는 절반 초과가 아니며, 12:05를 넘었는데 출발 확인이 없을 때 현재 선택 차량 다음의 이용 가능한 후보로 변경한다. 활성 화면 정기 조회 주기는 기존 확정 60초를 유지하며 그 평가에서 조건을 검사한다. 추가 고빈도 API 조회 규칙을 만들지 않는다.
- 다음 후보도 W+B 및 이후 환승/목표 도착 조건을 검증하고 권장 출발·여유·최종 도착 예상 시각을 재계산한다. 다음 차량 정보가 없거나 만료/근거 부족이면 시각을 만들어내지 않고 insufficient_data로 안내한다. 출발 확인 후에는 이 미확인 규칙으로 자동 변경하지 않는다.
- 기존 manual departed 이벤트를 재사용하며 GPS로 미출발을 판정하지 않는다. 출발 확인 없음은 미이동의 증명이 아니므로 미출발/차량 놓침 관측을 자동 생성하거나 개인화 학습에 넣지 않는다. 새 API 경로/요청·응답 필드 추가 없음, 계산/후보 선택 동작 변경이며 미구현이다.
## 7. 오류 코드
<table header-row="true">
<tr>
<td>HTTP</td>
<td>코드</td>
<td>의미·화면 동작</td>
</tr>
<tr>
<td>401</td>
<td>AUTH_REQUIRED / SESSION_EXPIRED</td>
<td>로그인 필요 또는 재로그인</td>
</tr>
<tr>
<td>404</td>
<td>RESOURCE_NOT_FOUND</td>
<td>없거나 접근할 수 없는 개인 자원</td>
</tr>
<tr>
<td>409</td>
<td>VERSION_CONFLICT / IDEMPOTENCY_CONFLICT / EVENT_ORDER_CONFLICT</td>
<td>최신값 재조회 또는 이벤트 확인</td>
</tr>
<tr>
<td>405</td>
<td>METHOD_NOT_ALLOWED</td>
<td>허용되지 않은 HTTP 방식. Allow 헤더 유지</td>
</tr>
<tr>
<td>422</td>
<td>VALIDATION_ERROR</td>
<td>필수 필드·범위·시각 형식 오류</td>
</tr>
<tr>
<td>429</td>
<td>RATE_LIMITED</td>
<td>Retry-After 후 재시도, 자동 반복 제한</td>
</tr>
<tr>
<td>502</td>
<td>AI_OUTPUT_INVALID</td>
<td>검증 실패로 결과 미저장. 제한된 재시도 후 안내</td>
</tr>
<tr>
<td>503</td>
<td>PROVIDER_UNAVAILABLE</td>
<td>외부 지도·교통·AI 서비스 사용 불가</td>
</tr>
<tr>
<td>504</td>
<td>PROVIDER_TIMEOUT</td>
<td>외부 응답 시간 초과</td>
</tr>
<tr>
<td>500</td>
<td>INTERNAL_ERROR</td>
<td>요청 ID로 조사, 내부 예외 원문 노출 금지</td>
</tr>
</table>
```json
{
  "error": {
    "code": "VALIDATION_ERROR",
    "message": "입력값을 확인해주세요.",
    "details": [{"field": "first_boarding_buffer_seconds", "reason": "음수는 사용할 수 없습니다."}]
  },
  "meta": {"request_id": "req_demo_error", "server_time": "2026-09-30T00:00:00Z"}
}
```
비동기 작업 오류는 작업 조회 자체가 성공하면 HTTP 200, data.status=failed 및 data.error에 위 코드를 전달한다.
## 8. 로깅·품질 이력
서버가 생성한 request_id를 응답 헤더 X-Request-ID와 meta에 함께 넣는다. React의 오류 화면과 백엔드 로그에서 같은 요청을 찾을 수 있어야 한다.
실행 로그: timestamp, level, event, request_id, 경로 템플릿, status_code, duration_ms, 필요한 결과 참조 ID.
품질 DB: AI 입력 근거·구조화 결과·검증 결과, 모델/프롬프트 버전, 안내 당시 교통 정보, 산정 버전, 실제 관측과 개인화 업데이트.
비밀번호·토큰·쿠키·API 키·정밀 주소·좌표·전체 본문은 실행 로그에서 제외한다. AI 내부 사고 과정은 저장하지 않는다. 개인정보가 섞인 예외 메시지도 정제한다.
보관은 실행 로그 14일, 개인 이동/품질 이력 90일로 확정한다. 사용자 삭제/탈퇴 시 연결 사본·학습 참조도 정리하며 상세는 20절을 따른다.
### F00-04 요청 로그 (2026-10-06)
- 요청 완료는 INFO `http.request.completed` 한 번, 처리 중 예상 밖 예외는 같은 서버 request_id의 ERROR `http.request.failed`를 추가한다. 완료 로그에는 UTC timestamp·level·service·event·request_id·method·route·status_code·duration_ms, 오류에는 error_code/exception_type만 포함한다. 처리시간은 단조 시계로 측정한 응답 생성까지의 서버 처리시간이며 전송 완료/클라이언트 응답시간으로 해석하지 않는다.
- route는 등록된 경로 템플릿만 사용하고 미매칭은 unmatched로 기록한다. 실제 경로·쿼리·주소/좌표·IP·헤더/쿠키/키·입출력 본문·예외 메시지/스택/지역변수는 출력하지 않는다. 예상 가능한404/405/422는 완료 로그로 구분하고 사용자 입력 오류를 서버 예외로 기록하지 않는다.
- Python 전용 요청 logger에 JSON 한 줄 stdout 출력을 적용, LOG_LEVEL 기본 INFO 및 INFO/WARNING/ERROR 지원. Uvicorn 원문 URL 접근 로그는 개발 실행 명령에서 끈다. 로그14일 정책은 배포 수집기/회전 설정에서 적용하며 이번 작업은 파일/외부 수집기/보관 작업을 도입하지 않는다.
- F00-04 구현/검증 완료: JSON 요청 완료/예상 밖 오류 stdout·LOG_LEVEL·빈 공급자 키/예시 URL의 환경 설정·로컬 실행/ID 대조 안내. 로그 검증7개 포함 백엔드40개·프론트20개 통과. 실제200/404/405에서 응답/로그ID 일치·요청당 완료1회·합성 경로/쿼리/헤더/본문 값 비노출 확인. health 성공·HTTP 오류/ID 계약 유지, 업무/교통/AI 로그는 해당 기능에서 추가한다.
## 9. 구현 순서와 확인 기준
1. GET /health와 React 연결, 정상·실패 응답 및 request_id 확인.
2. 인증 방식·DB 선택 후 /me와 장소 저장, 타인 데이터 접근 차단 검증.
3. 실제 교통·보행 공급자 연결, 경로 검색과 AI 도보 산정.
4. 루틴 저장, 여유 5분과 환승 연결 계산.
5. 이동 이벤트, 중복 방지, 관측 품질 판정, 개인화와 과거 버전 추적.
6. 기록 삭제·탈퇴·내보내기·모바일 화면 및 지인 테스트.
- GET /health·공통 HTTP 오류/request_id·React 서버 연결은 구현됨. 그 외 업무 API는 미구현이다.
- [ ] 실제 OpenAPI 스키마와 요청·응답 계약 비교는 구현 후 수행한다.
- [ ] 자동화 검증은 계산 경계값·소유권·이벤트 중복·개인화·공급자 실패를 우선한다.
## 10. 결정해야 할 사항
- 메일 공급자·발송 환경과 인증 운영 제한 값 검증. 이메일 인증 API 및 삭제 영수증 조회 초안은 17절.
- 운영 DB 호스팅·백업 정책, 지도·환승·실시간 도착·AI 공급자 및 지원 범위. 로컬 개발 DB는 PostgreSQL Docker로 확정.
- 설정값 허용 상한, 검색 결과 및 작업·내보내기 결과 유효기간은 20절에 확정했다. 구현 및 경계 검증은 미완료.
- 첫 출시 화면 내 출발 안내 포함, 백그라운드 푸시/예약 알림·자동 출발 감지는 제외(20절). 새 푸시 API 없음.
- 배포 URL과 프론트엔드 허용 출처.
## 11. 프론트 화면 프로토타입 상태
2026-10-01: `C:/projects/timeisnow/frontend`에 React 화면 검토용 프로토타입을 추가했다. 홈·루틴 편집·경로 상세·직행 및 환승 이동 단계·체험 기록·설정 화면을 제공한다. 상세 구성은 로컬 `screen_plan.md`를 참고한다.
실제 API, 로그인, 지도, AI, 실시간 교통, 푸시는 아직 미연동이다. 모든 시간·경로는 합성 예시이며 루틴과 이벤트는 브라우저 메모리에만 유지된다. API 구현 완료로 분류하지 않는다.
기본 5분 여유와 정보 만료 시 권고 중단 등 기존 계약을 시각화했으며 새 엔드포인트나 계약 변경은 없다. UI 체험의 1\~10분 설정 범위는 서버 허용 범위를 확정한 것이 아니다.
검증: 주요 사용자 흐름 테스트 5개와 프로덕션 빌드 통과. 초기 접속 문제 해결 후 브라우저에서 데스크톱 홈 및 390×844 모바일 홈·루틴·편집 창을 확인했다. 실제 휴대전화와 API 연동 검증은 아직 미완료.
## 12. 확장 기획: 일회성 약속과 출발 상태 공유
2026-10-02: 사용자 요청으로 기획에 추가. 전체 미구현이며 기존 통근 MVP 이후의 확장 범위다. 상세 로컬 문서는 `meeting_plan.md`다. 첫 약속 확장은 최대 2명(혼자 사용 가능)으로 확정하고 통근 핵심 이후 진행한다. 다인 지원은 후속 검토다.
### 목적과 사용자 흐름
반복 루틴뿐 아니라 일회성 약속도 출발 안내를 제공한다. 약속 생성 → 친구 초대 → 장소·시간 확정 → 개인별 출발 안내 → 출발 상태·예상 도착 공유 → 만남 종료 흐름이다. 장소가 정해졌으면 바로 등록하고, 미정이면 중간 만남 후보를 비교한다. 혼자 가는 일정은 초대 없이 이용한다. 약속별 채팅으로 조율하되 확정 버튼으로 저장한 장소·시간을 계산 기준으로 삼는다.
상대가 실제로 오고 있는지 알기 어려워 반복 연락하거나 불안하게 기다리는 경험을 줄이고, 출발과 도착 정보를 투명하게 공유하여 약속에 대한 신뢰 형성을 돕는다. 효과는 검증할 가설이며 사람의 성실성·신뢰도를 점수로 평가하는 기능은 이번 범위에 넣지 않는다.
### 출발 근거와 공유 정책
- 초기 수동 출발 기록은 ‘본인이 출발을 알림’으로 표시한다. 버튼 클릭·서버 수신만으로 실제 이동이 검증되었다고 표현하지 않는다. GPS·센서 자동 감지는 후속 검토이며 확인 근거·오탐·권한 정책 확정 전 구현하지 않는다.
- 공유는 사용자가 약속별로 선택하고 수락한 참여자에게만 제공하는 설계 제안이다. 출발 상태, 신고 시각, 예상 도착, 최종 갱신 시각, 지연·공유 중단 상태를 최소 범위로 제공한다. 집 주소·정밀 위치·이동 궤적은 기본 공유하지 않는다.
- 공유 중단, 통신 끊김, 오래된 예측은 ‘미출발’이나 ‘약속 불이행’으로 해석하지 않는다. 정정·취소는 최신 상태에 반영하고 서버 저장 전 상대에게 확정 상태로 전달하지 않는다.
- 약속 시각까지의 여유와 첫 탑승 기본 여유 300초는 구분한다. 예상 도착은 예측이며 정보 부족·만료 시 단정적인 도착 시각을 제공하지 않는다.
- 예시: ‘민수님이 18:20에 출발을 알렸어요 · 본인 입력 / 예상 도착 18:55 · 18:21 갱신’. 자동 확인 배지는 제공하지 않는다.
### 기존 계약 영향과 설계 미정
기존 `POST /guidance-queries`의 `routine_id` 필수 계약은 유지한다. 약속은 16절의 별도 `POST /meetings/{meeting_id}/guidance-queries`로 안내를 생성하고 기존 trips/events에 연결한다. 신규 계약은 미구현 설계 초안이다.
기존 `departed` 이벤트의 `source=manual`, `occurred_at`, `received_at`을 근거로 재사용 가능성을 검토한다. `POST /trips` 생성만으로 출발 상태를 공유하지 않는다. 개인 이동 API의 본인 접근 규칙은 유지하고 참여자에게는 허용된 요약만 별도 제공한다.
약속·초대·참여 권한, 확정 버전, 채팅·공유의 경로/필드/오류/전송 상세 초안은 16절에 작성했다. 인원·기간·보관/삭제 정책은 20절, 인증 방식은 17절에 확정했다. 실제 구현은 미완료다. 중복·순서 역전·재접속·초대 만료·참여 취소·약속 취소도 정의한다. 장소·시간 변경 시 기존 안내를 무효화하고 참여자별로 다시 계산한다.
저장 후보는 약속/참여자/확정 버전/개인 여정 연결/공유 동의·철회/출발 근거·정정 이력/도착 예측 스냅샷/채팅이다. 보관 기간, 약속 종료 후 공유 종료 시점, 삭제·탈퇴 시 공동 기록 처리 정책은 구현 전 확정한다. 채팅 본문·정밀 위치는 실행 로그에 복제하지 않고 이벤트 ID와 처리 결과로 추적한다. 기존 개인 품질 이력과 분리한다.
### 포팅 범위와 검증
`product`의 React/FastAPI 중간역 추천·방·채팅을 재사용 후보로 검토했다. 기존 2인 지하철 정적 계산은 대기를 제외하므로 버스·도보·환승·실시간 도착을 포함한 안내로 그대로 사용하지 않는다. 방 URL만으로 대화를 보는 정책은 초대 참여자 권한으로 재설계한다. 포팅 및 실행 검증은 아직 수행하지 않았다.
완료 기준: 일회성 약속 안내, 참여자 외 접근 차단, 수동 출발 표시, 중복·정정·철회·재접속 처리, 정보 만료 표현, 변경된 약속의 재계산, 탑승 여유와 약속 여유 구분. 효과 검증은 반복 확인 연락 감소, 기다림 불안에 대한 피드백, 예상·실제 도착 오차로 제안하며 출발 기록만으로 성실성을 판정하지 않는다.
## 13. PostgreSQL 개발 환경
2026-10-02 사용자 요청으로 PostgreSQL을 확정했다. 프로젝트 전용 Docker Compose 서비스와 영속 볼륨을 사용하고 호스트 접속은 127.0.0.1로 제한한다. 비밀번호는 Git 제외된 로컬 환경 파일에 보관하며 예제·로그에 실제 값을 남기지 않는다. 컨테이너 재생성으로 업무 데이터를 초기화하지 않는다. 업무 테이블·마이그레이션은 해당 기능 계약을 확인한 뒤 추가한다. 구성 및 연결 검증 결과는 로컬 `database.md`와 `development_log.md`에 기록한다. 기존 API 요청·응답과 개인정보 보관·삭제 계약은 유지한다.
## 14. 테이블·연관관계 설계 초안
2026-10-02: 로컬 `database_schema.md` v0.1에 PostgreSQL 논리 설계, 핵심 컬럼·FK·제약, MVP/약속 ERD, 삭제 정책, API 대응 및 생성 순서를 작성했다. **설계 제안이며 DDL·마이그레이션 미적용**이다. 현재 public 업무 테이블이 없음을 조회로 확인했다.
### 테이블 구성
- 회원·장소: `users`, `user_profiles`, `saved_places`. 인증 저장소는 방식 선택 후 설계.
- 경로·루틴: `journey_searches`, `journey_plans`, `journey_legs`, `routines`. 검색 후보 ID는 plan ID에 대응하고 소유권·검색 소속·유효성을 검증한다.
- AI 도보: `walking_paths`, `walking_estimates`, `walking_estimate_revisions`, `ai_executions`. 기준 경로와 개인화 산정 버전을 분리한다.
- 안내·이동: `guidance_snapshots`, `guidance_legs`, `trips`, `trip_guidances`, `trip_events`, `trip_event_revisions`, `walking_observations`.
- 개인화: `personalization_profiles`, `personalization_updates`, `personalization_update_samples`. 관측 버전과 학습 표본을 연결하고 리셋 세대·중복 갱신 방지를 둔다.
- 공통: `jobs`, `idempotency_requests`.
- 약속 확장 제안: `meetings`, `meeting_members`, `meeting_revisions`, `meeting_invites`, `meeting_recommendations`, `meeting_journeys`, `meeting_messages`, `meeting_share_events`. 신규 API·권한·보관/삭제 정책 확정 후 생성한다.
### 관계와 이력 정책
회원 1:N 장소·루틴·이동, 경로 1:N 구간, 산정 1:N 불변 revision, 안내 1:N 구간별 예측, 이동 1:N 이벤트/재안내, 이벤트 1:N 정정 이력이다. 회원과 약속은 참여자 테이블을 통한 N:M이며 개인 경로·출발 기록은 참여자별로 연결한다.
당시 예측은 나중에 학습된 값으로 덮어쓰지 않는다. 실제 출발/접근 완료/탑승을 분리하고 관측은 정확한 이벤트 revision과 예측을 참조한다. 수동 출발 신고를 실제 이동 자동 검증으로 취급하지 않는다.
개인 FK는 같은 소유자의 자원만 연결하도록 복합 FK와 트랜잭션 검증을 제안한다. 같은 약속 소속·현재 참여 권한도 검증한다. 필수 값, 초/미터 단위와 UTC 시각, 중복 이벤트의 UNIQUE 조건, expected_version에 대응하는 version을 명시한다. 계산된 slack_seconds는 음수를 허용하며 정보 부족은 NULL이다.
장소 삭제 시 루틴을 needs_attention으로 바꾸고 과거 안내 맥락은 기존 정책대로 유지한다. 개인 이동/회원 삭제는 관측·계수·근거·캐시·내보내기 등 파생 사본 정리를 포함한다. 약속 공동 기록의 탈퇴·삭제/보관은 16절/20절의 30일 및 개인 삭제 규칙을 따른다. 무조건 CASCADE하거나 영구 보관하지 않는다.
### 적용 범위
기존 API 경로·입출력·오류 계약은 변경하지 않는다. 기존 leg_id는 경로 구간 ID로 유지하고 서버가 이동에 연결된 안내 구간을 검증한다. 현재 guidance 요청의 routine_id 필수 조건도 유지한다. 약속은 16절의 별도 안내 API 및 meeting_journey 연결 초안을 따른다. DB 설계에는 재전송 이벤트·일회용 티켓 테이블과 약속 안내 FK를 추가할 예정이며 DDL은 미적용이다.
테이블 설계 문서와 Alembic 마이그레이션 기반(F00-05b)을 완료했다. 개발 DB에는 업무 테이블 없이 alembic_version의 0001_baseline 이력만 적용했다. 격리된 임시 스키마에서 적용·중복 적용·되돌리기·재적용을 검증했다. 실제 업무 테이블 생성과 FK/동시성/권한/삭제 테스트는 미완료다. 인증·장소부터 기능별로 생성하고 약속 테이블을 먼저 모두 만들지 않는다.
## 15. 마이그레이션 실행 기반
2026-10-02: Alembic 1.20.0과 SQLAlchemy 2.1.1 설치 및 버전 고정. 루트 alembic.ini와 backend/migrations에서 명시적 변경 파일을 관리하고 backend/[migrate.py](http://migrate.py)로 실행한다. DB 접속 설정은 기존 비공개 .env/프로세스 설정을 재사용하며 앱 시작 시 자동 변경하지 않는다. 초기 0001_baseline은 업무 DDL이 없는 기준점이다. 상세 명령·한계는 로컬 [migrations.md](http://migrations.md)에 기록했다. 업무 테이블과 인증 방식은 별도 단계에서 확정한다.
## 16. 친구 약속·채팅 상세 API
- 문서 버전: 0.2 / 2026-10-06 / 대응 Notion API 버전: 0.26
- 상태: **상세 설계 초안, 전체 미구현**. 요청/응답 예시는 합성 데이터다.
- 기존 공통 계약과 함께 사용한다. D03\~D05 위임 결정으로 수치/보관 정책은 20절과 아래에 확정했다. 서비스 구현은 미완료다.
- 범위: 약속 생성·초대·중간 만남 추천·확정·개인 출발 안내·채팅·출발 공유·재접속.
- 친구 목록/친구 요청, 공개 신뢰 점수, 파일 채팅, 읽음 표시, 상시 위치 추적은 포함하지 않는다.
### 1. 공통·정책·권한
REST 접두사 /api/v1. 전부 로그인 필요. 로그인은 17절의 서버 세션·HttpOnly 쿠키 계약을 따른다. user_id/member_id로 요청자의 신원을 지정할 수 없으며 서버 인증값을 사용한다. 쿠키 선택 시 변경 REST의 CSRF 방어를 포함한다.
성공은 \{data,meta:\{request_id,server_time\}\}, 오류는 \{error:\{code,message,details\},meta\}. 204는 본문 없이 X-Request-ID. 아래 성공 열은 data 내부다. 모든 날짜는 시간대 있는 ISO8601, 기간은 초, 거리 미터, ID는 문자열. JSON에서 ?가 붙은 설명은 선택/NULL 허용이며 실제 필드명에 ?를 붙이지 않는다.
생성/처리 POST에는 Idempotency-Key 필수(1\~128 ASCII, 보관 24시간 확정). user+method+자원 ID 포함 경로+키로 중복 방지. 같은 본문은 최초 성공 응답 재현, 다른 본문은 409 IDEMPOTENCY_CONFLICT. 처리 중 재요청은 409 REQUEST_IN_PROGRESS 및 Retry-After: 1. 재시도 전에 현재 권한을 다시 검사한다. 메시지에는 별도 client_message_id 중복 방지도 적용한다. 읽기 성격 POST인 초대 미리보기와 매 연결마다 새로 발급하는 realtime-tickets에는 키가 필요 없다.
변경에는 expected_version 정수 \>=1. meeting_version/member.version/message.version은 각각 다른 자원 버전이다. 서버는 충돌 시 409 VERSION_CONFLICT, details에 current_version을 포함하며 접근 권한 없는 사람에게는 반환하지 않는다.
<table header-row="true">
<tr>
<td>항목</td>
<td>확정 설계 정책(2026-10-06)</td>
</tr>
<tr>
<td>참여 인원</td>
<td>첫 버전 최대 2명(생성자 포함), 혼자 사용 가능. 다인 확장은 별도 검토</td>
</tr>
<tr>
<td>제목</td>
<td>trim 후 1\~100 Unicode 코드 포인트</td>
</tr>
<tr>
<td>초대</td>
<td>1회 수락, 유효 24시간, 활성 초대 1개/약속</td>
</tr>
<tr>
<td>목록</td>
<td>limit 기본 20/최대 100, 불투명 cursor. 변경된 필터에 이전 cursor 재사용 금지</td>
</tr>
<tr>
<td>채팅</td>
<td>일반 텍스트 trim 후 1\~1000 코드 포인트, HTML 해석 없음, 수정 미지원·본인 삭제 지원</td>
</tr>
<tr>
<td>초대 토큰 / WS 티켓</td>
<td>원본 로그 금지, DB에 해시. WS 티켓은 30초 내 1회 사용</td>
</tr>
<tr>
<td>추천</td>
<td>최대 3개, 결과 유효 5분, 참여자 출발 정보가 바뀌면 즉시 무효화</td>
</tr>
<tr>
<td>공유 ETA</td>
<td>계산 후 최대 120초 및 교통 근거 유효기간 중 짧은 값까지만 유효</td>
</tr>
<tr>
<td>속도 제한</td>
<td>채팅 사용자·약속당 10회/10초, 추천 약속당 3회/분, 초대 미리보기 사용자당 10회/분. 429+Retry-After</td>
</tr>
<tr>
<td>보관</td>
<td>종료/취소 후 약속·채팅 30일, 이벤트 재전송 24시간. 미사용 draft 30일, confirmed는 목표 시각 6시간 후 자동 종료. 실제 삭제 작업 검증은 구현 시 수행</td>
</tr>
</table>
상태: meeting=draft/confirmed/completed/cancelled. 생성은 draft, 확정은 confirmed, 확정 후 변경도 새 revision을 만들고 confirmed 유지. completed/cancelled는 읽기만 가능하며 초대·추천·채팅 전송·출발 공유·개인 안내 생성은 중단한다. 허용된 본인 메시지 삭제·약속 삭제는 가능하다.
활성 참여자만 약속 상세·채팅·공유를 조회한다. 탈퇴한 참여자와 비참여자는 404 RESOURCE_NOT_FOUND. 활성 참여자에게 주최자 전용 작업을 거절할 때만 403 MEETING_ROLE_REQUIRED. 주최자는 약속 변경/확정/종료/취소/삭제와 초대 발급·철회를 수행한다. 상대도 추천 요청, 본인 출발지 설정, 본인 채팅, 본인 공유 설정은 가능하다. 상대의 전체 개인 경로·주소·원본 이동/AI 기록 조회는 불가하다.
### 2. 응답 객체
<table header-row="true">
<tr>
<td>객체</td>
<td>필드</td>
</tr>
<tr>
<td>Meeting</td>
<td>meeting_id:string, title:string, status:enum, version:int, organizer_member_id:string, max_members:int, member_count:int, current_revision:MeetingRevision/null, members:Member\[\], created_at:datetime, updated_at:datetime</td>
</tr>
<tr>
<td>Member</td>
<td>member_id:string, display_name:string, role:organizer/participant, participation_status:active/left, origin_ready:bool, version:int. 공유 설정의 원본과 개인 좌표는 타인에게 반환하지 않음</td>
</tr>
<tr>
<td>MeetingRevision</td>
<td>revision_id:string, revision_no:int, target_arrival_at:datetime, timezone:string, destination:Destination, confirmed_at:datetime</td>
</tr>
<tr>
<td>Destination</td>
<td>name:string(1\~100), latitude:number\[-90,90\], longitude:number\[-180,180\], provider:string/null, place_ref:string/null. 공동 목적지만 공유</td>
</tr>
<tr>
<td>PrivateOrigin</td>
<td>origin:기존 saved_place/current_location/map_pin 중 하나, origin_version:int, recommendation_consent:bool, updated_at:datetime</td>
</tr>
<tr>
<td>Candidate</td>
<td>candidate_id:string, destination:Destination, journeys:\[\{member_id,estimated_seconds:int,transfer_count:int,time_source:realtime/timetable/estimated\}\], max_seconds:int, difference_seconds:int, explanation:string/null</td>
</tr>
<tr>
<td>Message</td>
<td>message_id:string, meeting_id:string, sender_member_id:string, sender_display_name:string, client_message_id:string, body:string/null, sent_at:datetime, deleted_at:datetime/null, version:int</td>
</tr>
<tr>
<td>SharedStatus</td>
<td>member_id:string, state:unknown/reported_departed/in_transit/arrived/unavailable/sharing_off, source:manual/estimated/none, reported_at:datetime/null, estimated_arrival_at:datetime/null, eta_calculated_at:datetime/null, valid_until:datetime/null, updated_at:datetime, version:int</td>
</tr>
</table>
일반 조회는 활성 members만 반환한다. 메시지에 남은 탈퇴한 작성자는 '탈퇴한 참여자'로 표시한다. SharedStatus의 arrived는 본인 도착 신고이며 자동 위치 인증이 아니다. in_transit도 본인이 입력한 탑승 등 이벤트를 근거로 하므로 실제 GPS 검증을 뜻하지 않는다.
### 3. 약속·초대 API
<table header-row="true">
<tr>
<td>방식·경로</td>
<td>권한 / 입력</td>
<td>성공·처리</td>
</tr>
<tr>
<td>POST /meetings</td>
<td>로그인. \{title\}</td>
<td>201 Meeting. 생성자 member를 함께 저장, draft/version=1</td>
</tr>
<tr>
<td>GET /meetings</td>
<td>로그인. status?:상태 enum, cursor?, limit?</td>
<td>200 \{items:Meeting\[\],next_cursor\}. 본인이 활성 참여 중인 약속만, created_at/id 내림차순</td>
</tr>
<tr>
<td>GET /meetings/\{meeting_id\}</td>
<td>활성 참여자. 입력 없음</td>
<td>200 Meeting</td>
</tr>
<tr>
<td>PATCH /meetings/\{meeting_id\}</td>
<td>주최자. \{title,expected_version\}</td>
<td>200 Meeting. 열린 약속만, 장소·시각은 확정 API로 변경</td>
</tr>
<tr>
<td>POST /meetings/\{meeting_id\}/confirmations</td>
<td>주최자. \{expected_version,target_arrival_at,timezone,destination\} 또는 \{expected_version,target_arrival_at,timezone,recommendation_id,candidate_id\}</td>
<td>201 \{meeting:Meeting,revision:MeetingRevision\}. 두 목적지 선택 방식은 XOR. 미래 시각 필수, IANA timezone 검증</td>
</tr>
<tr>
<td>POST /meetings/\{meeting_id\}/transitions</td>
<td>주최자. \{expected_version,status:completed/cancelled\}</td>
<td>200 Meeting. completed는 confirmed에서만, cancelled는 draft/confirmed에서만</td>
</tr>
<tr>
<td>DELETE /meetings/\{meeting_id\}</td>
<td>주최자. 쿼리 expected_version:int</td>
<td>202 \{job_id\}. 접근 즉시 차단 후 공동 기록 삭제. 개인 trip은 유지하되 약속 FK/공유 연결을 해제하고 개인 보관 정책 적용</td>
</tr>
<tr>
<td>POST /meetings/\{meeting_id\}/invites</td>
<td>주최자. \{expected_version\}</td>
<td>201 \{invite_id,token,expires_at,meeting_version\}. 기존 활성 초대 철회 후 새 초대 발급. 만석이면 409</td>
</tr>
<tr>
<td>DELETE /meetings/\{meeting_id\}/invites/\{invite_id\}</td>
<td>주최자. 쿼리 expected_version:int(약속 버전)</td>
<td>204. 철회 및 약속 버전 증가. 다른 약속 초대는 404</td>
</tr>
<tr>
<td>POST /meeting-invite-previews</td>
<td>로그인. \{token:string\}</td>
<td>200 \{title,organizer_display_name,member_count,max_members,expires_at\}. 주소·대화·참여자 상세 반환 안 함</td>
</tr>
<tr>
<td>POST /meeting-invite-acceptances</td>
<td>로그인. \{token:string\}</td>
<td>200 \{meeting_id,member:Member,meeting_version\}. 원자적으로 잔여 인원 검사·토큰 소비·member 저장</td>
</tr>
<tr>
<td>DELETE /meetings/\{meeting_id\}/members/me</td>
<td>본인 활성 참여자. 쿼리 expected_version:int(member 버전)</td>
<td>204. 주최자는 409 ORGANIZER_CANNOT_LEAVE. 상대 탈퇴 시 접근·공유·기존 연결 차단, 개인 데이터 정리</td>
</tr>
</table>
초대 token은 256비트 이상 난수의 URL-safe 문자열, 본문 길이 32\~256 제안이다. 링크를 만들면 브라우저 fragment에 넣어 읽고 수락 요청 본문으로 전송한다. 서버 URL/쿼리·로그에 원문을 남기지 않는다. 위 API는 링크를 반환할 뿐 자동으로 친구에게 발송하지 않는다.
만료/철회/존재하지 않는 초대는 모두 404 INVITE_UNAVAILABLE. 같은 사람이 이미 수락한 같은 토큰을 재요청하면 아직 활성 참여 중일 때 200 반환, 다른 사람은 404. 신규 수락과 만석 검사는 약속 행 잠금 안에서 처리한다. 동일 사용자는 member가 중복 생성되지 않는다. 초대 발급의 멱등 응답 재현을 위해 필요한 token 응답은 만료/소비/철회 전까지만 암호화된 응답 캐시에 보관한다. 영구 초대 레코드에는 해시만 둔다. 캐시 정리 후 같은 키에는 409 INVITE_RESPONSE_EXPIRED를 반환하며 새 발급이 필요하다. 탈퇴 후 재참여는 새 초대를 요구한다.
멤버 추가/탈퇴는 약속 버전을 올리고 기존 중간 추천을 무효화한다. 실제 장소·시각이 같으면 확정 revision 자체는 바꾸지 않는다. 삭제된 약속 접근은 주최자도 404이며 삭제 job만 본인 조회 가능하다.
### 4. 개인 출발지·중간 만남 추천
<table header-row="true">
<tr>
<td>방식·경로</td>
<td>입력</td>
<td>성공·처리</td>
</tr>
<tr>
<td>PUT /meetings/\{meeting_id\}/members/me/origin</td>
<td>\{origin, recommendation_consent:bool, expected_version:member버전\}</td>
<td>200 \{private_origin:PrivateOrigin,member_version\}. 본인만 조회 가능. consent=true는 서버가 중간 추천 계산에 사용할 동의이며 집 주소 공개 동의가 아님</td>
</tr>
<tr>
<td>GET /meetings/\{meeting_id\}/members/me/origin</td>
<td>없음</td>
<td>200 PrivateOrigin 또는 null</td>
</tr>
<tr>
<td>POST /meetings/\{meeting_id\}/recommendations</td>
<td>\{expected_version:약속버전,target_arrival_at,timezone\}</td>
<td>202 \{recommendation_id,job_id,status:queued\}. 활성 2명, 둘 다 origin·추천 동의가 있어야 함</td>
</tr>
<tr>
<td>GET /meetings/\{meeting_id\}/recommendations/\{recommendation_id\}</td>
<td>활성 참여자</td>
<td>200 \{recommendation_id,status:queued/running/succeeded/failed/stale,candidates:Candidate\[\],expires_at:datetime/null,outcome:available/no_feasible_journey/null,error:공통오류객체/null\}</td>
</tr>
</table>
origin은 기존 경로 검색 객체와 같다. saved_place는 본인 place_id, current_location은 latitude/longitude/accuracy_meters/captured_at, map_pin은 latitude/longitude를 받는다. 외부에 개인 출발지를 노출하지 않는다. 다른 사람에게는 origin_ready만 제공한다.
추천의 시간과 동의·출발지 버전·활성 멤버 집합을 고정해 저장한다. 계산 완료 시에도 버전을 다시 검사한다. 바뀌면 stale, 결과를 확정에 사용할 수 없다. 시간 차이와 최대 이동시간을 함께 비교하는 초기 순위 정책을 제안하며 정책 버전을 저장한다. 실제 데이터가 부족하면 후보를 꾸며내지 않는다. 성공했지만 후보 없음은 status=succeeded, candidates=\[\], outcome=no_feasible_journey, error=null이다. 후보가 있으면 outcome=available, 진행 중/실패/만료면 outcome=null이다.
후보 응답은 목적지와 개인별 총 예상시간·환승 수만 공유한다. 개인 출발역/주소/경로 좌표는 제외한다. AI 설명 실패는 explanation=null로 처리하며 검증된 시간/순위를 AI 문장으로 덮어쓰지 않는다. 설명용 프롬프트 세부 버전은 구현 전 별도 작성한다.
확정 시 추천과 후보의 약속 소속, 참여자·출발 정보 버전, 만료, target_arrival_at 일치를 확인한다. 직접 지정 목적지는 서버에서 유효성을 확인한다. 새 확정 revision은 기존 개인 안내를 stale로 만들고 출발 공유 ETA를 무효화한다.
### 5. 약속 전용 출발 안내와 기존 이동 API 연결
<table header-row="true">
<tr>
<td>방식·경로</td>
<td>입력</td>
<td>성공·처리</td>
</tr>
<tr>
<td>POST /meetings/\{meeting_id\}/guidance-queries</td>
<td>\{meeting_revision_id,departure_basis:recommended/now,origin_override?:기존위치객체,trip_id?:string\}</td>
<td>200 \{meeting_journey_id,meeting_revision_id,guidance:기존안내객체,meeting_arrival_slack_seconds:int/null\}. 본인의 저장 출발지 또는 override 사용</td>
</tr>
<tr>
<td>POST /meetings/\{meeting_id\}/arrivals</td>
<td>\{meeting_journey_id,client_event_id,occurred_at,source:manual\}</td>
<td>201 \{arrival_id,version:1,received_at,source:manual\}. 같은 ID·본문 재전송 200, 다른 본문 409</td>
</tr>
</table>
약속이 confirmed이고 최신 revision이어야 한다. 오래된 revision은 409 MEETING_REVISION_CHANGED. 출발지가 없으면 409 ORIGIN_REQUIRED. 근거 부족·경로 없음은 기존 guidance.status를 사용하고 값을 NULL로 둔다. 계산 중 약속이 바뀌어도 성공 결과로 내보내지 않는다.
첫 안내는 개인별 meeting_journey와 guidance를 연결한다. 같은 약속 revision·본인 여정의 재조회는 기존 여정을 사용하며 경로 변경/이전 이동 종료 후 새 이동은 새 여정을 만든다. trip_id는 본인·해당 약속 여정의 이동만 허용한다.
반환된 guidance.guidance_id를 기존 POST /trips에 전달한다. 서버가 guidance의 meeting_journey 연결을 따라 trip_id를 붙인다. 하나의 여정에 이미 진행 중 trip이 있으면 새 생성은 409 ACTIVE_TRIP_EXISTS. 루틴의 기존 POST /guidance-queries 요청은 변경하지 않으며 routine_id는 계속 필수다.
출발/정류장 도착/탑승/하차는 기존 POST /trips/\{trip_id\}/events와 정정 API를 재사용한다. 약속 arrivals는 최종 목적지 도착을 기록하는 별도 본인 신고이며 기존 type enum을 임의로 늘리지 않는다. 개인 보행 학습에는 넣지 않는다. arrivals는 연결된 trip에 departed가 있어야 한다. 잘못된 도착 신고는 아래 공유 상태의 '정정' 작업과 함께 새 기록으로 대체하며 원본은 보관 정책에 따라 이력 처리한다.
meeting_arrival_slack_seconds = target_arrival_at - estimated_arrival_at. 기존 guidance.slack_seconds는 첫 탑승 전 여유이며 별도 필드다. 5분 기본 여유를 약속 전 여유로 중복 계산하지 않는다.
### 6. 공유 설정·상태
<table header-row="true">
<tr>
<td>방식·경로</td>
<td>입력</td>
<td>성공·처리</td>
</tr>
<tr>
<td>PATCH /meetings/\{meeting_id\}/members/me/sharing</td>
<td>\{enabled:bool,expected_version:member버전\}</td>
<td>200 \{enabled,member_version,updated_at\}. 처음은 false, 과거 이력을 일괄 공개하지 않음</td>
</tr>
<tr>
<td>GET /meetings/\{meeting_id\}/shared-statuses</td>
<td>활성 참여자</td>
<td>200 \{items:SharedStatus\[\]\}. 비공유 사용자는 sharing_off와 NULL 시간만 제공</td>
</tr>
<tr>
<td>POST /meetings/\{meeting_id\}/arrival-corrections</td>
<td>\{arrival_id,expected_version,occurred_at?:datetime,excluded?:bool,correction_reason:wrong_time/wrong_action\}</td>
<td>201 \{arrival_id,version,received_at\}. 원본 보존·새 정정 이력, 본인 것만 가능</td>
</tr>
</table>
공유 enabled=true인 상태에서 저장에 성공한 departed/boarded 등 이벤트와 서버 산정 ETA를 공유 상태에 반영한다. **클라이언트가 상대에게 공개할 ETA를 직접 지정할 수 없다.** 서버가 개인 경로로 계산한다. trips 생성·WS 접속 자체는 출발이 아니다.
공유 도중 켜면 그 순간 본인 최신 상태 요약만 공유하고 과거 원문 이벤트는 제공하지 않는다. 출발 이벤트 정정/삭제, 도착 정정은 공유 상태에 반영한다. 정상 공유 상태 변경과 재전송 이벤트 저장은 같은 트랜잭션으로 처리한다.
철회·탈퇴·약속 종료·취소 시 ETA/출발 시각을 다음 응답에서 제거하고 연결된 클라이언트에 상태 무효화를 전달한다. 동의 철회로 본인 trip 학습까지 자동 삭제하지는 않는다. 네트워크 단절과 ETA 만료는 unavailable이며 '아직 출발 안 함'으로 단정하지 않는다. 이미 상대 기기에 표시된 내용을 소급 회수할 수 있다고 약속하지 않는다.
공유 기본 꺼짐, 종료 시점은 약속 종료/취소/본인 철회 중 먼저 발생한 때. 종료 처리가 없는 경우 확정 약속 시각 6시간 후 자동 종료한다. confirmed 약속도 이 시점에 completed로 정리하되 실제 참석/도착 판정은 하지 않는다. 종결 뒤 공유 재활성화는 409 MEETING_CLOSED.
### 7. 채팅 REST
<table header-row="true">
<tr>
<td>방식·경로</td>
<td>입력</td>
<td>성공·처리</td>
</tr>
<tr>
<td>GET /meetings/\{meeting_id\}/messages</td>
<td>before?:메시지 커서, limit?:기본20/최대100</td>
<td>200 \{items:Message\[\],next_cursor\}. 최신 구간을 오래된 순서로 반환, 다음 커서는 더 오래된 구간</td>
</tr>
<tr>
<td>POST /meetings/\{meeting_id\}/messages</td>
<td>\{client_message_id:UUID문자열,body:string\} + Idempotency-Key</td>
<td>201 Message. 저장 commit 후 알림. client_message_id가 같고 body가 같으면 200, 다르면 409 MESSAGE_ID_CONFLICT</td>
</tr>
<tr>
<td>DELETE /meetings/\{meeting_id\}/messages/\{message_id\}</td>
<td>쿼리 expected_version:message버전</td>
<td>204. 본인만, 타인 메시지는 403 MESSAGE_DELETE_FORBIDDEN(참여자 한정)</td>
</tr>
</table>
같은 Idempotency-Key 재전송은 공통 규칙에 따라 최초 HTTP 응답 재현(201 가능), 다른 키지만 같은 client_message_id이면 200이다. 삭제는 body=NULL인 tombstone으로 바꾸고 version을 증가시킨다. API 삭제 후 재전송이 본문을 되살리지 않도록 저장된 요청 해시/멱등 응답도 정리한다. 이미 삭제된 메시지의 동일 버전 삭제 재시도는 204, 그 외 충돌은 409. 전송 중 화면은 pending, REST 성공 또는 서버 이벤트를 받으면 message_id/client_message_id로 하나로 합친다.
채팅으로 '7시에 만나'라고 말해도 약속 시각을 자동 수정하지 않는다. 확정 API가 유일한 확정 기준이다. 상대 접속 중 여부와 관계없이 DB에 저장되면 전송 성공이며 읽음/전달 완료를 의미하지 않는다.
### 8. WebSocket 인증·이벤트·복구
#### 연결
POST /meetings/\{meeting_id\}/realtime-tickets
- 활성 참여자, 빈 본문 \{\}. 매 연결별 새 발급이므로 Idempotency-Key 예외이며 사용자당 10회/분 제한.
- 201 data=\{ticket:string,expires_at:datetime,websocket_path:"/api/v1/ws/meetings/\{meeting_id\}"\}.
- 만료 30초·1회 소비. 네트워크 오류로 응답을 잃으면 새 티켓을 요청한다. 이전 티켓은 사용/만료 시 소멸하며 원문 응답을 멱등 캐시에 저장하지 않는다.
- WS는 브라우저 기본 인증 헤더 지원에 의존하지 않고 첫 메시지 auth로 티켓을 전달한다. 토큰을 URL에 넣지 않는다.
- 운영 wss, 개발 [localhost](http://localhost) ws. 허용 Origin만 연결. 첫 5초 안에 auth 없으면 4401 종료.
- 서버는 인증 전 어떤 약속 데이터도 보내지 않는다. 티켓의 약속·사용자·현재 활성 참여 권한을 다시 검증한다.
클라이언트 프레임:
```json
{"type":"auth","request_id":"wsreq_demo_1","data":{"ticket":"synthetic_ticket","after_seq":"0"}}
```
seq는 약속 단위 증가 bigint를 **십진수 문자열**로 전달한다. 서버가 약속별 잠금 안에서 이벤트와 seq를 저장한 뒤 commit 이후 송신한다. client request_id는 상관관계용이고 HTTP 서버 request_id와 다르며 로그 신뢰 식별자로 사용하지 않는다.
서버 프레임:
```json
{"type":"chat.message.created","event_id":"evt_demo_1","seq":"42","meeting_id":"meeting_demo_1","occurred_at":"2026-10-02T09:00:00Z","data":{"message_id":"message_demo_1"}}
```
<table header-row="true">
<tr>
<td>서버 이벤트</td>
<td>data</td>
</tr>
<tr>
<td>ready</td>
<td>\{member_id,current_seq,replay_from_seq\} (제어 메시지, seq 없음)</td>
</tr>
<tr>
<td>chat.message.created</td>
<td>\{message_id\}</td>
</tr>
<tr>
<td>chat.message.deleted</td>
<td>\{message_id,version\}</td>
</tr>
<tr>
<td>meeting.updated</td>
<td>\{meeting_version,revision_id:null/string,status\}</td>
</tr>
<tr>
<td>member.updated</td>
<td>\{member_id,member_version,participation_status\}</td>
</tr>
<tr>
<td>sharing.updated</td>
<td>\{member_id,status_version\}</td>
</tr>
<tr>
<td>access.revoked</td>
<td>\{reason:membership_ended/meeting_deleted/session_expired\} 이후 종료 (제어 메시지, seq 없음)</td>
</tr>
<tr>
<td>resync_required</td>
<td>\{reason:cursor_expired/cursor_invalid\} (제어 메시지)</td>
</tr>
<tr>
<td>error</td>
<td>\{code,message,request_id?\} (제어 메시지)</td>
</tr>
<tr>
<td>pong</td>
<td>\{client_time:string\} (제어 메시지)</td>
</tr>
</table>
이벤트에는 채팅 본문·개인 주소·티켓·ETA 원문을 넣지 않는다. 클라이언트는 알림 후 REST로 권한을 다시 검사한 최신 데이터만 조회한다. 채팅 작성 직후 REST 성공 응답과 WS 알림의 순서는 달라도 된다. GET /meetings/\{meeting_id\}/messages/\{message_id\}는 활성 참여자에게 200 Message(삭제면 body=NULL), 없으면 404를 반환한다.
클라이언트는 auth와 ping(\{type:"ping",data:\{client_time\}\})만 보낸다. chat.send 같은 미정 이벤트로 메시지를 쓰지 않는다. 미지원 프레임은 error.code=UNSUPPORTED_EVENT. 프레임 최대 8KiB, 위반 종료 1009. 25초 간격 ping, 60초 무응답 종료로 확정한다. 일반 클라이언트가 서버 공유 상태를 임의로 갱신하는 프레임은 없다.
#### 복구
GET /meetings/\{meeting_id\}/sync
- 200 \{meeting:Meeting,shared_statuses:SharedStatus\[\],recent_messages:Message\[\],next_message_cursor:string/null,last_seq:string\}.
- 최근 메시지 최대20개와 last_seq를 **같은 일관된 DB 스냅샷**에서 읽는다.
- 첫 접속: sync → ticket → auth(after_seq=last_seq). 그 사이 commit된 이벤트는 저장 로그에서 재전송.
- 재접속: 마지막 처리 seq로 auth. 서버는 (after_seq,current_seq\]를 재생한 뒤 실시간으로 전환한다. 전환 사이 누락을 막기 위해 동일 이벤트 저장소를 기준으로 읽는다.
- event_id/seq로 중복 제거, 순서 역전/누락 감지 시 sync 후 재연결. 정확히 한 번 전송을 보장하지 않고 최소 한 번 수신에 맞춰 처리한다.
- 24시간 로그 만료, 미래 seq, 권한 없는 기간의 seq는 resync_required 후 4409로 종료. 클라이언트는 sync부터 다시 시작.
- 정기 sync는 연결 복구/오래된 상태 갱신 수단이며 폴링 주기를 제품상 확정하지 않는다.
- 세션 만료 4401, 권한 상실 4403, 인증/티켓 실패 4401, 서버 장애 1011. 재연결은 1·2·4·8·최대30초+지터. 4401은 로그인/티켓 갱신, 4403은 재시도 중지.
- 종료/취소된 약속은 채팅 열람은 가능하지만 출발 상태는 공유 종료로 표시. 세션/참여권한은 연결 시와 재전송·실시간 발송 시 확인한다.
### 9. 주요 요청·응답 예시
약속 생성:
```json
{"title":"토요일 저녁 약속"}
```
201:
```json
{"data":{"meeting_id":"meeting_demo_1","title":"토요일 저녁 약속","status":"draft","version":1,"organizer_member_id":"member_demo_1","max_members":2,"member_count":1,"current_revision":null,"members":[{"member_id":"member_demo_1","display_name":"민수","role":"organizer","participation_status":"active","origin_ready":false,"version":1}],"created_at":"2026-10-02T09:00:00Z","updated_at":"2026-10-02T09:00:00Z"},"meta":{"request_id":"req_demo_1","server_time":"2026-10-02T09:00:00Z"}}
```
직접 장소 확정:
```json
{"expected_version":3,"target_arrival_at":"2026-10-03T19:00:00+09:00","timezone":"Asia/Seoul","destination":{"name":"약속 장소 예시","latitude":37.5,"longitude":127.0,"provider":null,"place_ref":null}}
```
채팅 전송:
```json
{"client_message_id":"a0000000-0000-4000-8000-000000000001","body":"7시에 입구에서 만나자!"}
```
201:
```json
{"data":{"message_id":"message_demo_1","meeting_id":"meeting_demo_1","sender_member_id":"member_demo_1","sender_display_name":"민수","client_message_id":"a0000000-0000-4000-8000-000000000001","body":"7시에 입구에서 만나자!","sent_at":"2026-10-02T09:01:00Z","deleted_at":null,"version":1},"meta":{"request_id":"req_demo_2","server_time":"2026-10-02T09:01:00Z"}}
```
공유 상태 일부 예시(data.items의 원소):
```json
{"member_id":"member_demo_1","state":"reported_departed","source":"manual","reported_at":"2026-10-03T18:20:00+09:00","estimated_arrival_at":"2026-10-03T18:55:00+09:00","eta_calculated_at":"2026-10-03T18:21:00+09:00","valid_until":"2026-10-03T18:22:00+09:00","updated_at":"2026-10-03T18:21:00+09:00","version":4}
```
화면: '민수님이 출발을 알렸어요 · 본인 입력 / 예상 도착 18:55 · 18:21 갱신'. 위 값은 가상 예시이며 위치 검증 표시를 붙이지 않는다.
### 10. 오류와 상태 전이
<table header-row="true">
<tr>
<td>HTTP</td>
<td>code</td>
<td>조건 / 화면 처리</td>
</tr>
<tr>
<td>401</td>
<td>AUTH_REQUIRED / SESSION_EXPIRED</td>
<td>로그인·세션 갱신</td>
</tr>
<tr>
<td>403</td>
<td>MEETING_ROLE_REQUIRED / MESSAGE_DELETE_FORBIDDEN</td>
<td>참여자는 맞지만 권한 없음</td>
</tr>
<tr>
<td>404</td>
<td>RESOURCE_NOT_FOUND / INVITE_UNAVAILABLE</td>
<td>없음·비참여·다른 약속 자원 또는 사용할 수 없는 초대</td>
</tr>
<tr>
<td>409</td>
<td>VERSION_CONFLICT / IDEMPOTENCY_CONFLICT / REQUEST_IN_PROGRESS</td>
<td>최신 데이터 조회 또는 같은 키로 제한된 재시도</td>
</tr>
<tr>
<td>409</td>
<td>MEETING_FULL / MEETING_CLOSED / ORGANIZER_CANNOT_LEAVE / INVITE_RESPONSE_EXPIRED</td>
<td>인원·종료·주최자 탈퇴 제한</td>
</tr>
<tr>
<td>409</td>
<td>MEETING_NOT_CONFIRMED / MEETING_REVISION_CHANGED</td>
<td>확정 필요 또는 새 확정 버전 재조회</td>
</tr>
<tr>
<td>409</td>
<td>ORIGIN_REQUIRED / RECOMMENDATION_NOT_READY / RECOMMENDATION_STALE</td>
<td>본인 출발지 또는 상대 준비·추천 유효성 확인</td>
</tr>
<tr>
<td>409</td>
<td>ACTIVE_TRIP_EXISTS / EVENT_ORDER_CONFLICT / MESSAGE_ID_CONFLICT</td>
<td>기존 이동 복구, 시각·순서·중복 본문 확인</td>
</tr>
<tr>
<td>422</td>
<td>VALIDATION_ERROR</td>
<td>타입·문자 길이·시각·좌표·필수 필드 오류</td>
</tr>
<tr>
<td>429</td>
<td>RATE_LIMITED</td>
<td>Retry-After 이후 재시도</td>
</tr>
<tr>
<td>503/504</td>
<td>PROVIDER_UNAVAILABLE / PROVIDER_TIMEOUT</td>
<td>경로·교통 공급자 실패; 기존 값으로 성공처럼 안내하지 않음</td>
</tr>
</table>
```json
{"error":{"code":"MEETING_REVISION_CHANGED","message":"약속 장소 또는 시간이 변경됐어요. 다시 확인해주세요.","details":[{"field":"meeting_revision_id","reason":"stale"}]},"meta":{"request_id":"req_demo_error","server_time":"2026-10-02T09:02:00Z"}}
```
모든 자원 소속 확인은 존재·인증/권한 확인 후 버전·상태·필드 계산으로 이어진다. 상태 전이 불가(예: draft→completed)는 409 MEETING_NOT_CONFIRMED, 이미 종결된 약속 변경은 MEETING_CLOSED. 예상 밖 서버 오류는 기존 500 INTERNAL_ERROR.
### 11. 저장·삭제·로깅과 DB 영향
확정: completed/cancelled 이후 공동 기록 30일 후 삭제. draft는 마지막 사용자 변경부터 30일 미사용이면 접근 차단/삭제, confirmed는 목표 시각 6시간 후 completed 자동 정리(실제 참석 판정 아님). 주최자 명시적 삭제는 즉시 접근 차단 및202 작업으로 정리한다. 비주최자 약속 탈퇴는 개인 출발 입력·공유/티켓을 정리하고 공동 메시지는 보관기간까지 탈퇴한 참여자로 표시한다. 계정 탈퇴 시 본인 메시지 본문/공유/티켓도 삭제한다. 주최자 계정 탈퇴는 약속 자동 취소/공유 종료 후 다른 활성 참여자의 공동 30일 열람 기간을 적용한다. 개인 trip은 약속 연결을 해제하고 개인 90일 정책을 적용한다.
다른 사람이 적은 메시지에 개인정보가 있을 수 있으므로 작성자 탈퇴 처리만으로 모든 개인정보 삭제가 보장된다고 표현하지 않는다. 기존 개인 품질 이력·trip 삭제 정책은 유지하며 공동 약속과 따로 정리한다. 공유 철회 후 재전송 로그에 개인 상태 원문을 남기지 않는다.
기존 8개 약속 테이블에 다음 컬럼·테이블 설계를 추가한다(DDL 미적용).
- meetings: max_members, last_event_seq, closed_at, delete_after; members: private_origin jsonb, origin_version, recommendation_consent 및 버전/공유 종료.
- recommendations: target_arrival_at, input member/version 목록, status, job_id, error. 메시지: version와 본문 해시, share_events: version·정정 대상·arrival 기록.
- meeting_realtime_events 신규: meeting_id, seq, event_id, type, entity_ref, occurred_at, expires_at; UNIQUE(meeting_id,seq), 이벤트 본문에는 민감한 내용 제외. 24시간 청소.
- meeting_realtime_tickets 신규: token_hash UNIQUE, member_id, expires_at, consumed_at, auth_session_ref. 연결 종료/세션 무효화 시 정리.
- 약속 안내 FK는 guidance_snapshots에 meeting_journey_id? 추가. routine_id와 동시 사용 금지, 기존 기록의 루틴 삭제로 둘 다 NULL일 수 있음.
- arrivals와 arrival-corrections는 meeting_share_events에 private 원본/정정 관계로 저장하고 공유 동의와 별개로 본인 기록을 유지. GET 공용 상태는 동의한 최신 요약만 제공.
로그 이벤트: meeting.created/confirmed/closed, invite.accepted/rejected, chat.message.persisted/deleted, sharing.updated, realtime.connected/disconnected/resync. request_id·자원 참조·결과·소요 시간만 기록하며 본문·주소·좌표·초대/티켓 원문·쿠키 금지.
### 12. 구현 전 확인과 완료 기준
이번 문서의 2인·기간·길이·속도 제한·탈퇴 공동 기록 정책은 위임 결정으로 확정(20절)했다. 인증 계약은 17절, 실제 공급자 지원/권한·보관/삭제 실행 검증은 기능 구현 시 수행한다. 문서 결정 완료와 기능 구현 완료는 별도다.
- [ ] 비참여자/탈퇴자/다른 약속 ID로 REST·WS·재전송 접근 차단.
- [ ] 동시 초대 수락에서 정원 초과·중복 가입 방지.
- [ ] 약속 변경 중 추천/안내 결과가 저장돼도 오래된 확정으로 성공하지 않음.
- [ ] REST 성공/WS 알림 순서가 달라도 메시지 중복 표시 없음.
- [ ] commit 직후 프로세스 종료·재접속에도 sync+이벤트 이력으로 누락 복구.
- [ ] 토큰 만료/소비/로그 제외 및 회원 세션 만료 중 연결 해제.
- [ ] 수동 출발과 자동 감지 구분, ETA 만료·공유 철회·정정 반영.
- [ ] 삭제·탈퇴·기간 청소가 메시지 본문·개인 입력·티켓·캐시에 함께 반영.
- [ ] 기존 루틴 안내 요청·응답의 회귀 검증과 약속 여유/탑승 여유 분리.
## 17. 이메일·비밀번호 인증 상세 계약
- 버전 0.1 / 2026-10-02 / 전체 미구현
- 사용자 확정: 첫 버전은 이메일·비밀번호 로그인. 소셜 로그인은 테스트 이후 배포 확대 시 재검토하며 현재 구현 범위에서 제외한다.
- 아래 세션·검증·제한 수치는 구현 기준으로 제안하는 설계값이다. 인증 방식 결정과 실제 인증 구현 완료를 구분한다.
- PostgreSQL에 회원·자격정보·서버 세션을 저장한다. 로그인 상태는 HttpOnly 쿠키로 전달하며 JWT/localStorage 기반 인증은 첫 버전에 추가하지 않는다.
- 인증 API는 기존 /api/v1 접두사와 data/meta 및 error/meta 공통 응답을 따른다.
### 1. 입력·비밀번호·메일 정책
- email: 문자열 최대254자. 앞뒤 공백 제거, 도메인 소문자화, 서비스 로그인 식별자는 전체 소문자로 통일하는 정책을 채택한다. 최초 입력도 표시용으로 보관하며 점/플러스 주소를 임의 병합하지 않는다. 이메일 형식 검증과 실제 소유 확인을 구분한다.
- password: 15\~128 Unicode 코드 포인트. 공백·붙여넣기 허용, trim/조용한 절단/대소문자 변환 금지. 문자 종류 조합을 강제하지 않고 흔한/유출 비밀번호 차단 목록을 구현 시 적용한다.
- display_name: trim 후 1\~30자.
- Argon2id 해시와 라이브러리 생성 salt를 저장한다. 초기 최소 설정 memory=19456KiB, time_cost=2, parallelism=1을 기준으로 실제 서버에서 비용을 측정한다. 비밀번호 원문/복호화 가능한 암호문은 보관하지 않는다.
- 이메일 확인 전 계정 상태는 pending_verification. 비밀번호가 맞으면 제한 세션을 발급하지만 장소·루틴·약속 등 업무 API는 403 EMAIL_VERIFICATION_REQUIRED. /me, 확인 메일 재요청, 확인 완료, 로그아웃, 재인증·탈퇴는 허용한다.
- 이메일 확인 토큰은 24시간, 비밀번호 재설정 토큰은 30분 제안. 256비트 이상 난수, DB에는 해시·목적·만료·소비 시각만 저장. 서로 다른 목적의 토큰을 교차 사용하지 않는다.
- 메일 링크는 프론트의 고정 허용 URL로만 만든다. 요청 Host 헤더를 그대로 신뢰하지 않는다. URL fragment에서 토큰을 읽어 POST 본문으로 전달하고 브라우저 주소에서 즉시 제거한다. GET 링크 접근만으로 토큰을 소비하지 않는다.
- 확인 성공 시 기존 제한 세션을 폐기하고 로그인 화면으로 안내한다. 재설정 성공도 전체 세션·WS 티켓을 폐기하고 다시 로그인한다.
- 메일 공급자는 아직 미정이다. 로컬 개발은 외부 발송 없는 메일 캡처 도구를 사용할 수 있으나 토큰을 일반 로그/응답에 노출하지 않는다. 전달 큐에 안전하게 접수되기 전 메일 요청을 성공처럼 표시하지 않는다.
### 2. 세션·CSRF 계약
- 운영 쿠키: __Host-timeisnow_session, HttpOnly, Secure, SameSite=Lax, Path=/, Domain 없음. 로컬 HTTP에서는 별도 timeisnow_dev_session 및 Secure=false를 개발 환경에만 허용한다.
- 세션 원본은 256비트 이상 난수이며 DB에는 해시만 저장. 최대 수명7일, 미사용24시간 제안. 요청마다 서버가 만료·폐기·회원 상태를 검사한다. 무한 연장하지 않는다.
- 로그인 시 세션 ID·CSRF 토큰 교체, 로그아웃/탈퇴/비밀번호 변경 시 폐기. /me 응답에는 세션 원문을 포함하지 않는다. 같은 계정 다중 기기는 허용하되 각각 별도 세션이다.
- GET /auth/csrf는 세션에 묶인 csrf_token을 반환한다. 로그인 전에는 수명15분의 임시 세션을 만들며 동일 쿠키 보안 속성을 적용한다.
- 모든 POST/PUT/PATCH/DELETE(로그인·가입·토큰 소비 포함)에 X-CSRF-Token과 허용 Origin 검증을 적용한다. CSRF 불일치는 403 CSRF_INVALID. 토큰은 프론트 메모리에만 두고 새로고침 시 재조회한다.
- 로그인 성공 응답은 새 세션의 csrf_token을 포함한다. 이전 토큰은 재사용하지 않는다. logout 이후에도 다시 /auth/csrf부터 시작한다.
- 프론트와 API는 운영에서 같은 origin reverse proxy, 개발은 Vite 프록시를 기본 설계로 한다. credentials 포함 요청, wildcard+credential CORS 금지.
- 별도 refresh-token API는 만들지 않는다. 만료 시 로그인, 서버 미사용 만료 갱신은 절대 만료를 넘지 않는다.
- 기존 WS 티켓은 auth_[sessions.id](http://sessions.id)에 연결한다. 로그아웃·세션 만료 시 연결을 4401로 닫고 티켓도 무효화한다.
### 3. API 목록
아래 \{\} 필드는 모두 필수이며 ?만 선택이다. 성공 열은 공통 data 내부다.
<table header-row="true">
<tr>
<td>방식·경로</td>
<td>인증 / 입력</td>
<td>결과</td>
</tr>
<tr>
<td>GET /auth/csrf</td>
<td>비로그인 가능 / 없음</td>
<td>200 \{csrf_token:string,expires_at:datetime\}; Cache-Control:no-store</td>
</tr>
<tr>
<td>POST /auth/register</td>
<td>임시 세션+CSRF / \{email,password,display_name\}</td>
<td>201 \{user_id,email_verification_required:true\}. pending 회원·해시·프로필(첫 여유300초)·확인메일 큐 생성. 자동 로그인 안 함</td>
</tr>
<tr>
<td>POST /auth/login</td>
<td>임시/기존 세션+CSRF / \{email,password\}</td>
<td>200 \{user_id,email_verified:bool,session_expires_at:datetime,csrf_token:string\} + Set-Cookie</td>
</tr>
<tr>
<td>GET /me</td>
<td>로그인 / 없음</td>
<td>기존 user_id,display_name,profile + email_verified:bool 추가. pending도 조회 가능</td>
</tr>
<tr>
<td>POST /auth/logout</td>
<td>CSRF / \{\}</td>
<td>204. 세션 폐기·쿠키 제거. 유효한 CSRF 컨텍스트에서 이미 로그아웃이면 204</td>
</tr>
<tr>
<td>POST /auth/email-verification-requests</td>
<td>CSRF / \{email\}</td>
<td>202 \{message:"해당하는 계정이 있으면 안내 메일을 보냈어요."\}. 존재/확인 여부에 동일 응답</td>
</tr>
<tr>
<td>POST /auth/email-verifications</td>
<td>임시/기존 세션+CSRF / \{token\}</td>
<td>200 \{verified:true,login_required:true\}. 토큰 원자적 소비, 이미 확인된 사용자의 미소비 유효 토큰은 성공 처리</td>
</tr>
<tr>
<td>POST /auth/password-reset-requests</td>
<td>CSRF / \{email\}</td>
<td>202 \{message:"해당하는 계정이 있으면 안내 메일을 보냈어요."\}. 계정 존재와 무관한 상태/문구</td>
</tr>
<tr>
<td>POST /auth/password-resets</td>
<td>임시/기존 세션+CSRF / \{token,new_password\}</td>
<td>200 \{password_reset:true,login_required:true\}. 원자적 비밀번호 갱신·토큰 소비·전체 세션 및 나머지 복구 토큰 폐기</td>
</tr>
<tr>
<td>POST /auth/reauthentications</td>
<td>로그인+CSRF / \{password\}</td>
<td>200 \{reauthenticated_until:datetime\}; 해당 세션에 5분 유효한 재인증 표시</td>
</tr>
</table>
등록 이메일 중복은 409 EMAIL_UNAVAILABLE. 회원 존재 노출 가능성이 있는 UX 선택임을 기록하며, 비밀번호 오류/없는 계정의 로그인은 모두 401 INVALID_CREDENTIALS로 통일한다. 등록 재전송으로 기존 비밀번호를 덮어쓰지 않는다. pending 계정은 동일 정규 이메일로 중복 생성하지 않는다.
이메일 확인은 비밀번호 재설정이 아니다. 메일을 받은 사람이 자신이 가입하지 않은 계정의 확인 링크를 승인하지 않도록 안내한다. pending 가입 보관/재가입 정리는 운영 전 별도 확정하고 기존 계정을 자동 활성화하지 않는다.
인증 POST는 사용자 기준 Idempotency-Key 일반 규칙의 예외이며 원문 비밀번호/메일 토큰을 응답 캐시에 넣지 않는다. 계정 email unique, 토큰 1회 소비, 세션 폐기로 중복을 통제한다. 토큰 재사용/만료/존재하지 않음은 모두 400 AUTH_TOKEN_INVALID. 서버 상태 확인 후 재요청 또는 새 메일 요청으로 복구한다.
### 4. 계정 삭제와 오류
기존 DELETE /me는 로그인+CSRF 및 5분 이내 재인증을 요구한다. 실패는 403 REAUTHENTICATION_REQUIRED. 성공 202 \{job_id,deletion_receipt,receipt_expires_at\}. 삭제 접수와 함께 모든 로그인 세션/WS를 무효화하고 쿠키를 제거한다.
삭제 작업에 한해 GET /jobs/\{job_id\}에 X-Deletion-Receipt 헤더를 허용한다. 수명24시간의 난수 receipt는 해당 job 조회만 허용하고 DB에는 해시로 저장한다. 이 헤더를 다른 API 인증에 사용할 수 없다. 접근 로그·반환 메타데이터에 복제하지 않는다. 만료/잘못된 영수증은 404. 원문은 삭제 응답에서 한 번만 제공하며 클라이언트 메모리에서만 관리한다. 새로고침 후 복구가 필요하면 별도 사용자 지원 흐름을 검토한다.
<table header-row="true">
<tr>
<td>HTTP</td>
<td>code</td>
<td>처리</td>
</tr>
<tr>
<td>401</td>
<td>INVALID_CREDENTIALS</td>
<td>이메일 또는 비밀번호를 확인해주세요</td>
</tr>
<tr>
<td>401</td>
<td>AUTH_REQUIRED / SESSION_EXPIRED</td>
<td>로그인 필요/재로그인</td>
</tr>
<tr>
<td>403</td>
<td>CSRF_INVALID / EMAIL_VERIFICATION_REQUIRED / REAUTHENTICATION_REQUIRED</td>
<td>CSRF 재조회/메일 확인/비밀번호 재확인</td>
</tr>
<tr>
<td>409</td>
<td>EMAIL_UNAVAILABLE</td>
<td>해당 이메일로 가입할 수 없음, 로그인·복구 안내</td>
</tr>
<tr>
<td>400</td>
<td>AUTH_TOKEN_INVALID</td>
<td>토큰 만료/사용됨/잘못됨 통일</td>
</tr>
<tr>
<td>422</td>
<td>VALIDATION_ERROR</td>
<td>형식·길이 오류, 비밀번호 입력값을 details에 반사하지 않음</td>
</tr>
<tr>
<td>429</td>
<td>RATE_LIMITED</td>
<td>Retry-After 후 재시도</td>
</tr>
<tr>
<td>503</td>
<td>AUTH_DELIVERY_UNAVAILABLE</td>
<td>메일 큐/발송 서비스 접수 불가. 계정 존재와 무관하게 같은 서비스 상태 적용</td>
</tr>
</table>
로그인 속도 제한 초기값: 정규 이메일의 키 해시당 5회 실패/15분 + IP당30회/15분. 영구 계정 잠금은 하지 않는다. 가입은 IP당5회/시간, 메일 요청은 이메일 키당3회/시간 및 IP당20회/시간 제안. 분산 서버에서도 공통 제한 저장소가 필요하며 구현 전 선택한다. 메일 요청은 균일한 응답 경로를 사용하고 외부 발송을 동기 대기하지 않는다.
### 5. 저장 테이블
<table header-row="true">
<tr>
<td>테이블</td>
<td>주요 필드·관계</td>
</tr>
<tr>
<td>auth_credentials</td>
<td>user_id PK/FK(users), email_normalized UNIQUE, email_display, password_hash, email_verified_at?, password_changed_at, version</td>
</tr>
<tr>
<td>auth_sessions</td>
<td>id, user_id? FK(users), token_hash UNIQUE, csrf_token_hash, created_at,last_seen_at,absolute_expires_at,idle_expires_at,revoked_at?,reauthenticated_until?. user_id NULL은 임시 로그인 전 세션</td>
</tr>
<tr>
<td>auth_action_tokens</td>
<td>id,user_id FK, purpose:verify_email/reset_password, token_hash UNIQUE, expires_at,consumed_at?</td>
</tr>
<tr>
<td>auth_mail_outbox</td>
<td>id,user_id?,kind,encrypted_payload,status,created_at,expires_at,sent_at?,attempt_count. 원문 토큰은 발송에 필요한 짧은 기간만 암호화 보관 후 제거</td>
</tr>
</table>
회원 users의 상태 pending_verification/active/deleting 등을 인증 처리에서 검증한다. 일반 로그에 이메일 원문·비밀번호·쿠키·토큰·메일 본문·암호화 키를 기록하지 않는다. 임시/만료 세션과 소비/만료 토큰은 정기 청소한다. 가입/메일 요청 실패 시 트랜잭션 처리와 재전송으로 유령 계정·중복 발송을 통제한다. 회원 삭제 시 위 개인 인증 데이터도 정리하고 삭제 영수증은 jobs의 별도 만료 수명으로 관리한다.
소셜 auth_identities, OAuth 콜백·공급자 버튼은 이번 테이블/API 범위에서 제외한다. 추후 도입 시 이메일 일치만으로 계정을 자동 병합하지 않고 별도 계정 연결 계약을 만든다.
### 6. 진행 상태와 다음 결정
D01은 이메일·비밀번호 방식 및 관련 API 설계 문서 작성으로 완료 처리한다. 세션 수명·제한 값은 구현 시 검증 가능한 설계 기본값이며 성능·운영 요구에 따라 명세와 함께 조정한다. 인증 기능 F02, 인증 테이블 DDL, 메일 공급자/발송 설정과 운영 보관 정책은 미완료다.
다음 착수 전 결정은 D02(지원 지역·지도/교통/AI 공급자)다. 구현 단계로 건너뛰지 않는다. 메일 공급자 선택은 F02 구현 전 의존 작업으로 별도 TODO에 남긴다.
설계 참고: [OWASP 비밀번호 저장](https://cheatsheetseries.owasp.org/cheatsheets/Password_Storage_Cheat_Sheet.html), [인증](https://cheatsheetseries.owasp.org/cheatsheets/Authentication_Cheat_Sheet.html), [비밀번호 재설정](https://cheatsheetseries.owasp.org/cheatsheets/Forgot_Password_Cheat_Sheet.html).
## 18. 지원 지역 및 공급자 검토 (2026-10-06)
- 사용자 확정: 첫 지원 지역은 서울특별시·경기도. 인천은 자동 포함하지 않는다. AI 공급자는 OpenAI, 모델은 GPT-5.6 Luna (`gpt-5.6-luna`)로 사용자 확정(2026-10-06).
- 사용자 확정(2026-10-06): 카카오맵을 사용한다. 지도·장소 검색·대중교통·도보 경로 연동은 카카오맵 기준으로 검증한다. 선정 결정과 실제 응답·지원 범위·ID 매핑·저장/AI 전달 조건 검증 완료는 구분한다.
- 실시간 버스 도착은 서울특별시/경기도 공공 API를 별도 연동하는 안을 추천한다. 경로 예상 소요시간을 차량의 실시간 도착으로 취급하지 않는다. 지하철 실시간 정보와 운영기관별 시간표는 노선별 지원 검증 후 선정한다.
- 카카오 경로의 정류장·노선·방향을 공공 API ID와 신뢰성 있게 매핑할 수 있는지가 실시간 연동의 검증 조건이다. 이름만 일치하는 매핑은 사용하지 않는다. 실패하면 ODsay 대중교통 경로+지역 ID 연동을 대안으로 비교한다. 보행 대안은 TMAP이다.
- 서울·경기도 지역 확정과 모든 노선의 실시간 지원 보장은 구분한다. 출발/목적지 지역 판정, 타 지역 통과·환승 허용 여부와 상세 오류 정책은 관련 서비스 기능 구현 시 확정한다. 정보 부족은 기존 insufficient_data 정책을 적용하고 확정적인 출발 권고를 하지 않는다.
- 카카오 공식 일간 쿼터: 첫 활성화 앱 기준 대중교통·도보 각 1,000건. 추가 쿼터 사용 요금은 각각 건당10원(2026-10-06 공식 문서 재확인, 변경 가능). 개발 콘솔의 실제 적용 조건을 재확인한다. 앱 생성과 키 저장은 사용자 수행 보고이며, 2026-10-06 장소 검색 REST 실호출은 확인했다. 실제 무료 쿼터 적용·유료 활성화 여부는 콘솔 미확인이다. 서울 공개 역 주변 도보/대중교통 각 1회 실호출을 확인했으며 지역·노선 전체 지원 검증은 미완료다.
- 고정 장소 도보 재사용을 위해 원본 경로, 파생 도보 시간, AI 전달, 품질 이력의 저장·가공·제3자 전달 허용 조건을 각각 확인한다. 문서 열람만으로 장기 저장을 허용받았다고 간주하지 않는다. 도보 산정 재사용은 앱 정책으로 30일 확정(20절)하며 공급자 별도 승낙 확인과 구분한다. 사용자 지시로 조건 추가 확인은 생략한다.
- D02는 일부 진행: 지역 결정·추천안 작성·사용자의 카카오맵 선정 결정 기록 완료. D02-03은 실시간 공급자 선정, 실제 앱의 키/쿼터/비용, 저장·AI 전달 조건, 환승 및 도착정보 실응답과 ID 매핑 검증이 남아 미완료다. D02-04는 OpenAI GPT-5.6 Luna 선정 및 커스텀 서버 최소 연결 확인 완료, 예산·데이터 전달/보관 조건·서비스 품질/비용 검증 미완료다.
- AI 접속 검증(2026-10-06): 사용자 승인 후 프로젝트 환경의 OPENAI_BASE_URL에 지정된 HTTPS `mlapi.run` 서버로 Responses 형식의 최소 합성 요청을 전송했다. HTTP 200, completed, 응답 model=gpt-5.6-luna, OK 출력 확인. 1.33초, 입력 11·출력 5·총 16토큰(서버 보고). 중계 서버가 보고한 모델명이며 내부 실제 모델/공식 공급자의 직접 연결을 별도 검증한 것은 아니다. 키·서버 전용 전체 경로는 문서/로그에 기록하지 않는다. 이 승인은 합성 연결 테스트 범위이며 사용자 위치/일정·카카오 원본 데이터의 운영 전송/보관 조건은 미정이다. 공식 OpenAI 단가를 중계 서버 실제 청구 단가로 간주하지 않는다.
- AI 모델 검증(2026-10-06, 문서 확인): 공식 API 모델 ID는 `gpt-5.6-luna`이며 Structured Outputs를 지원한다. 표준 텍스트 100만 토큰당 입력 \$0.20·캐시 입력 \$0.02·출력 \$1.20이다(변경 가능, 부가 도구/장문 등 별도 조건 확인 필요). 이는 단가이며 프로젝트 예산 승인이나 실제 계정 사용 가능·품질 검증을 뜻하지 않는다. [공식 모델 문서](https://developers.openai.com/api/docs/models/gpt-5.6-luna).
- 카카오 접속 검증(2026-10-06): 프로젝트 환경의 REST API 키로 공식 장소 검색을 1회 호출했다. 공개 장소 강남역·SW8·주변 1km·최대 3개 조건에서 HTTP 200, 결과 3개, 장소 ID/이름/분류 및 WGS84 좌표 형식 확인. 0.12초. 원본 응답을 파일로 보관하거나 AI로 전달하지 않았다. JavaScript 키는 저장 존재만 확인했다. 지도 SDK 렌더링·공공 ID 매핑·저장 조건은 미검증이며, 도보/대중교통의 제한된 실호출 결과는 아래 경로 검증을 따른다.
- 카카오 경로 검증(2026-10-06): 공개 역 주변의 근사 좌표로 도보 강남역→역삼역 및 대중교통 강남역→서울역을 각 1회 호출했다. 모두 HTTP 200/status=OK. 도보 경로 1개·4단계·897m·925초(0.16초 응답), 대중교통 15개·총 49단계·버스/지하철/혼합 타입 확인(0.55초 응답). 첫 대중교통 후보는 15,471m·2,155초·환승 1회이며 최적/선택된 권고가 아니다. 모든 후보의 시간/거리 정수·음수 금지 및 경로 좌표 형식을 검사했다. 정류장/차량 이름 존재와 검사한 공공 ID 필드 부재 확인. 출입구·플랫폼 좌표 확정, 역 내부 이동 포함 범위, 공공 ID 매핑, 실시간 도착·미래 환승·막차, 경기 및 지역 경계는 미검증이다. 원본 응답 저장·외부 AI 전달 없음.
- 문서 검증 결과(실호출 아님): 카카오 GET /v2/routing/publictraffic 및 /v2/routing/walk는 REST API 키를 사용한다. WGS84에서 x는 경도, y는 위도이며 경로 시간은 초·거리는 미터다. 경로의 예상 소요시간을 실시간 차량 도착이나 미래 환승 시각으로 대체하지 않는다.
- ID 매핑 한계: 카카오 공개 경로 스키마의 `stops.name` 및 `vehicles.name`에 공공 정류장/노선 ID와 방향 식별자가 명시되어 있지 않다. 서울 도착 API의 busRouteId·stId·staOrd·dir와 이름만으로 직접 연결할 수 있다고 가정하지 않는다. 공공 정류장 좌표·노선 정차 순서·방향 등 추가 근거와 실응답을 대조하고 유일한 매핑이 불가능하면 기존 insufficient_data 정책을 적용한다. 경기 상세 필드/시간 단위는 최신 활용명세와 실응답 확인 대기다.
- 정책 확인 상태: 카카오 약관 제11조 제3항에 데이터 사용·변경·타인 제공의 사전 승낙 관련 조건이 있다. 해당 서비스의 원본 저장·파생 시간 재사용·외부 AI 전달·품질 이력 보관 허용 여부는 공식 답변/적용 조건 확인 전 미정이다. 공공 API 이용 조건이 카카오 데이터에도 적용된다고 간주하지 않는다.
- 근거: [카카오 REST](https://developers.kakao.com/docs/ko/kakaomap/rest-api), [쿼터·요금](https://developers.kakao.com/docs/ko/getting-started/quota), [서울 버스 도착](https://www.data.go.kr/data/15000314/openapi.do), [경기 버스 도착](https://www.data.go.kr/data/15080346/openapi.do), [ODsay 문서](https://lab.odsay.com/guide/releaseReference), [TMAP 경로](https://transit.tmapmobility.com/docs/routes).
### 공공 실시간 도착 API 준비 (2026-10-06)
- 서울 버스 도착 및 경기 버스 도착을 우선 검증하고, 정류소/노선 기반 데이터로 좌표·정차 순서·방향을 대조한다. 카카오의 장소 ID를 공공 정류장 ID로 사용하지 않는다. 도착 API 준비는 공급자 전체 연동/ID 매핑 완료가 아니다.
- 서울 버스: 공공데이터포털의 버스도착정보조회 서비스 활용신청과 인증키 필요. 노선 전체 도착 조회의 busRouteId, stId, staOrd, dir, mkTm 및 초 단위 예측 필드를 확인한다. 서울 정류소정보조회 서비스도 ID 매핑용 별도 활용신청 대상으로 준비한다.
- 경기 버스: 공공데이터포털 인증키와 v2 활용승인 필요. 개별 도착 요청은 stationId+routeId+staOrder를 사용한다. 같은 정류소에 상/하행이 모두 정차할 수 있어 순번을 생략하지 않는다. 공식 매뉴얼의 predictTimeSec1/2는 초, predictTime1/2는 분이다. 실제 응답·결측/0 의미·flag 상태와 단위 선택은 키 발급 후 검증한다.
- 서울 지하철: 열린데이터광장의 별도 지하철 인증키 필요. 노선 subwayId·역 statnId·상하행 updnLine·종착역 bstatnId와 열차/막차/도착코드를 대조하고 recptnDt 기준 최신성을 확인한다. barvlDt는 초다. 공식 안내상 서울 밖 일부 역 미제공이므로 경기도 지하철 전체 지원을 가정하지 않는다.
- 공개 샘플: 서울역 전용 sample 키로 도착 API 1회 호출하여 HTTP 200/INFO-000, 5건·초 단위 수치·식별/생성시각 필드 존재 확인. 개인 인증키·다른 역·실제 최신성/정확도 검증은 아니다. 개인 포털/지하철 키는 프로젝트 저장을 확인했다. 경기 버스 v2 HTTPS 요청은 HTTP 200/resultCode=0·1건, 초 필드 2개 및 stationId/routeId/staOrder/routeDestId 존재 확인. 서울 버스/지하철 HTTPS는 연결 단계 시간초과, 키 없는 별도 접속 진단에서도 443 시간초과·80 연결 확인. 초기 공식 HTTP 진단은 자동 승인 검토에서 거부됐으나 사용자 명시적 승인 후 각 1회 실행했다. 서울 버스 HTTP 200/headerCd=0·104건·초 필드 208개, 서울 지하철 HTTP 200/INFO-000·5건·초 필드 5개 확인. 모두 식별/생성시각 필드 존재 확인. 이는 개인 키 최소 인증/응답 구조 확인이며 기반정보 활용승인·카카오 ID/방향 매핑·생성시각의 실제 최신성·예측 정확도·운영 전송 보안은 미검증이다.
- 검증 준비는 서버용 CLI이며 서비스 API 구현이 아니다. HTTP 200 안의 공급자 오류와 정상 무결과를 구분한다. 키 포함 요청 URL/헤더·원문을 로그나 파일에 저장하지 않는다. 공공데이터포털 키는 Decoding 값을 환경에 저장하고 한 번 URL 인코딩한다. 기본 실키 호출은 HTTPS이며 실패 시 자동으로 HTTP로 낮추지 않는다. 서울 공식 명세가 HTTP로 제공하는 두 호스트(`ws.bus.go.kr`, `swopenapi.seoul.go.kr`)에 한해 --official-http 옵션을 명시한 진단 호출 도구를 준비한다. 2026-10-06 사용자가 두 공식 서버의 개인 키 HTTP 진단을 승인하여 각 1회 실행했다. 이 승인은 해당 최소 진단 범위이며 운영의 상시 전송 정책 확정과 구분한다. 이 옵션은 공개 교통 API의 서버 진단용이며 키가 암호화되지 않는 전송 구간이 생긴다. 외부 임의 호스트/리다이렉트는 금지하고 키 포함 URL·예외 원문을 기록하지 않는다. 운영 전송 방식·보안 조건은 확정 전이며 경기 API는 HTTPS를 유지한다.
- 근거: [서울 버스 도착](https://www.data.go.kr/data/15000314/openapi.do), [서울 정류소](https://www.data.go.kr/data/15000303/openapi.do), [경기 버스 도착](https://www.data.go.kr/data/15080346/openapi.do), [경기 v2 항목 매뉴얼](https://www.gbis.go.kr/gbis2014/publicService.action?cmd=mBusArrival), [경기 정류소 매뉴얼](https://www.gbis.go.kr/gbis2014/publicService.action?cmd=mBusStation), [서울 지하철 범위](https://data.seoul.go.kr/dataList/OA-12764/A/1/datasetView.do), [서울 지하철 API 명세](https://data.seoul.go.kr/dataList/openApiView.do?infId=OA-12764&srvType=A).
### 기반정보 권한 및 최신성 조사 (2026-10-06)
- 경기 기반정보 HTTPS 3종(getBusStationListv2, getBusStationViaRouteListv2, getBusRouteStationListv2)을 공식 공개 예시로 각 1회 호출했고 모두 HTTP 403이었다. 도착 API의 인증 성공과 별개로 정류소/노선 서비스의 추가 활용승인·권한·반영 상태 확인이 필요하다. 오류 원문을 확인하지 않았으므로 403의 상세 원인을 확정하지 않는다. 실제 카카오 ID/방향 매핑은 진행되지 않았으며 이름만으로 임의 매핑하지 않는다.
- 경기 도착정보 1회 재조회는 HTTP 200/resultCode=0·1건. 요청시각 queryTime 존재/파싱 가능을 확인했으나 확인한 행별 데이터 생성시각 필드는 없었다. queryTime 또는 HTTP 수신시각만으로 원천 데이터의 최신성을 보장하지 않는다. 원천 생성시각 확인 또는 공급자 갱신 지연 근거를 확보하기 전 생성시각 기반 최신성은 unknown으로 둔다.
- 진단 도구는 생성시각 누락/형식 오류/시간대 미확인/미래 시각을 정상 최신으로 처리하지 않는다. 호출자가 명시한 양수 만료 임계값으로 경계와 만료를 검사하며, 이 값은 운영 정책의 확정값이 아니다. 사용자 결정(2026-10-06): 활성 화면의 실시간 도착정보 정기 조회 주기는 60초(1분)로 확정한다. 기존 30초 조회 제안은 대체한다. 정보 만료는 수신/검증된 생성시각 기준 각각120초 중 이른 기한으로 확정(20절)했다. 원천 생성시각 unknown 원칙은 유지한다. 조회 주기와 원천 정보의 유효기간을 동일한 정책으로 취급하지 않는다. 기존 서비스 status/응답 계약은 유지하고 검증용 CLI·헬퍼만 준비했다.
- 추가 신청 확인 대상: [서울 정류소정보](https://www.data.go.kr/data/15000303/openapi.do), [경기 버스노선](https://www.data.go.kr/data/15080662/openapi.do), [경기 정류소/경유노선 안내](https://www.gbis.go.kr/gbis2014/publicService.action?cmd=mBusStation), [경기 노선 정차순서 안내](https://www.gbis.go.kr/gbis2014/publicService.action?cmd=mBusRouteStation). 정류소 API의 포털 직접 신청 URL은 미확인이며 공식 공개키 발급 안내에서 해당 서비스의 승인 상태를 확인한다.
### 경기 노선 기반 매핑 진단 (2026-10-06)
- 사용자 보고: 정류소 정보조회는 서울특별시 서비스에 신청했고 경기 버스노선 서비스도 신청했다. 재조회에서 경기 정류소 검색/경유노선은 HTTP 403 유지, 경기 노선 정차순서는 HTTP 200/resultCode=0·83건 확인. 경기 정류소 승인을 서울 정류소 승인으로 대체하지 않는다.
- 경기 노선 데이터의 stationId/stationName/x/y/stationSeq를 이용해 별도 경기 정류소 API 없이 진행 가능한 공개 사례를 대조했다. 카카오 판교역→성남시청 주변의 직행 버스 후보 중 첫 진단 대상 76번(판교역동편→성남시청전면)을 사용했다. 사용자 선택 경로/최적 경로로 확정한 것은 아니다.
- 동명 76번 공공 노선 후보 5개를 모두 조회한 결과 카카오 정류장 11개의 순서, 공공 승차순번 7/하차순번 17, 경로 양끝과 정류장 좌표 차이 11.07m/12.85m를 만족하는 후보가 하나였다. 해당 stationId+routeId+staOrder로 도착정보 1건을 받아 식별자/승차순번 일치를 확인했다.
- 진단 필터의 양끝 좌표 허용오차 100m는 이 실험용 설정이며 운영 매핑 정책의 확정값이 아니다. 이름만으로 선택하지 않고 모든 동명 노선 후보·중간 정류장 순서·양끝 좌표를 대조했다. 유일성 미확보·반대 방향·누락/중복 순번·좌표 부족은 후보를 확정하지 않는다. 원본 경로/기반정보를 파일에 저장하거나 AI로 전달하지 않았다.
- 이 결과는 공개 경기 사례 1개의 후보 대조/도착 ID 확인이다. 전체 지역/노선·회차/분기/급행/광역·서울 및 지하철 매핑·자동 운영 어댑터·원천 최신성 검증을 완료한 것은 아니다. 경기 정류소 및 서울 정류소 최소 연결의 후속 결과는 아래를 따른다.
### 서울/경기 정류소 연결 후속 확인 (2026-10-06)
- 사용자 승인 화면에서 경기 정류소/노선·서울 정류소·서울/경기 버스 도착정보 5개 서비스 승인과 만료예정일 2028-10-06을 확인했다. 이는 AI 키 기한과 별개이며 실제 권한 유지·만료 시각은 추가 확인이 필요하다.
- 경기 HTTPS 재조회에서 정류소 검색 2건·경유노선 4건·노선 정차순서 83건 모두 HTTP 200/resultCode=0. 이전 정류소 403은 해소됐으나 원인이 승인 반영 지연이었다고 확정하지 않는다. 위 이전 실패는 당시 진단 기록이다.
- 서울 정류소 명칭 검색은 공식 예시 경성중고사거리로 HTTP 200/headerCd=0·2건. 정류소 ID/이름/고유번호 및 tmX/tmY의 유한한 지리 좌표 범위를 확인했다. 좌표계 확정·카카오 대조·경유노선/회차/전체 범위·최신성 검증은 미완료다.
- 서울 호출은 기존 사용자 승인된 고정 공식 HTTP 호스트에서 1회 진단했다. 자동 HTTP 전환·리다이렉트·원문/키 저장 및 AI 전달 없음. 운영 전송 정책은 미정이다. 기존 앱 API 경로/입력/응답·계산 정책 변경 없음.
### 서울 좌표/경유노선 대조 진단 (2026-10-06)
- 서울 공식 개발 가이드에서 이름 검색 tmX/tmY와 좌표 검색 gpsX/gpsY는 WGS84, posX/posY는 GRS80임을 확인했다. 경유노선 조회 입력 arsId는 정류소 고유번호이며 stId와 혼용하지 않는다.
- 공개 강남역→서울역 첫 직행 버스 후보는 심야 N75였다. 이름 검색은 공급자 코드 4로 실패. 공식 좌표 검색(진단 반경 100m)은 양끝 주변 8개/6개 정류소 반환, 이름과 좌표를 함께 대조한 후보는 승차 1개/하차 0개였다. 승차 arsId로 경유노선 41건을 정상 조회했다.
- 이번 결과는 endpoint_unresolved로 전체 매핑 미확정이다. 공급자 간 이름/승강장 표기 차이·노선 이름의 심야 표기·정차순서/방향·하차 후보 선택은 추가 검증 필요. 임의 별칭 변환/가장 가까운 정류소 확정/운영 어댑터 적용 없음. 100m는 실험 설정이며 운영 정책 미확정.
- 기존 승인된 고정 공식 HTTP 호스트로 최소 진단, 카카오는 HTTPS. 원본/키 저장·AI 전달 없음. 후보 필터 합성 테스트 3개 통과. 앱 API 계약/계산 정책 변경 없음.
### 공급자 이용 조건 조사 (2026-10-06)
- 사용자 지시: 기획된 환승·AI 도보 산정·저장 시간 재사용·수동 탑승 확인을 유지한다. 전체 길찾기 검증을 별도 제품 목표로 확대하거나 첫 탑승만으로 기능을 축소하지 않는다. 현재 작업은 D02 이용 조건 확인이다.
- 카카오 약관 제11조 제3항의 사전 승낙/대리인 기밀 유지 예외와 데브톡 2026-08-18 API 응답 저장·반복 사용 불허 답변을 확인했다. 원본 저장/재사용을 기본 허용으로 취급하지 않는다. 도보 API의 파생 AI 기준 시간·개인화 결과/품질 이력 저장 및 최소 정보 AI 전달 허용은 별도 확인 필요다. 사용자 요구를 삭제하거나 매회 재산정 방식으로 임의 변경하지 않는다.
- 카카오 공개 쿼터는 전체 무료 월 300만 건, 키워드 검색 일 10만 건, 도보/대중교통 각 일 1천 건. 첫 활성화 앱 무료 대상 조건과 추가 쿼터 요금 키워드 2원/도보·대중교통 각 10원/건 확인. 현재 앱의 실제 무료 적용/사용량·유료 설정은 미확인, 변경하지 않았다.
- 사용자 제공 AI Campus URL/모델 정보 화면에서 엘리스 발급처·OpenAI 제공·openai/gpt-5.6-luna·Serverless 확인. 100만 토큰당 입력 304원/캐시 입력 30원/출력 1,827원, API Rate Limit 무제한 표시. 기존 연결 요청 gpt-5.6-luna 설정 유지. 화면 요금은 실제 청구/부가세/크레딧·예산 확인과 별개다. 입력/응답 보관·학습 사용·삭제·처리지역/기밀 유지 계약은 미확인이다.
- 서울 버스/지하철은 출처표시, 경기 버스는 이용허락범위 제한 없음. 서울/경기 버스 포털 무료·개발 신청 트래픽 1,000 확인. 서울 버스 mkTm은 제공시각, 지하철 recptnDt는 생성시각이며 지연 반영 필요 안내. 지하철 서울시 밖 역구간 미제공 안내로 경기 전체 지원을 가정하지 않는다. 시간대/만료/보장 지연·실제 계정 쿼터는 미정이다.
- 상세 출처·조건 표·공급자 문의 초안은 로컬 `provider_conditions.md`에 기록. 외부 문의 미발송, 키 포함 API 추가 호출/개인 데이터 전송 없음. 현재 D02 실제 미검증은 유지하며 D03 보관/만료 수치는20절 확정, 실제 AI 예산/청구는 별도다. 앱 API 계약/계산 정책 변경 없음.
- 사용자 후속 결정(2026-10-06): 미확인 공급자 조건에 대한 추가 확인을 생략하고, 제한이 없다는 작업 가정으로 D03 결정을 진행한다. 이는 공급자의 실제 허락/무보관/무학습을 확인한 사실이 아니다. 기존 기획을 유지하고 조건 확인을 반복 진행의 선행 단계로 요구하지 않는다. D02 미검증 항목은 확인 완료로 체크하지 않는다.
## 19. 자연어 일정 입력 — F17 (2026-10-06)
사용자 확정 요구: 자연어를 명확한 날짜·시간·반복 조건으로 해석해 루틴 또는 일회성 약속 입력을 돕는다. 기획 추가이며 기능·모델 연동은 미구현이다.
### 사용자 흐름과 역할
1. 루틴/약속 만들기에서 문장 입력 → AI 해석 → 날짜·요일·시간·출발/도착 기준·목적지 확인 카드.
2. 누락·모호한 필드는 질문 또는 직접 입력으로 보완한다. 사용자가 수정·확인한 뒤 기존 생성 API로 저장한다. 해석만으로 일정 생성·초대·채팅 전송·알림 예약을 하지 않는다.
3. AI는 문장 의도와 구조를 추출한다. 서버는 달력 날짜·요일·시간대·반복 유효성을 검증한다. 교통 데이터 기반 출발 시각·환승·여유·개인 계수 계산은 기존 서버 알고리즘을 유지한다.
4. 텍스트 입력부터 지원한다. 음성 인식·채팅 자동 감시·외부 캘린더 연결은 이번 추가 범위에 포함하지 않는다. AI 실패 시 기존 수동 입력을 제공한다.
### 해석 정책
- 상대 날짜는 서버가 부여한 reference_at과 사용자 IANA timezone 기준으로 해석한다. 기본 Asia/Seoul을 화면에 표시한다. 재질문에서도 최초 기준 시각을 유지하며 날짜 경계를 넘으면 재확인을 요구한다.
- 단일 일정은 현지 날짜와 시간대를 확인 후 절대 시각으로 변환한다. 반복은 현지 요일·시각·시간대·시작일·선택 종료일로 보존하며 단일 UTC 시각으로 축약하지 않는다.
- “내일 오후 3시까지 강남역에 가야 해”: 다음 현지 날짜, 15:00, arrive_by, 목적지 검색어 강남역.
- “매주 화·목 오전 9시까지 출근”: weekly, 화/목, 09:00, arrive_by, 저장된 회사 후보. 첫 적용일은 확인 카드에서 확인한다. 공휴일 제외를 임의 적용하지 않는다.
- “금요일 저녁 민수랑 만나”: 특정 금요일 후보를 보여주고 정확한 날짜·시각·장소를 확인한다. 저녁을 18시로 고정하거나 이름만으로 친구 계정을 연결하지 않는다.
- 오전/오후 없는 시각, 이번/다음 요일의 모호함, 출발/도착 불명확, 과거 시각, 존재하지 않는 날짜, 지원하지 않는 반복은 clarification_required. 숫자를 임의 보완하지 않는다.
- 목적지 검색어는 장소 ID가 아니다. 검색 후보 선택 및 본인 저장 장소 소유권 검증 후 기존 저장 API로 전달한다. 기존 루틴은 목표 도착 시각 중심이므로 depart_at 입력은 그대로 저장하지 않고 미지원 안내 또는 목표 도착 입력 보완으로 처리한다.
### API 설계 초안
- 신규 POST /api/v1/schedule-interpretations. 로그인·이메일 확인·CSRF 및 공통 응답/요청 추적 규칙 적용. 일정 저장 API와 분리한다.
- 입력: text(1\~1000자 확정), timezone(IANA), target_type(routine/meeting), 선택 clarification_context. 후속 문장은 전체 문맥으로 다시 제출한다. clarification_context는 서버 서명된 최초 reference_at·사용자·만료값으로 제한하며 임의 클라이언트 시각을 신뢰하지 않는다. 유효기간10분 확정.
- 200 data: status(ready_for_review/clarification_required/unsupported), reference_at, timezone, clarification_context, draft, missing_fields, questions, warnings. ready_for_review는 저장 완료를 뜻하지 않는다.
- draft: date(YYYY-MM-DD 또는 null), local_time(HH:mm 또는 null), time_basis(arrive_by/depart_at/unknown), recurrence(null 또는 frequency=weekly, weekdays=ISO 1\~7, start_date, end_date 선택), destination_query(string 또는 null). 불확실한 필드는 null/unknown과 질문으로 반환한다.
- 서버는 모델 출력 스키마·날짜·요일·구간·참조 소유권을 검증한다. 잘못된 출력은 저장하지 않는다. 본문/시간대 오류422 VALIDATION_ERROR, 인증401/403, 제한429, AI 실패503 AI_UNAVAILABLE, 출력 검증 실패502 AI_OUTPUT_INVALID. 문장 모호함은 200 해석 상태로 구분한다.
- 해석 API는 일정 생성 부작용이 없다. 일반 Idempotency-Key 규칙을 적용하되 중복 응답 저장에도 원문을 로그로 복제하지 않는다. 기존 루틴/약속 생성 계약 및 권한·버전·중복 방지는 그대로 적용한다. 정확한 기존 필드 변환·컨텍스트 서명/만료 오류·제한 수치는 구현 전 상세 설계에서 확정한다.
### 품질 이력과 완료 기준
- 실행 ID, 모델/프롬프트/정책 버전, 기준 시각·시간대, 비식별 구조화 결과, 검증 상태, 사용량·지연, 사용자 수정 필드와 확인/취소 여부를 연결한다. 이름·주소 포함 원문과 질문 전문은 기본 영구 저장/일반 로그에서 제외한다. 재현용 원문은 합성 사례 우선, 실제 원문 수집은 별도 동의·보관 정책 확정 후 검토한다.
- AI 전달은 필요한 문장과 기준 정보로 최소화하고 전체 채팅·주소록을 전달하지 않는다. 데이터 전송 조건과 모델 선택은 D02-04, 보관 기간은 D03 결정에 의존한다.
- 평가: 상대 날짜, 자정/월말/연말/윤년, 반복 요일, 모호한 오전/오후, 과거·잘못된 날짜, 악성 지시문, 실패 시 수동 입력. 같은 합성 기준 시각에서 기대 구조 및 확인 전 저장 없음 검증.
- F17은 F02 인증·F06 루틴 또는 F12 약속 생성 기능에 의존한다. 기존 착수 전 결정 순서는 유지한다. 기존 AI 도보/경로 설명 기능을 삭제하거나 대체하지 않는다.
## 20. D03·D04·D05 확정 정책 (2026-10-06)
사용자가 남은 정책 결정을 위임하여 기존 기획/약속 API 초안을 기준으로 확정했다. 기능 구현 완료가 아니며 로컬 `policy_decisions.md`가 판단 이유/검증 계획을 담는다. 기존 환승·AI 도보·저장 재사용·수동 출발/탑승 요구와 조건 추가 확인 생략 결정 유지.
### D03 유효기간·설정·보관
- 도보 기준/산정 재사용30일(2592000초), 위치/출입구/방향/경로 변경 즉시 무효화. 개인 계수만 바뀌면 유효 기준 시간에 재계산하고 지도/AI를 재호출하지 않는다.
- 활성 화면 도착정보 정기 조회60초, 비활성 정기 조회 중지·첫 진입/탭 복귀 조회. 출발 권고의 교통 근거는 수신후120초 및 검증된 생성시각후120초 중 이른 기한까지 유효. 경계120초 유효, 초과 중지. 미래/잘못된 생성시각 또는 원천 unknown을 최신으로 확정하지 않는다. 120초는 앱 만료 정책이며 공급자 정확도 보장이 아니다.
- 첫 탑승 여유 기본300초·환승 여유 기본120초, 각각 정수0\~1800초. 첫 출시 최대환승2회. 개인화 계수 초기1.0·지원 범위0.5\~2.0과 기존5개/최근20개 점진 학습 유지.
- 장소검색 결과10분·여정검색 결과5분. 여정의 차량 근거는 별도120초 유효 및 선택 시 재검사. 작업 성공/실패 결과는 종료후24시간, 내보내기 파일24시간·본인 인증 다운로드 링크10분. 만료 결과 조회404 RESOURCE_NOT_FOUND. 계정 삭제 영수증24시간 유지.
- 목록 기본20/최대100·멱등 결과24시간·자연어 입력1\~1000자/서명 컨텍스트 최초발급10분 확정. 기존 소유권/참여 권한·버전·날짜 검증 유지. 세션/메일 제한 계약은17절 유지, 메일 공급자는F02-00에서 선정.
- 실행 로그14일, 개인 이동/품질 이력90일, 장소/루틴/현재 프로필은 삭제/탈퇴까지 유지. 원문/키/상세 위치 일반 로그 제외. 표본/관측/산정 연결 이력은 함께 청소하고 과거 예측을 덮어쓰지 않는다.
- 만료 사용/노출 즉시 차단·기간 청소 매일. 명시 삭제/탈퇴는 즉시 접근 차단 및 기존202 작업으로 사본 정리, 완료 목표24시간·실패 재시도/failed 표시. 향후 백업 최대7일 순환·복원 시 삭제 기록 재적용. 실제 청소/백업 실행은 미구현이다.
### D04 첫 출시 알림
- 첫 출시는 반응형 모바일 웹의 활성 화면 출발 카드/카운트다운/상태 안내. 백그라운드 푸시/예약 알림·GPS/센서 자동 출발 감지는 첫 출시 제외하고 후속 검토. 새로운 푸시 등록/발송 API 없음, 수신 보장 표현 없음. 사용자 수동 출발/탑승 확인과 약속의 열린 화면 REST/WS 갱신 유지.
### D05 약속 확장
- 최대2명(주최자 포함)·혼자 사용 가능, 통근 핵심 이후 확장. 제목1\~100자·텍스트채팅1\~1000자, 수정 없음/본인 삭제 유지. 초대 활성1개/약속·24시간·1회 수락, WS 티켓30초·1회. 추천 최대3개·5분 및 입력/동의/revision/참여자 변경 즉시 무효화.
- 공유 기본꺼짐·약속별 본인 선택·활성 참여자만 요약 접근. 종료/취소/철회 중 이른 때 및 목표시각6시간 후 자동 종료. 공유 ETA는 계산후120초 및 교통근거 만료 중 이른 기한. 기존 REST/WS 소유권·정정·종결 오류 유지.
- 채팅10회/10초(사용자·약속), 추천3회/분(약속), 초대 미리보기10회/분(사용자), 초과429+Retry-After 확정. WS ping25초/무응답60초 유지.
- 공동 약속/채팅은 completed/cancelled 후30일. draft 마지막 사용자 변경후30일 미사용 삭제. confirmed 목표시각6시간 후 completed 자동 정리하되 실제 참석/도착 판정 아님. 재전송 이력24시간. 본인 약속탈퇴 시 개인 입력/공유 종료·정리, 기존 공동 메시지는 탈퇴한 참여자로 표시. 계정탈퇴는 본인 메시지 본문도 삭제, 주최자 탈퇴는 취소 후 다른 활성 참여자30일 열람. 개인 trip은 연결해제후90일 정책.
### 계약 영향·완료 기준
- 기존 경로/응답 객체 유지, 설정 상한·만료·공유 ETA120초·자동 종료/삭제·출시 알림 범위가 변경/확정됐다. 아직 서비스가 미구현이므로 배포된 클라이언트 마이그레이션 없음. 422/404/409 등 기존 오류 사용, 소유권·동시 수락·기한 경계·삭제 사본 검증은 구현 시 수행한다.
- D03·D04·D05 결정/문서와 F00-03 공통 호출/ID·F00-04 최소 요청 로그 완료, 핵심 서비스 기능은 미완료. 사용자 요청(2026-10-06)으로 F01 데이터 공급자 검증 단계를 작업 목록에서 삭제했다. 다음은 F02-00 회원가입·로그인 구현을 위한 메일 공급자·발송 설정·제한 저장소·미확인 가입 보관 정책 확정이다. 기존 공급자 연결 결과와 미확인 범위는 이력으로 유지한다. 공급자 응답 변환/오류 처리는 필요한 서비스 기능 연동에 포함하며 별도 선행 검증 단계로 진행하지 않는다.
## 변경 이력
- 2026-10-06 v0.28: F00-04 최소 JSON 요청 완료/예상 밖 오류 로그·필드 허용 목록·템플릿/미매칭 경로·LOG_LEVEL/실행 안내 추가. 기존 API 입력/성공/오류/ID 유지, 수집/보관 작업은 배포 단계. 민감정보/원문 스택 출력 없음.
- 2026-10-06 v0.29: 사용자 요청으로 F01-01 대표 사례 선정/검증 목록 정리를 작업 목록에서 삭제하고 다음 작업을 F01-02로 갱신. 기존 API 계약·계산 정책·클라이언트 호환성 변경 없음.
- 2026-10-06 v0.30: 사용자 요청으로 F01 데이터 공급자 검증 단계를 TODO·기능 목록에서 삭제하고 다음 작업을 F02-00으로 갱신. 기존 연결 이력은 보존, 응답 변환/오류 처리는 기능 연동에 포함. API 경로·필드·계산 정책·클라이언트 호환성 변경 없음.
- 2026-10-06 v0.27: F00-03 공통 클라이언트/서버 request_id 및404/405/422/500 오류 형식 구현 계약 기록. health 경로/성공 객체 유지, 기존 기본 오류 응답을 공통 error/meta로 맞춤. 405 METHOD_NOT_ALLOWED 명시, 초기 클라이언트만 영향·업무 기능 미구현.
- 2026-10-06 v0.26: 사용자 위임으로 D03 시간/설정/보관·D04 첫 출시 화면 안내·D05 2인 약속/공유/삭제 정책 확정. 60초 조회 유지·120초 만료/ETA, 기존 제안 수치 채택 및 미사용/종결 청소 정의. API 경로/객체 유지, 향후 검증/계산/보관 동작 영향·미구현·배포 클라이언트 영향 없음.
- 2026-10-06 v0.25: 출발 안내 시각 이후 접근 시간의 절반 초과·출발 확인 없음이면 다음 이용 가능한 차량 기준으로 안내 재계산하는 사용자 요구 반영. 기존 departed 이벤트/60초 정기 조회/환승 검증 유지, 데이터 만료와 구분. API 필드 변경 없으며 향후 후보 선택 동작 변경, 미구현.
- 2026-10-06 v0.24: 잦은 조회를 줄이려는 사용자 결정으로 활성 화면 실시간 도착정보 정기 조회 주기 60초 확정(기존 30초 제안 대체). 정보 만료 60초·기타 보관 수치는 미확정 유지. API 경로/필드 변경 없고 폴링 기능은 미구현.
- 2026-10-06 v0.23: 기획 범위 유지 지시와 공급자 저장/재사용·AI 전달·공공 데이터 조건 조사, 사용자 엘리스 모델 화면 요금 기록. 파생 시간 허용/AI 데이터 처리·예산 미확정 유지. 앱 API/클라이언트 영향 없음.
- 2026-10-06 v0.22: 서울 WGS84/arsId 근거 및 좌표 검색/경유노선 실호출 기록. 하차 후보 불일치로 전체 매핑 미확정, 임의 별칭 변환 없음. 앱 API 계약/클라이언트 영향 없음.
- 2026-10-06 v0.21: 경기 정류소 403 해소와 서울 정류소 개인 키 최소 응답 검증 기록. 좌표계/추가 매핑/최신성/운영 보안은 미확정 유지. 앱 API 계약 및 기존 클라이언트 영향 없음.
- 2026-10-06 v0.20: 사용자 신청 서비스 구분 및 경기 노선 API 권한 회복 확인, 동명 5개 노선의 정차순서/좌표 대조와 단일 사례 도착 ID 일치 기록. 진단 허용오차는 운영 미확정, 전체 매핑/최신성은 미완료. API 경로·필드·클라이언트 계약 변경 없음.
- 2026-10-06 v0.19: 경기 기반정보 3종 HTTP 403·활용승인 확인 필요와 요청시각/원천 생성시각 구분 기록. 만료 진단 헬퍼 준비, 운영 임계값은 미정 유지. 실제 매핑/원천 최신성 확인 미완료, API 경로·필드·기존 클라이언트 계약 변경 없음.
- 2026-10-06 v0.18: 사용자 승인 후 서울 버스/지하철 공식 HTTP 개인 키 최소 호출 성공과 필드 존재 기록. 기반정보/카카오 ID·방향·최신성·예측 정확도/운영 전송 보안 미검증 유지. API 경로·필드·기존 클라이언트 계약 변경 없음.
- 2026-10-06 v0.17: 등록된 개인 키 확인 및 경기 버스 HTTPS 실응답 1건 검증. 서울 HTTPS 연결 실패·공식 HTTP 개인 키 진단의 자동 승인 거부/사용자 승인 대기 기록. 자동 HTTP 전환 금지 유지, 운영 전송 보안 미정. API 경로·필드·기존 클라이언트 계약 변경 없음.
- 2026-10-06 v0.16: 지하철 역 내부 이동 결과를 수동 탑승 신고로 검증하고 GPS를 판정 근거로 쓰지 않는 사용자 결정 반영. 기존 관측 이벤트/입력 구조 유지, 대기 혼입 기록의 보행 학습 제외 명시. 공공 버스/지하철 API 신청·필드·샘플 검증 준비 기록. 기존 클라이언트 필드/경로 변경 없음.
- 2026-10-06 v0.15: 서울 공개 역 주변 도보/대중교통 최소 실호출 성공과 시간·거리·좌표 형식 검증 기록. 공공 ID 매핑/실시간/역 내부 이동/경기 사례 미검증 유지. 기존 API 경로·필드·클라이언트 호환성 변경 없음.
- 2026-10-06 v0.14: 카카오 앱 생성/키 저장 사용자 보고와 공식 장소 검색 1회 성공 기록. 지도 SDK·경로·실시간 매핑·저장 조건 미검증 유지. API 경로·입력·응답 및 클라이언트 호환성 변경 없음.
- 2026-10-06 v0.13: 사용자 승인된 커스텀 AI 서버의 합성 연결 확인과 운영 데이터 처리/품질 미검증 범위 기록. 기존 공식 서버 401은 커스텀 서버 인증 결과와 구분. API 경로·필드·클라이언트 호환성 변경 없음.
- 2026-10-06 v0.12: 사용자 지정 OpenAI GPT-5.6 Luna 선정 반영, 공식 API ID/구조화 출력/단가 확인. D02-04 예산·데이터 처리 조건·실호출은 미완료 유지. 기존 API 경로·필드 변경 및 클라이언트 호환성 영향 없음.
- 2026-10-06 v0.11: 자연어 일정 해석·사용자 확인 흐름과 F17 API/품질 이력 초안 추가. 기존 일정 생성 계약 유지, 신규 선택 입력 경로 추가. 기존 클라이언트 변경 불필요. 미구현.
- 2026-10-06 v0.10: 사용자 카카오맵 선정 결정 반영, 공식 경로·쿼터 문서 재확인 및 ID 매핑/저장/AI 전달 미검증 범위 명시. D02-03/04는 미완료 유지. 상태 API 구현 사실을 전체 미구현 표기에서 구분. 기존 API 경로·입력·응답 변경 및 클라이언트 호환성 영향 없음.
- 2026-10-02 v0.9: 사용자 요청으로 지원 지역 서울·경기도 확정, AI 공급자 PM 확인 대기. 공급자 추천·검증 조건 추가. API 경로/응답 형태 변경 없음, 지역 범위 제한은 구현 전 반영 필요.
- 2026-10-02 v0.8: 이메일·비밀번호 첫 버전 확정, 소셜 후속 검토. 인증 API·세션·CSRF·복구·재인증·삭제 영수증 초안 추가. GET /me에 email_verified 및 DELETE /me 응답에 영수증 필드 추가(미구현 계약의 추가 확장). 인증 관련 기존 미정 항목 구체화.
- 2026-10-02 v0.7: 친구 약속·초대·중간 추천·개인 안내·채팅·출발 공유의 REST 및 WebSocket 상세 설계 초안 추가. 기존 루틴 요청은 유지하며 약속 전용 안내 경로를 신설하는 설계. 신규 API와 DB 변경은 미구현, 제안 정책은 구현 전 확정.
- 2026-10-02 v0.6: Alembic 기반과 초기 이력 적용·격리 테스트 완료 상태 기록. 업무 테이블 및 API 계약 변경 없음.
- 2026-10-02 v0.5: 통근 MVP와 약속 확장 테이블·관계·이력·삭제 설계 초안 추가. DB 테이블 생성 및 마이그레이션 미적용, 기존 클라이언트 호환성 변경 없음.
- 2026-10-02 v0.4: PostgreSQL과 Docker 로컬 개발 DB 확정. 기존 API 경로·필드·클라이언트 호환성 변경 없음.
- 2026-10-02 v0.3: 일회성 약속·중간 만남·채팅·출발 상태 공유의 확장 기획 추가. 약속 신뢰 형성 목적과 수동 출발의 근거 한계 명시. 신규 API는 설계 대기이며 기존 클라이언트 계약 변경 없음.
- 2026-10-01 v0.2: 프로젝트 경로 및 화면 프로토타입 상태를 기록. API 계약과 클라이언트 호환성 변경 없음.
- 2026-09-30 v0.1: 기획 기반 API 초안 작성. 요청·응답 예시는 합성 데이터이며 구현 또는 테스트 완료를 의미하지 않는다.
