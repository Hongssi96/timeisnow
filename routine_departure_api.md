# 루틴 선택 → 최신 첫 출발 안내 — F07-02a-1

2026-10-14 · Notion v0.75: https://app.notion.com/p/3ebace1670c6806c8199cde33ebfbdfa

담당: 이 에이전트는 루틴 최신 출발 연결, 약속·참여자/채팅은 사용자 지정 다른 LLM.

POST /api/v1/routines/{routine_id}/departure-searches는 쿠키본인·Origin/CSRF·선택적 Idempotency-Key와 expected_version 양수정수만 받는다. 서버의 활성 루틴/현재 저장장소/위치버전으로 depart_now 검색을 만든다. 202는 기존search_id/job_id/status에 routine_id/routine_version을 추가한다. 기존 검색10회/분·동시본인2/전체8·300초/worker60초·24시간키 정책 유지, 키 fingerprint에 루틴ID/버전 포함. 버전변경/needs_attention409, 타인/삭제404. 좌표/접근초/프로필/장소ID 클라이언트입력 없음. 조회중 변경이면 안내하지 않고 실행되지 않은 queued lease는 기존중단정책으로만료한다.

검색은 기존DB에 저장하고 검색↔루틴 바인딩은 본인/루틴ID·버전/planID·좌표없는 구간서명/장소버전/기한을 최근32검색 프로세스메모리로 제한한다. 재시작/다른프로세스/퇴출은404·새키로새검색, 과거바인딩 복원없음. 새DDL/루틴·plan 쓰기/AI호출 없음.

GET /api/v1/routines/{routine_id}/departure-searches/{search_id}/first-departure?expected_version=N은 본인/no-store·CSRF불필요. 루틴/plan/장소버전/바인딩/검색을 전후 검사한다. 저장된 모든 구간의 type/도보role/차량이름/정류소순서와 유일하게 일치하는 최신후보만 기존first-departure(include_connections=true)로 검사한다. ID/시간/거리 변경은 비교에서 제외하지만 노선·승하차순서 변경이나 중복후보를 자동선택하지 않는다. 경로서명은 노선선택이며 물리방향/정류소 인증은 기존경기매핑이 별도 수행한다.

응답 routine.departure.v1: routine_id/routine_version/search_id/status(searching/ready/no_routes/route_changed/ambiguous_route)/candidate_id(nullable)/departure(first.departure.v1|null)/expires_at. searching은Retry-After2. 검색실패는 안전한저장코드503, 후보없음·불일치·복수는200/숫자null. ready는 유일후보이며 실제첫승차 가능은 nested valid_for_guidance, 전체환승은connection_status 별도다. wrapper기한과 숫자는 원래검색/도착기한을늘리지않는다. 기존POST /guidance-queries 초안과별도API다.

홈/내루틴선택: 이전숫자제거→CSRF/POST→기존jobpoll→GET→예상첫출발. 60초/탭복귀 도착재검사·검색300초만료 새경로검색/수동갱신. 숨김/이탈/선택교체/로그인모달은 취소·늦은응답무시. 루틴조회실패/도착갱신실패·인증/버전충돌/만료는 숫자제거, 실패무한재시도없음. 다른출발지선택에는 저장루틴 안내를 적용하지 않는다. 기존CSS/색상/카드/Clock3 재사용.

검증: 신규백엔드11개 포함 전체354개137.158초, 프론트212개10.81초·빌드1909모듈447ms 통과. 합성실컴포넌트1280×800/390×844의출발·접근·설정여유/추정/다시확인·모바일가로넘침없음. 서버health/프론트200·비인증GET401·OpenAPI신규2경로 확인. 실제키/AI0회, 새DDL없음. 실경로 예측정확도/전체실로그인시각검증은 제외.

첫출발 접근은 사용자 승인 공급자양수초×개인계수 추정이다. 검증된 개인 도보의 물리승차 연결은미완료라 F07-02a 전체는 체크하지 않는다. 목표도착/요일기반 예약출발·이동시작·이동중 안내도 후속이다.


## 2026-10-14 — F07-02a-2 누락 접근 도보 보완

루틴서버바인딩의현재출발장소/버전만 내부first_departure에전달한다. 첫BUS 접근누락에한해 검증공식승차좌표까지 공급자도보1회·최대3초·기존전체20초/최대22회로보완한다. DB루틴/후보스냅샷수정없음. access_walk_api.md.


## 2026-10-14 — F07-04 목표 도착 평가

루틴출발GET의선택후보에 nullable target_evaluation을추가했다. 현재본인루틴의오늘목표시간/프로필을전후검사하고서버에서평가한다. 일반후보GET는null·기존쿠키/본인/CSRF/no-store/버전·기한유지, 새외부조회/DDL없음. 미래예약/대체노선은후속. target_arrival_api.md.
