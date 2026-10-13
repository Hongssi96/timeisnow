# 첫 탑승 도착 근거 — F07-01a

- 날짜:2026-10-13·Notion v0.58. F07-01 전체는 미완료다.
- 목표: 검증된 공공 ID가 있는 첫 탑승만 조회하고, 원천 최신성을 확인할 수 없으면 출발 계산에 사용하지 않는다.

## 현재 공개 조회

GET /api/v1/journey-searches/{search_id}/candidates/{candidate_id}/first-arrivals: 로그인·본인·no-store, CSRF 불필요. 잘못된UUID/없음/타인/검색 만료404, 장소 위치 버전 변경409. 현재 공공 ID/방향이 없는 버스 후보는200 mapping_required·후보[]·valid_for_guidance=false이며 공급자를 호출하지 않는다. 지하철 첫 탑승은 unsupported다. 클라이언트의 정류소ID/검증 완료 쿼리/플래그는 매핑으로 사용하지 않는다.

arrival.evidence.v1: search_id,candidate_id,first_leg_id,status,source_status,received_at/generated_at,expires_at,valid_for_guidance,reasons,candidates. status는 mapping_required/unsupported/no_arrivals/insufficient_data/fresh/expired, source_status는unknown/fresh/stale/clock_mismatch다. 후보는 비식별candidate_id,provider_prediction_seconds,predicted_arrival_at(nullable). 원문·차량번호·좌표·키/URL 비노출, 새 저장/캐시/DDL/기간 연장 없음.

## 내부 조회와 경기 어댑터

first_arrivals(user_id,search_id,candidate_id,verified_mapping=...)는 호출 전후 본인/활성 회원·검색/후보 스냅샷·장소 위치 버전·매핑 기한을 확인한다. 호출 서비스가 첫 교통leg와 연결을 검증한 Mapping만 전달한다. provider=gyeonggi-bus,first_leg_id(UUID),station_id/route_id/route_dest_id(양수 숫자 문자열1~20자),sta_order(정수1~1000),mapping_version(ASCII토큰1~200자),verified_at/valid_until(aware datetime)을 사용한다. 공개 입력으로 이 구조를 받지 않으며 아직 자동 매핑 저장소/호출자는 없다.

고정 https://apis.data.go.kr/6410000/busarrivalservice/v2/getBusArrivalItemv2, DATA_GO_KR_SERVICE_KEY(.env보다프로세스환경우선),3초·256KiB·리다이렉트/HTTP 자동 전환 없음. 정상0/무결과4/공급자 실패를 구분하고 stationId/routeId/staOrder/routeDestId가 일치하는 유일 행만 사용한다. RUN의 predictTimeSec1/2는1~86400초 정수, vehId1/2는숫자ID/0제외. 분 필드로 대체하지 않고0/음수/누락/미확인 운행 상태는 시간 근거 부족이다. STOP은무후보,WAIT/PASS는운행/정차 조건이 미확인인 보수적 상태다. 중복 JSON 키/비정상 상수/중복 차량·잘못된 스키마는502, 전송/권한/쿼터503, 시간초과504. 원문·요청URL·키를 로그/DB에 기록하지 않는다.

## 최신성

수신 후120초와 검증된 생성 후120초 중 이른 기한에 검색/매핑 기한을 더해 적용한다.120초 경계까지 유효하며 초과는expired다. 원천 시각 없음/naive/미래와 수신 시각 역전은 최신으로 바꾸지 않는다. 검증된 생성시각이 있는 내부 입력만 생성시각+예측초를 계산하고, 이미 지난 예측은 사용하지 않는다. 차량 놓침/탑승 관측으로 해석하지 않는다.

[경기 공식 항목 명세](https://www.gbis.go.kr/gbis2014/publicService.action?cmd=mBusArrival)는 queryTime을 정보요청시간, predictTimeSec1/2를 초 단위로 설명한다. queryTime을 생성시각으로 사용하지 않으므로 현재 경기 조회는 source_status=unknown·predicted_arrival_at=null·valid_for_guidance=false다. 초가 있어도 최신 도착 후보/출발 안내 완료로 표시하지 않는다.

## 남은 범위

F07-01 전체 완료에는 실제 경로의 공공 정류소/노선/순번/방향 운영 매핑, 공급자 생성시각/시간대와 실조회 확인, 서울 버스/지하철 등 지원 확대가 필요하다. 현재 검색 모델의 public_id/public_direction_id는null이다. 자동 매핑·실제 공급자 호출·프론트·출발 시각/환승/목표 도착 계산은 이번 단계에서 수행하지 않았다. 다음은 F07-01b 운영 매핑과 신뢰 가능한 시간 근거 연결이다.


## F07-01b 방향 진단 준비/실조회 승인 대기 — 2026-10-13

Notion v0.59. backend/check_gyeonggi_mapping.py에 단순 왕복 노선의 회차/종착 방향 진단을 추가했다. 노선 상세 startStationId/endStationId/turnStID, 정차 목록 stationSeq/turnSeq/turnYn과 승하차 ID를 대조한다. 연속 순번·유일하고 일관된 회차점·기점 복귀가 확인된 후보만 방향 가설을 만들며 회차 경유/회차점 승차·순환/누락/충돌은 미확인으로 둔다. 도착 행의 stationId/routeId/staOrder/routeDestId가 모두 일치하는 유일 행인지 추가 검사한다. 이는 운영 정책 확정이나 자동 매핑/저장/API 연결이 아니다. 기존100m는 진단용으로 유지한다.

합성 신규7개+기존 매핑7개(0.001초), 도착17개(5.054초) 통과. 전체 백엔드는 이번에 재실행하지 않았다. 실조회 포함 명령은 자동 승인 검토가 외부 키/좌표 전송 승인 부재로 거부하여 실행하지 못했다. 이후 외부 호출을 제거한 별도 명령으로 테스트만 실행했다. 과거 성공 사례를 이번 성공으로 재사용하지 않는다.

승인할 실행: backend/.venv/Scripts/python.exe backend/check_gyeonggi_mapping.py. 고정 공개 판교역(127.11119217,37.39477123)→성남시청(127.12628814,37.41993056) WGS84만 dapi.kakao.com HTTPS 경로 API에1회, 저장 KAKAO_REST_API_KEY는 Authorization 헤더로 전송한다. apis.data.go.kr HTTPS 경기 서비스에는 저장 DATA_GO_KR_SERVICE_KEY를 쿼리로 전송하여 노선 검색1회·동명 노선 정차 목록 최대6회·유일 노선 상세1회·도착 항목1회, 전체 최대10회다. 리다이렉트/HTTP 전환 없음, 응답별25초/2MB 제한. 사용자 DB의 장소/좌표는 읽지 않고 키/URL/원문/차량번호는 출력·저장하지 않는다. 출력은 개수/일치 여부/진단 거리/순번/고정 상태만 제공한다.

경기 queryTime은 요청시각이며 공식 도착 명세에 검증된 생성시각 근거가 없어 generated_at/최신성은 계속 미확인이다. 이번 도구도 verified_generation_time_available=false·valid_for_guidance=false를 출력한다. 실조회 승인은 운영 상시 전송이나100m 운영 매핑 정책 승인과 구분한다. F07-01/F07-01b는 미체크이며 다음은 공개 실조회 방향 대조, 신뢰할 원천 시각/공급자와 운영 정책 확정이다.

공식 근거: [경유정류소](https://www.gbis.go.kr/gbis2014/publicService.action?cmd=mBusRouteStation), [노선 상세](https://www.gbis.go.kr/gbis2014/publicService.action?cmd=mBusRouteInfo), [도착 항목](https://www.gbis.go.kr/gbis2014/publicService.action?cmd=mBusArrival). 2026-10-13 웹 확인; routeDestId는 진행방향 마지막 정류소 ID이며 단순 이름/전체 노선 종점을 무조건 대신 넣지 않는다.


## F07-01b 공개 실조회 결과 — 2026-10-13

사용자가 공개 판교역→성남시청 좌표와 저장된 키의 공식 HTTPS 최대10회 조회를 명시 승인했다. 기존 진단을 실행한 결과 route_disambiguation_required·candidate_count=12·종료코드1이었다. 카카오 공개 경로1회·경기 동명 노선 검색1회, 총2회만 수행했다. 동명 후보12개가 노선 정차 목록 대조 한도6개를 넘어 중단됐으므로 정차 목록/노선 상세/도착정보는0회다. 이 실행의 방향·매핑·원천 최신성을 확인했다고 기록하지 않는다. 사용자 장소/좌표 DB를 읽거나 키·원문·차량번호를 출력/저장하지 않았다.

승인 대기는 해소됐으며 현재 제한은 동명 후보 초과다. 과거76번5개 사례와 달리 현재 첫 직행 후보 선택 결과12개로, 경로/응답 변화의 상세 원인은 미확정이다. 후보 일부만 골라 유일 매핑으로 인증하지 않는다. 다음은 정류소/지역 등 검증된 기반정보를 이용해 후보를 좁히는 전략과 호출 예산을 정리하는 작업이다. 운영 매핑·신뢰할 생성시각·최신 도착/출발 연결은 계속 미완료다. Notion v0.60에 실행 결과를 갱신하고 저장을 확인했다. 앱 API/계산/DB 계약 변경 없음.
