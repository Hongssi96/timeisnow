# 역 내부·환승 본인 기록 기반 추정 — F09-09

기준: [Notion API 명세 5.15](https://app.notion.com/p/3ebace1670c6806c8199cde33ebfbdfa), v0.96 / 2026-10-16. 사용자 승인: 같은 구간의 수동 시작·도착 기록을 5회 이상 모아 본인 기록 기반 추정으로 적용한다.

## 흐름과 API

기본 경로 `/api/v1/trips/{trip_id}/walking-segments`. 모든 API는 본인 이동만 허용하며 쓰기는 CSRF가 필요하다. 활성 루틴의 현재 접근·환승 중에 시작한다. 지하철 입구→승차 지점은 `station_internal`, 직전 하차→다음 승차 지점 전체는 `transfer`다. 이름에 입구·승강장·방향을 구별한다.

| 방식 | 경로 | 입력·응답 |
| --- | --- | --- |
| GET | 기본 경로 | `items` 측정 목록, `available` 현재 시작 가능 유형/leg/name 및 이전 이름별 표본/추정(최근20개 이름) |
| POST | 기본 경로 | `client_request_id`, `kind`, `leg_id`, `label` 1~60자, `occurred_at` 시간대 ISO, `start_boundary_confirmed:true` → 최초201/같은 요청200 |
| POST | `/{measurement_id}/confirm` | `expected_version`, `client_request_id`, `same_scope`, `condition`, `apply_to_guidance` →200 |
| PATCH | `/{measurement_id}` | 종료/취소 이동만 `expected_version`, `client_request_id`, `excluded` →200 |

측정 응답은 `measurement_id/kind/leg_id/label/status/version/started_at/finished_at/observed_seconds/predicted_seconds/predicted_arrival_at/sample_count/estimate_seconds/valid_until/basis_key/reasons/can_finish/apply_to_guidance`. 상태는 recording/valid/excluded. 표본5개 미만의 추정·기한은 null이다. condition은 normal/running/detour/errand/late_input. 쓰기 재시도는 같은 UUID/정규화 본문, 변경409·버전409·없음/타인/만료404·인증401·CSRF403·입력422. 확인/제외 영수증24시간, 시작 멱등키는 기록 보관기간 동안 유지한다.

## 계산·보존

- 끝 시각은 기존 수동 `approach_arrived`만 사용한다. 시작 전 departed/alighted와 순서를 검사하며 시작/도착 입력지연0~60초, 구간1~7200초·동일 범위·평소 걸음만 유효하다. 대기/탑승 시각으로 역산하지 않는다. 도착 누락422, 기타 품질 문제는 제외 상태/사유를 저장한다.
- 사용자·루틴/버전·경로 서명·장소 위치 버전·교통구간 순번·유형·이름·초기화 세대로 풀을 분리한다. 회당 kind/leg 하나이며 서로 다른 이동의 최근 유효20개, 최소5개의 중앙값을 초 단위 올림한다. 정정/제외/복원/삭제/만료는 원본 이벤트를 다시 읽어 즉시 재계산한다.
- 명시 적용한 이름만 다음 같은 루틴 안내에 재사용한다. `departure.personal_segment_walks[]`에는 kind/leg_id/label/source=manual_history/profile_version/basis_key/sample_count/estimate_seconds/valid_until을 추가한다. 현재 표본 해시를 게시/새 이동 생성 때 다시 검사해 변경된 안내를409로 차단한다. 공급자 접근 계수를 또 곱하지 않고 여유 시간은 그대로 유지한다.
- 환승 전체 시간은 환승 검사·목표 도착 계산의 기존 환승 도보를 대체한다. 역 내부는 별도 추정/시작 후 도착 예상이며 전체 접근·환승과 중복 합산하지 않는다. 기존 미지원 차량·최신성 차단은 유지한다. 첫 SUBWAY 실시간 출발을 새로 지원하지 않는다.
- 초기화 이전 기록은 BEFORE_RESET으로 제외한다. 첫 BUS 계수 restore는 구간 기록을 되살리지 않는다. 시작 당시 예측은 불변이며 실측 정확도·위치/동선 인증과 구분한다.
- migration0022: walking_segment_measurements/선택 테이블. 개인 기록90일, 이동/계정 삭제 cascade, 만료/고아 원문 영수증/선택 정리. 개인정보 이름은 외부 AI/공급자/일반 로그에 전송하지 않는다. 기존 JSON 내보내기 v1의 각 이동에 `walking_segments[]`를 추가한다. 외부 호출0.

실행 검증 결과와 미완료 범위는 development_log.md의 F09-09를 따른다.
