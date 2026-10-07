# 백엔드 실행 환경

개발 앱은 http://localhost:5173 또는 http://127.0.0.1:5173으로 열 수 있다. AUTH_PUBLIC_ORIGIN의 같은 포트에서만 두 loopback 주소를 허용하며 운영은 설정한 HTTPS origin과 정확히 일치해야 한다. CSRF 토큰/세션 쿠키 검증은 양쪽 모두 적용한다.

F00-01~04 및 기본 회원 인증 구현 완료. 상태 API·요청 ID·공통 HTTP 오류·JSON 요청 로그와 React 연결을 제공한다. 경로/현재 위치/약속 API는 미구현이다. PostgreSQL은 health 요청과 분리하며 [DB 안내](../database.md)를 참고한다.

F03-01(2026-10-07): POST /place-searches, POST /places, GET /places 및 GET /places/{place_id} 구현. 실행 전 `backend/.venv/Scripts/python.exe backend/migrate.py upgrade head`로0003_saved_places 적용. KAKAO_REST_API_KEY는 서버 .env에만 저장한다. [place_api.md](../place_api.md)의 후보/만료/멱등·오류 계약을 따른다. 장소 수정/삭제·지도 핀·현재 위치·경로/약속 API는 후속이다.

2026-10-06 기본 회원 인증 구현: GET /auth/csrf, POST /auth/register·login·logout, GET /me. 이메일 중복만 확인하며 메일 인증/복구는 후순위다. 실행 전에 DB와0004_place_map_pin 마이그레이션을 준비한다. `.env.example`의 AUTH_ENV/AUTH_PUBLIC_ORIGIN 및32자 이상 독립 난수 AUTH_RATE_LIMIT_SECRET을 로컬 `.env`에 설정한다(기존 .env 덮어쓰기 금지). 운영은 HTTPS origin·Secure 쿠키를 사용한다. health는 DB/인증 설정 없이 계속 동작한다. 장소 API는 아래 F03-01 범위를 따른다.
Python 3.13.1에서 FastAPI 0.142.2 / Uvicorn 0.54.0을 설치했고 전체 의존성 버전을 requirements.txt에 고정했다.

프로젝트 루트에서 PowerShell로 실행한다. 가상환경 활성화 없이 전용 Python 경로를 직접 사용한다.

```powershell
cd C:\projects\timeisnow
python -m venv backend/.venv
& backend/.venv/Scripts/python.exe -m pip install -r backend/requirements.txt
& backend/.venv/Scripts/python.exe -m uvicorn app.main:app --app-dir backend --host 127.0.0.1 --port 8000 --no-access-log
```

`http://127.0.0.1:8000/docs`에서 GET `/api/v1/health`를 확인할 수 있다. health는200 data/meta, 미존재 경로404 및 잘못된 방식405 등은 error/meta와 X-Request-ID로 응답한다. 입력/예외 원문은 반환하지 않는다. 프론트 설정의 서버 연결 카드에서 로딩·성공·실패/재시도와 요청 ID를 확인한다. Ctrl+C로 종료한다. DB 상태/교통/AI 연결 검사는 health와 별개다.

- app/main.py: FastAPI 앱 진입점.
- app/request_logging.py: 허용된 요청 메타데이터만 JSON 한 줄 stdout으로 출력. INFO 완료1회, 예상 밖 예외는 같은 ID의 ERROR 실패1회 추가. 처리시간은 응답 생성까지의 서버 처리시간이다.
- requirements.txt: 같은 라이브러리 버전으로 다시 설치하기 위한 목록.
- .venv/: 이 프로젝트의 Python과 라이브러리. Git 제외.
- 시작/종료 로그는 Uvicorn 기본 로그다. 실행 명령의 --no-access-log를 유지해 원문 URL 접근 로그를 끄고 앱의 안전한 JSON 요청 로그를 확인한다. route는 템플릿, 미존재 경로는 unmatched로 기록한다. 본문/쿼리/헤더/쿠키/키/IP·실제 경로·예외 메시지/스택은 출력하지 않는다.

프론트는 별도 터미널에서 `cd C:\projects\timeisnow\frontend` 후 `npm run dev`로 실행한다. 기존 npm 잠금 파일을 유지한다. 앱 진입점 실행에는 DB 접속이 필수가 아니며 DB 검증은 check_db.py로 별도 실행한다.

DB 변경은 [마이그레이션 안내](../migrations.md)의 migrate.py로 실행한다. 현재는0004_place_map_pin까지 적용했다.

## 환경 변수와 로그 확인

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
