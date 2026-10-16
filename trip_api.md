# 이동 세션·수동 출발 확인 — F08-01/F08-02a

Notion v0.80 · 2026-10-14 · https://app.notion.com/p/3ebace1670c6806c8199cde33ebfbdfa

### 5.8.1 루틴 안내 연결 이동 세션과 수동 출발(F08-01/F08-02a)
- 이번 범위는 지원 루틴의 유효 첫 출발 안내에 연결된 assisted/baseline 세션, 본인 조회/취소와 첫 departed 수동 신고다. 첫 접근 완료/탑승은5.8.2에서 확장했으며 하차·환승 결과·정정/학습/내보내기/삭제작업은 미구현 상태를 유지한다. F07-06b 절반 경과 정책은 이 저장 기반 후속 연결이며 이번 단계에서 자동 전환하지 않는다.
- 루틴 출발 GET의 nested first.departure.v1에 nullable guidance_id(UUID)를 추가한다. 유효 안내에만 서버가 당시 departure/좌표 없는 정규화 경로·루틴/장소/프로필 버전과 묶인 토큰을 최근128개 프로세스 메모리에 발급한다. 기한은 원래 안내/검색 중 최소, 연장 없음. 일반 후보 GET/근거부족은null. GET에서 DB 안내/이동 생성이나 실제 출발 신고는 없다. 재시작/다른 프로세스/퇴출은 토큰404·새 안내 필요.
- POST /api/v1/trips는 기존 guidance_id(UUID), measurement_mode:assisted\|baseline만 받는다. 쿠키 본인·Origin/CSRF/no-store, 유효 토큰과 현재 루틴/경로/장소/프로필 버전을 DB 공유 잠금으로 재검사하여 당시 안내 스냅샷과 이동을 원자 저장한다. 생성 시 현재부터 W만큼 접근할 수 있는 차량인지도 재검사하고 이미 접근 불가능하면404·새 안내 필요. 좌표/원문/사용자 지정 ETA·출발 여부를 입력받지 않는다. 201 data는 trip_id,guidance_id,routine_id(nullable),measurement_mode,status(active\|cancelled),version,created_at,expires_at,departure_event(nullable)이며 당시 안내는GET상세에서 제공한다. 아직 출발하지 않은 세션이며 departed와 구분한다.
- 선택 Idempotency-Key(1\~128자 ASCII 영문/숫자/밑줄/하이픈)는 본인+POST /trips+키/본문 해시와 결과 참조를24시간 보관한다. 같은 키/정규화본문200 저장결과, 다른본문409 IDEMPOTENCY_CONFLICT, 삭제/기한경과 기록은404·재생성없음. 키 없이도 동일 본인 guidance_id+mode 재전송은 같은 세션200(안내 토큰 만료/재시작 뒤에도 저장 결과 복구 가능), 다른mode409 IDEMPOTENCY_CONFLICT. 유효한 진행 중 이동은 본인당1개, 다른 guidance로 생성하면409 ACTIVE_TRIP_EXISTS. 본인 생성 요청10회/분·이벤트30회/분·멱등재전송 추가생성 없음. 지원외 guidance/타인/만료404, 루틴/장소/프로필 변경409 VERSION_CONFLICT.
- GET /api/v1/trips는 limit기본20/1\~100, cursor(본인trip UUID)·routine_id(UUID)·status:active|cancelled|missed|completed 선택 필터, 생성시각/ID내림차순과 items/next_cursor를 반환한다. from/to 필터는 후속. GET /trips/\{trip_id\}는 본인200의 trip, immutable guidance,events 배열,outcome(active면null/그외status). CSRF불필요/no-store·타인/만료404. 사용자 목록/상세에서 active 세션을 복구할 수 있다.
- POST /trips/\{trip_id\}/events는 client_event_id(UUID), type:departed, occurred_at(시간대 있는datetime), leg_id(UUID), source:manual만 지원하고 추가 필드 거부. guidance 경로의 첫 ordered_leg ID와 일치해야 한다. occurred_at은 당시 안내 calculated_at 이상/서버 received_at 이하, 시간대 없는 값/미래/안내 이전은422 VALIDATION_ERROR. 받은 시간은 서버에서 별도 저장하고 실제 보행시간/정확도/학습을 인증하지 않는다. 입력 지연은 received_at-occurred_at 초로 본인 응답에 제공하되 임의 임계값으로 학습 적격 처리하지 않는다.
- 세션 행을 잠그고 최초 departed 하나만 저장한다. 동일 본인 trip/client_event_id+정규화본문 재전송200 기존event·다른본문409 IDEMPOTENCY_CONFLICT, 다른ID의 두번째departed 또는 취소 세션의 새 이벤트409 INVALID_EVENT_ORDER. 201/200 event는 event_id,client_event_id,trip_id,type,leg_id,source,occurred_at,received_at,input_delay_seconds,excluded:false,version:1. 시각/좌표/출발 신고는 일반로그에 남기지 않는다.
- PATCH /trips/\{trip_id\}는 outcome:cancelled, expected_version양수정수만 지원한다. 본인/CSRF/no-store, 버전 일치200 cancelled와version증가·다른버전409, 같은버전의 이미취소는변경없이200. 본인 active 세션을 취소한 뒤 새 세션을 만들 수 있다. 취소는 과거 departed를 삭제하거나 실제 미이동/놓침으로 바꾸지 않는다.
- 안내 스냅샷/이동/이벤트는 생성시각부터90일 보관, 읽기와 쓰기에서 expires_at 이후 차단하며 다음 쓰기에서 만료 이동과 연결 스냅샷을 정리한다. 사용자 삭제/탈퇴 cascade; 이동 삭제·정정/학습 파생 정리와 매일 청소는 후속 미완료. 토큰의 짧은 계산 유효기간과 저장된 과거 안내의90일 보관을 구분한다. 새 DB guidance_snapshots/manual_trips/manual_trip_events/manual_trip_creation_keys는 미병합 F12 저장소와 구분하며 migration0013_manual_trips는 현재main0012에서 이어진다. F12별도 migration과 향후 병합 시 Alembic head 통합이 필요하다.
- UI는 기존 카드/버튼/상태표현으로 유효 루틴 안내의 '지금 출발했어요'를 제공한다. 당시 안내토큰으로 세션 생성→수동 departed 저장 후에만 확인 완료를 표시한다. 실패시 같은토큰/이벤트ID·발생시각 재시도, 중복누름 차단·화면 이탈취소. 복구된 진행중 세션과 출발 기록/취소를 표시한다. 사용자 저장 성공을 서버 확인하기 전 완료로 표시하지 않는다.
- 호환성: 기존 POST /trips의 guidance_id/mode 초안 입력 유지, 루틴 안내응답에 nullable 토큰 추가. 미구현 API의 구체적범위/시간/중복/보관/오류를확정하는 구현정책이며 다른담당 약속 안내토큰을 지원한다고 주장하지 않는다.
- F08-01/F08-02a 구현·검증 완료 <mention-date start="2026-10-14"/>: 유효 루틴 안내 토큰→불변 스냅샷/assisted·baseline 이동→본인 복구/취소→수동 departed·멱등/순서·시간/권한·90일 만료. 신규 격리 백엔드12개 최종23.270초, 전체406개194.374초 통과 후 ISO 문자열 검증 강화 관련12개 재검증. 프론트 전체242개37.85초 통과 후 취소 토큰 재사용 차단 관련6개1.73초 재검증·최종빌드1911모듈423ms. 합성 응답/실제 컴포넌트·클라이언트 PC1280×800·모바일390×844 성공/실패·재시도/취소 확인. 개발 DB0013_manual_trips 테이블4개/기존 데이터 보존. 외부 실키/AI0회·실사용자 로그인/추천 성공/실제 이동 정확도 미검증. F07-06b 연결·나머지F08 이벤트/정정/학습/내보내기/삭제·약속 안내 토큰 호환은 후속.

## F07-06b — 수동 출발 미확인 다음 차량 전환 (2026-10-14)

지원 경기 BUS 루틴에서 마지막 정상 안내의 권장 s 이후 now-s > 개인화 접근 W/2이며 유효 수동 departed 신고가 없으면 현재 차량을 제외한다. 정확히 절반은 유지하고 여유 B는 절반에 포함하지 않는다. 제공된 다음 차량 중 현재 ETA보다 늦고 W+B를 확보하는 가장 이른 차량으로 출발·순차 환승·오늘 목표를 재계산한다. 다음 후보/식별/최신 근거 부족은 숫자를 숨긴다. 수동 신고 부재로 실제 미출발/놓침 관측을 만들거나 학습하지 않는다.

first.departure.v1에 departure_state:unconfirmed|reported_departed 추가. 저장/복구된 출발은 출발전 숫자와 안내 토큰을 제공하지 않고 60초 도착/300초 검색 자동조회를 멈춘다. 취소 성공 뒤 새 검색으로 재개하고 신고 후 늦은 응답은 숫자를 복원하지 않는다. 기존 카드·색·CSS·버튼 재사용. 일반 후보 상세에는 기존 F07-06a만 적용하며 이동중 안내는 F07-07 후속이다.

공식 매핑·차량의 비식별 키와 선택 s/W/ETA는 본인/루틴별 최대128개 프로세스 메모리에서만 비교하고 제외16개 상한, 충돌429·변경중409를 적용한다. 차량 원문ID/새 좌표 저장·로그 없음. 검색ID가 바뀌어도 동일 버전/장소/노선/프로필/접근이면 이어가되 선택 ETA 경과·변경·재시작은 초기화한다. 기존 수신/기한을 연장하지 않으며 DB 신고를 조회 전후 검사한다. 새 DDL·직접 외부키/AI 호출 없음.

Notion v0.81 5.7.8 및 api_contract.md 동기화. 전체 백엔드421개 통과 후 최종 관련16개, 프론트 전체248개 후 최종 관련57개·빌드 통과. 전환/다음없음/출발확인 3상태 합성 API·실컴포넌트 PC/모바일 확인. 실제 사용자 경로 추천 성공/실이동 정확도는 미검증, 공식노선 상세 결과없음 대응은 사용자 요청으로 후속 보류. 세부 결과 development_log.md.

## F07-07a — 첫 탑승 전 남은 경로 안내 (2026-10-14)

출발 신고 후 사용자가 현재 위치/지도 핀을 확인하고 아직 첫 차량에 타기 전이라고 확인하면, 그 지점→루틴 목적지의 새 depart_now 경로를 조회한다. 이전 전체 도보를 다시 적용하거나 W-경과시간으로 이동을 추측하지 않는다. 현재점 접근을 제외한 첫 대중교통 이후 구간이 저장 경로와 동일한 유일 후보만 사용한다. 남은 접근 도보 양수초×현재 개인계수 올림과 현재 기준 정류장 여유·순차 환승·오늘 목표를 기존 추정 정책으로 계산한다.

POST /api/v1/trips/{trip_id}/remaining-searches 및 GET /api/v1/trips/{trip_id}/remaining-searches/{search_id}/guidance?expected_version 추가. 본인 active 수동출발/버전/루틴/장소/프로필/신고 전후 검사, 현재 위치 확인 접수+120초·검색/도착 기한의 최소값, 메모리32개·재시작/퇴출/만료 재확인. 기존 검색/이동 생성 조회 한도 공유. 위치 원문은 기존 worker 처리 중만 사용하고 새 DB/로그/URL/AI 저장 없음. 스냅샷·프로필·이벤트·guidance_id 변경 없음, 새 DDL 없음.

출발 확인 카드의 '첫 탑승 전 남은 경로 확인'에서 기존 OriginSelector/currentPointOnly와 카드·버튼·CSS를 재사용한다. 저장 장소 선택/저장을 숨기고 현재 위치/지도 확인과 탑승 전 확인을 받는다. 유효 동안60초/탭복귀 조회, 실패/위치기한/재선택/안내중지 시 숫자 제거·늦은 응답 무시. 현재 위치는 자동 추적하지 않는다. 새 응답이 이전 위치 확인 기한을 연장하지 못하도록 클라이언트도 최소 기한을 유지한다. 초 단위 여유/설정값을 올림 분으로 과장하지 않는다. '탑승했거나 안내 멈추기'는 이 안내 종료이며 실제 boarded 기록 생성은 아니다.

명세 Notion v0.82 5.7.9 및 moving_guidance_api.md. 전체 F07-07은 미완료: 차량 안/환승 중에는 현재 구간을 확인할 F08 접근 완료/탑승/하차 기록과 남은 구간 근거가 필요하다. 실제 GPS 품질/현재 위치 인증/실경로 정확도는 미검증. 특정 노선 상세 결과없음 대응은 사용자 지시로 후속 보류.

### 5.8.2 첫 접근 완료·탑승 수동 기록(F08-02b)
- 기존 POST /trips/\{trip_id\}/events에 type:approach_arrived|boarded를 추가한다. departed는 첫 ordered_leg, approach_arrived는 첫 차량 전 접근 WALK 구간(없으면 첫 차량), boarded는 첫 BUS/SUBWAY 구간의 leg_id다. 첫 차량 이후 환승/하차는5.7.10으로 확장했으며 놓침/정정은 후속이다.
- 본인 active 세션에서 departed 이후 접근 완료(선택)→탑승 순서로 각 type당 하나만 저장한다. 접근 완료 누락 상태의 탑승 신고도 허용하지만 접근 완료를 자동 생성하거나 출발→탑승을 보행시간으로 학습하지 않는다. 탑승 후 접근 완료/중복 type 새 ID/취소 세션의 새 이벤트는409 INVALID_EVENT_ORDER, 잘못된 구간·이전 이벤트보다 이른 발생시각·미래는422 VALIDATION_ERROR다. 같은 시각은 허용한다.
- 기존 쿠키·Origin/CSRF·이벤트30회/분·세션 잠금·동일 client_event_id/정규화본문200 재현·다른본문409·90일 보관과 occurred_at/received_at 분리는 유지한다. 기존 departed 요청/응답 호환, 이벤트 응답 type enum 확장. 이동 요약에 nullable approach_event/boarding_event를 추가하고 departure_event는 항상 departed를 가리킨다.
- 접근/탑승 신고 저장 뒤 첫 탑승 전 남은 경로 POST/GET은409 INVALID_EVENT_ORDER로 차단한다. 기존 안내 스냅샷·루틴/프로필·학습값은 변경하지 않는다. UI는 출발 확인 뒤 정류장 도착/탑승 버튼, 저장 중 중복 차단·동일 ID/시각 재시도·복구를 제공하며 진행 신고 중/실패 시 이전 여유 숫자를 제거한다. 탑승은 사용자 신고이며 특정 차량 인증이 아니다.
- 구현·검증 완료 <mention-date start="2026-10-15"/>: 전체 백엔드459개250.223초·추가 남은경로 차단1개2.344초 통과. 프론트 전체269개12.51초·최종 SDK10개1.65초·빌드1913모듈458ms 통과. 합성 실제 컴포넌트 PC1280×900/모바일390×844 버튼·상태/가로넘침 확인. 개발 DB0015 기존회원21/장소35/루틴12/이동0/약속0 보존·서버health/frontend200·OpenAPI enum 확인. 외부키/AI0회, 실제 이동 정확도·차량 안/환승 안내·하차/정정/자동학습은 미검증/후속.

## 진행 구간 확장 (2026-10-15)

하차·다음 차량별 반복 접근/탑승과 progress 요약은 Notion v0.84 5.7.10 및 moving_guidance_api.md를 따른다. 기존 첫 이벤트 요약/90일 보관/수동 입력 의미는 유지한다. F08-03 놓침·정정·최종 완료는 후속이다.

### 5.8.3 수동 놓침·목적지 도착과 이동 종료(F08-03b)
- 기존 POST /trips/\{trip_id\}/events에 missed/arrived를 추가한다. missed는 departed 이후 approaching/waiting/transfer/transfer_waiting에서 타려던 다음 BUS/SUBWAY leg_id로만 신고한다. 해당 구간의 탑승 놓침을 사용자가 신고하고 이번 이동을 종료한다. 실제 탑승 뒤 놓침·차량 순서 건너뛰기·자동 놓침 생성은 허용하지 않는다. 다음 차량 이용은 새 최신 안내/새 이동에서 시작하며 반복 놓침 시도를 같은 세션에 자동 합치지 않는다.
- arrived는 모든 차량의 수동 boarded/alighted가 순서대로 저장된 transit_finished에서만 허용한다. leg_id는 마지막 ordered_leg(마지막 도보가 없으면 마지막 차량)다. 버튼 문구는 목적지 도착 수동 확인이며 마지막 하차를 도착으로 자동 처리하지 않는다. GPS/좌표·특정 차량 인증/도착 정확도 보증이 아니다.
- 두 이벤트는 source:manual, client_event_id/occurred_at/received_at·비감소 시각/미래 차단·본인/Origin/CSRF·세션 잠금·30회/분·90일 보관 정책을 유지한다. 같은 ID/정규화본문 재전송200, 다른본문409. 새ID 반복 종료/종료 후 다른 이벤트·취소/다른 종료 결과 변경은409 INVALID_EVENT_ORDER, 잘못된 구간/시각422다. 저장된 원본 이벤트/안내 스냅샷을 삭제하거나 자동학습하지 않는다.
- 이벤트 저장과 manual_trips.status:missed|completed 및version+1은 한 트랜잭션으로 처리한다. 실패 시 모두 롤백하며 종료된 세션은 active 고유 제한을 해제한다. progress.stage에도 missed/completed를 추가하고 actions는빈객체, anchor_event_id는 종료 이벤트다. trip에 nullable terminal_event를 추가하며 기존 첫 이벤트 요약은 유지한다. event POST 응답은 기존 event 형식이며 최신 trip은GET으로 복구한다.
- GET /trips의 status 필터는 active|cancelled|missed|completed, 상세outcome은 active:null/그외status를 반환한다. 같은 guidance_id 생성 재시도는 기존 종료 세션을 재현하고 새 세션으로 되살리지 않는다. PATCH outcome:cancelled는 기존 계약 유지하며 completed/missed를 취소/다른 종료로 덮어쓰지 않는다. 종료 후 remaining-searches POST/GET은 숫자를 반환하지 않는다.
- UI는 탑승 전 '놓침을 기록하고 이동 종료', 최종 하차 뒤 '목적지에 도착했어요'를 제공한다. 저장 중/실패에는 기존 숫자와 다른 신고 버튼을 차단하고 같은ID/시각으로 재시도한다. 서버 종료 확인 후 완료/놓침 결과를 표시한다. 재방문은 본인 루틴 최신 이동을 조회해 종료 결과를 복구하며 '새 이동 준비'에서 최신 안내로 돌아간다. 실제 진행 중인 다른 루틴 이동과 소유권 검사는 서버에서 유지한다.
- DB0017_trip_outcomes는 기존 이벤트/상태 CHECK만 확장하고 관측/종료 상태가 있으면 downgrade를 거부하여 자동 삭제하지 않는다. F08-03b는 수동 놓침/완료 범위이며 정정/학습/기록 내보내기/삭제는 후속이다.
- 차량 안 근거 조사 <mention-date start="2026-10-15"/>: [경기 버스 위치정보 공식 명세](https://www.gbis.go.kr/gbis2014/publicService.action?cmd=mBusLocation)는 vehId/routeId/stationId/stationSeq/stateCd와 queryTime(요청시간)을 제공한다. 현재 앱의 수동 boarded는 실제vehId에 결합되지 않으며 이 목록만으로 탑승 차량의 남은 운행초/원천 최신성을 인증하지 않는다. F07-07b-2는 미완료·숫자 차단 유지, 실제 키 호출 없음.
- 구현·검증 완료 <mention-date start="2026-10-15"/>: 전체 백엔드471개289.156초, 프론트 전체280개12.93초 및 최종 종료/동시 취소 회귀15개2.30초·빌드1913모듈523ms 통과. 수동 완료/놓침·순서/시각/권한/중복/동시성·트랜잭션 롤백·종료 조회/새 이동·기존 안내 차단·migration 기존 행/종료 데이터 downgrade 차단 확인. 합성 실제 컴포넌트 PC1280×900/모바일390×844 완료→새 이동·놓침 실패→재시도→종료 및 가로넘침없음 확인. 개발DB0017 기존회원21/장소35/루틴12/이동0/약속0 보존·서버health/frontend200·enum 확인. 직접 외부키/AI0회. F08-03b와 지원 루틴 수동 기록 범위의F08-03 완료, 정정/학습/내보내기/삭제·차량 안 잔여 운행 근거/실제 이동 정확도는후속.

## 5.8.4 기록 정정·동기 삭제 (2026-10-16)
기존5.8.1~3의 정정/삭제 미구현·excluded:false/version:1 고정 표기를 확장한다. 본인 종료/취소 이동의 시각/학습 제외 및 보행 조건 정정, 버전/UUID 멱등·이력·현재 세대 재학습, 본인 이동 동기 삭제200과 원문/참조 정리를 구현했다. 최초 수신시각/기존 안내와 예측은 보존한다. 진행 중 이동 정정은409, 삭제는 안내도 종료한다. 정확한 요청·순서/시간 검증·호환성·재시도와 자료 보관은 record_correction_api.md/Notion5.11을 우선 따른다. 내보내기는 미구현이다.
