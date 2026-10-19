# 개인 이동 설정 저장 — F11-01

2026-10-19 · Notion v0.97 / 5.16: https://app.notion.com/p/3ebace1670c6806c8199cde33ebfbdfa

## 계약

`PATCH /api/v1/me/profile`: 쿠키 본인·Origin/CSRF·no-store. `expected_version` 양수 정수와 아래 필드 하나 이상 필수, 생략값 보존. null/알 수 없는 필드/타인 ID/클라이언트 계수·시간대는422.

| 필드 | 허용값·단위 |
| --- | --- |
| walking_preference | slow / normal / fast (자기보고) |
| route_preference | balanced / fewer_transfers / less_walking |
| first_boarding_buffer_seconds | 0~1800 정수 초, 기본300 |
| transfer_buffer_seconds | 0~1800 정수 초, 기본120 |

200 data는 `{profile, profile_version}`. profile은 GET /me와 동일하며 `profile.version=profile_version`. 미인증/만료401, CSRF403, 버전409 VERSION_CONFLICT, 입력422, DB장애503. 기존 가입 기본값/GET /me/계수/Asia/Seoul·테이블 유지, 새 DDL 없음. 입력 본문/쿠키/CSRF·개인 값은 일반 로그에 남기지 않으며 기존 최소 요청 로그 사용.

```json
{
  "expected_version": 1,
  "first_boarding_buffer_seconds": 377,
  "transfer_buffer_seconds": 59,
  "walking_preference": "slow",
  "route_preference": "less_walking"
}
```

## 저장과 영향

기존 본인 이동→루틴/도보 소유자→학습/프로필 잠금 순서를 재사용한다. 같은 값은 버전/산정을 유지한다. 실제 변경은 버전+1과 검증된 유효 도보 산정의 프로필 revision을 같은 트랜잭션에서 갱신하고 실패 시 모두 롤백한다. 계수/원본 기준초/과거 예측·기록/학습 세대·표본은 보존한다. AI/지도 재호출·TTL 연장 없음.

- 첫 탑승 여유: 다음 안내의 첫 출발 계산에 반영.
- 환승 여유: 다음 순차 환승의 최소 승차 시각에 반영.
- 경로 선호: 새 비교 화면의 기본값/새 검색 정렬에 반영. 화면에서 선택한 기준이 우선하며 저장 루틴 경로는 자동 교체하지 않는다.
- 보행 선호: 선택값만 저장. 문구만으로 계수/실제 속도를 추정하지 않고 기존 유효 관측 기반 학습·초기화·복구 유지.

## 화면·검증

내 설정에서 본인 서버값을 분·초로 표시하며 합계 정수 초를 명시 저장한다. 30분1초/소수/빈 입력 거절, 0초/초 단위 보존. 중복 차단·저장 중 비활성·실패 초안 유지·충돌 시 최신 설정 조회·인증 만료/계정 변경 시 초안 제거. 저장 직전 CSRF와 본인 계정을 재검사하며 다른 탭 로그인 뒤 이전 계정 초안을 새 계정에 적용하지 않는다. 새로고침/재로그인 후 서버값 복원, 저장 후 학습 카드 버전 재조회.

영향 설명은 기존 모달, 입력/카드/행동은 기존 디자인을 재사용한다. 실제 테스트·PC/모바일 검증 결과는 development_log.md F11-01을 따른다.
