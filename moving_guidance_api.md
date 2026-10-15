# 첫 탑승 전 남은 경로 안내 — F07-07a

API 기준: https://app.notion.com/p/3ebace1670c6806c8199cde33ebfbdfa


## F07-07a — 첫 탑승 전 남은 경로 안내 (2026-10-14)

출발 신고 후 사용자가 현재 위치/지도 핀을 확인하고 아직 첫 차량에 타기 전이라고 확인하면, 그 지점→루틴 목적지의 새 depart_now 경로를 조회한다. 이전 전체 도보를 다시 적용하거나 W-경과시간으로 이동을 추측하지 않는다. 현재점 접근을 제외한 첫 대중교통 이후 구간이 저장 경로와 동일한 유일 후보만 사용한다. 남은 접근 도보 양수초×현재 개인계수 올림과 현재 기준 정류장 여유·순차 환승·오늘 목표를 기존 추정 정책으로 계산한다.

POST /api/v1/trips/{trip_id}/remaining-searches 및 GET /api/v1/trips/{trip_id}/remaining-searches/{search_id}/guidance?expected_version 추가. 본인 active 수동출발/버전/루틴/장소/프로필/신고 전후 검사, 현재 위치 확인 접수+120초·검색/도착 기한의 최소값, 메모리32개·재시작/퇴출/만료 재확인. 기존 검색/이동 생성 조회 한도 공유. 위치 원문은 기존 worker 처리 중만 사용하고 새 DB/로그/URL/AI 저장 없음. 스냅샷·프로필·이벤트·guidance_id 변경 없음, 새 DDL 없음.

출발 확인 카드의 '첫 탑승 전 남은 경로 확인'에서 기존 OriginSelector/currentPointOnly와 카드·버튼·CSS를 재사용한다. 저장 장소 선택/저장을 숨기고 현재 위치/지도 확인과 탑승 전 확인을 받는다. 유효 동안60초/탭복귀 조회, 실패/위치기한/재선택/안내중지 시 숫자 제거·늦은 응답 무시. 현재 위치는 자동 추적하지 않는다. 새 응답이 이전 위치 확인 기한을 연장하지 못하도록 클라이언트도 최소 기한을 유지한다. 초 단위 여유/설정값을 올림 분으로 과장하지 않는다. '탑승했거나 안내 멈추기'는 이 안내 종료이며 실제 boarded 기록 생성은 아니다.

명세 Notion v0.82 5.7.9 및 moving_guidance_api.md. 전체 F07-07은 미완료: 차량 안/환승 중에는 현재 구간을 확인할 F08 접근 완료/탑승/하차 기록과 남은 구간 근거가 필요하다. 실제 GPS 품질/현재 위치 인증/실경로 정확도는 미검증. 특정 노선 상세 결과없음 대응은 사용자 지시로 후속 보류.

### 5.7.10 진행 구간별 이동 안내(F07-07b·F08-03 일부)
- 이동 진행은 저장된 manual 이벤트와 불변 경로로만 판정한다. GET /trips 목록/상세 및 생성·취소의 trip에 progress를 추가한다. progress=stage:not_departed|approaching|waiting|onboard|transfer|transfer_waiting|transit_finished, current_leg_id/next_leg_id(nullable), anchor_event_id(nullable), actions(허용 type→leg_id), boarding_stop/alighting_stop/vehicle_name(nullable). 완료된 대중교통 이후도 목적지 도착/이동 완료로 자동 확정하지 않는다. 기존 departure_event/approach_event/boarding_event는 첫 구간 기록을 유지한다.
- 기존 POST /trips/\{trip_id\}/events에 alighted 추가 및 다음 차량의 approach_arrived/boarded/alighted를 지원한다. departed→접근 완료(선택)→현재 차량 boarded→같은 차량 alighted→다음 접근 완료(선택)→다음 boarded 순서다. 차량 순서 건너뛰기·탑승 전 하차·하차 전 다음 탑승·같은 type/leg 새ID·취소/만료는 차단한다. source:manual·시각 비감소/미래 차단·세션 잠금·동일 client_event_id/본문200 재현/다른본문409·이벤트30회/분·90일 보관 유지. UNIQUE(trip_id,type,leg_id)로 확장하며 departed 하나는 서비스/세션 잠금으로 유지한다. 새0016 migration은 기존 관측 보존, 하차/반복type 관측이 있으면 downgrade 실패하여 자동 삭제하지 않는다. 놓침/최종 완료는5.8.3으로 확장했으며 정정은 후속이다.
- 차량 안 stage:onboard는 현재 차량/하차 지점과 수동 하차 버튼을 표시한다. 현재 차량 위치·남은 운행시간 근거가 없으므로 여유/ETA 숫자를 표시하거나 탑승 후 경과시간을 위치로 바꾸지 않는다. transit_finished도 목적지 도착을 추정하지 않는다. 수동 목적지 도착 확인은5.8.3이며 남은 마지막 도보 안내는 후속이다.
- POST /trips/\{trip_id\}/remaining-searches의 stage에 transfer 추가. transfer는 현재 진행이 transfer/transfer_waiting일 때만 허용하며 현재 위치/지도 확인·쿠키/CSRF·expected_version·기존 한도/TTL 정책을 재사용한다. 남은 첫 차량은 기록된 다음 차량이며 그 차량부터 이후 노선/정차순서/도보역할이 같은 유일 새 후보만 사용한다. 이미 지난 차량·도보·환승을 다시 계산하지 않는다. 새 현재점 접근도보×현재 계수 및 transfer_buffer_seconds를 사용해 다음 차량/남은 순차 환승/오늘 목표를 기존 승인 추정으로 계산한다.
- transfer 검색 연결은 stage와 anchor_event_id(최근 하차 또는 접근 완료)를 포함한다. POST 접수 및 GET 평가 전후에 진행/이벤트·소유권/루틴/장소/프로필을 재검사한다. 이후 탑승/하차/취소·구간 변경은409로 차단하고 기존 위치 기한을 연장하지 않는다. 첫 탑승 전 stage는 기존 departed만 있는 범위 그대로 유지한다. 응답 trip.remaining.v1에 stage/anchor_event_id/next_leg_id를 추가하며 기존 클라이언트 필드/계산은 유지한다.
- UI는 현재 차량/하차 지점→수동 하차→환승 위치 확인→유효한 다음 차량 여유→다음 탑승으로 이어진다. 신고 중/실패/기한/다른 구간 응답에는 이전 숫자를 숨기고 동일 이벤트ID·시각 재시도와 복구를 제공한다. 숨김 중 조회 중지·활성60초/탭복귀 재확인, GPS 자동 추적·원래 접근 재적용·자동 학습 없음. 기존 카드/버튼/글꼴/반응형을 재사용한다.
- 구현·검증 완료 <mention-date start="2026-10-15"/>: 전체 백엔드465개269.882초·최종 첫 접근 요약 보존 회귀1개3.596초, 프론트 전체275개13.16초·빌드1913모듈480ms 통과. 3차량 순서/중복/재현·다른 차량 차단·진행변경 전후 숫자 차단·현재점120초/환승여유120초·지난 경로 제외·migration 왕복/관측 보존을 확인했다. 합성 실제 컴포넌트 PC1280×1000/모바일390×1000에서 차량 안→하차→환승→다음 탑승 전환·미확인/유효 환승 숫자 표시 및 가로넘침없음 확인. 개발DB0016 기존회원21/장소35/루틴12/이동0/약속0 보존·서버health/frontend200·OpenAPI enum 확인. 직접 외부키/AI0회. F07-07b-1/F08-03a 범위 완료이며 차량 안 숫자의 운행 잔여 근거(F07-07b-2)·놓침/정정/최종완료·실제 이동 정확도는 후속, 위 검증 시점의F07-07/F07-07b/F08-03은 미완료였으며 F08-03 수동 종료 확장은5.8.3을 따른다.


## 2026-10-15 F07-07b-2 차량 확인 기반 하차 안내

POST /trips/{trip_id}/onboard-confirmations(expected_version/anchor_event_id/leg_id/plate_suffix4자리)와 GET /trips/{trip_id}/onboard-guidance?expected_version 추가. 본인 활성 onboard/현재 anchor·루틴/장소/프로필을 전후 확인하고, 명시 차량번호 확인·공식 노선 순번/방향·위치 목록의 유일 차량·같은 vehId의 공식 하차 정류소 양수 예측이 모두 있을 때만 수신 기준 하차 추정을 제공한다. 경과시간/정류소 수로 잔여초를 만들지 않는다. 확인 메모리32개/30분·근거120초/공식 매핑300초·조회60초·원기한 비연장. 공개 응답 trip.onboard.v1의 하차 ETA/남은초/출처·만료·needs_data 및 상세 계약은 api_contract.md 5.7.14. 구현/합성 검증은 완료, 실제 위치 API403으로 권한/키 적용 상태 확인과 실제 같은 차량 재검증 대기다. F07-07b-2 체크는 미완료 유지.

2026-10-15 후속: 현재 .env로 위치19대와 공식 방향·같은vehId의 다음 정류소 예측129초 실호출 성공. 이전403 해소 확인, 정확한 원인은 미확정. 실서버 정상 이동 세션 통합 검증은 후속이며 F07-07b-2 미완료 유지. development_log.md 근거.
