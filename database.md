# PostgreSQL 개발 DB

- 현재 적용(2026-10-07):0006_journey_searches. 기존 회원/장소를 유지하며 짧은 경로 후보/작업/멱등 테이블 추가. 아래 baseline/미적용 안내는 초기 구축 이력이며 최신 실행 기준은 [migrations.md](./migrations.md).

- 확정일: 2026-10-02. 로컬 개발용이며 운영 배포 구성은 별도 결정한다.
- Docker Compose 프로젝트: timeisnow / 서비스: db / 컨테이너: timeisnow-db-1.
- 이미지: postgres:17 (이번 실행 버전 17.11). 메이저 버전을 고정하며 pull 시 패치 버전은 바뀔 수 있다.
- 접속: 127.0.0.1:5432 / DB: timeisnow / 사용자: timeisnow.
- 비밀번호: 루트 .env. 실제 값은 출력·커밋하지 않는다. .env.example은 빈 비밀번호 예제다.
- 영속 볼륨: timeisnow_postgres_data. 컨테이너 재생성 후에도 데이터가 유지된다.
- React → FastAPI → PostgreSQL. 브라우저에서 DB에 직접 접속하지 않는다.

## 실행과 종료

프로젝트 루트 PowerShell에서:

```powershell
cd C:\projects\timeisnow
docker compose up -d --wait db
docker compose ps
& backend/.venv/Scripts/python.exe backend/check_db.py
docker compose stop db
```

현재 DB는 실행 중이다. stop은 데이터를 유지하고 정지한다. 다시 up으로 시작한다. docker compose down도 볼륨을 유지하지만 **down -v는 데이터를 삭제**하므로 일반 종료에 사용하지 않는다.

새 PC에서는 .env.example을 .env로 복사하고 비밀번호를 설정한 다음 시작한다. 기존 볼륨이 있으면 .env 비밀번호 수정만으로 DB 비밀번호가 변경되지 않는다. 초기화 대신 별도의 비밀번호 변경 절차를 사용한다.

## Python 연결

backend/app/database.py의 connect_db()는 루트 .env와 프로세스 환경을 읽으며 프로세스 설정이 우선한다. with connect_db() 구문으로 사용해 트랜잭션과 연결을 정리한다. 접속 제한은 5초다. 동기 드라이버이므로 향후 FastAPI 비동기 핸들러에서 직접 블로킹 호출하지 않도록 실행 방식을 정한다.

check_db.py는 SELECT 1과 서버 버전을 확인하고 성공/실패 JSON 로그 및 종료 코드 0/1을 반환한다. 오류 원문이나 접속 비밀번호는 출력하지 않는다. HTTP /health 계약은 변경하지 않았다.

## 검증과 남은 일

Compose 설정 검사, healthy 상태, Python 호스트 접속, SELECT 1, 컨테이너 재생성 후 테스트 값 42 유지, 잘못된 포트에서 안전한 실패 로그, pip check를 확인했다. 검증 전용 테이블은 삭제했다.

F00-05의 DB 구성·연결 및 Alembic 마이그레이션 기반은 완료했다. 현재 alembic_version에 0001_baseline만 적용했으며 업무 테이블은 미생성이다. [마이그레이션 안내](./migrations.md). 현재 로컬 DB 사용자는 초기화 관리자 권한이므로 운영 전에 앱/마이그레이션 권한 분리와 백업·복구 정책을 정한다.

이미지 초기화·환경변수·볼륨 기준: [PostgreSQL 공식 Docker 이미지](https://hub.docker.com/_/postgres).


## 테이블과 관계 설계

[database_schema.md](./database_schema.md)에 MVP·약속 테이블, ER 다이어그램, 주요 컬럼·제약·삭제 정책과 단계별 생성 순서를 정리했다. 현재 설계 초안이며 실제 업무 테이블은 생성하지 않았다.
