# 백엔드 실행 환경

F00-01 환경 준비 완료. 상태 API·요청 추적·인증은 아직 미구현이다. PostgreSQL 연결은 구성했으며 [DB 안내](../database.md)를 참고한다.
Python 3.13.1에서 FastAPI 0.142.2 / Uvicorn 0.54.0을 설치했고 전체 의존성 버전을 requirements.txt에 고정했다.

프로젝트 루트에서 PowerShell로 실행한다. 가상환경 활성화 없이 전용 Python 경로를 직접 사용한다.

```powershell
cd C:\projects\timeisnow
python -m venv backend/.venv
& backend/.venv/Scripts/python.exe -m pip install -r backend/requirements.txt
& backend/.venv/Scripts/python.exe -m uvicorn app.main:app --app-dir backend --host 127.0.0.1 --port 8000 --no-access-log
```

`http://127.0.0.1:8000/docs`에 빈 API 문서가 표시된다. 업무 API가 없으므로 루트와 `/api/v1/health`는 아직 404다. Ctrl+C로 종료한다. 프론트엔드와의 연동은 다음 F00-02에서 수행한다.

- app/main.py: FastAPI 앱 진입점.
- requirements.txt: 같은 라이브러리 버전으로 다시 설치하기 위한 목록.
- .venv/: 이 프로젝트의 Python과 라이브러리. Git 제외.
- 시작/종료 로그는 Uvicorn 기본 로그다. 사용자 요청 URL을 출력하는 기본 접근 로그는 끄고 F00-04에서 명세의 구조화 요청 로그를 추가한다.

프론트는 별도 터미널에서 `cd C:\projects\timeisnow\frontend` 후 `npm run dev`로 실행한다. 기존 npm 잠금 파일을 유지한다. 앱 진입점 실행에는 DB 접속이 필수가 아니며 DB 검증은 check_db.py로 별도 실행한다.

DB 변경은 [마이그레이션 안내](../migrations.md)의 migrate.py로 실행한다. 현재는 빈 0001_baseline만 적용했다.
