# 지금이니? API 설계 초안
- 문서 버전: 0.80 · 작성일: 2026-09-30 · 수정일: 2026-10-14 (F08 루틴 안내 연결 이동 세션·수동 출발 구현)
- 프론트엔드: React · 백엔드: Python FastAPI
- 상태: **기획/미구현 계약과 일부 구현을 함께 기록**. GET /health·공통 요청 처리/로그 및17절 기본 회원 인증은 구현, F03-01\~03 장소 검색/저장/본인 조회·지도 핀/출입구·이름 수정/삭제는 구현, F03-04 출발지 입력 확인·단발 현재 위치/지도/본인 저장 장소 선택은 구현. F03-05a 수동 확인은 구현/검증 완료이며 GPS 수치/자동 일치 판정은 사용자 결정으로 보류. F04-01 depart_now 대중교통 후보 조회 API 및F04-02 공통 구간 모델은 구현, F04-03 후보 비교 화면은 구현. F06-01 루틴 저장·상세 API와 비교 화면 저장 연동, F06-02 루틴 요일·목표 도착 저장(저장 입력과 일정 PATCH 포함)은 구현. F06-03 본인 목록·선택·이름/일정/경로 수정·삭제와 F06-03a 루틴 등록 중 장소 저장·선택은 구현·검증 완료. F06-04 장소 변경/삭제 루틴 복구 안내도 구현·검증 완료. F03-02a 검색 없는 지도 핀 저장·자동 선택도 구현·검증 완료. F05-01 기존 후보 도보 근거·누락 조회 API도 구현·검증 완료. F05-02 서버 내부 프롬프트 블록·버전 로딩도 구현·검증 완료. F05-03 서버 내부 AI 최소 입력/구조화 결과 검증과 실제 합성 최소 호출도 구현·검증 완료. F05-04 내부 산정/품질 이력 저장과 본인 상세 조회도 구현·검증 완료. F05-05 서버 내부 조건별 전체/부분 재사용도 구현·검증 완료. F05-06 내부 개인 계수 재계산·경로 변경/만료 무효화도 구현·검증 완료. F05-07 루틴/후보 상세의 근거 부족·실내 이동·실패/만료 화면 안내도 구현·검증 완료. F07-01a 기반/F07-01b 경기 매핑·본인GET·사용자 승인 수신 기준 추정은 구현·검증 완료, 원천 시간/갱신지연·지원 범위 강화는 F07-01c 후속으로 F07-01 전체 미완료. F07-02 후보 첫 버스 예상 출발 계산은 사용자 승인 공급자 접근 개인화 추정으로 구현·검증 완료. F07-03 지원 경기버스의 선택적 순차 환승 검사는 구현·검증 완료이며 미지원/근거부족은unknown이다. F07-02a-1 루틴 선택→최신 첫출발 연결은 구현·검증 완료. F07-02a-2 지원 경기BUS 루틴의 누락 접근도보 보완도 구현·검증 완료. F07-05 유효 첫출발의 남은 시간/현재 기준 정류장여유 안내도 구현·검증 완료. F07-04 선택 루틴의 현재후보 오늘목표도착 평가는 구현·검증 완료. 검증 개인 도보 물리연결/F07-02a와 미래예약/목표기반 대체경로 자동조회는 미구현. F12 일회성 약속 코어 REST(생성/목록/상세/수정/직접 목적지 확정/상태 전이/삭제/참여 탈퇴)와 초대 발급·철회·미리보기·수락은 구현·검증 완료이며 추천 기반 확정·개인 출발지·출발 안내·공유·채팅·WS는 미구현. F08-01 루틴 안내 연결 이동 세션 및F08-02a 수동 departed 신고·본인 복구/취소는 구현·검증 완료. 나머지이벤트/정정/학습·F07-06b 절반경과 연결은후속. 세부 완료 상태는 `todo.md`를 따른다.
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
첫 버전은 이메일 중복 확인과 비밀번호 기반 가입/로그인이다. 메일 소유 확인·복구는 후순위, 가입 즉시 active다. 서버 세션·HttpOnly 쿠키·CSRF 상세 계약은17절을 따른다.
## 4. 기능별 API 목록
GET /health·17절 기본 회원 인증·5.1.1\~3절 장소·5.2.1\~2절 출발지 선택/수동 확인·5.2.3절 depart_now 경로 후보 및 본인 작업 조회·5.3절 루틴 저장/상세/일정 및5.3.1절 목록/이름/경로 수정/삭제·5.5.3절 본인 도보 산정 상세·5.9절 첫 탑승 도착 조회·5.7.1절 후보 첫 버스 예상 출발 계산과 16절의 일회성 약속 코어 REST(생성/목록/상세/수정/직접 목적지 확정/상태 전이/삭제/참여 탈퇴·초대 발급/철회/미리보기/수락)는 구현되어 있으며 그 외 항목은 **미구현**이다. 성공 응답 열은 공통 data 내부 필드를 요약한다.
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
<td>200: user_id, display_name, profile</td>
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
<td>본인 비동기 작업 확인. 경로 검색과 약속 삭제(meeting_delete) 작업을 조회하며 계정 삭제 상태 조회는 17절의 X-Deletion-Receipt 헤더 사용</td>
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
<td>query: 검색어1\~100자</td>
<td>200: search_id, expires_at, candidates\[\]</td>
<td>주소가 URL·접근 로그에 남지 않도록 본문 전달. 검색 본문도 로깅 제외</td>
</tr>
<tr>
<td>`GET /map-config`</td>
<td>필요</td>
<td>없음</td>
<td>200: javascript_key</td>
<td>등록 도메인 제한용 공개 SDK 키만, REST 키 비노출</td>
</tr>
<tr>
<td>`POST /place-location-confirmations`</td>
<td>필요</td>
<td>location</td>
<td>200: confirmation_id, location, location_address, expires_at</td>
<td>서울/경기 확인·600초·본인 소유권 및 CSRF</td>
</tr>
<tr>
<td>`POST /origin-validations`</td>
<td>필요</td>
<td>origin: current_location/map_pin/saved_place. current_location.location_confirmed 선택boolean(기본false)</td>
<td>200: origin, label, location, location_address, expires_at, quality_status, quality, place_match</td>
<td>단발 위치/본인 장소·CSRF·10회/분·600초 메모리 선택. 현재 위치는 location_confirmed로 수동 확인, GPS 수치/자동 일치 판정은 보류</td>
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
<td>label, location, source?(기본search), search_id/candidate_id(search필수), location_confirmation_id(map_pin필수/search선택), entrance_ref(null), entrance_note?</td>
<td>201: place</td>
<td>검색 후보 또는 확인된 지도 핀으로 장소 등록. 본인·600초·좌표 일치, 선택 Idempotency-Key24시간(5.1.4)</td>
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
<td>expected_version, label?, location?, location_confirmation_id?, entrance_note?</td>
<td>200: place</td>
<td>본인 위치/설명 수정, 버전409 검사 및 버전 증가. 실제 산정 재사용 무효화는 F04/F05 후속</td>
</tr>
<tr>
<td>`DELETE /places/{place_id}`</td>
<td>필요</td>
<td>없음</td>
<td>204: 본문 없음</td>
<td>본인 장소 즉시 삭제204, 저장 재시도 키는NULL 삭제 표시. 연관 루틴은 해당 출발·도착 참조를 해제하고 status를 needs_attention으로 바꾼다(5.3)</td>
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
<td>F04-01은 depart_now 카카오 후보 비동기 조회. AI 도보·목표 도착은 후속</td>
</tr>
<tr>
<td>`GET /journey-searches/{search_id}`</td>
<td>필요</td>
<td>경로: search_id</td>
<td>200: status, candidates\[\], unavailable_reasons\[\]</td>
<td>완료·진행·실패 구분. 실시간/시간표 근거 표시</td>
</tr>
<tr>
<td>`GET /journey-searches/{search_id}/candidates/{candidate_id}/walking-evidence`</td>
<td>필요</td>
<td>경로: search_id, candidate_id</td>
<td>200: walking.evidence.v1, status=needs_data, segments\[\], expires_at</td>
<td>F05-01 기존 후보의 접근/환승/마지막 도보 제공값·누락 조회. 물리 범위 미검증, AI/저장/재사용은 후속</td>
</tr>
<tr>
<td>`GET /walking-estimates/{estimate_id}`</td>
<td>필요</td>
<td>경로: estimate_id</td>
<td>200: estimate_id, revision_id, base_seconds, estimated_seconds, source, reused, calculated_at, expires_at</td>
<td>F05-04 본인 검증 산정 요약(5.5.3). 만료/삭제404·위치/프로필409, 조건별 재사용은 후속</td>
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
<td>본인 목록·페이지 조회. F06-03 계약5.3.1, 구현 완료</td>
</tr>
<tr>
<td>`POST /routines`</td>
<td>필요</td>
<td>name, origin_place_id, destination_place_id, search_id, candidate_id, weekdays(필수), target_arrival_local_time(선택)</td>
<td>201: routine</td>
<td>본인 검색의 유효 후보만 저장하고 journey_plans 스냅샷을 만든다(5.3). 실시간 도착 시각을 영구 경로로 저장하지 않음. F06-01 구현, 요일·목표 도착 입력은 F06-02 구현</td>
</tr>
<tr>
<td>`GET /routines/{routine_id}`</td>
<td>필요</td>
<td>경로: routine_id</td>
<td>200: routine</td>
<td>루틴 상세. F06-01 구현</td>
</tr>
<tr>
<td>`PATCH /routines/{routine_id}`</td>
<td>필요</td>
<td>expected_version, name?, weekdays?, target_arrival_local_time?, 경로 참조4개(함께)</td>
<td>200: routine</td>
<td>일정 변경 F06-02 구현, 이름·경로 교체 F06-03 계약5.3.1·구현 완료</td>
</tr>
<tr>
<td>`DELETE /routines/{routine_id}`</td>
<td>필요</td>
<td>없음</td>
<td>204: 본문 없음</td>
<td>기존 이동 기록은 당시 스냅샷 유지, 삭제된 루틴 참조는 표시용으로만 사용. F06-03 계약5.3.1·구현 완료</td>
</tr>
</table>
약속·초대·중간 추천·채팅·공유 API의 입력/응답/권한/이벤트 상세는 이 페이지 16절에 있다. F06-01의 POST /routines·GET /routines/\{routine_id\}는 구현했고 F06-03 목록·수정·삭제는5.3.1 구현 완료이며 약속·출발 안내·이동 관측 API는 미구현 설계 초안이다.
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
<td>`GET /journey-searches/{search_id}/candidates/{candidate_id}/first-arrivals`</td>
<td>필요</td>
<td>본인 search_id/candidate_id</td>
<td>200: arrival.evidence.v2, status, source_status, timing_basis, candidates, received_at/generated_at, expires_at, valid_for_guidance</td>
<td>5.9: 검증된 경기 첫BUS 조회/60초 메모리 재사용. 원천unknown은 명시한 수신 기준 추정으로만 사용, 미매핑/지하철/만료/후보 없음은 안내 제외</td>
</tr>
<tr>
<td>`GET /journey-searches/{search_id}/candidates/{candidate_id}/first-departure`</td>
<td>필요</td>
<td>본인 search_id/candidate_id, departure_basis=recommended/now(기본recommended), include_connections:boolean(기본false)</td>
<td>200: first.departure.v1, status, recommended/selected_departure_at, vehicle_arrival_at, approach_seconds, buffer_seconds, slack_seconds, timing_basis, valid_until, provider_approach_source, approach_fetched_at, approach_valid_until, arrival_evidence, connection_status, transfers, estimated_final_alighting_at, target_evaluation</td>
<td>5.7.1\~6: 첫 차량 출발·버스 환승·선택루틴의 오늘 목표 평가. 미확인/만료는 숫자 없음, 미래예약/대체노선 자동조회는 후속</td>
</tr>
<tr>
<td>`POST /routines/{routine_id}/departure-searches`</td>
<td>필요</td>
<td>expected_version, Idempotency-Key 선택·CSRF</td>
<td>202: search_id/job_id/status/routine_id/routine_version</td>
<td>5.7.3: 현재 본인 저장장소로 최신검색, 루틴/장소변경 차단·10회/분</td>
</tr>
<tr>
<td>`GET /routines/{routine_id}/departure-searches/{search_id}/first-departure`</td>
<td>필요</td>
<td>expected_version</td>
<td>200: routine.departure.v1/status/candidate_id/nullable departure/expires_at</td>
<td>5.7.3: 저장노선 유일후보만 첫출발/환승 검사, 불일치·복수·없음은 숫자없음</td>
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
아래 값은 합성 예시이며 검색 응답에서 받은 본인 후보 ID와 좌표로 저장한다.
`POST /api/v1/places`
```json
{"label":"집","location":{"latitude":37.5001,"longitude":127.0001},"search_id":"00000000-0000-4000-8000-000000000001","candidate_id":"00000000-0000-4000-8000-000000000002","entrance_ref":null}
```
```json
{"data":{"place_id":"00000000-0000-4000-8000-000000000003","label":"집","name":"합성 건물","address":"서울 합성 주소","location":{"latitude":37.5001,"longitude":127.0001},"entrance_ref":null,"version":1,"location_version":1},"meta":{"request_id":"req_demo_01","server_time":"2026-10-07T00:00:00Z"}}
```
장소 좌표는 필요한 인증 응답에는 포함되지만 일반 실행 로그에는 남기지 않는다. 출입구 변경은 F03-02 후속이다.
### 5.1.1 F03-01 장소 검색·저장 상세 계약
- F03-01 최초 구현(2026-10-07): POST /place-searches, POST /places, GET /places 및 GET /places/\{place_id\}. 당시 검증 백엔드68개·프론트35개·빌드·카카오 검색/저장. 현재 지도 핀/출입구 설명/수정 및 응답 추가 필드는5.1.2절 F03-02 확장을 따른다. 삭제/현재 위치/전체 산정 재사용은 후속이다.
- 모든 API는 로그인 사용자 소유권과 no-store 적용. POST는 Origin/CSRF 검증. 검색어·주소·좌표·후보 원본·키는 일반 실행 로그 제외, 외부 카카오 HTTPS 호출은 서버에서만 수행하며 리다이렉트 금지.
- 검색 입력 query는 앞뒤 공백 제거 후1\~100자. 카카오 주소 검색과 키워드 검색을 각각 최대10건 호출하여 서울특별시·경기도 주소만 남기고 좌표/주소 중복 제거, 주소 결과 우선 최대20건. 공급자 응답이 잘못되면502 PROVIDER_RESPONSE_INVALID, 접속/인증/쿼터 실패503 PROVIDER_UNAVAILABLE. 검색 요청 사용자별 분당10회, 초과429와 Retry-After.
- 검색200 data: search_id, expires_at(생성후600초), candidates 배열. 후보는 candidate_id, name, address, location(latitude/longitude). 후보/검색 ID는 서버 발급 UUID이며 사용자와 검색에 묶인다. 주소/키워드 매칭이 없어도200 빈 배열. 첫 페이지 범위이며 모든 결과 조회를 보장하지 않는다.
- 저장 입력: label(공백 제거 후1\~30자), location, search_id, candidate_id 필수. entrance_ref는 이번 단계 null만 허용. 서버는 본인 검색/후보·만료 및 후보 좌표 일치를 검증한다. 임의 좌표/다른 후보 좌표422 VALIDATION_ERROR, 타인/만료/없는 후보404 RESOURCE_NOT_FOUND. 지도 핀 저장 계약은 F03-02 구현 시 확장한다.
- 저장201 data: place_id, label, location, entrance_ref(null), version(1), name, address. 선택 후보의 최소 이름/주소/좌표만 장소에 저장, 검색어와 공급자 원본은 영구 저장하지 않는다. 집/회사 외 라벨도 지원하며 이름 중복은 허용한다.
- POST /places는 선택 Idempotency-Key(1\~128자 영문/숫자/밑줄/하이픈) 지원. 사용자+경로+키로24시간 중복 결과 유지, 같은 본문은201 기존 장소 반환, 다른 본문은409 IDEMPOTENCY_CONFLICT. 권한 재검사 후 재응답하며 만료 후보라도 유효한 저장 재시도는 기존 결과 반환. 헤더 없이 생성하면 별도 장소가 된다.
- GET /places는 limit 기본20/최대100, 선택 cursor(이전 응답 next_cursor UUID). 생성 ID 내림차순으로 본인 목록만 반환. 타인/없는 cursor404. GET /places/\{place_id\}는 타인/없는/잘못된 ID404.
- 검색 후보는10분 후 접근 불가 및 다음 검색에서 만료행 청소. 멱등 결과는24시간 후 접근 불가 및 다음 저장에서 청소. 매일 청소 운영 스케줄은 F11 후속. 장소는 삭제/탈퇴까지 보관하며 F03-03 삭제 및 F11-02 탈퇴 API는 미구현.
- 호환성: 기존 장소 생성 예시는 미구현 설계였다. search_id/candidate_id 필수 필드와 name/address 응답 필드를 구체화하므로 첫 클라이언트는 검색 후 선택 흐름을 사용한다. 기존 인증·health·루틴 계약에는 영향 없다.
### 5.1.2 F03-02 지도 핀·출입구 확인/수정 계약
- 구현 상태(2026-10-07): 지도 SDK·위치 확인·생성 핀 저장·PATCH 구현. 실제 지도 클릭/드래그/방향 버튼·저장/수정·새로고침 유지 및 데스크톱1440×1000/모바일390×844 확인. 검증 근거는 `development_log.md`. 백엔드80개(새 핀12개 포함)·프론트49개·빌드 및 기존 장소 보존/0003↔0004 왕복 검증 완료. 도보/경로 산정 저장소는 미구현.
- 구현 범위: 검색 후보 또는 본인 저장 장소를 카카오 지도에서 확인, 클릭/마커 드래그/방향 버튼으로 핀 수정, 선택 위치 확인 후 저장. 출입구 설명은 사용자가 입력한1\~100자 또는 null이며 공식 출입구 ID/실내 위치 인증이 아니다. 기존 entrance_ref는 null 유지, entrance_note를 별도 추가한다.
- GET /map-config: 로그인 필요·no-store.200 data.javascript_key는 지도 SDK용 공개 JavaScript 키(등록 도메인 제한용)만 반환한다. 서버 REST 키는 반환하지 않는다. 키 미설정503 MAP_UNAVAILABLE. 지도 SDK는 공식 HTTPS SDK에서만 로딩하며10초 후 실패/재시도 안내. SDK 활성화/등록 도메인 설정은 카카오 앱 설정에 필요하다.
- POST /place-location-confirmations: 로그인·Origin/CSRF·no-store. 입력 location(latitude/longitude). 사용자당10회/분(429/Retry-After), 서버 카카오 coord2regioncode HTTPS로 서울/경기 법정동 범위 확인.200 data.confirmation_id(UUID), location, location_address(법정동 명칭, 정밀 주소가 아님), expires_at(생성후600초). 공급자503/잘못된 응답502는 검색과 동일. 바다/지원지역 밖422 UNSUPPORTED_REGION. 실패를 다른 지역으로 추측하거나 임의 좌표로 성공 처리하지 않는다.
- source=search의 POST /places 기존 필드는 유지, 선택 location_confirmation_id와 entrance_note 추가. 기존 후보와 동일 좌표는 기존 저장 가능. 다른 좌표는 본인/미만료 확인 ID와 정확히 일치해야 하며 확인 ID가 없으면422. 타인/만료/없는 확인404. 검색/후보 소유권과 만료 검사도 유지. 선택 확인 ID가 있으면 같은 좌표라도 source=map_pin. 기존 클라이언트 입력과 멱등 재시도 해시 호환 유지.
- PATCH /places/\{place_id\}: 로그인·Origin/CSRF·no-store. expected_version(정수\>=1) 필수, 선택 location, location_confirmation_id, entrance_note. 최소 하나의 location/entrance_note 필요. location이 있으면 일치하는 본인/미만료 확인 ID 필수. 설명 null은 제거.200 장소 객체. 타인/없는/잘못된 장소 ID404, 오래된 expected_version409 VERSION_CONFLICT. 서버가 행 잠금 후 소유권→버전→확인 ID/좌표를 검사하고 한 트랜잭션으로 갱신한다.
- 좌표 또는 출입구 설명/위치 출처가 바뀌면 version+1 및 updated_at 갱신. 같은 좌표/설명/출처는 버전을 유지한다. 검색 원래 name/address는 수정하지 않는다. label 수정은5.1.3절 확장을 따른다. 사용자 핀의 법정동 명칭은 location_address로 별도 저장하고 원래 검색 주소와 구분한다.
- 장소 응답 추가 필드: entrance_note(null/string), location_source(search/map_pin), location_address(null/법정동 명칭). 기존 location은 실제 계산 출발점이며 지도 핀 또는 검색 좌표다. 기존 장소는 source=search/추가 필드null로 마이그레이션한다.
- 도보/경로 근거는 F03-03부터 place_id/location_version을 사용한다. 일반version은 모든 수정 충돌 검사, location_version은 위치/출입구/출처 변경에만 증가한다. 이름만 변경해도 위치 근거를 유지한다. 장소가 없거나 location_version이 다르면 재사용하지 않는다. 실제 경로/도보 저장소의 재사용 검증은 F04/F05 후속이다.
- 확인 결과10분 후 접근 차단/다음 확인에서 만료행 청소, 매일 청소 스케줄은 F11 후속. 일반 로그에 키/좌표/주소/출입구 설명/공급자 원문을 출력하지 않는다. 지도는 해당 위치를 카카오에 표시하며 AI에 전달하지 않는다. 보관·공급자 조건은 기존 사용자 추가 확인 생략 지시와 미검증 상태 유지.
- UI: 지도 로딩/실패/재시도, 위치 확인 중/실패/지원지역 밖/만료, 핀 변경 시 이전 확인 제거, 저장 중 비활성,409 시 최신 장소 재조회 후 재확인, 세션 만료/화면 이탈 자료 제거와 요청 취소. 키보드 방향 버튼5m 이동 및 검색 위치로 되돌리기를 제공한다. 현재 위치 권한 요청은 F03-04 후속.
- 호환성: 기존 API에 선택 입력과 응답 필드 추가, 신규 config/확인 API와 기존 설계 PATCH 구현. F03-01 저장 흐름과 인증/health 유지. 장소 삭제/라벨 수정은5.1.3절 F03-03 확장에 구현했다.
### 5.1.3 F03-03 내 장소 이름 수정·삭제 계약
- 구현 상태(2026-10-07): label PATCH·DELETE204·삭제된 저장 키 재생성 방지·location_version 구현. 백엔드90개(관리10개 포함)·프론트57개·빌드 통과. 실제 DB/ASGI·로컬 HTTP·데스크톱1440×1000/모바일390×844 검증, 근거는 `development_log.md`. 루틴/산정 저장소는 후속.
- PATCH /places/\{place_id\}에 선택 label 추가(공백 제거 후1\~30자, null/빈 값 거절). 기존 location/확인 ID/entrance_note 및 expected_version 규칙 유지, 최소 label/location/entrance_note 중1개. 같은 값은 유지, 이름 또는 위치/출입구가 바뀌면 일반 version+1.200 장소 객체. 로그인·Origin/CSRF·no-store, 본인 행 잠금·타인/없는404·오래된 version409·입력422.
- 이름(label)은 사용자가 저장한 이름이며 검색 원래 name/address와 구분한다. 이름만 바꾸면 지도 공급자를 재호출하지 않고 실제 위치/출입구를 바꾸지 않는다.
- 새 응답 location_version(정수\>=1)은 위치/출입구/출처의 계산 근거 버전이다. 최초 생성1, 위치/출입구/출처가 바뀔 때만+1, label만 수정하면 유지. 기존 장소는 마이그레이션에서 현재 version으로 초기화하여 이미 알려진 위치 버전을 보존한다. 일반 version은 모든 수정 충돌 검사에 사용한다.
- F06-04 연동(2026-10-08): location_version 증가 시 연결된 본인 루틴을 같은 트랜잭션에서 needs_attention·version+1로 바꾼다. label만 변경/동일 값 재저장은 루틴을 무효화하지 않는다. 이전 경로 스냅샷/일정은 유지하며 재조회 후보로 PATCH한 뒤 active 복구한다. 세부 흐름은5.3.3.
- F04/F05에서 place_id/location_version 일치와 장소 존재 여부로 산정 재사용을 검사한다. 기존5.1.2의 place_id/version 계산 근거 규칙을 location_version으로 구체화하며 label 변경으로 지도/AI를 재산정하지 않는다. 아직 실제 경로/도보/루틴 테이블 및 API는 미구현이다.
- DELETE /places/\{place_id\}: 로그인·Origin/CSRF·no-store, 입력 본문 없음. 서버가 본인 장소 행을 잠그고 현재 저장소의 장소 이름/주소/좌표/설명을 같은 트랜잭션에서 즉시 물리 삭제. 성공204 본문 없음/X-Request-ID. 타인/없는/잘못된 ID 및 반복 삭제404 RESOURCE_NOT_FOUND, 인증401·CSRF403·DB503. 기존204 계약 유지, 위치 공급자 호출 없음.
- 연결된 place_creation_keys는24시간 재시도 기한까지 사용자/키/본문 해시/만료만 유지하고 place_id는NULL로 지워 삭제 표시로 사용한다. 같은 저장 키/본문 재시도는404로 반환하여 삭제한 장소를 재생성하지 않는다. 다른 본문은기존409, 다른 키를 통한 명시적 신규 저장은 허용. 후보/위치 확인은 독립된10분 자원이며 다른 검색/확인 자료를 일괄 삭제하지 않는다.
- 현재 연결 저장소는 saved_places와 생성 재시도 키뿐이다. F06 실제 루틴 추가 시 삭제 장소 참조를NULL 및needs_attention으로 바꾸고 이전 경로/도보를 재사용하지 않아야 한다. 과거 이동 스냅샷은 보관 정책에 따른다. 이번 기능은 미구현 루틴/산정 처리를 완료했다고 표시하지 않는다.
- UI: 각 장소에 이름 수정·삭제 동작. 이름 수정에 현재 version을 전송,409이면 최신 자료 재조회 후 다시 수정. 삭제는 대상 저장 이름과 취소/삭제 버튼으로 화면에서 확인, 확인 전 요청 없음. 처리 중 비활성·실패/재시도·세션 만료/이탈 취소. 삭제204 또는 이미 없는404는 목록에서 제거하고 목록 첫 페이지 재조회, 재조회 실패는 목록 재시도 안내를 유지. 화면에는 기술용 키/좌표/요청 ID를 노출하지 않는다.
- 동시 수정/삭제는 본인 장소 행 잠금으로 직렬화, 삭제 후 조회/수정/동일 저장 키 재시도는404. 사용자별 소유권·버전/동시성·삭제 재시도·목록/페이지·로그 비노출을 검증한다. 일반 로그에는 라벨/주소/좌표/본문/쿠키/삭제 대상 원문을 출력하지 않는다.
- 호환성: 기존PATCH에 선택label·응답location_version 추가, 기존 설계DELETE204 구현. 현재 일반version 클라이언트의 수정 충돌 검사는 유지. 향후 경로/도보 클라이언트는location_version 계산 근거를 사용한다. 장소 삭제는 현 저장소에서 동기 완료하므로 별도202 job을 만들지 않으며 개인 이동/탈퇴의202 사본 정리 계약은 유지한다.
### 5.1.4 F03-02a 검색 없이 지도 핀 저장
- 계약 확정 <mention-date start="2026-10-08"/>: POST /places에 source(search 기본값/map_pin)를 추가한다. source=search는 기존 search_id/candidate_id 필수·후보 검증/선택 핀 확인 계약 유지. source=map_pin은 label(1\~30자),location,location_confirmation_id 필수이며 search_id/candidate_id는 생략 또는 null만 허용한다. entrance_note 선택1\~100자, entrance_ref=null 유지. 직접 name/address 입력은 허용하지 않는다.
- map_pin은 본인·미만료600초 확인 ID와 좌표가 정확히 일치해야 한다. 인증401·Origin/CSRF403·형식/좌표 불일치422·타인/만료/없는 확인404. 확인은 기존 서울/경기 법정동 조회 규칙을 따른다. name은 생성 당시 label, address/location_address는 서버 확인 법정동 명칭이며 정밀 주소나 공식 장소명이 아니다. location_source=map_pin, version/location_version=1. 생성201·기존 장소 응답 유지, 새 DDL 없음.
- 기존24시간 Idempotency-Key·409 본문 충돌·삭제 후 같은 키404 규칙 유지. 기본 search와 생략 source의 기존 해시 호환을 유지한다. 동일 키/본문 재시도는 확인 만료 후에도 기존 저장 결과 반환하며 새 저장은 만료 확인404. 추가 장소 검색/AI 호출 없음, 좌표·주소·이름·쿠키/본문 일반 로그 비노출.
- UI: 출발/도착 지도에서 사용자가 핀을 움직인 뒤 '이 위치 저장하고 사용'을 누르면 선택 좌표를 유지하고 이름만 입력한다(기본 출발지/도착지). 이미 선택한 지도 출발지/도착지에서 '새 장소 저장'을 열어도 해당 핀을 가져온다. 지역 확인→명시 저장→saved_place 검증/자동 선택 순서. 핀 이동만으로 저장하지 않는다. 단발 위치 사용도 유지. 처리 중 지도/방식/취소 비활성·이탈 요청 취소/늦은 응답 무시. 저장 실패는 같은 키/본문 재시도, 위치 확인 만료는 재확인 안내. 저장 성공 뒤 선택 검증 실패는 기존 저장 장소로 재선택하며 중복 생성하지 않는다. 루틴 저장은 양 끝 저장 장소로 새 경로 조회 후 별도 확인한다.
- 호환성: source 선택 입력과 map_pin 조건부 요청 추가, 기존 검색 기반 클라이언트/API/계산·보관 유지. 구현/검증 완료. 신규 백엔드4개/전체134개·프론트148개·빌드1903모듈 통과. 실제 PostgreSQL 테스트 임시 스키마/ASGI, 실제 지도+합성 API의 PC1440×1000/모바일390×844 저장 폼·자동 선택/가로 넘침0/콘솔error0 확인. 실행 서버 재시작·health200. 사용자 업무 DB 변경 없음.
- map_pin 요청 예시: \{"source":"map_pin","label":"집","location":\{"latitude":37.5665,"longitude":126.9780\},"location_confirmation_id":"00000000-0000-0000-0000-000000000001"\}. ID는 예시이며 실제 본인 확인 응답 ID를 사용한다. search_id/candidate_id 없이201로 저장한다.
### 5.2 현재 위치에서 경로 검색
`POST /api/v1/journey-searches`
```json
{
  "origin": {
    "type": "current_location",
    "latitude": 37.5001,
    "longitude": 127.0001,
    "accuracy_meters": 15,
    "captured_at": "2026-09-30T00:00:00Z",
    "location_confirmed": true
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
origin/destination은 saved_place 또는 좌표 출발 객체다. 권한 거절 시 지도 선택은 type=map_pin과 좌표를 전달한다. v0.40 실행 계약은5.2.3절을 따르며 현재 위치는location_confirmed:true 수동 확인 필수, GPS 수치 판정은 보류한다.
목표 도착 검색은 timing.mode=arrive_by와 timing.arrive_by의 절대 시각을 필수로 전달한다. 루틴의 반복 목표는 local time과 timezone으로 별도 저장한다.
후보는 candidate_id, validity, ordered_legs, transfer_count, total_seconds, estimated_arrival_at, time_sources, missing_segments를 포함한다. 후보 ID는 해당 사용자의 search_id 안에서만 유효하다.
### 5.2.1 F03-04 현재 위치·지도 출발지 선택
- 이 절은 최초 F03-04 기반 계약/검증 이력이다. 현재 위치 수동 확인·200 응답 확장은 아래 v0.39 5.2.2절을 함께 적용한다.
- 구현/검증(2026-10-07): 백엔드94개·프론트73개·빌드 통과. 실제 PostgreSQL/ASGI 소유권·위치 버전·CSRF·지원지역/공급자 실패·실패 포함 쿼터·메타데이터/로그 비노출 확인. 공개 서울시청 좌표의 로컬 HTTP current_location200/quality_status=pending·UTC 정규화·no-store, 실제 지도 방향 버튼/키보드·데스크톱1440×1000/모바일390×844 선택·준비 카드·새로고침 초기화 확인. GPS 성공/거절/시간초과/미지원/취소는 모의 검증이며 실제 기기 위치 요청/권한 승인·실제 휴대전화 GPS 확인은 미실행. 근거: `development_log.md`.
```json
{"origin":{"type":"current_location","latitude":37.5665,"longitude":126.978,"accuracy_meters":10,"captured_at":"2026-10-07T11:00:00+09:00"}}
```
- 위 합성 요청의200 data 예: origin.captured_at=2026-10-07T02:00:00Z, origin.type=current_location, label=현재 위치, location은 입력 좌표, location_address=서울특별시 중구 태평로1가, quality_status=pending, expires_at=meta.server_time 이후600초. 장소/경로 생성·GPS 최신성 보증으로 해석하지 않는다.
- 범위: 다른 곳에서 출발 → 로그인 확인 → 기기 현재 위치1회 요청 또는 지도 핀/본인 저장 장소 선택 → 서버 확인 → 화면 메모리에 출발지 선택. 실제 경로 검색/출발 시각은F04\~07 후속이며 선택된 실제 출발지에는 기존 집 기준 예시 안내를 적용하지 않는다.
- POST /origin-validations: 로그인·Origin/CSRF·no-store, JSON body.origin. 부작용 없는 출발지 입력 확인 API이며 장소/루틴/이동/검색 자원을 생성하지 않는다. 생성 멱등 결과 저장 규칙 대상 아님. 사용자당10회/분(429/Retry-After), 공급자 호출 전 제한 소비, 실패도 포함.
- origin 구분: current_location은 type, latitude/longitude, accuracy_meters(유한·0이상), captured_at(시간대 있는ISO8601) 필수. map_pin은 type, latitude/longitude. saved_place는 type, place_id 및 선택 location_version(정수\>=1). 알 수 없는 필드·종류/좌표/시각 형식422 VALIDATION_ERROR.
- current_location/map_pin은 서버 카카오 지역 확인으로 서울/경기 범위를 검증한다. 지역 밖/바다422 UNSUPPORTED_REGION, 공급자503/잘못된 응답502는 기존 동일. saved_place는 본인/존재404·location_version 불일치409 VERSION_CONFLICT, 이름만 바뀌면 현재 저장 이름으로 반환하며 공급자 재호출 없음. 근처에 있다는 이유로 current_location을saved_place로 변환하지 않는다.
- 200 data: origin(검사한 종류/필드, saved_place는현재location_version 포함), label(현재 위치/지도 선택 위치/본인 저장 이름), location(latitude/longitude), location_address(법정동 또는 저장 주소), expires_at(서버 확인후600초), quality_status(current_location=pending, map_pin/saved_place=not_applicable). meta는 기존 공통. captured_at은UTC로 정규화, accuracy는측정치이며 위치 보증 아님.
- F03-04는 측정 시각/정확도의 형식과 전달을 구현한다. v0.39에서 수동 확인만 추가한다. GPS 수치 기준·자동 저장 장소/출입구 일치 판정은 사용자 결정으로 보류하며 pending/user_confirmed 모두 실제 경로 계산 가능 보증으로 처리하지 않는다. 현재 화면에는 실제 출발 안내 없음.
- 기기 위치 요청은 명시 버튼 클릭 후 getCurrentPosition 1회, enableHighAccuracy=true/maximumAge=0/timeout=10000ms. 앱 전체 대기는15000ms까지(권한 응답 대기 포함) 제한, 거절/시간 초과/위치 불가/HTTPS·API 미지원은 지도 선택과 재시도. watchPosition/백그라운드 추적/자동 권한 요청/역 내부 도착 판정 없음.
- 지도 시작은 본인 첫 저장 장소 또는 공개 서울시청 근사좌표(37.5665,126.9780). 시작 중심을현재 위치로 간주하지 않고 클릭/방향 버튼으로 명시 선택한 뒤 확인한다. 지도는 기존 SDK/공개 키/서버 REST 키 구분 유지, 선택 좌표를카카오로 지원지역 확인한다. GPS 원문·주소·좌표·쿠키/키는 로그 제외, 위치를AI로 전달하거나고정 장소에자동 저장하지 않는다.
- 선택은 화면 메모리에서만 유지, 새로고침/계정 모달 진입/인증 만료 인지 시 제거.600초 뒤 만료 안내/재선택, 실제 경로/출발 안내 대신 준비 중 카드, 예시 이동 시작 차단. 화면 이탈/방법 변경 시 요청 취소/늦은GPS 응답 무시. 저장 장소 목록 기본20/최대100 규칙·더보기/빈목록/조회실패 재시도 유지.
- 호환성: 신규 입력 확인API 및 출발지 선택UI 추가, 기존auth/장소/경로 검색 객체 유지. 현재GPS/지도 좌표를 영구 DB/URL/로그에 저장하지 않는다(요청 제한은기존HMAC 버킷). 경로 API에서는 다시인증/소유권/위치품질을검사해야 하며600초 선택유효기간은GPS 최신성 보장이 아니다.
### 5.2.2 F03-05 수동 위치 확인 (자동 GPS 수치 판정 보류)
- 사용자 결정(2026-10-07): GPS 측정 후 경과 시간·정확도·미래 시각 허용폭의 수치 기준은 보류한다. 60초/50m/5초 등 제안값을 구현하거나 확정 정책으로 사용하지 않는다. 자동 저장 장소 근접/출입구 일치 임계값도 미정이며 자동 일치 판정·도보 근거 재사용은 구현하지 않는다. F03-05는 수동 확인 부분만 구현하고 자동 품질/일치 판정 완료로 체크하지 않는다.
- POST /origin-validations current_location에 location_confirmed(선택 strict boolean, 기본false) 추가. false는200 quality_status=pending이며 확인 전, true는사용자가 지도상의 현재 출발 위치를 확인했다고 신고한200 quality_status=user_confirmed이다. 이 값은 GPS 정확성/최신성/실제 출입구 일치 검증이 아니며 서버가 위치를 보증하지 않는다. 다른 origin 종류에는 해당 필드를 받지 않는다.
- 모든200 data에 quality와 place_match 추가. quality는 assessment(current_location=unassessed, map_pin/saved_place=user_selected), confirmation(current_location false=required/true=reported, 나머지=not_applicable), numeric_policy=deferred, time_relation(current_location은서버처리시각 기준future/past_or_present, 나머지not_applicable). 측정 시각·정확도는origin의기존필드이며 시간 관계는표시 정보, 자동 유효/무효 판정 아님. quality_status=not_applicable은 지도/저장 장소 기존값 유지.
- place_match.status=current_location/map_pin은unconfirmed, saved_place는selected_by_user. 저장 장소의 명시 선택은 place_id/location_version 소유권·충돌 재검사 후 해당 저장 위치를 사용하는 행동이며 GPS와 물리적으로 같다는 인증이 아니다. GPS/고도/지하철 내부·출입구를자동확정하지 않는다.
- 구현/검증(2026-10-07): F03-05a 수동 확인 완료. 백엔드95개·프론트79개·빌드 통과. 실제 로컬 HTTP pending/user_confirmed200·no-store·미래 시각 표시 정보/품질 unassessed/일치 unconfirmed 확인. 실제 지도와 공개 좌표 합성 OriginReview 화면을 데스크톱1440×1000/모바일390×844에서 확인했고 지도 선택은 실제 앱/API로 회귀 검증했다. GPS 측정·확인/만료·실패는 모의 검증이며 실제 기기 GPS 권한 승인/정확도 검증은 수행하지 않았다. 임시 화면·합성 계정/세션 제거. GPS 수치·자동 일치 판정은 보류, 상위F03-05 미완료 유지. 근거 development_[log.md](http://log.md).
- UI: 명시GPS1회/인증·서울/경기 확인 → 지도 로딩 성공 후 측정 위치·측정 시각·정확도/미래 시각 표시 → '이 위치가 실제 출발 위치예요' 버튼으로같은 origin/location_confirmed=true 재확인 → 준비 카드. 확인 전 onSelect/실제선택 없음, 지도 핀을옮기면map_pin으로직접선택, 저장 장소는별도버튼으로사용자가선택한다. 다시측정/다른방법/이탈/계정/인증만료/600초 확인만료는 미확인자료를제거한다.
- 기존600초 선택/확인 유효기간은 유지하며GPS 최신성 기준으로 해석하지 않는다. 기한은meta.server_time과expires_at 차이로처리, 확인기간이끝나면현재위치를다시확인하도록한다. 입력이오래되거나미래라는이유로임의수치 차단하지 않고 화면에시각을표시해수동확인한다. 경로/출발 안내는F04\~07 후속이며지도/저장 장소의명시선택에도실제예시안내를적용하지않는다.
- 인증/Origin·CSRF/no-store/사용자10회·분(최초/확인/실패포함)/지역/오류/로그 비노출·임시App 메모리/DB좌표저장없음/AI전달없음은유지. 수동확인도기존출발지검증을다시호출하며확인 중서버실패/세션만료는선택하지않는다.
- 호환성: 기존current_location 요청은기본false와pending유지. 추가quality/place_match는추가필드이며user_confirmed는새location_confirmed=true요청에만반환한다. 수동확인UI를적용하려면프론트갱신/새로고침이필요, 이전pending을검증된품질로취급하지않는다. 이후경로API는인증/소유권/수동확인근거·미정GPS정책을재검사해야한다.
```json
{"origin":{"type":"current_location","latitude":37.5665,"longitude":126.978,"accuracy_meters":10,"captured_at":"2026-10-07T04:00:00Z","location_confirmed":true}}
```
- 위 공개 합성 좌표 요청은quality_status=user_confirmed, quality.assessment=unassessed/confirmation=reported/numeric_policy=deferred, place_match.status=unconfirmed로반환한다. GPS 위치 품질을valid로반환하지 않는다.
### 5.2.3 F04-01 대중교통 경로 후보 조회 (구현 단계 계약)
- 이 절은 최초F04-01 입력/작업 계약과 검증 이력이다. 현재 후보 구간/응답 확장은v0.41 5.2.4절을 함께 적용한다.
- 구현/검증(2026-10-07): 최신main8b4b40b 통합 후 백엔드106개·프론트79개·빌드 통과. 임시 PostgreSQL/ASGI에서 동시 멱등·소유권/위치 변경·초안 수동 확인 필수·만료/중단/늦은 응답·쿼터·응답 상한/리다이렉트/시간초과·로그/DB 입력 좌표 비저장·OpenAPI202 확인. 실제 로컬 공개 강남역→서울역 카카오 후보15개·POST202→GET200·no-store/요청ID·멱등 재현·작업 조회 성공, 합성 계정/세션/후보/키 제거. 실제 기기 GPS·AI/실시간·목표 도착·비교 화면·실제 환승/역 내부 정확도는 미검증. 근거 development_[log.md](http://log.md), journey_[api.md](http://api.md). UI 변경 없음.
- 범위: 로그인 사용자의 출발/도착 입력으로 카카오 대중교통 후보를 비동기 조회한다. 이번 단계는 depart_now(Asia/Seoul)만 실행하며 arrive_by는422 UNSUPPORTED_TIMING으로 명시한다. 목표 도착 검색·AI 도보 산정·실시간 도착·비교 화면·루틴 저장은 후속이며 기존 설계에서 삭제하지 않는다.
- POST /journey-searches: 쿠키·Origin/CSRF·no-store, origin/destination은 saved_place(place_id, location_version 선택), map_pin(latitude/longitude), current_location(기존 좌표/측정치 및 location_confirmed:true 필수). 현재 위치는 본인 보고만 사용하며 GPS 수치/자동 일치 판정은 보류한다. timing=\{mode:depart_now,timezone:Asia/Seoul\}, preferences.route_preference 선택 balanced/fewer_transfers/less_walking. 없는 선호는 본인 프로필 사용. 알 수 없는 필드/형식422. 양 끝 위치 서울/경기 확인은 접수 후worker에서 수행하며 지역 밖은GET200 failed/error.code=UNSUPPORTED_REGION이다. 본인 장소404·위치 버전409는 접수 전 검사, 이름 변경은 유효 유지.
- Idempotency-Key 선택(1\~128자 ASCII 영문/숫자/밑줄/하이픈): 사용자+경로+키와 비밀키 HMAC 본문 해시만24시간 보관, 같은 본문202 동일 search_id/job_id/queued 응답·현재 권한/위치 버전 재검사, 다른 본문409 IDEMPOTENCY_CONFLICT. 키 없이 새 검색이다. 사용자10회/분(실패 포함), 동시 진행 최대2개/사용자·전체8개로429 Retry-After. 중복 재현은 새 공급자 호출 없음.
- 접수202 data=\{search_id,job_id,status:queued\}. worker는 running→succeeded/failed로 전환하며 본인 장소 위치를 작업 전/후 다시 검사한다. 개별 공급자10초·지역 확인3초/회, 전체 작업60초 제한. 재시작/60초 초과 미완료 작업은 조회/새 요청에서 failed JOB_INTERRUPTED 처리, 사용자 좌표는 재실행하지 않는다. 실행 중 작업은 DB 상태/기한 조건으로 최종 결과를 반영하므로 늦은 응답이 실패 상태를 되돌리지 않는다.
- GET /journey-searches/\{search_id\}: 본인만200, 없거나타인/검색5분 만료404. status queued/running/succeeded/failed, candidates\[\], unavailable_reasons\[\], error(null 또는 공통code/message/details), expires_at 및 job_id. 진행 중 Retry-After:2; 후속 클라이언트는2/5/10/최대30초 및 비활성 중지 규칙 적용. 후보는 candidate_id,type,validity:insufficient_data,ordered_legs,transfer_count,total_seconds,total_distance_meters,walking_seconds,estimated_arrival_at:null,time_sources,missing_segments를 포함한다. 경로 ID는 본인 검색 안에서만 유효.
- ordered_legs는 최소 WALKING/BUS/SUBWAY 종류·순서·공급자 seconds/meters·정류장명/차량명만 정리한다. 시간 출처는 provider_estimate이며 접근/환승/마지막 도보의 AI 산정·실시간/미래 환승·역 출입구/플랫폼·중간 지역 범위는 미확인으로 명시한다. 후보 총 시간을 현재 시각에 더해 실제 도착 시각으로 만들지 않는다. 지도 geometry/공공 ID 매핑·완전한 방향/내부 이동은 F04-02\~05 후속이다.
- 최대2회 환승을 적용해 제외 사유 TRANSFER_LIMIT를 기록한다. 후보는 최대20개, balanced 총 소요시간·fewer_transfers 환승수·less_walking 공급자 도보시간 우선으로 정렬하며 동률은총시간/환승수/도보시간·공급자순서로 결정한다. 이 순서는 실시간 탑승 가능/최적 경로 보증이 아니다.
- 정상 무결과/EQUAL_POINTS/출발·도착 노드 없음은 succeeded/candidates\[\]/NO_ROUTE 또는 ENDPOINT_UNRESOLVED 사유, 공급자 장애는 failed PROVIDER_UNAVAILABLE, 시간초과 failed PROVIDER_TIMEOUT, 잘못된 응답 failed PROVIDER_RESPONSE_INVALID. failed 조회 자체는200, 접수 전 입력/권한/DB/제한 오류는 공통 HTTP 오류. 예상 밖 worker 오류는 안전한 INTERNAL_ERROR, 원문/스택 미노출.
- GET /jobs/\{job_id\}: 본인 작업 상태·종료/error/result_ref/결과 만료 여부만 조회, 후보/입력 좌표는 포함하지 않는다. 작업 상태는 종료 후24시간, 진행기한초과는failed 처리. 검색 결과는 생성부터300초, 선택/재현 시 별도 만료·장소 존재/위치 버전 검사. 만료 검색은 재실행하지 않고 새 요청을 요구한다.
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
- F04-03a 이동 방법 우선 보기: 결과에서 전체(기본)·버스(BUS)·버스 + 지하철(BUS_AND_SUBWAY)·지하철(SUBWAY)을 선택하면 해당 type 후보를 즉시 앞에 배치한다. 각 그룹 안에서는 기존 시간/환승/도보 비교 기준을 유지하며 다른 후보를 숨기지 않는다. 선택한 방식이 없으면 안내하고 기존 후보를 유지한다. 선택은 현재 결과 화면 메모리에만 보관하며 새 결과는 전체로 시작한다. 후보 ID에 연결된 상세·루틴 입력 상태를 유지한다. 추가 API/공급자 요청·DB 저장·응답 필드 변경 없음, 기존 클라이언트 호환성 영향 없음. 구현/검증 완료(2026-10-08): 프론트 138개 테스트·빌드1902모듈 통과. 합성 후보 PC1440×1000/모바일390×844에서 세 방식 즉시 첫 카드 이동·전체 복원·가로 넘침 없음·콘솔error0 확인. 실제 공급자 재호출/백엔드 재검증은 이번 작업에서 실행하지 않았다. 근거 `development_log.md`.
- 구현/검증(2026-10-07): 최신main63674ac에서codex/journey-comparison 구현. 프론트97개·빌드1899모듈·백엔드115개 회귀 통과. 실제합성계정/공개강남역→서울역 위치직접선택→POST202/GET200→15후보 비교/로컬정렬·상세/정류장순서·누락도보·키보드 Enter를확인했다. PC1440×1000/모바일390×844 카드·상세/하단메뉴·홈/설정/계정 회귀·가로넘침없음/콘솔error0, 자연검색만료시후보/상세제거 확인. 숨김/재시도/빈결과/실패/인증만료/늦은응답은 모의검증, 실제GPS권한/측정·실시간/운행시간표·AI/출발안내·루틴저장은미검증. 합성계정/장소/검색/작업/세션제거. 근거 `development_log.md`.
- 홈 '경로 후보 비교' 진입으로 기존 내비게이션/미색·초록 디자인을 유지한 비교 페이지를 제공한다. 아직 유효한 홈 출발지는 초기값으로 사용할 수 있으며 출발/도착은 기존 current_location/map_pin/saved_place 확인 흐름을 재사용한다. 도착 위치도 목적을 표시해 직접 선택한다. 로그인 전 기기 위치를 요청하지 않고 GPS 수동 확인/수치 보류를 유지한다.
- 출발/도착·선호를 명시 선택한 뒤 '경로 후보 조회'를 누를 때만 기존 POST /journey-searches를 호출한다. depart_now/AsiaSeoul 및balanced/fewer_transfers/less_walking만사용하며현재시각·주소원문을임의로입력하지않는다. 최초 접수에 새 Idempotency-Key, 접수 응답을 못 받은 네트워크/시간초과 재시도는 동일 본문/키를 유지한다. 입력 변경/새 검색은 새 키, 접수된 검색의 조회 실패는 GET만 재시도하며 POST 자동 재전송 없음.
- queued/running 접수는 완료로 표시하지 않는다. 최초2초→5→10→최대30초 간격으로 GET 결과 조회, 유효한 Retry-After 초 헤더를 우선하고1\~3600초 범위를 처리한다. 비활성 화면은 새 조회를 멈추며 진행 중 GET을 취소, 복귀 시 같은 search_id를 이어서 조회한다. 페이지 이탈/방법·입력 변경/로그인 모달·인증 만료 인지/입력600초 및검색300초 기한은 타이머·요청을 취소하고 늦은 응답을 무시한다. meta.server_time/expires_at 차이로 만료를 계산하며 입력 선택 유효기한보다 연장하지 않는다.
- 화면 상태: 위치 미선택/로그인 필요·접수/조회중·succeeded 후보/정상무결과·failed 안전한오류·네트워크조회재시도·권한/장소버전충돌·만료/재선택. 인증 실패는 좌표/목록/후보를 제거하고로그인행동,409 VERSION_CONFLICT는입력재선택,404 결과조회는만료/재검색. 숨겨진 화면/새로고침/계정변경에서 URL/DB/localStorage로 개인 위치/후보를 복원하지 않는다.
- 비교 카드: 카카오 예상 total_seconds·transfer_count·교통구간수기반차이가있으면횟수확인필요·제공된 walking_seconds 및누락여부. 접근/환승/마지막 도보가 빠지면0분으로확정하지않고‘도보 확인 필요/일부 도보·미확인 구간 있음’으로표시한다. DURATION_TOTAL_MISMATCH는총시간확인필요,unallocated_seconds는대기/여유로채우지않는다. 도착시각·출발까지카운트다운·탑승보장 없음. 실제응답에심야노선이포함될수있으므로 운행시간과지금이용가능여부는확인필요로표시하고시간표를추정해제외/인증하지않는다.
- 전체 예상 시간/환승수/제공된 도보시간 기준으로 로컬 정렬하며새 공급자요청을자동발생시키지않는다. 상세보기는화면메모리의한후보구간을펼치는동작이며실제이동/루틴저장이아니다. WALKING 역할과seconds/meters, BUS/SUBWAY 차량명·선택적세부분류/승하차 정류장순서를표시한다. 운행방향/공공ID·물리정류장일치·연결 feasibility는검증되지않았음을쉬운문구로표시한다. 연결 도보null과0을구분하며빠진접근/마지막도보·AI/실시간/출입구/플랫폼·중간지역·미정GPS 근거를안내한다.
- 프론트는journey.v1 후보/순서/ID/시간분해/연결참조·응답ID/기한·상태를검증하고깨진형식/미지원모델버전은성공으로표시하지않는다. 공급자/서버오류원문·주소·키/본문·좌표/후보를로그에출력하지않는다. React 텍스트출력·기존lucide/카드/버튼/CSS 변수·44px 행동·키보드 상세보기·모바일 줄바꿈을 유지한다.
- 기존API경로·입출력/권한/DB DDL·작업/보관·지도공급자 계약은 유지한다. 공통클라이언트는Retry-After 파싱 결과만 추가노출하고 자동재시도는추가하지않는다. API모델의실시간/AI/목표도착 미구현 상태를화면에서검증됨으로바꾸지않는다.
### 5.2.6 F04-05 경로 없음·지원 범위·정보 부족 안내
- 구현/검증(2026-10-07): 최신main63674ac에서codex/journey-unavailable 생성 후 필요한F04-03 커밋33efcec를fast-forward 통합했다. 게시 전F04-03 병합main4f94af1을다시fast-forward 반영했으며트리변경없음을확인했다. 프론트101개·백엔드117개·빌드1900모듈 통과. PostgreSQL/ASGI 모의공급자로 양 끝 지역 밖 worker failed/공급자 미호출, 무경로/지점/환승 제한과 실패 구분, 위치 재선택/새 키·정보 부족 유지·알 수 없는 사유 비노출 확인. PC1440×1000/모바일390×844 합성 상태 컴포넌트 시각검증·Enter 상세·44px 버튼·가로넘침없음·콘솔error0, 실제홈/비교입력 화면회귀 확인. 실공급자 새 호출/실GPS·운행/물리근거 검증은 수행하지 않았다. 임시시각검증파일 제거, 근거 `development_log.md`.
- 사용자 지시(2026-10-07): F04-04 물리 환승/출입구/플랫폼 근거 보강은 보류하고 F04-05를 먼저 진행한다. 보류 근거를 검증된 값으로 채우지 않는다.
- 정상 succeeded 빈 후보와 failed 공급자 장애를 구분한다. NO_ROUTE는 조회된 경로 없음, ENDPOINT_UNRESOLVED는 승하차 지점 연결 불가, TRANSFER_LIMIT는 최대2회 환승 지원 범위 초과로 각각 안내하며 복수 사유는 함께 표시한다. 알 수 없는 코드/빈 사유는 일반 확인 불가 안내로 처리하고 원문 코드나 공급자 메시지를 표시하지 않는다. 모든 후보가 환승 제한으로 제외되면 TRANSFER_LIMIT만 반환하고 NO_ROUTE를 추가하지 않는다.
- 입력 양 끝 지역은 POST202 접수 후 worker에서 확인한다. 지역 밖은 GET200 data.status=failed/error.code=UNSUPPORTED_REGION으로 반환한다. 기존 위치 선택 POST /origin-validations는 지역 밖422이며 경로 작업 실패와 구분한다. 화면은 검색 만료와 구분해 서울·경기 지원 안내 및 출발/도착 재선택 행동을 제공한다. 입력 선택/후보/검색 snapshot은 제거하며 잘못된 입력의 자동 재전송은 없다. 중간 경로 REGION_PATH_UNVERIFIED는 지역 밖으로 확정하지 않고 미확인 근거로 표시한다.
- 후보가 있는 insufficient_data는 삭제하거나 이용 가능으로 승격하지 않는다. 목록에 ‘구간 정보 확인 필요’와 상세에서 접근/환승/마지막 도보·방향·출입구/승강장·실시간·AI·지역/시간 불일치 사유를 구분해 표시한다. 알 수 없는 누락 사유는 일반 미확인 안내, 누락값을0으로 채우지 않는다. 결과 재확인은 기존GET이며 새 조회는 새POST/키를 사용한다.
- API 경로/필드/인증/소유권/기한/보관/로깅 및 journey.v1 모델 유지. 사유 정밀화는 기존 unavailable_reasons 필드 안의 동작 보완이며 이전 클라이언트의 TRANSFER_LIMIT 안내와 호환된다. GPS 수치·자동 판정과 실제 경로 선택/저장·출발 안내는 이번 범위에 포함하지 않는다.
### 5.3 루틴 저장·일정 계약(F06-01·F06-02)
- 구현/검증(2026-10-07): main 2367681에서 helpycode/routine-save 브랜치로 구현했다. 백엔드 unittest 123개(루틴 6개 신규 포함), 프론트 테스트 110개(루틴 9개 신규 포함), Vite 빌드 통과. 실제 카카오 공급자로 PC1440×1000과 모바일390×844에서 후보 카드 안 이름 입력 패널(기본 이름 '출발 → 도착 통근' 미리 채움, 빈 값은 기본 이름 사용)·저장 완료 표시·토스트와 가로넘침 없음을 확인했다. 근거는 `development_log.md`다.
- F06-02 구현/검증(2026-10-07): helpycode/routine-schedule 브랜치. 저장 패널에 반복 요일(기본 월\~금, ISO 1\~7)·목표 도착 시각(선택) 입력을 추가하고 일정 PATCH를 구현했다. 백엔드 unittest 125개(일정 저장·PATCH 신규 포함), 프론트 테스트 114개(요일·목표 도착 신규 포함), Vite 빌드, 마이그레이션 0008 up/down roundtrip 통과. 합성 fixture를 실제 브라우저(PC1440×1000·모바일390×844)에서 열어 요일 토글·요일 0개 저장 차단·목표 도착 입력·저장 전달값(weekdays·target_arrival_local_time)·가로넘침 0·콘솔 오류 0과 기존 톤 유지를 확인했다. 근거는 `development_log.md`다.
- `POST /api/v1/routines`(인증+CSRF, Idempotency-Key 선택 1\~128 ASCII): 입력 `{name, origin_place_id, destination_place_id, search_id, candidate_id, weekdays, target_arrival_local_time?}`. name은 1\~30자(앞뒤 공백 제거), origin과 destination은 서로 다른 본인 저장 장소다. search_id는 본인 검색이고 status=succeeded이며 만료 전이고, candidate_id는 그 검색 결과 후보 중 하나여야 한다. weekdays는 ISO 1(월)\~7(일)에서 중복 없이 1\~7개 필수이고, target_arrival_local_time은 HH:mm 형식의 선택 값이며 timezone은 입력받지 않고 Asia/Seoul로 저장한다(요일·목표 도착은 F06-02). 요청 장소의 현재 location_version이 검색 당시와 같아야 하고 다르면 409 VERSION_CONFLICT로 경로 재조회를 요구한다. 검색 없음·만료·미완료·타인 자원·후보·장소 없음은 404 RESOURCE_NOT_FOUND, 장소가 검색 참조와 일치하지 않으면 422 VALIDATION_ERROR다.
- 저장 시 그 후보를 journey.v1로 보강한 스냅샷을 journey_plans(user_id+search_id+candidate_id 고유)에 남긴다. 위치 좌표·참고 시각은 저장하지 않는다. 같은 후보를 다시 저장하면 스냅샷을 재사용하고 루틴만 새로 만든다. 루틴 행은 weekdays smallint\[\], target_arrival_local_time, timezone(Asia/Seoul 고정 CHECK) 컬럼을 함께 저장한다(마이그레이션 0008_routine_schedule).
- 성공 201 data: `{routine_id, name, origin_place:{place_id,label,name,address}|null, destination_place:동일 형태|null, route:{journey_plan_id,type,total_seconds,transfer_count}, weekdays, target_arrival_local_time, timezone, status, version, created_at, updated_at}`. status는 active\|needs_attention, version은 1부터다. weekdays는 저장된 ISO 요일 배열, target_arrival_local_time은 저장된 목표 도착(없으면 null), timezone은 항상 Asia/Seoul이다. 좌표·참고 시각은 응답 어디에도 없다.
- `GET /api/v1/routines/{routine_id}`(인증): 본인 루틴만 200으로 같은 형태를 돌려준다. 없거나 타인이면 404다.
- `PATCH /api/v1/routines/{routine_id}`(인증+CSRF, F06-02 일정 부분): 입력 `{expected_version, weekdays?, target_arrival_local_time?}`이고 알 수 없는 필드는 422다. expected_version이 현재 version과 다르면 409 VERSION_CONFLICT다. weekdays를 보내면 배열 전체를 바꾸고, target_arrival_local_time을 보내지 않으면 기존 값을 유지하며 명시적 null이면 삭제한다. weekdays가 비거나 범위를 벗어나면, target이 HH:mm이 아니면 422 VALIDATION_ERROR다. 성공 200은 상세와 같은 형태이며 version+1과 updated_at 갱신을 함께 돌려준다. F06-03 이름·경로 변경 확장 계약은5.3.1을 따른다.
- 멱등: 같은 키+같은 본문은 최초 201 응답을 재현하고, 같은 키+다른 본문은 409 IDEMPOTENCY_CONFLICT다. 저장에 성공한 루틴이 삭제되면 24시간 동안 같은 키 재시도는 404로 막는다(장소 저장과 동일한 삭제 표시).
- 장소 삭제 연동: DELETE /places/\{place_id\}는 그 장소를 출발이나 도착으로 참조하는 루틴의 해당 참조를 NULL로 해제하고 status=needs_attention, version+1로 바꾼다. 이전 경로 스냅샷은 유지되며 복구는 F06-04 안내에 따른다. 응답 스키마 변화는 없다.
### 5.3.1 루틴 목록·선택·수정·삭제(F06-03)
- 구현·검증 <mention-date start="2026-10-08"/>: codex/routine-management(최신 main2248346에서 생성, 미병합 F06-02 선행 커밋 포함). 백엔드129개(루틴12개 포함), 프론트121개·Vite 빌드 통과. 실제 PostgreSQL/HTTP POST201·GET목록200·PATCH200·DELETE204, PC1440×1000/모바일390×844 목록·선택·이름/요일/목표 시각 수정·새로고침 유지·삭제 확인/취소 확인. 실제 카카오15후보 중 기존 루틴 경로 PATCH 교체와 새 후보 POST 저장·최신 목록 반영 성공. 검증용 루틴만 삭제204 및 빈 목록 확인, 기존 사용자 데이터 보존. 루틴 추가/저장 후 목록 갱신·페이지 조회·인증 전환·버전 충돌·응답 검증·저장 키 재시도는 프론트 회귀 검증. 실기기GPS·실시간 차량/출발 안내·이동 이력은 미검증/미구현이며 이번 완료에 포함하지 않는다. 근거는 `development_log.md`와 `routine_api.md`.
- 계약 확정 <mention-date start="2026-10-08"/>: 구현·검증 완료. 저장된 루틴을 홈·내 루틴에서 조회하며 가상 루틴 2개와 메모리 전용 추가/수정을 제거한다. 추가는 경로 비교의 후보 저장으로 연결하고, 저장 완료 후 목록을 재조회한다.
- GET /api/v1/routines(인증): limit 기본20, 정수1\~100. cursor는 마지막 항목 routine_id(UUID), 본인 루틴이 아니거나 삭제됐으면404 RESOURCE_NOT_FOUND, 잘못된 형식/범위는422 VALIDATION_ERROR. user_id 필터·created_at 내림차순 및 동률 id 내림차순으로 limit개를 반환하고 다음 페이지가 있으면 마지막 ID를 next_cursor로 돌려준다. 200 data는 items(5.3 상세와 같은 객체 배열), next_cursor(문자열 또는 null). needs_attention 및 장소 null도 숨기지 않는다. Cache-Control: no-store.
- PATCH는 expected_version 필수 양의 정수, name(공백 제거1\~30자), weekdays, target_arrival_local_time을 선택적으로 받는다. 미전송은 유지, target 명시적 null은 삭제, name/요일의 null은422. 경로 변경은 origin_place_id·destination_place_id·search_id·candidate_id를 모두 함께 보내며 null/일부만 전송은422다. POST와 동일한 본인 저장 장소·서로 다른 장소·본인 성공 검색·5분 만료·후보·location_version 검사를 적용한다. 검색 당시 출발·도착 장소 순서까지 같아야 하며 뒤집힌 방향은422다. 새 journey_plans 스냅샷을 연결하고 status=active로 복구, 일반 이름/일정 변경은 기존 상태와 경로를 보존한다. version 불일치409, 타인/없는 루틴404, 오류 시 부분 변경 없음. 200은 기존 상세 형태로 version+1·updated_at을 반환한다.
- DELETE /api/v1/routines/routine_id(인증+CSRF): 본인 루틴만 동기 삭제204(본문 없음·no-store), 없는/타인/반복 삭제404. 생성 멱등 키는 routine_id=null 표시로24시간 재생성을 차단한다. 다른 루틴이 공유하는 경로 스냅샷은 유지하고 참조 없는 스냅샷은 삭제한다. 실제 이동 기록은 아직 미구현이며 향후 당시 스냅샷 보존 계약은 유지한다.
- 홈의 루틴 선택은 현재 화면 세션에서 관리하며 새로고침/재로그인 시 본인 목록 첫 항목을 기본 선택한다. 출발 안내는 F07 후속이라 저장 경로의 공급자 예상 시간만 표시하고 가상 차량 도착/권장 출발 숫자를 표시하지 않는다. 삭제한 장소는 확인 필요와 경로 다시 선택 행동으로 표시한다.
- 인증/목록 로딩·빈 상태·실패/재시도·페이지 추가 조회·삭제 확인/취소·버전 충돌 재조회·세션 만료를 제공한다. 로그인/로그아웃 시 이전 목록과 선택을 폐기하고 해당 세션으로 다시 조회한다. 일반 로그에 루틴 이름·장소·후보 원문·좌표를 넣지 않는다.
- 기존 POST/상세/일정 PATCH 응답을 유지하는 추가 계약이다. 기존 일정 PATCH 클라이언트는 그대로 동작한다. 기존 DB0008 스키마를 재사용한다.
### 5.3.2 루틴 등록 중 장소 저장·선택(F06-03a)
- 구현·검증 <mention-date start="2026-10-08"/>: codex/routine-inline-places. 프론트16파일134개(인라인 통합6개 포함)·Vite 빌드 통과. 장소0개 검증 계정으로 실제 브라우저에서 루틴 추가→출발지 선택→빈 저장 목록에서 새 장소 검색/명시 저장201→origin-validations200 자동 선택→도착지 새 장소201/검증200→카카오15후보 조회→루틴POST201→홈 목록 확인까지 설정 화면 이동 없이 완료했다. PostgreSQL에서 장소2개/루틴1개 확인. PC1440×1000·모바일390×844 폼/선택·반대쪽 유지·가로 넘침0·콘솔error0 확인. 생성 실패 동일 키 재시도, 저장 후 검증 실패 재선택(추가 생성 없음), 생성 중 취소/방식 전환 차단, 취소 미저장, 세션 만료는 통합 테스트로 검증했다. 백엔드 코드/DDL은 변경하지 않았으며 실기기GPS·새 장소 생성 모드의 지도 핀 시각 검증은 이번 범위에서 재실행하지 않았다. 검증 데이터는 전용 계정만 정리하고 기존 사용자 데이터를 보존한다. 근거는 `development_log.md`.
- 사용자 요구 <mention-date start="2026-10-08"/>: 처음 사용하는 사람이 내 설정으로 이동하지 않고 루틴의 출발·도착 장소 선택 화면에서 새 장소를 검색·저장·선택할 수 있게 한다. 구현·검증 완료.
- 출발지/도착지 선택기에 장소 저장 행동을 추가한다. 주소/장소명 검색 → 후보 직접 선택 → 이름(기본 출발지 또는 도착지)·선택적 출입구/지도 핀 확인 → 사용자의 저장 확정 순서다. 기존 PlacesCard 생성 폼과 POST /place-searches·POST /places를 재사용한다. 검색만 하거나 취소하면 장소를 생성하지 않는다.
- 장소201 저장 후 응답의 본인 place_id/location_version으로 기존 POST /origin-validations를 호출한다. 성공하면 해당 출발 또는 도착 선택에 즉시 반영하고 반대쪽 선택은 유지한다. 검증 실패 시 장소는 저장돼 있으며 저장 장소 목록에서 다시 선택하도록 오류/재시도를 제공한다. 루틴은 별도 후보 선택·저장 확인 전에는 생성하지 않는다.
- 저장 장소가 없는 빈 목록에서도 새 장소 저장 행동을 제공한다. 지도/현재 위치 조회 후 루틴 저장 조건 안내에서도 출발/도착 장소 저장 폼을 같은 화면에서 연다. 장소 선택 변경 시 기존 검색 후보는 폐기하고 새 저장 장소 기준으로 경로를 재조회한다. 좌표를 근처 장소로 자동 연결하거나 GPS를 자동 저장하지 않는다.
- 생성 폼에서 처리 중 중복 저장/방식 전환/취소를 차단한다. 실패·검색 무결과·10분 만료·로그인 필요·취소를 기존 장소 저장 규칙대로 처리한다. 명시 저장201 이후 검증만 재시도하며 장소를 다시 생성하지 않는다.
- API 경로·필드·인증·소유권·CSRF·멱등24시간·장소/검색 보관·시간/계산 정책·DB 스키마는 유지한다. 화면 흐름 확장이며 기존 설정 장소 관리와 루틴 클라이언트 호환성 영향 없음.
### 5.3.3 루틴 복구 안내(F06-04)
- 구현·검증 <mention-date start="2026-10-08"/>: codex/routine-recovery. 실제 PostgreSQL 격리 스키마/ASGI 루틴13개 포함 백엔드130개, 프론트142개·빌드1902모듈 통과. 출입구 변경→공유 루틴 확인 필요/버전 증가·이름/동일값 유지·이전 후보409/부분 변경 없음·새 후보 PATCH200 active 복구/일정 보존 확인. 합성 UI PC1440×1000/모바일390×844 안내·진입/취소·이전 예상 시간 비노출·가로 넘침 없음·콘솔error0 확인. 카카오 실호출/실제 브라우저 DB 복구·운행 변경 자동 감지는 이번 검증에 포함하지 않는다. 로컬 서버 재시작/health200 확인. 근거 `development_log.md`.
- 계약 확정 <mention-date start="2026-10-08"/>: 장소 위치·출처·출입구 설명이 실제 변경되어 location_version이 증가하는 PATCH /places는 같은 트랜잭션에서 해당 장소를 참조하는 본인 루틴을 needs_attention으로 바꾸고 version+1·updated_at을 갱신한다. 이름만 수정하거나 실제 변화가 없으면 루틴 상태/버전은 유지한다. 삭제 연동은 기존 NULL 참조·needs_attention 정책을 유지한다. 쓰기는 기존 회원별 routine-write 트랜잭션 잠금을 공유해 경로 교체와 장소 변경/삭제 순서를 직렬화한다. 이전 스냅샷/요일/목표 시각은 유지하며 추가 DDL/응답 필드 없음.
- 홈/내 루틴에서 삭제된 출발·도착 지점을 구분하고, 참조가 남은 needs_attention은 장소나 경로 정보 확인 필요로 안내한다. 이전 예상 시간은 현재 경로처럼 표시하지 않는다. 경로 복구 행동은 저장 장소 선택 → 현재 장소로 경로 재조회 → 후보 확인 → 기존 루틴 PATCH 변경 저장 순서다. 이름/요일/목표 시각을 기본값으로 유지하며 장소 선택은 저장 장소 모드로 시작하고 인라인 새 장소 저장도 제공한다. 진입/취소/검색만으로 복구 완료·새 루틴 생성 없음.
- 복구/경로 교체 PATCH 성공200 뒤 본인 routine_id·active·version=expected_version+1을 검증하고 목록을 새로 불러온다. 409/404는 최신 루틴 다시 확인 행동을 제공해 목록으로 돌아가 재조회하며 자동 덮어쓰기/자동 PATCH 재전송 없음. 인증 만료·만료 후보·무결과/공급자 실패는 기존 안전한 복구 흐름을 유지한다.
- 범위: 기존 needs_attention/삭제 참조와 이번 이후 장소 변경을 처리한다. 과거 active 스냅샷의 위치 일치 여부는 근거 없이 추정하지 않는다. 실제 노선 운행 변경의 자동 감지·실시간/AI 안내는 후속이다. API 경로/입출력/인증/보관/계산·기존 클라이언트 호환성 유지, 장소 변경 후 상태 전이와 화면 흐름 확장. 구현/검증 완료.
### 5.5 도보 근거 수집(F05-01)
- 계약 확정 <mention-date start="2026-10-08"/>: GET /api/v1/journey-searches/\{search_id\}/candidates/\{candidate_id\}/walking-evidence. 쿠키 인증·본인 성공 검색/후보만200, CSRF 불필요·no-store. 입력 UUID 오류/없음/타인/미완료/검색300초 만료는404 RESOURCE_NOT_FOUND(기존 자원 ID 규칙). 참조 장소 없음404·location_version 변경409 VERSION_CONFLICT, 깨진 후보502 PROVIDER_RESPONSE_INVALID. 읽기는 기존 검색 결과만 사용하며 새 지도/AI 호출·검색/근거 DB 쓰기·검색 보관 연장 없음. 기존 쿠키 인증의 세션 활동 기한 갱신은 유지한다.
- 200 data: model_version=walking.evidence.v1, search_id,candidate_id,expires_at(기존 검색 기한),status=needs_data,ready_for_estimation=false,reusable=false,segments 배열. 접근1개·각 환승 연결1개·마지막1개를 순서대로 제공한다. 각 segment는 segment_id(검색/후보/역할/연결 기반 안정적 UUID),role(access/transfer/egress),connection_id(환승 외null),walking_leg_ids\[\],from_ref/to_ref,provider_duration_seconds/provider_distance_meters(미제공null, 명시0은0),source(provider_estimate 또는 missing),scope(provider_walking_segment 또는 unknown),physical_endpoints=unconfirmed,missing_segments\[\]를 포함한다. from_ref/to_ref는 \{type:search_origin/search_destination\} 또는 \{type:transit_stop,leg_id,stop_name\}. 기존 저장소가 장소 참조의 출발/도착 역할을 보관하지 않으므로 양 끝은 검색 지점 참조이며 place_refs의 소유권/location_version은 별도 검증한다. 정밀 좌표·출입구 설명은 포함하지 않는다.
- 누락 segment 예시(접근): role=access,connection_id=null,walking_leg_ids=\[\],from_ref=\{type:search_origin\},to_ref=\{type:transit_stop,leg_id:원본교통UUID,stop_name:합성역\},provider_duration_seconds=null,provider_distance_meters=null,source=missing,scope=unknown,physical_endpoints=unconfirmed,missing_segments=\[PHYSICAL_ENDPOINTS_UNCONFIRMED,PROVIDER_WALK_MISSING,ENTRANCE_PLATFORM_UNCONFIRMED\]. 마지막 코드는 지하철에 인접할 때만 포함한다. 전체 필드 설명은 `walking_api.md`와 OpenAPI EvidenceEnvelope를 따른다.
- 기존 journey.v1 WALKING 역할·ID·거리·시간과 connections 참조에서 근거를 수집한다. 연속 도보는 역할별 합산하되 원본 leg ID들을 유지한다. 환승 도보가 없으면0으로 대체하지 않는다. 미제공은 PROVIDER_WALK_MISSING, 제공0초는 WALK_DURATION_ZERO, 모든 구간은 PHYSICAL_ENDPOINTS_UNCONFIRMED, 지하철 접점은 ENTRANCE_PLATFORM_UNCONFIRMED를 표시한다. 실제 보행 가능/정류장 방향·입구/승강장 범위가 미검증이므로 ready_for_estimation=false이며 AI 호출·기준 시간 저장·개인화 학습/재사용은 F05-02 이후다. 총 경로시간의 차이를 도보/대기/여유로 배분하지 않는다.
- F04-04/GPS 자동 판정 보류를 유지한다. 이 API는 제공 근거와 누락을 구분하는 단계이며 빠진 도보를 새로 산정하거나 운행/내부 동선을 인증하지 않는다. 기존 API/응답/계산/보관/DDL·클라이언트 호환성 유지, 새 읽기 API 추가. 일반 로그에는 이름·좌표·근거 원문을 출력하지 않는다. 구현/검증 완료. 실제 PostgreSQL 임시 스키마/ASGI·합성 공급자로 신규7개/전체137개 통과, 서버 재시작·health200·OpenAPI 등록 확인. 프론트 변경 없음, 물리 범위 실검증·AI 호출·기준값 저장은 후속.
### 5.5.1 프롬프트 블록·버전 로딩(F05-02)
- 구현/검증 완료 <mention-date start="2026-10-12"/>: 서버 내부 load_prompt는 `ai_prompts.md`의 common.v1 SYSTEM과 walking_estimate.v1 또는 journey_explanation.v2 DEVELOPER를 분리 로딩한다. 작업 버전과 SYSTEM 버전을 함께 보존하며 문서와 리소스의 문구·버전 일치를 검증한다. 기존 문구와 프롬프트 버전 유지.
- 허용된 작업만 선택하며 기대 버전 불일치·파일 누락/손상/빈 내용·잘못된 역할은 내부 PromptLoadError로 중단한다. 오류에는 본문/경로를 포함하지 않는다. 불변 블록과 새 메시지 목록을 반환하고 실행 폴더에 의존하지 않는다. 입력 JSON은 후속 단계의 별도 데이터 메시지로 전달한다. 자연어 일정은 보행 SYSTEM과 결합하지 않으며 F17에서 별도로 연결한다.
- 신규 로더 테스트8개·전체 백엔드149개 통과(실제 PostgreSQL 임시 스키마/ASGI 및 합성 공급자 포함). 운영 모델 품질 평가·사용자 서비스 연결은 후속이며 F05-03 내부 구조화 출력 검증/합성 최소 호출은5.5.2절, F05-04 내부 산정/품질 이력 저장은5.5.3절을 따른다. walking.evidence.v1의 needs_data 및 ready_for_estimation/reusable=false를 유지한다. 기존 HTTP API·입출력·인증/권한·오류·DB/보관·계산 계약과 클라이언트 호환성 영향 없음. UI 변경 없음.
### 5.5.2 AI 최소 입력·구조화 결과 검증(F05-03)
- 내부 구현·합성/실서버 최소 검증 완료 <mention-date start="2026-10-12"/>: 인증·소유권·유효기간과 물리 범위를 확인한 서버 내부 호출용 산정 모듈을 구현했다. 새 HTTP API·UI·저장소 없음. 현재 walking.evidence.v1은 전 구간 물리 범위 미확인으로 AI에 전송하지 않고 needs_data를 유지한다. 실제 근거 확보·사용자 서비스 연결은 후속이며 내부 산정 저장/품질 이력은5.5.3절에서 구현했다.
- 내부 입력은 기존 `ai_prompts.md`의 request_id, policy_version=walk-policy.v1, profile 및 candidates만 허용한다. profile은 version·validated_duration_factor(null 또는0.5\~2.0)·valid_factor_range=\[0.5,2.0\]·fallback_speed_mps(null 또는 양의 유한수). 후보는 ID/양끝 참조·direction·scope/required_scope·is_walkable_route·거리/공급자 시간(null 또는 양의 유한수)·이미 개인화 여부·근거 ID/누락 코드만 갖는다. 후보1\~20개·중복 ID/근거 금지·추가 필드 금지, 이름/주소/좌표/메모/공급자 원문 비전송. ID·방향·범위·누락은 제한된 식별자 문자열로 검증한다.
- 실제 보행 확인·명시 방향·일치하는 범위·근거 ID·누락 없음·양수 기준 시간(공급자 우선, 없으면 검증 거리/속도)이 모두 충족한 후보만 AI에 보낸다. 부족한 후보는 서버가 null 시간/계수·method=none·needs_data와 누락 사유로 반환하며 반복 호출하지 않는다. 계수 기본1.0, 공급자 개인화 포함이면1.0, 최종 ceil(기준×계수)·여유/차량대기 추가 금지 유지.
- F05-02 SYSTEM/DEVELOPER와 입력 JSON USER 메시지를 분리하여 설정된 HTTPS Responses 서버의 gpt-5.6-luna에 전달한다. store=false·strict JSON Schema·최대512출력토큰·35초·256KiB응답 제한, 리다이렉트/도구 호출/암묵적 JSON 모드 대체 금지. 설정은 기존 환경 우선 규칙. 연결/HTTP 실패503 PROVIDER_UNAVAILABLE, timeout504 PROVIDER_TIMEOUT, 거절/미완료/모델 불일치/손상502 AI_OUTPUT_INVALID. 키/URL/본문/오류 원문은 일반 로그에 남기지 않는다.
- 출력은 request_id·walking_estimate.v1·후보마다 유일 결과·양끝/방향/범위 보존·입력에 존재하는 근거 ID·숫자 자료형/유한성/상태와 null 규칙을 검증한다. ok는 모든 근거 보존·누락 없음·공급자 우선/거리÷속도·계수와 ceil을 서버가 재검산하며 불일치 전부 거부한다. needs_data/unsupported는 시간/계수null·method=none이며 unsupported는 확정된 다른 경로 지원을 의미하지 않는다. 형식 오류만 동일 입력으로 최대1회 재시도, 의미/수식/근거 오류·거절/연결 실패는 재시도 없음. 오류 결과는 저장하지 않는다.
- 검증 완료: 신규19개·최종 전체 백엔드168개 통과(58.394초, PostgreSQL 임시 스키마/ASGI·합성 공급자 포함). strict 요청/실패·ID/범위/수식·형식 재시도·현재 근거 호출0·누락/0초 보존·안전한 HTTP 오류 진단을 확인했다. 최초 구조화 요청 실패 후 사용자 승인된 추가3회에서 공급자HTTP400 및 INVALID/MAX_OUTPUT_TOKENS 고정 태그를 확인했다. 출력 한도를4096에서512로 낮춘 마지막 실제 `mlapi.run` 합성1후보 요청은 모델 보고값 일치·walking_estimate.v1·status=ok·estimated_seconds=360·서버 검산 성공,2.51초였다. 공급자 HTTP 상태·허용 오류 코드·고정 태그만 진단 출력하며 원문/키/URL·개인 위치 비노출, 공개 오류 계약 유지. `backend/check_ai_walking.py`는 합성300초×1.2=360초 요청을 재시도 없이 최대1회 실행한다. F05-03 내부 모듈 구현/최소 연결 검증 완료, 다수 후보 실응답·실제 보행/운영 품질·서비스 연결은 후속이며 내부 산정 저장은5.5.3절에서 구현했다.512토큰 한도에서 응답이 미완료면 검증 실패로 거부한다.
### 5.5.3 산정값·근거 이력 저장(F05-04)
- 내부 저장·본인 조회 구현/검증 완료 <mention-date start="2026-10-12"/>: 검증된 서버 내부 산정 결과를 walking_paths·walking_estimates·walking_estimate_revisions·ai_executions에 저장한다. 새 쓰기 HTTP API 없음. 인증된 사용자·유효한 프로필 버전·본인 장소/location_version·검증된 물리 근거의 유효기간은 저장 트랜잭션에서 확인한다. F05-03 입력/결과를 다시 검산하며 미확인/needs_data/unsupported는 유효 산정 revision을 만들지 않는다. 현재 실제 walking.evidence는 미확인 상태이므로 산정값 저장이 차단된다.
- 내부 저장 입력은 F05-03 최소 입력/검증 결과와 서버 확인 Context(place_refs, verified_at, valid_until), 실행 메타데이터(model_version, latency_ms?, usage?)다. Context는 공개 클라이언트가 만들 수 없고 호출 서비스가 먼저 물리 경로·방향·범위/소유권을 확인해야 한다. 정밀 위치/장소명/메모/원문/내부 사고 과정은 저장하지 않는다. 모델/지연/사용량은 호출자가 실제로 확인한 값만 기록하며 미제공 지연/사용량은 null이다. 프로필 계수는 검증된 내부 스냅샷이며 실제 개인화 학습 연결은 F09 후속이다.
- 동일 사용자/request_id의 동일 입력·결과·Context·메타데이터는 같은 실행/산정ID를 반환한다. 다른 내용이면409 IDEMPOTENCY_CONFLICT. 실행90일 보관 동안 같은 실행 식별자를 재사용하지 않는다. 공개24시간 생성 멱등 정책을 바꾸지 않는 내부 실행 식별 규칙이다. 저장은 회원별 기존 routine-write 잠금→회원/프로필→정렬된 장소 참조 순서로 원자 처리하며 실패 시 일부 행을 남기지 않는다. 과거 기준·계수·최종값/버전·근거는 불변 스냅샷으로 보존한다. estimate_and_store는 사용자/request_id별 DB 세션 advisory 잠금으로 동시 실행을 차단한다. 이미 실행 중이면 내부409 EXECUTION_IN_PROGRESS, 완료된 동일 실행은 모델 재호출 없이 반환한다. 이 잠금은 물리 모델 호출 동안 장소 수정 잠금을 잡지 않고 저장 직전에 버전을 재검사한다.
- 유효한 ok 후보만 path/estimate/revision을 만들고 기준 시간·계수·최종 초·범위/방향·최소 근거ID·장소 참조/위치 버전·profile_version·common/walking 프롬프트/정책/모델 버전을 연결한다. 산정 유효기간은 계산시각+30일과 물리 근거 valid_until 중 이른 시각, 품질 이력 보관은 생성부터90일. needs_data/unsupported는 안전한 구조화 상태만 실행 이력에 기록한다. 실패는 허용된 실패 코드·최소 입력만 기록하고 산정값/원문을 저장하지 않는다. 회원 삭제는 CASCADE, 장소 삭제/위치 변경은 조회 시 차단하며 과거 품질 스냅샷은90일 보존한다. 기간청소 함수를 제공하고 자동 매일 스케줄은 배포 후속이다.
- GET /api/v1/walking-estimates/\{estimate_id\}: 쿠키 인증·본인만200·CSRF 불필요·no-store. 기존5.6 data 필드 estimate_id,revision_id,base_seconds,applied_duration_factor,estimated_seconds,scope,source=ai_estimate\|profile_recalculation,reused=false,calculated_at,expires_at,prompt_version,policy_version을 반환한다. 조건별 재사용은5.5.4의 내부 실행에서 수행하며 단순 GET 조회는 재사용으로 표시하지 않는다. 원문/품질 내부 필드는 비노출. 잘못된UUID/없음/타인/30일 또는 근거 만료·삭제된 장소는404 RESOURCE_NOT_FOUND, 장소 location_version/프로필 버전 변경은409 VERSION_CONFLICT. 읽기는 모델 호출·산정 쓰기·만료 연장 없음, 기존 세션 활동 갱신만 유지한다.
- 신규 Alembic0009_walking_history로4개테이블·복합 소유권FK/조회/보관 인덱스를 추가한다. 내부 추가 저장/읽기만으로 기존 루틴/검색/프론트 클라이언트 호환성 영향 없음. F05-05 내부 캐시 재사용은5.5.4에서 구현했다. F05-06 내부 재계산/재산정 분기는5.5.5에서 구현했다. F07 출발 안내와 실제 보행 근거 확보/사용자 생성 연결은 후속이다.
- 검증 완료: 신규16개·전체 백엔드184개 통과(82.124초, PostgreSQL 격리 스키마/ASGI·합성 AI). 정상/실패/needs_data·30일/근거기한/90일·소유권·장소/프로필 버전·불변/중복/동시 실행·호출 도중 위치 변경·롤백·복합FK를 확인했다. Alembic0009 실제 개발DB 적용/4테이블 확인, 기존 회원/장소/루틴 행 수 유지. 격리 스키마 마이그레이션 적용/복구/재적용 통과. 백엔드 재시작·health200·OpenAPI GET 등록·실서버 비인증401 AUTH_REQUIRED·프론트200 확인. 기존 시간 경계에 의존하던 장소 만료/호출제한 테스트의 시간만 안정화했으며 해당 API 구현/정책은 변경하지 않았다. 외부 AI/카카오 추가 호출 및 실제 사용자 산정값 생성은 수행하지 않았다.
### 5.5.4 저장값 조건별 재사용(F05-05)
- 내부 구현/검증 완료 <mention-date start="2026-10-12"/>. 공개 쓰기 API/화면 추가 없음. 기존 estimate_and_store에 선택적 cache_sources를 전달한다. 서버가 검증한 candidate_id, provider, provider_path_ref, path_version, origin_entrance_ref, destination_entrance_ref, condition_version을 사용한다. 출입구가 적용되지 않는 경우만 not_applicable로 명시한다. unknown 등 미확인 식별자와 클라이언트 추정값은 허용하지 않는다. cache_sources 미제공/기존 이력은 재사용하지 않는다.
- 키는 사용자별 저장 장소/location_version·양끝 물리 참조·방향·범위/필요 범위·공급자 경로/버전·출입구·조건 버전·기준 거리/시간/기개인화 여부·필요한 fallback_speed·정책/공통 프롬프트/작업 프롬프트/모델 버전으로 구분한다. 일시적 candidate_id/evidence_id/request_id는 키에서 제외한다. 현재 물리 근거가 needs_data/unsupported이거나 유효기간이 지났으면 저장값을 쓰지 않는다.
- 같은 사용자·물리 조건·프로필 스냅샷의 유효한 검증 revision만 재사용한다. 원본 수치를 현재 입력으로 다시 검산하고 현재 candidate/evidence ID로 연결한다. 계수/프로필 버전만 바뀐 경우5.5.5의 서버 재계산으로 연결하며 AI를 호출하지 않는다. 같은 물리 키에서 프로필의 다른 필드도 바뀌면409 PROFILE_RECALCULATION_REQUIRED로 차단한다.
- 전체/부분 적중 모두 지원한다. 적중 후보는 AI 호출에서 제외하고 누락 후보만 F05-03에 전달한다. 내부 반환 estimates에 candidate_id/estimate_id/revision_id/reused/expires_at을 제공한다. 적중은 원래 estimate/revision ID를 유지하고 effective expires_at=min(원본 만료, 현재 근거 기한)이다. 적중으로 원본 만료·계산 시각·품질 스냅샷을 연장하거나 새 numeric revision을 만들지 않는다.
- 멱등 재실행은 전체 입력/Context/cache_sources와 저장된 원본 연결을 확인한다. 적중 내역은 ai_executions의 reused_estimates에 최소 연결만 기록한다. 전부 적중이면 model_version/latency_ms/usage=null이며 새 모델 실행으로 집계하지 않는다. 부분 적중은 실제 누락 후보 호출 메타데이터만 기록한다. 원본 연결 삭제/만료 후 재실행은404로 차단한다. 사용자/request_id 및 정렬된 물리 캐시 키의 세션 잠금으로 다른 실행ID의 같은 경로 동시 AI 호출도409 EXECUTION_IN_PROGRESS로 차단한다. 모델 호출 전후 본인/프로필/장소/기한을 재검사한다.
- Alembic0010_walking_cache는 walking_paths에 nullable cache_key/cache_identity와 인덱스, ai_executions에 reused_estimates 기본 빈 목록을 추가한다. 이전 이력은 확인된 물리 식별자가 없어 역추정/백필하지 않는다. 기존 GET은 단순 조회이므로 reused=false 계약을 유지한다. 현재 실제 도보 근거는 미확인이라 운영 재사용/출발 안내 연결은 아직 불가하다. 기존 클라이언트 응답 호환성 영향 없음.
- 기준 실수는 F05-03과 같은 rel_tol=1e-12/abs_tol=1e-9로 검산하며 계수/최종 정수 초는 정확히 일치해야 한다. DB NUMERIC에는 검증값의 Decimal 문자열을 전달해 계수 자릿수를 보존한다.
- 검증 완료: 신규18개·전체 백엔드202개 통과(78.408초, 실제 PostgreSQL 격리 스키마/ASGI·합성 AI). 전체/부분 적중의 호출 생략·현재 ID 연결·원본 기한 유지·물리 조건/버전/소유권·프로필 변경 차단·거리/속도·긴 계수·만료/삭제 재실행·호출 중 원본 만료 롤백·다른 실행ID의 같은 경로 동시 호출·실패 잠금 해제를 확인했다.0009 legacy 행 보존/0010 적용/복구/재적용과 전체 마이그레이션 왕복도 통과.0010 개발DB 적용 후 회원20/장소35/루틴12 및 실제 산정0 유지. 서버 재시작·health200·프론트200·OpenAPI 유지·비인증 GET401 확인. 추가 외부 AI/카카오 호출·실제 사용자 산정 생성·UI 변경 없음.
### 5.5.5 계수 변경 재계산과 경로 재산정(F05-06)
- 내부 구현/검증 완료 <mention-date start="2026-10-13"/>. estimate_and_store에서 같은 물리 키의 유효 근거가 있고 `profile.version`/validated_duration_factor만 바뀌면 지도·AI 호출 없이 저장 base_seconds에 새 계수(미제공 기본1.0, 허용0.5\~2.0)를 적용한다. 최종 초는 Decimal 기준 ceil(base_seconds × factor)이다. 이미 개인화가 포함된 공급자 기준은 factor=1로 이중 보정하지 않는다. 이전 개인화 최종값을 다시 곱하지 않는다.
- 동일 estimate에 증가하는 revision_no·새 프로필 버전·source=profile_recalculation·이전 parent_revision_id를 원자 저장한다. 이전 revision은 불변이며 새 calculated_at과 현재 candidate_id를 기록한다. 만료는 원본 revision/물리 경로/현재 근거 중 이른 기한, 품질 보관도 원본 기한을 넘기지 않는다. 모델 실행 없는 실행 이력은 model_version/latency_ms/usage=null이다. 부분 재사용/재계산/새 산정이 섞이면 AI에는 새 후보만 보낸다.
- 재계산 결과는 저장된 십진 기준을 사용해 검산한다. 거리/속도 기준의 소수 표현 때문에 새 계수 곱셈의 올림 경계가 달라질 수 있으며, 이전 최종 정수 초나 반올림한 분 단위에서 계산하지 않는다. 다음 조회/동일 실행 재요청은 같은 revision을 반환하고 중복 재계산하지 않는다.
- 본인/현재 프로필 버전/장소 location_version/물리 키/근거 기한·원본 수치/연결을 호출 전후 검사한다. 만료/경로·입구·방향·조건·필요 속도 변경은 캐시를 무효화하며 호출 서비스가 현재 검증 근거를 제공하면 기존 F05-03 새 산정으로 처리한다. 오래된 Context/삭제·변경 장소는404/409, 미확인 물리 근거는 needs_data로 유지한다. 프로필의 다른 필드가 달라지면서 같은 물리 키인 경우409 PROFILE_RECALCULATION_REQUIRED로 차단한다. F09 계수 학습과 실서비스 물리 근거 확보/지도 재조회 연결은 후속이다.
- GET 상세는 기존 필드/인증/no-store/reused=false를 유지하고 source에 profile_recalculation을 추가한다. estimate_id는 유지되며 최신 revision_id/계수/최종 초/계산 시각을 반환한다. 내부 estimates도 source를 제공한다. 기존 ai_estimate 값은 유지되지만 클라이언트가 source를 두 값으로 처리해야 한다.
- Alembic0011_walking_recalculation은 revision source 제약을 확장하고 같은 회원/estimate의 부모 revision FK·재계산 candidate_id를 추가한다. 기존 revision은 부모 null을 유지한다. 품질 보존을 위한 원본 경로/최초 AI 버전 연결을 유지하며 부모/회원 삭제는CASCADE. 공개 쓰기 API/프론트 변경 없음.
- 검증 완료: 신규19개·전체 백엔드221개 통과(88.249초, 실제 PostgreSQL 격리 스키마/ASGI·합성 AI).300×1.1=330·연속 계수 변경·기본/경계 계수·이미 개인화된 공급자·거리/속도 십진 올림·현재 ID 연결·재사용/재계산/새 산정 혼합·소유권/부모FK·원본 기한·삭제/만료/변경·롤백/잠금·멱등·잘못된 출력502·GET source를 확인했다. 파생 revision을 만든0011→0010→0011 격리 복구에서도 원본360초 보존을 확인했다.0011 개발DB 적용 후 회원20/장소35/루틴12·실제 산정/이력0 유지. Docker/DB와 서버 기동·health200·프론트200·GET401·OpenAPI source enum 확인. 기존 루틴 목록 테스트에 고정 생성시각/UUID 동률 경계를 제공했으며 루틴 API 구현/정렬 계약 변경 없음. 추가 외부 AI/카카오 호출·UI 변경 없음.
### 5.5.6 도보 실패·근거 부족 화면 안내(F05-07)
- UI 구현/검증 완료 <mention-date start="2026-10-13"/>. 본인 루틴 선택 화면과 유효 검색 후보 상세에 공통 도보 안내를 표시한다. 현재 실제 근거는 needs_data이며 개인 도보 AI를 실행하지 않았음을 명시한다. 저장 루틴은 기존 routine.route 요약으로 일반적인 범위/방향 미확인을 안내하고, 없는 상세 근거를 추측하지 않는다.
- 유효 후보는 기존 missing_segments에서 접근/환승/마지막 도보 누락을 구분한다. 공급자0초 구간은 실제0초로 확정하지 않는다. 지하철/혼합 경로와 ENTRANCE_PLATFORM_UNCONFIRMED는 입구부터 승강장·역 내부/환승 정보가 필요함을 안내한다. 도보가 제공된 버스 경로도 물리 범위/방향 미확인을 유지한다. 누락을0으로 채우거나 출발 시각/개인화 성공/캐시 가능으로 표시하지 않는다.
- 경로 조회 실패는 실패 코드에 대응하는 고정 안내와 기존 재시도 동작을 사용한다. AI_OUTPUT_INVALID/PROMPT_RESOURCE_INVALID는 AI 산정 검증/준비 실패, PROVIDER_UNAVAILABLE/PROVIDER_TIMEOUT은 시간 정보 확인 실패로 표현하며 공급자 실패를 AI 실행 증거로 해석하지 않는다. 원문·코드·키·주소·요청ID를 공통 도보 안내에 출력하지 않는다. 현재 AI 생성 공개 API는 추가하지 않으며 실제AI 실패 연결은 후속 공개 생성 흐름에서 적용한다.
- 검색/선택 만료 또는 장소/루틴 복구 상태는 이전 시간 사용을 차단하고 최신 장소/경로 선택으로 안내한다. 기존 로딩·빈 상태·취소/늦은 응답 무시·로그인/쿼터/재시도·만료 정책을 유지한다. 루틴 선택 카드에서 실시간/출발 안내 준비 상태와 구분해 필요한 도보 근거를 설명한다.
- 기존 info-box/card/초록 버튼·Noto Sans KR·lucide 선형 아이콘과 CSS 변수를 재사용하며 데스크톱/모바일 확인 대상은 홈 루틴 카드·후보 상세·실패/만료이다. 새 HTTP API/입력/응답/인증·계산·DDL·보관·AI/지도 호출 없음. 프론트 사용자 흐름 추가만으로 기존 API 클라이언트 호환성 유지. F07 실제 출발 안내·실제 물리 근거/AI 생성 연결은 후속이다.
- 검증 완료: 신규19개·전체 프론트167개 통과(11.41초), vite 빌드1904모듈 통과. 접근/환승/마지막 누락·역 내부·공급자0초·루틴 요약의 상세 근거 비추정·고정 실패 문구/원문·알 수 없는 속성명 비노출·AI 검증 오류502 화면·중복 alert 방지·후보 상세/만료 연결 및 기존 취소/재시도 회귀를 확인했다. 합성 루틴/경로 API와 위치 선택 fixture를 사용한 실제 Edge 렌더링에서1440×1000/390×844 홈·후보 상세·실패·시계 진행 만료8화면을 확인했고 가로 넘침/페이지 런타임 오류0이었다. 실제 사용자 정보/DB 변경·외부AI/지도 호출 없음. backend health200·프론트200 확인. 실제 휴대전화/실서비스 AI 실패 생성은 미검증이며 해당 생성 API 연결은 후속이다.
### 5.6 도보 결과
`GET /api/v1/walking-estimates/00000000-0000-4000-8000-000000000101`의 data 예시:
```json
{
  "estimate_id": "00000000-0000-4000-8000-000000000101",
  "revision_id": "00000000-0000-4000-8000-000000000102",
  "base_seconds": 300,
  "applied_duration_factor": 1.0,
  "estimated_seconds": 300,
  "scope": "place_entrance_to_stop",
  "source": "ai_estimate",
  "reused": false,
  "calculated_at": "2026-09-29T23:00:00Z",
  "expires_at": "2026-10-29T23:00:00Z",
  "prompt_version": "walking_estimate.v1",
  "policy_version": "walk-policy.v1"
}
```
`source`는 산정 방식이며 ai_estimate 또는 profile_recalculation이다. GET 상세는 읽기만 수행하며 reused=false를 유지한다. 내부 실행의 최종값 적중은 reused=true, 계수 재계산은 source=profile_recalculation·reused=false이며 다음 동일 프로필의 재사용은 같은 revision_id와 reused=true를 반환한다. 예를 들어 위 원본300초에 새 계수1.1을 적용하면 동일 estimate_id·새 revision_id·estimated_seconds=330·source=profile_recalculation이다. 새 calculated_at을 기록하되 원본 expires_at=2026-10-29T23:00:00Z를 늘리지 않는다. 산정/실시간 교통의 유효기간은 별개다.
### 5.7 출발·여유 안내
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
### 5.7.1 첫 버스 예상 출발 계산(F07-02)
- 사용자 결정 <mention-date start="2026-10-13"/>: 실제 검색 후보에 검증된 개인 도보 산정값이 연결되지 않은 상태이므로 사용자는 공급자 접근 도보 시간에 개인 계수를 적용한 추정을 허용했다. 첫BUS 이전의 access 도보 구간 전체가 양수이고 누락이 없을 때 W=ceil(공급자 접근 도보초 합×본인 walking_duration_factor), 기본계수1.0/허용0.5\~2.0, B=본인 first_boarding_buffer_seconds(초·기본300/0\~1800). 공급자 추정을 물리 범위/진행방향/보행 인증으로 승격하거나 AI 산정값이라고 표시하지 않는다. 환승/마지막 도보/차량 대기는 W에 포함하지 않고 여유를 자동 축소하지 않는다.
- GET /api/v1/journey-searches/\{search_id\}/candidates/\{candidate_id\}/first-departure?departure_basis=recommended\|now(기본recommended): 쿠키 인증·본인·no-store·CSRF 불필요, 클라이언트 시간/계수/접근초/정류소ID를 받지 않는다. search/후보/장소버전 검사는 first-arrivals와 동일(잘못된UUID/타인/없음/만료404·장소변경409). 공개 query 잘못된 basis422, 공급자/버킷502/503/504/429 기존형식. 호출 전후 소유권/검색후보 fingerprint/검색 기한·프로필버전/계수/여유를 재검사, 변경409 VERSION_CONFLICT. 계산은 읽기이며 새 경로/AI 호출·도보산정/루틴 쓰기·TTL연장 없음. first-arrivals의 검증 매핑/60초 캐시를 공유한다.
- first.departure.v1 응답: search_id/candidate_id/first_leg_id·status(ready/insufficient_data/not_enough_time/stale/unsupported)·departure_basis·calculated_at/valid_until·recommended_departure_at/selected_departure_at/vehicle_arrival_at(nullable)·arrival_candidate_id(nullable)·approach_seconds/provider_approach_seconds/applied_duration_factor/profile_version/approach_basis=provider_personalized(nullable)·buffer_seconds·slack_seconds(nullable, 현재/선택시각 기준 내림 정수 초)·slack_status(meets_buffer/below_buffer/unreachable/unknown)·timing_basis(none/source_generation/receipt_estimate)·valid_for_guidance·reasons·arrival_evidence(arrival.evidence.v2). 개인화 계수는 Alembic0012로 user_profiles.walking_duration_factor(double precision·NOT NULL·기본1·0.5\~2) 추가, 기존회원 보존/GET /auth/me의 profile에 필드추가. 일반 설정변경 API와 학습은 후속이며 내부변경 시profile.version 증가 규칙을 따른다.
- 유효한 첫 도착 후보 중5.7.7 기준 선택 차량에 s=t_vehicle-W-B. recommended는 s가 미래면선택s, 이미 지났으면 현재시각을 선택해 S=t_vehicle-(선택시각+W)를 다시 계산한다. now는 현재시각선택, 원래s별도유지. S\<0이면not_enough_time/validfalse·음수slack을0으로 바꾸지 않는다.0\<=S\<B면ready/below_buffer이며5분확보로표시하지 않는다. 원천unknown은 명시적receipt_estimate로만 허용. 기본13분뒤차량/접근5분/여유5분은3분뒤예상출발. 이미 지난차량을탑승/놓침기록으로만들지 않으며 접근불가 후보의 다음 차량 선택은5.7.7, 순차환승/목표도착은5.7.2/5.7.6을 따른다. 수동 departed 기반 전환/이동중 잔여는후속이다.
- 유효기한은 도착근거/검색기한과 계산+120초 중 이른값. 접근누락/0초/잘못된계수·도착근거없음/매핑미확인/미지원/만료는출발숫자없음. 후보상세는 도착과출발을한GET으로조회하고60초/탭복귀 재계산·숨김/이탈취소, 수신추정/공급자개인화접근/조회경과·기본여유 표시. 화면기한초과/선택차량예측경과/조회인증·경로변경오류는이전출발숫자제거, 권장시각이지난경우경과표시하고5분보장하지 않는다. routine_id 필수인 POST /guidance-queries의기존설계는유지하고 이번후보계산API와구분하며 루틴 자동재검색/출발 안내 및 전체여정은후속이다.
- F07-02 구현/검증 완료 <mention-date start="2026-10-13"/>: 후보 first-departure GET·본인/프로필/검색 스냅샷 호출 전후 검사·Decimal 접근초 올림·권장/지금 출발/지나간 권장시각 재평가·음수 여유/만료/부족 차단·도착 캐시 공유를 구현했다. 기존 arrival Envelope 이름을 유지하고 별도 DepartureEnvelope 스키마를 사용한다. 신규 백엔드15개4.903초 및 최종 전체329개123.044초, 프론트196개11.25초·빌드427ms 통과. 합성 브라우저1280×800/390×844에서 예상 출발/접근·설정 여유/추정 표기·줄바꿈/가로넘침 없음 확인. 다른 서울 날짜의 출발은 날짜를 붙이고 설정 여유 초는 분으로 임의 반올림하지 않는다. 마이그레이션0011→0012 적용·회원20/장소35/루틴12 보존·계수 범위 정상, 서버health/프론트200·비로그인 새GET401 확인. 이번 실제 교통키/AI 호출0회·실제 경로 출발 숫자/물리 보행/예측 정확도 미검증. F07-02 후보 첫 버스 계산 완료, F07-01c 원천 시간 강화 및 F07-02a 루틴 선택 자동갱신/검증 도보 연결, F07-03 이후 환승·목표도착·다음차량/이동중 계산은 미완료다. 이유/한계/실패 수정/검증은 `development_log.md`에 기록했다.
후보 첫 출발 data 합성 예시(실제 운행 응답 아님):
```json
{"model_version":"first.departure.v1","search_id":"00000000-0000-4000-8000-000000000001","candidate_id":"00000000-0000-4000-8000-000000000002","first_leg_id":"00000000-0000-4000-8000-000000000003","status":"ready","departure_basis":"recommended","calculated_at":"2026-10-13T03:00:00Z","valid_until":"2026-10-13T03:02:00Z","recommended_departure_at":"2026-10-13T03:03:00Z","selected_departure_at":"2026-10-13T03:03:00Z","vehicle_arrival_at":"2026-10-13T03:13:00Z","arrival_candidate_id":"00000000-0000-4000-8000-000000000004","approach_seconds":300,"provider_approach_seconds":300,"applied_duration_factor":1,"profile_version":1,"approach_basis":"provider_personalized","buffer_seconds":300,"slack_seconds":300,"slack_status":"meets_buffer","timing_basis":"receipt_estimate","valid_for_guidance":true,"reasons":["PROVIDER_ACCESS_ESTIMATE","RECEIPT_BASED_ESTIMATE"],"arrival_evidence":{"model_version":"arrival.evidence.v2","search_id":"00000000-0000-4000-8000-000000000001","candidate_id":"00000000-0000-4000-8000-000000000002","first_leg_id":"00000000-0000-4000-8000-000000000003","status":"estimated","source_status":"unknown","timing_basis":"receipt_estimate","received_at":"2026-10-13T03:00:00Z","generated_at":null,"expires_at":"2026-10-13T03:02:00Z","valid_for_guidance":true,"reasons":["GENERATION_TIME_UNCONFIRMED","RECEIPT_BASED_ESTIMATE"],"candidates":[{"candidate_id":"00000000-0000-4000-8000-000000000004","provider_prediction_seconds":780,"predicted_arrival_at":"2026-10-13T03:13:00Z","remaining_seconds":780}]}}
```
### 5.7.2 첫 차량·환승 연결 검사(F07-03)
- GET first-departure에 include_connections:boolean(기본false)을 추가한다. true이면 기존 첫 차량 계산을 유지하고 최대2회 환승을 순서대로 검사한다. 프로필 transfer_buffer_seconds(기본120초/0\~1800)를 읽고 호출 전후 버전·계수·첫/환승여유를 재검사한다. 버스 경로의 환승 도보도 기존 개인화 정책대로 ceil(제공 양수 환승 도보초×개인계수)로 추정하며 물리 범위/정류소 일치 인증으로 표시하지 않는다. 누락/0초·차량 구간시간0·미지원지하철/복수노선·매핑미확인은unknown, 실제 데이터 없는 시간표/대기/다음차량을 만들지 않는다.
- 기존 first.departure.v1에 connection_status(not_checked/estimated_feasible/unavailable/unknown/stale), transfers, estimated_final_alighting_at(nullable)을 추가한다. transfer 항목은 connection_id/from_leg_id/to_leg_id·estimated_alighting_at/minimum_boarding_at/next_boarding_at(nullable)·transfer_walk_seconds(nullable)/transfer_buffer_seconds·feasibility(estimated_feasible/unavailable/unknown)·time_source(none/receipt_estimate/source_generation)·reasons다. 이전 하차=선택차량 예상도착+공급자 차량구간초, 최소 다음승차=이전하차+환승추정도보+환승여유. 다음 정류소 도착 후보 중 최소승차시각 이상인 가장 이른 후보를 선택한다. 현재 제공된 모든 후보가 너무 이르면 unavailable이며 노선 전체/미래 모든 차량이 불가능하다는 뜻이 아니다. 한 연결의시각이없으면후속숫자도null. 현재운행예측을미래탑승보장으로해석하지않는다. 첫차량 valid_for_guidance는첫탑승범위만유지하고 전체환승은connection_status를별도확인한다. 마지막하차는목적지최종도착이아니며목표도착계산은F07-04후속이다.
- 신규 검색 메모리 근거는 첫 BUS뿐 아니라 같은 후보의 후속 BUS 최대2개의 공개 정류소명·차량1개·양끝 점을 포함한다. 사용자GPS/도보geometry/원문/공공ID 영구저장없음, 기존32검색/20후보·검색300초/본인fingerprint·재시작퇴출무효 유지. 각 후속leg에 첫조회와같은30m/제공이름순서/공식방문/회차·방향/유일성 매핑,arrival ID/방향일치·운행/예측초 검사·생성시각/수신추정·120초 기한 정책을 적용한다. 후속leg 매핑/도착을60초 프로세스메모리로재사용하며 원래received_at/ETA/기한을늘리지않는다. 각leg조회전후소유권/검색/후보/매핑기한검사·잠금·기존사용자갱신10회/분을공유한다. 기존후보는최대21회공식호스트HTTPS 호출(첫+2후속각최대7회), 루틴누락접근에별도도보를추가하면5.7.5에따라최대22회, 환승확인전체20초내상한·새매핑각최대5초/도착3초·남은시간부족이면추가호출없이unknown. 최초출발안내는include_connections=false 기본과호환. 후보상세는true/25초클라이언트대기상한으로확인하며 실패/만료에이전연결숫자를제거한다. 새DB/DDL/AI호출없음.
- 원천·물리근거미확인/미지원노선·지하철/재시작·정보만료·제공후보부족은확인불가로남긴다. 현재지원경기BUS환승검사와전체지역/지하철운영지원완료는구분한다. 마감사용자요구 <mention-date start="2026-10-21"/>까지채팅(F14)작동을목표로, 남은실사용출발흐름(F07-02a/04\~06)→약속·참여자(F12)→채팅저장/전달/재접속(F14)→통합검증순으로진행하며필수선행/보안/계약검증을생략하지않는다. 실구현/검증/체크상태는후속기록과TODO를따른다.
- F07-03 구현/검증 완료 <mention-date start="2026-10-14"/>: 지원 경기 버스의 첫 차량과 최대2회 환승 순차 검사를 구현했다. 미지원 지하철/근거 부족/후속 차량 없음은 확인불가 또는 제공 후보 연결불가로 구분한다. 신규 백엔드14개4.737초·전체343개124.115초, 프론트199개10.49초·빌드1907모듈 통과. 실 컴포넌트와 합성 응답으로 PC1280×800/모바일390×844의 연결 시각·확인불가·줄바꿈/가로넘침 없음을 확인했다. 실제 키/AI 호출0회·새DDL없음, 실경로 예측 정확도와 지역 전체 지원은 검증하지 않았다. 개발 일지와 TODO에 범위를 기록하며 F07-02a 루틴 출발 연결·F12 약속/참여자·F14 채팅을 마감 우선순위로 진행한다.
- 응답 예시(시간은 합성값):
```json
{"connection_status":"unknown","transfers":[{"connection_id":"00000000-0000-0000-0000-000000000001","from_leg_id":"00000000-0000-0000-0000-000000000002","to_leg_id":"00000000-0000-0000-0000-000000000003","estimated_alighting_at":"2026-10-14T01:20:00Z","minimum_boarding_at":"2026-10-14T01:24:00Z","next_boarding_at":null,"transfer_walk_seconds":120,"transfer_buffer_seconds":120,"feasibility":"unknown","time_source":"none","reasons":["LEG_MAPPING_UNCONFIRMED"]}],"estimated_final_alighting_at":null}
```
### 5.7.3 루틴 선택→최신 첫 출발 연결(F07-02a-1)
- 담당 분리 <mention-date start="2026-10-14"/>: 이 작업은 루틴 최신 출발 연결을 담당하고 약속·참여자/채팅(F12/F14)은 사용자가 다른 LLM에 맡긴다. 현재 첫 승차/환승 추정 범위 유지, 목표 도착시각·요일에 따른 예약출발/이동중/검증 개인 도보 연결은 후속이다. 루틴 목표시각을 이미 만족한 것처럼 표시하지 않는다.
- POST /api/v1/routines/\{routine_id\}/departure-searches: 쿠키본인·Origin/CSRF·Idempotency-Key 선택, 요청 expected_version:양수정수만 허용. 본인루틴404·버전변경/needs_attention409 VERSION_CONFLICT. 서버가 본인 활성 루틴의 현재 출발/도착 저장장소와 위치버전으로 depart_now 검색을 생성한다. 좌표/접근초/프로필/장소ID를 클라이언트로부터 받지 않는다. 기존검색202의 search_id/job_id/status에 routine_id/routine_version 추가. 기존 검색10회/분·동시본인2/전체8·검색300초/작업60초·안전한오류/중단·24시간요청키 정책을 재사용하며 키의 fingerprint에 루틴ID/버전도 포함한다. 호출전후 루틴/장소/plan 확인, 변경시 오래된 검색으로 안내하지 않는다.
- 검색→루틴 바인딩은 본인ID/루틴ID·버전/planID/좌표없는 경로 서명/검색기한을 최근32검색 프로세스메모리로 제한한다. 검색 자체는 기존DB에 저장하나 새DDL/루틴수정/좌표추가저장/AI호출은없다. 재시작·다른프로세스·퇴출은404로 새검색 필요, 요청키 재현도 바인딩이없으면404(새키필요)로 오래된 근거를 복원하지 않는다.
- GET /api/v1/routines/\{routine_id\}/departure-searches/\{search_id\}/first-departure?expected_version=N: 쿠키본인·no-store·CSRF불필요. 바인딩·루틴버전/plan/장소위치·검색기한을 전후 검사한다. 현재 검색의 공통후보에서 저장노선의 모든구간 type/도보role·교통차량이름/제공정류소순서를 비교한다(ID/시간/거리 변경은 무시). 유일 후보만 기존 first-departure(include_connections=true)로 계산하며 그 도착/프로필/환승 검사를 유지한다. 이 서명은 동일 노선 선택용이며 물리정류소/방향 매핑 인증이 아니다. 첫 도착은 기존검증매핑만사용한다. 다른후보자동선택/루틴경로덮어쓰기없음.
- 응답 routine.departure.v1: routine_id/routine_version/search_id·status(searching/ready/no_routes/route_changed/ambiguous_route)·candidate_id(nullable)·departure(first.departure.v1\|null)·expires_at. searching은 Retry-After:2, 검색실패는 저장된 안전한오류를반환, 후보없음200 no_routes/일치없음200 route_changed/복수일치200 ambiguous_route·숫자없음. ready는 후보가유일하다는뜻이며 실제안내가능여부는 departure.valid_for_guidance/connection_status를확인한다. 기존 GET 후보 first-departure와 초안 POST /guidance-queries는 유지하고 새 루틴 API와 구분한다.
- 화면은 선택/버전변경 시 이전숫자를즉시제거→CSRF/새검색→기존jobpoll→루틴첫출발조회. 첫출발60초/탭복귀 재평가, 검색300초만료시 보이는화면에서새검색·수동다시확인 가능. 숨김/이탈/루틴교체/로그인모달에서는요청취소·뒤늦은응답무시. 실패/인증/버전충돌/만료는이전숫자제거, 무한실패자동재시도없음. 기존미색/초록·카드/CSS 재사용, 다른출발지선택에는집루틴안내를적용하지않는다.
- 구현/검증 상태는 후속 기록. F07-02a의 검증 개인 도보 물리연결은 미완료이며 이번 사용자승인 공급자접근×개인계수 추정 범위로 F07-02a-1을 별도 관리한다.
- F07-02a-1 구현/검증 완료 <mention-date start="2026-10-14"/>: 루틴 선택→현재장소 최신검색→저장노선 유일후보→첫출발/환승 추정 연결. 버전/본인/CSRF/멱등·변경중차단·검색기한/메모리퇴출·실패숫자제거/숨김취소·60초도착/300초검색갱신을 구현했다. 최종전체 백엔드354개137.158초·프론트212개10.81초·빌드1909모듈447ms 통과. 합성 실컴포넌트 PC1280×800/모바일390×844의 출발/접근/여유·추정·다시확인과 가로넘침없음 확인. 실제 키/AI0회·새DDL없음, 실경로 예측정확도/검증개인도보/목표도착은 미검증 또는 후속. 약속·참여자/채팅은 사용자 지정 다른 LLM 담당, 이 에이전트는 루틴 출발 범위를 담당한다. 변경이유·파일·테스트/한계는 `development_log.md`.
### 5.7.4 출발 근거 부족 사유와 남은 시간 표시(F07-05)
- <mention-date start="2026-10-14"/> 사용자 화면 수정 요청: 개인 도보 카드의 이전 '실제 출발 안내 준비 중' 문구를 제거하고, 검증 개인도보와 사용자승인 공급자접근 추정을 구분한다. 접근누락이면 '출발지에서 승차 지점까지 도보 시간이 제공되지 않아 출발 시각을 계산할 수 없어요.'를 표시한다. 도착근거/매핑부족과 별개 원인이며 누락초를0 또는5분으로 대체하지 않는다.
- 기존 arrival.evidence.v2의 reasons에 고정 안전코드만 추가할 수 있다. MAPPING_CONTEXT_UNAVAILABLE(재검색근거필요), MULTIPLE_VEHICLE_OPTIONS(첫버스복수노선), STATION_CANDIDATES_UNCONFIRMED(승차정류소미확인), NO_ROUTE_AT_BOARDING_STOP(경기공급자정류소경유노선미확인), ROUTE_CANDIDATE_LIMIT/VISIT_CANDIDATE_LIMIT/ROUTE_MATCH_AMBIGUOUS(후보모호), ROUTE_SEQUENCE_UNCONFIRMED(정차순서/거리/범위복합미확인), ROUTE_INFO_UNCONFIRMED/TURNAROUND_UNCONFIRMED/DIRECTION_MATCH_AMBIGUOUS(노선방향미확인). 기존 PUBLIC_MAPPING_UNCONFIRMED/LEG_MAPPING_UNCONFIRMED 유지·기존필드/상태/안내차단/매핑30m/방향/호출/TTL 정책 유지. mapper의 이번 조회 diagnostics.reason을 허용목록으로만 전달하고 원문·ID/좌표·개수/세부match_checks·키는 공개하지 않는다. 성공매핑/이미캐시에는불필요한진단조회없음, 기존한조회에서만사유수집한다.
- 'N분 뒤 예상 출발'은 유효한 first.departure.v1과 서버시각+단조경과 기준 selected_departure_at까지 올림 분,60초미만은 '1분 이내 예상 출발', 시각도래/경과는 '지금 출발 기준으로 다시 확인해주세요.'다. 출발 시각이 지나도 과거의 설정여유 확보를 주장하지 않는다. 화면의 예상 여유초는 floor(vehicle_arrival_at-max(selected_departure_at,현재서버시각)-approach_seconds)이며 음수면 안내숫자제거. 미래권장/지금 선택일 때 '그때/지금 출발하면 정류장 도착 후 예상 M분\[초\] 여유'를 함께 표시한다. 설정여유보다 작으면명시경고·초단위보존, 첫승차 정류장여유만뜻하며목적지도착/전체환승/실제탑승보장없음.
- 실패·만료·접근누락·미지원·매핑부족에는 출발카운트/여유를만들지않는다. 숫자는서버유효근거만사용하며 이전기한/호출수·개인계수/루틴/DB/AI 정책변경없음. 구현/검증 상태는후속기록.
- 출발 문구/사유 수정·F07-05 구현검증 완료 <mention-date start="2026-10-14"/>: 이전 준비중 문구 제거·접근누락/허용매핑실패코드 구분·유효첫출발 카운트/현재정류장여유/설정미달·만료숫자제거. 신규백엔드5개3.102초 포함 최종전체359개132.743초 통과, 프론트218개13.85초·방어추가후관련33개2.27초·빌드1909모듈438ms 통과. 합성실컴포넌트1280×1100/390×1600의 유효/부족상태·줄바꿈/모바일가로넘침없음 확인. 기존격리오프라인진단도구의선택적diagnostics 전달을수정했고 추가실키/AI0회·새DDL없음. 최근저장검색의접근도보누락을확인했지만사용자선택후보의매핑실패단계/미지원지역은과거진단으로확정하지않았다. 검증과한계는 `development_log.md`.
- F07-02a-2의 미정 설계는5.7.5의 검증경기승차좌표→카카오도보1회/검색한정메모리 정책으로 확정·구현했다. 지원경기BUS 루틴의누락접근보완범위이며 목표도착F07-04/다음차량F07-06·검증개인도보연결은미완료유지.
### 5.7.5 루틴의 누락 접근 도보 보완(F07-02a-2)
- <mention-date start="2026-10-14"/> 사용자 후속진행: 본인 루틴 첫 버스에 ACCESS_WALK_MISSING이고 첫구간이BUS인 경우, 본인 저장출발지→검증된 경기 승차정류소의 공식좌표로 카카오 GET /v2/routing/walk를 최대1회 조회한다. 이미제공된 양수접근도보는유지, 명시0초/지하철/복수노선/매핑미확인/원래지도핀·현재위치후보GET에는자동대체없음. 루틴 내부서버의 검증출발장소참조만사용하며 공개좌표/장소ID/시간 입력추가없음.
- 공식 승차좌표는 기존30m/제공정류소순서/공식노선·순번/회차·방향 유일매핑을 통과한 실제 stationId/staOrder 행에서만 채택한다. 매핑의별도 비공개endpoint sink로 전달하며 diagnostics/공개Mapping/로그/DB에는넣지않는다. 좌표는같은검색근거메모리의 매핑identity/첫leg/fingerprint와묶고 현재기한·장소/루틴/프로필을 호출전후검사한다. 매핑해결은여전히선행조건이며 미지원노선에임의좌표로진행하지않는다.
- 도보API는고정 [dapi.kakao.com](http://dapi.kakao.com) HTTPS/리다이렉트금지/REST키 서버내부/WGS84·경도x/위도y/최단경로1개/최대3초·응답1MiB·중복JSON/NaN거절. status=OK·[route.properties](http://route.properties)의양수totalTime(초,최대86400)/양수totalDistance(미터,최대100000), 1\~20legs/전체500steps/20000points·정수비음수시간/거리·유한좌표·구간/단계합일치·단계연결/출발·승차양끝30m 이내를검사한다. 동일점/결과없음/도로없음/실패/0초·손상·위치불일치는시간없음, 직선거리/총대중교통시간의잔여/임의5분대체없음. 보행안전/정류장출입구·물리보행 인증 또는 AI산정값으로표현하지않는다. 공식계약: [카카오맵 REST API](https://developers.kakao.com/docs/ko/kakaomap/rest-api).
- 기존 first.departure.v1에 provider_approach_source(transit_segment/boarding_walk\|null)·approach_fetched_at/approach_valid_until(nullable)을 추가한다. 기존approach_basis=provider_personalized와계수/수식은유지, 별도도보초W=ceil(공급자도보totalTime×본인계수), 여유는별도. boarding_walk이면숫자근거/기한을함께표시, 계산기한은원래도착/검색/매핑/도보기한 중최소. 제공접근은transit_segment·새시간필드null, 구클라이언트필드호환. 후보/루틴/plan·missing_segments DB스냅샷은고치지않고sidecar로만사용한다.
- 도보양수초·fetched_at·기한·본인출발장소버전/매핑identity는동일검색의프로세스메모리에만보관한다(최대32검색/20후보·검색300초 이내), 원문/사용자좌표/보행geometry/이름 영구저장·AI전달없음. 새계수는원래공급자초에한번만적용·도보캐시기한연장/재조회없음. 실패시도도60초동일검색재시도차단, 기한초과/재시작/퇴출/매핑·장소변경은다시근거확보. 기존user갱신10회/분·entry잠금공유, 중복동시조회429. 전체출발/환승20초·클라이언트25초는유지하고 전체외부상한은도보1회를포함최대22회(첫+후속2각최대7/도보1), 남은시간부족이면추가조회없이부족처리한다.
- 고정사유: ACCESS_WALK_MAPPING_REQUIRED/ACCESS_WALK_UNAVAILABLE/ACCESS_WALK_TIMEOUT/ACCESS_WALK_TIME_LIMIT. 루틴출발화면은별도조회한공급자접근추정과실패를구분한다. 추가외부조회는실사용요청에서최대1회이며이번직접키검증은실행하지않는다. 새DDL/AI·새HTTP경로없음. F07-02a-2는지원경기BUS 루틴누락접근복구범위이며 검증개인도보/F07-02a전체·미지원매핑/목표도착은후속. 구현/검증은후속기록.
- F07-02a-2 구현/검증 완료 <mention-date start="2026-10-14"/>: 검증된공식승차행의비공개endpoint/identity·루틴본인출발장소·누락조건·카카오도보검증/메모리/계수재계산·호출전후변경검사/전체시간상한과출처/실패표시를구현했다. 신규백엔드16개 포함 최종전체375개155.207초 통과, 프론트222개23.72초·빌드1909모듈750ms 통과. 합성실컴포넌트1280×1100/390×1400 성공·실패/출처/줄바꿈·모바일가로넘침없음 확인. 최초전체의기존장소쿼터테스트 분경계불안정1개는테스트DB시간고정으로수정했고운영제한변경없음. 이번직접실키/AI0회·새DDL없음, 사용자실경로의양수출발/도보정확도는미검증. 미지원매핑·검증개인도보/목표도착은후속. 상세 `development_log.md`/TODO.
### 5.7.6 목표 도착 평가(F07-04)
- 루틴수동선택의 현재 유일후보를 오늘 Asia/Seoul의 target_arrival_local_time과 비교한다. 이는이번구현정책이며사용자가새날짜정책을별도확정했다고주장하지않는다. 반복요일은저장/일정참고이고수동선택을차단하지않는다. 미설정은not_configured, 이미지난오늘목표는target_passed·다음날/다음주로자동넘기지않는다. 미래예약시간표/arrive_by 경로검색·다른노선자동선택/루틴덮어쓰기·다음차량선택은이번범위밖후속이다.
- 기존 first.departure.v1에 nullable target_evaluation(target.arrival.v1)을 추가한다. 루틴GET의ready후보에서계산, 일반후보GET는null유지. 필드 status(not_configured/estimated_meets/estimated_late/target_passed/unknown/stale), evaluated_at, target_arrival_at, estimated_destination_arrival_at, margin_seconds, egress_seconds, timing_basis(none/provider_timeline), reasons. 시각/차이/도보초는미확인시null, scope는selected_routine_candidate. 기존첫승차 valid_for_guidance/connection_status는유지하며목표평가를별도로확인한다.
- 유효첫승차·전체connection_status=estimated_feasible·모든transit가BUS/양수차량구간초·순차연결일치·estimated_final_alighting_at와 타임라인일치가필요하다. 마지막차량이후 egress WALKING전체가양수/누락없을때 E=ceil(공급자마지막도보초합×본인walking_duration_factor), 목적지ETA=마지막하차+E. 마지막도보가없거나0초·미지원/앞연결실패·기한초과/차량경과/시간오류는unknown/stale, 정류소하차를목적지도착으로대체하지않는다.
- 공급자 timing_breakdown의unallocated_seconds를접근·환승·마지막도보/대기시간에임의배분하지않는다. 총합불일치(inconsistent)는unknown. 현재선택차량/환승의제공ETA와양수구간도보/차량초로만추정타임라인을계산하고미배분총시간은별도로더하지않는다. 실제교통/보행/미래탑승·목표충족보장이아닌provider_timeline 추정이며미배분이있는경우그사유도남긴다.
- 목적지ETA\<=목표면estimated_meets, 늦으면estimated_late·margin=floor((목표-ETA).total_seconds())를음수그대로반환한다. 목표여유는정류장첫승차버퍼와다르며초를보존하고자동여유축소/지난목표이월없음. 프로필·루틴/장소/검색/후보/매핑기한을기존전후검사로유지하고목표평가전후프로필도재확인한다. 계산+기한은기존출발근거기한을공유해연장하지않는다.
- 화면은목표시각·예상목적지도착·목표기준예상여유/늦음과추정한계를표시한다. 미설정/지난목표/마지막도보·환승부족/실패·만료를구분하고이전목표숫자를제거한다. 시계경과로목표가지나면재확인안내, 새API/외부조회/AI/DB·DDL추가없음. 기존CSS/색상/카드재사용. 구현/검증은후속기록.
- F07-04 구현/검증 완료 <mention-date start="2026-10-14"/>: 선택루틴의오늘목표·미설정/지난목표·양수마지막도보/순차환승 타임라인과목적지ETA·목표차이·충족추정/늦음/미확인/만료를계산하고목표/프로필변경중409를검사한다. 신규백엔드11개5.199초 포함 전체386개147.203초, 프론트229개10.04초·빌드1909모듈438ms 통과. 합성실컴포넌트 PC/모바일에서목표여유와정류장여유 구분·마지막도보부족/목표숫자없음·줄바꿈/모바일가로넘침없음확인. 새외부조회/직접실키/AI0회·DDL없음, 실도착정확도·미래예약/대체노선자동조회·다음차량선택은후속. 이유/파일/검증은 `development_log.md`와TODO에기록했다.
### 5.7.7 접근 불가능한 첫 차량 대신 다음 후보 선택(F07-06a)
- 기존 후보/루틴 first-departure GET에서 승인된 유효 도착 후보를 ETA와 후보ID 순으로 정렬한다. now부터 개인화 접근 W를 확보할 수 있는 가장 이른 후보(ETA-now \>= W)를 선택한다. 정확히 W인 경계도 허용한다. B는 별도 여유이며 권장 s=ETA-W-B, 지금 출발 여유와 below_buffer 경고는 기존 정책을 유지한다.
- 더 이른 제공 후보가 접근 불가능해 건너뛴 경우 고정 사유 NEXT_REACHABLE_VEHICLE을 추가한다. 응답 모델/필드/권한/CSRF/쿼터/캐시 기한은 유지하며 원래 후보 목록을 삭제하거나 수신시각을 새로 만들지 않는다. 가능한 후보가 없으면 기존 가장 이른 후보의 음수 여유/not_enough_time을 유지한다. 누락 도보/매핑/만료/원천 오류에서는 전환 시각을 만들지 않는다.
- 다음 첫 차량의 ETA로 기존 순차 환승과 루틴의 오늘 목표 도착을 다시 계산한다. 미제공 차량/시간표나 대체 경로 조회는 없고 추가 외부 호출/DDL/AI도 없다. 60초 조회·탭 복귀·실패/만료 차단은 기존 화면을 재사용한다.
- 이는 현재 위치에서 접근할 수 없는 후보를 제외하는 기능이다. 출발 안내 후 now-s \> W/2이고 수동 departed 확인이 없을 때 전환하는 사용자 규칙은 F07-06b로 미완료 유지한다. 수동 세션/출발 저장 기반은5.8.1에 따라 구현하고 절반경과 정책의 연결은후속이므로 출발 확인을 추측하거나 무조건 미출발로 판정하지 않는다. F07-06 전체는 아직 미완료다.
- 호환성: 기존 first.departure.v1 형식 그대로, 같은 제공 후보들 중 선택 차량/출발·환승·목표 숫자가 달라질 수 있고 reasons에 위 고정 코드를 추가한다. 기존 클라이언트는 알 수 없는 사유를 무시할 수 있다.
- F07-06a 구현/검증 완료 <mention-date start="2026-10-14"/>: 현재 접근 불가능한 후보를 제외한 다음 제공 차량 선택·동일 도착 TTL/수신 보존·환승/목표 재계산·전환 이유 표시. 신규 백엔드8개2.210초 포함 전체394개167.811초, 프론트231개10.63초·빌드1909모듈436ms, 실제 엄격 클라이언트/합성 응답 PC1280×1000·모바일390×1100 확인. 직접 외부키/AI0회·새DDL없음. 실제 사용자 경로 추천 성공은 미검증. 수동 departed 기반 F07-06b와F07-06전체 미완료.
### 5.8 실제 이동 이벤트
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
### 5.8.1 루틴 안내 연결 이동 세션과 수동 출발(F08-01/F08-02a)
- 이번 범위는 지원 루틴의 유효 첫 출발 안내에 연결된 assisted/baseline 세션, 본인 조회/취소와 첫 departed 수동 신고다. 접근 완료/탑승/하차·환승 결과·정정/학습/내보내기/삭제작업은 미구현 상태를 유지한다. F07-06b 절반 경과 정책은 이 저장 기반 후속 연결이며 이번 단계에서 자동 전환하지 않는다.
- 루틴 출발 GET의 nested first.departure.v1에 nullable guidance_id(UUID)를 추가한다. 유효 안내에만 서버가 당시 departure/좌표 없는 정규화 경로·루틴/장소/프로필 버전과 묶인 토큰을 최근128개 프로세스 메모리에 발급한다. 기한은 원래 안내/검색 중 최소, 연장 없음. 일반 후보 GET/근거부족은null. GET에서 DB 안내/이동 생성이나 실제 출발 신고는 없다. 재시작/다른 프로세스/퇴출은 토큰404·새 안내 필요.
- POST /api/v1/trips는 기존 guidance_id(UUID), measurement_mode:assisted\|baseline만 받는다. 쿠키 본인·Origin/CSRF/no-store, 유효 토큰과 현재 루틴/경로/장소/프로필 버전을 DB 공유 잠금으로 재검사하여 당시 안내 스냅샷과 이동을 원자 저장한다. 생성 시 현재부터 W만큼 접근할 수 있는 차량인지도 재검사하고 이미 접근 불가능하면404·새 안내 필요. 좌표/원문/사용자 지정 ETA·출발 여부를 입력받지 않는다. 201 data는 trip_id,guidance_id,routine_id(nullable),measurement_mode,status(active\|cancelled),version,created_at,expires_at,departure_event(nullable)이며 당시 안내는GET상세에서 제공한다. 아직 출발하지 않은 세션이며 departed와 구분한다.
- 선택 Idempotency-Key(1\~128자 ASCII 영문/숫자/밑줄/하이픈)는 본인+POST /trips+키/본문 해시와 결과 참조를24시간 보관한다. 같은 키/정규화본문200 저장결과, 다른본문409 IDEMPOTENCY_CONFLICT, 삭제/기한경과 기록은404·재생성없음. 키 없이도 동일 본인 guidance_id+mode 재전송은 같은 세션200(안내 토큰 만료/재시작 뒤에도 저장 결과 복구 가능), 다른mode409 IDEMPOTENCY_CONFLICT. 유효한 진행 중 이동은 본인당1개, 다른 guidance로 생성하면409 ACTIVE_TRIP_EXISTS. 본인 생성 요청10회/분·이벤트30회/분·멱등재전송 추가생성 없음. 지원외 guidance/타인/만료404, 루틴/장소/프로필 변경409 VERSION_CONFLICT.
- GET /api/v1/trips는 limit기본20/1\~100, cursor(본인trip UUID)·routine_id(UUID)·status:active\|cancelled 선택 필터, 생성시각/ID내림차순과 items/next_cursor를 반환한다. from/to·완료/놓침 필터는 후속. GET /trips/\{trip_id\}는 본인200의 trip, immutable guidance,events 배열,outcome(active면null/cancelled면cancelled). CSRF불필요/no-store·타인/만료404. 사용자 목록/상세에서 active 세션을 복구할 수 있다.
- POST /trips/\{trip_id\}/events는 client_event_id(UUID), type:departed, occurred_at(시간대 있는datetime), leg_id(UUID), source:manual만 지원하고 추가 필드 거부. guidance 경로의 첫 ordered_leg ID와 일치해야 한다. occurred_at은 당시 안내 calculated_at 이상/서버 received_at 이하, 시간대 없는 값/미래/안내 이전은422 VALIDATION_ERROR. 받은 시간은 서버에서 별도 저장하고 실제 보행시간/정확도/학습을 인증하지 않는다. 입력 지연은 received_at-occurred_at 초로 본인 응답에 제공하되 임의 임계값으로 학습 적격 처리하지 않는다.
- 세션 행을 잠그고 최초 departed 하나만 저장한다. 동일 본인 trip/client_event_id+정규화본문 재전송200 기존event·다른본문409 IDEMPOTENCY_CONFLICT, 다른ID의 두번째departed 또는 취소 세션의 새 이벤트409 INVALID_EVENT_ORDER. 201/200 event는 event_id,client_event_id,trip_id,type,leg_id,source,occurred_at,received_at,input_delay_seconds,excluded:false,version:1. 시각/좌표/출발 신고는 일반로그에 남기지 않는다.
- PATCH /trips/\{trip_id\}는 outcome:cancelled, expected_version양수정수만 지원한다. 본인/CSRF/no-store, 버전 일치200 cancelled와version증가·다른버전409, 같은버전의 이미취소는변경없이200. 본인 active 세션을 취소한 뒤 새 세션을 만들 수 있다. 취소는 과거 departed를 삭제하거나 실제 미이동/놓침으로 바꾸지 않는다.
- 안내 스냅샷/이동/이벤트는 생성시각부터90일 보관, 읽기와 쓰기에서 expires_at 이후 차단하며 다음 쓰기에서 만료 이동과 연결 스냅샷을 정리한다. 사용자 삭제/탈퇴 cascade; 이동 삭제·정정/학습 파생 정리와 매일 청소는 후속 미완료. 토큰의 짧은 계산 유효기간과 저장된 과거 안내의90일 보관을 구분한다. 새 DB guidance_snapshots/manual_trips/manual_trip_events/manual_trip_creation_keys는 미병합 F12 저장소와 구분하며 migration0013_manual_trips는 현재main0012에서 이어진다. F12별도 migration과 향후 병합 시 Alembic head 통합이 필요하다.
- UI는 기존 카드/버튼/상태표현으로 유효 루틴 안내의 '지금 출발했어요'를 제공한다. 당시 안내토큰으로 세션 생성→수동 departed 저장 후에만 확인 완료를 표시한다. 실패시 같은토큰/이벤트ID·발생시각 재시도, 중복누름 차단·화면 이탈취소. 복구된 진행중 세션과 출발 기록/취소를 표시한다. 사용자 저장 성공을 서버 확인하기 전 완료로 표시하지 않는다.
- 호환성: 기존 POST /trips의 guidance_id/mode 초안 입력 유지, 루틴 안내응답에 nullable 토큰 추가. 미구현 API의 구체적범위/시간/중복/보관/오류를확정하는 구현정책이며 다른담당 약속 안내토큰을 지원한다고 주장하지 않는다.
- F08-01/F08-02a 구현·검증 완료 <mention-date start="2026-10-14"/>: 유효 루틴 안내 토큰→불변 스냅샷/assisted·baseline 이동→본인 복구/취소→수동 departed·멱등/순서·시간/권한·90일 만료. 신규 격리 백엔드12개 최종23.270초, 전체406개194.374초 통과 후 ISO 문자열 검증 강화 관련12개 재검증. 프론트 전체242개37.85초 통과 후 취소 토큰 재사용 차단 관련6개1.73초 재검증·최종빌드1911모듈423ms. 합성 응답/실제 컴포넌트·클라이언트 PC1280×800·모바일390×844 성공/실패·재시도/취소 확인. 개발 DB0013_manual_trips 테이블4개/기존 데이터 보존. 외부 실키/AI0회·실사용자 로그인/추천 성공/실제 이동 정확도 미검증. F07-06b 연결·나머지F08 이벤트/정정/학습/내보내기/삭제·약속 안내 토큰 호환은 후속.
### 5.9 첫 탑승 도착 근거(F07-01a/01b, 생성시각 검증과 수신 기준 추정 구분)
- GET /api/v1/journey-searches/\{search_id\}/candidates/\{candidate_id\}/first-arrivals는 쿠키 인증·본인·no-store·CSRF 불필요다. journey.v1의 공공 ID/방향은 여전히 null이지만 신규 검색의 서버 메모리 근거로 유일 경기 BUS 매핑을 확인하면 도착을 조회한다. 근거 없음/재시작/다른 프로세스/퇴출·모호한 매핑은200 mapping_required·빈 후보·valid_for_guidance=false, 첫 지하철은200 unsupported다. 타인/없음/검색 만료404·장소 변경409, 공개 입력으로 검증 플래그/정류소ID를 받지 않는다. 앱 API 입력/응답 필드는 유지하며 실제 운영 키 실검증은 아래 결과를 따른다.
- 내부 조회는 본인/검색/장소 버전/후보 fingerprint/첫 leg를 확인한다. 서버 자동 매핑은 원문 geometry를 영구 저장하지 않고 검색 범위 메모리의 첫BUS 정류소/차량1개·양끝 점(선택적 환승 검사는5.7.2에 따라 후속BUS 최대2개도 보관)으로 경기 공식 정류소/경유노선/정차목록/상세를 대조해 Mapping을 생성한다. 이름이나 카카오 ID만으로 매핑하지 않는다. 내부 호출자가 검증한 station_id/route_id/sta_order/route_dest_id·first_leg_id·mapping_version·verified_at/valid_until을 전달하는 기존 함수도 유지한다. 세부30m/연속 정차/메모리·호출 제한은 F07-01b 운영 정책을 따른다.
- 고정 공식 HTTPS·키 환경변수·리다이렉트 금지·3초·256KiB 제한, 인증/쿼터/전송503 PROVIDER_UNAVAILABLE·시간초과504 PROVIDER_TIMEOUT·스키마/ID 충돌502 PROVIDER_RESPONSE_INVALID. 경기 결과0 정상/4 무결과를 구분하고 요청 stationId/routeId/staOrder/routeDestId가 정확히 일치하는 유일 행만 사용한다. RUN의 predictTimeSec1/2 양수 정수와 vehId1/2를 검사한다. 분 필드로 대체하지 않고0/음수/누락/86400초 초과·WAIT/PASS/미확인 상태는 시간 근거 부족, STOP은 무후보다. 차량번호/주소/원문/키/URL은 응답·로그·DB에 남기지 않는다.
- arrival.evidence.v2는 search_id/candidate_id/first_leg_id·status(mapping_required/unsupported/no_arrivals/insufficient_data/fresh/estimated/expired)·source_status(unknown/fresh/stale/clock_mismatch)·timing_basis(none/source_generation/receipt_estimate)·received_at/generated_at/expires_at·valid_for_guidance·reasons·candidates를 제공한다. 후보는 비식별 candidate_id·provider_prediction_seconds(원래 예측초)·predicted_arrival_at(nullable)·remaining_seconds(nullable, 각 응답 평가 시점의 올림 정수 초)이다. 유효기한은 수신+120초·검증 생성+120초(있을 때)·검색/매핑 기한 중 이른 값,120초 경계까지 유효다. 원천 시각 없음/naive/미래를 fresh로 인증하지 않는다. v1에서 enum/필드/의미를 변경하므로 클라이언트는 v2와 estimated를 처리해야 한다.
- 경기 queryTime은 정보요청시간이라 생성시각으로 쓰지 않는다. 생성시각이 없는 정상 경기 RUN/양수 예측초는 generated_at=null/source_status=unknown/timing_basis=receipt_estimate/status=estimated로 수신시각+예측초를 추정 도착시각으로 사용한다. 유효 후보가 있고 모든 기한을 만족하면 valid_for_guidance=true이며 이는 사용자 승인 추정 사용 허용이지 원천 최신성 인증/탑승 보장이 아니다. 검증 생성시각이 있으면 timing_basis=source_generation/status=fresh로 생성시각+예측초를 사용한다. 잘못된/naive/미래 생성시각·수신시각 역전은 수신 추정으로 우회하지 않는다. 이미 지난 예측은 제외하고 후보가 없으면 insufficient_data, 정상 무결과는 no_arrivals다. 원천 최신성 강화를 F07-01c로 별도 추적하고 개인 접근/기본여유300초를 사용하는 실제 출발 시각 계산은 F07-02에서 구현한다.
- 호출 전후 소유권·검색/후보 스냅샷·장소/매핑 기한을 재검사하고 메모리 재사용도 현재 소유권/기한을 다시 확인한다. DB/루틴 저장·TTL 연장·DDL·AI 호출 추가 없음. 후보 상세의 v2 추정 표시/60초 조회를 연결하며 개인 접근/여유 출발 계산은 F07-02 후속이다. 원천 최신성 강화(F07-01c)/지원 범위는 별도로 남겨 F07-01 전체는 미완료다.
공개 수신 기준 추정 data 합성 예시(평가시각=수신시각, 실제 응답 아님):
```json
{"model_version":"arrival.evidence.v2","search_id":"00000000-0000-4000-8000-000000000001","candidate_id":"00000000-0000-4000-8000-000000000002","first_leg_id":"00000000-0000-4000-8000-000000000003","status":"estimated","source_status":"unknown","timing_basis":"receipt_estimate","received_at":"2026-10-13T03:00:00Z","generated_at":null,"expires_at":"2026-10-13T03:02:00Z","valid_for_guidance":true,"reasons":["GENERATION_TIME_UNCONFIRMED","RECEIPT_BASED_ESTIMATE"],"candidates":[{"candidate_id":"00000000-0000-4000-8000-000000000004","provider_prediction_seconds":300,"predicted_arrival_at":"2026-10-13T03:05:00Z","remaining_seconds":300}]}
```
공개 미매핑 data 합성 예시:
```json
{"model_version":"arrival.evidence.v2","search_id":"00000000-0000-4000-8000-000000000001","candidate_id":"00000000-0000-4000-8000-000000000002","first_leg_id":"00000000-0000-4000-8000-000000000003","status":"mapping_required","source_status":"unknown","received_at":null,"generated_at":null,"expires_at":"2026-10-13T03:00:00Z","valid_for_guidance":false,"reasons":["PUBLIC_MAPPING_UNCONFIRMED"],"candidates":[],"timing_basis":"none"}
```
- 검증 완료: 신규17개·전체 백엔드238개 통과(104.254초, 격리 PostgreSQL/ASGI·합성 공급자). ID/초/운행 상태·중복/비정상 JSON/응답 크기·키 없음/전송 오류·120초 경계/미래/naive/예측 경과·소유권/미매핑 무호출·호출 중 검색/장소 변경·원문 비노출/TTL 유지·OpenAPI를 확인했다. 실제 서버health200·새GET 비인증401·프론트200, DB head0011/회원20·장소35·루틴12·산정0 유지. 실제 키 전송/공급자 실조회·프론트 변경 없음. 운영 매핑/원천 시각 검증과 실제 조회는 여전히 미완료이며 F07-01 전체는 체크하지 않는다.
- 공식 필드 근거: [경기 버스 도착 항목 명세](https://www.gbis.go.kr/gbis2014/publicService.action?cmd=mBusArrival). queryTime은 요청시간, predictTimeSec1/2는 초 단위 예측 필드다.
- F07-01b 방향 진단 준비 <mention-date start="2026-10-13"/>: 경기 공식 노선정보의 startStationId/endStationId/turnStID와 경유정류소의 stationSeq/turnSeq/turnYn을 대조하는 공개 경로 진단을 추가했다. 단순 왕복의 일관된 회차점·연속 순번·양끝 ID만 방향 후보로 만들고 회차 경유/회차점 승차·순환/누락/충돌은 미확인으로 둔다. 유일 도착행의 stationId/routeId/staOrder/routeDestId 일치를 추가 검사한다. 진단용100m는 운영 정책이 아니며 운영 매핑/저장/공개GET 연결은 추가하지 않았다. 합성 방향7개+기존 매핑7개, 기존 도착17개 통과. 실조회 명령은 자동 승인 검토에서 키/좌표 외부 전송 승인 부재로 거부되어 실행되지 않았다. 이후 사용자가 공개 판교역→성남시청 좌표의 카카오·경기 HTTPS 최대10회 조회를 명시 승인했다. 실제 카카오 경로1회/경기 노선 검색1회, 총2회 실행했으나 동명 후보12개가 대조 한도6개를 넘어 route_disambiguation_required로 중단됐다. 정차 목록/노선 상세/도착정보는 호출하지 않았다. 승인 대기는 해소됐고 유일 후보·방향·최신성 검증은 미완료다. 원문/키/차량번호는 출력·저장하지 않는다. 경기 생성시각은 계속 미확인으로 유지하고 F07-01/F07-01b는 미완료다. 다음은 동명 후보를 근거로 좁히는 조회 전략을 마련하고 승인된 호출 예산 안에서 방향을 대조하는 작업이다. 신뢰할 원천 시각/공급자와 운영 정책도 계속 미확인이다.
- F07-01b 정류소 기반 후보 축소 <mention-date start="2026-10-13"/>: 공개 진단을 승차 정류소명+양끝 좌표100m 대조→근처 정류소 최대2개 전체 경유노선 조회→이름이 일치하는 모든 노선의 정차 순서/승하차 좌표 대조로 변경했다. 가까운 한 정류소나 일부 노선만 골라 유일하다고 인증하지 않는다. 경유노선 stationId/routeId/staOrder/routeDestId를 후보와 연결하고 단순 왕복 회차 가설/도착행을 별도로 검사한다. 진단100m는 운영 정책이 아니다. 요청 예산1\~10회 선택·기본10회, 남은8회 실행은 앞선2회를 포함한 승인 총10회 안에서 강제했다. 추가10회 명령은 승인 검토에서 누적 한도 문제로 실행 전 거부됐고, 남은8회 제한 수정 후 승인 검토를 통과했다. 실제 이번7회/누적9회, 근처 정류소2개·노선1개·승차12/하차23·양끝 거리4.29m/12.85m·유일 매칭1개와 도착행1개의 정류소/노선/순번 일치를 확인했다. direction_unresolved/arrival_direction_matches=false라 방향 검증은 미완료이며 생성시각도 미확인이다. 뒤에 고정 실패 사유 출력 보완을 추가했으나 키 실조회는 재실행하지 않아 이번 방향 실패의 상세 사유는 아직 알 수 없다. 정류소/경유 노선·예산/권한 실패/중복·형식/충돌·고정 사유 비노출 합성 신규14개와 매핑15개 통과. 운영 자동 매핑/저장/공개GET/출발 계산 연결 없음. F07-01/F07-01b는 미체크다. 다음은 실제 방향 실패 원인과 노선 형태·원천 최신성/운영 정책 확인이다.
- F07-01b 방향 실패 사유 실확인 <mention-date start="2026-10-13"/>: 사용자 추가8회 승인 후 같은 공개 경로를7회 조회했다. 노선 후보1개·정류소2개·매칭1개·승차12/하차23·도착1행의 정류소/노선/순번 일치는 다시 확인했다. 실제 direction_reason=SIMPLE_RETURN_ENDPOINT_UNCONFIRMED이며 단순 왕복 검사에서 startStationId=endStationId 또는 정차 목록 첫/마지막 stationId가 startStationId와 불일치하는 묶음 조건이다. 어느 개별 조건이 실패했는지는 이번 출력만으로 구분되지 않으므로 특정 원천 오류나 반대편 정류소 문제로 단정하지 않는다. direction_unresolved/arrival_direction_matches=false/생성시각 미확인/valid_for_guidance=false를 유지한다. 이번7회·기존9회=누적16회, 승인10+8=18회 중2회 잔여다. 테스트/코드/앱 API/저장/계산 변경 없음. 다음은 단순 왕복 전제와 실제 양방향 종점 구조를 분리해 진단하고 공식 경유노선 방향 근거를 대조하는 작업이며 원천 시각/운영 연결도 미완료다.
- F07-01b 왕복 전제 분리 진단 <mention-date start="2026-10-13"/>: 공식 경유노선에서 얻은 station/route/방문순번/routeDestId scope를 선택적으로 사용하는 방향 진단을 추가했다. scope가 없으면 기존 단순 왕복 가설을 유지한다. scope가 있으면 노선 상세 routeId와 회차점 ID, 연속 정차 순번·유일/일관된 회차 표시·승하차 ID/순번·같은 방향 안의 구간을 확인하고 scope routeDestId를 해당 방향의 실제 끝 정류소와 정확히 대조한다. 왕복 마지막 정류소 ID가 canonical startStationId와 같다는 가정이나 endStationId의 물리 정류소 별칭 가정으로 목적 방향을 만들지 않는다. 순환/회차 통과/회차점 승차·scope 방문/종착 충돌은 계속 미확인이다. 공개 입력/API/운영 매핑에는 연결하지 않았다. 진단만 direction_basis와 return_endpoint_matches_start를 값 비노출로 제공한다. 새 합성7개 포함 매핑21개/정류소15개 총36개 통과. 수정 후 키 실조회0회이며 실제 실패 해소는 아직 확인되지 않았다. 기존 누적16회/승인18회·2회 잔여로 전체 진단 재실행에는 부족하다. F07-01b/F07-01 전체 미완료·원천 생성시각/운영 연결 미확인 유지. 다음은 수정 진단의 실제 방향 대조다.
- F07-01b 수정 방향 진단 실확인 <mention-date start="2026-10-13"/>: 사용자 추가8회 승인 후 동일 공개 판교역→성남시청 경로를7회 조회해 종료코드0을 확인했다. 노선 후보1개·근처 정류소2개·유일 매칭1개·승차12/하차23·거리4.29m/12.85m·도착1행에서 정류소/노선/순번/routeDestId 방향이 모두 일치했다. direction_status=direction_candidate/direction_basis=station_route_scope/arrival_direction_matches=true이며 return_endpoint_matches_start=false로 이전 단순 왕복 전제와 실제 끝 정류소 ID 불일치가 확인됐다. 이것만으로 해당 정류소의 물리적 반대편 여부를 단정하지 않는다. queryTime 존재·verified_generation_time_available=false/valid_for_guidance=false/production_mapping_validated=false를 유지한다. 이번7회+이전16회=누적23회, 승인10+8+8=26회 중3회 잔여다. 코드/테스트/앱 API/계산/저장 변경 없음. 공개 한 사례의 진단 성공이며100m 운영 매핑 정책·자동 저장/공개GET 연결·원천 생성시각은 미확인이다. F07-01b/F07-01 전체 미완료, 다음은 운영 매핑 정책/연결 설계와 신뢰할 원천 시각 확보다.
- F07-01b 경기 첫 버스 운영 연결 정책 <mention-date start="2026-10-13"/>: 신규 경로 검색 작업은 첫 교통leg가 BUS이고 차량 이름1개인 후보의 공개 버스 정류소 이름/첫·끝 점만 서버 메모리에 보관한다. 사용자 출발/도착 GPS·도보 geometry·공급자 원문은 저장하지 않는다. 본인/검색/후보·스냅샷 fingerprint와 묶어 검색300초 이내, 프로세스당 최근32검색/검색당 최대20후보로 제한하며 재시작/다른 프로세스/퇴출은 mapping_required로 복구한다. DB/루틴 영구 저장·TTL 연장 없음. 첫-arrivals GET은 메모리 근거가 있을 때만 경기 HTTPS 정류소 검색/최대2정류소 경유노선/최대2노선 정차목록/유일 노선 상세와 도착항목을 조회한다. 초기 운영 정책은 양끝30m 이내·모든 카카오 제공 정류소 이름의 순서(공공 중간 정류소 추가 허용)·공식 station/route/방문순번/방향ID·회차/같은 방향 범위/실제 끝 정류소의 유일 일치이며 최근 한 진단의100m를 운영 허용오차로 승격하지 않는다. 근거 부족/복수 후보/회차/순환/차량 복수는 mapping_required, 지하철 unsupported다. 매핑 최대6회/총5초 예산·각최대3초/응답1MiB와 도착1회/3초(전체최대7회), 호출 전후 본인/장소/검색/후보/매핑 기한을 검사한다. 동일 후보 조회는 프로세스 내 병렬 중복 방지·60초 수신 결과 재사용(최초 수신/생성/검색 기한 유지), 서버 메모리만 사용하며 최대10회/분/사용자의 공급자 갱신 제한을 적용한다. 공급자 오류502/503/504와 버킷429는 기존 오류 형식이다. 경기 생성시각은 unknown/generated_at=null을 유지하고 정상 예측초는 v0.72 사용자 승인 수신 추정 정책에 따라 estimated/receipt_estimate로 사용한다. v2 응답/후보 상세 표시 변경은 아래 정책을 따르며 실제 출발 시각은 F07-02 후속이다. F07-01b는 수정 완료조건(매핑/조회/명시적 수신 추정)으로 완료하고 원천 시각 강화/지원 범위를 F07-01c로 분리한다.
- F07-01b 운영 연결 구현/검증 <mention-date start="2026-10-13"/>: 신규 연결16개(9.167초)·최종 전체 백엔드283개(119.790초) 통과. 실제 격리 PostgreSQL/ASGI와 합성 경기 응답으로 검색 작업→메모리 근거→정류소/방향 매핑→본인GET→도착 초/unknown을 검증했다. 30m 초과/100m 이내·연속 정차 누락·복수/충돌·전송/중복JSON/크기/키/시간초과·소유권/fingerprint/재시작/용량/만료·60초 수신 기한/검색 기한 단축·병렬/10회 버킷·매핑 중 후보/검색 변경·DB 경로 무변경/원문 비노출을 확인했다. 실제 운영 키 연결 실조회는 이번0회이며 이전 공개 진단 성공을 새30m/연속 정책·GET 실검증으로 대체하지 않는다. 프로세스 메모리 만료는 사용을 즉시 차단하고 다음 접근에 정리한다. 신규 DB/DDL 없음·스키마0011/회원20/장소35/루틴12/산정0 유지. 서버health200·프론트200·비인증GET401 확인. 프론트 변경/시각 검증 없음. 원천 생성시각/최신성·실제 키 통합검증/지원 확대는 남아 F07-01b/F07-01 미완료다.
- F07-01b 실제 키 통합검증 준비 <mention-date start="2026-10-13"/>: backend/check_arrival_[connection.py](http://connection.py)는 동일 공개 판교역→성남시청 map_pin만 사용해 임시 auth_test UUID 스키마에서 합성 회원 로그인→실제 경로 검색/자동 매핑→본인 도착GET→동일GET 재조회를 검증하고 스키마/메모리를 정리한다. 카카오 지역 확인2회/경로1회+경기 매핑최대6회/도착1회로 총최대10회, 실패 시도 포함·고정2호스트 HTTPS/비표준포트·HTTP·타호스트 거부·리다이렉트 금지다. 요약은 상태/개수/호출횟수·원천/예측 유무·재조회 무호출/동일근거·검색 무변경만 출력하며 키/주소/좌표/정류소ID/차량번호/원문/쿠키는 출력하지 않는다. 외부 요청 없는 신규6개1.793초 검증으로 격리/정리·원문 비노출/실패횟수·예산/대상/선택/캐시를 확인했다. 실제 키 통합 실행은 아직0회, 기존 예산23/26회로3회 잔여이며 추가 최대10회 승인 대기다. 경기 공식 항목 매뉴얼을 재확인했고 queryTime=정보요청시간/행별 생성시각 계약 없음은 계속 제약이다. 서울 지하철 공식 출력 recptnDt는 생성시각이라고 명시하지만 지원 역/방향/시간대·전송 정책은 미검증이며 자동 대체하지 않는다. 현재 환경에서 해당 공식 호스트에 키/역명 없는 HTTPS HEAD1회는3초 timeout, HTTP로 전환하지 않았다. F07-01b/F07-01 전체 미완료·계산 차단 유지, 앱 API/계산/저장 변경 없음.
- F07-01b 실제 키 통합검증 결과 <mention-date start="2026-10-13"/>: 사용자 추가10회 승인 후 임시DB의 실제 키 검증을6회 실행했으나 HTTP200 mapping_required/후보0/source_status=unknown·생성/예측시각 없음·guidancefalse·종료1이었다. 이후 승인누적36회 중29회 사용/7회 잔여 범위로 안전한 단계 진단을 보완해 최대7회 재검증했고 실제6회를 사용했다. stage=route_stations/reason=ROUTE_SEQUENCE_UNCONFIRMED·station_count=1/route_count=1/matched_count=0이었다. 이 복합 검사는 전체 연속 정차 이름/양끝30m/공식 방문scope를 함께 대조하므로 어느 개별 조건이 실패했는지는 아직 단정하지 않는다. 두 번 모두 재조회 무호출/동일근거·저장검색 무변경을 확인하고 임시스키마/메모리를 정리했다. 도착 항목까지 연결된 성공으로 표시하지 않는다. 이번12회+이전23회=누적35회/승인36회·1회 잔여다. 내부 resolve의 선택적 diagnostics는 고정 단계/사유/개수만 제공하고 공개API에는 노출하지 않는다. 관련 연결17개9.095초/도구6개1.629초 통과·이번 전체 회귀 재실행 없음. 런타임 GET 정책/응답/계산/저장 변경 없음·F07-01b/F07-01 미완료. 다음은 매칭 복합 검사 불일치의 개별 근거 확인 및 신뢰할 생성시각/공급자 확보다.
- F07-01b 매칭 불일치 분리 진단 <mention-date start="2026-10-13"/>: 진단 요청이 명시된 실패 사례에만 match_checks를 추가해 유효순번 노선/승하차 이름쌍/중간이름 순서/전체연속 이름/공식 방문scope 일치·좌표결측/30m초과/정류소ID결측/통과쌍 개수를 구분한다. detail_reason은 고정 사유(SEQUENCE_DATA_UNCONFIRMED/ENDPOINT_NAMES_UNMATCHED/INTERMEDIATE_ORDER_UNMATCHED/VISIT_SCOPE_UNMATCHED/STOPS_NOT_CONTIGUOUS/COORDINATES_UNCONFIRMED/COORDINATE_LIMIT_EXCEEDED/STATION_IDENTITY_UNCONFIRMED/MATCH_AMBIGUOUS/MATCH_CHECKS_PASSED 등)만 반환하며 이름/좌표/공공ID는 반환하지 않는다. 최대200개정류소/노선당500행을 넘으면 상세진단만 DIAGNOSTIC_SIZE_LIMIT으로 생략한다. 공개GET/운영 매핑 정책/결과·캐시/기한·매칭 수용 여부는 바꾸지 않으며 추가 공급자 호출도 없다. 신규7개1.273초·연결17개9.280초·도구6개1.634초 통과, 수정 후 실제 키 재조회0회라 실제 불일치 원인은 아직 확인되지 않았다. 기존 누적35/승인36회·1회 잔여로 전체 재조회 부족, 동일 공개 경로/키/공식 HTTPS 추가최대8회로 진단 재검증을 준비했다. F07-01b/F07-01 미완료/원천 최신성 차단 유지.
- F07-01b 불일치 원인 실확인 <mention-date start="2026-10-13"/>: 사용자 추가최대8회 승인 후 동일 공개 경로/임시DB를6회 조회했다. station_count=1/route_count=1/matched_count=0, detail_reason=STOPS_NOT_CONTIGUOUS였다. 유효순번노선1·승하차 이름쌍2·중간이름 순서쌍2·공식 노선/승차정류소/방문순번 일치쌍2지만 연속 이름쌍0/공식방문연속쌍0이었다. 따라서 공공 목록에 카카오 목록 사이의 추가 정류소가 있는 형태를 현재 전체연속 목록 필수 정책이 차단한 것이 확인됐다. 좌표/식별 검사는 연속쌍에만 적용되므로 관련0개를 좌표/식별 통과로 해석하지 않는다. 동일GET 재조회 무호출/동일근거·검색무변경true, HTTP200 mapping_required·도착후보0/원천unknown/guidancefalse·종료1 유지. 코드/테스트/API/계산/저장 변경 없음. 수정 방향은 연속목록 필수 정책 재검토와 공식 방문순번/모든 제공이름 순서/양끝30m/회차·반복 방문·방향/유일성 검증 유지이며 아직 제안/미구현이다. 누적41회/승인상한44회(기존36+추가8)·3회 잔여, 이는 검증 승인용 횟수이며 공급자 잔여쿼터/요금은 확인하지 않았다. F07-01b/F07-01 전체 미완료·원천 생성시각 제약 유지.
- F07-01b 추가 정류소 처리 정책 <mention-date start="2026-10-13"/>: 사용자 진행 승인에 따라 카카오 제공 정류소 이름을 모두 같은 순서로 포함하면 공공 목록의 추가 정류소를 허용한다. 이름 별칭/일부 제공이름 누락/역순은 허용하지 않는다. 양끝30m·공식 노선/승차정류소/방문순번·연속 공공순번/유일하고 일관된 회차·같은방향/공식 routeDestId/실제 끝 정류소·최종 유일 후보 검증은 유지한다. 반복 하차방문 후보는 같은 유일 노선의 상세1회를 조회해 각각 회차/방향을 검사한 뒤 유일성 판단, 회차를 넘는 후보는 제외한다. 서로 다른 공공 노선이 둘 이상 매칭되거나 방향 검증 후 두 후보가 남으면 mapping_required다. 자원 보호를 위해 방문 후보32쌍 초과는 전체 미확인으로 두고 일부를 선택하지 않는다. 매핑 버전은 gbis.station-scope.v2.30m.ordered, 기존 GET 입력/응답 필드는 유지하되 제공목록 상세도가 다른 검증 경로가 새로 조회될 수 있다. 상세 진단은 제공이름 순서가 일치한 공식방문 쌍에서 좌표를 확인하며 연속성은 참고 개수로 남긴다. 조회/TTL/캐시/키 비노출·원천 생성시각unknown/출발 계산 차단 정책은 유지한다. 구현/검증 결과와 실제키 확인 여부는 후속 기록으로 구분하며 F07-01b 전체 완료가 아니다. 구현 완료: 공유 순서매칭/32후보 상한·동일 노선 상세1회 후 방향/유일성 검사·비연속 좌표 진단과 본인GET 연결을 수정했다. 신규9개(0.013초)·진단7개(1.183초)·연결17개(9.303초) 통과, 최종 전체 백엔드306개(115.947초) 통과. 추가 정류소/회차 뒤 반복방문 제외 후 유일 후보의 본인GET→도착 어댑터 연결은 합성 응답/격리DB로 확인했다. 변경 후 실제키 호출0회이며 실연결/원천 최신성/지원 범위는 미확인, 승인횟수41/44회·3회 잔여는 요금/공급자쿼터가 아니다. F07-01b/F07-01은 미체크 유지.
- F07-01b 실제 본인조회 연결 검증 <mention-date start="2026-10-13"/>: 사용자 완료 요청에 따라 앞서 제시한 공개 판교역→성남시청/저장 키/공식 HTTPS 최대8회 검증을 실행했다. 실제8회·종료0/HTTP200·connection_verified, MAPPING_CONFIRMED(station_count=1/route_count=1/matched_count=1). 본인GET의 매핑/도착 조회 연결과 재조회 무호출·동일근거·저장검색 무변경이 확인됐다. arrival_status=insufficient_data/source_status=unknown·후보0·생성시각/예측시각 없음·guidancefalse이며 최신 도착/출발 계산 성공으로 해석하지 않는다. 경기 공식 항목 명세를 재확인해 queryTime은 정보요청시간이고 행별 생성시각 계약은 없음을 확인했다. 사용자 완료 요청으로 추가5회의 제시된 검증 범위를 실행해 승인 누적49회/실제49회·잔여0, 이는 요금/공급자 쿼터가 아니다. 기존 API/계산/보관/키 비노출 정책 유지·구현 변경/새 테스트 없음. 기존 전체306개 통과 기록을 유지하되 이번 재실행으로 표시하지 않는다. F07-01b의 기존 완료조건(원천 시각/최신 도착 연결)은 충족되지 않아 미체크 유지하며, 매핑·조회 연결과 원천 최신성 검증의 TODO 분리 제안은 사용자 결정 대기다.
- 수신 기준 추정 사용자 결정 <mention-date start="2026-10-13"/>: 사용자는 생성시각 확보/공급자 지연 상한/수신 기준 추정 방법을 비교한 뒤 추천한 수신 기준 추정 진행과 선택 이유 기록을 승인했다. 이유는 경기 API가 생성시각을 제공하지 않아 엄격한 생성시각 필수 조건으로는 개발/출발 안내 진행이 차단되며, 명시적 추정·60초 재조회·120초 만료로 한계를 알리면서 실제 조회를 활용하기 위함이다. 재조회/여유5분은 원천 지연을 증명하거나 제거하지 못한다. queryTime/수신시각을 generated_at으로 기록하지 않는다. 캐시는 최초 received_at/추정도착/만료를 유지하며 응답마다 remaining_seconds와 후보 유효성을 재평가한다. 재조회 실패502/503/504 시 원래 캐시의 시각/만료를 갱신하지 않는다. 활성 후보 상세에서 첫 진입/60초/탭 복귀 조회, 숨김 중지·이탈 취소·중복 방지, 화면에 수신 기준 예상/조회 경과/갱신실패/만료/빈후보/미지원/매핑미확인을 표시한다. 검색 만료/장소 변경/인증실패는 기존 숫자를 즉시 제거하고 재검색/로그인을 안내한다. 공급자 생성시각/공식 지연 상한 검증은 F07-01c 후속이며 출발/여유 숫자는 유효한 개인 접근 근거가 있어야 F07-02에서 계산한다. 이번 정책과 v2/API/화면 구현·검증은 결과 기록을 따른다. 구현/검증 완료: 서버 v2 수신 ETA·remaining_seconds/캐시 재평가·기한 비연장·생성시각/시계 오류 우회 금지, 후보 상세 추정 표시/진입·60초·탭 복귀 조회·숨김/이탈 중지/오류·만료 상태를 구현했다. 최종 백엔드314개106.538초·프론트182개9.38초 및 빌드407ms 통과, 합성 브라우저1280×800/390×844에서 추정 카드/줄바꿈/넘침·만료 숫자 제거 확인. 이번 실제키0회(직전 실제8회 연결/후보0과 구분), 공급자 지연은 미확인이다. 사용자 변경 완료조건에 따라 F07-01b 매핑·조회·수신추정은 완료, F07-01c 원천 시각/갱신지연·지원 확대 및 F07-02 출발 계산은 미완료, F07-01 전체는 미체크다. 선택 이유/초기 실패 수정/실제 검증 범위는 `development_log.md`에 기록했다.
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
- GET /health·공통 HTTP 오류/request_id·React 서버 연결, 17절 기본 회원 인증 및5.1.1절 F03-01 장소 검색/저장/본인 목록·상세는 구현됨. 장소 위치/출입구 수정과 map-config/위치 확인은5.1.2절 구현. 이름 수정/삭제는5.1.3절 구현, 현재 위치/지도/저장 장소 선택 및 POST /origin-validations는5.2.1절 구현. 위치 수동 확인은5.2.2절 구현, GPS 수치/자동 일치 판정은 보류. depart_now 경로 후보/본인 작업 조회는5.2.3절 구현, AI/실시간/목표 도착·비교 화면/약속 API는 미구현이다.
- [ ] 실제 OpenAPI 스키마와 요청·응답 계약 비교는 구현 후 수행한다.
- [ ] 자동화 검증은 계산 경계값·소유권·이벤트 중복·개인화·공급자 실패를 우선한다.
## 10. 결정해야 할 사항
- 메일 소유 확인·메일 복구와 공급자/발송 준비는 후순위. 첫 회원 인증은17절의 중복 확인·가입/로그인·세션을 따른다.
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
테이블 설계와 Alembic 기반(F00-05b)을 완료했다. 개발 DB 현재 head는0005_place_management(2026-10-07)이며0002_member_auth의 회원 인증5개 테이블 및 saved_places/place_searches/place_creation_keys가 적용됐고 saved_places 핀/설명 컬럼 및 place_location_confirmations를 추가했다. 기존 장소 보존·0003↔0004 왕복을 추가 검증했다. 임시 스키마에서 head 적용·중복 적용·되돌리기·재적용, 회원/장소 소유권·만료·멱등 검증을 수행했다. 나머지 경로/루틴/관측/약속 테이블은 미생성이며 관련 FK/삭제/보관 검증은 해당 기능에서 진행한다. F03-03에서 location_version 초기화·장소 삭제 및 생성 재시도 키의NULL 삭제 표시를 추가했다.
## 15. 마이그레이션 실행 기반
2026-10-02: Alembic 1.20.0과 SQLAlchemy 2.1.1 설치 및 버전 고정. 루트 alembic.ini와 backend/migrations에서 명시적 변경 파일을 관리하고 backend/[migrate.py](http://migrate.py)로 실행한다. DB 접속 설정은 기존 비공개 .env/프로세스 설정을 재사용하며 앱 시작 시 자동 변경하지 않는다. 초기 0001_baseline은 업무 DDL이 없는 기준점이다. 상세 명령·한계는 로컬 [migrations.md](http://migrations.md)에 기록했다. 업무 테이블과 인증 방식은 별도 단계에서 확정한다.
## 16. 친구 약속·채팅 상세 API
- 문서 버전: 0.2 / 2026-10-06 / 대응 Notion API 버전: 0.26
- 상태: **상세 설계, 일부 구현**. 요청/응답 예시는 합성 데이터다. F12 코어: POST /meetings, GET /meetings, GET/PATCH/DELETE /meetings/\{meeting_id\}, POST /meetings/\{meeting_id\}/confirmations(직접 목적지만), POST /meetings/\{meeting_id\}/transitions, POST /meetings/\{meeting_id\}/invites, DELETE /meetings/\{meeting_id\}/invites/\{invite_id\}, POST /meeting-invite-previews, POST /meeting-invite-acceptances, DELETE /meetings/\{meeting_id\}/members/me는 구현·검증 완료(2026-10-14). 추천 기반 확정, 개인 출발지, 출발 안내, 공유, 채팅, WebSocket은 미구현이다.
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
만료/철회/존재하지 않는 초대는 모두 404 INVITE_UNAVAILABLE. 같은 사람이 이미 수락한 같은 토큰을 재요청하면 아직 활성 참여 중일 때 200 반환, 다른 사람은 404. 신규 수락과 만석 검사는 약속 행 잠금 안에서 처리한다. 동일 사용자는 member가 중복 생성되지 않는다. 초대 발급의 멱등 응답 재현을 위해 필요한 token 응답은 만료/소비/철회 전까지만 암호화된 응답 캐시에 보관한다. 영구 초대 레코드에는 해시만 둔다. 캐시 정리 후 같은 키에는 409 INVITE_RESPONSE_EXPIRED를 반환하며 새 발급이 필요하다. F12 현재 구현은 암호화 응답 캐시 없이 같은 키·같은 본문 재요청도 409 INVITE_RESPONSE_EXPIRED로 응답하며 새 키로 재발급해야 한다. 탈퇴 후 재참여는 새 초대를 요구한다.
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
확정 시 추천과 후보의 약속 소속, 참여자·출발 정보 버전, 만료, target_arrival_at 일치를 확인한다. 직접 지정 목적지는 서버에서 유효성을 확인한다. F12 구현 기준: name은 1\~100자(앞뒤 공백 제거), 위도 -90\~90·경도 -180\~180이며 provider와 place_ref는 null만 허용한다(장소 연동은 후속). timezone은 Asia/Seoul만 받고 target_arrival_at은 서버 시각보다 미래여야 한다. 새 확정 revision은 기존 개인 안내를 stale로 만들고 출발 공유 ETA를 무효화한다.
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
## 17. 이메일·비밀번호 회원 인증 — 첫 버전
사용자 변경(2026-10-06): 메일 소유 확인은 후순위다. 정규 이메일 중복만 확인해 가입시키며 이메일을 실제 소유한다고 표현하지 않는다. 가입 즉시 active, 자동 로그인 없음. 확인메일/복구메일/메일 토큰/outbox/pending 계정 및 메일 공급자 준비는 현재 구현 범위에서 제외한다.
### 입력·저장
- email: trim 후 최대254자, ASCII 이메일 형식, 전체 소문자 정규화. 점/플러스 주소는 합치지 않는다. DB UNIQUE로 동시 가입도 중복 방지, 중복409 EMAIL_UNAVAILABLE. 기존 회원 비밀번호를 덮어쓰지 않는다.
- password:15\~128 Unicode 코드 포인트, 공백/붙여넣기 허용, trim/절단/대소문자 변환 금지. Argon2id(memory19456KiB/time2/parallelism1) 해시 저장. 최소 일반 비밀번호 차단 목록을 적용하며 전체 유출 목록 연동은 후순위다.
- display_name:trim 후1\~30자. 첫 프로필:walking_preference=normal,walking_duration_factor=1.0,first_boarding_buffer_seconds=300,transfer_buffer_seconds=120,route_preference=balanced,timezone=Asia/Seoul,version=1.
- users/auth_credentials/user_profiles/auth_sessions/auth_rate_limit_buckets를 사용한다. 메일 확인 상태/토큰/메일 큐 테이블은 만들지 않는다. 회원/자격정보/프로필을 동일 트랜잭션으로 생성한다.
### 세션과 CSRF
- 서버 저장 세션:256비트 이상 난수, DB에는 SHA256 해시만 저장. 로그인7일 절대 만료·미사용24시간, 로그인 전 임시 세션15분. 인증 세션은 회원 active 상태를 검사한다.
- 운영 쿠키 __Host-timeisnow_session,Secure,HttpOnly,SameSite=Lax,Path=/,Domain 없음. 개발 HTTP 쿠키 timeisnow_dev_session,Secure=false. AUTH_ENV=development/production 및 고정 AUTH_PUBLIC_ORIGIN 설정; 운영 HTTPS 필수, 개발 origin은 [localhost/127.0.0.1만](http://localhost/127.0.0.1만) 허용. 잘못된 설정/DB 장애는503 SERVICE_UNAVAILABLE.
- GET /auth/csrf는 임시/기존 세션의 CSRF 토큰을 교체해 반환한다. CSRF 원문은 프론트 메모리에만 유지하며 서버에는 해시를 저장한다. 새로고침 시 재조회.
- 가입/로그인/로그아웃 POST는 Origin 및 X-CSRF-Token을 검사, 실패403 CSRF_INVALID. 운영은 설정된 HTTPS Origin과 정확히 일치해야 한다. 개발은 AUTH_PUBLIC_ORIGIN에 설정된 동일 HTTP 포트의 `localhost`와 `127.0.0.1` 두 origin만 허용하며 기본80 포트 표기는 정규화한다. 다른 포트·외부 도메인·Origin 누락/null은 거절한다. CSRF 토큰·세션 쿠키 검사는 유지하며 요청 Host/전달 헤더로 허용 origin을 만들지 않는다. 로그인 시 기존 세션 삭제/새 세션·CSRF 교체, 로그아웃 시 세션 삭제/쿠키 제거.
- 모든 인증 응답 Cache-Control:no-store, 공통 data/meta 또는 error/meta 및 요청 ID. 비밀번호/쿠키/CSRF/이메일 원문을 로그에 남기지 않는다.
- 계정 화면의 가입·로그인·회원 조회·로그아웃 실패 안내에는 해결에 필요한 메시지만 표시하고 요청 ID는 표시하지 않는다. 요청 ID의 API 응답·클라이언트 내부 보존·서버 로그 연결은 유지한다.
### API
<table header-row="true">
<tr>
<td>방식·경로</td>
<td>입력</td>
<td>성공</td>
</tr>
<tr>
<td>GET /auth/csrf</td>
<td>없음, 비로그인 가능</td>
<td>200 \{csrf_token,expires_at\} + 쿠키</td>
</tr>
<tr>
<td>POST /auth/register</td>
<td>임시/기존 세션+CSRF; \{email,password,display_name\}</td>
<td>201 \{user_id\}; active 회원, 자동 로그인 없음</td>
</tr>
<tr>
<td>POST /auth/login</td>
<td>임시/기존 세션+CSRF; \{email,password\}</td>
<td>200 \{user_id,session_expires_at,csrf_token\} + 새 쿠키</td>
</tr>
<tr>
<td>GET /me</td>
<td>로그인 쿠키</td>
<td>200 \{user_id,display_name,profile\}; email_verified 없음</td>
</tr>
<tr>
<td>POST /auth/logout</td>
<td>유효 세션+CSRF; \{\}</td>
<td>204, 쿠키 제거. 임시 세션에서도204</td>
</tr>
</table>
이메일 중복409 EMAIL_UNAVAILABLE, 없는 회원/잘못된 비밀번호401 INVALID_CREDENTIALS, 로그인 없음401 AUTH_REQUIRED, 만료401 SESSION_EXPIRED, 잘못된 입력422 VALIDATION_ERROR, 요청 제한429 RATE_LIMITED/Retry-After. 인증 POST는 일반 Idempotency-Key 응답 캐시에서 제외한다.
### 요청 제한·후순위
PostgreSQL 공통 버킷에 목적별 HMAC-SHA256(email/IP)만 저장하고 고정 UTC 창·행 잠금으로 동시 요청을 처리한다. AUTH_RATE_LIMIT_SECRET은32자 이상 별도 서버 비밀값. 가입IP5회/시간, 로그인IP30회 시도/15분·이메일5회 실패/15분. 창 만료 버킷은 인증 요청 시 정리, 영구 잠금 없음. 일반 로그에 버킷 키도 남기지 않는다.
메일 소유 확인·메일 복구·재인증·DELETE /me의 실제 인증/삭제 구현은 후속이다. 기존 삭제 영수증24시간·삭제 접수202 계약은 유지한다. 현재 메일 확인을 요구하는 업무 접근 차단은 적용하지 않는다. first release는 회원 중복 확인/가입·로그인·/me·로그아웃까지다.
### 구현 상태
F02-01 가입·로그인, F02-02 회원 조회·로그아웃, F02-05 초기 프로필 저장 구현 완료. PostgreSQL 마이그레이션과 임시 스키마 통합 검증·React 계정 폼·데스크톱1440×900/모바일390×844 실제 화면 확인. 로그인/로그아웃·중복409/요청 ID 확인. 메일 관련 준비 파일·Compose 서비스는 복구/제거, F02-00 메일 인증 준비는 후순위다. 첫 가입의 이메일 소유 확인·복구·업무 데이터 API는 미구현. 사용자가 검토 후 MR 생성/병합한다.
- 실제 최종 검증: 백엔드56개(인증15개·마이그레이션 왕복 포함)·프론트25개 및 빌드/pip check 통과. 임시 auth_test/migration_test 스키마 정리, 브라우저용 합성 계정 삭제 확인. 실제 `.env` 키 비노출/Git 제외. 개발 DB head=0002_member_auth. StrictMode 재마운트와 DB에서 읽은 쿠키 만료시각 UTC 변환 오류를 실제 화면에서 발견해 수정/회귀 검증.
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
- 신규 POST /api/v1/schedule-interpretations. 로그인·CSRF 및 공통 응답/요청 추적 규칙 적용. 일정 저장 API와 분리한다.
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
- 목록 기본20/최대100·멱등 결과24시간·자연어 입력1\~1000자/서명 컨텍스트 최초발급10분 확정. 기존 소유권/참여 권한·버전·날짜 검증 유지. 첫 회원 인증/세션/요청 제한은17절, 메일 인증/발송 준비는 후순위다.
- 실행 로그14일, 개인 이동/품질 이력90일, 장소/루틴/현재 프로필은 삭제/탈퇴까지 유지. 원문/키/상세 위치 일반 로그 제외. 표본/관측/산정 연결 이력은 함께 청소하고 과거 예측을 덮어쓰지 않는다.
- 만료 사용/노출 즉시 차단·기간 청소 매일. 명시 삭제/탈퇴는 즉시 접근 차단 및 기존202 작업으로 사본 정리, 완료 목표24시간·실패 재시도/failed 표시. 향후 백업 최대7일 순환·복원 시 삭제 기록 재적용. 실제 청소/백업 실행은 미구현이다. F03-03 현재 장소 단건 삭제는 현 저장소에서 트랜잭션 내 물리 삭제204로 완료한다. 독립10분 검색/확인은 기존 만료 정책, 삭제된 생성 키는24시간 최소 해시/키만 유지한다.
### D04 첫 출시 알림
- 첫 출시는 반응형 모바일 웹의 활성 화면 출발 카드/카운트다운/상태 안내. 백그라운드 푸시/예약 알림·GPS/센서 자동 출발 감지는 첫 출시 제외하고 후속 검토. 새로운 푸시 등록/발송 API 없음, 수신 보장 표현 없음. 사용자 수동 출발/탑승 확인과 약속의 열린 화면 REST/WS 갱신 유지.
### D05 약속 확장
- 최대2명(주최자 포함)·혼자 사용 가능, 통근 핵심 이후 확장. 제목1\~100자·텍스트채팅1\~1000자, 수정 없음/본인 삭제 유지. 초대 활성1개/약속·24시간·1회 수락, WS 티켓30초·1회. 추천 최대3개·5분 및 입력/동의/revision/참여자 변경 즉시 무효화.
- 공유 기본꺼짐·약속별 본인 선택·활성 참여자만 요약 접근. 종료/취소/철회 중 이른 때 및 목표시각6시간 후 자동 종료. 공유 ETA는 계산후120초 및 교통근거 만료 중 이른 기한. 기존 REST/WS 소유권·정정·종결 오류 유지.
- 채팅10회/10초(사용자·약속), 추천3회/분(약속), 초대 미리보기10회/분(사용자), 초과429+Retry-After 확정. WS ping25초/무응답60초 유지.
- 공동 약속/채팅은 completed/cancelled 후30일. draft 마지막 사용자 변경후30일 미사용 삭제. confirmed 목표시각6시간 후 completed 자동 정리하되 실제 참석/도착 판정 아님. 재전송 이력24시간. 본인 약속탈퇴 시 개인 입력/공유 종료·정리, 기존 공동 메시지는 탈퇴한 참여자로 표시. 계정탈퇴는 본인 메시지 본문도 삭제, 주최자 탈퇴는 취소 후 다른 활성 참여자30일 열람. 개인 trip은 연결해제후90일 정책.
### 계약 영향·완료 기준
- 기존 경로/응답 객체 유지, 설정 상한·만료·공유 ETA120초·자동 종료/삭제·출시 알림 범위가 변경/확정됐다. 아직 서비스가 미구현이므로 배포된 클라이언트 마이그레이션 없음. 422/404/409 등 기존 오류 사용, 소유권·동시 수락·기한 경계·삭제 사본 검증은 구현 시 수행한다.
- 사용자 요청으로 F01 별도 검증 삭제, 메일 인증/발송 준비 F02-00은 후순위. F02-01 가입·로그인, F02-02 회원 조회·로그아웃, F02-05 초기 프로필 완료. F02-04는 /me와 장소 생성/조회/수정/삭제 소유권 확인, 업무 데이터 소유권 검증은 각 API 구현에서 진행한다. F03-04 main0402d67·R01 mainca8cd93 병합 확인, F03-01\~04 구현/검증 완료. F03-05a 수동 확인은main8b4b40b에 병합 완료다. GPS 수치/자동 일치 판정은 보류한다. F04-01은 main0402d67에서codex/journey-search로 시작해최신main8b4b40b를통합한뒤구현/검증, F04-01은main9670281에병합완료, F04-02는main63674ac에병합완료. F04-03은main4f94af1에병합완료, F04-04는사용자요청으로보류. F04-05는codex/journey-unavailable에서F04-03을통합해구현/검증했다. 사용자MR/병합 후 다음F05-01 도보근거수집이며 미확인물리근거를확정값으로채우지않는다.
## 변경 이력
- <mention-date start="2026-10-14"/> v0.80: F07-06b의 수동 출발 확인 기반을 마련하기 위해 루틴 유효 안내에 nullable guidance_id 토큰 추가, 기존 POST /trips 초안 입력을 유지한 불변 안내/세션·수동 departed 저장/본인조회·취소 구현. 생성과 출발 신고 분리·24시간 멱등키·90일 이력/기한차단·시각/구간/중복·현재 버전 재검사·출발 접근 불가 생성 차단·재시도/취소 화면 동기화. 기존 안내 클라이언트는 nullable필드 추가와 호환. 전체 백엔드406개/프론트242개 및 최종 관련검증·빌드·합성PC/모바일 완료, 절반경과 정책과전체F08은후속.
- <mention-date start="2026-10-14"/> v0.79: 접근 불가능한 첫 차량만 계산해 시간부족으로 종료하던 문제를 해결하기 위해 제공된 다음 접근 가능 차량을 선택하는 F07-06a 구현. 기존 응답 필드/TTL/수신·권한 유지, 선택 차량·출발/환승/목표 숫자는 재계산하고 NEXT_REACHABLE_VEHICLE 고정사유 추가. 전체 백엔드394개/프론트231개·빌드·합성 PC/모바일 검증. 실제 이동/수동 departed API 선행이 없어 절반 경과 규칙F07-06b와전체06은미완료, 원천정보 없는 노선 대응은사용자지시후속보류.
- <mention-date start="2026-10-14"/> v0.78: F12 일회성 약속 코어 REST(생성/목록/상세/수정/직접 목적지 확정/상태 전이/삭제 202 job/참여 탈퇴)와 초대 발급/철회/미리보기(사용자당 10회 분)/수락을 구현·검증. meetings·meeting_members·meeting_revisions·meeting_invites·meeting_idempotency_keys·jobs 신설(0013)과 /jobs 조회의 약속 삭제 작업 처리 추가. 초대 응답 캐시 없이 같은 키 재요청은 409 INVITE_RESPONSE_EXPIRED(새 키로 재발급). 추천 기반 확정·개인 출발지·출발 안내·공유·채팅·WS는 미구현. 구현 검증: 백엔드 358개 테스트 통과, 직접 외부 키 호출 0회.
- <mention-date start="2026-10-14"/> v0.78: 선택루틴의오늘목표·유효첫승차/전체환승/마지막도보 기반 목적지ETA·목표차이·충족추정/늦음/미확인/지난목표/만료 계약추가. first.departure.v1 nullable평가추가·기존필드유지/새조회·DDL·AI없음. 날짜정책은수동선택오늘기준구현정책이며미래예약/대체후보는후속. 구현검증은후속기록.
- <mention-date start="2026-10-14"/> v0.77: 루틴누락접근을검증경기승차좌표와카카오도보1회로보완·양끝/시간/경로검증·검색한정메모리/계수재계산·기한/전체호출상한/사유계약추가. first.departure.v1 근거종류/시각필드추가·기존계산/새DDL·AI없음. 구현검증완료: 지원경기BUS 루틴누락접근보완·백엔드375개/프론트222개·빌드·합성PC/모바일, 직접실키/AI0회. 검증개인도보·미지원매핑/목표도착은후속.
- <mention-date start="2026-10-14"/> v0.76: 사용자화면의 이전준비중문구수정·접근누락/안전한매핑사유구분·유효첫출발 카운트/현재기준 정류장여유 정책추가. 기존v2 reasons 허용코드추가만·새조회/키실호출/DDL/AI없음. 구현검증완료: 백엔드359개·프론트218개/관련33개·빌드·합성PC/모바일. 접근누락복구F07-02a-2는설계미정/미완료, 실제키/AI0회.
- <mention-date start="2026-10-14"/> v0.75: 사용자담당분리·루틴최신검색/유일저장노선선택/첫출발연결 API·버전/기한/본인검사·300초재검색/60초도착갱신·실패숫자제거계약 추가. 기존후보계약/루틴guidance초안유지·새DDL/AI없음, 검증개인도보연결은후속. 구현검증완료: 백엔드354개·프론트212개/빌드·합성PC/모바일, 실제키0회·새DDL없음. 루틴최신출발은a-1완료, 검증개인도보/목표도착은미완료.
- <mention-date start="2026-10-14"/> v0.74: 기존first-departure의선택적버스환승검사·후속leg메모리근거/검증매핑·최소승차/현재제공후보선택·불가/미확인/만료·동일캐시/원래기한·20초/호출제한과프로필검사 계약추가.10월21일채팅마감및실사용/약속·참여자/채팅우선순위를기록,기존첫차량필드호환/새DB·AI없음. 구현검증완료: 지원경기버스순차검사·백엔드343개/프론트199개·빌드·합성PC/모바일,실제키0회/새DDL없음.미지원·부족unknown/원천시간강화와루틴·약속·채팅은후속.
- <mention-date start="2026-10-13"/> v0.73: 사용자 승인 공급자 접근 도보×개인계수 추정·기본여유300초로 F07-02 후보 예상출발 계산 계약 추가. 본인 first-departure GET/프로필계수컬럼/호출전후버전·기한검사·도착캐시공유/부족·음수여유·후속범위 구분. 기존 /me.profile에계수필드추가·routine guidance초안은유지하며 구현/검증결과는후속기록. 구현/검증 완료: 백엔드329개·프론트196개/빌드·합성PC/모바일·0012 보존 적용/서버 확인, 실제키0회·원천/보행/정확도 미확인. F07-02 후보 계산 완료·루틴 자동갱신은02a/환승 이후후속.
- <mention-date start="2026-10-13"/> v0.72: 사용자 승인으로 생성시각 검증/수신 기준 추정 정책을 구분했다. arrival.evidence.v2/status estimated/timing_basis/remaining_seconds·수신 ETA·60초 재조회/120초 만료·캐시 경과 재평가·실패 기한 비연장, 화면 추정/조회경과 표시와 선택 이유 기록. 원천 최신성 unknown 유지·강화는 F07-01c, 개인 접근/여유 출발 계산은 F07-02. 기존 클라이언트는 v2 enum/필드/valid_for_guidance 의미 변경 대응 필요. 구현/검증: 백엔드314개·프론트182개/빌드·합성PC/모바일 통과, 이번실제키0회·원천unknown 유지. F07-01b 수정 완료조건 완료/F07-01c 강화와 F07-02 계산 후속.
- <mention-date start="2026-10-13"/> v0.71: F07-01b 실제8회/HTTP200·유일 매핑/본인 도착 조회 연결·무호출 재사용·검색 무변경을 확인했다. 생성시각/사용 가능한 도착후보 없음·최신성unknown·출발 계산 차단 유지, 기존 완료조건 미충족/TODO 범위 분리 제안은 사용자 결정 대기. API/계산/보관 계약 변경 없음.
- <mention-date start="2026-10-13"/> v0.70: F07-01b 공공 중간 정류소 추가를 제공이름의 전체순서·30m·공식방문/회차/방향/최종유일성 검증으로 처리하도록 정책을 변경했다. 반복방문은 방향 후 유일성 평가·32후보 상한, GET 필드/캐시/시간/보관 유지·매핑 버전v2/원천unknown 유지. 구현/검증 완료 기록: 최종 백엔드306개 통과·합성 본인GET→도착 연결/안전 차단 확인, 변경 후 실제키0회·원천 최신성/실연결 미확인·전체 미완료.
- <mention-date start="2026-10-13"/> v0.69: 추가6회 실제 조회로 STOPS_NOT_CONTIGUOUS 원인을 확인했다. 제공이름 순서/공식 승차방문은 일치하지만 전체연속 목록 조건이 차단, 좌표 검사는 미실행. 수정 정책은 제안 상태, 기존 API/계산/저장 계약 유지·F07-01b 미완료.
- <mention-date start="2026-10-13"/> v0.68: F07-01b 미매칭을 이름/순서/연속성/방문scope/좌표/식별 결측의 안전한 개수·고정 사유로 분리했다. 신규7개 검증·수정 후 실제키0회, 운영 정책/공개API/계산/저장 계약·호환성 변경 없음. 추가 실진단 승인 대기/전체 미완료 유지.
- <mention-date start="2026-10-13"/> v0.67: F07-01b 실제 키6회+진단 재검증6회에서 mapping_required·정차목록 매칭0을 확인했다. 재조회 캐시/DB 보존은 확인했으나 도착 연결/최신성은 미완료, 정책을 완화하지 않았다. 내부 안전한 단계 진단만 추가, 공개 API/계산/저장 계약·호환성 변경 없음.
- <mention-date start="2026-10-13"/> v0.66: F07-01b 격리 DB 실제 키 통합검증 도구/최대10회·신규6개 검증과 원천 시간 제약/대체 공급자 전송 미확인을 기록했다. 실조회 승인 대기·경기 unknown/출발 계산 차단 유지, 앱 API/계산/저장 계약·호환성 변경 없음.
- <mention-date start="2026-10-13"/> v0.65: F07-01b 경기 첫 버스 메모리 근거/30m·연속 정차/공식 방향 매핑·본인 GET 연결·60초 중복 제한 정책을 추가했다. 기존 GET 입력/응답 필드 유지, 근거가 검증된 신규 검색은 공급자를 조회할 수 있다. 원천 시간 unknown·출발 계산 차단/전체 미완료 유지.
- <mention-date start="2026-10-13"/> v0.64: 수정한 F07-01b 공개 방향 진단7회 실조회 성공·정류소/노선/순번/방향 일치·왕복 끝 ID 차이를 기록했다. 원천 생성시각/운영 매핑 연결 미확인과 F07-01b 미완료 유지. 앱 API/계산/저장·클라이언트 호환성 변경 없음.
- <mention-date start="2026-10-13"/> v0.63: F07-01b 공식 정류소 방향 scope와 실제 방향별 끝 정류소 대조로 단순 왕복 가정을 분리했다. 합성36개 통과·수정 후 실조회0회, 실제 방향/생성시각·운영 연결은 미완료. 앱 API/계산/저장 계약·클라이언트 호환성 변경 없음.
- <mention-date start="2026-10-13"/> v0.62: 사용자 추가8회 승인 후7회 실조회, 방향 실패 사유 SIMPLE_RETURN_ENDPOINT_UNCONFIRMED를 확인했다. 개별 실패 조건/실제 물리 방향·원천 최신성은 미확인, F07-01b 미완료 유지. 앱 API/계산/저장·클라이언트 호환성 변경 없음.
- <mention-date start="2026-10-13"/> v0.61: F07-01b 정류소 기반 후보 축소·호출 예산 강제와 실제7회/누적9회 결과를 기록했다. 유일 후보/도착 ID 일치는 확인, 방향·생성시각·운영 연결은 미완료. 앱 API/계산/저장 계약·클라이언트 호환성 변경 없음.
- <mention-date start="2026-10-13"/> v0.60: 사용자 승인 후 공개 경로 HTTPS2회 실조회 결과를 기록했다. 동명 후보12개가 한도6개를 넘어 중단, 방향/도착 실조회는 미수행이며 F07-01b 미완료 유지. 앱 API/계산/저장·클라이언트 호환성 변경 없음.
- <mention-date start="2026-10-13"/> v0.59: F07-01b 회차/종착 방향 진단과 합성 검증·실조회 승인 대기를 기록했다. 앱 API·저장·계산·클라이언트 호환성 변경 없음. 진단 후보와 운영 매핑을 구분하고 원천 최신성/F07-01 전체 미완료를 유지한다.
- <mention-date start="2026-10-13"/> v0.58: F07-01a 본인 후보 first-arrivals GET·검증된 경기 ID의 내부 HTTPS 어댑터·원천 unknown/120초 신선도/오류·호출 전후 검사 추가. 신규17개/백엔드238개·서버 확인, 기존 API/DB/프론트 유지. 실제 매핑/원천 시각·실조회 연결은 미확인으로 F07-01 전체 미완료를 유지한다.
- <mention-date start="2026-10-13"/> v0.57: F05-07 루틴 선택/후보 상세·조회 실패/만료 도보 상태 안내 추가. 신규19개/프론트167개·빌드1904모듈·데스크톱/모바일8화면 확인. 미실행 AI·근거 부족/역 내부/0초를 구분하며 확인되지 않은 출발 시각을 만들지 않는다. 사용자 흐름만 추가, API/계산/DDL/보관 호환성 유지. 실제 물리 근거/AI 생성·F07 출발 안내는 후속.
- <mention-date start="2026-10-13"/> v0.56: F05-06 같은 물리 근거의 계수/프로필 버전 변경을 서버 십진 재계산으로 처리. 원본 기준·기한 유지/부모 revision 연결·최초 AI 근거/멱등/혼합 후보 처리와0011 제약을 추가했다. GET source에 profile_recalculation 및 내부 estimates source를 추가하므로 해당 enum 소비자는 두 값을 처리해야 한다. 미확인 실제 근거/지도 연결·F09 학습·F07 출발 안내는 후속. 신규19개/백엔드221개·0011 격리 복구/개발DB 적용·서버 확인 완료.
- <mention-date start="2026-10-12"/> v0.55: F05-05 확인된 물리 식별자 기반 내부 전체/부분 캐시 재사용 구현. 신규18개/백엔드202개·0010 legacy 보존 왕복/개발DB 적용·기존 회원/장소/루틴 유지·서버 확인. 일시 ID 제외 조건 키/프로필 일치·원본 기한 유지·적중 호출 생략·최소 연결/멱등/동시 실행 정책을 추가했다. 공개 GET/프론트 호환성 유지, 계수 변경/실제 근거/출발 안내 연결은 후속.
- <mention-date start="2026-10-12"/> v0.54: F05-04 내부 검증 산정/품질 이력 저장 및 본인GET 상세 구현. 신규16개/백엔드184개 통과·0009 개발DB 적용/기존 행 보존·실서버 GET401 확인.30일/근거기한 유효·90일 이력·소유권/버전/불변/실패/동시 실행 정책 확정. 기존 계산/클라이언트 호환성 유지, 신규4테이블/GET 추가. 미확인 물리 근거의 유효 산정 저장 차단·조건별캐시/개인화/사용자서비스 연결은후속.
- <mention-date start="2026-10-12"/> v0.53: F05-03 내부 AI 산정 입력/응답·호출 차단·검산·실패/재시도 구현. 신규19개/백엔드168개 및 실제 합성1후보360초 검산 완료. max_output_tokens HTTP400을 출력 한도512로 해결. 기존 HTTP/DDL/계산/보관·클라이언트 호환성 유지, 현재 미확인 근거는 AI 전송 차단. 사용자 서비스 연결/저장·운영 품질은 후속.
- <mention-date start="2026-10-12"/> v0.52: F05-03 연결을 위한 F05-02 서버 내부 프롬프트 블록·버전 로딩과 검증 상태 추가. 기존 문구/프롬프트 버전·API/계산/보관/클라이언트 호환성 유지. 신규8개/백엔드149개 통과, 실제 AI 호출·품질 평가는 후속.
- <mention-date start="2026-10-08"/> v0.51: F03-02a 지도 선택 좌표를 다시 검색하지 않고 확인 ID로 저장/자동 선택하는 흐름 추가. POST /places source 기본search/map_pin 조건부 입력, 기존 검색/멱등 해시 호환 유지. 새 DDL 없음. 구현/검증 완료(백엔드134개·프론트148개/빌드·합성PC/모바일).
- <mention-date start="2026-10-08"/> v0.50: F05-01 선택 후보의 접근/환승/마지막 도보 근거·누락 조회 API 추가. 기존 공급자 근거만 구분하며 물리 범위 미검증·AI/재사용 준비 전 상태 유지. 기존 API/DDL/보관·클라이언트 호환성 영향 없음. 구현/검증 완료(신규7개/백엔드137개·서버 재시작).
- <mention-date start="2026-10-08"/> v0.49: F06-04 장소 위치/출입구 변경 후 루틴 확인 필요 상태 연동과 복구·최신 재조회 흐름 추가. 이름만 변경 시 유지, 이전 스냅샷/일정 보존. API 필드/DDL·기존 클라이언트 호환성 영향 없음. 구현/검증 완료.
- <mention-date start="2026-10-08"/> v0.48: 원하는 이동 방법의 후보를 첫 카드부터 확인하는 F04-03a 흐름 추가 및 구현·검증 완료. 기존 비교 기준·나머지 후보 유지, 방식별 무결과 안내. API/DB 변경 및 호환성 영향 없음. 프론트138개/빌드·합성 PC/모바일 확인.
- <mention-date start="2026-10-08"/> v0.47: 사용자 요청으로 루틴 등록 중 출발/도착 선택기의 장소 검색·명시 저장·저장 후 선택 반영 흐름을 추가했다(5.3.2, F06-03a). 기존 장소/출발지 검증/루틴 API를 재사용하며 경로·필드·인증·보관·계산·스키마 및 기존 클라이언트 호환성 유지. 구현·검증 완료.
- <mention-date start="2026-10-08"/> v0.46: F06-03 본인 목록(cursor/limit), 이름·경로 교체 PATCH, DELETE204·참조 없는 스냅샷 정리와 삭제 멱등 표시 계약을 확정했다. 저장 후 목록 누락과 가상 루틴 문제를 해결하기 위한 홈/내 루틴 실제 조회·로그인 상태 전환·수정/삭제 흐름이며 구현·검증 완료. 기존 일정 PATCH/저장 응답 호환 유지.
- 2026-10-07 v0.45: F06-02 루틴 요일·목표 도착 저장 계약을 추가하고 구현으로 표시했다. POST /routines에 weekdays(ISO 1\~7 필수)·target_arrival_local_time(HH:mm 선택) 입력을 추가하고 응답에 weekdays·target_arrival_local_time·timezone(Asia/Seoul 고정)을 포함했다. PATCH /routines/\{routine_id\}를 expected_version 기반 요일·목표 도착 일정 변경으로 F06-02 구현 표기했고 이름·경로 변경은 F06-03으로 유지했다. 기존 클라이언트 영향: POST /routines는 weekdays가 필수가 되어 weekdays 없는 기존 본문은 422다.
- 2026-10-07 v0.44: F06-01 POST/GET /routines 저장·상세 계약을 구체화하고 구현으로 표시했다. 검색 후보 journey_plans 스냅샷, 멱등·소유권·location_version 검증, 장소 삭제 시 루틴 needs_attention 연동을 추가했다. weekdays·목표 도착은 F06-02, 목록·수정·삭제는 F06-03으로 단계 표기했다. 3절 루틴 표와 장소 삭제 규칙을 갱신하고 5.3에 F06-01 계약을 신설, 기존 예시 절을 5.6\~5.8로 재번호했다. 기존 클라이언트 계약 변화는 없다.
- 2026-10-07 v0.43: 사용자 요청으로 F04-04 보류/F04-05 우선. 무경로·지점 연결 불가·환승 제한·지원 지역 밖·구간 정보 부족 구분과 복구 행동 추가, 환승 제외에 NO_ROUTE 중복 사유 제거. 기존 모델/권한/보관/기한 유지.
- 2026-10-07 v0.42: F04-03 출발/도착 직접 선택·접수/조회/중지/재시도/만료·후보비교/상세/미확인근거 화면흐름 추가. 기존API모델/권한/보관/입력비저장 유지, Retry-After 클라이언트노출 추가. AI/실시간·루틴/출발안내는 후속.
2026-10-07 v0.41: F04-02 journey.v1 공통 구간/도보 역할·승하차/정류장 순서·차량 세부분류·환승 연결/시간 분해 추가. 이전 후보는 조회 시 보강, 기존 필드/권한/작업/기한/입력 비저장 유지. 실시간/물리 방향·출입구/플랫폼·AI/화면은 후속.
2026-10-07 v0.40: F04-01 카카오 후보 조회의 비동기 상태/권한/멱등/만료/재시작 실패·최소 후보·GPS 입력 비저장 계약 구체화. depart_now부터 구현하고 AI/실시간/목표 도착은 후속 유지. 신규 API로 기존auth/장소/F03 계약 유지.
2026-10-07 v0.39: 사용자 결정에 따라GPS 경과시간/정확도/미래허용수치 및자동일치판정은보류. F03-05 수동확인부분으로current_location.location_confirmed/quality/place_match·user_confirmed 상태 추가, 기존false/pending·지도/장소/auth 호환 유지. 사용자의 확인과위치품질 보증·실제경로계산을구분한다.
- 2026-10-07 v0.38: F03-04 POST /origin-validations·단발GPS/거절·지도/본인 저장 장소 선택·600초 메모리 선택 추가. 현재 위치를근처저장장소로추정하지 않으며 실제 예시 안내와 분리. 시각/정확도 형식은전달하고 품질/일치 판정은F03-05 후속, 기존 장소/auth/경로 객체 호환 유지.
- 2026-10-07 v0.37: F03-03 label 수정/DELETE204·24시간 삭제된 저장 키 재생성 방지·location_version 구체화. 이름 변경은 위치/도보 근거를 유지, 기존 일반version 충돌 검사 유지. 미구현 루틴/산정 삭제 연결은 F04\~06 후속, 현 장소 삭제만 동기 완료.
- 2026-10-07 v0.36: F03-02 지도 설정/위치 확인·본인 장소 PATCH·사용자 출입구 설명·장소 버전 동시성 계약 구체화. 서울/경기 확인600초·원래 주소와 핀 법정동 구분. 기존 생성 선택 필드/응답 필드 추가로 F03-01 호환 유지. 실제 산정 무효화는 F04/F05 후속.
- 2026-10-07 v0.35: F03-01 검색 후보/소유권/10분 만료·생성 멱등/24시간·주소/키워드 및 지원지역·오류·목록 계약 구체화. 미구현 장소 생성에 검색/후보 ID 필수, 이름/주소 응답 추가. 기존 인증/health 호환성 영향 없음. 구현/검증 상태는 [todo.md](http://todo.md) 및5.1.1절을 따른다.
- 2026-10-07 v0.34: 사용자 요청으로 계정 오류 화면의 문의용 요청 ID를 숨긴다. 가입 입력 안내와 재시도 유지. API 경로·응답·서버 로그 및 기존 클라이언트 호환성 영향 없음.
- 2026-10-06 v0.28: F00-04 최소 JSON 요청 완료/예상 밖 오류 로그·필드 허용 목록·템플릿/미매칭 경로·LOG_LEVEL/실행 안내 추가. 기존 API 입력/성공/오류/ID 유지, 수집/보관 작업은 배포 단계. 민감정보/원문 스택 출력 없음.
- 2026-10-06 v0.29: 사용자 요청으로 F01-01 대표 사례 선정/검증 목록 정리를 작업 목록에서 삭제하고 다음 작업을 F01-02로 갱신. 기존 API 계약·계산 정책·클라이언트 호환성 변경 없음.
- 2026-10-06 v0.30: 사용자 요청으로 F01 데이터 공급자 검증 단계를 TODO·기능 목록에서 삭제하고 다음 작업을 F02-00으로 갱신. 기존 연결 이력은 보존, 응답 변환/오류 처리는 기능 연동에 포함. API 경로·필드·계산 정책·클라이언트 호환성 변경 없음.
- 2026-10-06 v0.31: F02-00 로컬 Mailpit/운영 Resend SMTP·고정 링크 origin·PostgreSQL HMAC 제한 버킷·pending 계정7일 정리 정책 선정. 인증 기능/운영 발송 미구현과 구분. 기존 API 경로/성공 응답 유지, 제한/보관 구현 기준 구체화.
- 2026-10-06 v0.32: 사용자 요청으로 v0.31 메일 준비 결정을 철회하고 메일 소유 확인/복구를 후순위로 이동. 가입 즉시active·중복409·확인 관련 응답/상태/테이블 제외, 세션/CSRF/기본 프로필/요청 제한 유지. 미구현 인증 계약의 필드 제거이므로 클라이언트는 새17절을 따른다.
- 2026-10-06 v0.33: 사용자가 [localhost:5173](http://localhost:5173)으로 앱을 열어 개발 설정127.0.0.1:5173과 Origin이 달라403 CSRF_INVALID가 발생한 문제 수정. 개발 동일 포트 loopback 두 주소만 호환, 운영 정확한 origin·CSRF/쿠키 유지. API 경로/필드/응답 변경 없음.
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
