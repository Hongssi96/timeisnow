# 선택 루틴의 목표 도착 평가 — F07-04

2026-10-14 · Notion v0.78: https://app.notion.com/p/3ebace1670c6806c8199cde33ebfbdfa

수동 선택한 루틴의 현재 유일 후보를 오늘 Asia/Seoul의 설정 목표 시각과 비교한다. 반복 요일은 일정 참고이며 수동 선택을 막지 않는다. 목표 미설정은not_configured, 이미 지난 오늘 목표는target_passed다. 다음 날/다음 주로 자동 이월하지 않는다. 이 날짜 해석은 이번 구현 정책이며 사용자의 별도 날짜 정책 확정으로 기록하지 않는다. 미래 예약·arrive_by 검색/대체 노선 자동 선택/다음 차량은 후속이다.

기존 first.departure.v1에 nullable target_evaluation(target.arrival.v1)을 추가한다. 루틴ready 후보에만 평가하고 일반 후보GET는null이다. 필드는scope=selected_routine_candidate·status(not_configured/estimated_meets/estimated_late/target_passed/unknown/stale)·evaluated_at·target_arrival_at·estimated_destination_arrival_at·margin_seconds·egress_seconds·timing_basis(none/provider_timeline)·reasons. 미확인 목적지 시각/차이/도보초는null이다. 첫 valid_for_guidance와 전체connection_status는 독립 범위로 유지한다.

유효한 첫 승차·전체 환승 estimated_feasible·모든 BUS의 양수 차량 시간·순차 연결 ID/도보·버퍼/하차/최소승차/다음승차·마지막 하차 타임라인 일치가 필요하다. 마지막 차량 이후 egress WALKING이 모두 양수이고 누락되지 않았을 때 E=ceil(공급자 마지막 도보초 합×본인계수), 목적지ETA=마지막하차+E다. 마지막 도보 없음/0초·미지원/환승실패·현재 첫차량 접근불가·만료는 목적지 시각을 만들지 않는다. 하차 시각을 목적지 도착으로 대체하지 않는다.

총합 inconsistent는unknown. provider total의미배분 시간은 별도 접근/대기/도보에 배분하거나 다시 더하지 않고, 선택된 차량/환승 ETA와 제공 구간 시간을 사용하는 추정이다. 미배분이 있으면 PROVIDER_UNALLOCATED_TIME_NOT_USED 사유를 남긴다. 보행·미래 탑승·목표 충족의 실제 보장은 아니다.

ETA<=목표는estimated_meets, 늦으면estimated_late다. 차이는floor(목표-ETA)초로 음수도 그대로 보존한다. 목표 여유는 첫 정류장 탑승버퍼와 다르며 자동 버퍼 축소/지난목표 이월없음. 기존 출발기한을공유하고 평가전후프로필·루틴/장소/검색/후보변경을검사한다. 새 API/외부조회/AI/DB·DDL없음.

기존출발카드에 오늘목표/예상목적지도착/목표기준예상여유·늦음/추정한계를 표시한다. 미설정/지난목표/마지막도보·환승부족/실패·만료를 구분하며 현재 첫승차도 접근불가이거나 기한·목표가 지나면 이전 목적지숫자를 제거한다. CSS/색상/폰트체계 유지.

검증: 신규백엔드11개5.199초 포함 전체386개147.203초, 프론트229개10.04초·빌드1909모듈438ms 통과. 합성실컴포넌트 PC/모바일의 목표충족추정·마지막도보미확인·줄바꿈/모바일가로넘침없음 확인. 실제키/AI0회·새DDL없음. 실제경로 도착정확도/실보행과 미래예약·다른후보선택은 검증하지 않았다. 자세한 결과는development_log.md.
