# 지금이니? — 이메일·비밀번호 인증 계약

- 버전 0.1 / 2026-10-02 / 전체 미구현
- 사용자 확정: 첫 버전은 이메일·비밀번호 로그인. 소셜 로그인은 테스트 이후 배포 확대 시 재검토하며 현재 구현 범위에서 제외한다.
- 아래 세션·검증·제한 수치는 구현 기준으로 제안하는 설계값이다. 인증 방식 결정과 실제 인증 구현 완료를 구분한다.
- PostgreSQL에 회원·자격정보·서버 세션을 저장한다. 로그인 상태는 HttpOnly 쿠키로 전달하며 JWT/localStorage 기반 인증은 첫 버전에 추가하지 않는다.
- 인증 API는 기존 /api/v1 접두사와 data/meta 및 error/meta 공통 응답을 따른다.

## 1. 입력·비밀번호·메일 정책

- email: 문자열 최대254자. 앞뒤 공백 제거, 도메인 소문자화, 서비스 로그인 식별자는 전체 소문자로 통일하는 정책을 채택한다. 최초 입력도 표시용으로 보관하며 점/플러스 주소를 임의 병합하지 않는다. 이메일 형식 검증과 실제 소유 확인을 구분한다.
- password: 15~128 Unicode 코드 포인트. 공백·붙여넣기 허용, trim/조용한 절단/대소문자 변환 금지. 문자 종류 조합을 강제하지 않고 흔한/유출 비밀번호 차단 목록을 구현 시 적용한다.
- display_name: trim 후 1~30자.
- Argon2id 해시와 라이브러리 생성 salt를 저장한다. 초기 최소 설정 memory=19456KiB, time_cost=2, parallelism=1을 기준으로 실제 서버에서 비용을 측정한다. 비밀번호 원문/복호화 가능한 암호문은 보관하지 않는다.
- 이메일 확인 전 계정 상태는 pending_verification. 비밀번호가 맞으면 제한 세션을 발급하지만 장소·루틴·약속 등 업무 API는 403 EMAIL_VERIFICATION_REQUIRED. /me, 확인 메일 재요청, 확인 완료, 로그아웃, 재인증·탈퇴는 허용한다.
- 이메일 확인 토큰은 24시간, 비밀번호 재설정 토큰은 30분 제안. 256비트 이상 난수, DB에는 해시·목적·만료·소비 시각만 저장. 서로 다른 목적의 토큰을 교차 사용하지 않는다.
- 메일 링크는 프론트의 고정 허용 URL로만 만든다. 요청 Host 헤더를 그대로 신뢰하지 않는다. URL fragment에서 토큰을 읽어 POST 본문으로 전달하고 브라우저 주소에서 즉시 제거한다. GET 링크 접근만으로 토큰을 소비하지 않는다.
- 확인 성공 시 기존 제한 세션을 폐기하고 로그인 화면으로 안내한다. 재설정 성공도 전체 세션·WS 티켓을 폐기하고 다시 로그인한다.
- 메일 공급자는 아직 미정이다. 로컬 개발은 외부 발송 없는 메일 캡처 도구를 사용할 수 있으나 토큰을 일반 로그/응답에 노출하지 않는다. 전달 큐에 안전하게 접수되기 전 메일 요청을 성공처럼 표시하지 않는다.

## 2. 세션·CSRF 계약

- 운영 쿠키: __Host-timeisnow_session, HttpOnly, Secure, SameSite=Lax, Path=/, Domain 없음. 로컬 HTTP에서는 별도 timeisnow_dev_session 및 Secure=false를 개발 환경에만 허용한다.
- 세션 원본은 256비트 이상 난수이며 DB에는 해시만 저장. 최대 수명7일, 미사용24시간 제안. 요청마다 서버가 만료·폐기·회원 상태를 검사한다. 무한 연장하지 않는다.
- 로그인 시 세션 ID·CSRF 토큰 교체, 로그아웃/탈퇴/비밀번호 변경 시 폐기. /me 응답에는 세션 원문을 포함하지 않는다. 같은 계정 다중 기기는 허용하되 각각 별도 세션이다.
- GET /auth/csrf는 세션에 묶인 csrf_token을 반환한다. 로그인 전에는 수명15분의 임시 세션을 만들며 동일 쿠키 보안 속성을 적용한다.
- 모든 POST/PUT/PATCH/DELETE(로그인·가입·토큰 소비 포함)에 X-CSRF-Token과 허용 Origin 검증을 적용한다. CSRF 불일치는 403 CSRF_INVALID. 토큰은 프론트 메모리에만 두고 새로고침 시 재조회한다.
- 로그인 성공 응답은 새 세션의 csrf_token을 포함한다. 이전 토큰은 재사용하지 않는다. logout 이후에도 다시 /auth/csrf부터 시작한다.
- 프론트와 API는 운영에서 같은 origin reverse proxy, 개발은 Vite 프록시를 기본 설계로 한다. credentials 포함 요청, wildcard+credential CORS 금지.
- 별도 refresh-token API는 만들지 않는다. 만료 시 로그인, 서버 미사용 만료 갱신은 절대 만료를 넘지 않는다.
- 기존 WS 티켓은 auth_sessions.id에 연결한다. 로그아웃·세션 만료 시 연결을 4401로 닫고 티켓도 무효화한다.

## 3. API 목록

아래 {} 필드는 모두 필수이며 ?만 선택이다. 성공 열은 공통 data 내부다.

| 방식·경로 | 인증 / 입력 | 결과 |
| --- | --- | --- |
| GET /auth/csrf | 비로그인 가능 / 없음 | 200 {csrf_token:string,expires_at:datetime}; Cache-Control:no-store |
| POST /auth/register | 임시 세션+CSRF / {email,password,display_name} | 201 {user_id,email_verification_required:true}. pending 회원·해시·프로필(첫 여유300초)·확인메일 큐 생성. 자동 로그인 안 함 |
| POST /auth/login | 임시/기존 세션+CSRF / {email,password} | 200 {user_id,email_verified:bool,session_expires_at:datetime,csrf_token:string} + Set-Cookie |
| GET /me | 로그인 / 없음 | 기존 user_id,display_name,profile + email_verified:bool 추가. pending도 조회 가능 |
| POST /auth/logout | CSRF / {} | 204. 세션 폐기·쿠키 제거. 유효한 CSRF 컨텍스트에서 이미 로그아웃이면 204 |
| POST /auth/email-verification-requests | CSRF / {email} | 202 {message:"해당하는 계정이 있으면 안내 메일을 보냈어요."}. 존재/확인 여부에 동일 응답 |
| POST /auth/email-verifications | 임시/기존 세션+CSRF / {token} | 200 {verified:true,login_required:true}. 토큰 원자적 소비, 이미 확인된 사용자의 미소비 유효 토큰은 성공 처리 |
| POST /auth/password-reset-requests | CSRF / {email} | 202 {message:"해당하는 계정이 있으면 안내 메일을 보냈어요."}. 계정 존재와 무관한 상태/문구 |
| POST /auth/password-resets | 임시/기존 세션+CSRF / {token,new_password} | 200 {password_reset:true,login_required:true}. 원자적 비밀번호 갱신·토큰 소비·전체 세션 및 나머지 복구 토큰 폐기 |
| POST /auth/reauthentications | 로그인+CSRF / {password} | 200 {reauthenticated_until:datetime}; 해당 세션에 5분 유효한 재인증 표시 |

등록 이메일 중복은 409 EMAIL_UNAVAILABLE. 회원 존재 노출 가능성이 있는 UX 선택임을 기록하며, 비밀번호 오류/없는 계정의 로그인은 모두 401 INVALID_CREDENTIALS로 통일한다. 등록 재전송으로 기존 비밀번호를 덮어쓰지 않는다. pending 계정은 동일 정규 이메일로 중복 생성하지 않는다.

이메일 확인은 비밀번호 재설정이 아니다. 메일을 받은 사람이 자신이 가입하지 않은 계정의 확인 링크를 승인하지 않도록 안내한다. pending 가입 보관/재가입 정리는 운영 전 별도 확정하고 기존 계정을 자동 활성화하지 않는다.

인증 POST는 사용자 기준 Idempotency-Key 일반 규칙의 예외이며 원문 비밀번호/메일 토큰을 응답 캐시에 넣지 않는다. 계정 email unique, 토큰 1회 소비, 세션 폐기로 중복을 통제한다. 토큰 재사용/만료/존재하지 않음은 모두 400 AUTH_TOKEN_INVALID. 서버 상태 확인 후 재요청 또는 새 메일 요청으로 복구한다.

## 4. 계정 삭제와 오류

기존 DELETE /me는 로그인+CSRF 및 5분 이내 재인증을 요구한다. 실패는 403 REAUTHENTICATION_REQUIRED. 성공 202 {job_id,deletion_receipt,receipt_expires_at}. 삭제 접수와 함께 모든 로그인 세션/WS를 무효화하고 쿠키를 제거한다.

삭제 작업에 한해 GET /jobs/{job_id}에 X-Deletion-Receipt 헤더를 허용한다. 수명24시간의 난수 receipt는 해당 job 조회만 허용하고 DB에는 해시로 저장한다. 이 헤더를 다른 API 인증에 사용할 수 없다. 접근 로그·반환 메타데이터에 복제하지 않는다. 만료/잘못된 영수증은 404. 원문은 삭제 응답에서 한 번만 제공하며 클라이언트 메모리에서만 관리한다. 새로고침 후 복구가 필요하면 별도 사용자 지원 흐름을 검토한다.

| HTTP | code | 처리 |
| --- | --- | --- |
| 401 | INVALID_CREDENTIALS | 이메일 또는 비밀번호를 확인해주세요 |
| 401 | AUTH_REQUIRED / SESSION_EXPIRED | 로그인 필요/재로그인 |
| 403 | CSRF_INVALID / EMAIL_VERIFICATION_REQUIRED / REAUTHENTICATION_REQUIRED | CSRF 재조회/메일 확인/비밀번호 재확인 |
| 409 | EMAIL_UNAVAILABLE | 해당 이메일로 가입할 수 없음, 로그인·복구 안내 |
| 400 | AUTH_TOKEN_INVALID | 토큰 만료/사용됨/잘못됨 통일 |
| 422 | VALIDATION_ERROR | 형식·길이 오류, 비밀번호 입력값을 details에 반사하지 않음 |
| 429 | RATE_LIMITED | Retry-After 후 재시도 |
| 503 | AUTH_DELIVERY_UNAVAILABLE | 메일 큐/발송 서비스 접수 불가. 계정 존재와 무관하게 같은 서비스 상태 적용 |

로그인 속도 제한 초기값: 정규 이메일의 키 해시당 5회 실패/15분 + IP당30회/15분. 영구 계정 잠금은 하지 않는다. 가입은 IP당5회/시간, 메일 요청은 이메일 키당3회/시간 및 IP당20회/시간 제안. 분산 서버에서도 공통 제한 저장소가 필요하며 구현 전 선택한다. 메일 요청은 균일한 응답 경로를 사용하고 외부 발송을 동기 대기하지 않는다.

## 5. 저장 테이블

| 테이블 | 주요 필드·관계 |
| --- | --- |
| auth_credentials | user_id PK/FK(users), email_normalized UNIQUE, email_display, password_hash, email_verified_at?, password_changed_at, version |
| auth_sessions | id, user_id? FK(users), token_hash UNIQUE, csrf_token_hash, created_at,last_seen_at,absolute_expires_at,idle_expires_at,revoked_at?,reauthenticated_until?. user_id NULL은 임시 로그인 전 세션 |
| auth_action_tokens | id,user_id FK, purpose:verify_email/reset_password, token_hash UNIQUE, expires_at,consumed_at? |
| auth_mail_outbox | id,user_id?,kind,encrypted_payload,status,created_at,expires_at,sent_at?,attempt_count. 원문 토큰은 발송에 필요한 짧은 기간만 암호화 보관 후 제거 |

회원 users의 상태 pending_verification/active/deleting 등을 인증 처리에서 검증한다. 일반 로그에 이메일 원문·비밀번호·쿠키·토큰·메일 본문·암호화 키를 기록하지 않는다. 임시/만료 세션과 소비/만료 토큰은 정기 청소한다. 가입/메일 요청 실패 시 트랜잭션 처리와 재전송으로 유령 계정·중복 발송을 통제한다. 회원 삭제 시 위 개인 인증 데이터도 정리하고 삭제 영수증은 jobs의 별도 만료 수명으로 관리한다.

소셜 auth_identities, OAuth 콜백·공급자 버튼은 이번 테이블/API 범위에서 제외한다. 추후 도입 시 이메일 일치만으로 계정을 자동 병합하지 않고 별도 계정 연결 계약을 만든다.

## 6. 진행 상태와 다음 결정

D01은 이메일·비밀번호 방식 및 관련 API 설계 문서 작성으로 완료 처리한다. 세션 수명·제한 값은 구현 시 검증 가능한 설계 기본값이며 성능·운영 요구에 따라 명세와 함께 조정한다. 인증 기능 F02, 인증 테이블 DDL, 메일 공급자/발송 설정과 운영 보관 정책은 미완료다.

다음 착수 전 결정은 D02(지원 지역·지도/교통/AI 공급자)다. 구현 단계로 건너뛰지 않는다. 메일 공급자 선택은 F02 구현 전 의존 작업으로 별도 TODO에 남긴다.

설계 참고: [OWASP 비밀번호 저장](https://cheatsheetseries.owasp.org/cheatsheets/Password_Storage_Cheat_Sheet.html), [인증](https://cheatsheetseries.owasp.org/cheatsheets/Authentication_Cheat_Sheet.html), [비밀번호 재설정](https://cheatsheetseries.owasp.org/cheatsheets/Forgot_Password_Cheat_Sheet.html).
