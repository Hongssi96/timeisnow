# 기록 정정·삭제 후 재학습

기준: Notion API v0.92/5.11, 2026-10-16. 지원 첫 BUS 접근의 개인 보행 학습을 확장한다.

### 5.11 기록 정정·삭제 후 재학습 (2026-10-16, F08-04/F08-05·F09)
- 최초 POST 이벤트의 동일 요청 재시도는 원래 전송 해시로 판별하되 현재 정정 버전의 event를 반환한다. 정정/삭제의 멱등 응답은 해당 요청 당시 결과이며 최신 상태는 본인 목록/상세 재조회로 확인한다. 이전 세대 관측의 정정/삭제도 수동 복구된 옛 계수에 영향을 줄 수 있으므로 현재 세대의 남은 자료로 재생성한다.
- PATCH /trips/{trip_id}/events/{event_id}: 본인/Origin·CSRF/no-store, {occurred_at?:시간대 ISO문자열, excluded?:boolean, correction_reason:timestamp_error|accidental_input|learning_exclusion|learning_restore, expected_version:이벤트양수버전, client_request_id:UUID}. 한 필드 이상 필수, null/추가필드 거부. 진행 중 이동은409 ACTIVE_TRIP_EDIT_FORBIDDEN으로 취소/종료 후 정정한다. 구간/type/source/원래 received_at·최초 전송 해시는 불변, 이전/새 값과 사유 이력은90일 보존한다. 시각은 최초 안내 calculated_at 이상·원래 수신시각 이하·앞뒤 이벤트 순서 비감소만 허용(422). excluded는 관측 품질 제외이며 종료 결과는 보존한다. 이벤트/이동 버전 증가 및 이전 안내 조회 무효화. 200 {event,trip_version,personalization}. 잘못된 버전409 VERSION_CONFLICT, 타인/없음/만료404.
- PATCH /trips/{trip_id}/walking-observation: 종료/취소한 본인 이동에 {same_scope,condition,expected_version:관측버전,client_request_id}. 저장된 보행 조건을 정정하고 품질을 재판정, 200 {observation,personalization}. GET /trips/{trip_id}/walking-observation은 저장 관측 또는 null과 관측 version/confirmation을 반환한다. 기존 v0.91 유효 관측은 normal/same_scope=true로 이관할 수 있지만 기존 제외 관측의 조건은 추측하지 않고 CONFIRMATION_REQUIRED를 유지한다.
- DELETE /trips/{trip_id}: {expected_version:이동버전,client_request_id:UUID}, 200 {trip_id,deleted:true,personalization}. v0.91 미구현202 job 초안에서 동기200으로 변경한다. 본인 스냅샷·이동·이벤트/정정·학습 관측·이동 생성 키 및 연결된 학습 표본 참조를 같은 트랜잭션에서 정리한다. 진행 중 이동 삭제 시 안내도 종료한다. 삭제 영수증은 본인 요청/대상UUID·해시·집계 응답만24시간 보관, 원문/좌표/이벤트시각 없음. 같은 안내의 재생성도 영수증 유효 중404로 차단한다.
- 세 변경은 사용자별 manual-trip→routine-write 잠금과 멱등 영수증을 사용한다. 같은 client_request_id/정규화본문/대상 재시도200(버전 검사보다 우선), 다른본문/대상409 IDEMPOTENCY_CONFLICT. 삭제 뒤 이전 정정 영수증은 제거하며 삭제 재시도만 재현한다. 기록 UI는 명시 삭제 확인과 요청 중 중복 차단·실패 재시도·상태 재조회/페이지 이동을 제공한다.
- 재학습은 현재 세대의 남은 유효 관측을 원래 접수 created_at/id 순으로 재연산한다. 기본1부터 각 시점 같은 구간5개 우선/동일 유형 대체·최근20개 중앙값·0.8/0.2 규칙을 적용한다. 5개 미만은1.0. 초기화 이전 세대는 되살리지 않으며 수동 restore의 옛 숫자는 재현하지 않고 현재 자료로 교체한다. 수정 전 예측초·원래 안내와 품질 비교 기준은 덮어쓰지 않는다. 이전 오염 계수의 복구를 차단하고 새 rebuild 프로필 버전/근거를 저장한다. correction/removal 뒤 새 정상 갱신의 직전 안전 계수는 복구 가능하다.
- 지원 provider_mapped_access의 아직 유효한 동일 경로 기준만 새 source=profile_recalculation revision/실행 이력으로 재계산한다. 새 AI·지도 호출0, base_seconds×새계수 올림, 원래 기한/보관 기한 연장 없음. 장소/경로 변경·만료/원본 실행 소실은 재사용 금지. 활성 메모리의 같은 산정 참조도 최신 재계산 revision을 안전하게 읽되 과거 이동 안내는 불변이다.
- GET /trips/{trip_id}는 최근 정정 이력 corrections[]를 추가한다(최신50개, 이전/새 이벤트 시각·제외·버전 요약, AI 원문/좌표 없음). 기존 event 응답의 excluded는 boolean, version은 양수로 확장한다. 프론트 이동 기록에서 본인 목록/상세·시각 정정·학습 제외/복원·조건 정정·삭제와 학습 결과를 연결한다. 내보내기·역/환승 학습은 후속이다.


## 화면 사용

이동 기록 → 본인 기록 선택 → 종료/취소한 이동의 이벤트 시각·학습 제외 또는 보행 조건 정정 → 재학습 결과 확인. 삭제는 별도 확인 후 실행한다. 진행 중 이동의 정정은 출발 화면에서 종료/취소한 뒤 가능하며 기록 삭제는 안내도 함께 종료한다.

원래 안내와 학습 전 예측초는 불변이다. 5개 중 하나 제외/삭제 시 기본1.0, 6개 중 하나 삭제해 유효5개가 남으면 원래 접수순 재학습으로1.04가 된다(합성 비율1.2 예시). 수동 복구된 옛 계수도 삭제된 표본을 되살리지 못한다.

## 검증 범위

격리 PostgreSQL/ASGI와 실제 HTTP 로그인·React 화면으로 정정/삭제/재학습을 확인했다. 실제 사용자의 이동을 삭제하거나 보행 정확도를 측정하지 않았다. 내보내기·역/환승 학습·일반 신규 학습/초기화 시 전체 산정 자동 갱신은 후속이다.
