# 루틴 누락 접근 도보 보완 — F07-02a-2

2026-10-14 · Notion v0.77: https://app.notion.com/p/3ebace1670c6806c8199cde33ebfbdfa
공식 공급자 계약: https://developers.kakao.com/docs/ko/kakaomap/rest-api (도보 GET /v2/routing/walk·REST키·WGS84·초/미터,2026-10-14 확인).

본인 루틴의 최신 후보가 첫BUS부터 시작해 ACCESS_WALK_MISSING일 때만, 본인 저장출발지→검증된 경기 승차정류소의 공식좌표로 별도도보를 최대1회 조회한다. 기존 양수접근도보/명시0초/지하철/복수노선·매핑미확인과 일반후보GET에는대체하지않는다. 루틴 서버바인딩이 현재 출발장소/버전을 전달하며 공개입력은추가하지않는다.

기존30m/정류소순서/공식stationId·staOrder/노선·회차·방향유일성을통과한 실제행의좌표만 채택한다. 별도비공개 endpoint sink로 Entry에매핑identity와함께저장, diagnostics·공개Mapping/DB/로그에는미포함. 잘못된방향/근거없음에근사정류소로대체없음. 사용자출발좌표는현재저장장소에서 읽어 공급자요청에만사용하며 새저장/로그/AI전달없음.

고정HTTPS dapi.kakao.com·리다이렉트금지·서버REST키·최단경로/3초·1MiB, 중복JSON/NaN거절. status=OK·양수총초<=86400/양수거리<=100000·20legs/500steps/20000points·정수비음수시간/거리·단계/구간합일치·유한좌표·단계연결/출발/승차양끝30m이내를검사한다. 결과없음·동일점·0초/손상/조회실패·위치불일치는시간없음. 직선거리·대중교통총시간잔여·5분/0초대체없음. 물리보행안전·출입구/정밀보행·AI산정인증은아니다.

기존 first.departure.v1에 provider_approach_source(transit_segment/boarding_walk/null), approach_fetched_at/approach_valid_until(nullable)추가. basis=provider_personalized 유지·W=ceil(원래공급자초×개인계수)·설정여유별도. 도보기한은검색/매핑/Entry/수신+300초중최소, 최종안내는원래도착/검색/매핑/도보중최소. 별도조회숫자/기한은응답에포함하고 화면에는별도도보추정출처/실패를구분한다. 기존후보/루틴/plan/missing_segments DB스냅샷은변경하지않는다.

양수초/수신시각/기한·출발장소버전/매핑identity만기존검색프로세스메모리(32검색/20후보/300초)에보관한다. 개인계수변경은원래공급자초에한번만곱해재계산·기한연장/재조회없음. 실패시도60초재시도차단, entry잠금/사용자갱신10회·분 공유. 전체출발/환승20초·클라이언트25초 유지, 전체외부최대22회(첫+후속2각최대7/도보1), 남은시간3초미만이면새조회없음. 재시작/퇴출/기한/장소·매핑·루틴변경은새근거필요.

실패사유 ACCESS_WALK_MAPPING_REQUIRED/UNAVAILABLE/TIMEOUT/TIME_LIMIT. 새HTTP경로/DDL/AI없음. 검증개인도보F07-02a전체·미지원매핑/지역확대/목표도착은후속. 이번직접실키호출0회이며 실제루틴의양수출발/보행정확도는실검증하지않았다. 실제검증결과는development_log.md를따른다.

최종 검증: 신규백엔드16개 포함 전체375개155.207초, 프론트222개23.72초·빌드1909모듈750ms, 합성PC/모바일성공·실패표시 통과. 자세한 검증/분경계테스트수정은 development_log.md.
