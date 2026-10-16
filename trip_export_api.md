# 본인 이동 기록 JSON 내보내기

2026-10-16 / Notion v0.94 §5.13. 기존 미구현 POST /trip-exports 202 계약을 구현한다.

- POST /api/v1/trip-exports: 본인 쿠키·Origin/CSRF, `{from?:시간대 ISO,to?:시간대 ISO,format:"json"}`. 기본 최근90일, 생성시각 [from,to), 최대90일/500건, 사용자10회/분. 범위/형식422, 500건 초과422 EXPORT_LIMIT_EXCEEDED(부분 파일 없음), 인증401/CSRF403/속도429.
- 응답202: job_id, status:succeeded, error:null, result_ref, finished_at, expires_at, download_expires_at. 최대500건 작업을 요청 안에서 준비한다. GET /jobs/{id}, GET /trip-exports/{id}로24시간 조회하며 다운로드 링크는 발급10분 후 null이다.
- GET /trip-exports/{id}/download: 본인 인증·링크10분, 타인/없음/만료404, no-store/nosniff·고정 attachment 파일명. 공통 envelope의 data에 schema_version:trip-export.v1, generated_at, range:{from,to}, records[]를 반환한다. 화면은 data를 JSON 파일로 저장한다.
- records 항목: trip_id, measurement_mode, status, version, created_at, expires_at, 공개 events[], 전체 corrections[], 공개 walking_observation|null. 생성시각/id 오름차순이며 소수점 시각을 보존한다. AI/공급자 원문·좌표·계정/장소/차량ID·내부 해시/학습 표본 참조는 제외한다.
- 다운로드 시 사용자 이동 잠금을 잡아 현재 DB로 구성한다. 정정은 최신 값, 삭제/90일 만료는 제외하고 생성 요청 이후 시작 기록도 제외한다. 서버에는 기간/소유자/기한 메타데이터만 보관하며 파일/이동 ID 목록을 저장하지 않는다. 메타데이터24시간·요청 시 청소·회원삭제 cascade. 새 링크는 새 생성으로 받는다. 이미 내려받은 로컬 파일 회수는 불가하다.
- 이동 기록에서 최근7/30/90일 선택, 준비/빈 결과/실패/재시도/로그인·이탈 취소·중복 클릭 방지. 임시 Blob URL은 다운로드 후 회수한다.

검증: 신규 실제 격리DB/ASGI9개, 관련 회귀65개. 프론트 전체334개 통과 후 기존 selector 충돌 수정·관련6개 통과(총335개 검증), 빌드1922모듈512ms. 실제 합성 계정 HTTP 및 PC1280×900/모바일390×844에서 로그인 차단/기간 선택/1건 JSON 다운로드·가로넘침없음 확인. 외부 공급자/AI0회, 실제 보행 정확도는 검증하지 않았다.

## F09-09 추가 응답 (2026-10-16)
trip-export.v1의 각 records[]에 walking_segments[]를 선택 추가한다. 현재 본인 구간 측정/제외 사유·불변 시작 당시 예측·현재 표본/중앙값을 다운로드 시 읽으며 삭제/만료 기록 사본을 보관하지 않는다. 기존 필드/작업/다운로드 인증·기한은 유지한다. 상세 segment_walking_api.md.
