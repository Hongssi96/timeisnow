# 지금이니? — 개발 일지

기능별 작업이 끝날 때 짧게 추가한다. 아래 ‘실제 기록’만 완료된 작업이며 템플릿은 기록 형식이다.

## 실제 기록

### 2026-10-07 — F04-03 실제 경로 후보 비교 화면
- 목표/기반: 사용자 진행 요청에 따라 F04-02 main63674ac 병합을 fetch로 확인, 최신 main에서 codex/journey-comparison 생성. 기존 미색/초록·카드/버튼·내비게이션 톤으로 실제 출발/도착 선택과 후보 비교를 연결한다. 에이전트 MR 생성/main 병합 없음.
- 사전 확인/명세: todo/feature_breakdown F04-03·최신 Notion v0.41 5.2.3~4/20절·planning/personalization/ai_prompts/logging/development_log·design_guide/screen_plan 및 기존 App/OriginSelector/OriginReview/MapPinPicker/PlacesCard·CSS·API클라이언트/테스트를 비교했다. 구현 전에 Notion v0.42 5.2.5에 사용자 흐름·접수/조회/중지/재시도/만료·비교/상세/미확인 근거·호환성을 구체화했다. 기존 서버 API/JSON모델/권한/DB DDL/300초·600초·24시간 및GPS 수치 보류 계약 유지. 최신 재조회/전문 로컬 api_contract.md 동기화 확인. 기준 https://app.notion.com/p/3ebace1670c6806c8199cde33ebfbdfa
- 화면: App.jsx 홈 ‘경로 후보 비교’→JourneyComparison.jsx. 기존 내비게이션 항목을 추가하지 않고 비교 페이지/복귀를 제공, 유효한 홈출발지를 초기값으로만 사용한다. 출발/도착을 직접 선택해 기존 OriginSelector/OriginReview를 목적 문구와 함께 재사용한다. 명시 클릭 후 POST202·GET 결과를 조회한다. 비교 기준으로 로컬 정렬하고 JourneyCandidates.jsx 카드에서 총 예상시간/환승수/제공된 일부도보·차량명·구간 역할/정류장순서·연결/누락 근거를 표시한다. 반복노선명/같은세부분류는표시에서만중복제거, 펼친상세는전체폭·14px읽기문구/44px버튼/Enter포커스·PC2열/모바일1열. 출입구/플랫폼·실제운행방향/시간표·환승가능성/AI/실시간은확인필요, 루틴저장/실제이동은제공하지않는다.
- 조회/안전: src/lib/journeys.js는journey.v1·ID/순서/기한/정수/시간분해/연결참조·필수누락사유를검증하고잘못된모델/형식/참조를성공으로표시하지않는다. 2/5/10/최대30초 조회, 유효Retry-After1~3600초우선. 숨김화면은새GET중지/진행중GET취소, 복귀시같은ID. 이탈/입력변경/계정/인증만료/기한은취소·후보/상세제거·늦은응답무시. 입력선택기한보다검색기한을연장하지않으며반환직후에도기한을재검사한다. api.js는Retry-After값만추가노출하며자동재시도없음. 접수응답을못받은재시도는동일본문/키, 접수된검색의조회실패는GET만수동재시도. 입력변경/명시새조회는새키,429대기/409위치충돌/404만료/안전한실패·정상무결과구분. URL/DB/localStorage/콘솔에개인위치/후보/본문/키/서버원문을저장하지않는다.
- 실제 자동화 검증: 프론트13파일97개·빌드1899모듈통과(기존79+신규18). 공통모델검증·손상된연결/ID/미지원버전/null구간/시간·TTL·정렬/누락과0·Retry-After·조회간격/숨김/진행GET취소/동일ID복귀·기한뒤성공반영금지·명시입력/POST·동일키재시도/GET재확인·상세/정렬·실패/빈결과/인증만료/개인자료제거/입력변경취소·도착지문구/홈예시분리확인. 처음8개화면테스트는fake timer와userEvent대기조합으로timeout, 테스트입력을act/fireEvent로바꿔실제기한/비동기검증을유지한뒤통과했다. 백엔드115개회귀통과, 서버/API/DB코드변경없음. git diff --check 확인.
- 실제 브라우저: 합성 회원/공개강남역·서울역주변저장장소2개로로그인→출발/도착직접선택→실제POST202/GET200→15후보확인. PC1440×1000/모바일390×844 카드/상세/정류장순서·미확인도보·로컬환승정렬/복귀·Enter상세펼치기/보이는포커스·가로넘침없음(390px에서scrollWidth375)·콘솔error0. 공통CSS변경후홈/장소설정/계정모바일회귀확인. 실제5분검색만료로후보/펼친상세가제거되고만료안내를확인했다. 실패 fixture 재조회시점에는이미자연만료돼브라우저실패시각검증을주장하지않는다. 실패/빈결과/숨김/인증/GPS·시간초과/늦은응답은모의검증이다. 실제GPS권한승인/기기측정·실시간/AI/물리방향/실제환승·시간표품질은미검증.
- 실행/정리: 기존백엔드8000·Vite5173실행을확인하고재사용했다. 실제응답에심야노선이있어운행시간/지금이용가능여부를확인필요로안내하며공급자이름에서시간표를추측해필터링하지않는다. 합성계정로그아웃, 해당소유회원/장소/세션/검색/작업/멱등키를삭제·잔여0확인, 검증용상태fixture도함께정리. 브라우저닫기/viewport복구. 캡처는Codex visualization폴더의f0403-comparison-desktop.png·f0403-comparison-mobile.png에보관,레포미포함.
- 변경 파일/문서: frontend/src/components/JourneyComparison.jsx/JourneyCandidates.jsx/OriginSelector.jsx/OriginReview.jsx, src/lib/journeys.js/api.js, src/app/App.jsx, src/styles/styles.css, 대응tests/components·lib·app 및tests/fixtures/journeys.json(백엔드공통모델에서만든합성좌표미포함fixture). Notion/api_contract.md·journey_api.md·planning.md·personalization.md·ai_prompts.md·logging.md·design_guide.md·screen_plan.md·README.md·frontend/README.md·todo.md·feature_breakdown.md·일지동기화.
- 배운 개념: 검색접수와결과조회·정상무결과와장애·부분도보와전체도보·정류장순서와실제방향을다르게표현해야한다. Retry-After/페이지가시성/기한/취소가함께동작해야오래된결과나중복POST를줄일수있다. 화면정렬은조회된후보의표시순서이며추가공급자요청이나이동안내/루틴선택이아니다.
- 완료/다음: F04-03만완료, 사용자codex/journey-comparison→main MR/병합 후 F04-04 환승/출입구/플랫폼·마지막도보근거보강. F04-05/F05/F07 및실제운행·실시간/출발안내·루틴저장은후속유지, GPS수치판정은보류다.

### 2026-10-07 — F04-02 버스·지하철·도보 공통 구간 모델
- 목표/기반: F04-01 사용자 병합 main9670281을 fetch로 확인하고 codex/journey-segments를 생성했다. API 후보의 최소 단계 데이터를 후속 비교 화면/F05 근거에서 사용할 공통 모델로 보강했다. 에이전트 MR 생성/main 병합 없음.
- 사전 확인/명세: todo/feature_breakdown F04-02, 최신 Notion v0.40 5.2.3/20절, journey_api·planning·personalization·ai_prompts·logging·development_log·실제 provider/작업/테스트를 비교했다. 최신 카카오 공식 REST route/step/stops/vehicles/path 스키마를 확인했고 이름·순서를 공공ID/물리 방향으로 추정하지 않았다(https://developers.kakao.com/docs/ko/kakaomap/rest-api). 구현 전에 Notion v0.41 5.2.4·변경 이력/호환성/입출력·완료 범위를 구체화했다. GPS 수치 보류·수동 확인/권한/기한/원본 비저장·AI 미호출 유지. 최종 재조회/로컬 api_contract.md 전문 동기화 확인. 기준 https://app.notion.com/p/3ebace1670c6806c8199cde33ebfbdfa
- 모델: backend/app/journey_models.py의 엄격한 공통 Candidate/Leg/Connection/Breakdown과 이전 형식 모델. 기존 필드/ID/순서/초·미터를 유지하고 journey.v1·도보 access/transfer/egress·교통 boarding/alighting/direction/vehicle_options·교통단계 기반 환승수·connections·timing_breakdown을 추가했다. 승하차는 공급자 첫/마지막 정류장명, 공공ID/출입구/플랫폼은null. 방향은 provider_stop_order이며 같은 이름/가까운 위치로 물리 일치·환승 가능을 확정하지 않는다.
- 보강/검증: journey_provider.py는 geometry를 검증 후 폐기하고 차량 세부분류 문자열만 추가 보존한다. 교통 단계수/공급자 환승수 최대2회, 모순된 route 종류·순서/ID·유효하지 않은 숫자/필드는 안전한 PROVIDER_RESPONSE_INVALID. 누락된 접근/마지막/환승 도보·공공방향을 사유로 표시하고 명시0초만0으로 유지한다. 총시간/단계 합계 차이는 unallocated(대기/여유로 단정하지 않음), 음수 차이는null/inconsistent·DURATION_TOTAL_MISMATCH. 후보 validity=insufficient_data·estimated_arrival_at:null 유지.
- 이전 결과/스키마: journeys.py GET는 공통 모델로 저장 결과를 읽고 누락 사유를 합친다. 이전 JSONB 후보는 기존leg/candidate ID를 유지해 보강, 차량 종류null·connection_id는candidate+인접교통leg의uuid5로 안정적이며 재조회마다 바뀌지 않는다. DB 쓰기/공급자 재호출 없음. 이상 필드/잘못된 결과는502, worker 입력 문제는기존failed/error. SearchEnvelope/Candidate/Leg/Connection/Breakdown을 OpenAPI GET200 스키마에 노출했다. DB head0006 유지, 새 마이그레이션 없음.
- 실제 검증: 백엔드115개 통과(기존106+모델8+저장결과ASGI1). 직접 버스/지하철·버스↔버스/버스↔지하철/지하철↔버스/지하철↔지하철의 공통 타입/순서·역할·이름/차량분류·연결, 연속 도보·누락과0초·시간차/모순·환승수차/상한·route종류/참조/숫자/추가좌표 거절·legacy ID/값 유지·OpenAPI/실응답 일치·DB 재저장/공급자 재호출 없음 확인. 기존 PostgreSQL auth/작업/소유권/버전/멱등/만료/로그 비노출·migration 검증 유지. 프론트11파일79개·빌드1896모듈 통과, UI 코드 변경 없으므로 새 시각 검증 수행하지 않았다. 최초 모델 단독 테스트는 backend import 경로 누락으로 실패했고 독립 실행 경로를 맞춘 뒤8개 및전체115개가 통과했다.
- 실제 실행: 검증용 uvicorn을 최신 코드로 재시작, 합성 계정과 공개 강남역→서울역으로 카카오 경로1회 요청. HTTP202→GET200의15후보가 SearchEnvelope 검증에 통과했고 재조회 후보/leg/connection ID 일치·no-store/요청ID 확인. 실제 교통순서는 SUBWAY>SUBWAY>SUBWAY3개, SUBWAY>SUBWAY2개, SUBWAY>SUBWAY>BUS3개, BUS>SUBWAY>SUBWAY1개, BUS>BUS1개, BUS직행5개. 도보17개는모두transfer이며 연결17개 feasibility=unknown. 접근/마지막도보는 실제 응답에서 빠져 누락 사유로 유지했다. 합성 회원/세션/후보/작업 제거, 실제 사용자GPS/실제 환승 성공/물리 방향·공공ID/역 내부/AI·실시간은 미검증이다.
- 문서/완료: journey_api.md·api_contract.md·planning.md·personalization.md·ai_prompts.md·logging.md·README.md·backend/README.md·todo.md·feature_breakdown.md·일지 동기화. F04-02만 체크, F04-03~05 및F05/F07은 후속 유지. 공식 명세의 세부 차량명 변경 가능성을 상수 목록으로 고정하지 않았다.
- 배운 개념: 공통 모델은 서로 다른 교통수단을 같은 순서/시간/참조로 다루되 근거 수준을 보존한다. 빠진 도보와0초 도보, 공급자 총시간과 단계 합계, 정류장 순서와 물리 방향은 다르다. UUID 기반 안정적 연결 ID는 재조회·legacy 보강에서도 참조를 유지한다.
- 다음: 사용자 codex/journey-segments→main MR/병합 후 F04-03 후보 비교 화면. 실제 제공되지 않은 출입구/플랫폼/접근/마지막 도보와 실시간 연결 근거는 후속에서 확보한다.

### 2026-10-07 — F04-01 비동기 카카오 대중교통 경로 후보 API
- 최종 main 통합: 게시 전 fetch에서 사용자가 F03-05a를 main8b4b40b에 병합한 것을 확인했다. F04 기능 브랜치에 origin/main을 merge하며 Notion v0.40 전체 계약과 F03-05a/F04 일지·정책·TODO를 모두 보존해 문서 충돌을 해결했다. 통합 후 백엔드106개·프론트11파일79개·빌드1896모듈 통과, conflict marker0건·diff --check 확인. 아래105개/73개는 통합 전 실제 검증 이력이다. 다음MR은 codex/journey-search→main만 필요하며 에이전트가 main/MR을 병합하지 않는다.
- 목표: 사용자 F04 진행 요청에 따라 작은 기능 단위인 F04-01 API부터 구현했다. 최신 main0402d67에서 codex/journey-search 생성, F03-05a/codex/origin-quality/0168464는 아직 main 미병합으로 중복 코드 포함하지 않았다. GPS 수치 보류·수동 확인 요구는 여정 입력에서 location_confirmed:true 필수로 유지한다. 에이전트 MR 생성/병합 없음.
- 사전 확인: todo.md/F04-01·최신 Notion v0.39 5.2/20절·planning/feature_breakdown/personalization/ai_prompts/logging/policy_decisions·provider_plan/provider_conditions·기존 공급자 진단 및auth/장소 코드를 비교했다. 최신 카카오 공식 REST 대중교통 경로 문서의 요청/상태/route/steps/time/geometry를 확인했다(https://developers.kakao.com/docs/ko/kakaomap/rest-api). 조건 추가 확인 생략 가정은 유지하며 공급자 승낙/정확도 검증 완료로 표현하지 않는다.
- 명세 변경: 구현 전에 Notion v0.40 5.2.3으로 단계별 입력/응답/작업/오류/멱등/권한/상한/보관/재시작 실패 계약을 구체화하고 구현 상태·예시·공통목록·변경 이력을 맞췄다. depart_now(Asia/Seoul)만 실행, arrive_by는 UNSUPPORTED_TIMING으로 명시하며 목표 도착 설계는 후속 유지. AI/실시간/완전한 비교·방향/역 내부/중간지역 범위는 후속이다. 최신 저장 재조회 후 api_contract.md 전문 동기화. 기준 https://app.notion.com/p/3ebace1670c6806c8199cde33ebfbdfa
- 구현: backend/app/journeys.py — POST202 접수, worker queued/running/succeeded/failed, 본인 GET 검색/GET jobs. 로그인·Origin/CSRF·no-store, 선택 멱등 키/HMAC 본문 해시24시간, 동일202 ID 재현·변경본문409·현재 소유권/위치버전/만료 재검사. 사용자10회/분(실패 포함), 동시2개/사용자·전체8개, admission advisory lock으로 동시 키/진행 수 직렬화. DB는 두 짧은 트랜잭션으로 실패 쿼터도 소비한다.
- 공급자/모델: journey_provider.py는 기존 서버 키로 고정 HTTPS 호스트/no redirect·10초/2MB 상한을 적용한다. 정상 무결과와 장애/시간초과/잘못된 응답을 구분, 유한 좌표/정수 초·미터/타입·이름 필드를 검증하고 geometry/원문 안내/landingURL을 제거한다. 최대2회 환승/20후보, 선호별 총시간/환승/도보시간 정렬. 최소 ordered_legs는 정류장/차량명·종류/순서·공급자시간이며 완전한 방향·공공ID/출입구/플랫폼 근거는 F04-02~05 후속. 모든 후보 provider_estimate·insufficient_data·estimated_arrival_at:null, AI/실시간 근거를 만들지 않는다.
- 보관/중단: migration0006_journey_searches의 검색/작업 상태·최소 저장 장소 참조·정규화 후보 및 멱등 테이블. 입력 GPS/지도 좌표·측정치/주소·원본 응답/키/본문은 DB/로그 비저장·AI 전달 없음. 검색300초, 종료 작업24시간, 만료 사용 차단/요청 시 정리. 작업60초 기한을 넘으면 JOB_INTERRUPTED, 늦은 응답은 실패를 성공으로 되돌리지 않는다. worker는 사용자 active/장소 위치를 전후 재검사한다. 재시작 뒤 좌표로 자동 재실행하지 않는다. 매일 청소 스케줄은 후속이다.
- 실제 검증: PostgreSQL 임시 스키마/ASGI 전체105개 통과. 신규11개는202/200·OpenAPI202·동시 멱등/변경본문/재현·본인/타인/삭제/이름변경/위치버전·수동GPS strict true·provider 처리 중 위치변경·검색/작업 만료·중단/늦은실행 차단·실패쿼터/동시진행·정상무결과/안전한실패·정렬/환승초과·geometry 유효/폐기·리다이렉트/시간초과/2MB 상한·DB/로그 비노출을 확인했다. migrations 왕복/기존 장소 보존/중복 upgrade 포함. 기존main 프론트10파일73개·빌드1895모듈 통과, UI 변경 없으므로 새 시각 검증 없음. F03-05a 브랜치의79개와 다른 기반이며 해당 기능을 제거했다는 의미가 아니다.
- 실행 검증: 개발 DB0005→0006 upgrade만 적용해 기존 데이터 유지, 검증용 uvicorn 최신 코드 기동. 공개 강남역→서울역 좌표를 한 번 조회해 실제 카카오15후보·HTTP202 queued→GET200 succeeded·no-store/X-Request-ID·같은 키 동일202 ID·GET jobs 성공 확인. 테스트 도구가 logout204 빈 본문을 JSON으로 읽어 마지막 출력에서 오류가 발생했지만 finally에서 합성 자료는 제거됐고 경로 검증은 완료됐다. 도구의204 처리를 고쳐 별도 합성 로그인/로그아웃204·빈본문·정리를 확인했으며 공급자는 재호출하지 않았다. 합성 회원/세션/후보/작업/키 제거. 실제 사용자GPS/목표도착/실시간/AI/전체환승/역내부 정확도는 미검증.
- 변경 파일: journeys.py·journey_provider.py·main.py·0006 migration·test_journeys.py·test_migrations.py; journey_api.md·api_contract.md·database_schema.md·migrations.md·database.md·backend/README.md·README.md·planning.md·personalization.md·ai_prompts.md·logging.md·todo.md·feature_breakdown.md 및 일지.
- 배운 개념:202는 공급자 성공이 아닌 작업 접수다. 검색 결과 수명과 작업 상태/재시도 키 수명은 다르고 실제 위치를 저장하지 않아도 최소 참조/HMAC/기한으로 안전하게 중복·만료를 처리할 수 있다. 경로 예상 시간은 실시간 도착/탑승 가능/AI 도보 산정과 구분한다.
- 남은 일/다음: F04-01 API만 완료, F04-02~05는 유지. 사용자 기능 브랜치 검토/MR/병합 후 공통 구간 모델/방향·누락 근거 보강과 후보 비교 UI로 이어간다. F03-05a 별도MR/main 병합 및 GPS 수치 보류 상태를 유지한다.

### 2026-10-07 — F03-05a GPS 수치 보류·실제 출발 위치 수동 확인
- 목표/사용자 결정: ‘GPS 수치는 보류하고 수동 확인만’. 최신 main0402d67에서 codex/origin-quality를 만들었다. F03-04/ff5a5f4·R01/ca8cd93 포함을 fetch/ancestor로 확인했으며 에이전트는 MR 생성/main 병합을 수행하지 않는다.
- 명세 확인/변경: 최신 Notion v0.38 5.2.1과 todo·기획/개인화/프롬프트/로깅·정책·디자인/화면·기존 JSX/CSS를 비교했다. 구현 전에 v0.39 5.2.2를 추가하고 API 목록/상태/예시/호환성/변경 이력을 맞췄다. location_confirmed 선택 strict boolean(default false), user_confirmed, quality/place_match 추가. false/pending·지도/장소·auth/소유권/오류 계약 유지. GPS 수치/자동 근접·출입구 일치 판정은 미정/보류이며 F03-05 상위 체크를 유지했다. 최종 원문 저장 재조회 및 api_contract.md 전문 동기화 확인. 기준 https://app.notion.com/p/3ebace1670c6806c8199cde33ebfbdfa
- 구현: backend/app/origins.py는 확인을 본인 보고로 반환하며 품질 unassessed·수치 정책 deferred·장소 일치 unconfirmed를 유지한다. 현재/지도는 기존 지원지역 확인, 저장 장소는 본인/위치 버전 재검사 후 selected_by_user. 과거/미래 관계는 표시 정보이며 자동 승인/거절 없음. DB 스키마0005 유지, 좌표/측정치 저장·AI 전달·로그 원문 없음.
- 화면: frontend/src/components/OriginSelector.jsx·OriginReview.jsx는 최초 GPS 응답을 미리보기로만 유지한다. 실제 지도 로딩 성공 후 ‘이 위치가 실제 출발 위치예요’로 같은 측정치를 다시 확인하고 성공 후 적용한다. MapPinPicker.jsx에 선택적 로딩 상태 콜백을 추가했다. 핀 이동은 지도 직접 선택으로 전환, 저장 장소는 직접 선택, 재측정/방법 전환/이탈/인증 만료/600초 확인 만료 시 초안 제거. 만료는 진행 중 요청도 취소해 늦은 성공을 무시한다. App.jsx는 위치 직접 확인과 GPS 자동 판정 보류를 함께 표시한다. 기존 클래스/팔레트/반응형 재사용, 새 디자인 값 없음.
- 실제 검증: PostgreSQL 임시 스키마/ASGI 백엔드95개 통과. 기본false/엄격한 boolean·과거/미래·큰 정확도에서도 자동 수치 판정 없음·본인 장소/버전/CSRF·쿼터·로그 비노출 검증. 프론트11개 파일79개 통과(미확인 자동 적용 없음·확인 실패/잘못된 응답·지도 성공/실패 재시도 상태·핀 전환·초안 만료 및 확인 중 늦은 응답 차단). Vite build1896모듈 통과, git diff --check 통과.
- 실제 실행: 검증용 백엔드를 최신 코드로 재시작해 localhost8000에서 공개 서울시청 합성 좌표의 pending/user_confirmed200·no-store·future/품질unassessed/일치unconfirmed를 확인했다. 실제 앱의 지도 방향 버튼→서버 지역 확인→준비 카드 적용 회귀 확인. 임시 HTML에서 실제 OriginReview/MapPinPicker를 합성 측정치와 연결하여1440×1000/390×844 실제 지도·미래 안내·확인 버튼/핀 이동 콜백·가로 넘침 없음·브라우저 콘솔 error0건 확인. 실제 기기 GPS/권한 승인·휴대전화 정확도는 검증하지 않았으며 GPS 단계는 모의 테스트다. 임시 HTML/JSX·합성 계정/세션 제거, 검증 이미지는 Codex visualization 폴더에 보관했다.
- 문서/진행: origin_api.md·api_contract.md·planning.md·personalization.md·ai_prompts.md·logging.md·policy_decisions.md·screen_plan.md·design_guide.md·README.md·frontend/README.md·todo.md·feature_breakdown.md 동기화. F03-05a만 완료, F03-05 자동 품질/일치는 보류. 다음은 사용자 기능 브랜치 MR/병합 후 F04-01 대중교통 경로 후보 조회다.
- 배운 개념: 사용자가 위치를 확인한 사실과 GPS 오차/최신성 검증은 서로 다르다. 확인 화면 유효기간은 GPS 최신성 보증이 아니며 만료/취소 이후 응답도 적용되지 않아야 한다. W3C Geolocation의 accuracy/timestamp 의미는 참고하되 앱 임계값으로 사용하지 않았다(https://www.w3.org/TR/geolocation/).

### 2026-10-07 — F03-04 브랜치에 병합된 프론트 폴더 구조 반영
- 요청: R01이 먼저 main에 병합되어 F03-04를 새 구조에 맞추고 다시 검증/푸시한다. 기존 codex/current-origin을 계속 사용하며 main이나 MR을 에이전트가 병합하지 않는다.
- 확인: 최신 main ca8cd93에 R01/1ca0991 포함, F03-04/235d617 미포함을 fetch/ancestor로 확인했다. 최신 Notion v0.38 5.2.1 계약·TODO·폴더 README/Vite와 F03-04 import/테스트를 비교했다.
- 통합: 로컬 기능 브랜치에 origin/main을 병합하며 README.md·development_log.md·todo.md·src/app/App.jsx 충돌을 해결했다. 두 기능/일지 모두 보존, App은 새 styles/lib/components 경로와 OriginSelector를 사용한다. 자동 이동된 MapPinPicker에도 F03-04 설명/접근성 props와 새lib 경로를 모두 유지했다.
- 이동: OriginSelector.jsx→src/components, currentOrigin.js→src/lib, App.origin.test.jsx→tests/app, OriginSelector.test.jsx→tests/components, currentOrigin.test.js→tests/lib. 실제 import/vi.mock 경로를 함께 바꿔 Vitest tests/** 패턴에서 새16개를 누락하지 않는다. frontend/README.md·screen_plan.md·todo.md의 미통합 안내도 현재 상태로 갱신했다.
- 실제 검증: Vitest10개 파일/73개 테스트 모두 통과, Vite build1895모듈 통과. 실행 중 Vite5173 홈 렌더링과 브라우저 콘솔 error0건 확인. conflict marker 검색0건·git diff --check 확인. API/백엔드 코드를 추가 수정하지 않아 백엔드94개 검증은 최초F03-04 기록을 유지하며 이번에 재실행하지 않았다. 실제 기기 GPS나 지도 시각 재검증은 이번 경로 정리에서 수행하지 않았다.
- 명세 영향: 없음. F03-04 기능/권한/입출력·GPS/저장/로그 계약을 유지하고 내부 경로/충돌만 정리했다. 최신 Notion v0.38을 재확인하며 수정하지 않는다. 기준 https://app.notion.com/p/3ebace1670c6806c8199cde33ebfbdfa
- 배운 개념: 파일 rename과 기능 수정은 Git이 일부 자동 결합해도 새 파일/import·테스트 검색 경로는 직접 맞춰야 한다. 기존 feature에 main을 merge하면 공개 커밋을 재작성하거나 force-push하지 않고 최신 기반을 포함할 수 있다.
- 남은 일/다음: codex/current-origin 통합 커밋/푸시 후 사용자가 main 대상MR을 생성·병합한다. R01은 이미 main에 있어 다시 MR 만들 필요 없음. 병합 후 F03-05 위치 품질/저장 장소 일치 판정.

### 2026-10-07 — F03-04 현재 위치·지도·본인 장소 출발지 선택
- 목표: 홈 ‘다른 곳에서 출발’의 미연동 예시를 로그인 기반 출발지 선택으로 연결했다. 실제 경로/출발 시간은 F04~07 후속이며 실제 선택에 가상 집의 출발 안내·이동 체험을 적용하지 않는다.
- Git/명세 확인: F03-03 49a0a2f의 최신 main30b62a9 병합을 fetch/ancestor로 확인하고 깨끗한 상태에서 codex/current-origin 생성. 최신 Notion v0.37·TODO·기능 목록·기획/개인화/프롬프트/로그·디자인/화면/기존 JSX/CSS/장소/auth 코드를 비교했다. 사용자 검토 후 MR 생성/병합은 사용자 수행.
- 계약/동기화: Notion v0.38에5.2.1·API 목록·합성 요청/응답 예시·공통 구현 상태/변경 이력·다음F03-05를 갱신하고 저장 재조회 확인. api_contract.md는 전체 본문을 복사해 목차 매크로/끝 개행을 제외하고 대조한다. 신규 side-effect-free POST /origin-validations는 생성 멱등 결과 대상이 아니며 기존 auth/장소/경로 객체는 유지한다.
- 변경 파일: backend/app/origins.py/main.py·test_origins.py; frontend/src/OriginSelector.jsx/테스트·currentOrigin.js/테스트·App.jsx/App.origin.test.jsx·MapPinPicker.jsx·styles.css; origin_api.md·api_contract.md·place_api.md·README.md·backend/README.md·planning.md·screen_plan.md·design_guide.md·logging.md·todo.md·feature_breakdown.md·development_log.md. DB 마이그레이션/AI 프롬프트 블록/개인화 계산 공식 변경 없음, head0005 유지.
- 서버: current_location/map_pin/saved_place discriminated 입력·좌표/정확도 유한값/시간대ISO 문자열/UTC 정규화, 서울·경기 지역 확인, 본인 장소404/위치 버전409/현재 저장 이름. 로그인/Origin·CSRF/no-store·사용자10회/분·공급자 실패도 제한 소비. 위치 원문 저장소/로그/AI 전달 없음, 기존 HMAC 버킷/세션만 갱신. 현재GPS 품질pending은 F03-05 판정 전이며 집 근처라도 저장 집으로 바꾸지 않는다.
- 화면: 인증 재확인 후 명시 클릭 getCurrentPosition1회(high accuracy/maximumAge0/native10초), 권한 대기 포함 전체15초. 거절/시간초과/미지원/위치 불가 시 지도·재시도. 초기 중심은 본인 장소/공개 서울시청이며 핀 명시 선택 전 확인 차단. 기존 지도·5m 방향 버튼·현재/지도/본인 목록/빈 상태/더보기/실패 재조회. 방법 변경/이탈 취소·늦은GPS 무시. 선택은 App 메모리600초, 만료 안내·재선택·새로고침/계정/인증 만료 인지 시 제거. 실제 선택 중 예시 홈 경로/시간/출발 버튼을 숨긴다.
- 실제 검증:
  - Python unittest 전체94개(기존90+신규4) 통과: 실제 임시 PostgreSQL/ASGI 인증·CSRF·타인/삭제404·위치 버전409·이름 변경 수용·시각/정확도/좌표 형식·지원지역/공급자 실패·10실패 후429/Retry-After·600초/no-store·로그 ID 일치 및 위치/쿠키/키 비노출. 테스트 임시 스키마는 각 tearDown에서 제거.
  - Vitest 전체73개(기존57+신규16)·Vite build 통과: 단발 측정/메타데이터·거절/불가/시간초과/미지원·15초 총대기/취소·늦은 결과, 지도 초깃값 차단, 인증 만료 시 GPS 호출 전 차단·목록 제거, 저장 장소 충돌, 실제 선택의 예시 이동 차단/10분 만료/계정 진입 제거. 실패했던 테스트는 jest-dom 미설치 matcher/타이머 도구 적용 시점/다른 계정 준비 시 기존 세션 사용 문제를 고쳐 재실행 통과했다.
  - 실행 서버 로컬 HTTP에서 공개 서울시청 합성 current_location 입력200/no-store·quality_status=pending·UTC captured_at=2026-10-07T02:00:00Z 확인. req_d945912b44dc4de398ba91f572296b2e 응답 ID와 서버 JSON 완료 로그 대조, 위치 원문 출력 없음.
  - 실제 브라우저1440×1000/390×844에서 합성 회원 로그인·지도/방향 버튼(데스크톱 Enter 키)·지역 확인/준비 카드·재선택·빈 저장 장소·새로고침 초기화 확인. 모바일 clientWidth/scrollWidth 모두390·실제 출발 버튼0. 화면 캡처 f03-04-desktop.jpg/f03-04-mobile.jpg(개인 위치 없음). 실제 기기 GPS/권한 승인·실제 휴대전화는 요청하지 않았고 성공/거절/타임아웃은 모의 검증이다.
- 실행 문제/조치: 장시간 Vite가 이전 브랜치 PlacesCard의 빈 변환 모듈을 반환해 브라우저 export 오류/빈 화면이 발생했다. 해당 확인된 Vite만 재시작해 정상 렌더링·지도를 검증했다. 백엔드도 신규 API 반영 후 PID9780/8000 재시작, 프론트5173 실행 유지. npm 옵션 전달 문제는 직접 node Vite CLI 실행으로 복구했다. 이번에 만든 합성 QA 회원만 이메일/표시이름으로 한정 삭제(1명), 잔여 인증0건 확인.
- 배운 개념: 기기 위치 측정·지원지역 확인·GPS 품질 판단·경로 계산은 다른 단계다. native timeout은 권한 대기를 온전히 제한하지 않아 앱 전체 타이머가 필요하다. 메모리 선택600초는 GPS 최신성을 보증하지 않으며 후속 계산 때 재검증해야 한다. 근거: https://www.w3.org/TR/geolocation/.
- 남은 일/다음: F03-05 최신성/정확도 임계값·미래/오래된 측정 재확인·저장 장소/실제 출입구 일치 판정. F04~07 경로/출발 안내는 미구현. 실제 기기 위치/모바일 GPS 검증은 별도. F03-04 기능 브랜치를 커밋/푸시하고 사용자 검토/병합을 기다린다.
- Notion: https://app.notion.com/p/3ebace1670c6806c8199cde33ebfbdfa

### 2026-10-07 — R01 프론트엔드 실행 코드·테스트 디렉터리 분리
- 요청/목표: frontend/src에 섞인 실행·테스트 파일을 역할별 폴더로 구분한다. 화면·API·계산·로그 정책은 그대로 유지한다.
- Git/선행 확인: 최신 main30b62a9를 fetch하고 깨끗한 상태에서 codex/frontend-structure 생성. F03-04 235d617은 아직 main 미병합이며 codex/current-origin에 보존되어 있어 이번 작업에 합치지 않았다. TODO·기능 목록/기획/화면/디자인·기존 import/mocks/Vite 설정과 Notion 최신v0.38의 기존 인증/장소 계약을 확인했다.
- 구조: src/main.jsx는 진입점, src/app/App.jsx는 앱 화면, src/components는 계정/장소/지도 UI, src/lib는 API/지도 SDK, src/styles는 기존 CSS. tests/app·components·lib로 기존7개 테스트 파일을 옮기고 tests/setup.js로 공통 환경을 분리했다. index.html·vite.config.js·package.json과 잠금 파일은 도구 진입점으로 frontend 루트에 유지, node_modules/dist 생성 폴더는 이동하지 않았다.
- 변경: 위 파일16개 이동·main/import/vi.mock/동적import 경로 수정, vite.config.js test.include=tests/**/*.test.{js,jsx}·setupFiles=tests/setup.js. frontend/README.md에 트리·파일 추가 규칙·기존 실행 명령·미병합 F03-04 경로 대응 안내. README.md·screen_plan.md·design_guide.md 경로/안내 및 TODO/기능 목록 R01 갱신. 과거 일지의 당시 파일 경로는 역사 기록으로 보존한다.
- 실제 검증: npm --prefix frontend test에서 기존7개 파일/57개 모두 통과, npm --prefix frontend run build 통과(1893모듈). 실행 중 Vite5173에서 새 src/app 및 import 경로로 홈 렌더링 확인, 브라우저 콘솔 error0건. 화면/CSS 내용 변경 없이 파일 위치만 이동하여 별도 시각 재설계·새 테스트·백엔드 테스트는 수행하지 않았다.
- 명세 영향: 없음. 경로·인증·입출력·권한·시간/계산·보관/로그·화면 동작 계약을 바꾸지 않은 내부 파일 정리이므로 Notion 수정 불필요. 최신 Notion v0.38 확인, main의 로컬v0.37과 차이는 미병합 F03-04 명세이며 기존 계약은 유지한다. https://app.notion.com/p/3ebace1670c6806c8199cde33ebfbdfa
- 배운 개념: 브라우저 실행 모듈과 테스트 러너 코드를 폴더로 분리할 수 있다. Vitest include/setupFiles와 실제 import·mock 경로를 함께 옮겨야 기존 검증을 유지한다. HTML/설정/package 파일은 Vite/npm이 찾는 프로젝트 루트에 두는 것이 적절하다.
- 남은 일/다음: 기능 브랜치 커밋/푸시 후 사용자 MR/병합. 미병합 F03-04의 App/지도 변경과 OriginSelector/currentOrigin/테스트도 새 src/components·lib/tests 경로로 맞춰 병합해야 한다. 그 후 F03-05 위치 품질/저장 장소 일치 판정 진행. MR 생성/병합은 수행하지 않는다.

### 2026-10-07 — F03-03 내 장소 이름 수정·삭제
- 목표: 기존 목록/상세·위치/출입구 수정에 저장 이름(label) 수정과 삭제 확인/취소·DELETE204를 추가했다. 실제 루틴·도보·경로 저장소는 아직 없으므로 해당 연결 처리는 F04~06 후속이다.
- Git/선행 확인: 최신 main4225eea(init→main, F03-02 병합)를 fetch하고 깨끗한 상태에서 codex/place-management 생성. Notion v0.36, TODO/기능 목록, 장소 API·기획·DB·정책·디자인·화면·개인화·프롬프트·로그·일지와 기존 JSX/CSS/API를 비교했다. 기능 브랜치 커밋/푸시, MR 생성·병합은 사용자 수행.
- 계약: Notion v0.37에5.1.3, PATCH label/DELETE 표, 예시location_version, 버전 구분, 삭제 재시도·연결 범위, D03 단건204 예외, 구현 상태·변경 이력을 갱신하고 저장 재조회. label은 공백 제거 후1~30자, null/빈 값422. 로그인/Origin·CSRF/no-store·소유권404/버전409 유지. 현재 장소 삭제는 동기204, 개인 이동/탈퇴의202 계약은 유지한다.
- 변경 파일: backend/app/places.py, 0005_place_management.py, test_place_management.py 및 기존 핀/마이그레이션 테스트; frontend/src/PlacesCard.jsx/테스트·styles.css; api_contract/place_api/README/backend README/planning/database_schema/migrations/policy_decisions/personalization/ai_prompts/screen_plan/design_guide/logging/TODO/기능 목록/일지. 모델 프롬프트 블록·개인화 공식은 바꾸지 않았다.
- 저장/계산: 일반version은 모든 수정 충돌용, location_version은 위치/출입구/출처 변경용이다. 이름만 바꾸면 지도/AI 호출과 위치 버전 변경이 없다. 기존 장소의 location_version은 기존version으로 초기화한다. 장소 삭제 후 place_creation_keys.place_id=NULL, 사용자/키/본문 해시/만료만24시간 기한까지 남겨 지연 재전송의 재생성을 막는다. 같은 키/본문404·다른 본문409, 다른 키의 명시적 새 저장은 허용한다. 독립10분 검색/확인 자료는 다른 작업을 위해 기존 만료 정책을 유지한다.
- 백엔드: 전체90개 통과(관리10개). 실제 PostgreSQL/ASGI에서 이름 수정200·trim/범위/null/빈 값422·같은 값 유지·지도 호출 없음·일반version 증가/위치 버전 유지, 위치+이름 변경 두 버전 증가·오래된 버전409. 삭제204/빈 본문/X-Request-ID/no-store, 이후 목록 제거·상세/수정/반복 삭제404·동일 생성 키404·다른 본문409·새 키201 확인. 타인 수정/삭제404와 그 자료/키 보존, CSRF403/인증401/잘못된ID404, 동시 삭제204/404·수정/삭제 직렬화·삭제cursor404·다른 장소/독립 자료 보존도 확인. PATCH200/DELETE204 로그의 ID 일치와 라벨/실제ID/원문 비노출 검증.
- 마이그레이션: 임시 스키마에서 기존version4 장소가 location_version4로 보존됨을 확인했다. head 적용/중복 적용·0003 downgrade/re-upgrade·base 왕복 두 차례, 기존 좌표/버전·기대 테이블/head 검증. fixture 확장 후 관련 통합 테스트1개 재통과. public은0005 upgrade/head 확인만 수행했다. downgrade는NULL 삭제 키 표시를 지우며 삭제 장소를 복원하지 않는다.
- 프론트: 전체57개 및 최종 빌드 통과. 이름만PATCH·지도 호출 없음/빈 값 차단, 삭제 확인 취소 시 요청 없음,204 후 첫 페이지 조회, 실패 대상 유지/같은 대상404 재시도, 목록 조회만 실패할 때 삭제 복원 안 함, 처리 중 중복 차단/이탈 취소, 이름 충돌 최신 조회 및 조회 중 세션 만료 자료 제거를 검증했다. 기존 생성/지도/회원/health 흐름도 통과.
- 실제 실행: 이전 개발 백엔드PID15072를 확인하고 최신 코드로 재시작(PID8132),8000 서버를 유지한다. 본 작업의 정확한 합성 이메일/표시명 계정만 사용했다. 회원가입IP 제한을 소모하지 않도록 QA 회원/프로필은 로컬DB fixture로 준비하고, 실제 로그인·공개 강남역 검색·장소POST201 후 브라우저 이름 수정200·새로고침 유지 확인. DB version2/location_version1 확인. 로컬HTTP DELETE204/빈 본문·상세404·같은 생성 키404·목록0, 다른 명시 키의 새 저장201도 확인했다.
- 시각 검증: 데스크톱1440×1000·모바일390×844에서 이름 입력/행동 줄바꿈/삭제 대상 확인·취소/삭제 후 빈 목록 확인. 모바일 documentWidth375<=viewport390, 삭제 취소 Enter 동작 확인. 브라우저에서는 삭제 확인/취소를 확인했고 실제 삭제 전송은 CLI HTTP로 QA 자료에 수행했다. UI 최종 삭제·응답/목록 갱신은 React 테스트로 검증했다. 공통 테마 변경 없이 새 스타일은 장소 카드에 한정했다. 실제 휴대전화·운영 배포는 미검증.
- 정리/잔여: QA 회원1명과 연결 장소/키/검색/확인/세션만 정리, 사용자 자료 유지. 모바일 이미지는 Codex visualizations 폴더에 보관(Git 제외). 실제 루틴 FK NULL/needs_attention, 과거 스냅샷·산정 사본 처리는 F04~06에서 구현한다. 매일 청소/백업/탈퇴는 F11 후속. F03-03 완료, 다음 F03-04 현재 위치 출발·권한 거절 시 지도 선택.
- 배운 개념: 이름 편집 버전과 위치 계산 버전을 나누면 표시 이름 변경 때문에 기존 도보 근거를 불필요하게 무효화하지 않는다. 삭제 시 원래 생성 키까지 지우면 지연 재전송이 삭제 자료를 다시 만들 수 있으므로 제한된 최소 삭제 표시가 필요하다. 삭제 성공과 후속 목록 조회 실패는 구분해 알려야 한다.
- 명세: https://app.notion.com/p/3ebace1670c6806c8199cde33ebfbdfa (v0.37, 저장 재조회/로컬 복사 동기화)

### 2026-10-07 — F03-02 지도 핀·출입구 확인/수정
- 목표/범위: 다음 TODO F03-02. 검색 후보/저장 장소를 지도에서 확인 → 핀 클릭/드래그/방향 버튼으로 수정 → 서버 지역 확인 → 생성/수정 저장. 출입구 설명은 사용자 직접 입력이며 공식 출입구 ID/실내 이동 인증과 구분한다. GPS·라벨 수정/삭제·실제 경로 계산은 다음 단계다.
- Git: 깨끗한 codex/fixed-place-search에서 main fetch, F03-01 병합 main0204e7e 확인 후 codex/place-map-pin 생성. 기능별 커밋/푸시, MR 생성/병합은 사용자 수행.
- 선행 명세/문서: Notion 최신 v0.35·todo/feature_breakdown/place_api/planning/database_schema/관련 JSX·CSS/design_guide/screen_plan 및 이전 일지/프롬프트/개인화/로그 근거를 확인. 공식 Kakao 지도 가이드·클릭/SDK 문서·coord2regioncode API를 확인했다. https://apis.map.kakao.com/web/guide/ 및 https://developers.kakao.com/docs/ko/local/dev-guide 기준. 공급자 저장/전달 조건 추가 확인 생략 지시 유지, 전체 조건 확인 완료로 표시하지 않음.
- 계약: Notion v0.36에5.1.2 상세·지도 설정/확인 API 표·PATCH/생성 필드·DB/구현 상태·변경 이력 갱신 후 저장 재조회. GET /map-config는 공개 JavaScript SDK 키만(로그인/no-store), REST 키 반환 없음. POST /place-location-confirmations는 서울/경기 법정동 확인·600초 본인 결과·10회/분. PATCH는 본인 행 잠금/expected_version, 확인 ID 소유권·만료·좌표 일치. 지원 범위 밖422 UNSUPPORTED_REGION·버전409·타인/만료404. 생성의 신규 선택 필드 null/생략은 기존 멱등 해시 유지.
- 구현 변경: backend/app/places.py·main.py, 0004_place_map_pin.py, test_place_map_pin.py·test_migrations.py; frontend/src/MapPinPicker.jsx·LocationConfirmation.jsx·kakaoMap.js와 테스트3개, PlacesCard.jsx/기존 테스트·api.js·styles.css; .env.example 및 api_contract/place_api/README/backend README/planning/database_schema/migrations/screen_plan/design_guide/logging/TODO/기능 목록/본 일지 동기화.
- 저장: 기존 장소에 entrance_note/location_source/location_address 추가 및 place_location_confirmations 테이블/만료 인덱스. 원래 검색 name/address 보존, 실제 핀 좌표와 법정동 명칭 별도 기록. 좌표/출처/설명 변경이면version+1, 동일값은 유지, 설명null은 제거. 장소 version이 이전 경로/도보 근거의 유효성 기준이며 실제 경로/도보 저장소·무효화 처리는 F04/F05 후속.
- DB/백엔드 검증: 전체80개 통과(새 핀12개). 기존 장소가 있는0003에서0004 upgrade/중복 적용/downgrade0003/re-upgrade·base 왕복 두 차례, 좌표/버전/기본값search/null/null 유지 확인. 개발 public0004 upgrade/head 확인, 기존 회원/장소 보존. 본인 핀 생성·설명/좌표 수정·같은 값 유지·설명 제거·오래된 버전409·동시 수정200/409, 타인 확인/장소404·만료/불명확인404·좌표 변조422·CSRF403·지원지역/바다422·429/Retry-After·청소·기존 멱등 해시 호환 확인.
- 로그/키: 지도 설정/좌표 확인/PATCH200/200/200의 요청ID/로그 일치, 공개 SDK 키·확인ID·좌표/주소/출입구 설명 비노출 확인. REST/AI 키는 서버 전용, JavaScript 키만 도메인 제한용 공개키로 지도 SDK에 전달. 일반 원문/예외/공급자 응답 로그 추가 없음, AI 전달 없음.
- 프론트 검증: 전체49개 통과/빌드 성공. 지도 클릭/드래그/방향 버튼 및 요청 중 조작 차단·정리, SDK 동시 로딩1개/오류 재시도/10초 무응답, 핀 변경·확인 재요청·만료 시 저장 차단, 지원지역 밖/세션 만료/다른 좌표 응답/이탈 취소, PATCH expected_version·409 최신 장소 재조회/재확인 검증. 마지막 지도 초기 비활성 보완 후 관련3개 재검증 및 최종 빌드 통과.
- 실제 실행: 이전 작업에서 시작한8000 백엔드를 최신 코드로 재시작(PID15072)하여 현재 서버를 유지한다. 사용자 계정에 접근하지 않고 본 작업의 정확한 합성 이메일/표시명 계정에서 공개 강남역 검색·Kakao 지도 렌더링·클릭/마커 드래그/5m 방향 버튼·법정동 확인200·핀 생성201·수정200 및 새로고침 유지 확인. 실제 저장 version1→2→3·source=map_pin 확인. 카카오 JS 키와 현재127.0.0.1:5173 도메인 SDK 동작 확인, 운영/다른 도메인 전체 설정 검증은 아님.
- 시각/정리: 데스크톱1440×1000·모바일390×844 지도/수정 폼·방향 버튼 배치·저작권 표시 확인. 모바일 documentWidth375<=viewport390으로 가로 넘침 없음. 지도 핀 이동 후 저장 비활성 및 재확인 후 저장 가능 확인. 기존 홈/루틴과 계정 모달 흐름 회귀 확인, 지도 조작과 현재 위치 권한 요청은 분리. 정확한 QA 회원1명 및 연결 장소/확인/세션을 정리, 사용자 데이터 유지. 모바일 검증 이미지는 Codex visualizations 폴더에 보관, Git 제외. 실제 휴대전화/지도 위치 정확도/실내 출입구·GPS는 미검증.
- 배운 개념: 지도에서 보이는 좌표와 서버가 허용한 저장 좌표는 다르므로 본인·기한이 있는 확인 결과를 연결한다. 공식 지도 SDK 공개키와 서버 REST 비밀키는 용도가 다르다. optimistic version은 오래된 화면이 새 장소 위치를 덮어쓰지 않게 하며, 이후 산정 재사용은 place_id/version을 함께 검사해야 한다.
- 완료/다음: F03-02 체크 완료, F03-03은 목록/상세/위치 수정 부분 완료지만 라벨 수정·삭제/연결 데이터 처리 전까지 미완료 유지. 다음 F03-03. 현재 위치/정확도·매일 확인 결과 청소/F11·F04/F05 산정 재사용 무효화는 남음. 명세 https://app.notion.com/p/3ebace1670c6806c8199cde33ebfbdfa

### 2026-10-07 — F03-01 고정 장소 검색·저장
- 목표: TODO 순서의 F03-01을 작은 기능 단위로 진행. ‘내 설정 → 내 장소’에서 주소/장소 검색 → 후보 선택 → 집·회사 등 이름 저장 → 본인 목록을 제공한다. F03-02~05는 후속이며 F03 전체 완료와 구분한다.
- Git: 깨끗한 작업 폴더에서 origin/main fetch(ac28d5f) 후 codex/fixed-place-search 생성. 기존 회원 오류 안내 main 병합 내용 보존. 이 브랜치에 커밋/푸시하며 MR 생성·병합은 사용자 수행.
- 선행 확인: Notion v0.34 최신 조회, todo/feature_breakdown/planning/personalization/ai_prompts/logging/development_log 및 기존 JSX/CSS/design_guide/screen_plan 확인. 최신 카카오 공식 Local 주소/키워드 API 문서 https://developers.kakao.com/docs/ko/local/dev-guide 확인. 사용자 D02 조건 추가 확인 생략 지시 유지, 공급자 저장/전체 서비스 조건 검증 완료로 표시하지 않는다.
- 계약: Notion v0.35에5.1.1 상세 계약·목록/생성 표·예시·구현 상태·DB 상태·변경 이력 추가/정정 후 저장 재조회. 검색/후보 UUID·사용자 소유권·600초 만료·좌표 대조, 라벨1~30자·검색어1~100자·서울/경기 주소·각 첫10건/최대20건, 429/502/503, 선택 멱등 키24시간 및 목록 limit/cursor 구체화. 미구현 생성 초안에 search_id/candidate_id 필수 및 name/address 응답 추가. entrance_ref는 null만 지원하며 지도 핀/출입구는 후속. 기존 인증/health/루틴 계약 영향 없음.
- 구현 파일: backend/app/places.py·main.py, migrations/versions/0003_saved_places.py, tests/test_places.py·test_migrations.py; frontend/src/PlacesCard.jsx·PlacesCard.test.jsx·App.jsx·App.test.jsx·api.js·styles.css. 관련 api_contract/place_api/planning/database_schema/migrations/screen_plan/design_guide/logging/README/backend README/TODO/기능 목록 동기화.
- DB: saved_places·place_searches·place_creation_keys와 FK/라벨·좌표 CHECK/인덱스 추가. 개발 public에0003 upgrade 및 head 확인. 임시 migration_test 스키마에서 head 적용/중복 적용/전체 downgrade/re-upgrade 두 차례 검증. 기존 회원 데이터 유지. 검색어·공급자 원본 저장 없음; 선택 후보의 이름/주소/좌표를 본인 장소에 저장한다.
- 백엔드 검증: 전체68개 통과(장소12개 포함). 실제 PostgreSQL/ASGI에서 저장201·상세/목록200·재로그인 유지, 타인 검색/장소/cursor404, 변조좌표422·만료404·불명후보404, 인증401·CSRF403·입력422, 분당10회 제한429/Retry-After·공급자실패503, 만료 청소, 페이지 경계, 동시 로그인 세션의 같은 키 재시도에서 장소1개 생성 확인. 동일 키/본문201·다른본문409·후보 만료 후 기존201·멱등 만료 후404 확인.
- 로그 검증: 장소 검색200/생성201/상세200 실행 로그의 request_id와 응답 일치, 실제 ID 대신 /places/{place_id} 템플릿 및 검색어/주소/좌표/라벨/쿠키/키 제외 확인. 입력/공급자 예외 원문 미노출.
- 프론트 검증:35개 통과 및 Vite 빌드 성공. 신규8개로 로그인/빈 결과/실패/만료/검색어 변경 시 선택 해제/멱등 재시도/세션 만료 자료 제거/StrictMode 및 이탈 취소 확인. 기존 health 테스트는 장소 카드와 분리하여 API별 요청 횟수와 결과를 검증한다. 최초 테스트의 쿼리 전달/후보 accessible name 및 완료 요청 취소 기대 오류를 수정하고 다시 통과했다.
- 실제 브라우저: 기존8000 서버가 이전 코드를 실행 중이라 별도8001/5175 검증 서버 사용. 샌드박스 외부 통신 차단에서 장소 검색503/재시도 확인, 통신 허용 후 카카오 공개 강남역 키워드/공개 주소 검색200·후보10/11건, 합성 계정에서 집/회사 이름 저장201·목록200·새로고침 유지 확인. 데스크톱1440×1000 후보 선택·저장, 모바일390×844 주소 검색·선택·저장 및 가로 넘침 없음(documentWidth=390) 확인. 로그아웃/계정 모달 복귀 시 이전 장소 제거 확인. 실제 휴대전화·지도 SDK·GPS·경로 연결은 검증하지 않았다.
- 정리: 본 작업에서 생성한 정확한 합성 이메일/표시명 조건의 QA 회원1명과 연결된 장소/후보/세션만 삭제. 사용자 회원/장소는 변경하지 않았다. 임시 QA Vite 설정/자체 검증 프로세스 정리. 모바일 검증 이미지는 Codex visualizations 폴더에 보관(Git 제외).
- 배운 개념: 검색 후보는 사용자/검색/기한을 가진 임시 자원이고 저장 장소는 지속 자원이다. 요청 타임아웃이 저장 실패를 뜻하지 않으므로 멱등 키와 DB 잠금으로 재시도/동시 세션 중복을 막는다. 브라우저 위치/지도 선택은 주소 후보 선택과 구분해야 한다.
- 완료/남은 일: F03-01 완료, F03-03은 목록/상세만 부분 완료라 체크 유지. 다음 F03-02 출입구/지도 핀 확인·수정 및 변경 버전/산정 무효화. 수정/삭제·현재 위치/시각/정확도/저장 장소 일치, 매일 청소 운영 스케줄(F11), 탈퇴 정리 및 실제 루틴 연결은 미구현. Notion https://app.notion.com/p/3ebace1670c6806c8199cde33ebfbdfa

### 2026-10-07 — F02-01 계정 오류 요청 ID 비노출
- 사용자 요청: 회원가입 실패 시 request 식별자를 사용자에게 표시하지 않는다.
- 최신 main(928af7c, 회원 인증 병합)에서 codex/auth-error-message 생성. AccountForm.jsx의 문의용 ID 행 제거, 입력 조건·중복 오류·재시도·접근성 유지. 계정 폼 전체에 동일 표현 적용.
- 변경 파일: AccountForm.jsx/기존 테스트, api_contract.md/auth_api.md, screen_plan.md/design_guide.md/logging.md, todo.md/feature_breakdown.md, 본 일지.
- 명세: 최신 Notion v0.33 확인 → v0.34 계정 화면 비노출 정책과 변경 이력 저장 → 재조회 확인, 전체 본문 api_contract.md 동기화. API 응답·ApiError 내부 ID·서버 로그는 유지하며 백엔드 계약/코드 변경 없음.
- 검증: 프론트 테스트27개 및 빌드 통과. 기존 입력 오류/중복 오류 검증을 요청 ID 비노출 요구로 갱신. 실제 localhost 가입 폼에서 합성 입력과 차단된 비밀번호로 실패 안내 확인(회원 생성 없음), 데스크톱1440×900·모바일390×844 오류 문구/입력/재시도와 ID 비노출 확인. 임시 뷰포트 원복. 백엔드 변경이 없어 백엔드 테스트 재실행 없음.
- 배운 개념: 개발용 요청 추적 식별자를 API/로그에 보존하는 것과 사용자 화면에 표시하는 것은 별개다. 오류 화면은 해결 가능한 안내를 중심으로 구성한다.
- 완료: F02-01의 오류 표현 수정. 다음: 사용자 브랜치 검토·MR/병합 후 F03-01 고정 장소 검색·저장. 메일 인증/복구 후순위 유지.
- 기준: https://app.notion.com/p/3ebace1670c6806c8199cde33ebfbdfa

### 2026-10-06 — localhost 회원가입 CSRF 차단 수정
- 증상/근거: 사용자 화면의 req_7634d878dc6b49c888608d9ab60a82a7은 POST register403 CSRF_INVALID. 사용자가 앱 주소 http://localhost:5173을 확인했다. 개발 설정은 http://127.0.0.1:5173이며 정확한 Origin 비교가 localhost를 거절했다. 수정 전 같은 쿠키/CSRF 절차의 실제 프록시 POST는127.0.0.1에서204, localhost에서403으로 재현했다.
- 선행 계약/구현: 최신 Notion v0.32 읽고 v0.33에 개발 AUTH_PUBLIC_ORIGIN 동일 HTTP 포트의 localhost/127.0.0.1만 허용하도록 기록. backend/app/auth.py에 설정값에서만 계산한 두 origin 집합 적용, 기본80 정규화. 운영은 기존 HTTPS origin 정확한 일치 유지, CSRF 토큰·쿠키·외부/다른 포트/null 거절 유지. 요청 Host/X-Forwarded-For를 신뢰하거나 wildcard CORS를 추가하지 않았다.
- 검증: 개발 alias 가입/로그인·다른 포트/외부/null 거절, 운영 origin 정확한 검사 테스트2개 추가. 백엔드56개 통과. 확인된 개발 서버 PID5072만 종료/재시작 후 실제 Vite 프록시/쿠키/CSRF POST가 두 주소 모두204 확인. 기존 사용자 계정/가입 제한 버킷을 수정하거나 검증용 신규 가입으로 사용자 호출 제한을 소모하지 않았다. 프론트/UI 코드 변경 없음으로 시각 검증·프론트 테스트 반복 대상 없음.
- 문서/배운 개념: .env.example·backend README·auth_api.md·api_contract.md 동기화, Notion v0.33 저장 재조회. localhost와127.0.0.1은 같은 로컬 서버를 가리켜도 브라우저 origin 문자열이 다르다. 개발 주소의 제한된 호환과 운영 origin 검증을 구분한다. API 경로/응답 변경 없음, 개발 허용 origin 정책만 구체화.
- 완료/다음: codex/member-auth의 회원 기능 후속 수정 완료, 사용자 검토 후 MR/병합 및 기존 다음 F03-01 유지. 기준 https://app.notion.com/p/3ebace1670c6806c8199cde33ebfbdfa

### 2026-10-06 — 회원가입 입력 검증 오류 안내 개선
- 사용자 증상: 회원가입 실패. 서버/프론트 프록시는 정상이며 실제 요청 기록에서 register/login422 VALIDATION_ERROR 확인. 요청 제한은 초과하지 않았다. 사용자 입력 원문이나 비밀번호는 읽거나 기록하지 않았으므로 사용자의 어느 항목이 틀렸는지는 미확인이다. 기존15~128자 비밀번호·이메일 형식·이름 조건은 변경하지 않는다.
- 변경: frontend/src/api.js에서 error.details의 허용 필드3개만 안전한 고정 설명으로 변환, 원문 message/reason/임의 필드/객체는 제외. AccountForm.jsx에 설명 연결과 해당 입력 aria-invalid/aria-describedby. 기존 "입력값을 확인해주세요"만 보여주는 문제 개선, screen_plan.md 갱신. codex/member-auth의 동일 회원 기능 후속 수정이며 새 기능/MR/병합 없음.
- 검증: API 비노출·필드 안내와 계정 폼 오류/접근성 테스트2개 추가, 프론트27개 및 빌드 통과. 실제 브라우저 합성 가입으로 흔한 비밀번호422의 구체적 안내·요청ID를 데스크톱1440×900/모바일390×844에서 확인, 유효 비밀번호로 수정해201 가입/로그인 화면 전환 확인. 합성 회원은 검증 후 정리, 사용자의 계정/입력은 변경하지 않음. 백엔드 코드는 변경하지 않아 전체 백엔드 테스트를 반복하지 않음.
- 명세 영향: 최신 Notion v0.32 확인, 기존422 details.field와 입력 계약 유지, API/계산/로깅 정책 변경 없음으로 Notion 수정 불필요. 기준 https://app.notion.com/p/3ebace1670c6806c8199cde33ebfbdfa
- 배운 개념/잔여: 서버의 입력 거절과 서버 연결 실패는 다르며 안전한 필드별 안내가 있어야 사용자가 바로 고칠 수 있다. 특정 사용자 입력 실패 원인은 새 안내 문구/문의용 ID로 추가 확인한다. 다음 기능 순서는 기존 TODO대로 사용자 MR/병합 후 F03-01 유지.
### 2026-10-06 — 메일 인증 후순위·이메일 중복 기반 회원 인증 구현
- 사용자 변경: 메일 인증은 후순위, 기존 회원 중복만 확인하는 가입/로그인으로 단순화. main(78fcaf7)에서 만든 기능 브랜치를 codex/member-auth로 변경. 이전 Mailpit/Resend 준비용 .env.example·compose·기획/DB/실행 안내 변경을 먼저 HEAD로 복구, auth_preparation.md 제거 및 이번에 만든 Mailpit 컨테이너 정지/제거. 운영 메일 선정·pending7일 정책을 현재 계약에서 철회했으며 외부 메일 발송 없음.
- 명세 선행: 최신 Notion v0.31 확인 후 v0.32로17절 기본 인증 재정의. 가입 즉시active, 이메일 정규화/중복409·201 user_id만·자동 로그인 없음, login/GET me의 이메일 확인 필드 제거. 메일 소유 확인/복구/outbox/token/pending을 후순위로 이동. 이메일 중복 확인은 소유권 인증이 아님. CSRF/서버 세션·프로필 기본값·공통 오류/요청 제한 유지. 저장 재조회 후 api_contract.md·auth_api.md 및 관련 문서 동기화.
- 구현 파일: backend/app/auth.py·main.py, 0002_member_auth 마이그레이션, requirements 및 인증/응답/마이그레이션 테스트. users/auth_credentials/user_profiles/auth_sessions/auth_rate_limit_buckets5개 적용. UNIQUE 정규 이메일로 동시 가입 중복 방지·트랜잭션 정리, Argon2id19MiB/time2/p1, 서버 난수 세션/CSRF 해시 저장·HttpOnly/SameSite 쿠키, Origin+CSRF 검사, 로그인ID 교체·절대7일/미사용24시간, PostgreSQL HMAC 버킷/429. 기존 계정 비밀번호 덮어쓰기 없음.
- 화면: AccountForm.jsx·테스트, App.jsx 계정 모달/API 실제 연결 및 api.js 오류 문구·기존 CSS 토큰의 auth-tabs만 추가. 회원 가입 후 로그인 전환·중복/입력/연결 실패/요청ID·로그인 회원/첫 여유·로그아웃·요청 중 비활성/이탈 취소. 이동 데모는 그대로이며 회원별 장소/루틴 저장과 연결하지 않음. design_guide.md·screen_plan.md 갱신.
- 실제 검증: 백엔드 전체54개 통과(인증13개: 동시/대소문자 중복·로그인/없는 계정 동일401·CSRF/Origin·정상/만료/이전 세션·CSRF 재발급·다른 회원 me·공백 비밀번호·프로필·가입/로그인 제한·운영 쿠키/설정·DB 오류; 마이그레이션 upgrade 재실행/downgrade 왕복 포함). 프론트25개·build·pip check·git diff --check 통과. 임시 스키마 및 브라우저 테스트용 합성 회원 정리, 개발 DB0002_member_auth 적용. DB 연결은 이번 실제 실행에서 정상 확인.
- 실제 UI: Vite 프록시/uvicorn을 확인된 프로젝트 PID만 재시작. 데스크톱1440×900·모바일390×844 로그인 폼/성공·중복409/요청ID·모바일 로그아웃 확인, 기존 초록/미색/카드·줄바꿈/입력·닫기/반응형 유지. 실제 화면에서 StrictMode 첫 요청 취소로 로딩 고착, DB datetime의 쿠키 GMT 변환 실패를 발견해 수정·각 회귀 테스트 추가. 기존 Vite 실행의 잘못된 root 인자를 직접 Node 실행으로 수정. 개인 주소/메일/운영 자격증명은 테스트에 쓰지 않음.
- 환경/보안: 기존 .env 값은 보존하고 없던 독립 AUTH_RATE_LIMIT_SECRET만 로컬 난수로 추가(값 출력 없음), .env.example에는 빈 자리·origin만 기록. Git 파일과 실제 KEY/PASSWORD/BASE_URL/SECRET 대조 일치0건, .env 추적 제외. 메일 캡처/SMTP 설정은 최종 변경에 없음. AGENTS.md에 사용자 브랜치/MR 작업 흐름 기록.
- 배운 개념: 가입 중복은 DB UNIQUE가 최종 보장하며 UI 검사만으로 동시 요청을 막지 못한다. 메일 주소 중복 검사와 이메일 소유 확인은 다르다. 개발 StrictMode의 정리/재실행과 쿠키 GMT 시각 변환은 실제 브라우저 경로로도 확인해야 한다.
- 완료/잔여: F02-01/02/05만 완료. 메일 인증/복구·재인증·탈퇴·업무 API 전체 소유권/WS·전체 유출 비밀번호 목록은 후속. 개발 스키마 회원 기능 검증이며 운영 배포/실제 메일 소유 검증 완료 아님. 사용자가 브랜치 검토 후 MR/병합, 이후 F03-01. 기준 https://app.notion.com/p/3ebace1670c6806c8199cde33ebfbdfa

### 2026-10-06 — F01 단계 삭제 문서 커밋 준비
- 사용자 요청: 사례 선정 및 데이터 공급자 검증 단계 삭제에 따른 문서6개 변경을 커밋하고 origin/init에 푸시.
- 검증: 최신 Notion v0.30과 api_contract.md 전체 본문 일치, TODO/기능 목록의 F01 활성 항목 제거 및 다음 F02-00 확인, git diff --check 통과. 실제 환경 키/비밀번호/AI URL의 변경 파일 일치0건, .env 제외.
- 명세 영향: 기존 단계 삭제 반영 외 추가 계약 변경 없음. 문서만 변경되어 실행 테스트 재수행 대상 없음. 푸시 결과는 실행 후 최종 보고한다. 기준 https://app.notion.com/p/3ebace1670c6806c8199cde33ebfbdfa

### 2026-10-06 — 사용자 요청으로 F01 데이터 공급자 검증 단계 삭제
- 변경: todo.md·feature_breakdown.md의 F01 전체 단계(F01-02~06)를 삭제하고 다음 작업을 F02-00 회원가입·로그인 구현 준비로 변경. provider_plan.md의 별도 체크리스트 삭제 및 진행 결정, policy_decisions.md의 다음 작업을 동기화했다. 공급자 응답 변환/오류 처리는 필요한 기능 연동에 포함한다.
- 명세: 최신 Notion v0.29 확인 후 v0.30에 단계 삭제·다음 작업·관련 기능에서의 응답 처리 반영, API 경로/입력/응답/계산 정책 변경 없음. 저장 재조회 후 api_contract.md 동기화. 기준 https://app.notion.com/p/3ebace1670c6806c8199cde33ebfbdfa
- 검증/배운 개념: TODO와 기능 목록의 F01 활성 항목 제거·다음 F02-00·명세 저장 내용을 대조. 단계 삭제는 검증 성공이나 기능 완료를 뜻하지 않으며 기존 연결 이력은 보존한다. 코드/UI 변경·실행 테스트 없음.

### 2026-10-06 — 사용자 요청으로 F01-01 사례 선정 작업 삭제
- 변경: todo.md와 feature_breakdown.md에서 F01-01 항목 삭제, 다음 작업을 F01-02로 갱신. provider_plan.md·policy_decisions.md의 후속 작업 참조도 갱신했다. 완료 처리나 기존 검증 이력 삭제가 아니라 작업 목록에서 제거한 것이다.
- 명세: 최신 Notion v0.28 확인 후 v0.29에 사용자 요청·작업 삭제·다음 순서 기록. API 경로/입력/응답·계산 정책 변경 없음. api_contract.md를 저장된 원문과 동기화한다. 기준 https://app.notion.com/p/3ebace1670c6806c8199cde33ebfbdfa
- 검증/배운 개념: 문서 내 활성 작업 항목과 후속 참조를 대조한다. 삭제한 작업을 완료로 표시하지 않는다. 코드/UI 변경과 실행 테스트는 없으며 다음은 F01-02다.

### 2026-10-06 — 누적 변경 커밋/푸시 준비 검증
- 사용자 요청: 현재까지의 변경 전체 커밋 및 origin/init 푸시. 공통 API 호출/오류/요청 ID·최소 JSON 로그 구현, D03~D05 정책 및 출발/조회 정책 문서 동기화를 포함한다.
- 실제 검증: unittest discover 백엔드 전체41개, 프론트20개 및 프로덕션 빌드 통과. git diff --check 통과. 실제 .env의 키/비밀번호/AI URL 값과 Git 대상 파일 대조에서 일치0건, .env 추적 제외 확인.
- 명세: 최신 Notion v0.28 재조회와 api_contract.md 전체 본문 대조 일치. 이번 작업은 커밋 준비이며 API 계약 추가 변경 없음. 기준 https://app.notion.com/p/3ebace1670c6806c8199cde33ebfbdfa
- 배운 개념/잔여: 테스트 성공과 배포·DB/외부 공급자 연결 성공은 별개다. 이번에는 DB/외부 API를 호출하지 않았으며 기존 미검증 상태와 다음 F01-01을 유지한다. 푸시 결과는 실행 후 최종 보고한다.

### 2026-10-06 — F00-04 최소 JSON 요청 완료/오류 로그 완료
- 목표/명세 확인: 최신 Notion v0.27·TODO·logging.md와 기존 API/응답 테스트·환경 예시·실행 안내 확인. 요청 ID로 성공/오류를 대조하며 개인정보/키/원문을 남기지 않는 최소 로그만 구현, 업무 API/새 UI/외부 수집기 추가 없음. Notion v0.28에 로그 필드/수준·경로/시간/비노출·보관 적용 범위를 선행 기록.
- 구현: backend/app/request_logging.py에 전용 timeisnow.requests logger·JSONFormatter·이벤트 필터, stdout1줄·UTC·LOG_LEVEL INFO 기본/INFO·WARNING·ERROR. 프레임워크 메시지/args/traceback/무관한 extra를 출력하지 않음. main.py에서 단조 시계 처리시간·registered route.path 템플릿/unmatched·status/error_code·서버 request_id 기록. 예상 밖 예외는 종류만 ERROR 실패+같은 ID INFO 완료, 완료는 요청당1회. 404/405/422 사용자 입력 오류는 서버 예외로 기록하지 않음. 시간은 응답 생성까지이며 전송 완료시간 아님.
- 환경/안내: .env.example에 누락된 카카오/AI 키·승인 URL 자리·LOG_LEVEL 추가, 공급자 키는 빈 값/AI URL은 .example 예시. 실제 .env 변경/키 출력 없음. backend/README.md에 기존 .env 덮어쓰기 방지·실행/LOG_LEVEL/ID 대조·테스트 명령 정리, Uvicorn --no-access-log 유지. stdout만 제공하며 로그14일 수집/회전은 배포F11에서 적용, 미구현.
- 실제 테스트: test_request_logging.py7개 통과(완료1회/응답ID 일치·경로템플릿·쿼리/헤더/본문/응답/예외/extra 비노출·404/422·예상 밖500·handler 중복/DEBUG 방지). 기존 응답계약6개·진단21개·최신성6개 합계 백엔드40개 통과, 프론트20개 회귀 통과. DB/외부 API 호출 없음, DB 테스트는 재실행하지 않음. 프론트 코드/UI 변경 없어서 시각 검증/빌드 재실행 불필요.
- 실서버: 이전 작업의 확인된 개발 PID14368만 재시작, 정상8000 서버에서200/404/405 호출. 각각응답 헤더/meta/실제 stdout ID 일치·호출당 완료1회 및 임의 클라이언트ID 무시 확인. 합성 privacy-sentinel을 경로/쿼리/Authorization/Cookie/본문에 넣어도stdout 포함0건. expected error에는오류코드,404route=unmatched 확인. 터미널 화면의 자동 줄바꿈은 실제 JSON 레코드와 구분. 환경 예시 필수 설정 존재/실제 API 키값 매치0건 확인.
- 변경 파일: backend/app/request_logging.py·main.py·tests/test_request_logging.py·test_api_contract.py·.env.example·backend/README.md·README.md·logging.md·planning.md·api_contract.md·todo.md·feature_breakdown.md·policy_decisions.md·development_log.md. Notion v0.28 구현 상태/검증 결과 재조회·로컬 대조. API 성공/오류/헤더/ID 형식 변경 없음, 실행 로그 필드/정책 구현.
- 최종 확인: Notion v0.28 재조회/로컬 본문 일치, TODO/기능 목록 F00-04 완료·F01-01 미완료 상태 일치, py_compile·git diff --check 통과(기존 줄바꿈 경고만). .env는 Git 변경에 포함되지 않음.
- 완료/다음: F00-04만 기능 완료, 업무/AI/교통 로그·배포 수집/회전 미완료. 다음 F01-01 대표 출발 안내 사례/검증 목록을 기획 범위 안에서 정리하며 D02 실제 미검증/DB 연결 문제를 완료로 바꾸지 않음. 이번 변경 커밋/푸시 없음.
- 배운 개념: 로그는 허용된 필드만 처음부터 구성해야 한다. HTTP 4xx와 예상 밖 서버 오류를 구분하고 응답·프론트·로그의 서버 ID를 맞춰야 실패 요청을 찾을 수 있다.

### 2026-10-06 — F00-03 공통 API 호출/오류/요청 ID 연결 완료
- 목표/명세 확인: 최신 Notion v0.26·TODO·기획/로깅·design_guide.md·screen_plan.md와 기존 JSX/CSS 확인. 직접 fetch하던 health 카드에 공통 호출·로딩/실패·서버 request_id 연결. 업무 API/인증/교통·AI 기능을 추가하지 않음. FastAPI 공식 오류 처리 문서 https://fastapi.tiangolo.com/tutorial/handling-errors/ 참고.
- 계약 선행: Notion v0.27에 공통 클라이언트·404/405/422/500 형식/405 METHOD_NOT_ALLOWED·서버 ID 생성·민감 입력 비반사 기록 후 구현. 첫 Notion 편집은422 행 중복 매치로 거절됐으므로 고유 공통 오류 행 전체로 좁혀 성공, 변경 후 재조회. health 성공 객체/경로 유지, 다른 HTTP 오류는 기존 프레임워크 detail에서 error/meta로 맞춤.
- 구현: frontend/src/api.js 공통 JSON 호출/응답 검증·same-origin 쿠키·헤더 전달·외부 경로 금지·리다이렉트 금지·기본10초 시간초과·취소·202 접수/204 본문 없음 구분·수동 재시도. 실패 메시지는 안전한 정적 문구, 원문/URL/본문 로그 없음. 헤더/본문 요청 ID 불일치·깨진 JSON·잘못된 health 데이터는 정상 연결로 표시하지 않음.
- 화면: App.jsx 서버 연결 카드 로딩/비활성·성공·실패/재시도·지원용 요청 ID, 화면 이탈 요청 취소·오래된 상태 제외. 기존 클래스/색/카드 유지, styles.css request-id 줄바꿈만 추가. 프론트 개발 성공/실패 이벤트에 안전한 요청 ID만 연결.
- 서버: backend/app/main.py 미들웨어에서 서버 request_id 생성, 클라이언트 임의 ID 무시. health/meta/헤더 일치.404/405/422 공통 handler·예상 밖500의 정적 오류, 검증 입력값/예외 원문 비반사. Allow 헤더 보존. 요청 완료/예상 밖 오류 구조화 로그는 아직 F00-04 미구현.
- 실제 테스트: frontend App11개/API9개 합계20개 통과·프로덕션 빌드 통과. backend/tests/test_api_contract.py6개(ASGI 실제 응답/임의 ID·요청별 ID·404/405/422/500/입력 비반사) 통과, 기존 진단/매핑21개·최신성6개 합계27개 회귀 통과. DB 테스트는 이번 범위에서 재실행하지 않음, 기존 연결시간초과 미해결 유지.
- 실행/시각 검증: 실제 로컬 health200·404·405(errorcode/Allow)에서 헤더/본문ID 일치 확인. 데스크톱 및390×844 실제 브라우저 성공/로딩/QA500실패·재시도/ID 교체/줄바꿈 확인. 임시 QA 서버는 응답2초 지연/의도적500만 주었고 프로덕션 코드에 QA 경로/스위치 없음. QA 플래그/파일 정리, 검증된 QA PID만 종료 후 정상 backend8000/frontend5173 재시작/최종 연결 성공 확인. Windows QA 종료가 Ctrl+C/Stop-Process로 끝나지 않아 확인된 PID에만 taskkill 적용. 브라우저 뷰포트 원복.
- 변경 문서: api_contract.md·planning.md·screen_plan.md·design_guide.md·logging.md·README.md·backend/README.md·todo.md·feature_breakdown.md·policy_decisions.md·development_log.md. Notion v0.27 구현 상태/검증 결과 재조회·로컬 본문 대조. F00-03만 완료, F00-04는 미완료.
- 배운 개념/남은 문제: 서버 요청 ID는 네트워크 요청을 묶는 식별자이고 네트워크 실패에 가짜 ID를 만들지 않는다. common JSON/HTTP 성공만으로 업무 데이터 정상이라고 판단하지 않는다. 다음 F00-04에서 같은 ID의 요청 완료/실패 로그를 추가하며 기능/API 데이터는 그대로 미구현이다.

### 2026-10-06 — 위임에 따른 D03·D04·D05 정책 확정
- 사용자 요청: 남은 결정을 에이전트가 기존 기획 기준으로 진행. 최신 Notion v0.25·todo·planning·약속 API/계획·개인화·로깅·DB/자연어 문서를 확인해 수치/정책을 확정했다. 환승·AI 도보 산정·저장 재사용·수동 확인 요구와 공급자 조건 추가 확인 생략 가정 유지, 길찾기 제품으로 범위 확대 없음.
- D03: 도보30일·활성화면60초 조회·수신/검증 생성시각120초 중 이른 만료(경계 포함)·장소검색10분/여정검색5분·작업/내보내기24시간/다운로드10분·멱등24시간·자연어컨텍스트10분. 작업 상태는2→5→10→최대30초/Retry-After 우선이며 교통 조회와 구분. 기본 여유 첫탑승300초/환승120초·각0~1800초, 최대환승2회·목록20/100. 생성시각 unknown/미래/오류를 최신으로 만들지 않음.
- 보관/삭제: 로그14일·개인 이동/품질90일·장소/루틴/현재프로필 삭제까지 유지. 매일 기간 청소·만료 접근 즉시 차단·삭제202 작업24시간 목표/실패 재시도·백업 최대7일 및 복원 삭제 재적용. 120초는1분 조회의 한 차례 지연을 허용하는 앱 정책이며 공급자 정확도 보장 아님. 현존 데이터를 삭제하거나 실행 환경을 설정한 것은 아님.
- D04: 첫 출시 반응형 모바일 웹 활성화면 출발 안내 포함. 백그라운드 푸시/예약 알림과 자동 출발/GPS 감지는 후속, 새 푸시 API/알림 권한/UI 도입 없음.
- D05: 약속 최대2명/혼자사용·초대24시간1회·추천3개5분·제목100자/채팅1000자·기존 속도제한 확정. 공유 기본꺼짐·종결/취소/철회/목표6시간후 종료·ETA최대120초. draft미사용30일 삭제·confirmed목표6시간후 자동종결(참석판정아님)·공동30일·재전송24시간·본인약속탈퇴와 계정탈퇴 메시지 처리/주최자탈퇴/개인trip 연결해제 구분. 기존 API 객체/경로 유지, 검증/만료/종결 동작 계약 확정.
- 변경 파일: policy_decisions.md 신규, api_contract.md·planning.md·meeting_api.md·meeting_plan.md·personalization.md·logging.md·database_schema.md·natural_language_schedule.md·ai_prompts.md·provider_plan.md·public_arrivals_plan.md·provider_conditions.md·feature_breakdown.md·todo.md·development_log.md. Notion v0.26에 공통 값·예시/정책·약속·20절/변경 이력 동기화, 재조회 저장 확인. 자동 이스케이프(~)는 의미 동일함을 비교하고 로컬 원문에 반영.
- 검증: 코드/실제API/UI/청소 변경 없음·실행 테스트 대상 없음. Notion/로컬 전체 본문 일치와 기존 API 경로 언급 목록 동일 확인. 문서 일관성 검사 첫 시도는 문구의 정확한 문자열 가정 때문에 실패해 실제 문서 표현으로 수정, 이후 결정 체크·120초 만료·백그라운드 후속·기능 미구현4개 확인 통과. git diff --check 통과(줄바꿈 경고만). 결정 완료 D03·D04·D05와 기능 미구현 체크를 구분, D02 실제 미검증/DB 연결시간초과를 숨기지 않음.
- 다음: F00-03 공통 API 클라이언트·로딩/실패/request_id 연결 후 F00-04 요청 로그. 실제 구현에서 경계·만료·권한/동시 수락·삭제/재연결 회귀를 검증한다. 이번 문서 변경은 커밋/푸시하지 않았다.
- 배운 개념: 경로 구조/실시간 예측/도보 산정은 서로 다른 유효기간을 가진다. 문서 정책 확정과 기능 실행·제3자 보장은 별개이며 종료 상태를 실제 참석 증거로 사용하지 않는다.

### 2026-10-06 — 누적 변경 커밋/푸시 준비 검증
- 사용자 요청: 현재까지 저장된 레포 변경 전체를 커밋 메시지와 함께 커밋/푸시. 현재 init 브랜치·기존 origin 사용, 새 기능/범위 추가 없음.
- 비밀 검증: 추적/추가 후보 63개 파일에서 현재 .env의 실제 API 키와 전용 AI baseURL 값 대조, 노출 0건. .env·backend/.venv·frontend/node_modules·빌드 결과는 Git 제외 확인. .env.example은 예시 파일로만 포함.
- 실제 검증: frontend npm test 7개 통과, npm run build 통과. backend 진단/매핑 테스트 21개·최신성 6개 합계 27개 통과. health 함수 HTTP 200·data.status·request_id 헤더/본문 일치 검사 통과(HTTP 서버 실호출 아님).
- DB 검증 제한: 마이그레이션 통합 테스트 1개는 오류로 실패. 별도 연결 검사 ConnectionTimeout 확인. 현재 셸 Docker는 사용자 설정 접근 제한 및 compose 명령 사용 불가로 DB 실행 상태 확인 못함. 기존 성공 이력과 이번 실패를 구분하며 이번 테스트를 통과로 표시하지 않음. DB 환경 복구/재검증은 별도 잔여 작업.
- 명세: 게시 전 최신 Notion v0.25 재조회, api_contract.md 전체 본문 일치 확인. 이번 Git 저장 자체는 API 계약 변경 없음. 출발/조회 정책은 문서 확정이며 핵심 서비스/폴링/차량 전환 구현 완료를 주장하지 않음.
- 체크: git diff --check 통과(기존 줄바꿈 경고만). 커밋 범위는 React 프로토타입/health API·DB 기반·공급자 진단 도구·기획/설계/정책/진행 문서. 조건 추가 확인 생략 및 D03 진행 결정 유지.

### 2026-10-06 — 출발 확인 지연 시 다음 차량 안내 정책
- 사용자 요구: 앞선 ‘예상 이동시간 절반’은 정보 만료/차량 도착까지 남은 시간의 기준이 아니라, 사용자가 아직 출발하지 않았으면 다음 차량으로 변경하는 규칙이라고 정정. 출발 확인은 사용자 수동 입력이다.
- 정책 정리: 안내한 권장 출발 시각 s를 기준으로 now-s > W/2·유효한 departed 확인 없음이면 다음 이용 가능한 후보로 변경. W는 정류소/승강장 접근 시간(전체 교통 이동시간/여유 제외), 기준 시점을 출발 안내 시각으로 해석해 사용자에게 예시 설명. 12:00 안내·W=600초이면 12:05를 넘은 경우, 동일 경계는 초과 아님. 기존 60초 정기 평가 유지. 출발 확인 후 적용하지 않음.
- 동작/계약 영향: 다음 차량에도 W+B·환승/목표 도착·최신성을 검사하고 출발/여유/최종 도착 재계산. 후보 부족/만료는 insufficient_data, 시각 추측 없음. 기존 manual departed 이벤트와 필드 재사용·새 API/필드 없음. 미확인을 실제 미출발/놓침 관측으로 기록하거나 보행 학습에 넣지 않음. 기존 환승 범위 유지, AI 도보 재호출 불필요.
- 확인/변경: 최신 Notion v0.24·TODO·planning/personalization/프롬프트/로깅 확인 후 Notion v0.25 계산 정책/변경 이력과 로컬 api_contract.md·planning.md·personalization.md·ai_prompts.md·logging.md·todo.md·feature_breakdown.md·development_log.md 반영. 코드/UI 구현 없이 정책 설계만 변경, 실행 테스트 대상 없음. F07-06 및 D03 미완료 유지.
- 문서 검증: Notion 계산식 자동 이스케이프를 코드 표기로 정리하고 재조회·로컬 본문 일치 확인. git diff --check 통과(기존 줄바꿈 경고만 표시).
- 다음: 정보 만료·도보 재사용·로그/품질 보관·설정 상한 등 D03 잔여 결정. 실제 구현 때 임계값 경계·수동 출발 수신/정정·다음 후보 없음·환승/목표 도착 실패를 검증할 예정이며 아직 실행하지 않음.

### 2026-10-06 — 도착정보 조회 주기 1분 확정
- 사용자 결정: 잦은 조회를 줄이기 위해 활성 화면 실시간 도착정보 정기 조회 주기를 60초(1분)로 변경. 기존 기획의 30초 제안을 대체한다. 첫 진입/탭 복귀 정책은 기존 기획을 유지한다.
- 명세 확인: 최신 Notion v0.23·TODO와 planning.md의 실시간 정책 확인. 정보 만료 60초는 별도 미확정 제안, 조회 주기와 동일한 정책으로 확정하지 않음. 다른 기능의 WS 티켓 30초/재연결 정책은 이번 범위 밖이다.
- 변경 파일: planning.md·provider_plan.md·public_arrivals_plan.md·api_contract.md·todo.md·feature_breakdown.md·development_log.md. Notion v0.24에 사용자 결정/변경 이유·미구현 상태 반영. API 경로/입력/응답 변경 없음, 향후 정기 조회 호출 빈도 정책만 변경.
- 구현/검증: 코드에서 해당 30초 도착정보 폴링 구현을 발견하지 못함. 서비스 폴링 기능은 아직 미구현이며 문서 결정만 반영, 실행 테스트 대상 없음. D03은 다른 상한/만료/보관 결정이 남아 미완료 유지.

### 2026-10-06 — 사용자 결정으로 조건 추가 확인 생략/D03 전환
- 사용자 지시: 미확인 공급자 조건을 없다고 가정하고 다음 단계로 진행. 추가 문의/계약 조사 선행을 요구하지 않으며 기획된 환승·AI 도보·저장 재사용 범위를 유지한다.
- 상태 기록: 공급자 실제 허락/데이터 보관·학습 조건을 확인했다고 표시하지 않음. D02 미검증 체크 유지, 현재 작업을 D03으로 이동. 기존 제안은 도보 재사용 30일, 활성 화면 조회 30초, 정보 만료 60초, 실행 로그 14일, 품질 이력 90일이며 아직 확정 아님.
- 변경 파일: todo.md·provider_conditions.md·api_contract.md·development_log.md. Notion v0.23의 조건 조사에 사용자 후속 가정/전환만 추가. 서비스 API/계산 정책 수치 변경 없음. 구현/실호출/배포/외부 문의 없음.

### 2026-10-06 — 공급자 조건 조사와 엘리스 사용자 화면 요금 확인
- 목표/범위: 사용자 범위 준수 지시에 따라 전체 길찾기 검증 확대를 중단하고 D02 저장/재사용/AI 전달/비용 및 공공 도착정보 조건 조사. 환승·AI 도보 산정·저장 재사용·수동 탑승 확인은 유지, 첫 탑승만으로 기획 축소하지 않음. 최신 Notion v0.22·TODO·provider_plan·관련 기획 확인.
- 공식 조사: 카카오 약관 제11조 제3항·운영 정책·쿼터, 2026-08-18 데브톡 API 응답 저장/반복 사용 불허 답변 확인. 파생 도보 시간/개인화/품질 이력 저장·AI 추론 전달의 개별 허용은 답변/승낙 미확인. 무료 월 300만·도보/대중교통 각 일 1천·키워드 일 10만과 첫 활성화 앱 무료 대상·추가 쿼터 단가 확인. 실제 앱 적용은 미확인.
- 공공 조건: 서울 버스/지하철 출처표시, 경기 버스 제한 없음, 두 버스 무료·개발 신청 트래픽 1,000 확인. 서울 버스 mkTm=제공시각, 지하철 recptnDt=생성시각/지연 반영·서울시 밖 미제공 안내 확인. 원천 시간대/보장 지연·만료·실제 계정 쿼터 미확정 유지.
- AI 발급처: 사용자 AI Campus 상세 URL 제공으로 엘리스 확인. 웹 도구 접근 불가, 브라우저에서 로그인 필요 확인. 최신 법적 약관 링크 웹 접근 불가·추가 브라우저 읽기는 사용자 중단으로 미완료. 일반 공개 개인정보 PDF는 API 무보관/무학습 보장 근거로 사용하지 않음.
- 화면 확인: 사용자 첨부 모델 정보 화면 제공자 OpenAI, Serverless, 모델 ID openai/gpt-5.6-luna, 100만 토큰 입력 304원/캐시 입력 30원/출력 1,827원·API Rate Limit 무제한. 기존 성공 요청 gpt-5.6-luna 설정 유지. 화면 단가와 실제 청구·부가세·크레딧·예산/데이터 계약 구분. 입력 1,000+출력 500 일반 토큰 단순 산술 약 1.22원, 실제 측정 아님.
- 변경 파일: provider_conditions.md 신규(출처/조건표/미해결 영향/미발송 문의), provider_plan.md·planning.md·api_contract.md·todo.md·feature_breakdown.md·development_log.md 갱신. Notion v0.23에 범위 유지와 부분 확인 반영. 앱 API 경로/필드/계산 계약 변경 없음.
- 검증/제한: 이번 작업은 공개 문서와 사용자 화면 읽기, 키 포함 API 호출/개인 위치 전송/유료 설정/외부 문의 발송/코드 변경 없음. 실행 테스트 대상 없음. D02 완료 체크 안 함. 파생 저장/전달 승인 및 엘리스 데이터 계약·실제 예산 확인 후 D03→D04→D05 순서 유지.
- 최종 문서 검증: Notion v0.23 재조회 후 자동 링크로 바뀐 로컬 파일명을 코드 표기로 바로잡고 api_contract.md 본문 일치 확인. git diff --check 통과(기존 줄바꿈 경고만 표시).
- 배운 개념: 공급자 원본 이용허락과 앱 파생 결과 보관은 분리 확인해야 한다. API 연결·모델 화면 가격·실제 청구·무학습 계약은 서로 다른 검증 항목이다.

### 2026-10-06 — 서울 WGS84/경유노선 확인과 하차 후보 불일치
- 목표: 최신 Notion v0.21·todo.md·로컬 기획과 공식 서울 개발 가이드 확인 후 좌표/경유노선 대조. 공식 getStationByName/getStationByPos에서 WGS84(tmX/tmY·gpsX/gpsY)와 GRS80(posX/posY)을 구분, getRouteByStation 입력 arsId 확인.
- 구현: backend/check_seoul_mapping.py 신규, 고정 공식 호스트/리다이렉트 금지·응답 상한·명시적 HTTP·원문 저장/AI 전달 없음. 공개 카카오 강남역→서울역 첫 직행 후보 N75(심야). 이름 검색 진단 실패 2회 중 두 번째에서 공급자 코드 4 확인. 처음 오류코드가 누락돼 안전한 코드 요약을 추가했고, 이후 좌표 기반 검색으로 전환했다. 이름 별칭 임의 변환 없음.
- 실제 실행: 좌표 기반 첫 진단은 주변 8개/6개·이름+좌표 후보 1개/0개, 하차 미확정. 독립 검증 가능한 승차 경유노선 단계 추가 후 재실행에서 동일 후보 개수 및 arsId 경유노선 41건 정상 응답. 최종 endpoint_unresolved/종료 1은 하차 후보 미확정이며 전체 인증 실패를 뜻하지 않음. 단일 공개 경로·100m 실험용 허용오차, 운영 정책 미확정.
- 검증: backend/tests/test_seoul_mapping_probe.py 3개 통과, 경계 이름/승강장 차이·원거리 동명·무효 arsId/NaN·중복 식별자를 검사. 정차순서/방향/전체 노선 매핑·최신성 테스트 아님.
- 변경 문서: api_contract.md·provider_plan.md·public_arrivals_plan.md·planning.md·todo.md·feature_breakdown.md·development_log.md. Notion v0.22에 동일 미완료 범위와 원인 조사 기록. 앱 API 계약/계산 정책/클라이언트 영향 없음. 키·개인 주소·원문 출력/저장 없음.
- 최종 확인: Notion v0.22 재조회와 기대 본문/로컬 api_contract.md 일치. py_compile·git diff --check 통과(기존 파일 줄바꿈 경고만 표시).
- 남은 문제/다음: 공급자 정류소/승강장 이름 및 심야 노선 표기 차이를 공식 데이터로 대조하고 정차순서·방향 확인. 임의 후보 확정 없이 D02-03h 미완료 유지.
- 배운 개념: 좌표가 가까워도 같은 승강장/운행 방향을 증명하지 못하며, 정류소 ID와 고유번호는 API별로 정확히 구분해야 한다.

### 2026-10-06 — 서울 정류소 개인 키 최소 조회 성공
- 목표/명세 확인: 최신 Notion v0.20·todo.md·planning.md·public_arrivals_plan.md와 서울 정류소 공식 포털 요청주소/stSrch/응답 필드를 확인. 전체 매핑/좌표계/최신성을 연결 성공과 구분.
- 구현: backend/check_seoul_baseinfo.py 추가. 고정 공식 호스트·NoRedirect·HTTPS 기본·명시적 HTTP 옵션·응답 크기 제한·비밀 없는 요약. backend/tests/test_seoul_baseinfo_probe.py 추가. 키/URL/원문 출력·저장/AI 전달 없음.
- 실제 조회: 기존 사용자 HTTP 전송 승인 범위에서 ws.bus.go.kr 정류소 명칭 검색 공식 예시 경성중고사거리 1회. HTTP 200/headerCd=0·2건·stId/stNm/arsId 존재·tmX/tmY 유한한 지리 좌표 범위 확인. 좌표계 확정 또는 카카오 ID 매핑 완료 아님.
- 검증: unittest 4개 통과(오류와 정상 빈 결과 구분, 누락 식별 필드, 비유한/잘못된 좌표, 성공과 운영 매핑 구분). 실제 서비스 API/UI 변경 없음.
- 문서: Notion v0.21에 경기 정류소 403 해소와 서울 정류소 후속 결과 반영·재조회 기대 본문 일치 확인. api_contract.md·provider_plan.md·planning.md·public_arrivals_plan.md·TODO/기능 목록 갱신. 앱 API 경로/필드/계산 정책 변경 및 기존 클라이언트 영향 없음.
- 다음/남은 문제: 서울 정류소 좌표계와 경유노선·카카오 대조, 추가 노선/반대 방향·회차 및 원천 생성시각/최신성 검증. D02-03h/전체 공급자 검증 미완료 유지. 운영 HTTP 정책 미정.
- 배운 개념: 숫자가 경도/위도 범위 안에 있어도 좌표계가 일치한다고 증명된 것은 아니다.

### 2026-10-06 — 경기 정류소 승인 화면 및 403 해소 재확인
- 사용자 화면에 경기 정류소·노선, 서울 정류소, 경기/서울 버스 도착정보 5개 서비스 승인 표시 확인. 화면의 만료예정일은 2028-10-06이며 AI 키 사용 기한과 별개다.
- 실제 검증: 기존 backend/check_public_baseinfo.py를 저장된 포털 키로 공식 HTTPS에서 실행. 정류소 검색 2건, 정류소 경유노선 4건, 노선 정차순서 83건 모두 HTTP 200/resultCode=0. 종료 코드 0. 이전 정류소 403 해소 확인. 승인 반영 지연이 원인이었는지는 확정하지 않음.
- 변경 파일: todo.md·feature_breakdown.md·development_log.md. 기존 진단 재실행 및 진행 상태 정정만 수행, 구현/API 계약·정책 변경 없음. Notion은 이번 진단에서 수정하지 않음. 키와 원문 응답 출력/저장 없음.
- 남은 일: 서울 정류소 실조회, 추가 노선/회차/방향 매핑과 원천 생성시각·최신성 검증. D02-03h는 미완료 유지.
- 배운 개념: 포털 승인 표시와 실제 API 응답을 함께 확인해야 연결 가능 여부를 판정할 수 있다.

### 2026-10-06 — 경기 노선 회복과 단일 공개 경로 매핑 대조 성공
- 사용자 보고/정정: 노선/정류소 활용신청 후 정류소 서비스가 서울특별시_정류소정보조회임을 확인. 경기 정류소 승인으로 간주하지 않음. 최신 Notion v0.19·TODO와 GBIS 노선/정류소 경유노선 명세 확인.
- 실제 재조회: check_public_baseinfo.py 실행, 경기 정류소 검색/경유노선은 각 HTTP 403 유지. 경기 노선 정차순서는 HTTP 200/resultCode=0·83건, 요청시각 queryTime 파싱 가능 확인. 이는 도착정보 생성시각 확인이 아님.
- 독립 진행: 카카오 공개 판교역→성남시청 좌표 경로를 1회 조회해 76번 판교역동편→성남시청전면 후보 확인. 경기 노선 API가 정류장 ID·좌표·순번을 제공하므로 정류소 API 권한을 우회하지 않고 허용된 노선 데이터로 대조.
- 구현 준비: backend/route_mapping_probe.py와 check_gyeonggi_mapping.py 신규. 이름 정규화·전체 중간 정류장 순서·양끝 좌표·순번 유일성/중복 검사. 반대 방향·동명 정류장/노선·반복 방문은 임의 선택하지 않음. 원본 응답은 메모리에서만 처리, 파일 저장/AI 전달·개인 주소 없음. 진단 좌표 허용오차 100m는 실험용이며 운영 정책 미확정. F01-06 서비스 어댑터가 아님.
- 실제 실행: 첫 진단은 76번 동명 후보 5개에 기존 한도 4개가 부족해 route_disambiguation_required로 종료. 한도를 6개 후보/최대 9회 요청으로 조정해 모든 5개 노선을 조회. 최종 후보 1개, 카카오 정류장 11개가 공공 순번 승차 7→하차 17로 일치, 양끝 좌표차 11.07m/12.85m. 해당 stationId/routeId/staOrder로 도착 1건을 받아 식별자와 승차순번 일치 확인, 종료 0. 첫 카카오 직행버스는 진단 대상일 뿐 사용자 실제/최적 경로 선정 아님. 원천 최신성/정확도 검증 아님.
- 로컬 검증: 매핑 unittest 7개 통과(정상 후보, 역방향, 원거리 동명, 복수 노선, 반복 정류장 순번, 좌표/중간 정류장 누락, 중복 순번). 운영 연동·UI·추가 노선/회차/광역·서울/지하철 매핑은 수행하지 않음.
- 문서: 게시 전 최신 Notion 재조회 후 v0.20로 경기 노선 회복/단일 매핑 결과·진단 한계 기록, 재조회 기대 본문 일치 확인. api_contract.md·provider_plan.md·planning.md·public_arrivals_plan.md·README.md·todo.md·feature_breakdown.md·일지 갱신. 서비스 API 경로/필드·계산/저장 계약과 클라이언트 호환성 변경 없음. https://app.notion.com/p/3ebace1670c6806c8199cde33ebfbdfa
- 완료/남은 일: D02-03i 단일 공개 사례 대조 완료, D02-03h·D02/F01 전체 미완료. 경기 정류소 추가 승인·서울 기반정보 조회·반대편/회차/다른 지역·원천 생성시각/만료·운영 매핑 허용오차 검증 필요. 다음은 이 잔여 검증이며 F00로 건너뛰지 않음.
- 배운 개념: 별도 정류소 API가 없어도 허용된 노선 정차순서/좌표로 일부 공개 사례를 대조할 수 있다. 동명 노선 5개 중 이름만으로 택하지 않고 전체 정류장 순서·양끝 좌표·실시간 응답 ID까지 비교해야 한다.

### 2026-10-06 — 기반정보 권한과 최신성 조사: 403으로 실제 매핑 보류
- 요청/근거: 사용자가 다음 단계 진행 요청. 최신 Notion v0.18·TODO·공공 API 계획과 서울 정류소/GBIS v2 정류소 경유노선·노선 정차순서 공식 명세 읽음. 경기 버스노선 포털 신청 페이지(15080662) 확인. 정류소 포털 직접 신청 URL은 공식 열람으로 확정하지 못했으므로 임의 URL을 제공하지 않음.
- 실제 권한 조회: 경기 getBusStationListv2(keyword=판교역동편), getBusStationViaRouteListv2(stationId=공식 예시), getBusRouteStationListv2(routeId=공식 예시)를 HTTPS로 각 1회 병렬 호출. 모두 HTTP 403. 상세 오류 원문 미출력/미분석으로 신청 누락/반영 지연 등 원인을 단정하지 않음. 도착 API 성공과 별개로 추가 서비스 승인/권한 확인 필요. 기반정보를 받지 못해 카카오 ID·좌표·방향·정차순서 실제 매핑을 수행하지 않음.
- 최신성 조회: 경기 도착 항목 1회 HTTPS 재조회 HTTP 200/resultCode=0·1건. queryTime 존재/파싱 가능 확인, 확인한 행별 생성시각 필드 없음. queryTime은 공식 정보요청시간이며 원천 데이터 생성시각이 아니므로 최신성 확인 완료로 기록하지 않음. 서버가 생성시각을 전혀 제공하지 않는다고 일반화하지 않음.
- 준비/변경: backend/check_public_baseinfo.py 신규(권한 재확인 3종·키/URL/원문 미출력), backend/provider_freshness.py 신규(명시적 임계값·생성시각 진단만, 운영 서비스 미연결), backend/tests/test_provider_freshness.py 신규. public_arrivals_plan.md·provider_plan.md·planning.md·todo.md·feature_breakdown.md·README.md·api_contract.md 및 일지 갱신. 원본 공급자 응답 저장/AI 전달 없음, .env 변경 없음, 서울 HTTP 개인 키 추가 전송 없음.
- 검증: 생성시각 누락/시간대 미확인/잘못된 시각·미래 시각·임계값 경계/만료·유효하지 않은 임계값 관련 unittest 6개 통과. 명시된 시간대가 없으면 naive 생성시각을 임의 KST로 확정하지 않음. missing→age=0 치환 없음. 60초는 합성 테스트 값이며 운영 만료 정책 확정/실제 데이터 신선도 검증 아님.
- 명세: Notion v0.19에 권한 실패·요청시각/원천 생성시각 구분·진단 준비와 미검증 범위 추가, 재조회 기대 본문 일치 확인. 대응 로컬 본문 동기화. 서비스 API 경로/입력/응답 및 클라이언트 호환성 변경 없음. 기존 30초 갱신·60초 만료는 제안 상태 유지, D03 미정. https://app.notion.com/p/3ebace1670c6806c8199cde33ebfbdfa
- 완료/다음: D02-03g 조사/진단 준비만 완료, D02-03h 실제 매핑은 403으로 보류. 경기 정류소/노선 서비스 추가 활용신청·승인/반영 확인 후 재조회. 서울 정류소 승인과 원천 생성시각/갱신 지연 근거 확인도 남음. D02/F01 전체 미체크.
- 배운 개념: 인증키가 같아도 서비스별 접근권한은 별개다. 도착 응답에 시각이 있다는 이유만으로 데이터가 최신인 것은 아니며 요청/수신/원천 생성시각을 구분해야 한다.

### 2026-10-06 — 사용자 승인 후 서울 공공 API 개인 키 연결 성공
- 승인: 사용자가 공식 서울 버스/지하철 서버에 HTTP로 키를 보내는 각 1회 테스트를 명시적으로 승인. 자동 승인 검토의 기존 차단이 해소돼 --official-http로 실행. 운영 상시 전송 정책 확정과 구분.
- 실제 결과: 서울 버스 HTTP 200/headerCd=0·104건·초 필드 208개·정류소/노선/순번/방향·mkTm 필드 존재. 서울 지하철 HTTP 200/INFO-000·5건·초 필드 5개·노선/역/상하행/종착역·recptnDt 필드 존재. 둘 다 public_sample=false, transport=http, 명령 종료 코드 0. 키/키 포함 URL·원문 저장/로그·개인 데이터·AI 전달 없음.
- 검증 범위: 개인 키 인증·최소 응답 구조만 확인. 모든 수치의 의미/0 결측 처리·운영중 상태·생성시각의 신선도·예측 정확도·카카오 ID/방향 매핑·기반정보 서비스 권한은 미검증. 이전 경기 HTTPS 성공과 함께 세 API 최소 연결 확인 완료.
- 변경: Notion v0.18로 승인/실응답/잔여 상태를 갱신하고 재조회 기대 본문 일치 확인. api_contract.md·provider_plan.md·public_arrivals_plan.md·planning.md·todo.md·feature_breakdown.md 및 이 일지 동기화. 코드 변경 없음, 기존 로컬 테스트 7개를 재실행한 것은 아님. API 경로·필드·계산 정책/클라이언트 호환성 변경 없음. https://app.notion.com/p/3ebace1670c6806c8199cde33ebfbdfa
- 완료/다음: D02-03f 최소 연결 완료, D02-03d/D02/F01 전체는 미체크. 다음은 기반정보 ID·정류장 좌표/정차 순서/방향과 카카오 경로 대조, 생성시각·최신성/만료 검증. 서울 운영 전송 보안·저장/재사용/AI 전달 조건도 미정. 지하철 수동 탑승 결과 검증 정책 유지.

### 2026-10-06 — 공공 API HTTPS 재확인: 동일 결과
- 사용자 재확인 요청에 따라 세 공급자를 각각 1회 기본 HTTPS로 병렬 호출. HTTP 옵션을 사용하지 않음, 키/URL/원문 미출력.
- 실제 결과: 경기 버스 HTTP 200/resultCode=0·1건·초 필드 2개·식별 필드 존재, transport=https. 서울 버스/지하철은 URLError로 실패하여 인증/도착정보 응답 확인 불가. 현재 기록된 HTTPS 연결 실패 상태를 해소하지 못함.
- 변경: 이 일지와 TODO의 최근 재검증 메모만 추가. 코드·API 계약/운영 정책 변경 없음, Notion v0.17의 검증 상태와 동일해 원본 수정 불필요. 기존 HTTP 개인 키 전송의 자동 승인 거부는 계속 유효하며 명시적 사용자 승인 전 HTTP 호출을 하지 않음. 다음은 승인 또는 안전한 접속 방법 확인. https://app.notion.com/p/3ebace1670c6806c8199cde33ebfbdfa

### 2026-10-06 — 공공 개인 키 최소 검증: 경기 성공, 서울 HTTP 승인 대기
- 사용자 보고: Decoding 포털 키 및 지하철 키 등록. dotenv로 두 변수 존재 확인, 값 출력 없음. 최신 Notion v0.16·TODO·검증 CLI 확인.
- 실제 HTTPS 각 1회: 경기 v2 항목조회는 HTTP 200/resultCode=0·1건, 초 필드 2개 및 stationId/routeId/staOrder/routeDestId 존재 확인. 예시 ID의 정상 응답만 확인했고 카카오 매핑·최신성·다른 노선/시간대·기관별 전체 활용승인 검증 아님. timestamp_fields_present=false는 현재 경기 프로브가 행별 시각 필드를 지정하지 않은 결과이며 공급자가 시각을 제공하지 않는다는 결론이 아님.
- 서울 버스·지하철 HTTPS는 각각 URLError로 실패, 인증 응답 없음. 키 없는 TCP/TLS 진단에서 각 443 TimeoutError·80 tcp_ok. 공식 서울 버스/지하철 명세의 요청주소는 HTTP로 확인. HTTPS 전면 미지원 또는 키 오류라고 단정하지 않음.
- HTTP 진단 준비: CLI에 --official-http 추가, 고정 서울 공식 호스트 두 곳에서만 적용. 경기에는 금지, 자동 HTTPS→HTTP 전환 없음. 키가 평문 전송될 수 있음을 승인 요청 도구에 명시했으나 자동 승인 검토가 실행 전 거부함. 사유: 사용자 API 확인 요청에 암호화되지 않은 HTTP 키 전송의 명시적 동의 없음. 우회하지 않았고 실제 개인 키 HTTP 요청은 미실행. 사용자 승인 또는 안전한 접속 방법 필요.
- 변경: backend/check_public_arrivals.py·tests/test_public_arrivals_probe.py, public_arrivals_plan.md·provider_plan.md·planning.md·todo.md·feature_breakdown.md·api_contract.md 및 이 일지. tests 7개 통과, 기본 HTTPS 실패 시 무재시도/HTTP 전환 금지 및 경기 HTTP 옵션 무호출 검증 포함. 실제 .env 변경 없음.
- 명세: Notion v0.17에 경기 성공/서울 연결·자동 승인 거부/HTTP 진단 승인 대기 기록. 재조회와 기대 본문 일치 확인, 로컬 API 전문 동기화. 원문 자동 링크가 생긴 공식 호스트 표기는 코드로 정리. 기존 서비스 API 구조/클라이언트 호환성 영향 없음. https://app.notion.com/p/3ebace1670c6806c8199cde33ebfbdfa
- 완료/잔여: D02-03e 경기 최소 연결만 완료. D02-03d·D02/F01 전체 미완료, 서울 개인 키 인증·기반정보/카카오 ID·방향/최신성 및 운영 보안 조건 미검증. 다음은 공식 서울 HTTP 키 전송의 명시적 승인 또는 안전한 접속 방법 확인. 지하철 수동 확인 정책 유지.

### 2026-10-06 — 지하철 수동 탑승 검증 정책과 공공 실시간 API 준비
- 사용자 요구: 지하철 역 내부 이동 결과는 GPS가 아닌 역 근처 도착 후 본인 수동 탑승 여부로 확인. 서울·경기 공공 실시간 도착 API 준비 시작.
- 정책 반영: GPS·고도·근접으로 승강장 도착/탑승을 확정하지 않고 source=manual 본인 탑승/놓침 신고로 안내 결과 검증. 탑승 시각의 대기 혼입 때문에 접근 완료 없이 내부 이동 시간을 역산/학습하지 않음. 기존 관측 이벤트·단위·수동 접근 완료 품질 규칙 유지, 새 필드/도보 분 필수 입력 없음. planning.md·personalization.md·ai_prompts.md·logging.md 및 명세 동기화.
- 조사: 서울/경기 버스 도착·서울 정류소 공공데이터포털, GBIS 최신 v2 도착/정류소/노선 매뉴얼, 서울 지하철 API와 범위 안내 실제 열람. 경기 stationId/routeId/staOrder 필요 및 초 predictTimeSec/분 predictTime 구분 확인. 서울 밖 일부 지하철 역 미제공 안내 확인, 경기 지하철 전체 지원으로 간주하지 않음.
- 준비 파일: public_arrivals_plan.md 신규(신청 링크·키·ID·단위·한계·실행 안내), backend/check_public_arrivals.py 신규(세 공급자 1회 프로브·키 누락 시 무호출·리다이렉트 차단·원문/URL 미출력), backend/tests/test_public_arrivals_probe.py 신규. .env.example에 공공 포털/지하철 빈 키 변수만 추가, 실제 .env 변경 없음. README·provider_plan·todo·feature_breakdown 갱신.
- 실제 호출: 공식 서울 지하철 공개 sample 키로 서울역 1회 조회. HTTP 200·INFO-000·5건, 초 단위 필드 5개·식별/생성시각 필드 존재 확인, 종료 코드 0. sample은 비밀 없는 공식 HTTP 예제이며 실키는 HTTPS만 준비(실제 지원 미검증). 개인 키 인증·다른 역·실제 최신성/정확도·운영 호출권한 검증은 아님. 키/개인 데이터·원본 응답을 출력/보관/AI 전달하지 않음.
- 로컬 검증: unittest 5개 통과(HTTP 200 본문 오류, 정상 무결과, 분/초 혼동과 음수 예측, 방향 누락, 키 없을 때 무호출). 실제 개인 키 모드 3개 모두 missing_key/종료 1로 확인, 외부 호출 없음. 버스 실호출·키 발급/활용신청·계정 로그인은 수행하지 않음. 서비스 F01-06 어댑터/출발 안내 구현과 구분.
- Notion: 최신 v0.15 원문 확인 후 수동 탑승 근거 및 18절 준비 상태를 v0.16으로 수정. 재조회 본문과 기대 변경 내용 일치 확인. api_contract.md와 provider_plan.md 대응 부분 동기화. 기존 API 경로/이벤트/입력·클라이언트 호환성 변경 없음, 관측 근거 정책을 명시화. 기준 https://app.notion.com/p/3ebace1670c6806c8199cde33ebfbdfa
- 완료/잔여: D02-03c 준비·샘플 구조 검증만 완료. D02-03d 개인 키 발급/활용승인·인증 실호출/ID·방향·만료 검증 미완료, D02/F01 전체 미체크. DATA_GO_KR_SERVICE_KEY(Decoding 키), SEOUL_SUBWAY_API_KEY(지하철 전용 키) 준비 후 다음 단계 진행. 운영 보관·카카오 저장/AI 전달·경기 지하철 추가 공급자 검증도 미완료.
- 배운 개념: 수동 탑승 결과는 성공/놓침 품질 근거지만 대기 없는 내부 이동 시간의 직접 측정은 아니다. 도착정보는 ID·노선·방향·정차 순서·생성시각까지 연결해야 하며 샘플 응답은 개인 서비스 승인/전체 지원을 증명하지 않는다.

### 2026-10-06 — 카카오 도보·대중교통 최소 경로 검증
- 사용자 요청: 장소 검색 성공 후 도보·대중교통 검증 진행 승인. 최신 Notion v0.14·todo/provider_plan 및 카카오 공식 REST 요청/응답 스키마 확인.
- 변경/목표: backend/check_kakao_routes.py 신규. .env REST 키로 공식 /v2/routing/walk와 /v2/routing/publictraffic 각 1회 호출. 강남역→역삼역/서울역 주변 공개 근사 좌표 사용(실제 출입구·플랫폼 확정 좌표 아님). WGS84 x=경도/y=위도, 시간=초·거리=미터 기준 검사. 전체 후보/구간의 정수·음수 금지·유한 좌표 범위, 단계 타입·환승 필드와 검사한 공공 ID 필드 존재 여부 확인. 키·원본 응답·실제 개인 주소 출력/저장·AI 전달 없음, 리다이렉트 차단.
- 실제 실행: 외부 통신 권한으로 backend/.venv/Scripts/python.exe backend/check_kakao_routes.py 실행, 종료 코드 0. 도보 HTTP 200/status OK·경로 1개/4단계·897m/925초·0.16초. 대중교통 HTTP 200/status OK·경로 15개/총 49단계·BUS/SUBWAY/BUS_AND_SUBWAY 및 BUS/SUBWAY/WALKING 단계·0.55초. 첫 후보 15,471m/2,155초/환승 1회(권고/최적 후보 선정 아님). 전체 시간·거리·좌표 형식 검사 통과.
- ID 결과/한계: 정류장/차량 name 존재. 검사한 stId/stationId/busRouteId/routeId/arsId/staOrd 필드가 stops/vehicles에 없음을 확인. 실제 공공 ID 연결 성공으로 간주하지 않음. 역 내부 이동·출입구·방향 검증, 서울 외 경기/광역·지역 경계, 막차/급행/분기, 실시간 도착/미래 환승·정상 무결과/공급자 실패는 이번 요청에서 미검증.
- 명세/문서: Notion v0.15에 18절·상태·변경 이력 갱신 및 재조회 저장 확인. api_contract.md와 provider_plan.md의 대응 본문 동기화. planning.md·feature_breakdown.md·todo.md·README.md·이 일지 갱신. API 경로·입력/응답·계산·저장 정책 변경 없음, 기존 클라이언트 영향 없음. https://app.notion.com/p/3ebace1670c6806c8199cde33ebfbdfa
- 진행: D02-03b 최소 실호출만 완료. F01-02/03은 부분 상태이며 미체크, D02·D02-03 전체 미완료. 저장/파생 재사용/AI 전달 허용·실제 앱 비용/쿼터·지도 SDK는 별도 미정/미검증.
- 로컬 검증: 최종 api_contract.md와 Notion 재조회 전문의 개행 정규화/파일 끝 개행 제외 대조 통과. 경로 검증 스크립트 py_compile 및 git diff --check 통과(줄바꿈 변환 안내만 있음). UI 변경 없음, 앱 테스트/브라우저 검증은 수행하지 않음.
- 배운 개념/다음: 경로 예상 소요시간은 차량 실시간 도착이 아니다. 이름만 있는 경로를 공공 도착정보에 붙이려면 정류장 좌표·노선 정차 순서·방향 ID 근거가 필요하다. 다음은 공공 실시간 API 승인/키와 ID 매핑 근거 확인 및 경기 대표 사례 검증. F00로 건너뛰지 않음.

### 2026-10-06 — 카카오 장소 검색 최소 실호출 성공
- 사용자 진행: 앱 생성 및 .env 키 저장 보고. dotenv로 KAKAO_REST_API_KEY·KAKAO_JAVASCRIPT_KEY 존재 확인. 키 값을 출력하지 않음. 콘솔 무료 쿼터 배지·사용 설정·도메인 등록을 직접 확인한 것으로 기록하지 않음.
- 목표/구현: backend/check_kakao.py 신규. 프로젝트 루트 .env에서 REST 키를 읽어 공식 dapi.kakao.com 키워드 장소 검색에 공개 장소 강남역·지하철역 SW8·주변 1km·size=3으로 1회 요청. 리다이렉트 차단, 원문 응답/키/좌표 값을 출력·저장하지 않고 개수와 필드/좌표 범위 검증만 출력. 실제 사용자 주소·AI 전달 없음.
- 실행: backend/.venv/Scripts/python.exe backend/check_kakao.py를 외부 통신 권한으로 실행. HTTP 200, 결과 3개, 장소 ID·이름·SW8 분류 및 x=경도/y=위도 범위 확인, 0.12초, 종료 코드 0. JavaScript 키는 존재 확인만 했으며 SDK 렌더링 성공을 뜻하지 않음.
- 변경/진행: provider_plan.md·todo.md·feature_breakdown.md·planning.md·README.md·api_contract.md 및 이 일지 갱신. D02-03a만 완료, D02-03·F01-02 전체·F01-03/04/05 등은 미완료 유지. F00 구현으로 건너뛰지 않음.
- 명세: 최신 Notion v0.13과 카카오 공식 REST 문서 읽음. v0.14로 18절·버전/변경 이력에 실제 검증 상태 반영 후 재조회로 기대 내용과 일치 확인. API 경로·요청/응답·계산·저장 정책 변경 및 기존 클라이언트 호환성 영향 없음. https://app.notion.com/p/3ebace1670c6806c8199cde33ebfbdfa
- 배운 개념/다음: REST 키의 장소 검색 성공과 지도 JavaScript 키/경로 API/실시간 데이터 연결 성공은 별개다. 다음은 도보·대중교통 대표 경로 응답과 공공 ID 매핑 검증. 원본 저장·파생 시간·AI 전달 조건과 실제 앱 쿼터/비용은 별도 미정.

### 2026-10-06 — 현재 AI 키 사용 기한 기록
- 사용자 제공 정보: 현재 커스텀 AI 서버용 키는 2026-10-08까지 사용 가능. 정확한 만료 시각·시간대 및 서버 설정을 직접 검증한 것은 아님.
- 변경: provider_plan.md에 사용 기한, todo.md에 D02-04d 갱신/교체 확인 작업 기록. 키 원문·일부 문자·전용 서버 경로를 기록하지 않음. .env 변경·외부 호출·자동 알림 설정 없음.
- 명세 영향: 현재 개발용 자격정보의 운영 메모이며 API 경로·필드·계산·저장 계약 변경 없음. Notion 수정 불필요. 2026-10-08 이후 호출 전 새 키/갱신 여부 확인. 기준 https://app.notion.com/p/3ebace1670c6806c8199cde33ebfbdfa

### 2026-10-06 — 승인된 커스텀 AI 서버 연결 성공
- 승인: 사용자가 mlapi.run으로 .env 키를 보내는 최소 연결 테스트를 명시적으로 승인. 이전 자동 승인 검토 차단이 해소되어 준비된 backend/check_ai.py를 외부 통신 권한으로 실행.
- 실제 결과: HTTP 200, completed, 응답 model=gpt-5.6-luna 일치, 정확한 OK 출력 확인. 소요 1.33초, 입력 11·출력 5·총 16토큰(중계 서버 보고), 프로세스 종료 코드 0. 키/헤더/서버 전체 경로·개인 위치/일정·카카오 원본 데이터를 출력/전송하지 않음. 요청 store=false이며 중계 서버의 실제 보관 이행은 별도 검증하지 않음.
- 범위: 연결/인증·합성 모델 응답 확인 완료. 도보/일정 프롬프트 품질·구조화 스키마·운영 데이터 처리·중계 서버 실제 청구 단가·예산은 미완료. 공식 OpenAI 직접 호출/중계 내부 실제 모델 검증으로 간주하지 않음. 이전 키 접두사/401 기록은 커스텀 서버 키 오류 근거가 아님.
- 변경: todo.md·feature_breakdown.md의 D02-04c만 완료 처리, D02/D02-04b는 미완료 유지. provider_plan.md·planning.md·ai_prompts.md·README.md·api_contract.md와 이 일지에 결과/한계 기록. Notion v0.13에 접속 경로·최소 검증·운영 조건 미정을 반영하고 재조회로 저장 확인. 기존 API 경로/필드·클라이언트 호환성 영향 없음. https://app.notion.com/p/3ebace1670c6806c8199cde33ebfbdfa
- 배운 개념/다음: 같은 모델명이라도 baseURL이 다른 서버에는 해당 서버의 키가 필요하다. 최소 연결 성공은 기능 품질 완료가 아니다. 다음은 D02-03 잔여 검증 및 D02-04 예산·운영 데이터 처리/품질 결정. F00 구현으로 건너뛰지 않음.

### 2026-10-06 — baseURL 확인 및 연결 스크립트 준비: 외부 호스트 키 전송 승인 대기
- 사용자 요청: .env의 baseURL을 확인해 재검증. OPENAI_API_KEY·OPENAI_BASE_URL·OPENAI_MODEL 존재 확인. baseURL은 HTTPS mlapi.run 엔드포인트이며 쿼리/사용자정보 없음. 키·엔드포인트 전체 경로는 일지에 기록하지 않음.
- 이전 판단 정정: 앞선 요청들은 .env의 baseURL을 무시하고 api.openai.com으로 고정 호출했다. 그 401 및 sk- 접두사 부재로 커스텀 서버의 키 유효성을 판단할 수 없다. 기존 기록은 당시 실행 사실이며 현재 키 오류의 근거로 사용하지 않는다.
- 변경 파일: backend/check_ai.py 신규. 프로젝트 루트 .env를 읽고 설정된 baseURL에 /responses를 붙임. 모델 gpt-5.6-luna 검증, HTTPS/사용자정보·쿼리 제외, 리다이렉트 차단. 합성 OK 입력·32 출력 토큰 제한·store=false. 키/헤더/원문 오류/서버 전용 경로 미출력. 설정된 엔드포인트를 이용하는 최소 연결 확인 준비 완료.
- 검증: backend/.venv/Scripts/python.exe -m py_compile backend/check_ai.py 성공. 실제 외부 호출은 자동 승인 검토에 의해 실행 전에 거부됨. 거부 사유: 저장된 API 키를 신뢰되지 않은 외부 호스트 mlapi.run에 전송하는 명시적 승인이 없음. 우회 실행하지 않음. 해당 서버로 키를 보내는 사용자 승인 대기.
- 명세: 최신 Notion v0.12 읽음. 기능/API/계산/저장 계약 구현은 변경하지 않음. 실제 서비스 데이터의 중계 서버 전달 조건은 여전히 미정이며 이번 합성 연결 확인과 별개. 신규 전송 정책은 승인 전 확정하지 않음, Notion 수정 없음. https://app.notion.com/p/3ebace1670c6806c8199cde33ebfbdfa
- 배운 개념/다음: 모델 이름·API 호환성·접속 서버는 구분한다. 커스텀 서버에는 해당 서버용 키와 baseURL을 함께 적용해야 한다. mlapi.run으로 최소 요청의 키 전송을 승인받은 뒤 준비된 스크립트 실행. D02-04 연결 검증은 미완료 유지.
- 예시 파일 정리: .env.example에도 실제 키가 들어 있었고 파일 전체 열람 도구 출력에 노출됨. 이를 출력한 확인 방식은 잘못됐으며 키 원문을 이 일지에 복제하지 않음. 예시의 OPENAI_API_KEY를 빈 값으로, baseURL을 공개 기본값으로 변경. 실제 .env는 변경하지 않음. 사용자에게 노출 키 교체 필요를 안내함.

### 2026-10-06 — OpenAI 연결 추가 재시도: 401 유지
- 사용자 재요청에 따라 저장된 .env로 같은 최소 Responses 요청 1회 재실행. 0.53초에 HTTP 401, 모델 출력/사용량 없음.
- 원인 분리를 위해 생성 없는 GET /v1/models/gpt-5.6-luna 조회 추가: HTTP 401 JSON 오류. 허용된 분류에서 invalid_api_key/insufficient_quota/model_not_found 명시 여부는 모두 false이며 오류 원문을 출력하지 않아 상세 사유를 단정하지 않음.
- 로컬 형식 확인: 키 존재, 앞뒤 공백 없음, 줄바꿈 없음, ASCII 값. 일반적인 OpenAI API 키의 sk- 접두사 없음. 키 일부나 길이·원문은 출력하지 않음. API 키 대신 다른 식별자/설정값인지 사용자 확인 필요.
- 변경: 이 일지와 todo.md의 최근 시도 상태만 갱신. API 계약/기능/보관/계산 정책 영향 없음, Notion v0.12 수정 불필요. 앱 기능·모델 접근·품질 검증은 미완료. 다음은 실제 OpenAI API 키를 루트 .env에 저장한 뒤 연결 재확인. https://app.notion.com/p/3ebace1670c6806c8199cde33ebfbdfa

### 2026-10-06 — OpenAI 연결 재확인: HTTP 401 인증 실패
- 요청: 사용자가 .env 저장 후 재확인 요청. 루트 .env를 python-dotenv로 읽어 OPENAI_API_KEY 존재 및 OPENAI_MODEL=gpt-5.6-luna 일치 확인. 키 원문·일부 문자·헤더·서버 오류 원문을 출력하지 않음.
- 실행: backend/.venv/Scripts/python.exe로 표준 urllib 사용. POST https://api.openai.com/v1/responses에 model=gpt-5.6-luna, 합성 입력 “Reply with exactly OK.”, max_output_tokens=32, reasoning.effort=none, store=false로 최소 요청. 개인 위치/주소·일정·공급자 원본 데이터 전송 없음. 앱 코드 변경 없음.
- 실제 결과: 기본 샌드박스 요청은 0.08초에 URLError로 실패. 외부 통신 권한으로 재시도하여 0.51초에 HTTP 401 응답 수신. 인증 실패, 모델 출력·사용량·품질/비용 실측 없음. 서버 오류 코드가 허용 목록에 없거나 누락되어 원문 대신 unclassified로 출력했으므로 상세 원인은 단정하지 않음. 현재 키의 유효성·권한 확인이 필요함.
- 명세: 최신 Notion v0.12의 모델 선정 및 D02-04 미검증 상태 확인. API 계약·기능·저장 정책 변경 없음, Notion 수정 불필요. provider_plan.md와 todo.md에 실패 결과 반영. https://app.notion.com/p/3ebace1670c6806c8199cde33ebfbdfa
- 배운 개념: .env 로딩·네트워크 도달·인증·모델 출력은 별개다. 키 존재와 모델 설정 일치만으로 연결 완료가 아니며 HTTP 401은 이번 요청의 인증이 승인되지 않았다는 뜻이다.
- 남은 문제/다음: 올바른 OpenAI API 키의 유효성/권한을 확인하고 루트 .env에 저장한 뒤 동일 최소 요청 재검증. D02-04b/D02 상위는 미완료 유지. 모델 품질·예산·외부 데이터 전달 조건은 별도 검증 필요.

### 2026-10-06 — OpenAI 연결 확인 보류: 저장된 키 없음
- 요청: 사용자가 .env에 추가한 AI 키 확인 및 연결 1회 검증 요청.
- 실제 확인: C:/projects/timeisnow/.env에는 PostgreSQL 변수 5개만 존재, OPENAI_API_KEY 할당과 sk- 형태 텍스트 없음. 현재 프로세스에도 OPENAI_API_KEY 없음. 프로젝트 검색에서 별도 backend/.env/frontend/.env는 발견되지 않음. 루트 .env 수정 시각은 2026-10-02 10:30:09(실행 호스트 표기). 비밀값은 출력하지 않음.
- 명세 확인: 연결된 Notion에서 최신 v0.12 및 D02-04 상태 확인. OpenAI 공식 텍스트 생성 문서 열람. 계약·공급자 선택·보관 정책 변경 없음, Notion 수정 불필요. https://app.notion.com/p/3ebace1670c6806c8199cde33ebfbdfa
- 실행 결과: 키 부재로 외부 API 호출/과금 발생 없음. 연결 성공이나 모델 접근 확인으로 기록하지 않음. 앱 코드·API 계약 변경 및 앱 테스트 없음. 초기 Python 확인은 루트 .venv가 없어 실패했고 실제 가상환경은 backend/.venv/Scripts/python.exe임을 확인.
- 배운 개념/다음: 편집기 내용과 디스크에 저장된 .env는 다를 수 있다. 루트 .env에 OPENAI_API_KEY를 저장하거나 실제 파일 경로를 확인한 뒤 최소 합성 입력으로 1회 연결 검증. 키 원문은 채팅/로그로 보내지 않는다. D02-04 미완료 유지.

### 2026-10-06 — D02-04 OpenAI GPT-5.6 Luna 선정
- 사용자 결정: “ai 공급자는 gpt 5.6 루나야”. 공급자는 OpenAI, 모델은 GPT-5.6 Luna로 기록. 공식 API ID는 gpt-5.6-luna이며 다른 모델로 대체하지 않음.
- 변경 파일: provider_plan.md, planning.md, feature_breakdown.md, todo.md, ai_prompts.md, README.md, api_contract.md 및 이 일지. D02-04a 선정/문서 확인만 완료, D02-04/D02-04b 예산·데이터 처리 조건·계정 접근·실호출은 미완료 유지.
- 검증: OpenAI Docs 스킬 사용. 공식 모델 문서를 검색 후 실제 열람하여 ID·Structured Outputs 지원·표준 텍스트 100만 토큰 입력 $0.20/캐시 입력 $0.02/출력 $1.20 확인. 장문·부가 도구 등의 별도 조건이 있으며 단가는 프로젝트 예산 승인이 아님. 모델 접근·스키마 준수·한국어 도보/일정 해석 품질·지연·비용 실측은 검증하지 않음. https://developers.openai.com/api/docs/models/gpt-5.6-luna
- 명세 동기화: 최신 Notion v0.11 자연어 일정 기획을 먼저 읽고 보존한 뒤 v0.12로 요약·18절·버전/변경 이력만 수정. 재조회 결과가 기대 내용과 일치함을 확인(Notion의 달러 기호 이스케이프 포함). 로컬 api_contract.md와 전문 대조. 기존 API 경로·필드·클라이언트 호환성 변경 없음. 기존 프롬프트 본문/버전 유지.
- 실행 제한: AI 연결 코드·키 발급·과금 활성화·모델 실호출·앱 테스트는 수행하지 않음. 공식 문서 기능 지원이 실제 계정에서의 연동/평가 완료를 뜻하지 않음.
- 배운 개념: 공급자(OpenAI)와 모델(GPT-5.6 Luna), API 모델 ID(gpt-5.6-luna)는 구분한다. 구조화 출력 지원에도 서버 스키마 검증과 실제 품질 평가가 필요하다.
- 남은 문제/다음: D02-03 실시간 공급자/ID/저장 조건과 D02-04 예산·외부 데이터 처리·실호출 검증. 이후 D03 정책 결정. F00로 건너뛰지 않음. 기준 https://app.notion.com/p/3ebace1670c6806c8199cde33ebfbdfa

### 2026-10-06 — D02-03 카카오맵 선정 반영과 문서 검증
- 목표/사용자 결정: 이전 대화의 “카카오맵을 쓸 거야”를 선정 결정으로 반영하고 D02 잔여 검증을 진행. 착수 전 결정 순서를 유지하며 F00 구현으로 건너뛰지 않음. 지원 지역 서울·경기, AI 공급자/모델/예산은 PM 확인 대기.
- 변경 파일: provider_plan.md, planning.md, feature_breakdown.md, todo.md, README.md, api_contract.md 및 이 일지. 공급자 검증표·대표 사례 후보·통과 기준·공급자 문의 초안 작성. 문의는 발송하지 않음.
- 명세 확인: 웹 도구의 Notion URL 접근은 실패했지만 연결된 Notion fetch로 v0.9 원문을 읽음. 변경 전 로컬 api_contract.md와 원문 본문이 일치함을 확인. 관련 지역/공급자·계산·저장·AI·로깅 문서와 비교.
- 문서 검증: 2026-10-06 카카오 공식 REST·쿼터·이용 방법·약관/운영 정책 및 서울/경기 공공데이터포털 열람. 대중교통/도보 API 존재, REST 키·초/미터·좌표 순서 및 각 일간 1,000건/추가 10원 재확인. 검색어 불일치로 처음 찾지 못한 항목은 공식 본문에서 재확인했으며 미지원으로 판단하지 않음.
- 주요 결과: 카카오 공개 경로 스키마에 공공 정류장/노선/방향 ID가 명시되지 않아 이름만으로 연결할 수 없음. 서울 노선 전체 도착 기능의 ID·순번·방향·기준시각·초 단위 필드 확인. 경기 상세 활용명세·단위·실응답은 미확인. 카카오 약관 제11조 제3항의 사전 승낙 조건을 확인했지만 서비스별 원본 저장·파생 시간 재사용·AI 전달·품질 이력 보관 허용은 확정하지 않음.
- 실행 결과/제한: 현재 프로세스 환경 및 프로젝트 .env/backend/.env에서 공급자 키를 확인하지 못함. 변수 이름만 확인했고 값은 출력하지 않음. 키 발급·가입·활용신청·과금 활성화·실호출·앱 코드 변경·앱 테스트는 수행하지 않음. 기존 테스트 결과를 이번 작업 성공으로 재사용하지 않음.
- Notion 동기화: v0.10로 18절·요약·버전/변경 이력 갱신. 상태 API 구현 사실을 전체 미구현 표기와 구분. 기존 API 경로·입력·응답·계산 수치 변경 없음, 클라이언트 호환성 영향 없음. 재조회로 수정한 본문과 기대 내용의 완전 일치 확인. Notion이 추가한 파일/필드 자동 URL은 인라인 코드로 바로잡음. 최종 재조회 본문 54,608문자와 api_contract.md를 개행 정규화/파일 끝 개행 제외하여 전체 대조 통과. provider_plan.md 18절도 같은 본문 사용.
- 기준: https://app.notion.com/p/3ebace1670c6806c8199cde33ebfbdfa
- TODO: 선정 결정 기록과 공식 문서 조사는 완료. D02·D02-03·D02-04 및 F01 체크는 미완료 유지. 개발 문서 작성과 실제 공급자 연동 완료를 구분함.
- 로컬 검증: git diff --check에서 feature_breakdown.md의 기존 파일 끝 빈 줄을 발견해 정리하고 재검사 통과(줄바꿈 변환 안내만 있음). TODO 갱신일·현재/다음 작업·D02 미체크 상태와 기획 변경 이력 검색 확인.
- 배운 개념: 지도 표시·경로 예상시간·실시간 도착은 별개의 데이터다. 공급자마다 ID가 달라 정류장 좌표·정차 순서·방향까지 연결해야 하며, 파생 시간만 저장해도 저장/외부 전달 조건을 별도로 확인해야 한다.
- 남은 문제/다음: 실제 앱 무료 쿼터/키·공공 API 승인 준비, 공급자 저장/AI 전달 조건과 공식 ID 연계 근거 확인, 대표 사례 실호출. AI는 PM 답변 반영. D02 해소 뒤 D03 정책 결정으로 진행하며 F00-03/04 착수는 이번 작업 범위 아님.

### 2026-09-30 — 기획 및 개발 방식 정리

- 목표: 개인화 통근 서비스의 기능과 개발 구조를 정한다.
- 결정: React 프론트엔드, Python FastAPI 백엔드를 사용한다.
- 기획 내용: 회원가입, 고정 장소·현재 위치 출발, 환승, AI 도보 산정, 저장값 재사용, 초기 5분 여유, 관측 기반 개인화.
- 이번 문서 작업: 실행 로그와 품질 이력 및 개발 일지의 역할을 구분하고 logging.md에 로깅 기준을 작성했다.
- 상태: 기획 문서 작성 단계. 이 작업에서 애플리케이션 코드 구현·서버 실행·테스트는 수행하지 않았다.
- 배운 개념: request_id는 한 요청과 관련된 여러 로그를 함께 찾기 위한 식별자다. 품질 이력은 AI의 예측을 실제 관측과 비교하는 기록이다.
- 다음 작업: 개발 환경과 기존 코드를 확인한 후 React–FastAPI의 작은 요청 흐름부터 구현한다.

## 새 작업 기록 템플릿

### YYYY-MM-DD — 작업명

- 목표: 사용자에게 어떤 동작을 제공하려는가?
- 변경 파일: 실제 바꾼 파일과 각 역할.
- 선택 이유: 이 구조나 방법을 택한 이유.
- 확인 방법: 실제 실행한 명령 또는 화면 조작.
- 결과: 기대값과 실제값. 실행하지 않은 검증은 미실행으로 표시.
- 로그 확인: 이벤트명, 오류 코드, 필요한 경우 비식별 요청 ID.
- 문제와 해결: 원인, 수정 내용, 아직 남은 문제.
- 배운 개념: 핵심 개념 1~2개를 쉬운 말로 설명.
- 다음 작업: 이어서 할 작은 작업.

## 추가 실제 기록

### 2026-09-30 — 기능별 작업 분리

- 목표: 큰 기획을 하나씩 구현하고 확인할 수 있는 작업으로 나눈다.
- 변경 파일: feature_breakdown.md 신규 작성, planning.md에 연결과 버전 반영.
- 선택 이유: React 화면과 FastAPI 동작을 작은 사용자 흐름 단위로 함께 완성하기 위해서다.
- 검증 범위: 문서의 기능 목록과 파일 저장 확인. 애플리케이션 구현·실행·테스트는 아직 수행하지 않았다.
- 다음 작업: 작업 폴더와 실행 환경을 확인하고 F00의 작은 요청 흐름을 구현한다.

### 2026-09-30 — API 명세 참조·동기화 규칙 추가

- 목표: 개발 전에 최신 Notion API 명세를 확인하고 기획·계약 변경 시 문서 갱신을 누락하지 않는다.
- 변경 파일: 프로젝트 루트 C:/Users/태휘/Documents/ChatGPT/elice_first_project/AGENTS.md 신규 작성.
- 규칙: 개발 전 명세 조회, 계약 변경 시 Notion과 관련 로컬 문서 동기화, 저장 재확인, 접근 실패 시 의존 작업 보류와 미완료 보고.
- 명세 영향: 개발 절차 규칙 추가이므로 API 경로·필드·계산 정책에는 변경 없음.
- 검증: 규칙 파일 저장 및 내용 확인. 앱 코드 변경이나 실행 테스트는 수행하지 않음.
- 배운 개념: AGENTS.md는 해당 프로젝트에서 AI가 개발할 때 참고하는 작업 규칙 파일이다.

## 2026-10-01 — 영문 경로에 작업 저장소 준비
- 이유: 프로젝트 루트에서 한글 경로를 제거하기 위해 C:/projects/timeisnow를 새 작업 폴더로 선택.
- 작업: GitLab timeisnow 저장소 clone, 기존 기획 문서 6개와 .gitignore 복사, AGENTS.md 복사 및 기획 문서 경로 수정. 원본 보존.
- 실제 검증: clone 성공(빈 원격 저장소), origin 주소 확인, 복사한 7개 파일의 SHA-256 원본 일치 확인, git status에서 문서 파일 확인. 이 일지는 복사 검증 후 추가함.
- 명세 영향: 파일 위치와 Git 작업 환경만 변경하여 API 계약 변경 없음. 이번 작업에서 Notion 명세를 조회하거나 수정하지 않음.
- 배운 개념: clone은 원격 저장소 연결을 포함한 로컬 Git 저장소를 만들며, 새 파일은 커밋하고 push해야 원격에 저장됨.
- 남은 작업: 첫 커밋과 push는 아직 수행하지 않음. 앞으로 새 경로에서 작업.

## 2026-10-01 — 첫 버전 등록
- 요청: 기획 문서와 개발 규칙의 첫 커밋 및 GitLab main 브랜치 push.
- 대상: .gitignore, AGENTS.md, 기획 문서 6개. API 계약 변경 없음.
- 사전 확인: 현재 main 브랜치에 커밋 없음, origin이 지정된 GitLab timeisnow 저장소임을 확인. Git 작성자 설정 및 .gitignore 확인.
- 배운 개념: commit은 로컬 이력을 만들고 push는 해당 이력을 원격 저장소로 전송함.
- 이 기록은 첫 커밋에 포함하기 위해 실행 전에 작성함. push 결과는 실행 후 로컬 HEAD와 원격 main의 커밋 ID를 비교하여 확인함.

- 실제 실행 결과: 문서 8개로 첫 커밋 생성 성공. push는 GitLab의 보호된 기본 브랜치 권한 정책으로 거부됨(pre-receive hook declined). 원격 커밋 일치 검증은 미완료. Maintainer의 첫 push 또는 Owner/관리자의 권한 조치가 필요함. Markdown 줄바꿈용 끝 공백과 파일 끝 빈 줄은 원본대로 보존함.

### 2026-10-01 — 실제 프로젝트 루트 확인 및 README 추가

- 사용자 안내로 실제 프로젝트가 C:/projects/timeisnow임을 확인했다. 이 폴더의 AGENTS.md도 동일한 경로를 명시하고 있다.
- 잘못된 채팅 작업 폴더의 README를 이 프로젝트로 옮겼다. 기획 배경과 Mermaid를 유지하고 문서 링크를 상대 경로로 수정했다.
- 검증: README의 Mermaid 코드 블록과 모든 로컬 문서 링크 확인. draw.io 재렌더링 및 앱 테스트는 수행하지 않았다.
- API 명세 영향: 없음. 기존 기획 내용을 정리하고 문서 위치만 바로잡음.

### 2026-10-01 — React 화면 프로토타입

- 목표: 언제 출발할지와 도착 후 예상 여유를 중심으로 화면 흐름을 확인한다.
- 변경: frontend의 React/Vite 앱, 반응형 CSS, 화면 흐름 테스트, screen_plan.md와 README 실행 안내.
- 구현: 홈, 루틴 추가·수정, 경로 상세, 직행·환승 단계, 체험 기록, 여유 설정, 미연동 장소·계정 안내.
- 명세: 최신 Notion API 문서 조회. 계약 변경 없이 화면 검토용 프로토타입임을 명세와 구분해 기록.
- 로그: 개발 환경에서 시각·이벤트명·ui_demo 모드만 기록. 실제 request_id 기반 서버 로그는 FastAPI 구현 후 연결.
- 실제 검증: npm test 5개 통과, npm run build 통과. npm 의존성 검사 당시 취약점 0개 보고.
- 한계: 브라우저 도구가 로컬 URL을 ERR_BLOCKED_BY_CLIENT로 차단했고 Chrome 연결도 없어 시각·실기기 검증 미완료. API·로그인·지도·AI·알림 없음.
- 배운 개념: React state는 새로고침 전까지 화면 상태를 유지한다. 샘플 UI 동작과 서버에 저장되는 실제 기능은 별개다. jsdom 흐름 테스트는 실제 브라우저 모양 검증을 대체하지 않는다.
- 다음 작업: 사용자의 레이아웃 피드백, 실제 브라우저 확인, FastAPI와 인증·교통 연동 순으로 진행.

#### 후속 확인 — 로컬 미리보기 복구

- 로컬 서버의 실행 인자 문제를 수정하고 http://127.0.0.1:5174/ 에서 접속을 확인했다.
- 브라우저에서 데스크톱 홈, 390×844 모바일 홈과 하단 메뉴, 루틴 화면 및 편집 창을 확인했다. 기존 시각 검증 미완료 상태를 갱신한다.
- 자동 테스트 5개와 빌드 통과 상태 유지. 실제 휴대전화 및 서버 연동은 아직 검증하지 않았다.

### 2026-10-02 — 약속과 출발 공유 확장 기획

- 요청/이유: 일회성 약속·중간 만남·채팅을 도입하고, 출발 상태 공유로 반복 확인과 불안한 기다림을 줄여 신뢰 형성을 돕는다.
- 변경 파일: meeting_plan.md 신규, planning.md v0.7, feature_breakdown.md F12~F16, README.md 및 이 일지.
- 명세: 최신 Notion을 조회하고 v0.3 확장 기획·정책·계약 영향·변경 이력을 반영한 뒤 재조회해 저장 확인. https://app.notion.com/p/3ebace1670c6806c8199cde33ebfbdfa
- 검증: 로컬 파일 생성과 버전·공유 정책·작업 목록·README 링크 확인. Notion v0.3 및 본인 출발 신고 문구 재조회 확인. 앱 코드 변경, 포팅, 서버 실행, 테스트는 수행하지 않음.
- 계약 영향: 기능 범위 추가. 기존 엔드포인트 요청·응답은 유지하며 신규 약속/채팅/공유 계약은 설계 대기. 기존 클라이언트 호환성 변경 없음.
- 배운 개념: 서버가 수동 출발 신고를 받았다는 사실은 실제 이동 검증과 다르다. 공유 상태에는 근거와 갱신 시각을 표시해야 한다.
- 남은 결정: 2인 우선·출시 순서, 초대/참여 권한 상세, 확장 API, 채팅·공유 기록 보관/삭제, 공유 종료 시점, 자동 감지 검증. AI 프롬프트와 보행 학습 알고리즘은 이번 기획에서 변경하지 않음.

### 2026-10-02 — TODO 체크리스트와 진행 관리 규칙

- 요청: 할 일을 체크박스로 정리하고 작업 완료마다 체크하여 진행 상황을 확인.
- 변경: todo.md 신규, AGENTS.md에 완료 근거·체크 동기화·진행 보고 규칙 추가, README.md에 TODO 링크 추가.
- 검증: 기능 목록의 모든 F 작업 ID와 TODO ID 일치 및 중복 없음 확인. 준비 완료 4개만 기존 일지 근거로 체크하고 실제 연동 기능과 의사결정 항목은 미완료로 유지. 앱 테스트·서버 실행은 수행하지 않음.
- 명세 영향: 기존 요구의 진행 관리만 추가하므로 API 계약 변경 없음. Notion 수정 없음. 기준 명세: https://app.notion.com/p/3ebace1670c6806c8199cde33ebfbdfa
- 배운 개념: 체크박스는 실제 완료 조건과 검증 근거를 표현하며 작업 개수 비율은 제품 완성률이 아니다.
- 다음: F00 백엔드 준비와 상태 API·React 연결·요청 추적. 기능 작업 시 최신 Notion을 다시 확인한다.
### 2026-10-02 — F00-01 개발 환경 준비 완료

- 목표: 기존 React를 유지하고 Python FastAPI의 독립된 실행 환경을 준비한다.
- 확인: 실제 루트 C:/projects/timeisnow, Python 3.13.1, Node 22.14.0, npm 10.9.2. 백엔드 및 전역 FastAPI/Uvicorn이 없음을 확인했다.
- 변경: backend/app/__init__.py, app/main.py, requirements.txt, README.md 신규. backend/.venv 생성(기존 .gitignore로 제외). 루트 README·TODO·기능 목록 갱신. 오래된 first_pjt 위치 설명도 실제 프로젝트 위치로 수정.
- 설치: FastAPI 0.142.2 / Uvicorn 0.54.0과 간접 의존성 모두 requirements.txt에 버전 고정. 기존 프론트 의존성 변경 없음.
- 실제 검증: pip check 정상, FastAPI import 및 비어 있는 업무 경로 확인, Uvicorn 임시 포트 18001 시작 성공, HTTP /openapi.json 조회 성공·/docs 200 확인, React npm run build 통과. 임시 서버 종료. 이번에는 UI 테스트를 재실행하지 않았다.
- 명세: 최신 Notion v0.3을 착수 전 및 완료 전 조회. 실행 환경만 준비했고 상태 API도 아직 없으므로 API 계약·구현 상태 변경 및 Notion 수정 없음. https://app.notion.com/p/3ebace1670c6806c8199cde33ebfbdfa
- 로그: Uvicorn 기본 시작 로그로 구동 확인. 기본 접근 로그는 비활성화했으며 request_id 기반 JSON 로깅은 F00-03~04에서 구현한다.
- 배운 개념: .venv는 프로젝트별 Python 라이브러리를 분리한다. requirements.txt는 같은 버전으로 재설치하는 목록이며, FastAPI는 앱·Uvicorn은 앱을 실행하는 서버다. /docs가 열린다는 것은 실행 확인이지 업무 API 완성이 아니다.
- 다음: F00-02 상태 API와 React 연결. DB·인증·외부 API는 아직 미정이며 필요 시 결정한다.
### 2026-10-02 — PostgreSQL Docker 구성 및 연결 검증
- 사용자 결정: DB는 PostgreSQL, 로컬 실행은 Docker 컨테이너.
- 변경: compose.yaml, .env.example, Git 제외 .env(생성한 비밀번호는 출력하지 않음), backend/app/database.py, backend/check_db.py, requirements.txt, database.md, 기획·README·기능 목록·TODO.
- DB 상태: timeisnow-db-1 healthy, PostgreSQL 17.11, 127.0.0.1:5432, 전용 영속 볼륨. 기존 다른 프로젝트 컨테이너는 변경하지 않음.
- 실제 검증: Compose config --quiet, 호스트 Python SELECT 1, pip check 통과. 검증용 테이블 값 42를 저장하고 해당 DB 컨테이너 재생성 후 값 유지 확인, 검증용 테이블만 삭제. 잘못된 포트에서 종료 코드 1과 비밀 없는 실패 로그 확인.
- 명세: 최신 Notion을 조회하고 v0.4로 PostgreSQL·Docker 결정 및 운영 미정 사항 동기화, 재조회 저장 확인. API 경로·응답·호환성 변경 없음. https://app.notion.com/p/3ebace1670c6806c8199cde33ebfbdfa
- 완료 체크: F00-05a 완료. F00-05 전체 및 F00-05b 마이그레이션은 미완료. 인증 선택 D01도 미완료 유지.
- 배운 개념: 컨테이너는 DB 실행 환경이고 볼륨은 데이터를 유지하는 저장 공간이다. 볼륨을 삭제하는 down -v와 단순 stop은 다르다.
- 다음: F00-02 화면·상태 API 연결, F00-05b 마이그레이션. DB는 사용자 요청대로 실행 중이며 웹/API 서버는 시작하지 않았다.

### 2026-10-02 — F00-05c 테이블·연관관계 설계 초안

- 요청: 필요한 테이블과 관계를 먼저 계획한다. 실제 테이블 생성은 요청 범위에 포함하지 않았다.
- 변경: database_schema.md v0.1 신규(통근 MVP 23개·약속 확장 8개 제안, ERD 2개), planning.md v0.9, database.md·README 연결, TODO·기능 목록의 F00-05c 설계 완료 체크.
- 설계: 회원/장소, 검색/경로/루틴, AI 기준 경로/산정 버전, 안내 스냅샷/실제 이벤트/정정/관측, 개인화 표본, 비동기·멱등 처리, 약속별 참여자/개인 여정/채팅/공유 분리. 컬럼·FK·중복 제약·인덱스·삭제·생성 순서와 미정 결정을 기록.
- 실제 검증: PostgreSQL public 테이블 목록 조회 결과 업무 테이블 없음. 문서 검사에서 31개 테이블과 ERD 2개의 이름 대응, 로컬 링크, TODO·기능 목록의 F00-05c 완료/F00-05b 미완료 상태 확인. Mermaid 실제 렌더링·DDL 실행·FK/쿼리 테스트는 수행하지 않음.
- 명세: 최신 Notion v0.4 조회 후 v0.5에 테이블 구성·관계·이력/삭제 설계 제안을 동기화하고 재조회로 저장 확인. 기존 API 경로·필드·호환성 변경 없음. https://app.notion.com/p/3ebace1670c6806c8199cde33ebfbdfa
- 배운 개념: FK는 테이블 간 연결, N:M은 연결 테이블로 표현한다. 재사용 경로·당시 예측·실제 관측을 분리해야 개인화 전후 품질을 비교할 수 있다. CHECK 하나로 다른 행의 권한과 상태를 모두 보장할 수 없다.
- 남은 결정: 인증 방식, 스키마 변경 도구, 보관/삭제 기간과 약속 공동 기록 처리. 다음은 F00-05b 마이그레이션 기반 준비와 회원/장소부터 단계적 생성이며 이번 작업은 DB 데이터를 변경하지 않았다.

### 2026-10-02 — F00-05b 마이그레이션 기반 완료
- 변경: alembic.ini, backend/migrations(env·템플릿·0001_baseline), backend/migrate.py, backend/tests/test_migrations.py, requirements.txt, migrations.md. DB/설계/README/기획/TODO·기능 목록 갱신.
- 설치: Alembic 1.20.0 / SQLAlchemy 2.1.1. 기존 connect_db()와 .env 설정 재사용, 비밀을 ini나 로그에 넣지 않음. API 시작 시 자동 마이그레이션 없음.
- 실제 검증: PostgreSQL의 고유 임시 스키마에서 upgrade·중복 upgrade·downgrade·재적용 왕복 2회 통과(통합 테스트 1개), pip check 정상. 개발 public에는 alembic_version만 존재하며 0001_baseline(head) 확인. 테스트 스키마 잔여 0개. 잘못된 포트에서는 비밀 없는 실패 로그와 종료 코드 1 확인, 정상 접속 재확인.
- 명세: 착수 전 최신 Notion v0.5 조회, v0.6으로 기반 구현 상태 갱신 후 재조회 저장 확인. 기존 업무 API 계약과 데이터 정책 변경 없음. https://app.notion.com/p/3ebace1670c6806c8199cde33ebfbdfa
- 배운 개념: revision 파일은 구조 변경 코드, alembic_version은 적용 위치다. baseline은 빈 출발점이며 업무 테이블 생성이나 데이터 복구 검증을 뜻하지 않는다.
- 완료: F00-05b 및 기반 범위 F00-05 체크. 회원·약속 테이블, 실제 데이터 롤백·FK 검증은 미완료. 다음 F00-02~04 화면/API/로그 연결, 회원 기능 전 인증 방식 결정.

### 2026-10-02 — F12-API 친구 약속·채팅 상세 API 초안

- 요청: 화면/API 연결 작업보다 친구 약속·채팅 상세 API 문서를 먼저 작성.
- 변경: meeting_api.md v0.1 신규. meeting_plan.md, database_schema.md v0.2, planning.md, logging.md, README, TODO·기능 목록 동기화.
- 계약: 약속·초대·추천·확정·개인 안내·도착 신고·공유·채팅 REST와 WS 티켓/변경 알림/재생·sync 상세 작성. 별도 약속 안내 경로로 기존 routine_id 필수 요청을 유지. 채팅은 REST 저장 후 알림, 수동 출발과 자동 확인 구분.
- 정책: 2인·기간·본문 길이·속도 제한·보관·탈퇴는 초기 제안값으로 표시. 인증 방식과 운영 정책 승인 미완료. 신규 업무 코드·DDL·서버 실행 없음.
- Notion: 최신 v0.6 조회 후 v0.7에 상세 본문(16절)과 기존 개요/관계 설명·변경 이력 갱신. 재조회에서 신규/기존 참조 포함 30개 방식·경로 문구 누락 없음, JSON 예시 9개와 네이티브 표 9개 저장 확인. https://app.notion.com/p/3ebace1670c6806c8199cde33ebfbdfa
- 검증: 로컬 JSON 예시 9개 파싱, 문서 파일/디렉터리 링크 존재, F12-API만 완료 및 F12~F16 구현 미완료 상태 확인. 최초 링크 검사에서 기존 README의 디렉터리 링크를 파일로 가정한 오류가 있어 존재 검사로 수정 후 통과. Notion 이스케이프 문자를 정규화해 경로 비교. 실제 API 통합 테스트는 미실행.
- DB 영향: meeting_realtime_events/tickets 2개와 필요한 컬럼·약속 안내 FK 추가 제안. 설계 총 33개 후보, 마이그레이션 미적용.
- 배운 개념: REST 저장 성공과 WS 수신 순서는 다를 수 있다. 이벤트 ID/seq와 일관된 sync 스냅샷을 함께 사용해 재접속 누락과 중복을 처리한다.
- 다음: 신규 정책 제안 및 인증 방식 결정, 예정된 F00-02~04 React/FastAPI/로그 연결. 현재 완료는 상세 설계 문서이며 약속 기능 자체가 아니다.

### 2026-10-02 — Notion 명세 원문 로컬 복사
- 사용자 요청에 따라 최신 Notion v0.7 전체 본문을 api_contract.md에 복사. 조회 메타데이터와 page/content 래퍼만 제외하고 Notion Markdown의 표·코드·이스케이프는 보존.
- 검증: 전체 44,021문자를 분할 저장하면서 원문과 길이·내용 비교 통과. SHA256: 79FB7779B4DD18CF820B04976EC80CC466DEE532B130E6E355FA8A0B96923164.
- 최초 문자열 인용 방식이 본문의 특수 따옴표를 처리하지 못해 실패하여 here-string으로 처음부터 다시 저장 후 검증함.
- 원본 최종 수정 시각: 2026-10-02T04:08:16.546Z. https://app.notion.com/p/3ebace1670c6806c8199cde33ebfbdfa
- API 계약·Notion 변경 없음. 이 파일은 수동 복사본이며 자동 동기화는 구현하지 않음. 앱 테스트 불필요·미실행.

### 2026-10-02 — 디자인 가이드와 에이전트 준수 규칙
- 요청: 현재 프론트 디자인이 마음에 들어 다른 개발자/AI도 같은 톤을 유지하도록 문서와 규칙 작성.
- 변경: design_guide.md 신규, 기존 AGENTS.md 7절에 필수 준수 규칙 추가, README/screen_plan 연결, TODO P06 완료 체크.
- 근거: 실제 styles.css와 App.jsx의 CSS 변수·색상·폰트·크기·간격·모서리·미디어쿼리·기존 컴포넌트·문구를 읽어 추출. 약속/채팅은 미구현 디자인 적용 제안으로 구분.
- 검증: 로컬 문서 링크 존재 확인. styles.css/App.jsx SHA256 작업 전후 동일 확인. UI 코드 변경 없으며 새 브라우저 렌더링·앱 테스트는 수행하지 않음.
- 명세 영향: 디자인 작업 규칙 문서화만 수행. API 계약 변경 없음, Notion 및 api_contract.md 수정 없음. 기준 API: https://app.notion.com/p/3ebace1670c6806c8199cde33ebfbdfa
- 배운 개념: 디자인 가이드는 색·간격·컴포넌트를 재사용하는 기준이며 기존 작은 글자·대비 문제까지 복제하라는 뜻은 아니다.
- 다음: 실제 UI 작업에서 가이드 재사용 및 영향 화면 검증. 기존 F00-02~04 구현은 여전히 미완료.

### 2026-10-02 — D01 이메일·비밀번호 로그인 결정
- 사용자 결정: 첫 버전은 이메일·비밀번호 로그인. 소셜은 테스트 후 배포 확대 시 검토.
- 변경: auth_api.md 신규, planning.md/meeting_api.md/database_schema.md/feature_breakdown.md/todo.md/README.md 갱신. 서버 쿠키 세션·CSRF·메일 확인·비밀번호 복구·재인증·삭제 영수증은 상세 설계 초안으로 구분.
- Notion API v0.8에 인증 17절 및 관련 기존 계약 반영 후 재조회로 저장 확인. api_contract.md 전체 51,997문자를 원문과 분할별 길이·내용 비교하여 저장.
- 검증: 문서의 인증 결정, 상세 API 및 TODO 상태 확인. F02 구현 항목은 미체크. 앱 코드·DB DDL 변경 없고 실행 테스트는 수행하지 않음.
- 명세 변경: 인증 경로·세션·저장 후보 4개 추가, /me 이메일 확인 상태 및 삭제 영수증 구체화. 기존 계약은 모두 미구현 설계이며 인증 기본 수치는 구현 전 검증 대상.
- 기준: https://app.notion.com/p/3ebace1670c6806c8199cde33ebfbdfa
- 배운 개념: 인증 방식 결정은 실제 로그인 구현 완료가 아니다. 서버 세션은 쿠키의 난수로 서버에 저장된 로그인 상태를 찾는 방식이다.
- 남은 일: 메일 공급자·제한 저장소·미확인 계정 보관 정책 및 F02 구현. 다음 순서는 착수 전 결정 D02이며 F00 구현으로 건너뛰지 않는다.

### 2026-10-02 — D02 지역 확정과 공급자 추천
- 사용자 확정: 서울·경기도 한정, AI 공급자는 프로젝트 매니저 확인 대기.
- 변경 파일: provider_plan.md 신규, planning.md/feature_breakdown.md/todo.md/README.md/api_contract.md 및 이 일지.
- 공식 카카오 REST·쿼터, TMAP 대중교통, ODsay API/약관, 서울·경기 버스 도착 API를 조사. 카카오 중심 경로+공공 실시간 버스 API를 추천안으로 기록. ODsay/TMAP은 매핑·보행 대안.
- 검증: Notion v0.9 및 18절 재조회 저장 확인, 로컬 계약 전체 53556문자 분할별 원문/길이 비교 통과. D02-01/02만 완료, D02 상위·공급자 최종 선정·F01 실제 응답 검증은 미완료 유지.
- 실제 API 키 발급·실호출·요금제 활성화·코드 변경·앱 테스트는 수행하지 않음. 저장·AI 전달 허용 범위는 확정하지 않음.
- 명세 영향: 지원 지역 제한 및 공급자 검토 상태 반영. API 경로/응답 형태 변경 없음. 기준 https://app.notion.com/p/3ebace1670c6806c8199cde33ebfbdfa
- 배운 개념: 경로 검색의 소요시간과 차량의 실시간 도착예정은 다른 데이터이며 정류장·노선·방향 ID를 정확히 연결해야 한다.
- 다음: D02 공급자 검증 및 PM 답변 반영. 지역 경계/타 지역 통과·환승 정책도 검증 시 확정.

### 2026-10-02 — F00-02 상태 API와 React 서버 연결 확인
- 요청: 사용자 지시로 D01 동기화 상태를 먼저 검증한 뒤 F00-02를 구현.
- 동기화 검증: D01 관련 로컬 문서(meeting_api.md·database_schema.md·api_contract.md·todo.md·feature_breakdown.md)가 이전 작업에서 이미 갱신돼 있음을 파일 재조회로 확인. 로컬 명세 추가 변경 없음. App.jsx 계정 안내 문구 "로그인 방식은 아직 정하지 않았어요"는 D01 확정과 어긋나 "이메일·비밀번호 로그인으로 만들기로 했어요…"로 수정(UI 문구만, 계약 영향 없음).
- 변경 파일: backend/app/main.py(GET /api/v1/health 추가), frontend/vite.config.js(개발 프록시 /api → 127.0.0.1:8000), frontend/src/App.jsx(설정 화면 '서버 연결' 카드·ServerCheck 컴포넌트·계정 문구), frontend/src/App.test.jsx(성공·실패 테스트 2개 추가), todo.md·feature_breakdown.md(F00-02 체크).
- 구현 내용: 계약 01절대로 200 {data:{status,server_time}, meta:{request_id,server_time}}과 X-Request-ID 헤더 반환. DB·키 등 내부 정보 미노출. 화면은 로딩·성공(연결됨·확인 시각)·실패(연결 불가 안내·다시 확인하기) 상태를 role=status로 전달. 기존 CSS 클래스만 재사용해 새 공통 스타일 없음(design_guide.md 변경 없음).
- 검증: uvicorn 기동 후 Invoke-WebRequest로 200, X-Request-ID와 meta.request_id 일치, 본문 {"data":{"status":"ok","server_time":"...Z"},"meta":{...}} 확인. vitest 7개 전부 통과(기존 5+신규 2). npm run build 통과. Edge 헤드리스 실제 브라우저로 데스크톱 1440×900·모바일 390×844 설정 화면 캡처: 클릭 후 '● 연결됨 · 확인 시각' 표시, 텍스트 넘침·요소 겹침 없음, 기존 흰 카드 체계와 일치. 백엔드→Vite 프록시→화면 전구간 실호출로 확인.
- 명세 영향: API 계약 변경 없음(기존 GET /health 계약을 그대로 구현). Notion 수정 불필요. 단 이 세션은 Notion 직접 접근 불가(웹 로그인 장벽, MCP·API 키 없음)여서 명세는 같은 날 이전 작업에서 v0.9로 재조회·전문 대조가 끝난 api_contract.md 로컬 복사본을 기준으로 확인했다. 미확인 범위: 마지막 Notion 재조회 이후 원본 변경 여부. 다음 Notion 접속 시 01절 GET /health 행과 구현 일치를 재확인할 것.
- 배운 개념: 로그인 없이 호출하는 상태 API는 공통 응답 형식(data/meta)과 X-Request-ID를 처음부터 지켜야 이후 기능이 같은 모양으로 붙는다. Vite 개발 프록시는 CORS 설정 없이 같은 출처처럼 요청을 전달한다.
- 남은 문제: F00-03(공통 API 클라이언트·request_id 화면 표시)·F00-04(요청 완료·오류 로그, 환경 변수 예시·실행 안내) 미완료. 백엔드 공통 오류 응답과 요청 로그 미들웨어도 F00-03/04 범위. Notion 연결 수단이 생기면 원문 재조회 필요.

### 2026-10-02 — 로컬 API 명세 문서와 Notion 원문 동기화 확인
- 요청: 사용자가 로컬의 API 명세 md 문서들과 Notion 명세서의 동기화 상태 확인을 요청.
- 접근 상태: 이 세션에서 Notion MCP가 연결되어 fetch·search 사용 가능으로 확인. 이전 세션의 "Notion 직접 접근 불가" 상태는 해소됐고, v0.9 원문(18절·변경 이력 포함 1,248줄)을 재조회했다.
- 검증 결과:
  - api_contract.md ↔ Notion v0.9: 본문 전체 diff에서 차이는 Notion 전용 목차 매크로 1줄과 파일 끝 개행뿐. 18개 절 구조·버전 표기(0.9 · 2026-10-02)·변경 이력까지 동일. 내용 완전 동기화.
  - provider_plan.md ↔ Notion 18절: 불릿 전 문장 일치. 로컬의 "선정 이유와 대안"·"F01 검증 체크리스트"·출처 절은 Notion에 없는 로컬 전용 보충이다.
  - meeting_api.md(대응 Notion v0.8 표기): v0.9 변경은 18절 신설과 1절 요약(서울·경기 확정, 공급자 추천안)뿐이라 근거인 16절 본문은 변화 없음. 문서 내 지역 관련 참조 0건(grep 확인)으로 v0.9 내용과 충돌 없음.
  - auth_api.md(Notion v0.8 17절 기반): 17절은 v0.9에서 변경 없음. 92행 "다음 착수 전 결정은 D02"는 D02-01/02 완료 후에도 공급자 최종 선정·AI 공급자 확인 잔여로 여전히 유효하다.
- 잔여 항목 해소: 앞 기록의 "다음 Notion 접속 시 01절 GET /health 행과 구현 일치 재확인"을 수행. Notion 4절 GET /health 행(인증 불필요·입력 없음·200 status/server_time·내부 정보 미노출)과 backend/app/main.py 구현 일치 확인.
- 명세 영향: 없음. 동기화 확인만 수행했으므로 Notion·로컬 명세 모두 수정하지 않았다. 기준 https://app.notion.com/p/3ebace1670c6806c8199cde33ebfbdfa
- 다음: 이후 계약 변경 작업부터는 Notion 원문을 직접 확인·갱신하는 절차를 복원한다. 남은 작업은 F00-03~04 또는 D02-03~04(착수 시 사용자와 순서 확인).

### 2026-10-06 — F17 자연어 일정 입력 기획 추가
- 요청: 자연어를 날짜·시간·반복 조건으로 변환하는 AI 기능을 기획에 추가.
- 변경: natural_language_schedule.md 신규; planning.md, ai_prompts.md, feature_breakdown.md, todo.md, meeting_plan.md, screen_plan.md, logging.md, README.md, api_contract.md.
- 계약: POST /schedule-interpretations 설계 초안과 확인 카드·누락 질문·사용자 확인 후 기존 생성 API 흐름 추가. 기존 도보/개인화/일정 생성 계약 유지. 상세 제한·컨텍스트 구현은 후속 확정.
- Notion v0.10 최신 확인 후 관련 추가만 적용, v0.11 19절 저장 재조회 확인. 전체 57622문자 로컬 복사본 분할 내용/길이 대조 통과. 카카오맵 선정 등 기존 변경 보존.
- 검증: F17 TODO 및 기능 목록 동일 항목, 관련 문서 참조 존재 확인. 코드/DB/UI 변경과 모델 평가/앱 테스트는 수행하지 않음. F17 구현 체크는 전부 미완료.
- 배운 개념: AI의 자연어 해석, 서버의 달력 검증, 사용자의 저장 확인은 서로 다른 단계다. 날짜 경계에서 상대 표현이 바뀌지 않도록 기준 시각을 고정한다.
- 남은 일: D02-04 모델/전송 조건, D03 보관 정책, 기존 인증·루틴/약속 기능 및 F17 구현·평가. 기존 착수 전 결정 순서 유지.
- 기준: https://app.notion.com/p/3ebace1670c6806c8199cde33ebfbdfa

### 2026-10-07 — F04-05 경로 없음·지원 범위·구간 정보 부족
- 목표: 사용자 요청으로 F04-04를 보류하고 F04-05 안내/복구를 진행. 최신 origin/main63674ac에서 codex/journey-unavailable 생성, 미병합 비교 화면33efcec를 fast-forward 통합했다. main/MR 생성·병합은 수행하지 않는다.
- 변경: backend/app/journey_provider.py의 환승 제한 전체 제외에서 NO_ROUTE 중복 제거. frontend/src/components/JourneyUnavailable.jsx 신규, JourneyComparison.jsx의 정상 빈 후보/지역 밖 재선택과 worker 오류 처리, JourneyCandidates.jsx의 미확인 근거/알 수 없는 사유 안전 표시, styles.css의 비교 화면 범위 본문 대비·버튼44px/줄바꿈. 관련 backend/tests/test_journeys.py·frontend/tests/components/JourneyComparison.test.jsx 보완.
- 계약: Notion v0.43 5.2.6·변경 이력 추가 및 재조회 저장 확인, api_contract.md 전체 동기화. journey_api.md/planning.md/screen_plan.md/design_guide.md/TODO/기능 목록 동기화. 기존 경로/필드/권한/보관/DB DDL 유지. 무경로 사유 정밀화와 화면 흐름 변경.
- 발견/수정: 최초 지역 밖 테스트가422 기대/실제202로 실패했다. 코드에서 지역 확인은 worker 단계임을 확인해 계약을POST202→GET200 failed/UNSUPPORTED_REGION으로 바로잡고 프론트의 worker 실패도 재선택 상태로 연결했다. POST /origin-validations의422와 구분한다. 재검증 완료.
- 실제 검증: 프론트13파일101개·프로덕션 빌드1900모듈 통과. 백엔드 unittest117개(37.164초) 통과: 격리 PostgreSQL/ASGI·모의 공급자 양 끝 지역 밖 결과/경로 공급자 미호출, NO_RESULTS/EQUAL_POINTS/노드없음/전체환승제외 사유, 기존 auth/소유권/멱등/만료 회귀. 프론트 재선택 새 키/복수·미지 사유/지역 실패 입력 제거/정보 부족 후보 유지 검증.
- 시각 검증: 임시 합성 fixture 화면에서 PC1440×1000/모바일390×844 무경로/지점/환승/지역 밖 안내와 구간 상세/Enter를 확인했다. 읽기전용 DOM 검사 가로넘침없음(390/375), 최종 버튼 전부44px 이상, 콘솔error0. 실제 홈/비교 입력 화면 PC/모바일 회귀도 확인. 임시 f0405-qa.html/jsx 삭제 및 탭/viewport 정리. screenshots f0405-unavailable-desktop.png/mobile.png는 워크스페이스 외 visualizations에 보관.
- 검증 한계: 무경로/지역 밖 실제 카카오 호출·실기기GPS·실제 환승/운행·물리방향/출입구/플랫폼·AI는 검증하지 않았다. 시각 검증은 합성 상태이며 실공급자 E2E로 보고하지 않는다. 부족 근거를0/검증됨으로 채우지 않는다.
- 실행 반영: 명령행을 확인한 기존 프로젝트 uvicorn을 종료하고 변경 코드로 localhost:8000 재시작, GET /api/v1/health status=ok 확인. Vite는 기존5173 서버의 변경 감지를 사용한다.
- 게시 전 통합: 새로 갱신된 F04-03 병합 main4f94af1을 작업 브랜치에 fast-forward 반영했다. 기존33efcec와4f94af1의 파일 트리는 동일해 검증한 코드 변화/충돌 없음. main 기준 MR에는 F04-05 변경만 포함한다. Notion/로컬 진행 상태 재동기화.
- 배운 개념: 정상 무결과·지원 범위 제한·외부 실패·부분 근거는 별개 상태다. 비동기 접수 HTTP 상태와 작업 결과 상태도 다르며 복구 행동은 실패 위치에 맞춰야 한다.
- 남은 일: F04-04 및 GPS 수치/자동 판정 보류. 사용자MR/병합 후 다음 F05-01 도보 근거 수집, 실제 후보 선택/루틴 저장·출발 안내는 후속.
- 기준: https://app.notion.com/p/3ebace1670c6806c8199cde33ebfbdfa

## 2026-10-07 F06-01 선택 경로 루틴 저장(helpycode/routine-save)

- 목표: 사용자 지시로 F06(출근·퇴근 루틴)을 착수하고 체크리스트 항목마다 helpycode/브랜치로 게시하는 흐름을 시작. F06-01은 선택 경로를 이름과 함께 저장한다. 검색 결과가 24시간 뒤 정리되므로 저장 시점에 후보를 journey_plans 스냅샷으로 복사해 루틴이 계속 참조하게 만든다.
- 변경: backend/migrations/versions/0007_routines.py 신규(journey_plans·routines·routine_creation_keys), backend/app/routines.py 신규(POST /routines 201·GET /routines/{id} 200·멱등·소유권·location_version 검증), backend/app/main.py(라우터·no-store 경로), backend/app/places.py(장소 삭제 시 참조 루틴 참조 해제·needs_attention·version+1), backend/tests/test_routines.py 신규 6개. 프론트는 components/JourneyCandidates.jsx(후보별 저장 버튼·카드 안 이름 입력 패널·저장 완료 표시), JourneyComparison.jsx(POST /routines 호출·응답 검증·멱등 키 보관·기본 이름 '출발 → 도착 통근'), app/App.jsx(저장 토스트·saves 재조회·내 루틴 화면 안내 문구), styles.css(routine-name-panel 스타일 추가), tests/components/JourneyCandidates.test.jsx(루틴 9개 신규)로 구현했다. 저장 버튼 클릭 시 후보 카드 안에서 이름을 입력하고(기본값 미리 채움, 빈 값은 기본 이름 사용) '루틴 저장'으로 확정한다.
- 계약: Notion v0.44로 갱신(3절 루틴 표 F06-01/F06-02/F06-03 단계 표기, 장소 삭제 규칙, 5.3 F06-01 계약 신설, 기존 예시 5.6~5.8 재번호, 변경 이력 추가) 후 재조회로 저장 확인. api_contract.md 전문 동기화, database_schema.md B절에 F06-01 실제 DDL과 차이(목적/구간 분해/유효기간 미정) 기록.
- 발견/수정: 응답 조립을 트랜잭션 밖에서 실행해 psycopg OperationalError(500)가 발생했다. 데이터 조립을 연결이 살아 있는 with 블록 안으로 옮겨 수정하고 재검증했다. 전체 스위트에서 test_expiry가 2회 간헐 실패(만료 기대 404에 200) 후 재실행/단독 실행 통과를 확인했다. 백그라운드 worker 진행과 테스트 UPDATE 사이 경쟁으로 추정하며 F06-01 변경과 무관한 기존 경쟁 가능성이 높아 이후 재확인을 남긴다.
- 실제 검증: 백엔드 unittest 123개(41.8초) 통과 — 저장/상세/재로그인 조회, 스냅샷 내 좌표 미저장, 입력·소유권·만료·버전·참조 오류 코드, 멱등 재현/충돌/삭제 표시, 같은 후보 plan 재사용, 장소 삭제 후 needs_attention 복수 단계. 프론트 테스트 110개(루틴 9개 신규: 저장·멱등·실패 재시도·응답 거부·세션 만료·만료 비활성·재선택 초기화·장소 미선택 차단·사용자 지정 이름 전송과 빈 값 기본 이름 대체)·Vite 빌드 통과. 마이그레이션 up/down roundtrip과 0007_routines head 적용 확인.
- 시각 검증: 실제 카카오 공급자로 Playwright에서 가입→강남역·서울역 저장→실제 경로 검색→이름 입력 패널로 루틴 저장을 수행했다. PC1440×1000에서 후보 표시·저장 패널 기본 이름 '집 → 회사 통근' 확인·'아침 등근길'로 저장·'루틴에 저장했어요' 비활성 표시·토스트 '아침 등근길 루틴을 저장했어요.' 확인. 모바일390×844에서 같은 계정 로그인→후보 조회→이름 패널(가로넘침 0px)→'모바일 출근길' 저장·토스트 확인. 두 화면 모두 콘솔 오류 없음(로그인 전 익명 401 2건은 예상 동작)을 확인했고 스크린샷으로 미색 배경·초록 버튼·둥근 카드 톤 유지를 확인했다. 검증 계정은 임시로 만들었고 코드 변경은 없다. 참고로 편집기 전환 시 진행 중인 위치 검증이 취소되는 앱 동작(의도된 UX) 때문에 스크립트는 각 선택 완료를 기다려야 했다.
- 검증 한계: 루틴 목록/수정/삭제·요일·목표 도착·출발 안내는 이번 범위가 아니다. 실제 재로그인 브라우저 확인은 백엔드 테스트로 대체했고(단위 검증은 수행) 요일 표기·루틴 화면 연동은 F06-02/F06-03에서 검증한다.
- 실행 반영: 명령행으로 기존 uvicorn을 종료하고 변경 코드로 localhost:8000 재시작, GET /api/v1/health 200 확인. Vite는 기존 5173 서버를 사용한다.
- 배운 개념: 검색 결과 자원은 만료 정리 대상이라 참조가 필요한 데이터는 저장 시점에 별도 스냅샷 자원으로 복사해야 한다. 응답 조립에 추가 질의가 필요하면 트랜잭션 안에서 수행해야 한다.
- 남은 일: F06-02 요일·목표 도착 저장, F06-03 목록·선택·수정·삭제, F06-04 복구 안내. 사용자가 helpycode/routine-save를 검토 후 MR 생성·병합한다. Notion 5절의 5.6~5.8 재번호는 예시 절 이동이며 참조 문구는 없음을 확인했다. 2026-10-07 사용자 결정: 홈·내 루틴의 가상 루틴(initialRoutines '평일 출근'·'학교 가는 길')은 지금 유지하고 F06-03에서 실제 API 목록으로 교체하면서 제거한다(사용자 선택).
- 기준: https://app.notion.com/p/3ebace1670c6806c8199cde33ebfbdfa

## 2026-10-07 F06-02 루틴 요일·목표 도착 시각 저장(helpycode/routine-schedule)

- 목표: F06-01로 저장한 루틴에 반복 요일(ISO 1~7)과 선택적 목표 도착 시각(HH:mm, Asia/Seoul)을 저장하고, 저장 후 요일·목표 도착만 바꾸는 일정 PATCH를 제공한다. 이전 세션에서 백엔드·마이그레이션·저장 패널 일부까지 구현된 상태로 터미널이 종료돼 이어서 마무리했다.
- 변경: backend/migrations/versions/0008_routine_schedule.py 신규(routines에 weekdays smallint[] NOT NULL 기본 월~금·CHECK, target_arrival_local_time time, timezone 기본 Asia/Seoul·CHECK), backend/app/routines.py(저장 입력 weekdays 필수·목표 도착 HH:mm 선택 검증, 응답에 weekdays·target_arrival_local_time·timezone 포함, PATCH /routines/{routine_id} 일정 부분: expected_version 불일치 409, 미전송 필드 유지·명시적 null로 목표 삭제, version+1·updated_at 갱신), backend/tests/test_routines.py(요일 빈값/중복/범위/문자열·HH:mm 오류·timezone 입력 차단과 저장·PATCH 테스트 추가, 만료 보정 UPDATE를 과거 시각으로 명시), backend/tests/test_migrations.py(기대 head 0008), frontend/src/components/JourneyCandidates.jsx(저장 패널 반복 요일 토글 기본 월~금·목표 도착 time 입력·요일 0개면 저장 비활성·안내 문구 갱신), frontend/src/components/JourneyComparison.jsx(validSchedule 헬퍼로 POST 본문에 weekdays·target_arrival_local_time 전송, 응답의 요일·목표·timezone 검증 추가), frontend/src/styles/styles.css(routine-days·day-list 스타일 추가 — 기존 tabs/nav 활성 팔레트 재사용), frontend/tests/components/JourneyCandidates.test.jsx(요일 기본·토글·전체 해제 차단·목표 전달·일정 누락 응답 거부 등 신규 5개 포함).
- 계약: Notion v0.45로 갱신(헤더·상태 줄, 2절 POST/PATCH 행, 5.3 제목·입력·스냅샷·201 응답·PATCH 계약·F06-02 구현/검증 문단, 변경 이력) 후 재조회로 저장 확인(작성 오타 Aisa→Asia 정정 포함). api_contract.md를 Notion 본문과 바이트 일치 방식으로 전문 동기화했다. database_schema.md B절에 0008 적용 기록. POST weekdays 필수 전환은 weekdays 없는 기존 본문이 422가 되는 호환성 변경으로 변경 이력에 명시했다. PATCH는 요일·목표 도착만이며 이름·경로 변경은 F06-03 확장임을 명세에 표기했다.
- 발견/수정: 기존 api_contract.md 사본이 Notion 이스케이프(\~, \{)를 부분적으로 풀어 쓰고 F06-01 프론트 검증 수치가 109개로 개발 일지·Notion(110개)과 달랐다. 이번부터 Notion 원문 본문을 그대로 저장하는 동기화 방식으로 바꿔 다음 대조가 기계적으로 가능하게 했고 todo.md·feature_breakdown.md의 F06-01 수치를 110개로 정정했다. 프론트 테스트에서 getAllByRole은 0개 기대에 예외를 던지므로 queryAllByRole로 바로잡았다.
- 실제 검증: 백엔드 unittest 125개(43.4초) 통과 — 요일·시각·timezone 422 케이스, 저장 응답 weekdays·target·timezone, PATCH 401/403/422/409·미전송 유지·null 삭제·version 증가·타인 404, 마이그레이션 up/down roundtrip(기대 head 0008). 프론트 테스트 114개·Vite 프로덕션 빌드 통과. 로컬 DB에 0008 적용 확인(migrate.py current = 0008_routine_schedule head).
- 시각 검증: tests fixture를 렌더링한 임시 QA 페이지를 Vite+Playwright(Chromium)로 PC1440×1000·모바일390×844에서 확인 — 요일 버튼 7개·기본 월~금 aria-pressed, 금 해제·토 선택 반영, 요일 전부 해제 시 저장 비활성, 목표 도착 08:30 입력 시 저장 전달값 weekdays [1,2,3,4,6]·target '08:30', 기본 저장은 target null, 가로넘침 0px, 콘솔 오류 0, 미색 배경·흰 카드·녹색 강조 기존 톤 유지(스크린샷 확인). 임시 qa_f0602 html/jsx는 삭제했다.
- 검증 한계: 실제 카카오 저장 흐름 재호출은 하지 않았다(공급자·화면 흐름은 F06-01에서 실호출 검증, 이번 변경은 전달 필드 추가). 화면 시각 검증은 합성 fixture 기준이며 실기기는 미확인. 내 루틴 화면 연동·요일 표기는 F06-03에서 실제 API 목록으로 교체하며 검증한다.
- 실행 반영: 시각 검증을 위해 Vite 개발 서버를 임시 실행 후 종료했다. 백엔드는 테스트가 ASGI 레벨에서 검증하며 uvicorn 재시작은 사용자 확인 시점에 맞춰 진행한다.
- 배운 개념: 일정 PATCH에서 '보내지 않으면 유지, 명시적 null이면 삭제'를 구현하려면 Pydantic model_fields_set으로 전송 여부를 구분해야 한다. 부분 수정 계약을 단계(F06-02)로 나눠 도입할 때는 나머지 필드(이름·경로)의 소속 단계를 문서에 명시해 계약이 흐려지지 않게 한다.
- 남은 일: F06-03 루틴 목록·선택·수정·삭제(App.jsx 가상 루틴 '평일 출근'·'학교 가는 길'을 실제 API 목록으로 교체), F06-04 복구 안내. 커밋은 사용자 화면 확인 후 helpycode/routine-schedule에 진행하고 MR 생성·병합은 사용자가 한다.
- 기준: https://app.notion.com/p/3ebace1670c6806c8199cde33ebfbdfa

## 2026-10-07 F06-02 후속: 계정 모달이 경로 비교 화면을 지우던 문제 수정

- 목표: 사용자 확인 중 보고된 "경로 후보 비교에 들어가면 출발지·도착지를 다시 선택해야 하고 그 상태에서 루틴 추가가 안 된다" 문제의 원인 규명과 최소 수정.
- 원인 진단(근거: App.jsx·JourneyComparison.jsx·OriginSelector.jsx 코드와 17:41~17:42 성공한 검색 3건·저장 0건 DB 대조): 1) App.jsx가 `modal==='account'`일 때 JourneyComparison을 언마운트해 도착지·검색 결과·편집 상태가 사라졌고, 출발지는 홈 위치 모달에서만 App 레벨로 저장돼 비교 화면 안에서 고른 출발지는 보존되지 않았다. 2) 출발지 선택은 서버 TTL 최대 10분(origin-validations expires_at)이라 로그인에 시간을 쓰면 만료됐다. 3) 경로 검색 결과 만료(5분)는 재조회로 같은 출발지·도착지로 복구되므로 재선택 원인이 아니었다. 백엔드 저장 API 자체는 정상(아래 실증).
- 서버 원인 별건: 사용자가 사용하던 8000 포트를 이전 세션의 낡은 백엔드(F06-01 코드, 시스템 Python, 15:33 시작)가 점유하고 있어 새 프론트가 보낸 weekdays를 모르는 필드로 거부했다. 낡은 프로세스를 종료하고 venv로 새 백엔드를 교체(17:10)했고 PATCH /routines/... 422로 새 계약 서빙을 확인했다. 백그라운드 작업 중단 표시는 포트 충돌 때문이었다.
- 실제 저장 실증(사용자 확인용): 실제 카카오 공급자로 가입→로그인→강남역/서울역 장소 저장→경로 검색(후보 15)→루틴 저장 201→상세 200까지 성공. DB에 'E2E 저장확인'(weekdays [1,2,3,4,5], 목표도착 08:30, Asia/Seoul, 17:16:56) 기록 확인. 사용자의 마지막 저장 시도가 이 시점 이후 없음을 확인.
- 수정: App.jsx 93행의 `modal!=='account'` 조건 제거. 계정 모달이 열려 있어도 비교 화면(출발지·도착지·검색 결과·저장 패널)이 유지되고, 로그인 후 조회 버튼으로 이어서 진행한다. 익명 감지는 조회 시 401(AUTH_REQUIRED)로 이뤄지므로 별도 복구 로직이 필요 없었다. API 계약 영향 없음(명세 변경 없음).
- 테스트: App.test.jsx에 "계정 모달을 열었다 닫아도 출발지·도착지 선택이 유지된다" 추가(OriginSelector 목킹, /me 401 스텁). 프론트 115개 통과. vi.mock은 모듈 최상위에 있어야 한다는 점, <dialog>에 접근 가능한 이름이 없어 이름 미지정 조회로 바로잡았다.
- 시각 검증: Playwright(Chromium) 실제 화면으로 PC1440×1000(사이드바 프로필→모달)과 모바일390×844(출발지 선택 편집기의 로그인하기→모달)에서 모달 뒤 '경로 후보 조회' 버튼 유지·닫은 뒤에도 유지·가로넘침 0px·콘솔 오류 0 확인. 모바일 스크린샷으로 미색/녹색 톤·잘림 없음 확인. 모바일은 사이드바가 숨겨져(.sidebar display:none) 비교 화면 위 모달 진입은 편집기/조회 실패 경로만 존재한다(기존 설계 유지).
- 배운 개념: 조건부 렌더링으로 모달을 "화면 대체"로 쓰면 모달을 여는 순간 화면 상태가 사라진다. 모달은 오버레이(dialog)로 두고 화면은 살려두는 것이 상태 보존의 기본이다. 백엔드 교체 후에는 실제 포트 점유자(프로세스 시작 시간·신규 라우트 응답)로 코드 버전을 확인해야 했다.
- 남은 일: F06-03 루틴 목록·수정·삭제(내 루틴 화면 실제 API 연결 — "저장했는데 내 루틴에 안 보인다" 체감의 근본 해소), F06-04 복구 안내. 출발지 10분 만료와 페이지 이동 시 상태 초기화는 이번 범위 밖(사용자 승인 시 후속).
- 기준: https://app.notion.com/p/3ebace1670c6806c8199cde33ebfbdfa


## 2026-10-08 F06-03 DB·루틴 저장 진단

- 목표: 사용자가 F06-03 진행 중 실제 DB 연결 여부와 경로 후보를 루틴에 추가해도 반영되지 않는 원인 확인을 요청했다. 이번 작업은 연결·저장 진단이며 F06-03 전체 구현 완료를 의미하지 않는다.
- 작업 상태: 현재 helpycode/routine-schedule, HEAD 및 최신 origin/main 모두2248346. 기존 미커밋 F06-02 코드/문서/0008 마이그레이션이 존재하며 그대로 보존했다. 기능 코드 변경·새 기능 브랜치·기존 변경 커밋/푸시·MR 생성/병합은 하지 않았다. 변경 파일은 이번 진단을 추가한 todo.md 및 development_log.md다.
- 명세: Notion API 명세 v0.45(마지막 편집2026-10-07T08:05:00.054Z)를 연결 도구로 읽고5.3 및 루틴 API 목록과 로컬 planning.md·feature_breakdown.md·관련 개발 일지/화면/개인화/프롬프트/로깅 문서를 확인했다. POST 저장 및 GET 상세/PATCH 일정은 구현, GET 목록/이름·경로 수정/DELETE는 F06-03 후속이라는 명세와 실제 코드가 일치한다. 진단·실행 환경 복구만 수행했으므로 계약 변경 및 Notion 수정 없음.
- 실제 DB 확인: backend/.venv/Scripts/python.exe backend/check_db.py 성공, PostgreSQL17.11. migrate.py current는0008_routine_schedule(head). 읽기전용 SQL로 routines8건·journey_plans8건·journey_searches15건 확인. 최신 기존 저장은2026-10-07 17:16:56 KST이며 weekdays 월~금·목표 도착 있음·active다. 이름/계정/주소/연결 비밀은 출력·기록하지 않았다.
- 원인1: App.jsx initialRoutines와 useState(initialRoutines)가 홈/내 루틴의 가상2개를 사용한다. JourneyComparison.saveRoutine은 POST /api/v1/routines를 호출하지만 App.jsx onRoutineSaved는 토스트/로그만 처리하며 setRoutines 또는 목록 재조회가 없다. DB 저장 성공과 화면 목록 반영이 분리돼 있어 저장해도 목록에 나타나지 않는다.
- 원인2: 내 루틴의 추가/수정 RoutineForm은 setRoutines로 브라우저 메모리만 바꾼다. 경로 후보 저장 API와 다른 데모 흐름이고 새로고침하면 사라진다. 목록 API GET /api/v1/routines 자체가 없으며 실행 서버 요청은405 METHOD_NOT_ALLOWED다.
- 실행 상태: 점검 시127.0.0.1:8000 및 localhost:5173 HTTP 접속 모두 실패했다. DB 자체는 실행 중이므로 DB 설정/데이터/마이그레이션을 변경하지 않았다. 프로젝트 venv로 최신 uvicorn을8000에, 현재 Vite를5173에 숨김 창으로 실행했다. 이후 backend health200, frontend HTML200, Vite 프록시 /api/v1/health200 확인. OpenAPI에서 POST /routines 및 GET/PATCH /routines/{id}, RoutineInput의 weekdays/target_arrival_local_time 제공 확인. runtime-check stdout/stderr 로그는 기존 *.log 무시 규칙으로 Git 제외된다.
- 실제 검증: 백엔드 test_routines.py8개(9.438초) 통과. 실제 PostgreSQL의 테스트 전용 격리 스키마에 합성 공급자 경로를 저장해 POST201·GET200·재로그인 조회·멱등·소유권·장소 삭제 연동·일정 PATCH 검증. 프론트 tests/components/JourneyCandidates.test.jsx13개 통과(저장 본문·요일/목표 시각·성공/실패/만료 등). 실제 카카오/사용자 계정 저장 재현 또는 브라우저 시각 검증은 이번에 수행하지 않았다. 사용자 특정 저장 시도의 HTTP 오류는 캡처하지 않았으므로 모든 실패를 목록 문제로 단정하지 않는다.
- 배운 개념: DB 연결 성공, 저장 API 성공, 화면 목록 동기화는 각각 확인해야 한다. 저장201을 받더라도 목록이 데모 상태이거나 성공 후 재조회가 없으면 화면에 반영되지 않는다. health200만으로 DB 연결 정상이라고 판단하지 않는다.
- 남은 일/다음 작업: F06-03은 [ ] 유지. 기존 F06-02 변경 검토·게시 후 본인 GET /routines(명세의 cursor/limit), 홈·내 루틴 실제 목록·저장 후 갱신, 추가/수정/삭제 API 연결 및 빈 상태/인증 만료/오류를 구현하고 검증해야 한다. 확인된 현재 저장 조건은 출발·도착 모두 본인 저장 장소, 검색5분 이내, 검색 당시 location_version 유지다. 실제 사용자 저장 오류는 해당 요청 상태/오류 코드로 별도 구분한다.
- 기준: https://app.notion.com/p/3ebace1670c6806c8199cde33ebfbdfa


## 2026-10-08 F06-03 실제 루틴 목록·선택·수정·삭제 (codex/routine-management)

- 목표: 경로를 저장해도 내 루틴에 보이지 않던 문제를 해결하고, 목록·선택·이름/요일/목표 도착 수정·경로 교체·삭제를 실제 계정 DB에 연결한다.
- Git 기반: 최신 origin/main 2248346을 확인했다. 기존 미커밋 F06-02 변경과 사전 진단 문서를 백엔드125개·프론트115개/빌드로 검증하고 helpycode/routine-schedule의2a51611로 보존했다. 최신 main에서 codex/routine-management를 만들고 선행 커밋을 반영(f1431d1)했다. main에 F06-02가 아직 없어 이 브랜치에 포함된다. MR 생성/병합은 사용자가 수행한다.
- 백엔드 변경: backend/app/routines.py에 본인 GET 목록(limit 기본20/최대100, cursor 소유권, created_at DESC/id DESC), 이름·경로 참조4개를 받는 PATCH, DELETE204를 추가했다. 이름/요일 null·일부 경로 참조·검색 방향 불일치를 차단하고 기존 후보/5분 만료/location_version/expected_version 검사를 유지했다. 실패는 트랜잭션 전체를 취소한다. selected_plan으로 저장 로직을 재사용하며 회원별 트랜잭션 잠금과 공유 plan 잠금으로 여러 세션의 쓰기를 직렬화한다. 삭제·교체 후 참조 없는 plan만 지우고 생성 키의 삭제 표시는24시간 유지한다. DB0008을 재사용해 추가 DDL은 없다.
- 프론트 변경: frontend/src/lib/routines.js(목록/페이지/응답 검증/중단), components/RoutinesPanel.jsx(목록·요약·선택·수정·삭제 확인/취소), app/App.jsx(실제 목록과 저장 후 갱신·가상 initialRoutines/RoutineForm 제거), AccountForm.jsx(로그인/로그아웃 콜백), JourneyComparison.jsx(경로 교체 PATCH·기존 일정 기본값·실패 재시도 키 유지), JourneyCandidates.jsx(교체 버튼/일정 기본값), styles.css(기존 카드·팔레트·줄바꿈/44px 행동)를 변경했다. 홈에는 실제 저장 후보의 예상 시간/반복 일정과 출발 안내 준비 상태를 표시하며 가상 버스 도착·출발 숫자·이동 시작은 제거했다. 내비게이션과 설정 톤은 유지한다.
- 테스트 변경: backend/tests/test_routines.py에4개를 추가(총12개)해 목록/페이지/입력/소유권·이름/방향/원자적 교체/버전·삭제/공유 plan/생성키·삭제 장소 복구/만료를 검증했다. frontend/tests/app/App.routines.test.jsx 신규9개와 JourneyCandidates.test.jsx 신규2개로 실제 목록·선택·새로고침·추가 후 갱신·수정/삭제/계정 전환·충돌·추가 페이지·needs_attention·요청 키 재시도·교체 PATCH를 검증했다. App.test.jsx/App.origin.test.jsx의 제거된 가상 이동 테스트는 실제 빈 상태/개인 위치/계정 모달/서버 확인으로 정리했다.
- 최종 실행 결과: 백엔드 unittest129개(50.585초), 프론트15파일121개(9.44초), Vite 프로덕션 빌드1902모듈 통과. git diff --check 통과. PostgreSQL17.11/head0008은 사전 진단으로 확인했고 실제 HTTP 저장에서도 DB 연결을 확인했다.
- 발견/수정: cursor에 장소 공통 헬퍼를 쓰면 잘못된 형식도404라 명세422와 달랐다. UUID 검증과 소유권404를 분리했다. UUID4 내림차순은 생성순이 아니므로 신규 저장이 첫 페이지에 보이도록 created_at/id 최신순으로 명세·코드·테스트를 맞췄다. 저장 키가 성공 후에만 남아 응답 유실 재시도에서 중복 저장 가능성이 있어 호출 전에 본문/키를 보관하도록 수정했다.
- 기존 회귀 테스트: 첫 전체 검증에서 test_expiry_restart_and_late_worker_cannot_resurrect가404 기대/200으로 실패했다(앞선 F06-01 일지에 동일 간헐 실패 기록). DB now()를 앱 UTC와 즉시 비교하면 시계 차이 때문에 만료가 확실하지 않다. backend/tests/test_journeys.py의 합성 expires_at/worker_deadline/job_expires_at을 now()-1hour로 바꿔 명확한 과거를 검증했고 최종129개 통과했다. 서비스 코드와 만료 정책은 유지했다.
- 실제 DB/HTTP 검증: 전용 example.invalid 검증 계정에 공개 역 좌표의 테스트 장소와 합성 검색 후보로2루틴을 준비했다. POST201·GET목록200 후 실제 브라우저에서 로그인·목록·선택·이름/요일 PATCH·키보드 시간 수정09:30·새로고침 유지를 확인했다. 실제 카카오 강남역~서울역15후보 중 기존 루틴을2번째 지하철 후보로 PATCH200하고 목표08:30/화·목 유지·환승1/약36분을 홈에서 확인했다. 실제 후보로 신규 POST201·목록3개/신규 첫 항목도 확인했다. 검증용3루틴만 HTTP DELETE204로 지워 빈 목록과 브라우저 빈 상태를 확인했다. 생성 계정 ID와 검증 이메일을 대조해 해당 데이터만 정리했고 기존 사용자 루틴8건은 유지됐다.
- 시각/회귀 검증: PC1440×1000·모바일390×844에서 목록/수정 폼·요일·삭제 확인/취소(취소 초기 포커스)·선택/홈·교체 패널을 확인했다. 모바일 가로 넘침0·콘솔error0, 기존 미색/녹색/흰 카드/선형 아이콘을 유지한다. 설정의 장소/여유/계정 화면도 두 크기로 확인했다. 로그아웃 후 이전 목록 제거와 로그인 안내를 확인하고 viewport를 원복했다. 스크린샷은 visualizations의 f0603-routines-desktop.png와 f0603-home-mobile.png에 보관한다. 실제 브라우저의 삭제 최종 버튼은 누르지 않았으며 UI 확인/취소·실제HTTP204·프론트 확인 테스트로 검증했다.
- 실행 반영: 이전 프로젝트 uvicorn의 명령행/경로/자식PID를 확인 후 교체했다. 제한 환경 서버에서는 카카오 연결이 실패했지만 네트워크 가능한 최소 호출에서OK/15후보여서 같은 인증 설정·localhost8000으로 실행 환경을 교체했고 브라우저 조회가 성공했다. 현재 프로젝트 venv launcher15148·Vite5173 유지. 키/쿠키/사용자 이메일은 일지에 기록하지 않았다.
- 명세/문서: 착수 전 Notion 최신v0.45와 관련 로컬 문서를 확인했다. 구현 전 v0.46의5.3.1 계약·변경 이력을 추가하고 최신 생성순/방향 검증을 보완했다. 최종 API 목록·입력 예시·공통 구현 상태·검증·변경 이력을 갱신한 후 재조회해 저장을 확인했다. api_contract.md는 최종 Notion 본문과 기계 비교해 동기화했다. routine_api.md 신규, planning.md/screen_plan.md/design_guide.md/database_schema.md/README/TODO/feature_breakdown.md 동기화. 기존 POST/상세/일정 PATCH 응답은 유지하며 선택적 이름/경로 필드와 목록/DELETE를 추가했다.
- 배운 개념: 저장 성공과 목록 갱신은 별개다. UUID 정렬은 생성순이 아니므로 생성 시각과ID를 함께 페이지 경계로 써야 한다. 이름/일정과 경로 교체는 같은 버전 검사·원자적 트랜잭션으로 다루고 공유 스냅샷은 마지막 참조가 사라질 때 정리한다. 응답 유실은 저장 실패와 다르므로 생성 키를 요청 전에 보관한다.
- 남은 일: F06-04 장소/경로 변경 시 복구 안내 확장, F05 도보/AI와 F07 실시간 출발 안내·이동 기록·실기기GPS는 후속이다. 선택은 화면 세션에서 유지하고 새로고침 시 첫 항목이 기본이다. 사용자 검토/MR·병합 후 다음 기능을 최신 main에서 시작한다.
- 기준: https://app.notion.com/p/3ebace1670c6806c8199cde33ebfbdfa


## 2026-10-08 F06-03 후속: 저장 클릭 시 요청 없이 후보가 사라지는 문제

- 사용자 보고: 이 경로를 루틴에 저장 → 루틴 저장을 눌러도 백엔드 호출 없이 경로 후보가 사라졌다.
- 화면에서 해결하는 순서: 새로고침 → 출발지/도착지의 저장 장소 선택 → 서로 다른 본인 저장 장소2개 선택 → 경로 후보 재조회 → 이 경로를 루틴에 저장 → 이름/요일/목표 시각 확인 → 루틴 저장. 저장한 장소가 없으면 내 설정의 장소 관리에서 먼저 등록한다.
- 원인: JourneyCandidates의 저장 버튼은 이름/콜백 존재만 검사하고, JourneyComparison.saveRoutine은 지도 핀/현재 위치의 placeRef가 없으면 SEARCH_EXPIRED를 호출했다. 따라서 프론트가 요청 전에 검색을 만료 처리했다. 양 끝이 저장 장소인 검증은 통과했지만 이전의 '저장 장소 없으면 저장 차단' 테스트는 후보가 없는 초기 화면만 검사해 이 조합을 놓쳤다.
- 재현 근거: 수정 전 회귀 재현 테스트에서 지도 출발→저장 도착의 실제 후보를 띄우고 저장 버튼을 클릭하자 API 호출 수 증가0·후보 제거·만료 안내를 확인했다. 이후 기대 동작 테스트5조합(지도/저장, 현재/저장, 저장/지도, 저장/현재, 지도/지도)과 저장 장소 복구 테스트가 수정 전6개 실패하는 것을 확인한 뒤 구현했다.
- 변경 파일: frontend/src/components/JourneyComparison.jsx(저장 가능 조건·후보 버튼 연결·저장 전 오류 안내·저장 장소 바로 선택·내 장소 관리), OriginSelector.jsx(initialMode로 저장 장소 탭 시작), app/App.jsx(내 설정 이동 연결), styles.css(안내 버튼 줄바꿈), tests/components/JourneyCandidates.test.jsx(혼합 입력5개와 실제 POST 복구1개), OriginSelector.test.jsx(저장 탭 직접 시작/GPS 미호출1개). 기타 문서는 TODO/기능 목록·screen_plan/design_guide/routine_api 및 이 일지다.
- 수정 행동: 양 끝이 서로 다른 본인 저장 장소일 때만 저장 버튼을 표시한다. 지도/현재 위치의 후보는 유지하고 저장 장소 선택을 먼저 안내한다. 저장 함수의 방어 검사도 이 입력을 만료로 처리하지 않으며 잘못된 일정/같은 장소에는 구체적 안내를 남긴다. 실제 검색 만료300초 정책은 유지한다. 장소 자동 저장이나 근접 장소 추정은 도입하지 않았다.
- 실제 검증: 프론트15파일128개(8.22초) 및 Vite1902모듈 빌드 통과, diff --check 통과. 수정 전 재현용 임시 테스트는 최종 기대 동작 회귀 테스트로 교체했다. 백엔드/API 코드는 변경하지 않아 이번에 전체 백엔드 테스트를 재실행하지 않았다(선행 F06-03의129개 통과 기록과 구분).
- 실제 브라우저/DB 검증: 임시 QA 페이지에서 공개 역 좌표의 지도 출발점과 전용 검증 계정 저장 도착지를 선택해 실제 카카오15후보 조회를 수행했다. 후보 유지·저장 버튼0·만료 오류0을 확인했다. 안내의 출발지 저장 장소 선택을 누르면 저장 탭이 바로 열리고, 출발역을 저장 장소로 선택한 뒤 실제 후보를 재조회했다. 모바일에서 후보 저장 패널→루틴 저장을 실제 클릭해 /auth/csrf200 및 POST /api/v1/routines201 로그(req_0a976d1bb6db4a7c9e69db7253ce6815)와 DB루틴1행·월~금·active를 확인했다. 실제 App 홈에서도 저장된 루틴과 환승2/약31분이 보였다.
- 시각 검증: 안내/선택 버튼과 기존 후보 저장 폼을 PC1440×1000·모바일390×844로 확인했다. 가로 넘침0·콘솔error0, 기존 미색/초록/흰 카드 유지. screenshot routine-save-fix-db-success.png 및 routine-save-fix-success-mobile.png는 visualizations에 보관한다. 임시 QA html/jsx와 전용 계정/데이터는 ID·검증 이메일을 대조해 정리했고 기존 루틴8건은 유지됐다. 로그아웃·임시 탭 종료·viewport 원복. 실제 기기GPS는 미검증이며 지도 출발점은 합성 입력이다.
- 명세: 최신 Notion v0.46의5.3 저장 장소 입력 계약과 관련 로컬 문서를 착수 전 확인했다. 기존 명세/화면 기획대로 버튼 조건을 바로잡는 버그 수정으로 API/필드/인증/저장/계산 정책 변경이 없어 Notion 계약 변경 없음. 게시 전 최신 명세를 재확인한다.
- Git: 최신 origin/main2248346에서 codex/routine-save-eligibility 생성, 미병합 F06-02·03을 fc83bcd/9875549로 반영한 뒤 수정했다. 수정 커밋9f8c401을 origin/codex/routine-save-eligibility에 푸시 완료했다. MR 생성/병합은 하지 않았다.
- 배운 개념: 화면의 버튼 표시 조건과 저장 함수의 필수 조건을 일치시켜야 한다. 입력 종류가 다른 문제를 정보 만료로 분류하면 요청도 보내지 않고 정상 결과를 지운다. 테스트는 비어 있는 초기 화면 대신 실제 후보가 표시된 혼합 입력과 복구 경로를 검증해야 한다.
- 남은 일: F06-04 복구 안내 확장과 F05/F07 도보·실시간 안내는 기존 후속 상태다. 현재 루틴 저장은 본인 저장 장소 간 경로만 지원한다.
- 기준: https://app.notion.com/p/3ebace1670c6806c8199cde33ebfbdfa


## 2026-10-08 F06-03a 루틴 등록 중 장소 저장·선택 (codex/routine-inline-places)

- 목표: 첫 사용자가 루틴을 추가할 때 내 설정으로 이동해 장소를 먼저 저장하는 불편을 줄인다. 같은 출발·도착 선택 화면에서 주소 검색·명시 저장·해당 지점 선택까지 이어간다.
- Git 기반: 최신 origin/main2248346에서 codex/routine-inline-places를 만들고 미병합 codex/routine-save-eligibility를 fast-forward 반영했다(선행 F06-02·03·저장 버튼 수정·일지 포함, ee24032). 사용자 MR 생성/병합 흐름은 유지한다.
- 변경 파일: frontend/src/components/PlacesCard.jsx에 creationOnly·initialLabel/title·onCreated/onAuthError/onBusyChange를 추가해 기존 검색/후보/이름/핀 확인 저장 폼을 재사용했다. 설정의 기본 목록·수정·삭제 동작은 유지하고 생성 전용 모드는 자동 폼 열기/검색 포커스/목록 관리 숨김으로 처리한다. OriginSelector.jsx에는 장소 저장 탭·빈 목록 생성 행동·저장201 이후 기존 origin-validations200 자동 선택·생성 중 취소/방식 전환 차단을 추가했다. JourneyComparison.jsx에는 저장 조건 안내에서 출발/도착 새 장소 저장·처리 중 선택기 닫기 차단을 연결하고 App.jsx의 설정 이동 prop을 제거했다. styles.css는 기존 카드/여백/본문 톤을 재사용하는 선택기 범위 스타일만 추가했다. tests/components/RoutineInlinePlaces.test.jsx 신규6개와 관련 문서를 추가/갱신했다.
- 입력/저장 정책: 주소/장소명 검색 후 후보를 사용자가 선택하고 장소 이름·선택적 출입구/지도 핀을 확인해 명시 저장한다. 생성201 후 본인 place_id/location_version으로 기존 출발지 검증을 호출한다. 성공하면 해당 출발 또는 도착 선택에 반영하고 반대쪽은 보존한다. 장소가 저장됐지만 선택 검증이 실패하면 저장된 목록에서 검증만 재시도한다. 루틴은 후보 선택/저장 확인 전에는 만들지 않는다. 좌표 근접 자동 연결·GPS 자동 저장·새 API·DDL은 추가하지 않았다.
- 통합 테스트6개: 출발/도착 모두 생성→첫 선택 유지→경로/루틴 저장; 빈 목록 생성/취소 미저장; 생성 실패 동일 멱등 키 재시도; 저장 후 선택 검증 실패·재선택·추가 생성 없음; 생성 중 취소/방식 전환/중복 쓰기 차단; 세션 만료 시 폼 폐기/로그인 안내. 실제 OriginSelector·PlacesCard·JourneyComparison을 함께 렌더링하고 API만 대체한다.
- 발견/수정: 초기 구현에서 모든 위치 방식 전환을 busy 중 차단해 기존 GPS 측정 취소 테스트가 실패했다. 신규 장소 생성 중에만 전환을 막고 기존 GPS 방식 변경의 중단 동작은 유지하도록 좁혀 수정했다. 재검증 통과. 생성 폼의 저장 후 검증 실패는 '장소는 저장됐어요' 안내를 붙여 저장 실패와 구분한다.
- 실제 검증: 프론트16파일134개(9.34초) 및 Vite1902모듈 프로덕션 빌드 통과. 기존 PlacesCard 설정/이름/핀/삭제 및 GPS/루틴 저장 회귀 테스트도 포함한다. diff --check 통과. 백엔드/API 코드는 변경하지 않았으며 이번에 백엔드 전체 스위트를 재실행하지 않았다.
- 실제 첫 등록 흐름: saved_places0개 전용 검증 계정으로 실제 App의 내 루틴→추가→출발지 선택→빈 저장 목록→새 장소 저장→강남역 검색/후보 선택/이름 '처음 집'→장소POST201→origin-validations200 자동 선택을 수행했다. 같은 화면에서 도착지 장소 저장→서울역 검색/후보 선택/이름 '처음 회사'→POST201/검증200으로 도착지를 반영했다. 출발지 유지와 내 설정 미이동을 확인했다. 실제 카카오15후보 조회 후 '첫 사용 루틴 검증'을 POST /routines201(req_cca548ee40d74ff49fb96ec843fb3329)로 저장하고 홈 목록 반영·환승1/공급자 약29분을 확인했다. 실제 PostgreSQL에 본인 장소2개/루틴1개가 생성된 것을 SQL로 확인했다.
- 시각/설정 회귀: PC1440×1000 출발 폼·모바일390×844 도착 폼/저장/자동 선택/루틴 저장을 확인했다. 가로 넘침0·콘솔error0, 기존 미색·녹색·흰 카드·얇은 선·Noto Sans KR/lucide 톤 유지. 기존 내 설정의 장소 목록에도 새2개가 표시됐다. 공개 역 주소는 검증 입력이며 실사용 경로/실시간 가능성 보장이 아니다. 인라인 생성의 지도 핀 브라우저 확인과 실기기GPS는 이번에 재실행하지 않았다(기존 재사용 컴포넌트 테스트는 통과).
- 정리/실행: 테스트 계정 ID와 전용 example.invalid 이메일을 대조해 생성 데이터만 정리했고 전용 검증 계정 외 루틴은 건드리지 않았고 정리 후 다른 계정의 루틴9건을 확인했다. 로그아웃·임시 탭 종료·viewport 원복. 기존 Vite5173의 HMR을 사용했고 백엔드8000은 그대로 유지했다. 스크린샷은 visualizations의 routine-inline-place-desktop.png / routine-inline-place-mobile.png / routine-inline-success-mobile.png에 보관했다. 개인 키·쿠키·사용자 이메일은 일지에 기록하지 않았다.
- 명세 동기화: 착수 전 최신 Notion v0.46 및 관련 로컬 문서를 확인했다. 사용자 흐름 확장이므로 구현 전 v0.47의5.3.2/변경 이력에 기존 장소 API 재사용·저장 후 선택·실패/취소·반대쪽 유지·호환성 정책을 추가했다. 최종 구현/검증 상태·공통 상태·변경 이력을 갱신하고 재조회로 저장 확인, api_contract.md를 Notion 최종 본문과 기계 비교해 동기화했다. planning/screen_plan/design_guide/routine_api/frontend README·TODO·feature_breakdown을 함께 갱신했다. 기존 API 경로/필드/인증/CSRF/멱등/보관/시간/계산·DB 스키마와 클라이언트 호환성은 유지한다.
- 배운 개념: 같은 저장 로직을 생성 전용 화면으로 재사용하면 설정과 등록 흐름의 계약이 갈라지지 않는다. 장소 저장 성공과 지점 선택 검증은 별개 단계다. 저장201 이후 검증만 실패했다면 재생성 대신 같은 place_id를 다시 검증해야 중복 장소를 막을 수 있다. 새 흐름의 중복 클릭 차단 때문에 기존 GPS 취소까지 막지 않도록 범위를 좁힌다.
- 남은 일: 사용자 검토/MR·병합 후 F06-04 복구 안내 확장 및 F05/F07 도보·실시간 출발 안내는 기존 후속 상태다. 이번 작업은 F06-03a 완료이며 장소 저장과 루틴 생성의 명시 확인을 유지한다.
- 기준: https://app.notion.com/p/3ebace1670c6806c8199cde33ebfbdfa
