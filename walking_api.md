# F05-01 도보 근거 수집

2026-10-08 · Notion v0.50 · `walking.evidence.v1`

선택한 검색 후보에 공급자가 제공한 접근·환승·마지막 도보를 구분한다. 물리적 출입구·승강장·보행 가능 범위는 미확인이므로 AI 산정 준비나 재사용 완료로 취급하지 않는다. F04-04와 GPS 자동 판정 보류를 유지한다.

## 조회 계약

`GET /api/v1/journey-searches/{search_id}/candidates/{candidate_id}/walking-evidence`

- 쿠키 인증, 본인 성공 검색과 후보만 허용. GET은 CSRF 불필요, 응답은 `Cache-Control: no-store`.
- 잘못된 UUID·없음·타인·미완료·검색 300초 만료는 404 `RESOURCE_NOT_FOUND`. 참조 장소 삭제도 404, 위치 버전 변경은 409 `VERSION_CONFLICT`, 손상된 후보는 502 `PROVIDER_RESPONSE_INVALID`.
- 검색 후보를 읽고 기존 `place_refs`의 소유권/위치 버전을 확인한다. 검색/근거 쓰기·보관 연장·추가 지도/AI 호출은 없다. 인증 세션 활동 기한은 기존 규칙대로 갱신한다. 새 DDL 없음.
- 검색 저장소는 저장 장소 참조의 출발/도착 역할을 기록하지 않는다. 잘못 연결하지 않도록 양 끝은 좌표 없는 검색 지점 참조로 반환한다.

200은 기존 `{data, meta}` 형식이다. `data`:

| 필드 | 값/규칙 |
| --- | --- |
| model_version | `walking.evidence.v1` |
| search_id, candidate_id | 조회 대상 UUID |
| expires_at | 기존 검색 만료 시각, 연장 없음 |
| status | `needs_data` |
| ready_for_estimation, reusable | 둘 다 `false` |
| segments | 접근 1개 → 각 환승 연결 1개 → 마지막 1개 |

각 segment:

| 필드 | 값/규칙 |
| --- | --- |
| segment_id | 검색·후보·역할·연결 기반 안정적인 UUID |
| role | `access`, `transfer`, `egress` |
| connection_id | 환승 연결 UUID, 나머지는 `null` |
| walking_leg_ids | 제공 도보 leg UUID 배열, 누락은 `[]` |
| from_ref, to_ref | `{type: search_origin/search_destination}` 또는 `{type: transit_stop, leg_id, stop_name}` |
| provider_duration_seconds, provider_distance_meters | 연속 도보 제공값 합계. 누락은 `null`, 명시 0은 `0` |
| source | `provider_estimate` 또는 `missing` |
| scope | `provider_walking_segment` 또는 `unknown` |
| physical_endpoints | `unconfirmed` |
| missing_segments | 아래 사유 코드 배열 |

모든 구간에 `PHYSICAL_ENDPOINTS_UNCONFIRMED`를 남긴다. 도보 미제공은 `PROVIDER_WALK_MISSING`, 제공 0초는 `WALK_DURATION_ZERO`, 인접 지하철이 있으면 `ENTRANCE_PLATFORM_UNCONFIRMED`를 추가한다. 정밀 좌표·출입구 설명·공급자 원문은 응답/일반 로그에 포함하지 않는다. 총 경로 시간의 남는 값을 도보·대기·여유로 배분하지 않는다.

## 구현과 검증

`backend/app/walking`은 router(HTTP) → service(소유권·만료·근거 구분) → repository(검색 읽기), dto(응답 계약)로 나눈다. 기존 journey.v1 모델과 장소 참조 검증을 재사용한다.

`backend/tests/test_walking.py` 7개 및 전체 백엔드 137개 통과. 실제 PostgreSQL 임시 스키마/ASGI와 합성 공급자 결과로 제공·누락·0초·연속 도보·환승·지하철·반복 조회 무변경·소유권·만료·버전·손상 응답을 확인했다. 실서비스 공급자의 물리 범위 검증과 AI 호출은 수행하지 않았다. 프론트 변경 없음.

다음은 F05-02 프롬프트 블록/버전 로딩이다. F05-03 AI 입력으로 넘기기 전 보행 가능 범위·방향·출입구/승강장 검증을 해결해야 하며 이 응답만으로 유효 산정값을 저장하면 안 된다.
