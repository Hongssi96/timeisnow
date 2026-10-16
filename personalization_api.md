# 개인 보행 기록 학습 API

기준: Notion API 명세 5.10 / v0.91, 2026-10-16. 아래는 첫 BUS 접근 구현 범위이며 F09 전체 완료를 뜻하지 않는다.

### 5.10 개인 보행 기록 학습 F09 (2026-10-16)
- 정책 버전은 manual-walking.v1이다. 수동 관측 판정/계수 변경 이력은 이 버전을 보존한다.
- 첫 구현 범위는 검증된 provider_mapped_access 기준 산정이 안내 스냅샷에 고정된 첫 BUS 접근이다. 실내·역 내부·환승 학습은 준비 중이다. source=manual은 본인 신고이며 실제 이동 인증이 아니다.
- POST /trips/{trip_id}/walking-observation (로그인·Origin/CSRF·no-store): {same_scope:boolean, condition:normal|running|detour|errand|late_input}. 서버가 본인 불변 안내와 departed/approach_arrived 이벤트, 산정 revision/base_seconds/경로 키/장소 위치 버전을 조회한다. 클라이언트 기준초·계수·검증 필드는 받지 않는다. 동일 이동의 최초 요청201, 같은 본문 재시도200, 다른 본문409 IDEMPOTENCY_CONFLICT. 본인 아닌/만료404, 입력422.
- 응답 {observation_id,status:valid|excluded,exclusion_reasons:[],observed_seconds:null|number,profile_version,sample_count,updated:boolean}. 접근 완료 누락·시간 순서·출발 당시 안내 만료·입력 지연60초 초과·범위 불일치·비정상 조건·미검증 기준·장소 변경·초기화 전 관측·지원비율0.5~2 밖은 제외 사유를 보존한다. 탑승/대기 시간은 보행으로 역산하지 않는다.
- 유효 표본은 최근90일 내 같은 사용자/세대/접근 유형에서 같은 물리 경로5개 우선, 부족하면 같은 유형5개를 사용한다. 선택한 풀 최근 최대20개 비율 중앙값으로 k=clamp(0.8*이전k+0.2*중앙값,0.5,2). 부족하면 기존 계수 유지. 동일 이벤트 재학습 금지. 변경 이력에 정책·선택 풀·최대20개 표본 ID를 저장한다. 첫 구현의 활동 계수는 기존 user_profiles.walking_duration_factor이며 지원 BUS 접근 안내가 재조회 시 새 profile.version으로 계산한다. 유형별 독립 적용은 후속.
- GET /me/personalization: 200 {status:learning|active,profile_version,factors:[{type:provider_mapped_access,value}],sample_counts:{valid,excluded},policy_version,quality:{sample_count,baseline_mae_seconds,personalized_mae_seconds,baseline_underprediction_rate,personalized_underprediction_rate},can_restore}. 학습 전 예측을 관측과 비교하며 표본 없으면 MAE/과소예측률 null. valid는 현재 유효 표본 전체 수, quality는 최근 최대20개다. 개인정보·원문·좌표 없음.
- POST /me/personalization/reset 및 /restore: {expected_version:positive_integer,client_request_id:UUID}, 200 위 상태. 초기화는 동기 처리로 기본1.0·새 세대를 만들고 초기화 전 시작한 관측은 재학습하지 않는다. restore는 직전 변경 전 계수를 새 버전으로 적용하며 표본 재처리는 하지 않는다. 소유권·CSRF·프로필 잠금, 같은 요청 재시도200/변경409, 버전409 VERSION_CONFLICT, 복구대상 없음409 RESTORE_UNAVAILABLE. 기존 미구현 reset 202 job_id 초안을 동기200으로 변경하므로 향후 클라이언트는 새 계약을 따른다.
- 계수 변경은 여유300초를 줄이지 않는다. 과거 안내/예측은 불변이다. 기존 F05 명시 적용에서 유효한 동일 경로 기준초를 재계산하며 AI 호출/기한 연장을 하지 않는다. 모든 유효 산정의 자동 일괄 재계산 및 관측 삭제/정정에 따른 재학습은 후속이며 완료로 표시하지 않는다.
- 관측/배제 사유는 이동과 동일90일·이동 삭제 cascade, 프로필 변경 이력은 계정 삭제까지 보관(표본 원문 없음), 샘플 집계는 유효기한과 현재 장소 버전 검사. 신규 추가 API로 기존 이동 API 호환성을 유지한다.


## 사용 흐름

1. 지원 BUS 루틴에서 검증된 개인 도보 산정을 적용하고 안내를 확인한다.
2. 안내한 시작점에서 실제 출발할 때 출발 확인, 정류장 도착 즉시 접근 완료 확인을 누른다. 탑승 확인과 구분한다.
3. ‘이번 보행 기록 학습’에서 같은 시작점·경로·방향·도착 지점인지와 평소 걸음/뛰기/우회/중간 용무/늦은 입력 여부를 확인한다.
4. 서버가 유효/제외 사유를 저장한다. 유효 기록5개부터 갱신하고 내 설정에서 개수·계수·오차·초기화/복구를 확인한다.
5. 새 안내 조회에는 새 개인 계수가 반영된다. 같은 유효 기준의 개인 도보 명시 적용은 기존 F05 재계산을 사용한다. 과거 이동 안내는 바뀌지 않는다.

## 검증과 한계

- 격리 PostgreSQL + ASGI의 합성 수동 기록으로 계산·권한·동시성·세대·재시도·표본 풀·마이그레이션을 확인한다. 실제 사용자의5회 보행/입력 정확도·실기기 센서 검증은 수행하지 않았다.
- 기준 경로/정류장 매핑/기준초를 클라이언트 신고로 만들지 않는다. 별도 AI 호출은 이번 학습에 없으며 공급자 시간만 있고 검증된 산정 revision이 없으면 UNVERIFIED_BASE로 제외한다.
- 역 내부/환승·유형별 독립 계수·일괄 파생 산정 갱신·관측 정정/삭제에 따른 재학습은 후속이다. 초기화 전 기록은 되살리지 않으며 이전 계수 복구는 숫자와 버전만 새로 적용한다.
