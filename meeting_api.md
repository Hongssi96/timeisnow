# 지금이니? — 친구 약속·채팅 상세 API 초안

- 문서 버전: 0.3 / 2026-10-14 / 대응 Notion API 버전: 0.78
- 상태: **상세 설계, 일부 구현**. 요청/응답 예시는 합성 데이터다.
- F12 코어 구현·검증 완료(2026-10-14, migration 0013): POST/GET /meetings, GET/PATCH/DELETE /meetings/{meeting_id}, POST /meetings/{meeting_id}/confirmations(직접 목적지만), POST /meetings/{meeting_id}/transitions, POST/DELETE /meetings/{meeting_id}/invites(/{invite_id}), POST /meeting-invite-previews, POST /meeting-invite-acceptances, DELETE /meetings/{meeting_id}/members/me. 직접 목적지는 name 1~100자·위도 -90~90·경도 -180~180이고 provider/place_ref는 null만 허용하며, timezone은 Asia/Seoul만 받는다. 초대 응답 캐시는 미구현이라 같은 키 재요청은 409 INVITE_RESPONSE_EXPIRED다. 추천 기반 확정, 개인 출발지, 출발 안내, 공유, 채팅, WebSocket은 미구현이다.
- 기존 공통 계약과 함께 사용한다. 사용자 위임으로 D03~D05 수치/보관/공유 정책을 확정했다. [policy_decisions.md](./policy_decisions.md)와 Notion20절을 따른다. 구현 완료와 구분한다.
- 범위: 약속 생성·초대·중간 만남 추천·확정·개인 출발 안내·채팅·출발 공유·재접속.
- 친구 목록/친구 요청, 공개 신뢰 점수, 파일 채팅, 읽음 표시, 상시 위치 추적은 포함하지 않는다.

## 1. 공통·정책·권한

REST 접두사 /api/v1. 전부 로그인 필요. 로그인은 auth_api.md의 서버 세션·HttpOnly 쿠키 계약을 따른다. user_id/member_id로 요청자의 신원을 지정할 수 없으며 서버 인증값을 사용한다. 변경 REST에는 CSRF 방어를 적용한다.

성공은 {data,meta:{request_id,server_time}}, 오류는 {error:{code,message,details},meta}. 204는 본문 없이 X-Request-ID. 아래 성공 열은 data 내부다. 모든 날짜는 시간대 있는 ISO8601, 기간은 초, 거리 미터, ID는 문자열. JSON에서 ?가 붙은 설명은 선택/NULL 허용이며 실제 필드명에 ?를 붙이지 않는다.

생성/처리 POST에는 Idempotency-Key 필수(1~128 ASCII, 보관 24시간 확정). user+method+자원 ID 포함 경로+키로 중복 방지. 같은 본문은 최초 성공 응답 재현, 다른 본문은 409 IDEMPOTENCY_CONFLICT. 처리 중 재요청은 409 REQUEST_IN_PROGRESS 및 Retry-After: 1. 재시도 전에 현재 권한을 다시 검사한다. 메시지에는 별도 client_message_id 중복 방지도 적용한다. 읽기 성격 POST인 초대 미리보기와 매 연결마다 새로 발급하는 realtime-tickets에는 키가 필요 없다.

변경에는 expected_version 정수 >=1. meeting_version/member.version/message.version은 각각 다른 자원 버전이다. 서버는 충돌 시 409 VERSION_CONFLICT, details에 current_version을 포함하며 접근 권한 없는 사람에게는 반환하지 않는다.

| 항목 | 확정 설계 정책(2026-10-06) |
| --- | --- |
| 참여 인원 | 첫 버전 최대 2명(생성자 포함), 혼자 사용 가능. 다인 확장은 별도 검토 |
| 제목 | trim 후 1~100 Unicode 코드 포인트 |
| 초대 | 1회 수락, 유효 24시간, 활성 초대 1개/약속 |
| 목록 | limit 기본 20/최대 100, 불투명 cursor. 변경된 필터에 이전 cursor 재사용 금지 |
| 채팅 | 일반 텍스트 trim 후 1~1000 코드 포인트, HTML 해석 없음, 수정 미지원·본인 삭제 지원 |
| 초대 토큰 / WS 티켓 | 원본 로그 금지, DB에 해시. WS 티켓은 30초 내 1회 사용 |
| 추천 | 최대 3개, 결과 유효 5분, 참여자 출발 정보가 바뀌면 즉시 무효화 |
| 공유 ETA | 계산 후 최대 120초 및 교통 근거 유효기간 중 짧은 값까지만 유효 |
| 속도 제한 | 채팅 사용자·약속당 10회/10초, 추천 약속당 3회/분, 초대 미리보기 사용자당 10회/분. 429+Retry-After |
| 보관 | 종료/취소 후 약속·채팅30일, 이벤트 재전송24시간. draft 미사용30일 삭제·confirmed 목표시각6시간후 자동종결, 실행 검증 미완료 |

상태: meeting=draft/confirmed/completed/cancelled. 생성은 draft, 확정은 confirmed, 확정 후 변경도 새 revision을 만들고 confirmed 유지. completed/cancelled는 읽기만 가능하며 초대·추천·채팅 전송·출발 공유·개인 안내 생성은 중단한다. 허용된 본인 메시지 삭제·약속 삭제는 가능하다.

활성 참여자만 약속 상세·채팅·공유를 조회한다. 탈퇴한 참여자와 비참여자는 404 RESOURCE_NOT_FOUND. 활성 참여자에게 주최자 전용 작업을 거절할 때만 403 MEETING_ROLE_REQUIRED. 주최자는 약속 변경/확정/종료/취소/삭제와 초대 발급·철회를 수행한다. 상대도 추천 요청, 본인 출발지 설정, 본인 채팅, 본인 공유 설정은 가능하다. 상대의 전체 개인 경로·주소·원본 이동/AI 기록 조회는 불가하다.

## 2. 응답 객체

| 객체 | 필드 |
| --- | --- |
| Meeting | meeting_id:string, title:string, status:enum, version:int, organizer_member_id:string, max_members:int, member_count:int, current_revision:MeetingRevision/null, members:Member[], created_at:datetime, updated_at:datetime |
| Member | member_id:string, display_name:string, role:organizer/participant, participation_status:active/left, origin_ready:bool, version:int. 공유 설정의 원본과 개인 좌표는 타인에게 반환하지 않음 |
| MeetingRevision | revision_id:string, revision_no:int, target_arrival_at:datetime, timezone:string, destination:Destination, confirmed_at:datetime |
| Destination | name:string(1~100), latitude:number[-90,90], longitude:number[-180,180], provider:string/null, place_ref:string/null. 공동 목적지만 공유 |
| PrivateOrigin | origin:기존 saved_place/current_location/map_pin 중 하나, origin_version:int, recommendation_consent:bool, updated_at:datetime |
| Candidate | candidate_id:string, destination:Destination, journeys:[{member_id,estimated_seconds:int,transfer_count:int,time_source:realtime/timetable/estimated}], max_seconds:int, difference_seconds:int, explanation:string/null |
| Message | message_id:string, meeting_id:string, sender_member_id:string, sender_display_name:string, client_message_id:string, body:string/null, sent_at:datetime, deleted_at:datetime/null, version:int |
| SharedStatus | member_id:string, state:unknown/reported_departed/in_transit/arrived/unavailable/sharing_off, source:manual/estimated/none, reported_at:datetime/null, estimated_arrival_at:datetime/null, eta_calculated_at:datetime/null, valid_until:datetime/null, updated_at:datetime, version:int |

일반 조회는 활성 members만 반환한다. 메시지에 남은 탈퇴한 작성자는 '탈퇴한 참여자'로 표시한다. SharedStatus의 arrived는 본인 도착 신고이며 자동 위치 인증이 아니다. in_transit도 본인이 입력한 탑승 등 이벤트를 근거로 하므로 실제 GPS 검증을 뜻하지 않는다.

## 3. 약속·초대 API

| 방식·경로 | 권한 / 입력 | 성공·처리 |
| --- | --- | --- |
| POST /meetings | 로그인. {title} | 201 Meeting. 생성자 member를 함께 저장, draft/version=1 |
| GET /meetings | 로그인. status?:상태 enum, cursor?, limit? | 200 {items:Meeting[],next_cursor}. 본인이 활성 참여 중인 약속만, created_at/id 내림차순 |
| GET /meetings/{meeting_id} | 활성 참여자. 입력 없음 | 200 Meeting |
| PATCH /meetings/{meeting_id} | 주최자. {title,expected_version} | 200 Meeting. 열린 약속만, 장소·시각은 확정 API로 변경 |
| POST /meetings/{meeting_id}/confirmations | 주최자. {expected_version,target_arrival_at,timezone,destination} 또는 {expected_version,target_arrival_at,timezone,recommendation_id,candidate_id} | 201 {meeting:Meeting,revision:MeetingRevision}. 두 목적지 선택 방식은 XOR. 미래 시각 필수, IANA timezone 검증 |
| POST /meetings/{meeting_id}/transitions | 주최자. {expected_version,status:completed/cancelled} | 200 Meeting. completed는 confirmed에서만, cancelled는 draft/confirmed에서만 |
| DELETE /meetings/{meeting_id} | 주최자. 쿼리 expected_version:int | 202 {job_id}. 접근 즉시 차단 후 공동 기록 삭제. 개인 trip은 유지하되 약속 FK/공유 연결을 해제하고 개인 보관 정책 적용 |
| POST /meetings/{meeting_id}/invites | 주최자. {expected_version} | 201 {invite_id,token,expires_at,meeting_version}. 기존 활성 초대 철회 후 새 초대 발급. 만석이면 409 |
| DELETE /meetings/{meeting_id}/invites/{invite_id} | 주최자. 쿼리 expected_version:int(약속 버전) | 204. 철회 및 약속 버전 증가. 다른 약속 초대는 404 |
| POST /meeting-invite-previews | 로그인. {token:string} | 200 {title,organizer_display_name,member_count,max_members,expires_at}. 주소·대화·참여자 상세 반환 안 함 |
| POST /meeting-invite-acceptances | 로그인. {token:string} | 200 {meeting_id,member:Member,meeting_version}. 원자적으로 잔여 인원 검사·토큰 소비·member 저장 |
| DELETE /meetings/{meeting_id}/members/me | 본인 활성 참여자. 쿼리 expected_version:int(member 버전) | 204. 주최자는 409 ORGANIZER_CANNOT_LEAVE. 상대 탈퇴 시 접근·공유·기존 연결 차단, 개인 데이터 정리 |

초대 token은 256비트 이상 난수의 URL-safe 문자열, 본문 길이 32~256 제안이다. 링크를 만들면 브라우저 fragment에 넣어 읽고 수락 요청 본문으로 전송한다. 서버 URL/쿼리·로그에 원문을 남기지 않는다. 위 API는 링크를 반환할 뿐 자동으로 친구에게 발송하지 않는다.

만료/철회/존재하지 않는 초대는 모두 404 INVITE_UNAVAILABLE. 같은 사람이 이미 수락한 같은 토큰을 재요청하면 아직 활성 참여 중일 때 200 반환, 다른 사람은 404. 신규 수락과 만석 검사는 약속 행 잠금 안에서 처리한다. 동일 사용자는 member가 중복 생성되지 않는다. 초대 발급의 멱등 응답 재현을 위해 필요한 token 응답은 만료/소비/철회 전까지만 암호화된 응답 캐시에 보관한다. 영구 초대 레코드에는 해시만 둔다. 캐시 정리 후 같은 키에는 409 INVITE_RESPONSE_EXPIRED를 반환하며 새 발급이 필요하다. 탈퇴 후 재참여는 새 초대를 요구한다.

멤버 추가/탈퇴는 약속 버전을 올리고 기존 중간 추천을 무효화한다. 실제 장소·시각이 같으면 확정 revision 자체는 바꾸지 않는다. 삭제된 약속 접근은 주최자도 404이며 삭제 job만 본인 조회 가능하다.

## 4. 개인 출발지·중간 만남 추천

| 방식·경로 | 입력 | 성공·처리 |
| --- | --- | --- |
| PUT /meetings/{meeting_id}/members/me/origin | {origin, recommendation_consent:bool, expected_version:member버전} | 200 {private_origin:PrivateOrigin,member_version}. 본인만 조회 가능. consent=true는 서버가 중간 추천 계산에 사용할 동의이며 집 주소 공개 동의가 아님 |
| GET /meetings/{meeting_id}/members/me/origin | 없음 | 200 PrivateOrigin 또는 null |
| POST /meetings/{meeting_id}/recommendations | {expected_version:약속버전,target_arrival_at,timezone} | 202 {recommendation_id,job_id,status:queued}. 활성 2명, 둘 다 origin·추천 동의가 있어야 함 |
| GET /meetings/{meeting_id}/recommendations/{recommendation_id} | 활성 참여자 | 200 {recommendation_id,status:queued/running/succeeded/failed/stale,candidates:Candidate[],expires_at:datetime/null,outcome:available/no_feasible_journey/null,error:공통오류객체/null} |

origin은 기존 경로 검색 객체와 같다. saved_place는 본인 place_id, current_location은 latitude/longitude/accuracy_meters/captured_at, map_pin은 latitude/longitude를 받는다. 외부에 개인 출발지를 노출하지 않는다. 다른 사람에게는 origin_ready만 제공한다.

추천의 시간과 동의·출발지 버전·활성 멤버 집합을 고정해 저장한다. 계산 완료 시에도 버전을 다시 검사한다. 바뀌면 stale, 결과를 확정에 사용할 수 없다. 시간 차이와 최대 이동시간을 함께 비교하는 초기 순위 정책을 제안하며 정책 버전을 저장한다. 실제 데이터가 부족하면 후보를 꾸며내지 않는다. 성공했지만 후보 없음은 status=succeeded, candidates=[], outcome=no_feasible_journey, error=null이다. 후보가 있으면 outcome=available, 진행 중/실패/만료면 outcome=null이다.

후보 응답은 목적지와 개인별 총 예상시간·환승 수만 공유한다. 개인 출발역/주소/경로 좌표는 제외한다. AI 설명 실패는 explanation=null로 처리하며 검증된 시간/순위를 AI 문장으로 덮어쓰지 않는다. 설명용 프롬프트 세부 버전은 구현 전 별도 작성한다.

확정 시 추천과 후보의 약속 소속, 참여자·출발 정보 버전, 만료, target_arrival_at 일치를 확인한다. 직접 지정 목적지는 서버에서 유효성을 확인한다. 새 확정 revision은 기존 개인 안내를 stale로 만들고 출발 공유 ETA를 무효화한다.

## 5. 약속 전용 출발 안내와 기존 이동 API 연결

| 방식·경로 | 입력 | 성공·처리 |
| --- | --- | --- |
| POST /meetings/{meeting_id}/guidance-queries | {meeting_revision_id,departure_basis:recommended/now,origin_override?:기존위치객체,trip_id?:string} | 200 {meeting_journey_id,meeting_revision_id,guidance:기존안내객체,meeting_arrival_slack_seconds:int/null}. 본인의 저장 출발지 또는 override 사용 |
| POST /meetings/{meeting_id}/arrivals | {meeting_journey_id,client_event_id,occurred_at,source:manual} | 201 {arrival_id,version:1,received_at,source:manual}. 같은 ID·본문 재전송 200, 다른 본문 409 |

약속이 confirmed이고 최신 revision이어야 한다. 오래된 revision은 409 MEETING_REVISION_CHANGED. 출발지가 없으면 409 ORIGIN_REQUIRED. 근거 부족·경로 없음은 기존 guidance.status를 사용하고 값을 NULL로 둔다. 계산 중 약속이 바뀌어도 성공 결과로 내보내지 않는다.

첫 안내는 개인별 meeting_journey와 guidance를 연결한다. 같은 약속 revision·본인 여정의 재조회는 기존 여정을 사용하며 경로 변경/이전 이동 종료 후 새 이동은 새 여정을 만든다. trip_id는 본인·해당 약속 여정의 이동만 허용한다.

반환된 guidance.guidance_id를 기존 POST /trips에 전달한다. 서버가 guidance의 meeting_journey 연결을 따라 trip_id를 붙인다. 하나의 여정에 이미 진행 중 trip이 있으면 새 생성은 409 ACTIVE_TRIP_EXISTS. 루틴의 기존 POST /guidance-queries 요청은 변경하지 않으며 routine_id는 계속 필수다.

출발/정류장 도착/탑승/하차는 기존 POST /trips/{trip_id}/events와 정정 API를 재사용한다. 약속 arrivals는 최종 목적지 도착을 기록하는 별도 본인 신고이며 기존 type enum을 임의로 늘리지 않는다. 개인 보행 학습에는 넣지 않는다. arrivals는 연결된 trip에 departed가 있어야 한다. 잘못된 도착 신고는 아래 공유 상태의 '정정' 작업과 함께 새 기록으로 대체하며 원본은 보관 정책에 따라 이력 처리한다.

meeting_arrival_slack_seconds = target_arrival_at - estimated_arrival_at. 기존 guidance.slack_seconds는 첫 탑승 전 여유이며 별도 필드다. 5분 기본 여유를 약속 전 여유로 중복 계산하지 않는다.

## 6. 공유 설정·상태

| 방식·경로 | 입력 | 성공·처리 |
| --- | --- | --- |
| PATCH /meetings/{meeting_id}/members/me/sharing | {enabled:bool,expected_version:member버전} | 200 {enabled,member_version,updated_at}. 처음은 false, 과거 이력을 일괄 공개하지 않음 |
| GET /meetings/{meeting_id}/shared-statuses | 활성 참여자 | 200 {items:SharedStatus[]}. 비공유 사용자는 sharing_off와 NULL 시간만 제공 |
| POST /meetings/{meeting_id}/arrival-corrections | {arrival_id,expected_version,occurred_at?:datetime,excluded?:bool,correction_reason:wrong_time/wrong_action} | 201 {arrival_id,version,received_at}. 원본 보존·새 정정 이력, 본인 것만 가능 |

공유 enabled=true인 상태에서 저장에 성공한 departed/boarded 등 이벤트와 서버 산정 ETA를 공유 상태에 반영한다. **클라이언트가 상대에게 공개할 ETA를 직접 지정할 수 없다.** 서버가 개인 경로로 계산한다. trips 생성·WS 접속 자체는 출발이 아니다.

공유 도중 켜면 그 순간 본인 최신 상태 요약만 공유하고 과거 원문 이벤트는 제공하지 않는다. 출발 이벤트 정정/삭제, 도착 정정은 공유 상태에 반영한다. 정상 공유 상태 변경과 재전송 이벤트 저장은 같은 트랜잭션으로 처리한다.

철회·탈퇴·약속 종료·취소 시 ETA/출발 시각을 다음 응답에서 제거하고 연결된 클라이언트에 상태 무효화를 전달한다. 동의 철회로 본인 trip 학습까지 자동 삭제하지는 않는다. 네트워크 단절과 ETA 만료는 unavailable이며 '아직 출발 안 함'으로 단정하지 않는다. 이미 상대 기기에 표시된 내용을 소급 회수할 수 있다고 약속하지 않는다.

공유 기본꺼짐, 종료 시점은 약속 종료/취소/본인 철회 중 먼저 발생한 때. 종료 처리가 없으면 확정 약속 시각6시간후 공유 종료 및 confirmed 약속 completed 자동 정리(실제 참석/도착 판정 아님). 종결 뒤 공유 재활성화는409 MEETING_CLOSED.

## 7. 채팅 REST

| 방식·경로 | 입력 | 성공·처리 |
| --- | --- | --- |
| GET /meetings/{meeting_id}/messages | before?:메시지 커서, limit?:기본20/최대100 | 200 {items:Message[],next_cursor}. 최신 구간을 오래된 순서로 반환, 다음 커서는 더 오래된 구간 |
| POST /meetings/{meeting_id}/messages | {client_message_id:UUID문자열,body:string} + Idempotency-Key | 201 Message. 저장 commit 후 알림. client_message_id가 같고 body가 같으면 200, 다르면 409 MESSAGE_ID_CONFLICT |
| DELETE /meetings/{meeting_id}/messages/{message_id} | 쿼리 expected_version:message버전 | 204. 본인만, 타인 메시지는 403 MESSAGE_DELETE_FORBIDDEN(참여자 한정) |

같은 Idempotency-Key 재전송은 공통 규칙에 따라 최초 HTTP 응답 재현(201 가능), 다른 키지만 같은 client_message_id이면 200이다. 삭제는 body=NULL인 tombstone으로 바꾸고 version을 증가시킨다. API 삭제 후 재전송이 본문을 되살리지 않도록 저장된 요청 해시/멱등 응답도 정리한다. 이미 삭제된 메시지의 동일 버전 삭제 재시도는 204, 그 외 충돌은 409. 전송 중 화면은 pending, REST 성공 또는 서버 이벤트를 받으면 message_id/client_message_id로 하나로 합친다.

채팅으로 '7시에 만나'라고 말해도 약속 시각을 자동 수정하지 않는다. 확정 API가 유일한 확정 기준이다. 상대 접속 중 여부와 관계없이 DB에 저장되면 전송 성공이며 읽음/전달 완료를 의미하지 않는다.

## 8. WebSocket 인증·이벤트·복구

### 연결

POST /meetings/{meeting_id}/realtime-tickets
- 활성 참여자, 빈 본문 {}. 매 연결별 새 발급이므로 Idempotency-Key 예외이며 사용자당 10회/분 제한.
- 201 data={ticket:string,expires_at:datetime,websocket_path:"/api/v1/ws/meetings/{meeting_id}"}.
- 만료 30초·1회 소비. 네트워크 오류로 응답을 잃으면 새 티켓을 요청한다. 이전 티켓은 사용/만료 시 소멸하며 원문 응답을 멱등 캐시에 저장하지 않는다.
- WS는 브라우저 기본 인증 헤더 지원에 의존하지 않고 첫 메시지 auth로 티켓을 전달한다. 토큰을 URL에 넣지 않는다.
- 운영 wss, 개발 localhost ws. 허용 Origin만 연결. 첫 5초 안에 auth 없으면 4401 종료.
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

| 서버 이벤트 | data |
| --- | --- |
| ready | {member_id,current_seq,replay_from_seq} (제어 메시지, seq 없음) |
| chat.message.created | {message_id} |
| chat.message.deleted | {message_id,version} |
| meeting.updated | {meeting_version,revision_id:null/string,status} |
| member.updated | {member_id,member_version,participation_status} |
| sharing.updated | {member_id,status_version} |
| access.revoked | {reason:membership_ended/meeting_deleted/session_expired} 이후 종료 (제어 메시지, seq 없음) |
| resync_required | {reason:cursor_expired/cursor_invalid} (제어 메시지) |
| error | {code,message,request_id?} (제어 메시지) |
| pong | {client_time:string} (제어 메시지) |

이벤트에는 채팅 본문·개인 주소·티켓·ETA 원문을 넣지 않는다. 클라이언트는 알림 후 REST로 권한을 다시 검사한 최신 데이터만 조회한다. 채팅 작성 직후 REST 성공 응답과 WS 알림의 순서는 달라도 된다. GET /meetings/{meeting_id}/messages/{message_id}는 활성 참여자에게 200 Message(삭제면 body=NULL), 없으면 404를 반환한다.

클라이언트는 auth와 ping({type:"ping",data:{client_time}})만 보낸다. chat.send 같은 미정 이벤트로 메시지를 쓰지 않는다. 미지원 프레임은 error.code=UNSUPPORTED_EVENT. 프레임 최대 8KiB, 위반 종료 1009. 25초 간격 ping, 60초 무응답 종료로 확정한다. 일반 클라이언트가 서버 공유 상태를 임의로 갱신하는 프레임은 없다.

### 복구

GET /meetings/{meeting_id}/sync
- 200 {meeting:Meeting,shared_statuses:SharedStatus[],recent_messages:Message[],next_message_cursor:string/null,last_seq:string}.
- 최근 메시지 최대20개와 last_seq를 **같은 일관된 DB 스냅샷**에서 읽는다.
- 첫 접속: sync → ticket → auth(after_seq=last_seq). 그 사이 commit된 이벤트는 저장 로그에서 재전송.
- 재접속: 마지막 처리 seq로 auth. 서버는 (after_seq,current_seq]를 재생한 뒤 실시간으로 전환한다. 전환 사이 누락을 막기 위해 동일 이벤트 저장소를 기준으로 읽는다.
- event_id/seq로 중복 제거, 순서 역전/누락 감지 시 sync 후 재연결. 정확히 한 번 전송을 보장하지 않고 최소 한 번 수신에 맞춰 처리한다.
- 24시간 로그 만료, 미래 seq, 권한 없는 기간의 seq는 resync_required 후 4409로 종료. 클라이언트는 sync부터 다시 시작.
- 정기 sync는 연결 복구/오래된 상태 갱신 수단이며 폴링 주기를 제품상 확정하지 않는다.
- 세션 만료 4401, 권한 상실 4403, 인증/티켓 실패 4401, 서버 장애 1011. 재연결은 1·2·4·8·최대30초+지터. 4401은 로그인/티켓 갱신, 4403은 재시도 중지.
- 종료/취소된 약속은 채팅 열람은 가능하지만 출발 상태는 공유 종료로 표시. 세션/참여권한은 연결 시와 재전송·실시간 발송 시 확인한다.

## 9. 주요 요청·응답 예시

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

## 10. 오류와 상태 전이

| HTTP | code | 조건 / 화면 처리 |
| --- | --- | --- |
| 401 | AUTH_REQUIRED / SESSION_EXPIRED | 로그인·세션 갱신 |
| 403 | MEETING_ROLE_REQUIRED / MESSAGE_DELETE_FORBIDDEN | 참여자는 맞지만 권한 없음 |
| 404 | RESOURCE_NOT_FOUND / INVITE_UNAVAILABLE | 없음·비참여·다른 약속 자원 또는 사용할 수 없는 초대 |
| 409 | VERSION_CONFLICT / IDEMPOTENCY_CONFLICT / REQUEST_IN_PROGRESS | 최신 데이터 조회 또는 같은 키로 제한된 재시도 |
| 409 | MEETING_FULL / MEETING_CLOSED / ORGANIZER_CANNOT_LEAVE / INVITE_RESPONSE_EXPIRED | 인원·종료·주최자 탈퇴 제한 |
| 409 | MEETING_NOT_CONFIRMED / MEETING_REVISION_CHANGED | 확정 필요 또는 새 확정 버전 재조회 |
| 409 | ORIGIN_REQUIRED / RECOMMENDATION_NOT_READY / RECOMMENDATION_STALE | 본인 출발지 또는 상대 준비·추천 유효성 확인 |
| 409 | ACTIVE_TRIP_EXISTS / EVENT_ORDER_CONFLICT / MESSAGE_ID_CONFLICT | 기존 이동 복구, 시각·순서·중복 본문 확인 |
| 422 | VALIDATION_ERROR | 타입·문자 길이·시각·좌표·필수 필드 오류 |
| 429 | RATE_LIMITED | Retry-After 이후 재시도 |
| 503/504 | PROVIDER_UNAVAILABLE / PROVIDER_TIMEOUT | 경로·교통 공급자 실패; 기존 값으로 성공처럼 안내하지 않음 |

```json
{"error":{"code":"MEETING_REVISION_CHANGED","message":"약속 장소 또는 시간이 변경됐어요. 다시 확인해주세요.","details":[{"field":"meeting_revision_id","reason":"stale"}]},"meta":{"request_id":"req_demo_error","server_time":"2026-10-02T09:02:00Z"}}
```

모든 자원 소속 확인은 존재·인증/권한 확인 후 버전·상태·필드 계산으로 이어진다. 상태 전이 불가(예: draft→completed)는 409 MEETING_NOT_CONFIRMED, 이미 종결된 약속 변경은 MEETING_CLOSED. 예상 밖 서버 오류는 기존 500 INTERNAL_ERROR.

## 11. 저장·삭제·로깅과 DB 영향

확정: completed/cancelled 이후 공동 기록30일후 삭제. draft는 마지막 사용자 변경후30일 미사용이면 접근 차단/삭제. confirmed 목표시각6시간후 자동completed로 정리하며 실제 참석/도착 판정은 하지 않는다. 주최자 명시 삭제는 즉시 접근 차단 및202 작업. 비주최자 약속탈퇴는 개인 출발/공유/티켓 정리, 기존 공동 메시지는 탈퇴한 참여자로 표시. 계정탈퇴는 본인 메시지 본문도 삭제, 주최자 계정탈퇴는 약속 취소후 다른 활성 참여자30일 열람. 개인 trip은 약속 연결을 해제하고90일 정책 적용.

다른 사람이 적은 메시지에 개인정보가 있을 수 있으므로 작성자 탈퇴 처리만으로 모든 개인정보 삭제가 보장된다고 표현하지 않는다. 기존 개인 품질 이력·trip 삭제 정책은 유지하며 공동 약속과 따로 정리한다. 공유 철회 후 재전송 로그에 개인 상태 원문을 남기지 않는다.

기존 8개 약속 테이블에 다음 컬럼·테이블 설계를 추가한다(DDL 미적용).
- meetings: max_members, last_event_seq, closed_at, delete_after; members: private_origin jsonb, origin_version, recommendation_consent 및 버전/공유 종료.
- recommendations: target_arrival_at, input member/version 목록, status, job_id, error. 메시지: version와 본문 해시, share_events: version·정정 대상·arrival 기록.
- meeting_realtime_events 신규: meeting_id, seq, event_id, type, entity_ref, occurred_at, expires_at; UNIQUE(meeting_id,seq), 이벤트 본문에는 민감한 내용 제외. 24시간 청소.
- meeting_realtime_tickets 신규: token_hash UNIQUE, member_id, expires_at, consumed_at, auth_session_ref. 연결 종료/세션 무효화 시 정리.
- 약속 안내 FK는 guidance_snapshots에 meeting_journey_id? 추가. routine_id와 동시 사용 금지, 기존 기록의 루틴 삭제로 둘 다 NULL일 수 있음.
- arrivals와 arrival-corrections는 meeting_share_events에 private 원본/정정 관계로 저장하고 공유 동의와 별개로 본인 기록을 유지. GET 공용 상태는 동의한 최신 요약만 제공.

로그 이벤트: meeting.created/confirmed/closed, invite.accepted/rejected, chat.message.persisted/deleted, sharing.updated, realtime.connected/disconnected/resync. request_id·자원 참조·결과·소요 시간만 기록하며 본문·주소·좌표·초대/티켓 원문·쿠키 금지.

## 12. 구현 전 확인과 완료 기준

이번 문서의 2인·기간·길이·속도 제한·탈퇴 공동 기록 정책은 확정했다. 인증은 기존auth_api.md, 실제 공급자 지원 및 기간청소/삭제/권한 검증은 구현 단계에서 수행한다. 문서 결정 완료와 기능 구현 완료는 별도다.

- [ ] 비참여자/탈퇴자/다른 약속 ID로 REST·WS·재전송 접근 차단.
- [ ] 동시 초대 수락에서 정원 초과·중복 가입 방지.
- [ ] 약속 변경 중 추천/안내 결과가 저장돼도 오래된 확정으로 성공하지 않음.
- [ ] REST 성공/WS 알림 순서가 달라도 메시지 중복 표시 없음.
- [ ] commit 직후 프로세스 종료·재접속에도 sync+이벤트 이력으로 누락 복구.
- [ ] 토큰 만료/소비/로그 제외 및 회원 세션 만료 중 연결 해제.
- [ ] 수동 출발과 자동 감지 구분, ETA 만료·공유 철회·정정 반영.
- [ ] 삭제·탈퇴·기간 청소가 메시지 본문·개인 입력·티켓·캐시에 함께 반영.
- [ ] 기존 루틴 안내 요청·응답의 회귀 검증과 약속 여유/탑승 여유 분리.
