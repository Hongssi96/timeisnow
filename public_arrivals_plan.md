# 지금이니? — 공공 실시간 도착 API 준비

## 서울 좌표/경유노선 진단 — 2026-10-06

- 공식 가이드: [이름 검색](http://api.bus.go.kr/contents/sub02/getStationByName.html), [좌표 검색](http://api.bus.go.kr/contents/sub02/getStationByPos.html), [경유노선](http://api.bus.go.kr/contents/sub02/getRouteByStation.html). tmX/tmY·gpsX/gpsY=WGS84, posX/posY=GRS80. 경유노선 요청 arsId와 정류소 ID stId 구분.
- 실행: `backend/.venv/Scripts/python.exe backend/check_seoul_mapping.py --official-http`. 공개 강남역→서울역 첫 직행 후보 N75(심야) 대상으로 좌표 검색 주변 8개/6개, 이름+좌표 후보 1개/0개. 승차 경유노선 41건 정상 조회, 하차 불일치로 endpoint_unresolved. 100m는 진단값이며 운영 정책 아님.
- 이름 검색은 코드 4 실패 기록. 별칭/승강장 표기/심야 노선 이름을 임의 변환하지 않으며 정차순서/방향·도착 ID/최신성은 아직 검증하지 못함. 원문 저장/AI 전달 없음. 합성 필터 테스트 3개 통과.

## 최신 연결 확인 — 2026-10-06

- 경기 정류소 검색/경유노선 403 해소: HTTP 200/resultCode=0·각 2건/4건. 노선 정차순서 83건도 정상. 아래 이전 실패 기록은 당시 결과다.
- 서울 정류소 명칭 검색 개인 키 진단: 공식 예시 경성중고사거리로 HTTP 200/headerCd=0·2건, ID/이름/고유번호·좌표 수치 범위 확인. 좌표계 확정/카카오 대조/경유노선/최신성 미완료.
- 재현: `backend/.venv/Scripts/python.exe backend/check_seoul_baseinfo.py --official-http`. 기본은 HTTPS이며 HTTP는 기존 사용자 승인된 공식 고정 호스트 진단 옵션이다. 운영 전송 정책 미정, 원문 저장/AI 전달 없음.
- 오류/빈 결과/누락 필드/유한하지 않은 좌표 합성 테스트 4개 통과. Notion v0.21, 앱 API 계약 변경 없음.

- 갱신: 2026-10-06 / 경기 HTTPS·서울 버스/지하철 승인된 HTTP 개인 키 최소 응답 성공. 카카오 ID 매핑·최신성/정확도·운영 보안은 미완료.
- 기준: [Notion 18절](https://app.notion.com/p/3ebace1670c6806c8199cde33ebfbdfa), provider_plan.md, todo.md.

## 신청 대상

| 대상 | 공식 신청/안내 | 현재 상태 |
| --- | --- | --- |
| 서울 버스 도착 | [공공데이터포털](https://www.data.go.kr/data/15000314/openapi.do) | 로그인 후 활용신청, 키 없음 |
| 경기 버스 도착 v2 | [공공데이터포털](https://www.data.go.kr/data/15080346/openapi.do) | 로그인 후 활용신청, 키 없음 |
| 서울 정류소 ID/좌표/경유노선 | [서울 정류소정보](https://www.data.go.kr/data/15000303/openapi.do) | 도착정보와 별도로 활용신청·권한 확인 |
| 경기 정류소/노선 기반정보 | [정류소 매뉴얼](https://www.gbis.go.kr/gbis2014/publicService.action?cmd=mBusStation), [노선 매뉴얼](https://www.gbis.go.kr/gbis2014/publicService.action?cmd=mBusRoute) | 안내의 공개키 발급에서 연결된 포털 서비스에 추가 신청. 도착 권한으로 자동 이용된다고 가정하지 않음 |
| 서울 지하철 도착 | [열린데이터광장](https://data.seoul.go.kr/dataList/OA-12764/A/1/datasetView.do) → Open API → 인증키 신청(지하철) | 버스 포털 키와 별개. 지하철 전용 인증키 필요 |

버스 두 포털 페이지는 무료·개발 트래픽 1,000·개발/운영 자동승인 표기다. 실제 승인 상태·적용량·갱신 시점은 계정 화면/실호출로 확인한다. 서울 버스/지하철은 출처표시 조건, 경기 버스는 이용허락범위 제한 없음 표기. 이 조건을 카카오 데이터에 적용하지 않는다. 앱 보관/유효기간은 D03 확정 policy_decisions.md를 따르며 공급자 실제 적용은 별개다.

## 환경 변수와 실행

인증키를 받은 뒤 루트 .env에 저장한다. 실제 키는 .env.example·채팅·로그에 넣지 않는다.

```dotenv
DATA_GO_KR_SERVICE_KEY=공공데이터포털_Decoding_인증키
SEOUL_SUBWAY_API_KEY=서울_지하철_전용_인증키
```

공공데이터포털 개인 키로 각 서비스의 활용승인이 필요하다. 버스 두 서비스의 동일 키 적용 여부도 실제 계정/응답으로 확인한다. Decoding 값을 저장하면 이중 인코딩을 피할 수 있다. 코드는 퍼센트 인코딩을 한 번 풀고 쿼리를 한 번 생성한다. 키가 URL 쿼리/경로에 들어가므로 URL·예외 원문을 출력하지 않는다.

```powershell
& backend/.venv/Scripts/python.exe backend/check_public_arrivals.py seoul-bus
& backend/.venv/Scripts/python.exe backend/check_public_arrivals.py gyeonggi-bus
& backend/.venv/Scripts/python.exe backend/check_public_arrivals.py seoul-subway
```

각 명령은 공식 예시 ID/서울역으로 최대 1회 조회한다. 카카오 연결은 미확인이다. 키가 없으면 무호출 종료하며 기본은 HTTPS·리다이렉트/HTTP 자동 전환 금지다. 경기 개인 키 요청은 HTTP 200/resultCode=0·1건·초 필드 2개 및 식별 필드 확인. 서울 HTTPS는 요청과 무자격정보 443 접속 진단 모두 시간초과, 80 접속 확인. 키 오류로 단정하지 않는다. 서비스 어댑터/출발 계산은 아니다.

서울 공식 명세는 HTTP 주소를 안내한다. `--official-http`는 고정 공식 서울 호스트의 명시적 진단 옵션이며 경기에는 적용할 수 없다. 초기 자동 승인 거부 후 사용자가 HTTP 키 전송을 승인하여 각 1회 실행했다. 서울 버스 104건(headerCd=0)/초 필드 208개, 서울 지하철 5건(INFO-000)/초 필드 5개, 모두 HTTP 200·식별/생성시각 필드 확인. 운영 상시 전송 승인/보안 정책은 미정이다. 임의 호스트/리다이렉트·원문 URL 로그는 금지한다.

```powershell
& backend/.venv/Scripts/python.exe backend/check_public_arrivals.py seoul-subway --sample
```

공식 HTTP 예제의 공개 sample 키로 비밀키 없이 서울역만 조회한다. 2026-10-06 실제 호출: HTTP 200/INFO-000·5건, 초 단위 수치·식별·생성시각 필드 존재 확인. 개인 키 인증·다른 역·최신성/정확도 검증은 아니다. 원본 응답 저장 없음.

## ID·단위·검증 순서

1. 서울 busRouteId/stId/staOrd/dir, 경기 stationId/routeId/staOrder로 구분한다. 반대편·동명·반복 정류소를 배제하려면 좌표·정차 순서·방향을 대조해야 한다. 카카오 장소 ID나 이름만으로 매핑하지 않는다.
2. [경기 항목 명세](https://www.gbis.go.kr/gbis2014/publicService.action?cmd=mBusArrival): predictTimeSec1/2는 초, predictTime1/2는 분. 초 필드 유효성을 먼저 확인하고 결측을 0으로 만들지 않는다. 0/음수·WAIT/STOP 의미는 실응답으로 확인한다.
3. [서울 지하철 명세](https://data.seoul.go.kr/dataList/openApiView.do?infId=OA-12764&srvType=A): barvlDt는 초, recptnDt는 데이터 생성시각. 노선·역·상하행·종착역·급행·열차·막차를 구분하고 수집 지연/시간대·만료를 검증한다.
4. 서울 지하철 데이터는 서울 밖 일부 역 미제공 안내가 있다. 경기 지하철 전체 지원을 가정하지 않는다. 지원 역 목록 대조 및 추가 공급자/시간표 검증이 필요하며 근거 부족은 insufficient_data다.
5. HTTP 200 본문의 인증/권한/쿼터 오류와 정상 무결과를 구분한다. 현재 도착예측을 미래 환승 성공의 보장값으로 사용하지 않는다.

## 지하철 내부 이동 확인 — 사용자 확정

역 근처에서 사용자가 탑승 여부/놓침을 직접 확인하는 수동 기록으로 안내 결과를 검증한다. GPS·고도·근접으로 승강장 도착/탑승을 판정하지 않는다. source=manual은 본인 신고이며 특정 열차 자동 인증이 아니다. 탑승만 있으면 대기가 섞여 순수 내부 이동 학습에서 제외한다. 접근 완료 수동 기록이 있으면 기존 구간 범위/입력 지연 품질 규칙을 적용한다. 필수 도보 분 입력·새 이벤트/API를 추가하지 않는다.

## 검증 상태

2026-10-06 신청 후 재확인: 사용자 정류소 신청은 서울특별시 서비스였음. 경기 정류소 검색/경유노선은 여전히 403, 경기 노선 정차순서는 200/resultCode=0·83건. 노선 데이터에도 stationId·좌표·정차순서가 있어 이를 이용한 단일 공개 사례 대조를 진행했다.

`backend/.venv/Scripts/python.exe backend/check_gyeonggi_mapping.py`는 카카오 판교역→성남시청 공개 경로와 경기 노선 후보를 최대 9회 HTTPS 요청으로 비교한다. 동명 76번 후보 5개 모두 대조, 카카오 정류장 11개 순서·승차 7/하차 17·양끝 좌표 차이 11.07m/12.85m의 후보 1개 확인. 해당 ID/순번 도착정보 1건과 식별자 일치. 좌표 허용오차 100m는 실험용 설정이며 운영 정책이 아니다. 첫 카카오 직행 버스를 진단 대상으로 택했고 사용자 실제 경로/최적 경로로 선정하지 않았다.

backend/route_mapping_probe.py의 합성 테스트 7개 통과: 역방향·멀리 있는 동명 정류장·동일 후보 복수 노선·반복 정류장 순번·좌표/중간 정류장 누락·중복 순번을 구분한다. 원본 저장/AI 전달 없음. 경기 정류소 추가 승인·서울/지하철·회차/광역·원천 최신성·운영 허용오차와 어댑터는 미완료다.

2026-10-06 후속 조사: 경기 정류소명 검색·정류소 경유노선·노선 정차순서 세 API를 HTTPS로 각 1회 조회했으나 HTTP 403. 추가 활용승인·권한·반영 상태 확인 필요, 상세 원인은 미확정. [경기 버스노선 신청](https://www.data.go.kr/data/15080662/openapi.do) 및 공식 정류소 안내에서 해당 포털 서비스의 승인 완료 여부를 확인한다. [서울 정류소 신청](https://www.data.go.kr/data/15000303/openapi.do)도 별도 확인한다. 실제 이름/좌표/순서 대조 단계는 아직 진행하지 못했다.

재검증 준비: `backend/.venv/Scripts/python.exe backend/check_public_baseinfo.py`는 경기 기반정보 3종을 각 1회 조회하고 원문/URL 없이 상태/개수를 요약한다. 승인 후 실행하며 현재 403 결과는 실제 선행 호출에서 확인했다.

경기 도착 응답 재조회에서 queryTime 존재·파싱 가능 확인. 이는 정보요청시간으로 원천 생성시각이 아니다. 확인한 도착정보 행별 생성시각 필드가 없어 원천 최신성은 미확인이다. backend/provider_freshness.py는 명시된 임계값과 생성시각으로 경계·만료·미래·누락·시간대 오류를 진단한다. 6개 합성 테스트 통과, 서비스 연결 없음. 사용자 결정(2026-10-06)으로 활성 화면의 정기 조회는 60초(1분)로 확정하며, 정보 만료는 수신/검증 생성시각 각각120초 중 이른 기한으로 확정했다. 조회 주기와 정보 만료는 별개다. 생성시각이 없으면 unknown이며 수신 시각을 대신 넣지 않는다.

- 준비 완료: 공식 신청/필드/범위 조사, 검증 CLI, 오류/빈 응답/단위/키 누락 로컬 검증, 서울역 공개 샘플 1회.
- 확인: 개인 키 2종 저장, 경기 개인 키 HTTPS 최소 응답/필드 1건.
- 확인: 사용자 승인 후 서울 개인 키 최소 인증/응답 필드 확인. 세 API 연결 확인 완료.
- 미완료: 기반정보 활용승인·카카오 ID/방향 매핑·경기 전체 지원·최신성/정확도·운영 조건. D02-03/F01 전체는 미체크.

## F07-01a 어댑터/신선도 준비 — 2026-10-13

2026-10-13 경기 공식 항목 매뉴얼을 다시 읽어 stationId/routeId/staOrder·routeDestId·predictTimeSec1/2·flag와 queryTime=정보요청시간을 확인했다. 새 서버 어댑터는 HTTPS/리다이렉트 금지·응답 제한·오류 분리와 원천 시간unknown을 유지한다. 내부 합성 timestamp만120초 경계/정렬을 검증했고 공개조회는미매핑/미지원으로막는다. 개인 키 실조회와 운영 매핑을 확인한 것으로 기록하지 않는다. arrivals_api.md·Notion v0.58.


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
