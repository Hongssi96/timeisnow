# 마이그레이션 사용 안내

2026-10-02 / F00-05b 완료. Alembic 1.20.0, SQLAlchemy 2.1.1.
현재 개발 DB revision은 `0001_baseline`이다. `alembic_version`만 존재하고 업무 테이블은 없다.

## 실행

프로젝트 루트 PowerShell에서 실행한다. 다른 작업 폴더에서도 migrate.py의 절대 경로로 실행하면 설정 파일을 찾는다.

```powershell
cd C:\projects\timeisnow
docker compose up -d --wait db
& backend/.venv/Scripts/python.exe backend/migrate.py current
& backend/.venv/Scripts/python.exe backend/migrate.py history
& backend/.venv/Scripts/python.exe backend/migrate.py upgrade head
```

current는 DB 적용 위치, history는 파일의 변경 순서다. upgrade head는 아직 적용하지 않은 변경만 순서대로 실행한다. 앱 시작 시 자동 실행하지 않는다. .env 비밀번호를 alembic.ini나 변경 파일에 복사하지 않는다.

## 새 테이블 변경 파일

```powershell
& backend/.venv/Scripts/python.exe backend/migrate.py revision -m "create_users"
```

이 명령은 빈 파일을 생성할 뿐이다. 최신 명세 확인 → upgrade()/downgrade() 작성 → 별도 테스트 DB 검증 → 개발 DB 적용 → 문서/TODO 갱신 순서다. 이미 공유·적용된 변경 파일을 수정하는 대신 새 revision을 만든다.

현재 모델 메타데이터가 없으므로 자동 생성(--autogenerate)은 사용하지 않는다. SQLAlchemy는 Alembic 연결에 사용하며 기존 psycopg 앱 연결 방식을 바꾸지 않는다.

## 되돌리기와 검증

되돌리기는 downgrade의 내용을 실행하는 기능이며 데이터 백업을 대신하지 않는다. 업무 테이블 삭제 등을 포함할 수 있으므로 실제 데이터가 생긴 뒤에는 내용을 확인하고 백업/복구 계획을 세운다. 이번 baseline의 downgrade는 업무 데이터를 변경하지 않는다.

```powershell
# 명시한 이전 revision으로 돌아가는 형식 (이번 빈 baseline 확인용)
& backend/.venv/Scripts/python.exe backend/migrate.py downgrade base
& backend/.venv/Scripts/python.exe backend/migrate.py upgrade head

# 현재 baseline 전용 통합 테스트
& backend/.venv/Scripts/python.exe -m unittest discover -s backend/tests -v
```

테스트는 고유 migration_test_* 스키마만 생성하고 마지막에 제거한다. public은 수정하지 않는다. baseline upgrade 재실행, downgrade 및 반복 왕복을 검증했다. 새 업무 마이그레이션을 추가하면 기대 테이블·head와 롤백 검증도 함께 갱신해야 한다. 향후 public을 명시하는 DDL·확장 설치 등은 스키마 격리만으로 충분하지 않으므로 별도 테스트 DB를 사용한다.

## 파일과 로그

- alembic.ini: 변경 파일 위치. 접속 문자열·비밀 없음.
- backend/migrations/env.py: 기존 connect_db() 설정으로 연결, 트랜잭션 적용.
- backend/migrations/versions/0001_baseline.py: 빈 시작점.
- backend/migrations/script.py.mako: 새 변경 파일 틀.
- backend/migrate.py: 성공/실패 이벤트와 종료 코드 0/1. 원본 접속 예외는 출력하지 않음.
- backend/tests/test_migrations.py: 실제 PostgreSQL에서 초기 이력 왕복 검증.

검증: 통합 테스트 1개 통과, pip check 정상, 개발 DB head 확인, 임시 스키마 잔여 0개, 잘못된 포트의 실패 로그/종료 코드 1 확인. 빈 baseline 검증이므로 업무 데이터 복구나 FK 검증 완료를 뜻하지 않는다.

참고: [Alembic 공식 튜토리얼](https://alembic.sqlalchemy.org/en/latest/tutorial.html).
