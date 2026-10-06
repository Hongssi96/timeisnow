# 지금이니? — 기본 회원 인증 계약

- 버전0.4 / 2026-10-06 / Notion v0.33 기준
- 메일 인증은 후순위, 개발 loopback 주소 호환 및 운영 origin 검증을 유지한다.

## 17. 이메일·비밀번호 회원 인증 — 첫 버전
사용자 변경(2026-10-06): 메일 소유 확인은 후순위다. 정규 이메일 중복만 확인해 가입시키며 이메일을 실제 소유한다고 표현하지 않는다. 가입 즉시 active, 자동 로그인 없음. 확인메일/복구메일/메일 토큰/outbox/pending 계정 및 메일 공급자 준비는 현재 구현 범위에서 제외한다.
### 입력·저장
- email: trim 후 최대254자, ASCII 이메일 형식, 전체 소문자 정규화. 점/플러스 주소는 합치지 않는다. DB UNIQUE로 동시 가입도 중복 방지, 중복409 EMAIL_UNAVAILABLE. 기존 회원 비밀번호를 덮어쓰지 않는다.
- password:15\~128 Unicode 코드 포인트, 공백/붙여넣기 허용, trim/절단/대소문자 변환 금지. Argon2id(memory19456KiB/time2/parallelism1) 해시 저장. 최소 일반 비밀번호 차단 목록을 적용하며 전체 유출 목록 연동은 후순위다.
- display_name:trim 후1\~30자. 첫 프로필:walking_preference=normal,first_boarding_buffer_seconds=300,transfer_buffer_seconds=120,route_preference=balanced,timezone=Asia/Seoul,version=1.
- users/auth_credentials/user_profiles/auth_sessions/auth_rate_limit_buckets를 사용한다. 메일 확인 상태/토큰/메일 큐 테이블은 만들지 않는다. 회원/자격정보/프로필을 동일 트랜잭션으로 생성한다.
### 세션과 CSRF
- 서버 저장 세션:256비트 이상 난수, DB에는 SHA256 해시만 저장. 로그인7일 절대 만료·미사용24시간, 로그인 전 임시 세션15분. 인증 세션은 회원 active 상태를 검사한다.
- 운영 쿠키 __Host-timeisnow_session,Secure,HttpOnly,SameSite=Lax,Path=/,Domain 없음. 개발 HTTP 쿠키 timeisnow_dev_session,Secure=false. AUTH_ENV=development/production 및 고정 AUTH_PUBLIC_ORIGIN 설정; 운영 HTTPS 필수, 개발 origin은 [localhost/127.0.0.1만](http://localhost/127.0.0.1만) 허용. 잘못된 설정/DB 장애는503 SERVICE_UNAVAILABLE.
- GET /auth/csrf는 임시/기존 세션의 CSRF 토큰을 교체해 반환한다. CSRF 원문은 프론트 메모리에만 유지하며 서버에는 해시를 저장한다. 새로고침 시 재조회.
- 가입/로그인/로그아웃 POST는 Origin 및 X-CSRF-Token을 검사, 실패403 CSRF_INVALID. 운영은 설정된 HTTPS Origin과 정확히 일치해야 한다. 개발은 AUTH_PUBLIC_ORIGIN에 설정된 동일 HTTP 포트의 `localhost`와 `127.0.0.1` 두 origin만 허용하며 기본80 포트 표기는 정규화한다. 다른 포트·외부 도메인·Origin 누락/null은 거절한다. CSRF 토큰·세션 쿠키 검사는 유지하며 요청 Host/전달 헤더로 허용 origin을 만들지 않는다. 로그인 시 기존 세션 삭제/새 세션·CSRF 교체, 로그아웃 시 세션 삭제/쿠키 제거.
- 모든 인증 응답 Cache-Control:no-store, 공통 data/meta 또는 error/meta 및 요청 ID. 비밀번호/쿠키/CSRF/이메일 원문을 로그에 남기지 않는다.
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
