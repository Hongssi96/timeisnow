# 첫 탑승 도착 근거 — F07-01a/01b

- 날짜:2026-10-13·Notion v0.72. F07-01 전체는 미완료다.
- 목표: 검증된 공공 ID가 있는 첫 탑승만 조회하고, 검증된 생성시각과 수신 기준 추정을 구분하고, 사용자 승인 추정 근거는 유효기간 안에서만 안내에 사용한다.

## 현재 공개 조회

GET /api/v1/journey-searches/{search_id}/candidates/{candidate_id}/first-arrivals: 로그인·본인·no-store, CSRF 불필요. 잘못된UUID/없음/타인/검색 만료404, 장소 위치 버전 변경409. 신규 검색의 서버 메모리 근거로 유일 경기 매핑을 확인한 버스 후보는 실제 공급자를 조회한다. 근거 없음/재시작/다른 프로세스/퇴출·매핑 미확인은200 mapping_required·후보[]·valid_for_guidance=false이며 공급자를 호출하지 않는다. 지하철 첫 탑승은 unsupported다. 클라이언트의 정류소ID/검증 완료 쿼리/플래그는 매핑으로 사용하지 않는다.

arrival.evidence.v2: search_id,candidate_id,first_leg_id,status,source_status,timing_basis(none/source_generation/receipt_estimate),received_at/generated_at,expires_at,valid_for_guidance,reasons,candidates. status는 mapping_required/unsupported/no_arrivals/insufficient_data/fresh/estimated/expired, source_status는unknown/fresh/stale/clock_mismatch다. 후보는 비식별candidate_id,provider_prediction_seconds(원래 예측초),predicted_arrival_at(nullable),remaining_seconds(nullable·평가 시점 남은 초 올림). 원문·차량번호·좌표·키/URL 비노출, DB/루틴 영구 저장·DDL/기한 연장 없음. 서버 메모리 근거/60초 도착 재사용은 아래 F07-01b 정책을 따른다.

## 내부 조회와 경기 어댑터

first_arrivals(user_id,search_id,candidate_id,verified_mapping=...)는 호출 전후 본인/활성 회원·검색/후보 스냅샷·장소 위치 버전·매핑 기한을 확인한다. 호출 서비스가 첫 교통leg와 연결을 검증한 Mapping만 전달한다. provider=gyeonggi-bus,first_leg_id(UUID),station_id/route_id/route_dest_id(양수 숫자 문자열1~20자),sta_order(정수1~1000),mapping_version(ASCII토큰1~200자),verified_at/valid_until(aware datetime)을 사용한다. 공개 입력으로 이 구조를 받지 않는다. F07-01b 자동 매핑은 서버 메모리의 본인 검색/후보 근거로 이 구조를 생성한다.

고정 https://apis.data.go.kr/6410000/busarrivalservice/v2/getBusArrivalItemv2, DATA_GO_KR_SERVICE_KEY(.env보다프로세스환경우선),3초·256KiB·리다이렉트/HTTP 자동 전환 없음. 정상0/무결과4/공급자 실패를 구분하고 stationId/routeId/staOrder/routeDestId가 일치하는 유일 행만 사용한다. RUN의 predictTimeSec1/2는1~86400초 정수, vehId1/2는숫자ID/0제외. 분 필드로 대체하지 않고0/음수/누락/미확인 운행 상태는 시간 근거 부족이다. STOP은무후보,WAIT/PASS는운행/정차 조건이 미확인인 보수적 상태다. 중복 JSON 키/비정상 상수/중복 차량·잘못된 스키마는502, 전송/권한/쿼터503, 시간초과504. 원문·요청URL·키를 로그/DB에 기록하지 않는다.

## 생성시각 검증과 수신 기준 추정 — 사용자 결정 2026-10-13

검증 생성시각이 있으면 source_status=fresh/timing_basis=source_generation/status=fresh로 생성시각+예측초를 사용한다. 생성시각이 없는 정상 RUN/유효 예측초는 generated_at=null/source_status=unknown/timing_basis=receipt_estimate/status=estimated로 수신시각+예측초를 추정한다. 두 경우 모두 유효 후보가 있으면 valid_for_guidance=true다. 이 플래그는 추정 사용 허용도 포함하며 원천 최신성 인증이 아니다. 잘못된/naive/미래 생성시각·수신시각 역전은 추정으로 우회하지 않는다. queryTime은 정보요청시간이므로 생성시각으로 저장하지 않는다.

유효기한은 수신+120초·검증 생성+120초(있을 때)·검색/매핑 기한 중 이른 값이다.120초 경계까지 유효, 초과면expired/후보[]/guidancefalse. 남은 시간은 ceil(추정 또는 검증 도착시각-현재 평가시각), 이미 지난 후보는 제외한다. provider_prediction_seconds는 원래 값을 유지한다. 정상 무결과는no_arrivals, 시간/운행근거 부족 또는 모든 후보 경과는insufficient_data다. 통과/탑승 사실로 해석하지 않는다.

동일 후보 캐시 조회에도 남은 시간/지난 후보를 재평가하지만 최초 received_at/추정도착/기한은 유지한다. 활성 후보 상세는 진입/60초/탭 복귀 조회, 숨김 중지·이탈 취소·중복 방지. 재조회 오류502/503/504는 원래 캐시 기한을 연장하지 않고 화면에 실패를 표시한다.120초 초과면 기존 숫자를 제거한다. 인증/검색/장소 변경 오류는 기존 숫자를 즉시 제거한다. 화면은 서버시각+단조 경과시간으로 평가해 단말 시계 차이를 줄이며 '수신 기준 예상·N초 전 조회'를 표시한다. 실제 출발 시각 숫자는 개인 접근 근거를 연결하는 F07-02 후속이다.

선택 이유: 사용자가 세 방법을 비교한 뒤 수신 기준 추정을 승인했다. 경기 API에 생성시각이 없어 생성시각 필수 조건은 기능 진행을 막지만, 추정 표시/짧은 재조회/만료로 한계를 알리며 실제 데이터를 활용할 수 있다. 재조회/여유5분은 공급자 지연을 증명하거나 제거하지 않는다. 생성시각 또는 공식 지연 상한 확보는 별도 F07-01c로 강화한다. API 모델v2는 estimated/timing_basis/remaining_seconds와 valid_for_guidance 의미 변경을 클라이언트에 요구한다.

## 남은 범위

경기 자동 매핑과 본인GET 연결은 아래 합성/격리DB 검증까지 구현했다. F07-01 전체 완료에는 별도 F07-01c의 원천 시간/갱신지연 근거·지원 범위 강화가 남았다. 경기 매핑/본인조회는 직전 실제 키8회 연결 확인, 수신 기준 추정은 이번 합성/격리DB 검증으로 구분한다. 서울 버스/지하철·운영 전체 지역/노선 지원·프론트 실시간 표시·출발/환승/목표 도착 계산은 미구현이다. 현재 journey.v1의 public_id/public_direction_id는null을 유지하며 서버 내부 메모리 매핑과 분리한다. 다음은 신뢰할 원천 시간 근거와 실제 연결 검증이다.

## F07-01b 방향 진단 준비/실조회 승인 대기 — 2026-10-13

Notion v0.59. backend/check_gyeonggi_mapping.py에 단순 왕복 노선의 회차/종착 방향 진단을 추가했다. 노선 상세 startStationId/endStationId/turnStID, 정차 목록 stationSeq/turnSeq/turnYn과 승하차 ID를 대조한다. 연속 순번·유일하고 일관된 회차점·기점 복귀가 확인된 후보만 방향 가설을 만들며 회차 경유/회차점 승차·순환/누락/충돌은 미확인으로 둔다. 도착 행의 stationId/routeId/staOrder/routeDestId가 모두 일치하는 유일 행인지 추가 검사한다. 이는 운영 정책 확정이나 자동 매핑/저장/API 연결이 아니다. 기존100m는 진단용으로 유지한다.

합성 신규7개+기존 매핑7개(0.001초), 도착17개(5.054초) 통과. 전체 백엔드는 이번에 재실행하지 않았다. 실조회 포함 명령은 자동 승인 검토가 외부 키/좌표 전송 승인 부재로 거부하여 실행하지 못했다. 이후 외부 호출을 제거한 별도 명령으로 테스트만 실행했다. 과거 성공 사례를 이번 성공으로 재사용하지 않는다.

승인할 실행: backend/.venv/Scripts/python.exe backend/check_gyeonggi_mapping.py. 고정 공개 판교역(127.11119217,37.39477123)→성남시청(127.12628814,37.41993056) WGS84만 dapi.kakao.com HTTPS 경로 API에1회, 저장 KAKAO_REST_API_KEY는 Authorization 헤더로 전송한다. apis.data.go.kr HTTPS 경기 서비스에는 저장 DATA_GO_KR_SERVICE_KEY를 쿼리로 전송하여 노선 검색1회·동명 노선 정차 목록 최대6회·유일 노선 상세1회·도착 항목1회, 전체 최대10회다. 리다이렉트/HTTP 전환 없음, 응답별25초/2MB 제한. 사용자 DB의 장소/좌표는 읽지 않고 키/URL/원문/차량번호는 출력·저장하지 않는다. 출력은 개수/일치 여부/진단 거리/순번/고정 상태만 제공한다.

경기 queryTime은 요청시각이며 공식 도착 명세에 검증된 생성시각 근거가 없어 generated_at/최신성은 계속 미확인이다. 이번 도구도 verified_generation_time_available=false·valid_for_guidance=false를 출력한다. 실조회 승인은 운영 상시 전송이나100m 운영 매핑 정책 승인과 구분한다. F07-01/F07-01b는 미체크이며 다음은 공개 실조회 방향 대조, 신뢰할 원천 시각/공급자와 운영 정책 확정이다.

공식 근거: [경유정류소](https://www.gbis.go.kr/gbis2014/publicService.action?cmd=mBusRouteStation), [노선 상세](https://www.gbis.go.kr/gbis2014/publicService.action?cmd=mBusRouteInfo), [도착 항목](https://www.gbis.go.kr/gbis2014/publicService.action?cmd=mBusArrival). 2026-10-13 웹 확인; routeDestId는 진행방향 마지막 정류소 ID이며 단순 이름/전체 노선 종점을 무조건 대신 넣지 않는다.


## F07-01b 공개 실조회 결과 — 2026-10-13

사용자가 공개 판교역→성남시청 좌표와 저장된 키의 공식 HTTPS 최대10회 조회를 명시 승인했다. 기존 진단을 실행한 결과 route_disambiguation_required·candidate_count=12·종료코드1이었다. 카카오 공개 경로1회·경기 동명 노선 검색1회, 총2회만 수행했다. 동명 후보12개가 노선 정차 목록 대조 한도6개를 넘어 중단됐으므로 정차 목록/노선 상세/도착정보는0회다. 이 실행의 방향·매핑·원천 최신성을 확인했다고 기록하지 않는다. 사용자 장소/좌표 DB를 읽거나 키·원문·차량번호를 출력/저장하지 않았다.

승인 대기는 해소됐으며 현재 제한은 동명 후보 초과다. 과거76번5개 사례와 달리 현재 첫 직행 후보 선택 결과12개로, 경로/응답 변화의 상세 원인은 미확정이다. 후보 일부만 골라 유일 매핑으로 인증하지 않는다. 다음은 정류소/지역 등 검증된 기반정보를 이용해 후보를 좁히는 전략과 호출 예산을 정리하는 작업이다. 운영 매핑·신뢰할 생성시각·최신 도착/출발 연결은 계속 미완료다. Notion v0.60에 실행 결과를 갱신하고 저장을 확인했다. 앱 API/계산/DB 계약 변경 없음.


## F07-01b 정류소 기반 후보 축소 — 2026-10-13

Notion v0.61. 전국 동명 노선 검색 대신 카카오 첫 직행 버스 구간의 승차 정류소명과 경로 시작 좌표로 경기 정류소 목록을 대조한다. 진단용100m 내 같은 이름의 정류소를 최대2개 모두 유지하고 각각 경유노선을 조회한다. 동일 차량 이름에 일치하는 공공 routeId/staOrder/routeDestId를 정차 목록의 승차 stationId/순번과 연결한 뒤 전체 정류소 순서와 승하차 좌표를 대조한다. 가장 가까운 정류소나 일부 노선만 택하지 않는다. 반복 방문은 순번으로 분리, 같은 순번의 종착 방향 충돌·좌표 결측/중복 ID 충돌은 미확인으로 둔다.100m는 운영 정책이 아니다.

backend/check_gyeonggi_mapping.py --max-requests 8: 요청 예산은1~10회 정수로 제한, 기본10회다. 실패 요청도 호출 횟수에 포함하고 상세/도착2회를 남긴 뒤 모든 후보 정차 목록이 예산에 들어갈 때만 조회한다. 응답4는 정상 무결과로 처리하고 권한 실패에는 HTTP 전환이나 전체 노선 검색으로 우회하지 않는다. 개인 저장 장소/좌표 읽기와 원문·키·차량번호 출력/저장 없음.

실제 결과: 이번7회(카카오1/정류소 검색1/정류소2개의 경유노선2/정차 목록1/노선 상세1/도착1), 이전2회 포함 누적9회. 근처 정류소2개에서 노선 후보1개/유일 매칭1개로 축소했다. 승차12/하차23, 양끝 거리4.29m/12.85m, 도착1행의 stationId/routeId/staOrder는 일치했다. direction_unresolved·arrival_direction_matches=false·verified_generation_time_available=false·valid_for_guidance=false·종료1이다. 방향/생성시각/출발 계산은 검증되지 않았다.

새 최대10회 명령은 자동 승인 검토가 이미 사용한2회와 누적 한도를 이유로 실행 전 거부했다. 남은8회만 사용하도록 예산 옵션/검증을 보완한 후 해당 제한 명령은 승인 검토를 통과해 실행했다. 거부된 명령은 호출0회다. 그 이후 고정 direction_reason을 추가했지만 키 실조회를 다시 실행하지 않아 실제 실패 상세 원인은 아직 확인하지 못했다. 누적 승인 예산은1회만 남았으며 전체 진단 재실행에는 부족하다.

검증: 새 정류소/경유노선·예산·권한 실패·비노출14개(0.007초), 매핑/방향15개(0.002초) 전부 통과. 전체 백엔드/프론트 검증은 재실행하지 않았다. 고정 실패 사유는 ROUTE_ID_MISMATCH/STATION_SEQUENCE_INCOMPLETE/TURN_SEQUENCE_CONFLICT/TURN_SEQUENCE_OUT_OF_RANGE/TURN_MARKERS_UNCONFIRMED/SIMPLE_RETURN_ENDPOINT_UNCONFIRMED/TURN_DESTINATION_UNCONFIRMED/DIRECTION_FIELDS_UNCONFIRMED 및 경유노선 종착 충돌로 구분하며 값/예외 원문을 반환하지 않는다.

[정류소 검색 공식 문서](https://www.gbis.go.kr/gbis2014/publicService.action?cmd=mBusStation)와 [경유노선 공식 문서](https://www.gbis.go.kr/gbis2014/publicService.action?cmd=mBusStationRoute)를2026-10-13 읽었다. 정류소 후보 축소는 실제 확인했지만 운영 매핑/저장/공개GET 연결은 없고 F07-01b/F07-01 전체 미완료다. 다음은 방향 실패 상세 원인·노선 형태를 확인하고 신뢰할 생성시각/공급자·운영 정책을 정하는 작업이다.


## F07-01b 방향 실패 사유 실확인 — 2026-10-13

사용자가 추가 최대8회 조회를 승인해 --max-requests 8로7회 실행했다. 이번 결과도 근처 정류소2개·노선 후보1개·매칭1개·승차12/하차23·거리4.29m/12.85m·도착1행의 정류소/노선/순번 일치다. direction_reason=SIMPLE_RETURN_ENDPOINT_UNCONFIRMED, direction_status=direction_unresolved·arrival_direction_matches=false·verified_generation_time_available=false·valid_for_guidance=false·종료코드1을 실제 확인했다.

해당 사유는 startStationId=endStationId 또는 정차 목록의 첫/마지막 stationId가 startStationId와 불일치할 때 반환하는 묶음 검사다. 출력만으로 어느 개별 조건이 실패했는지 구분되지 않는다. 실제 노선 오류·반대편 정류소·특정 입력 필드 문제로 단정하지 않으며 단순 왕복 전제와 실제 양방향 종점 구조를 분리해 다음 단계에서 대조해야 한다. 원천 최신성/운영 매핑·출발 연결은 미완료다.

이번7회+이전9회=누적16회, 승인10+추가8=18회 중2회 잔여. 승인 검토를 통과했으며 사용자 저장 장소/좌표를 읽거나 키/원문/차량번호를 출력·저장하지 않았다. 코드/테스트/API/저장/계산 변경 없음, 테스트를 새로 실행했다고 기록하지 않는다. Notion v0.62 저장 확인·F07-01b/F07-01 미체크 유지.


## F07-01b 왕복 전제 분리 진단 — 2026-10-13

Notion v0.63. direction_candidate에 서버 진단 내부 scoped_direction을 추가했다. scope가 없으면 기존 단순 왕복 가설로 검사한다. scope가 있으면 공식 정류소 경유노선에서 얻은 routeId/승차 stationId/방문순번과 실제 매칭 구간을 재대조하고, routeDestId가 해당 방향의 실제 끝 정류소 ID와 일치해야 방향 후보가 된다. 실제 회차점 ID/노선 상세 routeId·연속 순번·일관된 turnSeq/유일 turnYn·승하차 ID·같은 방향의 구간을 검사하며 순환/회차를 넘는 구간·회차점 승차/종착 충돌은 미확인으로 둔다.

왕복 끝 stationId가 canonical startStationId와 같거나 canonical endStationId가 물리 회차 정류소 ID와 같다는 가정으로 방향을 추론하지 않는다. 진단 출력 direction_basis=station_route_scope/simple_return_hypothesis, return_endpoint_matches_start는 고정 상태/boolean만 제공한다. 이는 운영 매핑/공개 API 연결이 아니며 기존100m 진단 허용오차·원천 최신성 unknown·valid_for_guidance=false를 유지한다.

합성 신규7개 포함 test_route_mapping_probe.py21개0.003초/test_station_first_mapping.py15개0.009초 총36개 통과. 다른 왕복 끝 ID·canonical 종점 별칭·scope 방문/종착 충돌·회차 통과/승차·결측/boolean/순환·CLI 공식 방향 대조와 guidance 차단 유지까지 검증했다. 수정 후 키 실조회0회이므로 이전 실제 사례 해결을 주장하지 않는다. 전체 백엔드/프론트 테스트 재실행 없음.

누적16회/승인18회로2회만 남아 전체 공개 진단 재실행에는 부족하다. 검토할 다음 실행은 동일 공개 판교역→성남시청/동일 키/고정 카카오·경기 HTTPS로 --max-requests 8이며, 추가 최대8회 예산을 받아 수정 후 실제 방향 일치를 확인하는 것이다. 원문·키·차량번호 저장/출력과 사용자 저장 장소 읽기 없음. F07-01b/F07-01 전체 미완료이며 API/저장/계산/클라이언트 호환성 변경 없음.


## F07-01b 공개 방향 진단 성공 — 2026-10-13

사용자 추가 최대8회 승인 후 --max-requests 8을 실행해7회·종료코드0을 실제 확인했다. 노선 후보1개·근처 정류소2개·유일 매칭1개·승차12/하차23·양끝 거리4.29m/12.85m·도착1행의 stationId/routeId/staOrder/routeDestId가 모두 일치했다. direction_status=direction_candidate, direction_basis=station_route_scope, direction_reason=null, arrival_identity_matches=true, arrival_direction_matches=true, return_endpoint_matches_start=false다. 왕복 끝 정류소 ID가 canonical 기점과 달랐음을 확인했으나 물리적 반대편 여부는 단정하지 않는다.

이번7회+이전16회=누적23회, 승인10+8+8=26회 중3회 잔여다. queryTime 존재는 확인했지만 verified_generation_time_available=false·valid_for_guidance=false·production_mapping_validated=false를 유지한다. 원문·키·차량번호 저장/출력·사용자 저장 장소/좌표 읽기 없음. 코드/테스트/API/계산/저장 변경 없고 이번 테스트 재실행도 없다.

이는 공개 한 사례의 방향 진단 성공이다.100m는 진단 정책이며 운영 허용오차/자동 매핑 저장·공개GET 연결은 미확인이다. 경기 원천 생성시각도 없어 최신 도착/출발 계산 완료가 아니다. Notion v0.64 저장 확인·F07-01b/F07-01 미체크 유지. 다음은 운영 매핑 정책/조회 연결 설계와 신뢰할 원천 시각 확보다.


## F07-01b 경기 자동 매핑/본인 조회 연결 — 2026-10-13

Notion v0.65. 신규 경로 검색 작업은 첫 교통leg가 BUS이고 차량 이름1개일 때 공개 버스 정류소 이름·양끝 점만 본인/검색/후보/fingerprint에 묶어 서버 메모리에 보관한다. 입력 GPS·도보 전체 geometry·원문·키는 저장하지 않는다. 검색300초 이내·프로세스당 최근32검색/검색당 최대20후보, 만료 후 사용 금지/다음 접근 정리. 재시작/다른 프로세스/퇴출·옛 검색은 mapping_required이며 새 검색으로 복구한다. 루틴 영구 저장·새DB/DDL 없음.

첫-arrivals GET은 이 근거로 경기 정류소 검색→최대2정류소 경유노선→최대2노선의 정차목록→유일 노선 상세를 대조한다. 현재 운영 정책은 양끝30m 이내·모든 카카오 제공 정류소 이름의 순서(공공 중간 정류소 추가 허용)·공식 station/route/방문순번/방향ID·일관된 회차/같은 방향·실제 끝 정류소 일치다. 근처 한 정류소/일부 노선만 골라 유일하다고 표시하지 않는다. 기존100m는 진단용으로 남고 운영 정책이 아니다. 복수 차량/노선·회차 넘기/회차점 승차·순환/근거 없음은 mapping_required, 첫 지하철은 unsupported다.

매핑 최대6회/총5초 예산·각최대3초/응답1MiB·고정HTTPS/리다이렉트 및 HTTP 전환 금지. 도착은 기존3초/256KiB/정확한ID·RUN·양수 예측초 검사다. 전체최대7회. 같은 후보는 프로세스 내 lock으로 병렬 중복 차단429/Retry-After2, 사용자 공급자 갱신10회/분 버킷429. 수신 후60초 동안 재사용하되 최초 수신/생성/검색/매핑 기한을 연장하지 않는다. 미매핑 결과도60초 중복 호출 방지. 캐시/매핑 호출 전후 활성 회원/본인·장소 버전·검색/후보 fingerprint/매핑 기한을 확인하고 매핑 도중 후보가 바뀌면 도착 호출 전409로 차단한다. 검색 기한이 짧아져도 캐시 응답 기한을 함께 줄인다.

경기 원천 생성시각은 계속 unknown이다. 예측 초가 있어도 generated_at=null·predicted_arrival_at=null·valid_for_guidance=false다. GET 입력/응답 필드·쿠키/소유권/no-store·CSRF 불필요를 유지하며 공개 입력의 정류소ID/검증플래그는 무시한다. 공급자502/503/504, 현재 소유권/기한404·장소/후보 변경409. 새 AI/프론트/출발 계산 연결 없음.

검증: 신규 연결16개9.167초, 최종 전체백엔드283개119.790초 전부 통과. 실제 격리PostgreSQL/ASGI·합성 공급자로 경로 작업→메모리 근거→공공 매핑→본인GET→도착 초/unknown·60초 재사용을 검증했다. 30m 초과/100m 이내·연속 정차 누락·복수/충돌·키/크기/JSON/시간초과·재시작/용량/소유권/fingerprint/TTL·동시/버킷·호출 중 후보/검색 변경·DB 경로 무변경/원문 비노출도 확인했다. 이번 키 실조회0회이며 이전 공개 진단을 신규 운영 정책/GET 실검증으로 표시하지 않는다.

서버 최종 적용health200·프론트200·비인증GET401. DB head0011·회원20/장소35/루틴12/ai_executions0/walking_paths0 유지. F07-01b/F07-01 전체는 원천 생성시각/최신성·실제 키 통합검증·지원 범위가 남아 미완료다. 다음은 신뢰할 원천 시각/공급자 확인과 신규 운영 연결의 실제 키 통합 검증이다. 기존 공개 진단 예산은 누적23회/승인26회·3회 잔여이고 이번에 추가 사용하지 않았다.


## F07-01b 실제 키 통합검증 준비 — 2026-10-13

backend/check_arrival_connection.py --max-requests 10: 공개 판교역(127.11119217,37.39477123)→성남시청(127.12628814,37.41993056) map_pin만 고정 사용한다. 임시 auth_test UUID 스키마에 합성 회원/세션을 만들어 실제 경로 검색→첫 직행BUS/차량1개 후보 선택→자동30m/연속정차/방향 매핑→본인 first-arrivals GET→동일GET 재조회를 검증한 뒤 임시 스키마와 메모리를 정리한다. 실제 사용자 장소/회원/루틴은 변경하지 않는다. 기존 테스트의 격리DB/ASGI 인증 도우미를 사용하므로 프로젝트 테스트 파일이 필요하다.

전송 범위: 저장 KAKAO_REST_API_KEY로 dapi.kakao.com HTTPS 지역 확인2회/대중교통 경로1회, DATA_GO_KR_SERVICE_KEY로 apis.data.go.kr HTTPS 매핑최대6회/도착1회. 전체최대10회, 실패 시도도 포함하며 추가 호출 전에 예산을 검사한다. 리다이렉트/HTTP/다른 호스트·비표준포트·URL 사용자정보는 거부한다. 별도 외부 원문 저장 없음. 로그인 쿠키/합성 회원 입력은 내부 ASGI에만 전달한다.

출력은 상태/오류 코드·요청 횟수/예산 소진·도착 후보 개수/원천·예측시각 유무·guidance 여부·재조회 무호출/동일근거·경로DB 무변경 boolean만 제공한다. 키/좌표/주소/공공ID/차량번호/쿠키/원문/예외 메시지는 출력하지 않는다. 성공은 연결/재사용 검증이며 source_status=unknown이면 최신성이나 출발 계산 완료가 아니다.

외부 호출 없는 신규6개1.793초 통과: 예산 초과 전 차단·고정HTTPS/포트/호스트·직행첫BUS/단일차량·고정 공개 입력·전체격리ASGI/임시스키마 정리/기존회원 개수 유지·캐시 재사용/검색 무변경·실패시도 횟수/원문 비노출. 실제 키 통합 실행0회. 기존 공개 경로 개인키 예산23/26회·3회 잔여로 전체 실행에 부족하며 추가 최대10회 승인 대기다.

원천 확인: [경기 공식 항목 명세](https://www.gbis.go.kr/gbis2014/publicService.action?cmd=mBusArrival)를 다시 읽었다. queryTime은 정보요청시간이며 행별 생성시각 계약은 없으므로 해당응답만으로 freshness를 확정할 수 없다. [서울 지하철 공식 출력](https://data.seoul.go.kr/dataList/openApiView.do?infId=OA-12764&srvType=A)은 recptnDt를 생성시각/barvlDt를 초로 설명한다. 다만 실제 역/노선/방향/시간대/지원 범위와 운영 전송은 미검증이고 자동 대체하지 않는다. 웹 도구의 HTTPS sample 접근은 불가였으며 이 결과만으로 로컬 연결을 단정하지 않았다. 별도 로컬 환경에서 공식 swopenapi.seoul.go.kr에 인증키/역명 없는 HTTPS HEAD1회·3초 timeout을 확인했고 HTTP 전환/서울키 전송은0회다. 이는 키 오류나 모든HTTPS 지원 불가의 증명이 아니다.

Notion v0.66 저장 확인. 앱 API/계산/저장·runtime 코드 변경 없음, F07-01b/F07-01 미체크 유지. 다음은 승인된 추가 예산으로 실제 경기 연결을 검증하고, 경기 원천시각 제약을 해소할 공급자/전송 정책을 정하는 작업이다.


## F07-01b 실제 키 연결 미매핑/중단 단계 — 2026-10-13

사용자가 추가 최대10회 실제 키 검증을 승인해 check_arrival_connection.py --max-requests 10을 실행했다. 실제6회·종료1: HTTP200 mapping_required/source_status=unknown·후보0·생성/예측시각 없음/guidancefalse, 재조회 무호출/동일근거/경로DB 무변경true였다. 도착 항목까지 연결됐다고 표시하지 않는다.

서버 내부 mapping.resolve에 선택적 diagnostics를 추가해 고정 stage/reason와 정류소/노선/매칭 개수만 반환하도록 했다. 공개 GET 입력/응답/정책에는 연결하지 않고 CLI 임시DB에서만 수집한다. 관련 매핑 연결17개9.095초·도구6개1.629초 전부 통과, 이번 전체 회귀는 재실행하지 않았다.

당시 승인누적36회(기존26+추가10) 중29회 사용/7회 잔여를 확인해 --max-requests 7로 재검증, 실제6회·종료1이었다. stage=route_stations/reason=ROUTE_SEQUENCE_UNCONFIRMED, station_count=1/route_count=1/matched_count=0. 모든 정류소 이름의 연속 순서/양끝30m/공식 방문scope를 함께 검사한 결과이며 어느 개별 조건이 실패했는지는 아직 확인되지 않았다. 정책을 완화하거나 다른 후보를 임의로 선택하지 않았다. HTTP200 mapping_required/후보0·unknown·guidancefalse와 재조회 무호출/동일근거·검색 무변경true를 재확인했다.

이번12회+이전23회=누적35회/승인36회·1회 잔여다. 각 실행 후 임시 스키마/메모리 정리가 성공 반환됐고 실제 DB는head0011·회원20/장소35/루틴12/산정0을 유지했다. 키/좌표/공공ID/차량번호/쿠키/원문 출력·저장 없음. 생성시각 없음은 기존 공식 계약 제약이며 이번에는 도착 항목까지 조회되지 않아 해당실응답 최신성 검증도 수행하지 못했다.

Notion v0.67 저장 확인·F07-01b/F07-01 미완료. 다음은 매칭 복합 검사의 정차/좌표/방문scope 불일치 근거를 분리하고, 신뢰할 생성시각/공급자를 확보하는 작업이다. 공개 API/계산/저장 계약·클라이언트 호환성 변경 없음.


## F07-01b 매칭 불일치 원인 분리 진단 — 2026-10-13

명시적인 내부 diagnostics 요청이 있는 실패 사례에서만 match_checks를 계산한다. 유효한 순번노선/승하차 이름쌍/중간이름 순서/전체 연속이름/공식 방문scope 일치·좌표 결측/30m 초과·정류소ID 결측·통과쌍 개수를 반환한다. detail_reason은 이름/순서/연속성/방문scope/좌표/데이터/식별/복수 매칭의 고정 코드로 구분하며 정류소 이름/좌표/공공ID를 반환하지 않는다. 첫 실패 단계 사유와 전체 개수를 함께 확인하며 복합 문제가 있으면 하나의 코드만으로 유일 원인을 단정하지 않는다.

상세진단은 정류소200개/노선당500행 초과 시 DIAGNOSTIC_SIZE_LIMIT으로 생략한다. 추가 공급자 호출0회·운영 수용조건/매핑 결과/공개GET 응답·캐시/시간/저장 정책 변경 없음. 운영 GET처럼 diagnostics가 없으면 추가 진단을 실행하지 않는다. 빈/중복순번 데이터는 이름 불일치와 구분한다.

새7개1.273초·기존연결17개9.280초·도구6개1.634초 총30개 통과. 이름/순서/연속성/30m 좌표·공식 route/station/순번 충돌·빈/중복 데이터·결측·원문 비노출/크기 제한·명시적 내부 진단에만 실행됨을 확인했다. 전체 백엔드 회귀는 이번 재실행하지 않았다. 수정 후 실제 키0회, 실제 직전 불일치의 개별 원인은 아직 확인되지 않았다.

기존 누적35회/승인36회·1회 잔여로 전체실진단에는 부족하다. 검토할 다음 실행은 같은 공개 판교역→성남시청/같은 저장키/고정 카카오·경기 HTTPS·임시DB의 check_arrival_connection.py --max-requests 8이며 추가 최대8회 승인 대기다. 원문/키/좌표/공공ID/차량번호/쿠키 비노출과 임시DB 정리를 유지한다. Notion v0.68 저장 확인·F07-01b/F07-01 미체크·원천 최신성 차단 유지.


## F07-01b 정류소 목록 연속성 차단 실확인 — 2026-10-13

사용자 추가최대8회 승인 후 같은 공개 경로/임시DB를 --max-requests 8로 실제6회 조회했다. HTTP200 mapping_required·후보0/source_status=unknown·생성/예측시각 없음/guidancefalse·종료1, 재조회 무호출/동일근거·저장검색 무변경true였다.

안전한 상세 진단은 valid_sequence_routes=1, endpoint_name_pairs=2, ordered_name_pairs=2, scoped_ordered_name_pairs=2, contiguous_name_pairs=0, scoped_contiguous_name_pairs=0, detail_reason=STOPS_NOT_CONTIGUOUS다. 정류소 이름은 순서대로 나타나고 공식 노선/승차정류소/방문순번도 맞지만, 경기 목록에 카카오 목록 사이 추가 정류소가 있는 형태를 현재 전체 연속 목록 필수 정책이 차단했다. 순서가 뒤바뀌거나 공식 승차 순번이 틀렸다는 판정이 아니다.

missing_coordinates/outside_coordinate_limit/missing_station_identity/passing_pairs는 모두0이다. 코드가 공식방문+연속 목록 쌍에만 좌표/식별을 검사하므로 이번0은 검사 미실행이며 좌표/식별 통과 근거가 아니다. 실제 양끝30m·회차/방향·하차 반복방문 유일성·도착정보는 아직 확인되지 않았다.

수정 방향(제안/미구현): 전체 목록 연속성 필수 조건을 재검토하고, 모든 카카오 제공 정류소의 순서·공식 승차방문·양끝30m·회차/같은방향/반복방문·공식 방향ID/유일성 검증을 유지해 공공 중간 정류소 추가를 처리한다. 이번에는 구현/정책을 바꾸거나 도착 연결 완료로 표시하지 않았다. 원천 생성시각 제약도 유지한다.

누적41회/승인상한44회=기존36+추가8,3회 잔여다. 이 상한은 사용자 승인한 검증 횟수이며 실제 공급자 잔여쿼터/요금 예산이 아니다. 공급자 잔여쿼터·비용은 확인하지 않았다. 키/좌표/공공ID/차량번호/쿠키/원문 비노출·임시DB/메모리 정리를 유지했다. 새 코드/테스트/API/계산/저장 변경 없음, 테스트도 재실행하지 않았다. Notion v0.69 저장 확인·F07-01b/F07-01 미체크 유지.


## F07-01b 추가 정류소 처리·방향 후 유일성 — 2026-10-13

Notion v0.70. 앞선 STOPS_NOT_CONTIGUOUS 조사 후 사용자가 구현 진행을 승인했다. 카카오가 제공한 모든 정류소 이름이 같은 순서로 존재하면 경기 목록의 추가 중간 정류소를 허용한다. 이름 별칭/누락/역순은 허용하지 않는다. 양끝30m·공식 노선/승차정류소/방문순번·연속 공공순번·일관된 유일 회차·공식 방향ID/실제 끝 정류소 검증은 유지한다.

같은 노선의 반복 하차 방문은 노선 상세1회를 공유해 각 후보의 회차/방향을 검사한 뒤 최종 유일성을 판단한다. 회차를 넘는 후보는 제외하며 같은 방향 후보가 두 개 남거나 서로 다른 공공 노선이 매칭되면 mapping_required다. 이름/좌표가 맞는 방문 후보가32쌍을 넘으면 일부를 선택하지 않고 전체 미확인 처리한다. 매핑 버전은 gbis.station-scope.v2.30m.ordered다. 상세 진단은 제공이름 순서와 공식 방문이 일치한 쌍에서 좌표를 검사하고 연속 이름 개수는 참고로 남긴다.

기존 GET 입력/응답 필드와 조회 상한·TTL/60초 캐시·소유권·검색/매핑 기한·보관 정책은 유지한다. 제공목록 상세도 차이로 차단되던 검증 경로는 새로 공급자를 조회할 수 있다. 경기 원천 생성시각은 여전히 unknown·예측시각null·guidancefalse이며 출발 계산에 사용하지 않는다. 이전 날짜별 조사 기록은 당시 결과이며 이 정책으로 대체된다. 변경 후 실제 키 연결 검증과 신뢰할 생성시각/지원 범위가 남아 F07-01b/F07-01은 미완료다. 이번 작업 실제 키 호출0회, 승인횟수41/44회·3회 잔여는 요금/공급자 잔여쿼터를 뜻하지 않는다.

검증: 신규 순서/반복방문/방향/상한/좌표9개0.013초·진단7개1.183초·연결17개9.303초 통과. 추가 정류소와 회차 뒤 반복 하차방문을 포함한 본인GET→도착 어댑터 연결을 합성 upstream/격리DB로 확인한 최종 전체 백엔드306개115.947초가 모두 통과했다. 실제 키 결과와 구분한다.


## F07-01b 실제 본인조회 연결 확인·원천 최신성 제약 — 2026-10-13

Notion v0.71. 사용자 01b 완료 요청에 따라 앞서 제시한 같은 공개 판교역→성남시청 경로/저장 키/공식 카카오·경기 HTTPS/격리DB 검증을 --max-requests 8로 실행했다. 실제8회·종료0·HTTP200/connection_verified, MAPPING_CONFIRMED·station_count=1/route_count=1/matched_count=1. 재조회 외부 무호출·동일 근거·저장 검색 무변경이 모두true다. 운영 매핑과 본인GET→공공 도착 조회 연결은 실제로 확인했다.

응답은 insufficient_data/source_status=unknown·도착후보0·생성/예측시각 없음·guidancefalse다. 실제 최신 도착 후보 확보나 출발 계산 성공을 뜻하지 않는다. 경기 공식 항목 명세(https://www.gbis.go.kr/gbis2014/publicService.action?cmd=mBusArrival)를 다시 읽어 queryTime=정보요청시간이고 행별 생성시각 계약이 없음을 확인했다. 수신시각을 생성시각으로 바꾸지 않는다. 오래된 예측을 지금의 대기시간으로 해석하면 이미 지나간 버스에 맞춰 출발할 수 있기 때문이다.

완료 요청으로 추가5회의 앞서 제시한 범위를 실행해 승인 누적49회/실제49회·잔여0이다. 이는 공급자 쿼터나 요금이 아닌 사용자 승인 호출 상한이다. 키/URL/원문/차량번호·사용자 DB 좌표 출력·저장 없음. 구현/공개API/계산/보관 정책 변경 없음·이번 신규 테스트/전체 회귀 재실행 없음(직전306개 통과 유지). 매핑·조회 연결로 F07-01b 범위를 명확히 하고 원천 최신성을 별도 TODO로 분리하는 안은 제안이며, 사용자는 최신성의 중요성을 질문했으나 분리 승인하지 않았다. 기존 F07-01b/F07-01 완료조건을 유지해 미체크로 둔다.


## F07-02 — 첫 버스 예상 출발 계산 (2026-10-13)

사용자는 검증된 개인 도보 산정값 연결 전에도 공급자 접근 도보 시간에 개인 계수를 적용한 추정을 허용했다. 첫 BUS 이전 access 도보의 양수 초 합만 사용하고 환승/마지막 도보/차량 대기를 제외한다. 접근초 W=ceil(공급자 접근초×본인 walking_duration_factor), 기본계수1.0/범위0.5~2.0, 여유 B=first_boarding_buffer_seconds(기본300초/0~1800). 물리 보행·진행방향/AI 산정 인증은 아니며 화면에 공급자 개인화 추정임을 표시한다. 원천 도착은 수신 기준 추정 또는 생성시각 검증을 구분한다.

권장 시각 s=t_vehicle-W-B. recommended는 미래 s를 선택하며 이미 지났으면 지금 기준 여유 S=t_vehicle-(now+W)를 다시 계산한다. now는 현재를 선택하고 원래 s도 유지한다. 음수 여유는0으로 바꾸지 않고 not_enough_time/안내불가, 설정 여유보다 적으면 below_buffer 경고로5분확보를 주장하지 않는다. 정보/접근 누락·0초·만료·미지원은 출발 숫자가 없다. 도착/검색 기한과 계산+120초 중 이른 기한,60초/탭복귀 재계산·숨김/이탈 중지. 개인 계수 변경은 새 GET에서 원래 공급자 접근초에 새 계수로 재계산하며 도착60초 캐시를 공유해 추가 AI/지도 호출과 TTL 연장이 없다.

본인 GET /api/v1/journey-searches/{search_id}/candidates/{candidate_id}/first-departure?departure_basis=recommended|now가 first.departure.v1과 포함된 arrival.evidence.v2를 반환한다. 소유권/장소버전/검색 스냅샷/기한과 프로필버전·계수·여유를 호출 전후 검사해 변경409·타인/없음/만료404·인증401·잘못된basis422로 차단한다. 공급자/버킷 오류와 no-store/CSRF 불필요는 기존 도착조회와 같다. client의 접근초/시간/계수를 사용하지 않는다. 새 산정/루틴 쓰기·AI 호출 없음. Alembic0012로 개인 계수 컬럼 추가, 기존 회원 보존·GET /auth/me의 profile 필드 추가. 계수 설정 변경 API/학습은 후속, 내부 변경 시profile.version 증가.

후보 상세에서 예상 출발 HH:MM(KST)·다른 날짜라면 날짜·접근 약N분/설정 여유(초 단위 보존)·공급자 개인 계수 추정·수신 기준 예상/조회경과를 표시한다. 부족/만료·선택차량 경과/현재 접근 불가 시 기존 출발 숫자를 제거한다. 루틴 선택 자동재검색/검증 개인 도보 연결은 F07-02a 후속이며 기존 routine_id 필수 POST /guidance-queries 초안은 유지한다. F07-03 이후 환승/목표도착/다음차량 선택/이동중 잔여 계산은 미구현이다. 후보 첫 차량 계산 성공을 전체 여정 연결/도착 보장으로 표시하지 않는다.

검증: 신규 백엔드15개4.903초·최종 전체329개123.044초, 프론트196개11.25초·빌드427ms 통과. 합성 실제브라우저1280×800/390×844에서 카드/추정표시·줄바꿈·가로넘침 없음 확인. 로컬DB0011→0012·회원20/장소35/루틴12 보존·계수범위 정상, 서버health/프론트200·비로그인first-departure401 확인. 이번 실제 교통키/AI 호출0회·실제 경로 출발 숫자/물리보행/예측 정확도 미검증. API 신규필드/endpoint·프로필필드/DB추가이며 기존arrival v2 계약은 유지. Notion v0.73:https://app.notion.com/p/3ebace1670c6806c8199cde33ebfbdfa. 자세한 이유·검증·실패수정은 development_log.md.


## 2026-10-14 — F07-03

첫BUS 검색 근거 외 후속BUS 최대2개 공개 정류소/차량1개/양끝점 메모리를 선택적 환승 검사에 사용한다. 소유권/fingerprint/TTL와 후속leg별 원래60초 근거를 유지하며 DB 후보에 저장하지 않는다. connections_api.md.


## 2026-10-14 — 출발 부족 사유·F07-05

기존v2 reasons에 고정 매핑실패코드만 추가한다. 프로세스근거없음/복수노선/정류소/경유노선/정차순서/방향 미확인을 구분하며 raw diagnostics·ID/좌표/개수/키는 비노출. mapper의 기존한조회에서사유를수집, 호출수/30m/방향/TTL/캐시/상태 정책변경없음. Notion v0.76의5.7.4.


## 2026-10-14 — F07-02a-2 누락 접근 도보 보완

성공경기매핑은공식stationId/staOrder행의승차좌표를별도비공개endpoint sink로 Entry에전달한다. 공개Mapping/diagnostics/DB·로그에좌표미포함, 매핑identity/후보fingerprint/TTL로연결한다. 기존도착v2/매핑30m/방향·기한변경없음. 접근도보조회까지외부상한22회/전체20초는access_walk_api.md.
