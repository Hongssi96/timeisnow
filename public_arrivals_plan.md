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
