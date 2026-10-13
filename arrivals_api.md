# 첫 탑승 도착 근거 — F07-01a/01b

- 날짜:2026-10-13·Notion v0.65. F07-01 전체는 미완료다.
- 목표: 검증된 공공 ID가 있는 첫 탑승만 조회하고, 원천 최신성을 확인할 수 없으면 출발 계산에 사용하지 않는다.

## 현재 공개 조회

GET /api/v1/journey-searches/{search_id}/candidates/{candidate_id}/first-arrivals: 로그인·본인·no-store, CSRF 불필요. 잘못된UUID/없음/타인/검색 만료404, 장소 위치 버전 변경409. 신규 검색의 서버 메모리 근거로 유일 경기 매핑을 확인한 버스 후보는 실제 공급자를 조회한다. 근거 없음/재시작/다른 프로세스/퇴출·매핑 미확인은200 mapping_required·후보[]·valid_for_guidance=false이며 공급자를 호출하지 않는다. 지하철 첫 탑승은 unsupported다. 클라이언트의 정류소ID/검증 완료 쿼리/플래그는 매핑으로 사용하지 않는다.

arrival.evidence.v1: search_id,candidate_id,first_leg_id,status,source_status,received_at/generated_at,expires_at,valid_for_guidance,reasons,candidates. status는 mapping_required/unsupported/no_arrivals/insufficient_data/fresh/expired, source_status는unknown/fresh/stale/clock_mismatch다. 후보는 비식별candidate_id,provider_prediction_seconds,predicted_arrival_at(nullable). 원문·차량번호·좌표·키/URL 비노출, DB/루틴 영구 저장·DDL/기한 연장 없음. 서버 메모리 근거/60초 도착 재사용은 아래 F07-01b 정책을 따른다.

## 내부 조회와 경기 어댑터

first_arrivals(user_id,search_id,candidate_id,verified_mapping=...)는 호출 전후 본인/활성 회원·검색/후보 스냅샷·장소 위치 버전·매핑 기한을 확인한다. 호출 서비스가 첫 교통leg와 연결을 검증한 Mapping만 전달한다. provider=gyeonggi-bus,first_leg_id(UUID),station_id/route_id/route_dest_id(양수 숫자 문자열1~20자),sta_order(정수1~1000),mapping_version(ASCII토큰1~200자),verified_at/valid_until(aware datetime)을 사용한다. 공개 입력으로 이 구조를 받지 않는다. F07-01b 자동 매핑은 서버 메모리의 본인 검색/후보 근거로 이 구조를 생성한다.

고정 https://apis.data.go.kr/6410000/busarrivalservice/v2/getBusArrivalItemv2, DATA_GO_KR_SERVICE_KEY(.env보다프로세스환경우선),3초·256KiB·리다이렉트/HTTP 자동 전환 없음. 정상0/무결과4/공급자 실패를 구분하고 stationId/routeId/staOrder/routeDestId가 일치하는 유일 행만 사용한다. RUN의 predictTimeSec1/2는1~86400초 정수, vehId1/2는숫자ID/0제외. 분 필드로 대체하지 않고0/음수/누락/미확인 운행 상태는 시간 근거 부족이다. STOP은무후보,WAIT/PASS는운행/정차 조건이 미확인인 보수적 상태다. 중복 JSON 키/비정상 상수/중복 차량·잘못된 스키마는502, 전송/권한/쿼터503, 시간초과504. 원문·요청URL·키를 로그/DB에 기록하지 않는다.

## 최신성

수신 후120초와 검증된 생성 후120초 중 이른 기한에 검색/매핑 기한을 더해 적용한다.120초 경계까지 유효하며 초과는expired다. 원천 시각 없음/naive/미래와 수신 시각 역전은 최신으로 바꾸지 않는다. 검증된 생성시각이 있는 내부 입력만 생성시각+예측초를 계산하고, 이미 지난 예측은 사용하지 않는다. 차량 놓침/탑승 관측으로 해석하지 않는다.

[경기 공식 항목 명세](https://www.gbis.go.kr/gbis2014/publicService.action?cmd=mBusArrival)는 queryTime을 정보요청시간, predictTimeSec1/2를 초 단위로 설명한다. queryTime을 생성시각으로 사용하지 않으므로 현재 경기 조회는 source_status=unknown·predicted_arrival_at=null·valid_for_guidance=false다. 초가 있어도 최신 도착 후보/출발 안내 완료로 표시하지 않는다.

## 남은 범위

경기 자동 매핑과 본인GET 연결은 아래 합성/격리DB 검증까지 구현했다. F07-01 전체 완료에는 원천 생성시각/시간대·실제 키 통합검증·지원 범위 확인이 남았다. 서울 버스/지하철·운영 전체 지역/노선 지원·프론트 실시간 표시·출발/환승/목표 도착 계산은 미구현이다. 현재 journey.v1의 public_id/public_direction_id는null을 유지하며 서버 내부 메모리 매핑과 분리한다. 다음은 신뢰할 원천 시간 근거와 실제 연결 검증이다.

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

첫-arrivals GET은 이 근거로 경기 정류소 검색→최대2정류소 경유노선→최대2노선의 정차목록→유일 노선 상세를 대조한다. 초기 운영 정책은 양끝30m 이내·모든 정류소 이름의 연속 순서·공식 station/route/방문순번/방향ID·일관된 회차/같은 방향·실제 끝 정류소 일치다. 근처 한 정류소/일부 노선만 골라 유일하다고 표시하지 않는다. 기존100m는 진단용으로 남고 운영 정책이 아니다. 복수 차량/노선·회차 넘기/회차점 승차·순환/근거 없음은 mapping_required, 첫 지하철은 unsupported다.

매핑 최대6회/총5초 예산·각최대3초/응답1MiB·고정HTTPS/리다이렉트 및 HTTP 전환 금지. 도착은 기존3초/256KiB/정확한ID·RUN·양수 예측초 검사다. 전체최대7회. 같은 후보는 프로세스 내 lock으로 병렬 중복 차단429/Retry-After2, 사용자 공급자 갱신10회/분 버킷429. 수신 후60초 동안 재사용하되 최초 수신/생성/검색/매핑 기한을 연장하지 않는다. 미매핑 결과도60초 중복 호출 방지. 캐시/매핑 호출 전후 활성 회원/본인·장소 버전·검색/후보 fingerprint/매핑 기한을 확인하고 매핑 도중 후보가 바뀌면 도착 호출 전409로 차단한다. 검색 기한이 짧아져도 캐시 응답 기한을 함께 줄인다.

경기 원천 생성시각은 계속 unknown이다. 예측 초가 있어도 generated_at=null·predicted_arrival_at=null·valid_for_guidance=false다. GET 입력/응답 필드·쿠키/소유권/no-store·CSRF 불필요를 유지하며 공개 입력의 정류소ID/검증플래그는 무시한다. 공급자502/503/504, 현재 소유권/기한404·장소/후보 변경409. 새 AI/프론트/출발 계산 연결 없음.

검증: 신규 연결16개9.167초, 최종 전체백엔드283개119.790초 전부 통과. 실제 격리PostgreSQL/ASGI·합성 공급자로 경로 작업→메모리 근거→공공 매핑→본인GET→도착 초/unknown·60초 재사용을 검증했다. 30m 초과/100m 이내·연속 정차 누락·복수/충돌·키/크기/JSON/시간초과·재시작/용량/소유권/fingerprint/TTL·동시/버킷·호출 중 후보/검색 변경·DB 경로 무변경/원문 비노출도 확인했다. 이번 키 실조회0회이며 이전 공개 진단을 신규 운영 정책/GET 실검증으로 표시하지 않는다.

서버 최종 적용health200·프론트200·비인증GET401. DB head0011·회원20/장소35/루틴12/ai_executions0/walking_paths0 유지. F07-01b/F07-01 전체는 원천 생성시각/최신성·실제 키 통합검증·지원 범위가 남아 미완료다. 다음은 신뢰할 원천 시각/공급자 확인과 신규 운영 연결의 실제 키 통합 검증이다. 기존 공개 진단 예산은 누적23회/승인26회·3회 잔여이고 이번에 추가 사용하지 않았다.
