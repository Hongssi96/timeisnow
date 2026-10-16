# 백엔드 실행 환경

F04-02(2026-10-07): app/journeys/models.py(당시 journey_models.py)의 journey.v1 구간/후보 모델과 GET 결과 OpenAPI 스키마를 제공한다. WALKING 접근/환승/마지막 역할, 교통 승하차·공급자 순서·차량 종류, 환승 연결과 시간 분해·누락 근거를 정리하며 기존 JSONB 후보는 조회 시 보강한다. DB head0006 유지·마이그레이션 추가 없음, [journey_api.md](../journey_api.md)·Notion v0.41 참고.

F04-01(2026-10-07): POST /journey-searches202·본인 GET 결과/GET /jobs 구현. 실행 전 `backend/.venv/Scripts/python.exe backend/migrate.py upgrade head`로0006_journey_searches를 적용한다. 현재는 depart_now 공급자 후보 조회이며 AI/실시간/목표 도착/비교 화면은 후속이다. GPS/지도 입력 좌표 비저장 및 상태/권한/멱등/만료는 [journey_api.md](../journey_api.md)를 따른다.

개발 앱은 http://localhost:5173 또는 http://127.0.0.1:5173으로 열 수 있다. AUTH_PUBLIC_ORIGIN의 같은 포트에서만 두 loopback 주소를 허용하며 운영은 설정한 HTTPS origin과 정확히 일치해야 한다. CSRF 토큰/세션 쿠키 검증은 양쪽 모두 적용한다.

F00-01~04 및 기본 회원 인증 구현 완료. 상태 API·요청 ID·공통 HTTP 오류·JSON 요청 로그와 React 연결을 제공한다. 경로/현재 위치/약속 API는 미구현이다. PostgreSQL은 health 요청과 분리하며 [DB 안내](../database.md)를 참고한다.

F03-01(2026-10-07): POST /place-searches, POST /places, GET /places 및 GET /places/{place_id} 구현. 실행 전 `backend/.venv/Scripts/python.exe backend/migrate.py upgrade head`로0003_saved_places 적용. KAKAO_REST_API_KEY는 서버 .env에만 저장한다. [place_api.md](../place_api.md)의 후보/만료/멱등·오류 계약을 따른다. 장소 수정/삭제·지도 핀·현재 위치·경로/약속 API는 후속이다.

2026-10-06 기본 회원 인증 구현: GET /auth/csrf, POST /auth/register·login·logout, GET /me. 이메일 중복만 확인하며 메일 인증/복구는 후순위다. 실행 전에 DB와0005_place_management 마이그레이션을 준비한다. `.env.example`의 AUTH_ENV/AUTH_PUBLIC_ORIGIN 및32자 이상 독립 난수 AUTH_RATE_LIMIT_SECRET을 로컬 `.env`에 설정한다(기존 .env 덮어쓰기 금지). 운영은 HTTPS origin·Secure 쿠키를 사용한다. health는 DB/인증 설정 없이 계속 동작한다. 장소 API는 아래 F03-01 범위를 따른다.
Python 3.13.1에서 FastAPI 0.142.2 / Uvicorn 0.54.0을 설치했고 전체 의존성 버전을 requirements.txt에 고정했다.

프로젝트 루트에서 PowerShell로 실행한다. 가상환경 활성화 없이 전용 Python 경로를 직접 사용한다.

```powershell
cd C:\projects\timeisnow
python -m venv backend/.venv
& backend/.venv/Scripts/python.exe -m pip install -r backend/requirements.txt
& backend/.venv/Scripts/python.exe -m uvicorn app.main:app --app-dir backend --host 127.0.0.1 --port 8000 --no-access-log
```

`http://127.0.0.1:8000/docs`에서 GET `/api/v1/health`를 확인할 수 있다. health는200 data/meta, 미존재 경로404 및 잘못된 방식405 등은 error/meta와 X-Request-ID로 응답한다. 입력/예외 원문은 반환하지 않는다. 프론트 설정의 서버 연결 카드에서 로딩·성공·실패/재시도와 요청 ID를 확인한다. Ctrl+C로 종료한다. DB 상태/교통/AI 연결 검사는 health와 별개다.

- app/main.py: FastAPI 앱 진입점. 라우터 조립·미들웨어·전역 예외만 담당한다.
- app/common/: 공통 계층(errors·timeutil·database·response·http·request_logging). 도메인 로직을 담지 않는다. request_logging은 허용된 요청 메타데이터만 JSON 한 줄 stdout으로 출력하며 INFO 완료1회, 예상 밖 예외는 같은 ID의 ERROR 실패1회 추가. 처리시간은 응답 생성까지의 서버 처리시간이다.
- app/auth/, app/places/, app/origins/, app/journeys/, app/routines/: 도메인별 3계층 패키지. router(엔드포인트)→service(비즈니스 규칙)→repository(SQL) 순으로만 의존하고, DTO는 dto.py, 외부 API 클라이언트는 provider.py에 둔다. auth는 security.py에 세션/CSRF/레이트리밋 공통 인증을 제공하며 journeys/models.py는 공통 구간 모델이다.
- requirements.txt: 같은 라이브러리 버전으로 다시 설치하기 위한 목록.
- .venv/: 이 프로젝트의 Python과 라이브러리. Git 제외.
- 시작/종료 로그는 Uvicorn 기본 로그다. 실행 명령의 --no-access-log를 유지해 원문 URL 접근 로그를 끄고 앱의 안전한 JSON 요청 로그를 확인한다. route는 템플릿, 미존재 경로는 unmatched로 기록한다. 본문/쿼리/헤더/쿠키/키/IP·실제 경로·예외 메시지/스택은 출력하지 않는다.

프론트는 별도 터미널에서 `cd C:\projects\timeisnow\frontend` 후 `npm run dev`로 실행한다. 기존 npm 잠금 파일을 유지한다. 앱 진입점 실행에는 DB 접속이 필수가 아니며 DB 검증은 check_db.py로 별도 실행한다.

DB 변경은 [마이그레이션 안내](../migrations.md)의 migrate.py로 실행한다. 현재는0005_place_management까지 적용했다.

## 환경 변수와 로그 확인

F03-03: PATCH /places/{place_id} label 수정·DELETE204 추가. 최신 head0005_place_management, 기존 장소 보존/location_version 초기화. 삭제된 생성 키는place_id=NULL로24시간 최소 표시를 유지하며 같은 저장 키/본문 재시도404. 일반version 수정 충돌 및location_version 위치 근거를 구분한다. 실제 루틴/산정 연결은 후속. [place_api.md](../place_api.md)와 Notion v0.37 기준.

F03-02: GET /map-config, POST /place-location-confirmations 및 PATCH /places/{place_id} 추가. 최신 head는0004_place_map_pin, 기존 장소 보존. KAKAO_JAVASCRIPT_KEY는 등록 도메인 제한용 공개 SDK 키이며 로그인된 /map-config로 전달한다. KAKAO_REST_API_KEY는 서버에서만 사용한다. 카카오 앱에서 지도 API 활성화/localhost:5173 및127.0.0.1:5173 SDK 도메인 등록 필요. 지도 핀·소유권/600초/버전409 계약은 [place_api.md](../place_api.md). 서버 코드를 바꾼 후 개발 백엔드를 재시작해야 새 API가 적용된다.

루트 `.env.example`은 빈 공급자 키와 예시 DB/AI URL을 담는다. 기존 `.env`를 덮어쓰지 않는다. 새 체크아웃에서 `.env`가 없을 때만 다음을 실행하고 발급받은 값을 로컬 파일에 입력한다.

```powershell
if (-not (Test-Path -LiteralPath .env)) { Copy-Item -LiteralPath .env.example -Destination .env }
```

LOG_LEVEL은 `.env` 또는 프로세스 환경 변수로 INFO(기본)/WARNING/ERROR를 설정한다. 프로세스 값이 우선이며 미지원 값은 INFO로 처리한다. WARNING/ERROR에서는 INFO 완료 로그가 필터링된다. 변경 후 백엔드를 재시작한다. 서버 API 키를 프론트 VITE_ 변수에 넣지 않는다.

별도 터미널에서 다음 요청을 보내고 X-Request-ID/meta.request_id와 서버 JSON 로그의 request_id가 같은지 확인한다. 프론트 설정의 문의용 요청 ID로도 대조할 수 있다.

```powershell
curl.exe -i http://127.0.0.1:8000/api/v1/health
curl.exe -i http://127.0.0.1:8000/api/v1/does-not-exist
```

첫 요청은200·route=/api/v1/health, 두 번째는404·route=unmatched·error_code=RESOURCE_NOT_FOUND다. 예상 밖 오류는500 응답과 ERROR http.request.failed/INFO http.request.completed가 같은 ID로 연결된다. 터미널 너비에 따른 화면 줄바꿈과 실제 JSON 레코드의 한 줄 출력을 구분한다.

백엔드 로그/응답 계약 검증은 다음처럼 DB/외부 API 없이 실행한다.

```powershell
& backend/.venv/Scripts/python.exe -m unittest discover -s backend/tests -p test_request_logging.py
& backend/.venv/Scripts/python.exe -m unittest discover -s backend/tests -p test_api_contract.py
```

현재는 stdout만 제공하며 로그 파일이나 원격 수집기를 만들지 않는다. 14일 보관/회전은 배포 설정(F11)에서 적용한다. 명령/오류 로그에 실제 키·주소를 붙여 공유하지 않는다.
F03-04(2026-10-07): POST /origin-validations 구현. 단발GPS/지도 서울·경기 확인 및 본인 저장 장소/location_version 검증, 로그인·Origin/CSRF·no-store·사용자10회/분(실패 포함). 좌표를 새 DB/로그에 저장하지 않으며 현재GPS quality_status=pending,600초 선택·실제 경로 계산 후속. DB head0005 유지, 서버 재시작 후 적용. [origin_api.md](../origin_api.md)·Notion v0.38.

## F06-03 루틴 관리 (2026-10-08)
GET /routines(limit/cursor), PATCH /routines/{id}(이름/일정·전체 경로 참조 교체), DELETE /routines/{id}204를 제공한다. 본인 목록과 버전/CSRF/삭제 멱등 표시는 [routine_api.md](../routine_api.md)를 따른다. 최신 마이그레이션은0008_routine_schedule이며 추가 DDL은 없다. 코드 반영 후 서버를 재시작한다. 개발 서버의 네트워크 제한과 DB 상태는 별개이며 카카오 API에 접근 가능한 실행 환경이 필요하다.
F06-04(2026-10-08): 장소 location_version이 증가하면 연결된 본인 루틴을 같은 트랜잭션에서 needs_attention/version+1로 바꾼다. label만 변경/동일값 수정은 루틴을 유지한다. 장소 변경/삭제와 경로 교체는 기존 회원별 routine-write 잠금을 공유한다. 기존0008 DDL/응답 유지. 로컬 서버 재시작 적용, 루틴13개 포함 백엔드130개 회귀 통과. routine_api.md·Notion v0.49 참고.

## F05-02 프롬프트 블록 로딩 (2026-10-12)

app.ai.prompt_loader의 load_prompt('walking_estimate', expected_version='walking_estimate.v1')는 common.v1 SYSTEM과 walking_estimate.v1 DEVELOPER, 두 버전을 포함한 불변 PromptBundle을 반환한다. messages()로 별도 역할 메시지를 받으며 입력 JSON은 후속 서비스에서 별도로 전달한다. 경로 설명은 journey_explanation.v2를 지원한다. 자연어 일정은 F17에서 별도 SYSTEM을 연결한다.

app/ai/prompts의 UTF-8 JSON 리소스를 배포 코드와 함께 보존한다. 파일 누락/손상·역할/버전 불일치·지원하지 않는 작업은 안전한 PromptLoadError이며 AI 호출로 진행하지 않는다. ai_prompts.md와 리소스 문구·버전 일치 검증은 test_prompt_loader.py를 실행한다. API/DB 변경과 AI 호출은 없으며 후속 F05-03에서 서비스에 연결한다.

## F05-03 내부 AI 도보 산정 (2026-10-12)

app/ai/walking_dto.py(최소 입출력), walking_service.py(준비 근거 분류/검산), provider.py(Responses 전송)를 사용한다. 공개 HTTP API는 추가하지 않는다. estimate 호출 전 소유권/근거 유효성·물리 범위 확인은 후속 호출 서비스 책임이다. 기존 미확인 Evidence의 estimate_evidence는 이름/좌표를 제거하고 needs_data로 반환하며 외부 호출하지 않는다.

AI 실패 원문·키·전체 URL·본문은 출력하지 않는다. DTO/JSON Schema·거절·미완료·ID/근거/범위/수식 검증 및 최대1회 형식 재시도는 ai_prompts.md13절/Notion v0.53을 따른다. 저장·품질 이력·재사용·화면 연결은 후속이다. 로컬 합성 검증: backend/.venv/Scripts/python.exe -m unittest discover -s backend/tests -p test_ai_walking.py. 실제 서버 승인 후 check_ai_walking.py로 개인정보 없는 합성 요청 최대1회와 검산 결과만 확인할 수 있다. 2026-10-12 실제 합성 요청의 strict 응답·360초 서버 검산 성공(2.51초)을 확인했다.

2026-10-12 실호출 후속: 사용자 승인된 구조화 합성 요청1회를 실행했지만503 PROVIDER_UNAVAILABLE로 실패했다. 키 존재/모델/호스트 설정은 로컬 재확인 정상이며 공급자 인증/요청 형식/가용성 중 원인은 미확정이다. 다음 진단 도구는 upstream_http_status와 허용된 upstream_error_code만 추가 출력한다. 원문/키/URL은 출력하지 않고 공개 오류 형식도 유지한다. 추가 호출은 아직 실행하지 않았다.

2026-10-12 최종: HTTP400의 max_output_tokens 오류 진단 후 출력 한도를512로 낮춰 실제 합성1후보 검산 성공. 응답 미완료는 거부하며 다수 후보/실제 보행 품질·운영 서비스 연결은 후속이다. 공급자 오류 진단에는 상태·허용 오류코드·고정 분류태그만 포함한다.

## F05-04 산정 이력·본인조회 (2026-10-12)

실행 전 backend/.venv/Scripts/python.exe backend/migrate.py upgrade head로0009_walking_history 적용. 신규4테이블과 GET /api/v1/walking-estimates/{estimate_id}, 내부 walking/history_service.py의 persist/estimate_and_store/record_failure/purge_expired_history를 제공한다. 내부 호출자는 Context의 물리경로/방향/범위 확인과 소유권 근거를 먼저 확보해야 하며 공개 쓰기 API는 없다. 현재 미확인Evidence는 유효산정 저장을 차단한다. 일반조회는reused=false, 조건별캐시는F05-05후속.

정상/실패/중복실행·검산·본인/장소/프로필/근거기한·30일유효/90일품질·삭제/청소 계약은 walking_api.md·Notion v0.54 참고. 원문/키/좌표/모델 자유문reason 비저장. 테스트는 실제DB 임시스키마·합성AI로 test_walking_history.py를 실행한다. 서버코드 반영 후 백엔드 재시작이 필요하다.

동시 실행 보강: estimate_and_store는 사용자/request_id별DB 세션advisory 잠금으로 두 번째 AI 호출을 차단하고 내부409 EXECUTION_IN_PROGRESS를 반환한다. 완료한 동일 실행은 모델 재호출 없이 조회한다. 장소 수정 잠금은 모델 호출 동안 유지하지 않고 저장 전 위치 버전을 다시 검사한다.


F07-02(2026-10-13): 본인 활성 검색 후보의 first-departure GET으로 첫 버스 예상 출발을 계산한다. 사용자 승인 공급자 접근 도보×개인 계수 추정·기본여유300초, 후보 상세 표시/60초 재평가·기한/부족 차단. 로컬DB head0012_departure_profile·기존 데이터 보존 확인. 계수의 기본1.0/0.5~2.0은 GET /auth/me의 profile에 추가된다. 루틴 자동갱신/전체환승·목표도착/실제 보행·예측 정확도 확인은 후속이다. 상세 departure_api.md·Notion v0.73.

## 보관 만료 관리 (F09-08)
서버가 시작된 뒤 및 매시간 기존 보관 기한을 정리하고, 만료 표본의 영향을 제거하도록 개인 계수/유효 산정을 함께 갱신한다. 본인 인증 요청에서도 사용 전에 같은 처리를 실행한다. 수동 실행(프로젝트 루트 PowerShell):

```powershell
$env:PYTHONPATH='backend'
backend/.venv/Scripts/python.exe -m app.retention
```

checked/changed/rebuilt/failed 집계만 출력하며 실패가 있으면 종료코드1이다. 실패 사용자는 롤백·나머지 계속, 다음 실행에서 재시도한다. 별도 외부 API·DDL·화면 변경 없음. 계약/보관/동시성/정확한 범위는 ../retention_api.md, 검증은 ../development_log.md.
