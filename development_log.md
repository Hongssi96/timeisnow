# 지금이니? — 개발 일지

기능별 작업이 끝날 때 짧게 추가한다. 아래 ‘실제 기록’만 완료된 작업이며 템플릿은 기록 형식이다.

## 실제 기록

### 2026-10-08 — F04-03a main 대상 중복 체리픽 확인
- 요청/기반: 사용자가 init에 병합된 이동 방법 우선순위 커밋을 체리픽 요청. 최신 origin/main4ddd36b에서 `codex/journey-method-priority-main` 생성 후 원본823113c를 실제 cherry-pick했다. 최신 Notion v0.50의5.2.5·TODO와 원본 변경/현재 코드·디자인/화면 문서를 확인했다.
- 결과/이유: 동일 기능은 이미6c238cb로 codex/routine-recovery에 포함되어 main에 병합됨을 ancestry와 개발 일지로 확인. JSX/정렬/전용 테스트에 추가 변경0, 문서6개와 CSS1개의 충돌은 우선순위 설명/스타일과 후속 변경을 포함한 최신 main을 유지했다. continue 결과 빈 체리픽(nothing to commit)이며 skip으로 정상 종료했다. 오래된 Notion v0.48 복사나 TODO 후속 작업으로 되돌리지 않았다.
- 실제 검증: 원격 main/init의 JourneyCandidates.jsx·journeys.js·JourneyMethods.test.jsx 내용 동일. `npm test -- tests/components/JourneyMethods.test.jsx` 전용4개 통과(2.41초). 최초 테스트 필터에 frontend 접두사를 중복 사용해 파일을 찾지 못했으며 올바른 frontend 상대 경로로 재실행했다. 기능/UI/API/DB 변경 없음, 전체 테스트/빌드/시각 검증은 이번 작업에서 재실행하지 않았다.
- 변경/명세: development_log.md와 todo.md에 확인 이력만 추가. Notion 계약 변경 없음(v0.50 재확인). 신규 기능 커밋이나 MR/병합은 만들지 않으며 검증 기록만 기능 브랜치에 커밋/푸시한다.
- 배운 개념/다음: 원본 SHA가 main에 없어도 다른 SHA로 체리픽된 변경은 이미 반영될 수 있다. 이때 패치를 반복 적용하면 문서 충돌만 생기며 결과는 빈 변경이다. 우선순위 기능의 추가 병합은 필요 없음. F05-01 codex/walking-evidence 사용자 검토/병합 후 F05-02, 화면 미표시는 로컬 실행 브랜치/프론트 상태를 별도로 확인한다.
- 명세: https://app.notion.com/p/3ebace1670c6806c8199cde33ebfbdfa (v0.50, 계약 영향 없음)

### 2026-10-12 — F05-04 산정값·근거 이력 저장 및 본인 조회
- 목표/기반: 최신 main 2b2e210과 F05-03 미병합 상태를 fetch로 확인했다. 최신 main에서 codex/walking-estimate-history를 생성하고, 필수 선행 커밋513929c를eb958d5로 포함했다. MR 생성이나 main 병합은 하지 않았다. TODO와 기획·개인화·프롬프트·로깅·DB 문서 및 기존 계층 코드를 Notion v0.53과 비교하고, 구현 전에 v0.54의5.5.3에 저장·조회·보관 계약을 확정했다.
- 구현 파일: 0009_walking_history에 ai_executions, walking_paths, walking_estimates, walking_estimate_revisions를 추가했다. 복합(id,user_id) FK와 숫자 제약, 조회·보관 인덱스를 사용한다. walking/history_dto·history_repository·history_service는 F05-03 결과를 재검산하고, 물리 확인 Context와 회원·프로필·장소 버전을 확인한 뒤 원자적으로 저장한다. GET /walking-estimates/{id}는 본인 쿠키 인증 후 숫자 요약만 반환한다.
- 실행 처리: estimate_and_store는 모델 호출 전후에 권한·버전·근거 기한을 검사한다. 같은 실행의 동시 요청은 DB 세션 advisory 잠금과 내부409 EXECUTION_IN_PROGRESS로 차단한다. 완료한 실행은 모델을 다시 호출하지 않는다. 모델을 기다리는 동안 장소 수정 잠금을 잡지 않으므로, 저장 직전에 위치 버전을 다시 검사한다. 서로 다른 조건의 캐시 재사용은 F05-05 후속이다.
- 저장 정책: ok만 유효 산정을 만들고, needs_data/unsupported/허용된 실패는 최소 실행 이력만 보관한다. 산정은30일과 근거 기한 중 이른 때 만료하고, 품질 이력은90일 보관한다. 회원 삭제는 CASCADE, 기간 청소 함수는 제공하되 자동 스케줄은 후속이다. 장소 이름 변경은 유지하고 위치·프로필 변경은409, 삭제는404로 조회를 차단한다. 원문·키·좌표·이름·메모·사고 과정·모델 자유문 reason은 저장하지 않는다. 모르는 사용량/지연과 실행하지 않은 모델은 null이다. 프로필 계수는 내부 검증 스냅샷이며 실제 학습 연결은 F09 후속이다. 현재 미확인 Evidence는 유효 산정 저장을 차단한다.
- 실제 검증: 신규 test_walking_history16개가9.311초에 통과했다. PostgreSQL 격리 스키마/ASGI와 합성 AI로 정상값·실패·needs_data·중복/충돌·동시 실행·호출 중 위치 변경·본인/타인·프로필/장소 버전·30일/근거 기한·90일 청소·회원 삭제·복합 FK·중간 실패 전체 롤백·OpenAPI를 확인했다. 최종 백엔드 전체184개가82.124초에 통과했다. 마이그레이션 적용/복구/재적용과 기존 장소 보존도 통과했다. AST 검사에서 repository 밖 직접 SQL 실행0건, git diff --check 통과.
- 회귀 실패와 수정: 최초183개는 통과했다. 동시 실행 보강 후 기존 장소 만료 테스트가 expires_at=now() 경계에서201!=404로 실패했다. 해당 테스트만5초 과거 시각으로 바꾸고 장소12개(7.126초) 통과를 확인했다. 다음 전체 실행에서는 기존 현재 위치 호출 제한 테스트가60초 창을 넘으며503!=429로 실패했다. 해당 테스트의 clock_now를 하나의 실측 창 시각으로 고정하고 현재 위치5개(4.645초) 통과를 확인했다. 장소/현재 위치 API 코드와 정책은 변경하지 않았다. 최종 전체184개는 통과했다.
- 개발 DB/서버: 실제0008→0009 upgrade와 새 테이블4개를 확인했고, 기존 회원·장소·루틴 행 수는 전후 동일했다. 실제 사용자 산정/품질 자료는 만들지 않았다. 이 채팅에서 시작한 백엔드18056/23176만 확인 후 종료하고 숨김 재시작(worker10420)했다. 시작 완료·health200·OpenAPI 등록·실제 비인증401 AUTH_REQUIRED·프론트5173 HTTP200을 확인했다. UI 변경이 없어 프론트 테스트와 브라우저 시각 검증은 반복하지 않았다. 외부 AI/카카오 추가 호출은 없었다. 임시 테스트 로그는 정리했다.
- 명세/문서: Notion v0.54의5.5.3, API 목록,5.6 UUID/reused=false 예시, 관련 후속 상태, 상단 구현 상태와 변경 이력을 맞추고 재조회했다. api_contract1488줄 전문 일치를 확인했다. walking_api/database_schema/migrations/planning/personalization/ai_prompts/logging/backend README·TODO·feature_breakdown도 갱신했다. 기존 계산·HTTP 클라이언트 호환성을 유지하며 새 GET/DDL·이력 저장만 추가했다. 프롬프트 문구와 버전은 유지했다.
- 배운 개념/다음: 사용 가능한30일과 품질 보관90일은 다르다. 만료된 값을 안내에 쓰지 않으면서 검증 이력은 남길 수 있다. 부모 ID와 user_id를 함께 참조하면 DB에서도 타인 자료 연결을 막을 수 있다. DB 중복 저장 방지와 모델 중복 호출 방지는 별도이며, 실행 잠금과 호출 전후 버전 검사가 함께 필요하다. F05-04 내부 저장/본인 조회 완료. 사용자 검토/MR/병합 후 F05-05 조건별 재사용을 진행한다. 실제 물리 근거 확보·사용자 생성/UI 연결·자동 청소·학습/재산정·출발 안내는 후속이다.
- 명세: https://app.notion.com/p/3ebace1670c6806c8199cde33ebfbdfa (v0.54).

### 2026-10-12 — F05-03 최종 실제 합성 검증 및 완료
- 승인/원인: 사용자가 동일한 개인정보 없는 합성 요청의 추가 진단·수정 검증을 최대3회 승인했다. 추가1회 HTTP400/unclassified, 고정 태그 진단을 보강한 추가2회에서 INVALID/MAX_OUTPUT_TOKENS를 확인했다. 원문을 출력하지 않고 고정 어휘만 진단했으며 HTTP 오류코드/공개503 형식은 유지했다. 첫 실패의 정확 원인은 후속 진단으로 출력 토큰 설정 문제로 좁혔다.
- 수정/실제 결과: provider.py의 max_output_tokens를4096에서512로 낮추고 전송 계약 테스트를 함께 수정했다. 마지막 추가3회 check_ai_walking.py 실행은 status=ok·prompt_version=walking_estimate.v1·model_matches=true·result_count1·result_statusok·estimated_seconds360·server_validation_passedtrue·2.51초, 종료0. 합성300초×factor1.2의 strict 응답/ID/근거/범위/수식 검산을 확인했다. 실제 모델명은 중계 서버 보고값이며 내부 실제 공급자 증명은 아니다. 승인된 추가3회 모두 사용, 최초 실패까지 구조화 요청 총4회, 이후 외부 호출 없음. 키/URL/응답·오류 원문/개인 위치·카카오 원본은 출력/전송하지 않았다.
- 최종 로컬 검증: 신규19개0.091초 OK(토큰 한도·거절/미완료·안전한 HTTP 상태/코드/고정 태그 포함), 전체백엔드168개58.394초 OK(실제 PostgreSQL 격리 스키마/ASGI·합성 공급자). git diff --check 통과. 앞선 실패/승인 대기 기록은 당시 진행 이력으로 보존한다. UI/기존HTTP/DB 계약 변경이 없어 프론트/시각 확인과 서버 재시작은 수행하지 않았다.
- 문서/완료: 게시 전 최신 Notion v0.53 재확인,5.5.2의 출력 한도512·실호출 결과·검증/완료 상태,5.5.1 후속 문구·상단 구현 상태·변경 이력을 갱신하고 재조회 확인. api_contract1479줄 전문 일치. ai_prompts/planning/provider_plan/backend README·TODO/feature_breakdown F05-03 완료 동기화. 기존 HTTP/DDL/계산 공식/보관·클라이언트 호환성 유지, 내부 전송 제한과 구현 상태만 확정. 프롬프트 문구/버전은 그대로다.
- 배운 개념/다음: HTTP503 정규화만으로는 인증 오류와 요청 형식 오류를 구분할 수 없어 고정 어휘 기반 안전한 진단이 도움이 된다. 키 최소 인증과 실제 구조화 요청 호환성은 별도 검증이다. F05-03 서버 내부 최소 입력/검증 모듈 단계 완료, 사용자 MR/병합 후 F05-04 산정/근거 이력 저장. 현재 물리 근거 미확인 Evidence는 호출0/needs_data를 유지한다. 다수 후보 실응답·512토큰 내 완료 가능성·실제 도보/서비스/운영 품질은 미검증이며 미완료 응답은 거부한다. 유효한 물리 범위 확보/사용자 서비스 연결/저장·재사용은 후속이다.
- 명세: https://app.notion.com/p/3ebace1670c6806c8199cde33ebfbdfa (v0.53).


### 2026-10-12 — F05-03 첫 실호출 실패 및 안전한 진단 보강
- 승인/실행: 사용자가 합성 도보 요청1회를 승인하여 준비된 check_ai_walking.py를 실행했다. 실제 출력은 failed/http_status503/PROVIDER_UNAVAILABLE, 종료코드1. 도구는 재시도하지 않았고 추가 요청도 실행하지 않았다. 키/모델/호스트 설정의 존재/일치는 로컬 재확인 정상이다. 공급자의 원래 HTTP 상태를 보존하지 않은 최초 어댑터 때문에 인증·형식·가용성 중 정확한 원인은 미확정이다.
- 보강/검증: provider.py의 AIProviderError/http_failure는 제한된 응답 크기에서 공급자 HTTP 상태와 허용 코드만 내부 진단에 보존한다. 알 수 없는 코드/본문·키·URL은 출력하지 않는다. check_ai_walking.py에서 안전한 상태/코드만 출력, 공개 AuthError 계약은 기존503 유지. HTTP400 invalid_json_schema/invalid_api_key 및 악성 코드/본문/자료형 비노출 테스트1개 추가, 신규19개0.090초·전체백엔드168개58.749초 OK. py_compile·diff --check 통과. 이번 보강 후 실제 외부 요청은 실행하지 않았다.
- 문서/상태: Notion v0.53의5.5.2·변경 이력에 첫 실호출503 실패/원인 미확정/추가 진단 승인 대기·19개/168개 결과를 기록하고 재조회 확인. api_contract1479줄 전문 일치. TODO/feature_breakdown은 미완료 유지, ai_prompts/backend README/provider_plan 실패 기록 추가. 기능 브랜치의 최종 완료 커밋·푸시는 실호출 확인 후 진행한다.
- 남은 일: 최초 승인1회는 사용했다. 추가 사용자 승인 후 동일한 개인정보 없는 합성 입력으로 공급자 오류를 진단하고 필요한 수정/검증을 수행한다. 아직 실제 구조화 응답 성공이나 품질 평가 완료로 보고하지 않는다.


### 2026-10-12 — F05-03 AI 최소 입력·구조화 결과 검증 (실호출 승인 대기)
- 목표/기준: 사용자 다음TODO 진행 요청. 최신 origin/main2b2e210에서 F05-02 병합을 fetch로 확인하고 codex/ai-walking-validation 생성. TODO·기획/기능·개인화/프롬프트/로깅·최신 Notion v0.52를 확인했다. 현재 F05-01은 미확인 물리 범위/산정 준비false이므로 운영 입력을 AI에 보내지 않는다. OpenAI Docs 스킬로 공식 Responses Structured Outputs 문서를 검색/열람 후 strict text.format 형식을 확인했다. https://developers.openai.com/api/docs/guides/structured-outputs?api-mode=responses
- 계약/범위: 구현 전 Notion v0.53의5.5.2에 내부 입력·준비조건·결과 검산·실패/재시도 계약을 추가했다. 공개 HTTP/UI API·DDL·계산 공식/기존 보관 정책 변경 없음. 검증된 내부 후보만 모델로 전달하며 부족한 후보는 needs_data로 차단한다. 인증/소유권/물리 근거 확인은 후속 호출 서비스의 선행 책임이며 새 클라이언트 입력 경로는 없다. 저장/품질 이력·재사용은 F05-04 이후다.
- 변경 파일/이유: app/ai/walking_dto.py strict 최소 입력/출력, provider.py HTTPS Responses strict JSON Schema·storefalse·4096출력토큰/35초/256KiB·리다이렉트/도구/거절/미완료/모델 검사, walking_service.py 준비조건 분류·SYSTEM/DEVELOPER/USER 분리·결과ID/근거/범위/수식/ceil 검산·형식 최대1회 추가호출을 구현했다. 공급자 시간 우선·거리/검증 속도 fallback·기본계수/이중보정 방지, 숫자 유한성/중복·추가 필드 차단. estimate_evidence는 현 미확인 근거에서 이름/좌표를 제거하고 호출0/needs_data를 보존한다. check_ai_walking.py는 합성300초×1.2→360초를 최대1회(재시도 없음) 요청하고 안전한 검산 요약만 출력하도록 준비했다.
- 실제 로컬 검증: test_ai_walking.py 신규18개0.076초 OK, 백엔드 전체167개59.732초 OK(실제 PostgreSQL 임시 스키마/ASGI·합성 공급자). 정상/ceil/계수/이중보정·공급자 우선·미확인/누락/0초·정밀 위치/메모 추가 필드 거절·동일ID/근거·출력 위조/버전/상태/null/수식·한정 재시도·거절/미완료/도구/크기/HTTP/timeout·유한 입력의 파생 오버플로·누락 사유 상한 보존을 확인했다. 마지막 보강은 누락20개에 서버 사유를 추가해도 결과를 보존하는 경계 테스트다. py_compile 구문 확인·git diff --check 통과. UI/기존 API 흐름 무변경으로 프론트/시각 검증·서버 재시작은 수행하지 않았다.
- 키/실호출: 앞선 사용자 명시 승인으로 check_ai.py 최소 인증1회는HTTP200·completed·모델 일치·OK·1.43초·11/5/16토큰 성공. 현재 키 인증 가능, 실제 만료일/갱신 상태 미확인. 이번 F05-03 합성 요청은 자동 승인 검토가 이전 승인을 키 인증1회로 한정해 키의 mlapi.run 전송을 거부했다. 거부된 명령은 실행되지 않았고 해당 명령의 로컬 보강/합성 검증만 외부 통신 없이 분리 수행했다. 우회 요청/추가 외부 호출 없음. 실제 구조화 모델 응답/품질은 미검증, 별도 사용자 승인 대기다. 키/URL/원문/개인 위치는 기록하지 않았다.
- 문서: Notion v0.53을 내부 구현·18개/167개 검증 완료 및 실호출 승인 대기로 갱신,5.5.1 후속 상태와 변경 이력을 맞추고 재조회 확인. api_contract.md 최종1479줄 줄별 일치 확인. ai_prompts13절/planning/provider_plan/backend README·TODO/feature_breakdown 동기화. F05-03 체크는 실호출 검증 전 미완료로 유지한다.
- 배운 개념/남은 일: strict JSON Schema도 ID/범위/수식 의미 검증을 대체하지 않는다. 공급자 값 존재와 실제 보행 범위 확인은 다르며 미확인 입력의 호출 차단이 중요하다. 로컬 구현/회귀는 완료, 승인 후 준비된 합성 요청1회와 서버 검산을 확인하고 최종 기록·커밋·푸시한다. 실제 사용자 위치/카카오 원문 전송·물리 범위 확보·저장/재사용/운영품질은 후속이다.
- 명세: https://app.notion.com/p/3ebace1670c6806c8199cde33ebfbdfa (v0.53).


### 2026-10-12 — F05-02 프롬프트 블록·버전 로딩
- 목표/기준: 사용자 진행 요청에 따라 fetch 후 최신 origin/main bb4e72e에서 codex/prompt-loading 생성. TODO·planning/feature_breakdown/personalization/ai_prompts/logging 및 최신 Notion v0.51의5.5·프롬프트/계산 정책을 확인했다. F05-02는 기존 작업 문구를 버전별로 읽는 내부 기반이며 실제 AI 호출은 F05-03이다.
- 변경 파일/이유: backend/app/ai/prompt_loader.py에 불변 PromptBlock/PromptBundle·load_prompt·안전한 PromptLoadError를 추가했다. app/ai/prompts의 common.v1/walking_estimate.v1/journey_explanation.v2 JSON은 ai_prompts.md 해당 text 블록을 변경 없이 복사했다. 허용 작업만 선택, 기대 버전/역할/필드/빈 내용 검증, 패키지 리소스로 실행 폴더 독립 로딩. SYSTEM과 DEVELOPER를 분리하고 입력은 후속 별도 메시지로 유지한다. 자연어 일정은 별도 SYSTEM이므로 F17 후속. 캐시/외부 호출/DB 쓰기/일반 로그 추가 없음. dataclass repr에서 본문을 제외하고 messages는 새 목록으로 반환한다.
- 실제 검증: test_prompt_loader.py 신규8개 0.041초 OK. 문서와 본문/버전 정확 일치·별도 역할·실행 폴더 변경·임의 경로/일정 작업 거절·기대 버전 오류·누락/인코딩/손상/잘못된 역할/빈 내용·부분 실패·불변/목록 오염 방지를 확인했다. 백엔드 전체149개 58.731초 OK(실제 PostgreSQL 임시 스키마/ASGI·합성 공급자 포함). git diff --check 통과. UI/API 실행 흐름 무변경이므로 프론트/시각 검증·서버 재시작은 수행하지 않았다. 실서비스 AI/지도 호출·모델 품질 평가는 하지 않았다.
- 문서/명세: Notion v0.52에5.5.1 내부 로더 범위/실패/구현 상태·상단 상태·버전/변경 이력을 갱신하고 재조회 저장 확인. 파일명이 자동 링크로 바뀐 부분은 코드 표기로 수정 후 다시 확인했다. api_contract.md는 최종 본문1471줄을 줄별 비교해 일치 확인. ai_prompts/planning/backend README·TODO/feature_breakdown 동기화. 기존 HTTP 입력/응답·인증/권한/오류·DDL/보관/계산 계약 및 클라이언트 호환성 영향 없음. 프롬프트 문구/버전은 유지하며 구현 상태만 확장했다.
- 배운 개념: 문서 전체를 보내지 않고 버전·역할이 붙은 런타임 블록만 로딩하면 설명 문서와 모델 지시를 분리할 수 있다. 문서와 패키지 리소스의 일치 테스트로 복사본 드리프트를 발견한다. 로더 검증과 실제 모델 출력/품질 평가는 서로 다른 완료 조건이다.
- 남은 일/다음: F05-02 완료·기능 브랜치 커밋/푸시 후 사용자 MR/병합 대상. 다음 F05-03 최소 근거/구조화 출력 검증. 현재 walking.evidence는 물리 범위 미확인/needs_data이며 산정 준비로 바꾸지 않았다. AI 키의 기존 사용자 제공 기한은2026-10-08로 실제 호출 전에 갱신 여부 확인 필요. F04-04/GPS 자동 판정 보류 유지.
- 명세: https://app.notion.com/p/3ebace1670c6806c8199cde33ebfbdfa (v0.52).


### 2026-10-12 — F05-01 main 병합 및 통합 검증
- 요청/기준: 사용자가 codex/walking-evidence를 찾아 병합하도록 명시 요청하여 기존 사용자 직접 병합 규칙의 이번 작업 예외로 적용했다. fetch 후 main/origin/main6257ba2와 기능 브랜치c5ad2ce를 확인했다. 최신 Notion v0.51의5.5 도보 근거 계약을 다시 읽고 구현과 비교했다.
- 통합: walking 패키지/라우터/테스트와 walking_api.md·개인화/기획 문서를 반영했다. api_contract/development_log/planning/todo 충돌을 해결하며 최신 v0.51과 지도 핀 저장 기록, 도보 근거 기록을 모두 보존했다. TODO/feature_breakdown F05-01 완료 상태를 맞추고 다음 작업을 F05-02로 정리했다. 기존 기능 코드는 수정하지 않았다.
- 실제 검증: backend/.venv/Scripts/python.exe -m unittest discover -s backend/tests 전체141개,59.251초,OK. 실제 PostgreSQL 임시 스키마/ASGI 및 합성 공급자 검증이며 지도 핀 저장4개와 도보 근거7개를 함께 포함한다. git diff --check 통과·문서 충돌 표시0건. UI 변경이 없어 프론트/시각 검증은 반복하지 않았다. 실제 지도/AI 공급자 호출·개발 서버 재시작은 이번 병합 범위에서 수행하지 않았다.
- 명세 영향: 기존 v0.51 계약의 구현을 main에 통합하는 작업이며 새 계약 변경 없음. Notion 수정 불필요, 최신 본문을 확인했고 로컬 api_contract.md의 v0.51을 보존했다. https://app.notion.com/p/3ebace1670c6806c8199cde33ebfbdfa
- 배운 개념/남은 일: 서로 다른 기능 브랜치의 문서 충돌은 최신 계약과 양쪽 검증 이력을 함께 보존해야 한다. F05-01 통합 검증 완료, 다음 F05-02 프롬프트 블록·버전 로딩. 물리 도보 범위·AI 산정/저장/재사용은 기존 후속 상태다.


### 2026-10-08 — F05-01 선택 후보 도보 근거 수집
- 목표/기반: 사용자 진행 요청에 따라 R02 병합 main4ddd36b를 확인하고 최신 origin/main에서 `codex/walking-evidence` 생성. 최신 Notion v0.49 및 TODO·planning·feature_breakdown·personalization·ai_prompts·logging 정책 확인 후 새 읽기 계약을 v0.50으로 먼저 추가했다.
- 변경 파일: `backend/app/walking/{router,service,repository,dto}.py`, 패키지 초기화·main 라우터 등록·`backend/tests/test_walking.py`. GET `/api/v1/journey-searches/{search_id}/candidates/{candidate_id}/walking-evidence`에서 접근1개·각 환승 연결1개·마지막1개를 조회한다. 기존 journey.v1/장소 참조 검증 재사용, 안정적인 segment UUID/원본 leg ID 유지, 연속 도보 제공값 합산.
- 정책/이유: 제공0초는 0+WALK_DURATION_ZERO, 미제공은 null+PROVIDER_WALK_MISSING. 모든 물리 범위는 unconfirmed, 지하철은 입구/승강장도 미확인. needs_data·ready_for_estimation/reusable=false. 정밀 좌표/출입구 설명 비노출, 남는 경로 시간을 도보/대기로 배분하지 않는다. 저장소에 장소 참조의 출발/도착 역할이 없어 추측하지 않고 검색 지점 참조를 사용한다. F04-04/GPS 자동 판정 보류 유지.
- 저장/호환성: 새 DDL·지도/AI 호출·검색/근거 DB 쓰기·검색 만료 연장 없음. 기존 인증 세션 활동 기한 갱신은 유지한다. 새 GET 추가이며 기존 API/클라이언트·보관/계산 동작 유지. 일반 로그에 원문/정밀 위치 추가 없음.
- 실제 검증: 신규7개/전체 백엔드137개(59.241초) 통과. 실제 PostgreSQL 테스트 임시 스키마/ASGI·합성 공급자로 값/누락/0초·연속 도보·환승·지하철·반복 조회 검색 행 무변경/추가 호출0·auth401·소유권/잘못된ID/만료/미완료404·장소 이름 유지/위치409/삭제404·손상502·OpenAPI 모델 확인. 사용자 업무 DB 변경·실제 공급자 물리 범위 검증 없음.
- 실행 확인: 프로젝트 실행 명령 확인 후 백엔드 재시작(worker20796), health200·OpenAPI 새 GET 등록·실행 서버 비인증401 AUTH_REQUIRED/no-store 확인. 초기 프로세스 검사는 venv가 시스템 Python을 사용하는 점 때문에 중단했으며 command line의 프로젝트 경로를 확인한 뒤 재시작했다. 프론트 변경/시각 검증/프론트 재테스트 없음.
- 문서: Notion v0.50 API 목록·5.5 계약/예시·상태·변경 이력 저장 후 재조회 확인. api_contract.md 원본 복사, walking_api.md·planning/personalization 수집 설명·TODO/feature_breakdown F05-01 체크 동기화. 프롬프트 작업 블록 자체는 변경 없음. MR 생성/병합은 사용자 담당.
- 배운 개념/남은 일: 공급자 숫자 존재와 실제 이동 범위 검증은 다르며 null와0의 구분이 허위 기준값 저장을 막는다. 다음 F05-02 프롬프트/버전 로딩. F05-03 AI·F05-04 저장은 후속, 보행 가능 범위·방향·입구/승강장은 미검증 유지.
- 명세: https://app.notion.com/p/3ebace1670c6806c8199cde33ebfbdfa (v0.50, 새 도보 근거 GET API 추가)


### 2026-10-08 — F03-02a 검색 없이 지도 핀 저장·자동 선택
- 목표/기반: 사용자가 지도에서 고른 지점을 저장하려고 주소를 다시 검색해야 하는 불편을 해결하도록 요청. 최신 origin/main4ddd36b에서 codex/map-pin-place-save 생성. TODO·장소/출발/루틴 명세·기획·기능 목록·디자인/화면·로깅 문서와 Notion v0.50 확인, 구현 전에 v0.51/5.1.4 조건부 핀 생성 계약 추가. F05-01은 별도 codex/walking-evidence에 있으며 이번 브랜치에 미병합 코드를 포함하지 않았다.
- 원인/변경: 기존 PlaceInput의 search_id/candidate_id 필수와 create의 후보 조회 때문에 지도 핀만으로 새 장소 생성 불가. backend/app/places/dto.py에 source 기본search/map_pin과 조건부 검증, service.py에 확인 ID 기반 생성 분기 추가. map_pin은 name=생성 당시label, address/location_address=서버 확인 법정동, 실제 좌표=확인된 핀. 정밀 주소/공식 장소명을 추측하지 않는다. 검색 입력과 과거 멱등 해시 유지, 새 DDL 없음.
- 화면/파일: frontend/src/components/PinPlaceSave.jsx 추가, OriginSelector.jsx·JourneyComparison.jsx 연결. 지도 선택 뒤 '이 위치 저장하고 사용'→이름만 입력→지역 확인/POST201→saved_place 검증/자동 선택. 이미 선택한 지도 지점의 '새 장소 저장'에도 기존 핀 전달, 반대쪽 선택 유지. 저장 중 지도/취소/방식 잠금, 이탈 abort/늦은 응답 무시. 응답 유실 재시도는 같은 body/키, 404는 명시적 재확인, 저장 성공 뒤 선택 검증 실패는 저장 목록에서 재선택하여 중복 생성 방지. 기존 단발 지도 사용/검색 저장 유지.
- 실제 검증: 신규 backend/tests/test_pin_place_create.py4개 포함 백엔드134개(62.698초) 통과. 실제 PostgreSQL의 테스트 임시 스키마/ASGI로 검색 없는 저장/상세·확인 만료/좌표 불일치/타인·CSRF·형식422·멱등409·만료 후 동일키 재시도·삭제 후404·기존 search 해시 호환 확인. 최초 전체 검증에서 레거시 해시 테스트가 새 DTO 필드source를 포함하는 문제 발견, test_place_map_pin.py에 과거 형식 재현을 위한 source 제외 후 전체 재실행 통과.
- 프론트 검증: PinPlaceSave.test.jsx 신규5개·OriginSelector.test.jsx 추가1개, 전체148개/18파일·빌드1903모듈 통과. 검색 없이 핀 전달/저장 장소 자동 선택, 네트워크 재시도 같은 키/본문·확인 재호출0, 처리 중 잠금/이탈 abort, 확인404 재확인·로그인 만료를 검증했다. 마지막 테스트 assertion 강화 후 OriginSelector12개 재통과. 구현을 복제하는 테스트 대신 API 흐름과 실패 복구를 검증한다.
- 시각/실행: 임시 localhost 검증 페이지에서 실제 Kakao 지도(공개 서울시청 좌표)+합성 확인/저장/선택 API로 PC1440×1000·모바일390×844 폼/버튼/자동 도착지 선택 완료 확인, 가로 넘침0·콘솔error0. 실제 사용자 계정에 테스트 장소를 생성하지 않았으며 임시 페이지/탭 제거, viewport 원복. UI 저장 결과는 합성이며 실사용 HTTP 생성 테스트로 표시하지 않는다. 프로젝트 백엔드 재시작(worker33740)·health200. 기존 미색/초록·place-form/info-box/버튼 재사용, 새 CSS/팔레트 없음.
- 문서/명세: Notion v0.51 API 목록/5.1.2 적용범위/5.1.4 입력·예시·오류·화면·구현 상태/변경 이력 저장 후 재조회. api_contract.md 복사·place_api.md/origin_api.md/routine_api.md/planning.md/design_guide.md/screen_plan.md·TODO/feature_breakdown F03-02a 동기화. 기존 클라이언트 search 기본값·기존키 재시도·API 응답/계산/보관 호환, 새 지도 핀 생성 조건과 사용자 흐름 추가. 좌표/이름/주소/쿠키/본문 일반 로그 추가 없음.
- 배운 개념/다음: 검색 후보의 신원과 사용자가 정한 위치는 서로 다른 생성 근거다. source별 필수값을 검증하면 가짜 검색 후보를 만들지 않고 기존 확인 자원을 재사용할 수 있다. 새 생성 필드가 기본값이어도 과거 멱등 해시와 호환시켜야 한다. F03-02a 완료, 사용자 기능 브랜치 MR/병합 후 F05-02 프롬프트/버전 로딩(선행 F05-01 별도 브랜치 검토). GPS 자동 판정/F04-04/AI·실시간은 기존 후속/보류 상태.
- 명세: https://app.notion.com/p/3ebace1670c6806c8199cde33ebfbdfa (v0.51, 지도 핀 조건부 생성 입력/사용자 흐름 추가)

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
## 2026-10-08 — F04-03a 이동 방법 선택 시 첫 카드 우선 표시

- 목표/이유: 사용자가 버스·버스 + 지하철·지하철을 선택하면 원하는 방법의 경로를 즉시 첫 카드로 확인하도록 요청했다. 기존 화면은 시간/환승/도보 기준만 제공했다.
- 기준: 최신 origin/main a99eea4에서 codex/journey-method-priority 생성. 착수 전 Notion v0.47·TODO·기획/기능·화면/디자인·기존 JSX/CSS를 확인했다. 사용자 흐름 변경을 구현 전 Notion v0.48의 5.2.5와 변경 이력에 반영했다.
- 변경 파일: frontend/src/components/JourneyCandidates.jsx에 전체/세 방식 버튼·선택 상태·미제공 안내 추가. frontend/src/lib/journeys.js의 sortCandidates는 선택 type의 후보를 앞 그룹에 배치하고 그룹 내부는 기존 비교 기준을 유지한다. 원본 배열은 변경하지 않는다. styles/styles.css에 범위를 한정한 버튼 스타일 추가. tests/components/JourneyMethods.test.jsx에 회귀4개 추가, JourneyCandidates.test.jsx의 반복 요일 검증은 해당 fieldset으로 범위를 좁혔다. api_contract/planning/screen_plan/design_guide/todo/feature_breakdown 문서를 동기화했다.
- 동작: 선택 시 추가 API/공급자 호출 없음. 다른 후보는 숨기지 않고 전체로 원래 정렬을 복원한다. 후보 ID가 동일하므로 펼친 상세/작성 중 루틴 이름을 유지하며 저장 대상이 바뀌지 않는다. 새 결과는 전체로 시작한다. 미제공 방식은 안내 후 기존 후보를 유지한다.
- 실제 실행 결과: 초기 테스트는 신규 버튼 때문에 기존 요일 테스트의 전체 화면 pressed 조회가 영향을 받았고 새 테스트가 프로젝트에 없는 jest-dom matcher를 사용해 실패했다. 요일 그룹 범위와 표준 Vitest 단언으로 수정 후 npm test:17파일138개 전체 통과. npm run build:1902모듈 성공. 후보 우선 배치/전체 복원·시간/환승/도보 그룹 내부 정렬·원본 보존·미제공 안내·상세/루틴 입력/저장 ID 유지 검증.
- 시각 검증: 임시 Vite QA 페이지에서 실제 컴포넌트와 합성 후보로 PC1440×1000·모바일390×844 세 방식의 첫 카드 이동 확인, 가로 넘침 없음·콘솔error0. 임시 페이지/JSX와 탭 제거 및 viewport 복원. journey-method-mobile.png를 시각화 폴더에 저장했다. 실제 카카오 재호출·실제 DB 저장·백엔드 테스트는 프론트 로컬 정렬 변경인 이번 작업에서 재실행하지 않았다.
- 명세: Notion v0.48 최종 구현/검증 상태를 갱신하고 재조회 저장 확인. api_contract.md는 최종 Notion 본문과 기계 비교해 복사했다. API 경로/요청/응답/인증/권한/시간/캐시/보관/DB 계약 변경 및 기존 클라이언트 호환성 영향 없음. 신규 프론트 흐름만 추가.
- 배운 개념: 필터링 대신 우선순위 정렬로 원하는 방법을 먼저 보여주면서 다른 대안을 비교할 수 있다. 배열 위치 대신 고유 ID를 사용하면 카드 이동 시 입력과 상세 상태가 올바른 경로에 남는다. 접근성 상태를 검사하는 테스트는 대상 그룹의 범위를 명확히 해야 한다.
- 남은 일/다음: F04-03a 완료. 사용자가 MR/병합 후 F06-04 장소/경로 변경 복구 안내를 진행한다. F04-04/GPS 자동 판정·실시간/AI 출발 안내는 기존 후속 상태다.
- 명세: https://app.notion.com/p/3ebace1670c6806c8199cde33ebfbdfa
## 2026-10-08 — F06-04 장소 변경/삭제 후 루틴 복구 안내

- 목표: 장소나 경로가 변경되어 확인이 필요한 루틴을 안전하게 복구하도록 안내한다. 삭제 연동은 이미 있었지만 장소 위치·출입구 수정은 루틴을 active로 남기는 누락을 확인했다.
- 기준: 최신 main a99eea4에서 codex/routine-recovery 생성. 아직 main에 미병합인 직전 F04-03a 823113c를6c238cb로 포함했다. TODO와 기획/기능/디자인/화면/개인화/프롬프트/로그·routine_api 및 최신 Notion v0.48을 확인했다. 구현 전에 v0.49/5.3.3으로 장소 변경 상태 전이·복구 흐름을 확정했다.
- 변경 파일/이유: backend/app/places.py의 실제 location_changed 때 연결된 본인 루틴을 needs_attention/version+1로 전환한다. 이름만 수정/동일값 수정은 유지한다. 기존 routine-write 회원 잠금을 장소 수정/삭제에서도 먼저 획득해 경로 저장과 같은 잠금 순서로 직렬화했다. 추가 DDL 없음, 이전 스냅샷·일정 보존. frontend의 routines.js/RoutinesPanel.jsx/App.jsx는 삭제된 지점별 이유와 복구 행동·이전 예상 시간 비노출을 연결한다. JourneyComparison.jsx는 저장 장소 모드·단계 안내·기존 홈의 무관한 출발지 배제·PATCH 성공 ID/active/version 검사·409/404 최신 목록 재조회 행동을 추가했다. styles.css는 안내14px/--ink를 범위 한정 적용한다.
- 검증: backend/tests/test_routines.py의 공유 루틴/출입구 변경·무관 루틴 유지·이름만/동일값 유지·스냅샷/일정 보존·옛 후보409·새 후보 PATCH200 active 복구 신규1개 포함 루틴13개 통과. 전체 unittest130개 통과(실제 PostgreSQL 전용 격리 스키마/ASGI, 공급자 합성). 프론트는 삭제 안내/복구/최신 목록 재조회·409/404 단일 PATCH/POST 없음·저장 모드/무관한 초기 출발 배제 신규4개 포함17파일142개 통과. 기존 복구 테스트의 버튼 이름을 새 표현에 맞췄다. npm run build1902모듈 통과.
- 시각/실행: 실제 컴포넌트의 합성 QA 페이지로 PC1440×1000·모바일390×844 목록 안내/복구 단계/진입·취소·이전 예상값 비노출·넘침0·콘솔error0을 확인했다. 안내 글자14px 보정 후 PC/모바일 재확인. 임시 페이지/탭 제거·viewport 복원. routine-recovery-mobile.png 보관. 프로젝트 uvicorn 프로세스를 확인 후 숨김 재시작해 현재 코드 적용, health200/서버 시작 로그 확인. 기존 사용자 DB 자료를 직접 수정하지 않았다.
- 명세 동기화: Notion v0.49의5.3.3·장소 location_version 설명·공통 구현 상태·변경 이력을 최종 갱신하고 재조회로 저장 확인. api_contract.md는 최종 본문과 기계 비교해 복사했다. planning/screen_plan/design_guide/routine_api/backend README·todo/feature_breakdown 동기화. API 경로·필드·인증·소유권·시간/계산·보관·DDL 및 클라이언트 호환성 변경 없음. 장소 수정 후 상태 전이와 사용자 복구 흐름 확장이다.
- 배운 개념: 위치 근거 버전과 화면 편집 버전을 분리하면 이름 변경으로 경로를 불필요하게 무효화하지 않는다. 상태/버전 변경은 장소 쓰기와 한 트랜잭션으로 묶어야 오래된 후보 저장을 막을 수 있다. 복구는 최신 후보로 기존 루틴을 PATCH하며 진입/취소만으로 자동 저장하지 않는다.
- 범위/남은 일: F06-04 완료. 실제 카카오 재호출/실제 브라우저 DB 복구는 이번 작업에서 재실행하지 않았다. 실제 운행 변경 자동 감지·실시간/AI 출발 안내는 후속, 과거 active 스냅샷의 위치 일치는 근거 없이 추정/백필하지 않았다. 사용자 MR/병합 후 다음 F05-01 도보 근거 수집.
- 명세: https://app.notion.com/p/3ebace1670c6806c8199cde33ebfbdfa

## 2026-10-08 — 백엔드 3계층 구조 리팩터링 (Spring 스타일, 사용자 요청)

- 목표/이유: Java/Spring 경험자인 사용자가 FastAPI 백엔드의 내부 구조를 Spring 친화적 3계층(Controller/Service/Repository)으로 재구성하도록 요청했다. 기존 라우터 파일(auth.py 등 9개)은 Pydantic DTO·SQL·비즈니스 로직·라우트가 한 파일에 섞인 fat router 상태였다.
- 범위 결정: Python→Java 재작성이 아니라 FastAPI 유지 + 계층 재배치로 확정했다. API 계약 변경이 전혀 없으므로 AGENTS.md 3절에 따라 Notion 명세(v0.49 확인)를 수정하지 않는다. 순수 내부 구조 재편이다.
- 기준: 최신 main c51d0b7(사용자가 codex/routine-recovery 병합 완료 확인)에서 helpycode/three-tier-refactor 생성. 착수 전 Notion v0.49·todo.md를 확인했고 리팩터링 전 백엔드 전체 테스트 130개 OK를 기준선으로 기록했다.
- 새 구조: app/common/(errors·timeutil·database·response·http·request_logging), app/auth/(dto·repository·security·service·router), app/places/(dto·provider·repository·service·router), app/origins/(dto·repository·service·router), app/journeys/(dto·models·provider·repository·service·router), app/routines/(dto·repository·service·router), app/main.py는 라우터 조립·미들웨어·전역 예외만 남긴다. router는 요청 파싱/응답 봉투만, service는 비즈니스 규칙(멱등·버전 충돌·만료·할당량), repository는 SQL 전담, provider는 카카오 클라이언트, auth/security.py는 세션/CSRF/레이트리밋/인증 공통(Spring Security 역할)이다.
- 이전 원칙: SQL 문자열·오류 코드/메시지·상태 전이·트랜잭션 경계·잠금 순서(routine-write·journey-admission advisory lock)를 한 글자도 바꾸지 않고 이동했다. 응답 봉투 {data,meta}·{error,meta}·X-Request-ID·Cache-Control·ISO UTC 시각 표현 유지로 프론트 무수정 호환을 보장한다.
- 테스트 이전: 9개 테스트 파일의 import를 새 계층 경로로 수정했다. DB 격리 패치 대상을 auth.connect_db→app.common.database.connect_db로, 패치 대상 places.provider_search→app.places.provider로 옮겼다. 테스트 시나리오·단언은 변경하지 않았다.
- 확인된 계약 유지: migrations/env.py·check_db.py의 connect_db 경로만 갱신, Alembic 0001~0008·DB 스키마·Docker 구성 무변경. backend/README.md의 구조 설명을 새 계층에 맞춰 갱신했다.
- 실제 검증: 리팩터링 후 unittest discover 전체 130개 OK(기준선과 동일, 약 52초, 실제 PostgreSQL 격리 스키마/ASGI). OpenAPI 17경로·22엔드포인트 동일 확인. app import 스모크 및 uvicorn 진입 모듈 로드 확인. API 계약 테스트(test_api_contract) 포함 전 계약 응답 동등. Notion 명세 영향 없음(읽기만 수행, v0.49).
- 중간 수정 기록: 분리 과정에서 datetime import 누락(timezone) 2건(routines/service.py·origins/dto.py)을 테스트 실패로 발견해 수정했다. 로그에서 exception_type=NameError만 확인 가능한 프라이버시 설계 때문에 격리 스키마 재현 스크립트로 직접 트레이스백을 확인해 원인을 좁혔다.
- 배운 개념: Spring 3계층은 Controller(요청/응답)·Service(규칙)·Repository(영속성)로 책임을 나눈다. Python에서는 패키지당 router/service/repository 파일로 같은 관심사 분리가 가능하다. 계약 테스트가 남아 있으면 구조 리팩터링의 안전망이 되고, 예외 메시지를 로그에 남기지 않는 설계에서는 재현 스크립트가 디버깅 도구가 된다.
- 남은 일/다음: 사용자 MR/병합 검토 대상. 기능 순서는 기존대로 F05-01 도보 근거 수집이 다음이다. F04-04(환승·출입구·플랫폼)·GPS 자동 판정·메일 인증/복구는 기존 보류 유지.
- 명세: https://app.notion.com/p/3ebace1670c6806c8199cde33ebfbdfa (v0.49, 변경 없음)
## 2026-10-08 — R02 서버 재시작 및 독립 재검토

- 요청: 사용자가 3티어 리팩터링 후 실제 서버를 껐다 켜고 잘못된 부분을 확인하도록 요청했다. 검토 대상은 helpycode/three-tier-refactor의461825d이며 코드 변경 없이 점검했다. 최신 Notion v0.49·TODO·R02 일지·README와 router/service/repository·인증/DB 경로를 확인했다.
- 서버 실행: 기존 프로젝트 uvicorn 프로세스3296의 실행 경로를 확인 후 종료하고 같은 프로젝트 가상환경/진입점으로 숨김 재시작했다. 새 서버17664의 시작 완료 로그와 localhost8000 health200을 확인했다. frontend5173은 기존 실행을 유지했다. 사용자 입력/개인 DB 데이터는 수정하지 않았다.
- 실제 검증: check_db.py에서 PostgreSQL17.11 연결 성공. 백엔드 전체130개 테스트 OK(실제 DB 격리 스키마/ASGI), 프론트17파일142개 OK, Vite1902모듈 빌드 성공. 실제 HTTP health200·me/places/routines 비로그인401 AUTH_REQUIRED·origin-validations GET405를 확인했고 일반 API의 응답 meta/X-Request-ID 일치 확인. OpenAPI200·17경로23동작 확인. 기존 브라우저 홈은 로그인 안내 상태로 정상 표시. 테스트 로그의 /_test/broken500/ValueError는 의도된 오류 처리 검증이며 실제 서버 장애가 아니다.
- 검토 발견: backend/app/journeys/service.py:30(check_refs),39(resolve)에 connection.execute SQL2개가 남아 있다. 런타임 동작 오류는 아니지만 README/R02 완료 근거의 'repository가 SQL 전담'과 다르다. 각 SELECT와 FOR SHARE 잠금을 그대로 repository 함수로 옮겨 service가 호출하도록 마무리할 필요가 있다. 실제 계층 완료 기준이 남아 있으므로 TODO/feature_breakdown의 R02 체크를 해제하고 부분 완료로 기록했다. 이번 요청은 재시작·검토이므로 코드 수정은 수행하지 않았다.
- 명세 영향: API/DDL/인증/계산/보관 계약 변경 없음. 최신 Notion v0.49는 확인만 했으며 갱신하지 않았다. 외부 공급자 실제 경로 재호출/로그인한 브라우저의 전체 저장 흐름은 이번 검증에서 재실행하지 않았다. 기존 회원/장소/루틴을 정리하거나 재생성하지 않았다.
- 배운 개념/다음: 계약 회귀 테스트 통과는 실행 호환성의 근거이며 계층 책임 분리 완성의 증거와 별개다. SQL 경계의 정적 검사로 누락을 찾을 수 있다. R02 SQL2곳 위임 후 관련 회귀·완료 체크 복원, 그다음 기존 F05-01 순서를 유지한다.
- 명세: https://app.notion.com/p/3ebace1670c6806c8199cde33ebfbdfa

- OpenAPI 추가 대조: 이전 main c51d0b7도17경로23동작으로 현재와 같다. R02 최초 일지의22엔드포인트는 집계 오류다. SearchInput의 패키지 경로 변경으로 schema 참조 이름2종은 달라졌지만 참조를 펼친 실제 경로/입력/응답 계약은 동일함을 비교했다.
## 2026-10-08 — R02 SQL 계층 분리 마무리

- 요청/기준: 사용자가 남은 SQL2곳을 새 브랜치에서 수정·커밋·푸시하도록 요청했다. 작업 시작 시 TODO·기획/루틴 문서·R02 README/일지와 최신 Notion v0.49를 확인했다. 리팩터링/재검토가 main9945068에 병합돼 최신 origin/main에서 codex/journey-repository-boundary를 생성했다.
- 변경 파일/이유: backend/app/journeys/repository.py에 find_place_version_for_share·find_owned_place_for_share를 추가하고 service.py의 check_refs/resolve에서 호출한다. saved_places의 본인 user_id 조건·place_id 파싱·SELECT 열·FOR SHARE 잠금·fetchone·기존 connection 전달을 유지했다. 트랜잭션/404·409 판단은 기존 service에 남긴다. API 경로/입출력/권한/오류/상태/시간/보관/DDL 변경 없음.
- 실제 검증: unittest discover 전체130개 통과(실제 PostgreSQL 격리 스키마/ASGI, 경로 버전·소유권·만료·루틴 복구 회귀 포함). AST 정적 검사에서 router/service/dto/security의 execute/executemany 직접 호출0건 확인. 이전 HEAD와 변경 파일의 SQL 문자열 전체를 비교해 동일함을 확인했다. 기존 프로젝트 uvicorn을 식별 후 숨김 재시작하고 실제 health200/status=ok·meta/X-Request-ID 일치 확인. 프론트/UI 변경이 없어 프론트 테스트와 시각 검증은 이번 작업에서 반복하지 않았다. 실제 카카오 추가 호출/사용자 DB 자료 변경 없음.
- 문서/완료: 개발 일지와 TODO/feature_breakdown의 R02 완료 체크를 복원했다. 최신 Notion v0.49를 게시 전 재확인하며 내부 책임 분리이므로 명세 갱신이 불필요하다. 기존 R02 재검토 기록은 당시 발견 근거로 유지한다.
- 배운 개념/다음: 같은 connection을 repository에 전달하면 SQL 책임만 옮기면서 기존 트랜잭션/잠금 수명을 유지할 수 있다. 서비스가 조회 결과의 업무 규칙을 판단하고 repository는 저장소 접근을 담당한다. 사용자 MR/병합 후 다음 F05-01 도보 근거 수집, 이번 SQL 분리의 미완료 항목 없음.
- 명세: https://app.notion.com/p/3ebace1670c6806c8199cde33ebfbdfa (v0.49, 계약 변경 없음)

## 2026-10-12 — F05-05 같은 조건의 저장값 재사용

### 목표와 명세 확인

검증된 같은 물리 경로의 유효 산정값을 재사용해 AI 호출을 생략한다. 작업 시작 시 todo.md·Notion v0.54 최신5.5.3/5.6·walking_api.md·personalization.md·ai_prompts.md·logging.md·기존 저장/검산/정책 코드를 확인했다. 최신 main2690526에서 codex/walking-cache-reuse를 만들고 아직 main에 없는 F05-04 12d9e99를 d34b3e2로 포함했다. 사용자 지시에 따라 MR 생성/병합은 수행하지 않는다.

### 구현과 변경 파일

- backend/app/walking/cache_service.py, history_dto.py: 호출 서비스가 확인한 공급자/경로/버전·양끝 출입구·조건 식별자를 strict 검증한다. 사용자별 장소 위치 버전/방향/범위·기준/필요 속도·정책/프롬프트/모델 버전을 키에 포함하고 일시 candidate/evidence/request ID는 제외한다. 미확인 근거와 이전 이력은 재사용하지 않는다. 프로필만 변경된 유효 원본은409 PROFILE_RECALCULATION_REQUIRED로 AI 없이 차단한다.
- history_service.py, history_repository.py: 전체/부분 적중을 검산해 현재 ID로 연결하고 누락 후보만 AI에 전달한다. 원본 estimate/revision ID와 기한을 유지하고 현재 근거 기한이 짧으면 반환 기한만 줄인다. numeric revision 복제/원본 만료 연장 없음. 최소 연결을 실행 이력에 보관하며 전부 적중한 모델/지연/사용량은null이다. 원본 삭제/만료 재실행 차단, 입력/Context/cache_sources/연결 멱등 비교, 사용자/request_id와 정렬된 물리 키의 세션 잠금, 저장 직전 재검사를 구현했다. 긴 계수는 검증된 float의 십진 표현을 Decimal로 DB NUMERIC에 전달한다.
- backend/migrations/versions/0010_walking_cache.py: nullable cache_key/cache_identity 쌍·조회 인덱스와 reused_estimates 기본[]/배열 제약 추가. 미확인 legacy 이력은 백필하지 않는다. 기존4테이블 소유권FK·90일 청소/회원CASCADE 유지.
- backend/tests/test_walking_cache.py: 신규18개 실제 격리 PostgreSQL/합성 AI 검증. test_migrations.py:0009 legacy 행을 보존한0010 적용/복구/재적용을 추가했다.
- api_contract.md, walking_api.md, personalization.md, ai_prompts.md, logging.md, database_schema.md, migrations.md, planning.md, README.md, todo.md, feature_breakdown.md: 내부 입력/응답·재사용/멱등/잠금/프로필 변경·품질/마이그레이션 및 현재/다음 작업 동기화. UI·프롬프트 문구/버전·공개 GET 응답 변화 없음.

### 실제 실행과 결과

- 기존 도보 이력16개 회귀:9.475초 통과. 초기 캐시14개에서 두 번째 회원 fixture 이메일 중복을 고쳤다. 거리/속도 DB 전달의 작은 소수 정밀도 차이는 기존F05-03과 같은 rel_tol=1e-12/abs_tol=1e-9로 검산하며 최종 정수초/계수는 정확히 비교한다.
- 추가 fallback/버전/호출 중 원본 만료 검증을 포함한17개:11.542초 통과. 긴 계수18번째 검증은 환경의 실제 float 표현을 기준으로 저장 보존을 확인하도록 바로잡았다. 마이그레이션 legacy JSON의 SQLAlchemy 문자열 바인딩 오류는 jsonb_build_object로 해결했다. 실패한 중간 실행을 성공으로 기록하지 않는다.
- 최종 backend/.venv/Scripts/python.exe -m unittest discover -s backend/tests:202개 전부 통과,78.408초. 신규18개 포함. 전체/부분 적중 AI 생략·ID 재연결·원본 기한·소유권·장소 이름/위치/삭제·경로/출입구/조건/버전 변경·프로필 변경·fallback/긴 계수·만료/삭제 재실행·호출 중 원본 만료 롤백·다른 실행ID의 같은 경로 잠금·실패 잠금 해제를 확인했다. 마이그레이션 격리 왕복/legacy 보존도 통과.
- AST 검사:history_service.py/cache_service.py/router.py 직접 SQL 실행0건. git diff --check 통과.
- 실제 개발DB migrate.py upgrade head 성공,0010_walking_cache 확인. 전후 users20/saved_places35/routines12, ai_executions0/walking_paths0 유지. 실제 사용자 산정이나 품질 데이터를 생성하지 않았다.
- 프로젝트 백엔드 프로세스를 확인 후 재시작. 실제 health200·프론트5173 응답200·OpenAPI GET 유지·비인증 도보 GET401 AUTH_REQUIRED 확인. UI 변경이 없어 PC/모바일 시각 검증은 새로 수행하지 않았다. 추가 AI/카카오 네트워크 호출 없음.

### 명세 동기화·배운 개념·남은 일

구현 전 Notion v0.55에 내부 cache_sources·물리 키·전체/부분 적중·원본 기한·최소 연결/멱등/동시 실행 계약을 기록했다. 최종 검증 상태/예시 설명/변경 이력을 갱신하고 다시 읽어 저장을 확인했다. api_contract.md 전체1498줄과 Notion 본문을 줄별 대조해 일치를 확인했다. 공개 GET의 reused=false는 수동 조회 계약으로 유지하며 내부 실행의 적중은reused=true이다. 명세: https://app.notion.com/p/3ebace1670c6806c8199cde33ebfbdfa.

캐시의 핵심은 일시 요청ID 대신 검증된 물리 식별자와 버전을 쓰는 것이다. 재사용은 원본 숫자/기한을 바꾸는 새 계산과 구분하고, 부분 적중의 멱등 재실행에는 기존/신규 원본 연결이 모두 필요하다. 부동소수 DTO 값과 PostgreSQL NUMERIC의 전달을 구분해 검산 계약과 저장 정밀도를 유지한다.

현재 실제 walking.evidence는 물리 범위/방향 미확인으로 needs_data·reusable=false이며 운영 캐시·사용자 산정 생성·출발 안내 연결은 아직 미구현이다. 완료 범위는 검증된 서버 내부 근거에 대한 F05-05 모듈과 이력이다. 다음은 F05-06 개인 계수만 변경된 기준 시간 재계산이며 F07 화면 내 출발 안내/실제 물리 근거 확보·F09 학습은 후속이다.

## 2026-10-13 — F05-06 개인 계수 변경 재계산

### 목표와 선행 명세

개인 계수/프로필 버전만 변경되면 저장된 기준 초로 재계산하고 원본 숫자와 기한을 보존한다. todo.md F05-06·최신 Notion v0.55의5.5.4/5.6·personalization.md4절·walking_api.md·planning.md·ai_prompts.md·logging.md·저장/캐시/검산 코드를 확인했다. Notion spec-to-implementation 스킬을 읽고 요구와 검증 근거를 연결했다. 최신main2690526에서 codex/walking-profile-recalculation을 생성하고 미병합 F05-04 d34b3e2/ F05-05 a59dab3를 f1c7bf2/ebbb944로 포함했다. 사용자 규칙대로 MR 생성/병합은 하지 않는다.

### 구현 및 파일

- backend/app/walking/cache_service.py: 같은 물리 키의 유효 원본에서 계수/프로필 버전만 변경되면 저장된 Decimal 기준 초 × 새 계수를 올림한다. 기본1.0·허용0.5~2.0, 이미 개인화된 공급자 기준은1로 유지한다. 현재 최종값에 계수를 또 곱하지 않는다. 원본 수치/버전/프로필/키/기한을 검증하며 프로필 다른 필드 변경은 내부409 차단한다. 만료/물리 조건/필요 속도 변경은 현재 검증 근거의 새 산정으로 연결하고 미확인 근거는needs_data를 유지한다.
- history_service.py, history_repository.py, history_dto.py: 같은 estimate에 revision_no 증가·parent_revision_id·현재 candidate_id·새 프로필·source=profile_recalculation을 저장한다. 원본 숫자/경로/최초 AI 버전과 만료/보관 기한을 보존한다. 재사용/재계산/새 후보가 섞이면 새 후보만 AI 호출. 호출 없는 실행 메타데이터는null. 재계산 전후 확인·멱등·동시 물리 키 잠금·삭제/만료 재실행 차단·롤백 유지. 저장된 십진 기준의 재계산과 신규 AI 검산을 구분하며 결과ID 불일치의502 AI_OUTPUT_INVALID 계약을 유지한다. GET 기존 필드/인증/no-store/reused=false를 유지하고 source enum에 새 값을 추가했다. 내부 estimates에도 source를 제공한다.
- backend/migrations/versions/0011_walking_recalculation.py: source 제약 확대, 부모의 동일 회원/estimate 복합FK·candidate_id·출처별 부모 제약. 기존 AI 원본은 부모null, 회원/부모삭제CASCADE. downgrade는 파생 revision만 제거하므로 실제DB에서는 실행하지 않았다.
- backend/tests/test_walking_recalculation.py: 신규19개 실제 격리 PostgreSQL/ASGI·합성 AI. test_walking_cache.py의 기존 계수 변경 차단을 새 재계산 기대값으로 맞췄고 test_migrations.py head0011로 갱신했다. test_routines.py는 기존 생성시각 순서 가정을 고정 시각과 의도적인 동률/UUID 경계로 안정화했다. 루틴 API 구현/정렬 계약은 바꾸지 않았다.
- api_contract.md, walking_api.md, personalization.md, ai_prompts.md, logging.md, database_schema.md, migrations.md, planning.md, README.md, todo.md, feature_breakdown.md: 새 내부 흐름/계산/이력/호환성·현재/다음 작업 동기화. 프론트/프롬프트 문구·모델 버전 변경 없음.

### 실제 실행 및 검증

- 시작 시 Docker Desktop이 꺼져 PostgreSQL 연결이 실패했고 초기 캐시18개가 connection timeout으로 실패했다(90.308초). 이를 성공으로 기록하지 않는다. Docker를 숨김 기동하고 프로젝트 compose db를 켜 healthy를 확인했다.
- 초기 신규 재계산15개:8.883초 통과. 캐시18개 회귀:11.084초 통과. 부모FK/마이그레이션 복구/source enum/출력ID 오류502까지 포함한 최신 재계산19개:9.468초 통과.
- 최초 전체220개에서 기존 루틴 목록 테스트1개가 생성 순서=시간 순서를 가정해 실패했다(89.860초). 고정 시각/UUID 동률 경계를 제공한 뒤220개 통과(89.099초). 최신 출력ID 오류 검증까지 포함한 최종 backend/.venv/Scripts/python.exe -m unittest discover -s backend/tests:221개 전부 통과,88.249초.
- 기준300×1.1=330·연속 계수 변경 시 기준300 유지·기본/경계 계수/잘못된 입력·이미 개인화된 공급자·거리/속도 십진 올림·현재ID 연결·재사용/재계산/새 산정 혼합(새 후보만AI)·부모FK·기한/소유권/위치/프로필·호출 중 원본 만료 롤백·삭제/멱등·동시 실행/실패 잠금 해제·GET source·출력ID502를 확인했다. 파생을 만든0011→0010→0011 격리 복구에서도 원본360초 보존, 재적용 부모null을 확인했다.
- AST history_service.py/cache_service.py/router.py 직접SQL 실행0건·git diff --check 통과.
- 실제 개발DB upgrade head0011_walking_recalculation 성공. 전후 users20/saved_places35/routines12·ai_executions0/walking_paths0 유지. 실제 사용자 산정/이력 생성 없음. Docker 재기동으로 자동 실행된 다른 컨테이너의 데이터/설정은 조작하지 않았다.
- 꺼져 있던 backend8000/frontend5173을 숨김 기동하고 최종 백엔드를 재시작했다. 실제 health200·프론트200·비인증 GET401 AUTH_REQUIRED·OpenAPI source=[ai_estimate,profile_recalculation] 확인. 추가 외부 AI/카카오 호출 없음. UI 변경이 없어 PC/모바일 시각 검증은 새로 수행하지 않았다.

### 계약·학습·남은 범위

구현 전에 Notion v0.56에 재계산/부모이력/십진 기준/무효화/호환성 초안을 기록했다. 최종 상태·예시·공통 source/변경 이력을 갱신하고 다시 읽어 저장을 확인했다. Notion Markdown의 이스케이프된 물결/구분자 때문에 한 차례 문서 갱신/대조가 실패했으며 실제 저장 표기를 재조회해 반영했다. 최종 api_contract.md 전체1507줄과 Notion 본문이 줄별 대조에서 일치했다. 명세: https://app.notion.com/p/3ebace1670c6806c8199cde33ebfbdfa.

개인화 이전 기준과 개인화 최종값을 분리해야 반복 보정을 막을 수 있다. 저장된 십진 초를 사용하는 계수 재계산은 거리/속도를 다시 나누는 신규 AI 검산과 올림 경계에서1초 차이가 날 수 있어 각각의 계약으로 검증한다. 부분 실행은 모델 호출한 후보만 비용/지연으로 집계하고 부모 이력과 원본 기한을 유지해야 한다. source enum 확장은 신규 소비자가 두 값을 처리해야 하는 호환성 영향이며 현재 프론트는 해당GET을 쓰지 않는다.

완료 범위는 검증된 서버 내부 근거의 재계산과 만료/변경 분기다. 실제 walking.evidence는 물리 범위/방향 미확인으로 needs_data·reusable=false를 유지한다. 호출 서비스의 실제 지도 재조회/물리 검증·사용자 산정 생성 연결·F09 계수 학습·F07 출발 안내는 아직 후속이다. 다음 TODO는 F05-07 AI 실패/근거 부족/역 내부 누락 상태 안내다.

## 2026-10-13 — F05-07 도보 상태 화면 안내

### 목표·명세·작업 기반

선택 루틴과 후보 상세에서 개인 도보 시간이 확인되지 않은 이유를 설명하고 실패/만료의 기존 복구 동작을 유지한다. todo.md F05-07·최신 Notion v0.56·walking_api.md·기획/디자인 가이드/화면 계획·기존 JSX/CSS·프롬프트/로깅 정책을 확인했다. 선행 F05-04~06은main27a824c에 병합됐고, 해당 최신main에서 codex/walking-status-guidance를 생성했다. MR 생성/병합은 사용자 작업으로 유지한다.

### 구현과 파일

- frontend/src/components/WalkingGuidance.jsx: 공통 info-box/Footprints·고정 문구로 범위/방향 미확인·접근/환승/마지막 누락·입구/승강장 실내 이동·공급자0초 미확정을 설명한다. 저장 루틴의 요약에서 없는 상세 근거를 추측하지 않는다. 현재 루틴/후보의 AI 산정 미실행을 분명히 표시한다.
- frontend/src/app/App.jsx: 선택 루틴 요약 아래에 공통 안내 연결. 복구가 필요한 루틴은 이전 시간 비사용/새 장소·경로 선택 상태로 표시한다.
- JourneyCandidates.jsx: 유효 후보 상세에 공통 근거 안내 연결. JourneyComparison.jsx: 기존 실패 코드를 유지해 알려진 AI 검증/준비 실패와 공급자 시간 조회 오류를 고정 문구로 표시하고 검색 만료 시 이전 값 비사용을 설명한다. 공급자 오류를 AI 실행 증거로 표시하지 않는다. 기존 재시도/로그인/취소/늦은 응답 무시/기한/쿼터 동작은 유지한다.
- frontend/src/styles/styles.css: .walking-guidance 안에서만 제목/목록/줄바꿈/아이콘 축소 방지를 추가했다. 기존 CSS 변수·미색/초록·카드/버튼/폰트/내비게이션 유지. 실패의 기존 alert는 한 번만 알리고 보조 설명은 중복 알림을 하지 않는다.
- frontend/tests/components/WalkingGuidance.test.jsx·JourneyComparison.test.jsx: 신규19개 상태/상세/실패/만료 연결 검증. 원문·오류 코드·미확인 시각을 출력하지 않고 추가 모델 요청이 없음을 확인한다.
- api_contract.md, walking_api.md, planning.md, ai_prompts.md, logging.md, design_guide.md, screen_plan.md, README.md, todo.md, feature_breakdown.md: 사용자 흐름·상태/복구·비노출·현재/다음 작업 동기화. HTTP/API 입력/응답·인증·계산·DDL·보관 변경 없음.

### 실행 결과와 시각 확인

- 첫 전체 프론트161개에서 기존 실패 alert와 새 보조 안내 alert가 중복돼1개 실패했다. 보조 안내의 announce=false로 실제 오류 알림은 한 번만 유지하도록 고쳤다.
- npm --prefix frontend test -- --reporter=dot: 최종167개/19파일 전부 통과,11.41초. 기존148개와 신규19개를 포함한다. 알 수 없는 오류가 toString/constructor/__proto__와 같아도 객체의 기본 속성을 화면에 렌더링하지 않도록 Object.hasOwn으로 제한하고3개 회귀를 추가했다. 후보 상세/AI_OUTPUT_INVALID 고정 문구·오류 알림1개·자연 만료 후 후보 제거와 이전 시간 비사용·기존 재시도/이탈 회귀를 확인했다.
- npm --prefix frontend run build:1904모듈·480ms 빌드 성공. git diff --check 통과.
- bundled Playwright/실제 Edge를 사용해 합성 routine/journey API와 OriginSelector 위치 선택 fixture로 앱 전체를 렌더링했다. 실제 사용자 세션/장소/DB는 사용하지 않았다. 데스크톱1440×1000·모바일390×844 각각 홈 루틴 카드/후보 상세/AI 검증 실패/브라우저 시계 진행 만료의8화면을 캡처·이미지로 확인했다. 각 화면 가로 넘침0·페이지 런타임 오류0. 실제 휴대전화 GPS/실서비스 AI 실패 생성은 미검증이다.
- 시각 결과는 C:/Users/태휘/.codex/visualizations/2026/10/12/01a12d8b-b1b3-7dd1-83d9-e33fdf61b7ee/f57-{home,candidate,failure,expired}-{1440,390}.png에 보관했다. 임시 재현 스크립트는 TEMP/timeisnow-walking-visual.cjs이며 API/위치 선택을 모두 합성 fixture로 대체한다.
- 실제 backend8000 health200·frontend5173 응답200 확인. 백엔드 코드/DB 변경이 없어 이번 작업에서는 백엔드221개를 다시 실행하지 않았다. 추가 외부 AI/지도 호출·실제 사용자 산정/이력 생성 없음.

### 명세 동기화·배운 개념·남은 일

구현 전에 Notion v0.57에 화면 흐름·현재 미실행/누락/실내 이동·고정 오류/만료 복구·호환성 계약을 기록했다. 최종 상태/검증/변경 이력을 갱신하고 재조회해 저장을 확인했다. api_contract.md 전체1515줄과 Notion 본문이 줄별 대조에서 일치했다. 명세: https://app.notion.com/p/3ebace1670c6806c8199cde33ebfbdfa.

미실행·근거 부족·실패·만료를 분리해야 사용자가 불확실한 시간에 의존하지 않는다. 요약 응답에서 세부 누락을 추측하지 않고, 보조 안내를 추가할 때 기존 접근성 오류 알림을 중복하지 않아야 한다. 예측값 제공은 물리 범위/방향이나 출발 가능성을 검증했다는 뜻이 아니다.

완료 범위는 현재 루틴/후보 상태를 설명하는 UI와 알려진 실패/만료 표현이다. 현재 실제 walking.evidence는 needs_data/ready_for_estimation=false/reusable=false이며 실제 AI 공개 생성 API 연결과 물리 근거 확보는 후속이다. 실제 출발 시각은 아직 만들지 않는다. 다음은 F07-01 첫 탑승의 최신 도착 후보 연결과 이후 출발 안내 계산이다.

## 2026-10-13 — F07-01a 첫 탑승 도착 조회 기반, F07-01 전체 미완료

### 목표·사전 확인·범위 분리

F07-01 최신 도착 후보를 진행하기 위해todo.md·최신 Notion v0.57·public_arrivals_plan.md/provider_plan.md·personalization.md·policy_decisions.md·기존 진단/신선도/경로 모델을 확인했다. F05-07은main5be6426에 병합됐고 해당 최신main에서 codex/first-boarding-arrivals를 생성했다. MR 생성/병합은 하지 않는다.

현재 journey.v1은정류소 public_id/공공방향ID가null이고운영매핑저장소/호출자가없다. 경기queryTime은공식문서상정보요청시간이며원천생성시각이아니다. 따라서실제최신도착연결을완료라고표시할수없어F07-01을미체크로유지하고준비단계F07-01a만분리했다. 사전Notion v0.58에이제약/허용입력/응답/오류/기한을기록했다.

### 구현과 변경 파일

- backend/app/arrivals/dto.py: server-only Mapping(첫leg/양수공공ID·순번/목적방향·버전/검증/기한),arrival.evidence.v1/후보/응답모델. 공개입력으로검증플래그/공공ID를받지않는다.
- provider.py: 고정경기공식HTTPS·DATA_GO_KR_SERVICE_KEY·3초·256KiB·리다이렉트/HTTP자동전환금지. stationId/routeId/staOrder/routeDestId가일치하는유일행과RUN의양수초/차량ID를검사한다. 분/0/음수/결측/미확인운행상태를시간으로만들지않는다. 중복JSON키/비정상상수/스키마/중복차량502, 공급자/전송503,시간초과504. queryTime을원천시각으로반환하지않는다. 원문/번호판/키/URL로그없음.
- service.py/repository.py/router.py·main.py: 본인/활성회원/검색기한·후보스냅샷/첫교통leg·장소버전·매핑기한을호출전후확인한다. 현재공개GET /journey-searches/{search_id}/candidates/{candidate_id}/first-arrivals는버스미매핑/지하철미지원·후보없음·guidancefalse를반환하고공급자를호출하지않는다. 선택적내부검증매핑이있을때만조회한다. 수신/검증생성120초중이른기한과검색/매핑기한을적용하고경계120초까지만유효하다. 미확인/naive/미래시간은최신으로바꾸지않는다. 검증된생성시각만절대ETA기준으로쓰고지난예측을탑승/놓침관측으로만들지않는다. 현재경기조회는생성시각없음·ETA null·guidancefalse다.
- backend/tests/test_first_arrivals.py: 신규17개실제격리PostgreSQL/ASGI·합성상류검증. 실제공급자조회/키전송은하지않았다.
- arrivals_api.md,api_contract.md,planning.md,provider_plan.md,public_arrivals_plan.md,personalization.md,logging.md,README.md,todo.md,feature_breakdown.md: 준비단계계약·공식항목근거·검증상태/예시와남은운영매핑/원천시각연결을동기화했다. 신규DDL/DB저장·캐시·프론트/AI변경없음.

### 실제 검증

- 최초14개4.240초통과. JSON/크기/키없음/0차량과장소변경검증을추가한17개4.601초통과.
- backend/.venv/Scripts/python.exe -m unittest discover -s backend/tests:238개전부통과,104.254초. ID/초/운행상태·키/크기/전송오류·120초경계/초과·미래/naive/지난예측·미매핑무호출/본인/검색만료/장소변경전후·TTL무연장/원문비노출·OpenAPI를확인했다.
- AST service.py/router.py/provider.py 직접SQL 실행0건·git diff --check 통과. 신규SQL은repository한곳에만있다.
- 프로젝트백엔드를확인후재시작. 실제health200·프론트200·새GET비인증401 AUTH_REQUIRED·OpenAPI등록확인. DB head0011유지,회원20/장소35/루틴12·ai_executions0/walking_paths0확인. 실제사용자산정/도착/품질이력생성없음. 프론트변경이없어시각/프론트테스트를추가로실행하지않았다.
- 공식[경기버스도착항목매뉴얼](https://www.gbis.go.kr/gbis2014/publicService.action?cmd=mBusArrival)을2026-10-13웹으로재확인했다. queryTime은정보요청시간,예측초/순번/상태/목적ID가별도임을확인했다. 서울공식지하철자료페이지도열었지만새개인키전송/실조회는하지않았다. 공식문서조회와서비스실조회검증을혼동하지않는다.

### 명세 저장·배운 개념·남은 작업

최종Notion v0.58을갱신하고다시읽어F07-01a준비완료와F07-01전체미완료가저장됐음을확인했다. 중복5.7번호는5.9첫탑승근거로정리했다. api_contract.md 전체1529줄과Notion본문을줄별대조해일치를확인했다. 명세:https://app.notion.com/p/3ebace1670c6806c8199cde33ebfbdfa.

요청시각/수신시각과원천생성시각은다르다. 정상HTTP/예측초존재만으로최신정보와경로방향이검증됐다고할수없다. 방향/순번매핑은클라이언트의확인플래그나장소이름으로대체할수없으며,알수없는원천정보를그대로차단해야출발시각을만들어내지않는다.

F07-01a만완료다. F07-01전체는실제경로의공공ID/방향운영매핑·생성시각/시간대·실조회연결이없어미완료로유지한다. 경기어댑터만준비했으며서울버스/지하철운영연결·실시간화면·출발/환승/목표도착계산은후속이다. 다음F07-01b에서운영매핑과신뢰가능한원천시간을검증해야한다. 이번작업은준비코드/조회계약으로보고하며실제최신도착연결완료로보고하지않는다.


## 2026-10-13 — F07-01b 방향 진단 준비/실조회 승인 대기

목표: 첫 버스의 공공 노선/정류소/순번뿐 아니라 회차·종착 방향을 대조한다. 최신main c4794a6(F07-01a 병합)에서 codex/first-boarding-mapping을 생성했다. 시작 시 TODO·arrivals_api.md·public_arrivals_plan.md·최신 Notion v0.58 및 journeys/service.py/provider.py·기존 진단 코드를 읽었다. 기존 경로 정규화는 원문 좌표를 검증 후 버리고 공공 ID/방향을 null로 두고 있어 공개 GET은 계속 mapping_required다.

변경 파일: backend/route_mapping_probe.py에 방향 가설/도착 ID 대조, backend/check_gyeonggi_mapping.py에 유일 후보 노선 상세 조회와 방향/원천시각 미확인 요약을 추가했다. backend/tests/test_route_mapping_probe.py에 신규7개를 작성했다. arrivals_api.md·public_arrivals_plan.md·provider_plan.md·todo.md·feature_breakdown.md·api_contract.md에 승인할 구체적 실행과 미완료 상태를 기록했다. 앱 API/계산/저장 계약·DDL·프론트·AI는 변경하지 않았다. Notion v0.59에는 구현 상태와 승인 대기를 기록하고 저장 내용을 다시 읽었다.

실제 검증: 매핑 합성14개(기존7+신규7) 전부 통과0.001초. 도착 합성/격리DB17개 전부 통과5.054초. 왕복 양방향·회차 통과/승차·회차점 일관성/중복·순번 누락/중복/boolean·노선/정류소/종점 ID 충돌·순환/누락·정확한 유일 도착행을 검사했다. 전체 백엔드/프론트/시각 검증은 이번 변경 범위 밖이라 재실행하지 않았다.

실조회 포함 명령은 자동 승인 검토에서 실행 전에 거부됐다. 이유는 키/좌표를 외부 API로 전송하는 구체적 요청의 재승인 부재다. 거부를 우회하거나 실조회 성공으로 기록하지 않았다. 이후 별도 명령으로 외부 호출 없는 파일 작성과 테스트만 수행했다. 실제 공급자 호출·개인 키 전송은 이번 작업에서0회다. 요청 초안은 공개 판교역→성남시청 WGS84로 카카오1회+경기 최대9회, 총최대10회 HTTPS이며 사용자 저장 장소는 읽지 않는다. 키 전송·응답 제한·비노출 항목은 public_arrivals_plan.md에 상세 기록했다.

배운 개념: 정차 순서 유일성과 운행 방향은 별도 근거다. 회차점을 넘는 구간이나 회차점 승차는 단순 왕복 가설로 확인할 수 없고, 순환/지선/좌표 허용오차 정책도 별도로 검증해야 한다. 공식 routeDestId는 진행방향 마지막 정류소이며 queryTime은 원천 생성시각이 아니다. 진단이 성공해도 운영 전체 매핑/최신성 완료를 뜻하지 않는다.

남은 작업: F07-01b/F07-01 전체 미체크. 공개 실조회 사용자 승인 후 방향 후보 대조, 신뢰할 생성시각/공급자와 운영 매핑 정책을 확정한 뒤 코드 연결이 필요하다. Notion:https://app.notion.com/p/3ebace1670c6806c8199cde33ebfbdfa. 기존 F07-01a의 조회/계산 차단 계약과 클라이언트 호환성은 유지한다.


## 2026-10-13 — F07-01b 사용자 승인 후 공개 실조회

사용자 “해”는 직전 제시한 공개 판교역→성남시청 좌표/저장 키/카카오·경기 공식 HTTPS 최대10회 조회에 대한 명시 승인이다. 기존 codex/first-boarding-mapping 브랜치에서 backend/check_gyeonggi_mapping.py를1회 실행했다. 신규 기능 브랜치를 만들거나 범위를 확장하지 않았다. 승인 검토를 통과하고 명령은 종료코드1로 끝났다.

실제 출력: route_disambiguation_required, candidate_count=12. 코드상 카카오 경로1회·경기 노선 검색1회 후 후보 개수 검사에서 중단되므로 총2회다. 노선 정차 목록/상세/도착정보 호출은0회. 동명 후보12개가 최대6개 대조 한도를 넘었다. 현재 첫 직행 후보가 과거76번/5개 사례와 같은 노선인지 확인하지 않았으며 이름이나 원문을 추가 출력하지 않았다. 과거 사례를 현재 방향 성공 근거로 대체하지 않는다. 키/원문/차량번호 비노출, 실제 사용자 저장 장소·좌표 읽기 없음.

변경 파일은 api_contract.md·arrivals_api.md·public_arrivals_plan.md·provider_plan.md·todo.md·feature_breakdown.md·development_log.md의 결과/진행 상태 기록뿐이다. 최신 Notion v0.59를 다시 읽어 v0.60에 승인 해소/실제2회/12개 한도 초과와 방향·도착 미조회를 기록하고 저장 내용을 다시 읽었다. API/계산/저장 계약·코드·DDL·프론트 변경 없음. 이번에 합성 테스트를 재실행하지 않았으며 직전31개 통과를 신규 결과로 표시하지 않는다.

배운 개념: 첫 카카오 후보와 공공 동명 노선 개수는 매 실행 달라질 수 있다. 조회 성공과 유일 경로 매핑 성공은 다르며, 전체 후보를 대조하지 않고 일부만 골라 유일하다고 인증하면 안 된다. 무조건 호출 상한을 늘리는 대신 정류소/지역 등 검증된 기반정보로 후보를 좁혀야 한다.

현재 F07-01b/F07-01 전체 미완료. 승인 부족은 해결됐으나 이번 실행은 후보 초과로 중단되어 방향/실제 도착 연결을 검증하지 못했다. 다음은 근거 있는 후보 축소 전략과 호출 예산 설계, 이어서 원천 시각/공급자·운영 정책 검증이다. 명세:https://app.notion.com/p/3ebace1670c6806c8199cde33ebfbdfa.


## 2026-10-13 — F07-01b 정류소 기반 후보 축소

목표: 동명 노선12개를 일부만 골라 조회하지 않고, 승차 정류소 기반정보로 후보를 좁힌다. 시작 시 TODO·AGENTS·최신 Notion v0.60·arrivals_api.md/public_arrivals_plan.md·planning/logging 관련 정책과 기존 진단/기반정보 도구를 확인했다. git fetch 후 main c4794a6이 유지됐고 동일 미완료 F07-01b의 codex/first-boarding-mapping 브랜치에서 계속했다. 공식 경기 정류소 검색/경유노선 매뉴얼을 웹으로 읽어 순번/진행방향 마지막 정류소 필드를 확인했다.

구현: backend/route_mapping_probe.py의 boarding_candidates/station_route_scopes/scoped_matches는 이름+진단 좌표로 근처 정류소 전체를 최대2개 유지하고 경유 노선 ID/순번/방향을 전체 정차 목록과 대조한다. 중복 ID 좌표 충돌·같은 방문의 종착 충돌·결측/boolean/범위 초과를 거부하고 반복 방문은 별도 순번으로 구분한다. 가장 가까운 후보만 선택하지 않는다. backend/check_gyeonggi_mapping.py는 전역 노선 검색을 제거하고 요청 예산1~10회 옵션·실제 요청 횟수·모든 후보 대조/후속2회 예약·결과4 무결과·권한 실패 무우회와 응답 목록 형태 제한을 추가했다. 방향 진단은 고정된 안전한 실패 사유를 제공한다. API/계산/DB/프론트/AI 변경 없음.

실제 검증: backend/tests/test_station_first_mapping.py14개0.007초, 기존/확장 test_route_mapping_probe.py15개0.002초 전부 통과. 근처 동명 양방향 보존/멀리 있는 이름 제외·결측/중복좌표·정류소 한도·경유노선 이름 정확일치·반복방문/충돌·유일한 station/route/order 매칭·최대10회/남은8회·예산초과 전체 무호출·권한403/무결과4 무우회·키/원문 비노출·실패 사유 보존을 확인했다. 전체 백엔드/프론트는 실행하지 않았다.

실조회 승인 검토: 기본 최대10회 명령은 기존2회 이후 새10회 요청의 구체적 재승인이 없다는 이유로 실행 전에 거부됐다. 명령은 실행되지 않아 호출0회다. 위험을 해소하는 대안으로 --max-requests 8과 합성 검증을 추가하여 최초 승인 누적10회를 넘지 않도록 제한했다. 해당8회 제한 명령은 승인 검토를 통과했다. 공개 판교역→성남시청·동일 고정 공식 HTTPS/키만 사용했고 개인 저장 장소/원문/키/차량번호를 출력·저장하지 않았다.

실제 출력: mapping_status=candidate_unique, candidate_route_count=1, boarding_station_count=2, matched_pair_count=1, start_distance_meters=4.29, end_distance_meters=12.85, board_order=12, alight_order=23, direction_status=direction_unresolved, arrival_rows=1, arrival_identity_matches=true, arrival_direction_matches=false, query_time_present=true, verified_generation_time_available=false, valid_for_guidance=false, request_count=7. 종료코드1. 카카오1/정류소검색1/경유노선2/정차목록1/상세1/도착1=7회, 기존2회 포함누적9회다. 정류소 기반 후보 축소/도착 ID 일치는 확인했으나 방향/원천 최신성을 인증하지 않는다. 이후 direction_reason 보완만 합성 검증했고 실조회 재실행은 하지 않아 이번 실패의 상세 원인은 아직 미확인이다.

문서: api_contract.md·arrivals_api.md·public_arrivals_plan.md·provider_plan.md·todo.md·feature_breakdown.md에 정책/호출예산/실결과·준비와 운영 연결 구분을 기록했다. Notion v0.61 갱신 후 다시 읽어 저장을 확인했다. 앱 API/계산/저장 계약·클라이언트 호환성 영향 없음, 구현/진단 상태만 갱신했다. 명세:https://app.notion.com/p/3ebace1670c6806c8199cde33ebfbdfa.

배운 개념: 전국의 동명 노선 이름 대신 정류소 경유노선과 실제 방문 순번으로 검색 범위를 좁힐 수 있다. 좌표와 순서 유일성이 확인돼도 단순 왕복 회차 가설과 원천 최신성은 별도로 검증해야 한다. 예산 제한은 실패 호출과 이전 호출을 포함해 관리하고 일부 후보만 대조한 결과를 유일하다고 표시하지 않는다.

남은 문제: F07-01b/F07-01 전체 미완료 유지. 다음은 실제 방향 실패 상세 원인/노선 형태, 신뢰할 생성시각/공급자와 운영 정책 확인이다. 승인 누적9회로1회만 남았고 전체 진단 재실행은 예산 부족이다. 운영 매핑/저장/공개GET/실시간 화면·출발 계산은 이번에 추가하지 않았다.


## 2026-10-13 — F07-01b 방향 실패 사유 실확인

사용자 ㄱㄱ는 직전 제시한 동일 공개 경로/키/공식 HTTPS 추가 최대8회 조회의 명시 승인이다. codex/first-boarding-mapping에서 backend/check_gyeonggi_mapping.py --max-requests 8을1회 실행해 승인 검토를 통과했다. 카카오1/정류소검색1/경유노선2/정차목록1/상세1/도착1=7회 수행했다. 새 코드/기능은 추가하지 않아 기존 동일 기능 브랜치를 유지했다.

실제 결과: candidate_unique·노선1개·정류소2개·매칭1개·승차12/하차23·양끝 거리4.29m/12.85m·도착1행 ID/순번 일치. direction_reason=SIMPLE_RETURN_ENDPOINT_UNCONFIRMED·direction_unresolved·arrival_direction_matches=false·query_time_present=true·verified_generation_time_available=false·valid_for_guidance=false·request_count=7·종료1이다. 원문/키/차량번호를 저장·출력하거나 사용자 저장 장소/좌표를 읽지 않았다.

코드를 읽어 해당 실패 사유가 startStationId=endStationId 또는 첫/마지막 정차 stationId의 기점 ID 불일치 묶음 조건임을 확인했다. 어떤 개별 조건이 실패했는지는 출력되지 않아 미확인이다. 실제 운행 방향 오류/반대편 정류소라고 단정하지 않는다. 이번7회+이전9회=누적16회, 승인10+추가8=18회 중2회 잔여다.

최신 Notion v0.61·TODO를 읽고 명세 v0.62와 api_contract.md·arrivals_api.md·public_arrivals_plan.md·provider_plan.md·todo.md·feature_breakdown.md에 실결과/남은 범위를 기록했다. Notion을 다시 읽어 저장 확인했다. API/계산/저장 계약·코드·DDL·프론트/AI 영향 없음, 테스트도 재실행하지 않았다. 새 테스트 통과로 보고하지 않는다.

배운 개념: 진단 코드의 단순 왕복 가정 실패는 원천 데이터나 실제 운행 방향 오류의 증명이 아니다. 그룹화한 오류 사유를 구체적 필드/전제 검사와 분리해야 다음 조사를 정확히 좁힐 수 있다. 다음은 단순 왕복 전제와 실제 양방향 종점 구조를 분리하고 공식 경유노선 방향을 대조하는 작업이다. F07-01b/F07-01 전체 미완료·원천 최신성/운영 연결도 미완료다. 명세:https://app.notion.com/p/3ebace1670c6806c8199cde33ebfbdfa.


## 2026-10-13 — F07-01b 왕복 전제 분리

목표: 실제 SIMPLE_RETURN_ENDPOINT_UNCONFIRMED 사유와 단순 왕복 가정을 분리하고 공식 경유노선 방향을 실제 끝 정류소와 대조한다. 최신 Notion v0.62/TODO/route_mapping_probe.py·기존 테스트를 읽고 경기 공식 정류소 경유노선/노선 정차 목록 매뉴얼을 웹으로 다시 확인했다. git fetch 후 동일 미완료 기능 codex/first-boarding-mapping에서 계속했다.

변경: backend/route_mapping_probe.py direction_candidate의 선택적 scoped_direction은 공식 경유노선으로 좁힌 station/route/방문순번을 재확인하고 routeDestId와 해당 방향의 실제 마지막 정류소 ID를 대조한다. 기존 scope 없는 단순 왕복 가설은 유지한다. 실제 회차점 ID/노선 상세 routeId·연속 순번/회차 일관성·승하차/방향 경계 검증은 유지하고, 왕복 마지막 물리 정류소 ID를 canonical 기점과 강제로 같게 두지 않는다. canonical 종점의 물리 별칭도 방향 근거로 대체하지 않는다. 순환/회차 통과/회차점 승차·scope 충돌은 계속 차단한다. backend/check_gyeonggi_mapping.py는 해당 scope를 연결하고 고정 direction_basis/boolean return_endpoint_matches_start를 출력한다. 공개 API/운영 매핑/저장에는 연결하지 않는다.

실제 검증: backend/tests/test_route_mapping_probe.py21개0.003초, test_station_first_mapping.py15개0.009초 총36개 통과. 신규7개는 다른 왕복 끝 ID·canonical 종점 별칭·종착/방문 scope 충돌·회차 통과/승차·결측/boolean/순환·CLI 방향 대조와 guidance/production false 유지다. 이전 합성 회귀 포함 통과, 전체 백엔드/프론트는 재실행하지 않았다. 수정 후 외부 키 실조회0회이며 이전 실제 실패가 해결됐다고 보고하지 않는다.

문서: 최신 명세 v0.63·api_contract.md·arrivals_api.md·public_arrivals_plan.md·provider_plan.md·todo.md·feature_breakdown.md를 갱신하고 Notion 저장을 다시 읽었다. API/계산/저장 계약·DDL·프론트/AI·클라이언트 호환성 변경 없음. 진단/검증 구현 상태와 남은 실제 대조만 기록했다. 명세:https://app.notion.com/p/3ebace1670c6806c8199cde33ebfbdfa.

배운 개념: 왕복 양방향의 물리 정류소 ID는 같다고 가정할 수 없다. 공식 정류소 방문 방향 ID와 실제 정차 목록의 해당 방향 끝 정류소를 비교해야 하며 이름/노선 전체 종점을 대신 쓰면 안 된다. 합성 검증 통과와 실제 공급자 사례 해결은 별도다.

남은 작업: 누적16회/승인18회로2회 잔여, 전체 진단 재실행에는 부족하다. 동일 공개 경로/키/공식 HTTPS --max-requests 8로 추가 최대8회 검증 초안을 문서에 준비했다. 실제 방향/원천 시각·운영 매핑/출발 연결은 미완료라 F07-01b/F07-01 체크하지 않는다. 다음은 수정 진단의 실제 방향 대조다.


## 2026-10-13 — F07-01b 공개 방향 진단 성공

사용자 진행해는 직전 동일 공개 경로/키/공식 HTTPS 추가 최대8회 조회의 명시 승인이다. codex/first-boarding-mapping에서 backend/check_gyeonggi_mapping.py --max-requests 8을 실행해 승인 검토를 통과했다. 카카오1/정류소검색1/경유노선2/정차목록1/상세1/도착1=7회, 종료코드0이었다. 새 코드/기능은 추가하지 않아 동일 기능 브랜치를 유지했다.

실제 출력: candidate_unique·노선1개·정류소2개·매칭1개·승차12/하차23·거리4.29m/12.85m·도착1행. arrival_identity_matches=true, arrival_direction_matches=true, direction_status=direction_candidate, direction_reason=null, direction_basis=station_route_scope, return_endpoint_matches_start=false다. 왕복 끝 정류소 ID가 canonical 기점과 다름을 확인했으며 이전 단순 왕복 가정의 이 사례 차단이 수정 진단으로 해소됐다. 물리적 반대편 여부나 모든 노선 형태 지원을 단정하지 않는다.

query_time_present=true이지만 verified_generation_time_available=false·valid_for_guidance=false·production_mapping_validated=false를 유지한다. 경기 queryTime을 생성시각으로 대체하지 않는다. 이번7회+이전16회=누적23회, 승인10+8+8=26회 중3회 잔여다. 사용자 저장 장소/좌표 읽기·키/원문/차량번호 저장/출력 없음.

최신 Notion v0.63·TODO/arrivals_api.md의 남은 범위를 대조하고 v0.64와 api_contract.md·arrivals_api.md·public_arrivals_plan.md·provider_plan.md·todo.md·feature_breakdown.md를 갱신했다. Notion을 다시 읽어 저장 확인했다. API/계산/저장 계약·코드/DDL·프론트/AI·클라이언트 호환성 변경 없음. 테스트는 재실행하지 않았고 기존36개 결과를 신규 실행으로 보고하지 않는다.

배운 개념: 실제 정류소 방문 순번·공식 진행 방향 ID·해당 방향의 마지막 정류소를 함께 대조하면 canonical 노선 기점 ID의 왕복 동일성 가정을 제거할 수 있다. 한 사례의 방향 일치와 운영 전체 매핑/교통 정보 최신성은 별도 완료 조건이다.

F07-01b/F07-01 전체 미완료.100m 운영 허용오차·자동 매핑 저장/공개GET 호출 연결·원천 생성시각 확보가 남았다. 다음은 운영 매핑 정책/조회 연결 설계와 신뢰할 원천 시각 확보다. 명세:https://app.notion.com/p/3ebace1670c6806c8199cde33ebfbdfa.


## 2026-10-13 — F07-01b 경기 운영 매핑/본인 조회 연결

목표: 검증된 경로 근거를 실제 조회 API와 연결하며 경기 원천 생성시각 unknown은 출발 계산에 쓰지 않는다. 시작 시 TODO·최신 Notion v0.64·journeys/provider/service/repository 및 arrivals/provider/service/dto·연결 테스트를 확인했다. git fetch 후 main c4794a6 유지, 동일 F07-01b codex/first-boarding-mapping에서 계속했다. 사전 Notion v0.65에30m/연속 정차/공식 방향·메모리 수명/용량·GET 호출/오류/60초 재사용/갱신 제한과 이전 호환성 영향을 기록한 후 구현했다.

변경 파일: backend/app/arrivals/matching.py는 기존 진단 매칭을 공유 모듈로 옮기고 require_contiguous를 추가했다. backend/route_mapping_probe.py는 기존 진단 호환 import를 유지한다. cache.py는 본인/검색/후보/fingerprint·공개 버스 이름/양끝 점을 최근32검색/20후보·검색 기한으로 묶는다. 입력GPS/도보geometry·원문/키는 저장하지 않는다. 만료는 사용을 차단하고 다음 접근에 메모리를 정리한다. 재시작/다중프로세스/퇴출은 미매핑 복구다.

mapping.py는 고정 경기 HTTPS·3초/1MiB·매핑5초 예산·중복JSON/비정상상수/전송 오류/무결과4 구분과 정류소≤2/노선≤2·30m·전체 연속 이름/순번·공식 방향/회차/실제 끝 정류소를 검증한다. 총최대6회 매핑+1회 도착이다. journeys/provider.py는 선택적으로 첫BUS/단일차량의 최소 공개 근거를 추출하고 최종20후보만 남긴다. journeys/service.py는 DB 경로 저장 성공 후 메모리 근거를 게시한다. 실패/만료/검색 탈락이면 게시하지 않는다.

arrivals/service.py는 본인GET을 cache/자동매핑/기존 엄격 도착 어댑터와 연결했다. 동시 동일 후보는lock429/Retry-After2, 실제 갱신10회/분 HMAC 버킷·60초 수신 재사용·TTL/수신 시각 무연장·기한 단축을 적용한다. 매핑/도착/캐시 전후 회원/본인/장소·검색/후보 fingerprint/매핑 기한을 재검사하고 매핑 중 후보 변화는 도착 호출 전에409로 차단한다. 공개정류소ID/검증플래그를 받지 않고 생성시각unknown이면 ETA null/guidancefalse다. API 필드/CSRF/no-store·DB 경로/루틴 저장은 유지, 새DDL/프론트/AI/출발 계산 없음.

테스트: backend/tests/test_arrival_mapping_connection.py 신규16개9.167초 전부 통과. 첫 실행은 mock 원함수 참조/URL 문자열 타입/계정 중복 테스트 도우미 오류였고 수정했다. 스냅샷 테스트의 total_seconds만 변경하면 공통 모델 검증에서502가 나오는 것을 확인해 유효한 missing_segments 변화로 교체했다. 이후 호출 중 스냅샷 변화/검색 기한 단축 검사와30m 초과100m 이내·정류소 중간 누락을 엄밀하게 보강했다. 기존 도착17개/정류소15개도 통과. 중간 전체281개/282개 통과 후 최종 전체283개119.790초 전부 통과했다. 최종은 실제 격리 PostgreSQL/ASGI·합성 공급자이며 새로운 실제 키 조회0회다. 캐시 재시작/용량/소유권/fingerprint·스냅샷/장소/검색 만료·연속 정차/좌표/방향 충돌·전송/JSON/크기/누락 키/시간초과·쿼터/병렬·TTL/수신 무연장·응답/DB 경로 비변경·원문 비노출을 확인했다.

실행: 최종 코드로 기존 프로젝트 백엔드만 확인 후 재시작, launcher29912·health200·프론트200·비인증 first-arrivals401 확인. DB head0011_walking_recalculation·회원20/장소35/루틴12/ai_executions0/walking_paths0을 적용 전후 확인했다. 마이그레이션 없음. AST service/router/provider 영역 SQL 직접 실행0건·git diff --check 확인. 프론트 변경이 없어 시각 검증/프론트 테스트는 수행하지 않았다.

문서: API 목록/5.9 공통 조회와 구현 상태·오류/캐시/메모리/계산 차단·이전 API 호환성을 Notion v0.65에 맞췄다. api_contract.md·arrivals_api.md·planning.md·provider_plan.md·public_arrivals_plan.md·logging.md·README.md·todo.md·feature_breakdown.md를 동기화하고 Notion 저장을 다시 읽었다. 응답 필드/입력은 유지하지만 근거가 있는 새 검색의 GET은 공급자를 조회할 수 있어 이전 항상미매핑 동작은 변경됐다. 생성시각unknown으로 최신 도착/출발 안내 완료라고 표시하지 않는다. 명세:https://app.notion.com/p/3ebace1670c6806c8199cde33ebfbdfa.

배운 개념: 좌표를 DB에 영구 저장하지 않아도 검증한 최소 공개 교통 근거를 검색 수명에 묶어 매핑할 수 있다. 재시작/다중프로세스에서 메모리 근거가 없어지면 새 검색을 요구하는 제약이 있다. 수신 결과 재사용은 최초 수신/검색 기한을 연장하면 안 되고, 긴 매핑 조회 전후의 후보/장소 변화도 확인해야 한다.

남은 문제: F07-01b/F07-01 전체 미완료. 원천 생성시각/최신성·새30m/연속 정책과GET의 실제 키 통합검증·지원 범위 확대가 남았다. 이번 실제 키 사용0회, 기존 공개 진단 예산 누적23회/승인26회·3회 잔여다. 이전 공개 진단을 신규 정책/GET 실검증으로 대체하지 않는다. 다음은 신뢰할 원천 시각/공급자 확인과 새 운영 연결 실검증이다.


## 2026-10-13 — F07-01b 실제 키 통합검증 준비/원천 제약 확인

목표: 구현된 실제 경로 검색/자동 매핑/본인GET을 실제 키로 검증할 구체적 도구를 만들고 신뢰할 생성시각 공급자 근거를 확인한다. 시작 시 TODO·최신 Notion v0.65·check_public_arrivals.py·운영 mapping.py를 읽었다. 같은 미완료 F07-01b codex/first-boarding-mapping에서 계속했다.

변경 파일: backend/check_arrival_connection.py, backend/tests/test_connected_arrival_probe.py. 도구는 고정 공개 판교역→성남시청 입력·기존 격리DB/ASGI 인증 도우미로 임시 auth_test UUID 스키마에 합성 회원/경로를 만들고 실제 자동 매핑/본인GET·재조회/DB 무변경을 검증한다. 실제회원/장소/루틴을 변경하지 않으며 종료/실패 시 메모리/임시 스키마를 정리한다. 호출 예산1~10회·최대10회는 카카오 지역2/경로1+경기 매핑최대6/도착1, 실패 시도 포함이고 고정2호스트HTTPS만 허용한다. 원문/키/좌표/공공ID/차량번호/쿠키/예외 메시지는 출력하지 않는다. 운영 runtime/API/계산/저장 변경 없음.

검증: 처음 독립 테스트는 backend 모듈 경로가 없어 import 실패했고 경로를 명시해 수정했다. 초기4개0.001초 통과 후 전체 격리 흐름/정리·실패횟수/비노출까지 최종6개1.793초 전부 통과했다. 실제 PostgreSQL/ASGI·합성 공급자·외부 요청 강제 차단으로 원문 비노출/예산/대상/직행 선택/고정 입력·재조회 무호출/동일근거·검색 무변경·임시스키마 정리/기존 회원 개수 보존을 확인했다. 이번 전체283개를 재실행하지 않았으며 기존 결과와 구분한다. 실제 키 통합 실행0회/개인 키 전송0회다. 기존 공개 카카오/경기 예산은23/26회·3회 잔여라 전체실행 부족, 추가 최대10회 승인할 구체적 명령/목적을 public_arrivals_plan.md에 기록했다.

원천 연구: 경기 공식 항목 매뉴얼을 웹으로 다시 읽어 queryTime=정보요청시간과 행별 생성시각 계약 부재를 확인했다. 서울 지하철 공식 openApiView는 recptnDt=열차도착정보 생성시각/barvlDt=초 단위로 명시한다. 웹도구 HTTPS sample URL은 접근 불가로 나왔지만 로컬 연결 상태로 단정하지 않았다. 로컬 환경에서 공식 swopenapi.seoul.go.kr의 키/역명 없는 HTTPS HEAD1회·3초 timeout을 확인했다. 이 별도 무자격정보 전송 진단은 기존 개인키 카카오/경기 예산과 구분하며 서울키/HTTP 전송은0회다. 키 인증 오류나 모든 HTTPS 미지원으로 단정하지 않는다. 서울 역/노선/방향/시간대·지원범위·운영 전송 정책은 미확인이고 자동 공급자 대체/HTTP 전환을 하지 않았다.

문서: Notion v0.66·api_contract.md·arrivals_api.md·public_arrivals_plan.md·provider_plan.md·todo.md·feature_breakdown.md에 도구/검증/승인 대기·원천 제약·공식 링크를 갱신하고 Notion 저장을 다시 읽었다. API/계산/저장 계약·클라이언트 호환성 변경 없음, 개발 서버/프론트/DDL 변경 없음. 명세:https://app.notion.com/p/3ebace1670c6806c8199cde33ebfbdfa.

배운 개념: provider 단일 진단 성공과 실제 서버의 인증/검색/캐시/도착 흐름 통합 성공은 다르다. 실제 키 검증도 임시 스키마와 공개 입력으로 기존 개인 데이터와 분리할 수 있다. 생성시각 없는 응답은 정상 연결만으로 최신성을 확보할 수 없고, 다른 공급자의 생성시각 필드가 있어도 전송/시간대/방향을 검증해야 한다.

남은 작업: F07-01b/F07-01 미완료. 추가 조회 예산 승인 후 실제 연결 실행, 경기 원천 생성시각 제약을 해소할 공급자/전송 정책 확인이 필요하다. 도구 준비/합성 검증을 실제키 통합 성공으로 표시하지 않는다.


## 2026-10-13 — F07-01b 실제 키 연결 미매핑/중단 단계 확인

사용자 응은 직전 공개 판교역→성남시청·동일 저장 키/공식 HTTPS 추가 최대10회·임시DB 통합검증의 명시 승인이다. check_arrival_connection.py --max-requests 10을 실행해 실제6회·종료1이었다. HTTP200 mapping_required/unknown·후보0·generated_at_present=false/predicted_arrival_available=false/valid_for_guidance=false, second_get_no_upstream/second_get_same_evidence/stored_search_unchanged=true였다. 연결 성공이라고 기록하지 않았다.

현재 TODO·최신 Notion v0.66·mapping.py/CLI의 중단 조건을 대조하고 backend/app/arrivals/mapping.py에 선택적diagnostics를 추가했다. 고정 stage/reason와station/route/matched count만 수집하고 공개API/로그에 키/공공ID/좌표/원문을 노출하지 않는다. backend/check_arrival_connection.py는 임시DB에서만 trace를 연결한다. backend/tests/test_arrival_mapping_connection.py에 무노선/성공 trace의 안전한 키/사유·개수 검증을 추가했다. 관련17개9.095초·CLI6개1.629초 전부 통과, 전체회귀는 이번 재실행하지 않았다. 공개GET 정책/응답·계산/저장·프론트/AI 변경 없음.

당시 총승인36회=기존26+추가10, 실제누적29회=기존23+첫6회로7회 잔여였다. 이를 코드상 --max-requests 7로 강제해 승인 검토 통과 후 재검증했다. 실제6회/종료1: mapping_diagnostics stage=route_stations/reason=ROUTE_SEQUENCE_UNCONFIRMED/station_count=1/route_count=1/matched_count=0, HTTP200 mapping_required/unknown·후보0/생성·예측시각 없음/guidancefalse였다. 재조회 무호출/동일근거·검색무변경true 재확인. 누적35/승인36회로1회 잔여다. 생성시각에 도달하지 못한 도착 응답을 검증했다고 주장하지 않는다.

복합 매칭은 모든 정차 이름의 연속 순서·양끝30m·공식 방문scope를 함께 대조한다. 개별 실패 원인/실제 정류소 오류/경로 변경 여부는 이번 출력으로 단정할 수 없다. 매핑 정책을 낮추거나 미대조 후보를 선택하지 않았다. 임시스키마/프로세스 메모리는 두 실행이 정리 성공 후 반환했다. 실제DB head0011·회원20/장소35/루틴12·산정0을 확인했다. auth_test 패턴 스키마 총75개가 존재하는 것도 확인했다; 직전 격리 도구 테스트는 기존/종료후 스키마 개수 동일을 검증했으나 이75개의 생성 이력/원인은 이번 조사하지 않았고 무관한 기존 스키마를 삭제하지 않았다. 현재 도구의 임시 스키마 정리 성공과 전체 인스턴스에 임시 스키마가 없음을 혼동하지 않는다.

Notion v0.67 및 api_contract.md·arrivals_api.md·public_arrivals_plan.md·provider_plan.md·todo.md·feature_breakdown.md에 실제 실패/단계/개수·검증/예산을 갱신하고 저장을 다시 읽었다. API/계산/저장 계약·호환성 변경 없음. 명세:https://app.notion.com/p/3ebace1670c6806c8199cde33ebfbdfa.

배운 개념: 실제 카카오 후보 정렬/내용과 공식 정차 목록은 진단의 한 사례와 다를 수 있다. HTTP200 미매핑과 캐시 재사용 성공이 최신 도착 연결 성공을 뜻하지 않는다. 부족한 근거는 차단하고 내부 단계/개수를 통해 원인을 좁혀야 한다.

F07-01b/F07-01 전체 미완료. 다음은 정차/좌표/방문scope 중단의 개별 근거 확인과 신뢰할 원천 생성시각/공급자 확보다. 이번 실제키 통합검증은 실패(도착 미조회)로 보고하며 완료 체크하지 않는다.


## 2026-10-13 — F07-01b 매칭 불일치 원인 분리

목표: ROUTE_SEQUENCE_UNCONFIRMED 복합 검사를 이름/정차 순서/연속성/공식 방문scope/좌표/데이터로 나눈다. 시작 시 TODO·최신 Notion v0.67·mapping.py/matching.py를 읽었다. 같은 미완료 F07-01b codex/first-boarding-mapping에서 계속했다.

변경 파일: backend/app/arrivals/matching.py diagnose_match는 값 대신 고정 사유/개수만 반환한다. 순번 데이터·승하차 이름쌍·중간이름 순서/전체연속이름·공식 방문scope·좌표 결측/30m 초과·정류소ID 결측/통과쌍을 구분한다. 정류소200개/노선당500행 초과는 상세진단만 생략한다. mapping.py는 미매칭 실패이고 명시적diagnostics가 있을 때만 추가한다. 공개GET/매핑 수용결과/캐시/시간/저장 정책은 그대로며 추가 공급자 호출0회다. 원문/키/정류소 이름/좌표/공공ID를 반환하지 않는다.

검증: test_match_diagnostics.py 초기 독립 실행은 backend 경로 누락으로 import 실패했고 명시적 sys.path로 수정했다. 신규7개1.382초 통과 후 빈 정차 목록도 순번 데이터 부족으로 분리해7개1.273초 재확인했다. 기존연결17개9.280초·검증도구6개1.634초와 합계30개 전부 통과. 이름·중간 순서·비연속·방문scope의 노선/정류소/순번 충돌·좌표30m/결측·빈/중복순번·안전한 원인/개수/크기 제한·내부 진단에만 실행됨을 확인했다. 전체 회귀는 재실행하지 않았다. 이번 실제 키 호출0회로 실제 개별 원인이 확인됐다고 기록하지 않는다.

문서: Notion v0.68·api_contract.md·arrivals_api.md·provider_plan.md·public_arrivals_plan.md·todo.md·feature_breakdown.md에 진단/검증과 실제 재검증 대기를 동기화하고 저장을 다시 읽었다. 공개API/계산/저장 계약·프론트/DDL/AI/호환성 변경 없음. 명세:https://app.notion.com/p/3ebace1670c6806c8199cde33ebfbdfa.

배운 개념: 복합 매칭 실패는 한 가지 원인의 증명이 아니다. 정차 순서/연속성·공식 방문·좌표를 독립적인 개수로 분리해야 기준 완화 없이 원인을 좁힐 수 있다. 진단 코드 자체의 통과와 실제 실패 원인의 확인은 다르다.

남은 작업: 누적35/승인36회로1회 잔여, 전체실진단에 부족하다. 같은 공개 경로/저장키/공식HTTPS·임시DB check_arrival_connection.py --max-requests 8로 추가최대8회 승인할 구체적 실행을 준비했다. 실제 개별 불일치/도착 연결·원천 최신성은 미완료로 F07-01b/F07-01 체크하지 않는다.


## 2026-10-13 — F07-01b 정류소 목록 연속성 차단 실확인

사용자 “위의 추가조회해서 원인 확인해”는 직전 공개 경로/키/카카오·경기HTTPS 추가 최대8회 원인 진단의 명시 승인이다. check_arrival_connection.py --max-requests 8을 실행해 실제6회·종료1이었다. 같은 미완료 F07-01b 브랜치를 유지했다.

실제 결과: HTTP200 mapping_required/unknown·도착후보0·생성/예측시각 없음/guidancefalse, second_get_no_upstream/second_get_same_evidence/stored_search_unchanged=true. station_count=1/route_count=1/matched_count=0·detail_reason=STOPS_NOT_CONTIGUOUS. valid_sequence_routes=1/endpoint_name_pairs=2/ordered_name_pairs=2/scoped_ordered_name_pairs=2지만 contiguous_name_pairs=0/scoped_contiguous_name_pairs=0이다. 이름의 순서와 공식 노선/승차정류소/방문순번은 일치하는 쌍이 있으나 경기 목록 사이에 카카오 제공 목록 외 정류소가 포함되는 형태라 전체 목록 연속성 필수 정책이 차단했다.

최신 Notion v0.68·TODO와 diagnose_match 코드를 읽어 좌표/식별 검사 조건을 대조했다. missing_coordinates/outside_coordinate_limit/missing_station_identity/passing_pairs=0은 연속 일치쌍이 없어 해당검사 미실행임을 확인했다. 좌표가 맞거나 도착/방향/하차 반복방문이 유일하다는 뜻으로 해석하지 않는다. 해당 개별 단계는 아직 미확인이다.

제안/미구현: 전체 목록 연속성 필수 정책을 재검토하고 제공된 이름의 전체순서·공식 승차방문·양끝30m·회차/같은방향/반복방문·공식 방향ID/유일성을 유지하면서 공공 중간 정류소 추가를 처리한다. 이번 요청은 실제 원인 확인이며 코드/매핑 수용정책/공개API/계산/저장을 바꾸지 않았다. 테스트도 재실행하지 않았다.

사용자에게 설명한 것처럼 조회 상한은 검증 승인용 API 호출횟수이며 공급자 잔여쿼터/요금 예산이 아니다. 이번6회+기존35회=누적41회, 승인36+추가8=44회로3회 잔여다. 실제잔여쿼터/비용은 확인하지 않았다. 기존 사용자 데이터/장소를 변경하지 않고 키/좌표/공공ID/차량번호/쿠키/원문을 출력/저장하지 않았다. 도구는 임시스키마/메모리 정리 성공 후 반환했다.

Notion v0.69 및 api_contract.md·arrivals_api.md·provider_plan.md·public_arrivals_plan.md·todo.md·feature_breakdown.md에 실제 원인·미검사 범위·제안 상태·호출상한 의미를 기록하고 저장을 다시 읽었다. API/계산/저장 계약·클라이언트 호환성 변경 없음. 명세:https://app.notion.com/p/3ebace1670c6806c8199cde33ebfbdfa.

배운 개념: 같은 노선의 정류소 순서는 맞아도 공급자마다 제공 목록의 상세도가 다를 수 있다. 연속성 실패와 잘못된 순서/방문순번은 구분해야 한다. 뒤 단계 검사가 생략돼0개가 나오는 것과 실제 검사 통과는 다르다.

F07-01b/F07-01 전체 미완료. 다음은 연속 목록 조건 재검토·기존 방문/좌표/방향/유일성 검증 유지 구현과 실제 도착 연결 확인이다. 원천 생성시각/최신성 제약도 남았다.


## 2026-10-13 — F07-01b 추가 정류소 처리·방향 후 유일성

목표/근거: 실제 STOPS_NOT_CONTIGUOUS 조사 후 사용자 ㄱㄱ에 따라 공급자별 목록 상세도 차이를 처리했다. 최신 TODO·Notion v0.69·arrivals_api.md/provider_plan.md/public_arrivals_plan.md와 기존 매칭/본인GET 코드를 대조하고, 구현 전에 Notion v0.70 정책을 갱신했다. main205c7e3에서 codex/boarding-stop-sequence 생성, 미병합 조사문서9a98246를0b408d3으로 이어 붙였다. 사용자만 MR 생성/병합한다.

구현: backend/app/arrivals/matching.py는 모든 제공이름의 전체순서·양끝30m를 유지한 추가 공공 정류소 허용, 방문 후보32쌍 초과 전체 미확인 처리, 내부 진단의 ordered 정책 선택을 지원한다. backend/app/arrivals/mapping.py는 공식 승차방문scope를 대조한 뒤 서로 다른 노선 복수 매칭을 차단하고, 같은 노선 상세1회로 각 반복 하차방문의 회차/방향을 확인한 뒤 최종 유일한 후보만 연결한다. 공공 연속순번·유일하고 일관된 회차·공식 routeDestId/실제 끝 정류소 검사 유지. 매핑 버전gbis.station-scope.v2.30m.ordered. 기존 GET 입력/응답·조회 상한·소유권/TTL/60초 캐시·보관 정책 유지. 목록 상세도 차이로 차단되던 검증 후보는 새로 공급자를 조회할 수 있다. 원천 생성시각unknown/예측null/guidancefalse 유지로 출발 계산 완료가 아니다.

검증 파일: backend/tests/test_ordered_arrival_mapping.py(신규9개), test_arrival_mapping_connection.py(추가 정류소/회차 뒤 반복 방문 본인GET 연결 등 기대값 갱신), test_match_diagnostics.py(좌표 미확인 진단 기대값 갱신). 신규9개0.013초·진단7개1.183초·연결17개9.303초 통과. 전체 discover 최종306개115.947초 전부 통과. 추가 중간 정류소 허용/제공이름 누락·역순/30m 초과·좌표결측/공식 방문순번·ID 불일치/공공순번 결손·중복/회차·방향 충돌/회차 뒤 반복 방문 제외 후 유일 매칭/방향 후 남은2후보·복수노선 차단/32후보 경계와33후보 전체차단/상세1회 공유를 확인했다. 본인GET→실제 매퍼→합성 도착 어댑터 연결/unknown 유지도 격리DB로 확인했다. 최초 신규 테스트 단독 실행은 import 경로 누락으로 오류1개였고 기존 테스트 설정 import 순서를 수정한 뒤 통과했다. 실제 경기/카카오 키 호출0회, 이번 실제 연결 성공으로 표시하지 않는다. 승인 누적41/44회·3회 잔여는 요금/공급자쿼터가 아니다.

서버: 기존 프로젝트 uvicorn 프로세스 확인 후 재시작해 수정 적용. 초기 /health 검사는 경로 착오로404였고 실제 코드의 /api/v1/health로 재확인200, 프론트5173도200, 비로그인 first-arrivals는401. 프론트 UI 수정 없음/시각 검증 수행 안 함.

문서: api_contract.md·arrivals_api.md·provider_plan.md·public_arrivals_plan.md·todo.md·feature_breakdown.md 갱신. Notion v0.70의 계약/변경이력에 정책·306개 검증·실제키0회/미확인 상태를 기록하고 저장을 재조회, 로컬 API 미러1560줄 전체 일치 확인. 명세:https://app.notion.com/p/3ebace1670c6806c8199cde33ebfbdfa. 공개 필드 호환성은 유지하되 상세도가 다른 검증 경로의 매핑/조회 가능 범위는 변경됐다.

배운 개념: 공급자의 추가 중간 정류소와 제공이름의 누락/역순은 서로 다른 문제다. 반복 방문 후보가 둘이어도 방향 검증 전에는 유일성을 단정할 수 없다. 하나가 회차를 넘는 경우 제외한 뒤 유일 후보를 확인하고, 검증 후 둘이 남으면 임의 선택하지 않는다. 합성 회귀 성공은 실제 공급자와 최신성 증명이 아니다.

남은 문제/다음: F07-01b/F07-01은 미체크 유지. 변경 후 공개 경로 실제 키 연결 검증과 신뢰할 원천 생성시각/지원 범위가 남았다. 고정 공개 판교역→성남시청/기존 공식 HTTPS/키 비노출 조건의 통합도구 backend/check_arrival_connection.py가 준비돼 있으나 통합1회 최대8호출에는 승인 잔여3회가 부족하다. 추가5회로 승인 누적49회가 되면 --max-requests 8로1회 검증 가능하며 사용자 입력 없이 호출 상한을 늘리지 않았다.


## F07-01b 실제 본인조회 연결 확인·원천 최신성 제약 — 2026-10-13

Notion v0.71. 사용자 01b 완료 요청에 따라 앞서 제시한 같은 공개 판교역→성남시청 경로/저장 키/공식 카카오·경기 HTTPS/격리DB 검증을 --max-requests 8로 실행했다. 실제8회·종료0·HTTP200/connection_verified, MAPPING_CONFIRMED·station_count=1/route_count=1/matched_count=1. 재조회 외부 무호출·동일 근거·저장 검색 무변경이 모두true다. 운영 매핑과 본인GET→공공 도착 조회 연결은 실제로 확인했다.

응답은 insufficient_data/source_status=unknown·도착후보0·생성/예측시각 없음·guidancefalse다. 실제 최신 도착 후보 확보나 출발 계산 성공을 뜻하지 않는다. 경기 공식 항목 명세(https://www.gbis.go.kr/gbis2014/publicService.action?cmd=mBusArrival)를 다시 읽어 queryTime=정보요청시간이고 행별 생성시각 계약이 없음을 확인했다. 수신시각을 생성시각으로 바꾸지 않는다. 오래된 예측을 지금의 대기시간으로 해석하면 이미 지나간 버스에 맞춰 출발할 수 있기 때문이다.

완료 요청으로 추가5회의 앞서 제시한 범위를 실행해 승인 누적49회/실제49회·잔여0이다. 이는 공급자 쿼터나 요금이 아닌 사용자 승인 호출 상한이다. 키/URL/원문/차량번호·사용자 DB 좌표 출력·저장 없음. 구현/공개API/계산/보관 정책 변경 없음·이번 신규 테스트/전체 회귀 재실행 없음(직전306개 통과 유지). 매핑·조회 연결로 F07-01b 범위를 명확히 하고 원천 최신성을 별도 TODO로 분리하는 안은 제안이며, 사용자는 최신성의 중요성을 질문했으나 분리 승인하지 않았다. 기존 F07-01b/F07-01 완료조건을 유지해 미체크로 둔다.

실행: backend/.venv/Scripts/python.exe backend/check_arrival_connection.py --max-requests 8. 이번 수정은 검증 결과/구현 상태 기록으로 기존 codex/boarding-stop-sequence 기능 브랜치에 이어 기록했다. 최신 Notion v0.70·TODO/공공계획·provider/service/검증CLI를 확인하고 결과를 v0.71과 로컬 미러/arrivals_api.md/provider_plan.md/public_arrivals_plan.md/todo.md/feature_breakdown.md에 동기화했다. 계약 변경 없음/전체 완료조건 해제 없음. 결과 저장 재조회와 로컬 미러 전체 일치 확인 후 커밋·푸시한다. MR/병합은 사용자만 수행한다.

배운 개념: 최신성은 서버의 수신 성공과 별개의 성질이다. 공식 요청시각 필드를 데이터 생성시각으로 대체하면 원천 지연을 숨긴다. live connection_verified는 매핑/조회·캐시·보관 검증의 성공이며 최신 예측 확보/출발 안내 완료의 증명이 아니다. 생성시각 또는 믿을 수 있는 공급자 갱신 지연 근거가 필요하다.


## 2026-10-13 — F07-01b 수신 기준 추정 정책·선택 이유

사용자 결정/진행 이유: 생성시각 확보·공급자 지연 상한·수신 기준 추정 세 방법을 비교한 후 사용자가 추천한 수신 기준 추정 진행과 이유 기록을 승인했다. 경기 API는 queryTime=정보요청시간이며 생성시각을 제공하지 않는다. 생성시각 필수 조건을 그대로 두면 실제 매핑/조회가 성공해도 안내 개발이 막히므로, 원천 지연을 숨기지 않는 명시적 추정으로 기능을 진행하기로 했다.60초 재조회·120초 만료는 우리 앱의 오래된 캐시 사용을 제한하며 원천 지연이나 정확도를 보장하지 않는다. 개인 여유5분도 원천 지연의 증명이 아니다. source_status=unknown/generated_at=null 유지, 추정 상태와 생성시각 검증 상태를 구분하며 향후 공식 시간/지연 근거를 확보하면 강화한다.

착수/명세: 최신 TODO·Notion v0.71·provider/service/dto/cache/관련 테스트, arrivals_api/provider/public_arrivals/planning/personalization/policy_decisions/design_guide/screen_plan과 기존 JSX/CSS를 대조했다. 새 codex/arrival-receipt-estimate를 최신 origin/main205c7e3에서 생성하고 이전 미병합 매핑수정/실검증 기록을97b1663·2a00c78·3f254fb로 cherry-pick했다. 구현 전 Notion v0.72 계약 변경 후 로컬 API 미러에 동기화했다.

구현: backend/app/arrivals/dto.py·service.py에서 arrival.evidence.v2/estimated/timing_basis/remaining_seconds를 추가했다. 정상 RUN/양수 예측초는 수신시각+예측초로 추정ETA·원천unknown 유지, 검증 생성시각은 source_generation/fresh로 유지한다. 잘못된/naive/미래 생성시각과 수신 역전은 추정 우회 금지. 캐시 GET도 원래 수신/ETA/기한을 유지하면서 남은초 올림·지난후보 제외·120초 만료를 재평가한다. 유효 estimated의 valid_for_guidance=true는 추정 사용 허용이며 최신성 인증이 아니다. 정상 무결과·운행/시간 부족·매핑/지원 부족 상태는 기존대로 안내 제외. 재조회 실패는 원래 캐시의 received_at/attempted_at/expires_at을 바꾸지 않는다.

화면: frontend/src/lib/arrivals.js·components/FirstArrivals.jsx·JourneyCandidates/JourneyComparison.jsx에 본인 v2 GET 검증과 후보 상세 카드를 연결했다. 기존 info-box/walking-guidance/candidate-note·Clock3 아이콘 재사용, 신규CSS/테마/외부 라이브러리 없음. 진입/60초/탭 복귀 조회·숨김 중지·이탈 취소/중복 방지·서버시간+단조 경과로 계산, 수신 기준 예상/조회경과/원천지연 미확인/실패/만료·빈후보/미지원/매핑미확인 표시. 인증/검색/장소 변경 시 기존 숫자 즉시제거. 실제 예상 출발 숫자는 개인 접근근거 연결 F07-02 후속이다. 생성시각/공식 지연 상한·지원 확장은 F07-01c로 분리하며 사용자 변경 완료조건에 따라 F07-01b 완료/F07-01 전체 미완료로 맞췄다.

검증/수정: backend/tests/test_receipt_arrivals.py 신규8개는 수신ETA/unknown/출처 구분·120초 경계/검색기한·초올림/원래ID·캐시 GET의지난후보 제거/시계/naive·미래 우회 금지/갱신실패의원래캐시기한 유지 확인. 기존 first-arrivals17개4.920초/연결17개8.717초·검증CLI6개1.497초 통과. frontend FirstArrivals10개2.54초와 arrivals.js 계약5개 포함 최종 전체182개9.38초·빌드407ms 통과. 최종 전체 백엔드314개106.538초 통과. 유료AI/외부키 조회0회(직전 실제8회 매핑/도착연결 성공·후보0과 구분), 이번 생성시각/실제 양수 추정 후보/공급자 지연을 확인했다고 기록하지 않는다. 기존 승인49/49회·잔여0은 요금/공급자 쿼터가 아니다.

초기 실패와 배운점: 프론트 npm을루트에서 실행해 package.json 없음1회 오류 후 frontend 디렉터리로 수정했다. UI합성 실행에서 /api/v1 누락으로 요청 검증 실패를 발견해 수정하고 실제 API클라이언트 경로/응답 테스트5개를 추가했다. 격리DB정리 개수검사와 다른DB테스트를병렬실행해 임시스키마개수간섭으로 CLI1개 실패, 단독 재검증6개 통과. 첫 전체314개118.009초는 quota테스트 분경계429기대 실패1개·도보fixture의verified_at 미래판정 오류1개였다. 호스트-DB차이1.007초를 실제측정해 verified_at=호스트시각-1초 fixture가 경계에 걸림을 확인했다. 테스트에서 rate bucket의DB시간을 고정하고 공통 도보fixture 생성도 DB clock_timestamp를 사용하도록 수정했다(test_arrival_mapping_connection.py/test_walking_history.py). 운영 시간/검증/버킷 정책은 완화하지 않았다. 그 후 최종 전체314개 통과. 검증CLI는 카운트다운변화와 원래근거를 구분해 재조회 동일근거를 비교하도록 수정했다.

시각 검증: 실제 브라우저에서 합성 v2 응답·기존CSS·새실제컴포넌트로1280×800/390×844 확인. 수신 기준 예상/조회경과·줄바꿈·가로넘침 없음,120초 지난숫자 제거 확인. 리사이즈직후 첫캡처는이전프레임이라 실제viewport/body폭을 확인한뒤 다시캡처했다. 임시receipt-preview.html/jsx와검사탭 정리·viewport원복. 전체 실로그인/실경로 검색 시각검증은 이번 수행하지 않았으며 공통CSS도 변경하지 않았다.

문서: api_contract.md/arrivals_api.md/provider_plan.md/public_arrivals_plan.md/planning.md/personalization.md/policy_decisions.md/logging.md/design_guide.md/screen_plan.md/todo.md/feature_breakdown.md에 정책·선택 이유/한계·v2호환성·구현상태를 동기화했다. Notion v0.72 계약/예시/공통상태/변경이력/검증결과 저장을 재조회해 확인한다. 명세:https://app.notion.com/p/3ebace1670c6806c8199cde33ebfbdfa. v1클라이언트는v2/estimated/새필드와valid_for_guidance의추정허용 의미 대응필요. 새DB/DDL/AI 호출 없음. 사용자만 MR 생성/병합하며 에이전트는하지 않는다.

남은 문제/다음: 원천시간/갱신지연·정확도/지원범위는 F07-01c 후속이다. F07-02에서 유효한개인접근W와초기여유300초로t_vehicle-W-300을 계산하며근거없는숫자를만들지 않는다. 이번정책으로 출발계산에쓸수있는 추정근거는 준비됐으나 출발시각계산 자체는완료하지 않았다. F07-01 전체 미체크 유지.

최종 저장/서버 확인: Notion v0.72를 재조회해 계약/추정·미매핑 예시/선택 이유·검증 결과 저장과 로컬 API 미러1568줄 전체 일치 확인. 기존 프로젝트 uvicorn 프로세스 확인 후 재시작해 새 정책 적용, /api/v1/health200·프론트5173/200·비인증first-arrivals401 확인. 실제 키 추가 전송 없음. Notion의 일지 파일명이 자동외부링크로 변환된 부분은 코드형식으로 고쳐 재확인했다.


## 2026-10-13 — 수신 기준 추정 브랜치 main 충돌 해결

사용자 명시 요청: main 병합 충돌을 해결하고 에이전트가 main 병합/최신화를 수행한다. 이번 요청이 기존 '사용자가 MR/병합' 규칙에 우선하며 새 MR 생성은 요청하지 않아 수행하지 않는다.

최신 origin/main81aadd9에는 정류소 순서 수정/실조회 기록이0b408d3·4d16b56·f907b2e로 이미 병합됐다. 수신 추정 브랜치에는 같은 변경이97b1663·2a00c78·3f254fb cherry-pick으로 존재해 같은 문서 위치의 이전 상태(v0.71)와 최신 사용자 승인 상태(v0.72)가 충돌했다. api_contract.md/arrivals_api.md/development_log.md/feature_breakdown.md/provider_plan.md/public_arrivals_plan.md/todo.md 7개를 최신 사용자 승인 정책으로 해결했다. 이전 실검증 기록/변경이력은 기능 브랜치에 이미 보존돼 있음을 대조했다. 소스 충돌 없음, 해결 직후 staged diff와7558e40의차이0으로 기존 구현이 그대로 보존됨을 확인했다.

최신 Notion v0.72를 재조회해 수신 기준 추정 정책/완료조건을 확인했다. 이번 충돌 해결은 계약/계산/응답/캐시 변경이 없어 Notion을 불필요하게 수정하지 않는다. 수신 추정 핵심8개1.862초 재검증 통과. 직전 전체 백엔드314개106.538초 통과는 기존 구현의검증이며 이번 전체 재실행으로 표시하지 않는다. 프론트 전체/빌드 재검증 결과는 아래 최종 기록을 따른다. 실제 키/AI 호출·UI 변경 없음. 다음 F07-02 예상 출발 계산과 F07-01c 원천 최신성 강화는 그대로 미완료다.

배운 개념: 같은 변경을 다른 커밋ID로 cherry-pick한 브랜치와 원본 브랜치를 각각 병합하면 코드 의미가 같아도 문서의 후속 수정 위치에서 충돌할 수 있다. 최신 main의원본 기록을 지우지 않고 사용자 승인 최신 정책을 유지하며 최종 소스 차이를 확인해야 한다. 명세:https://app.notion.com/p/3ebace1670c6806c8199cde33ebfbdfa.

최종 프론트 재검증:182개10.27초 전부통과·빌드441ms 통과. 충돌마커/미해결항목 없음·git diff --check 통과. 충돌해결을 기능브랜치에 커밋/푸시한뒤 사용자명시요청으로 main 병합·원격푸시·로컬main 최신화하고 커밋포함여부/원격일치를 확인한다.


## 2026-10-13 — F07-02 첫 버스 예상 출발 계산

목표/사용자 결정: F07-02 착수 전에 최신 TODO·Notion v0.72의5.7/5.9·개인화 수식·도보/프로필/루틴/도착 서비스를 대조했다. 실제 검색 후보와 검증 개인 도보 산정값의 승차 지점 연결이 아직 없음을 확인하고 사용자에게 접근 시간 기준을 질문했다. 사용자는 '공급자 접근 도보 시간에 개인 계수를 적용한 추정 허용'을 선택했다. 이에 공급자 접근초×본인 계수의 추정으로 후보 출발 계산을 진행하되 실제 보행·물리 범위/진행방향·AI 산정 인증으로 표시하지 않는다. 첫 차량만 계산하며 전체 환승/목표도착 보장도 하지 않는다. 새 codex/departure-time를 최신main2a31fc4에서 생성했다.

명세 변경: 구현 전에 Notion v0.73의5.7.1에 본인 first-departure GET·first.departure.v1·접근 추정/프로필 계수·호출 전후 검사·기한·실패/후속 범위를 추가했다. 기존 routine_id 필수 POST /guidance-queries 초안은 유지했다. /auth/me.profile의walking_duration_factor 추가와0012 컬럼 변경·API목록/상태/예시/변경이력/최종 검증 기록을 함께 동기화했다. 기존 도착v2 API 목록의이전v1표기도 수정했다. 명세:https://app.notion.com/p/3ebace1670c6806c8199cde33ebfbdfa.

구현 파일: backend/app/guidance/{dto,service,router}.py·app/main.py, migrations/versions/0012_departure_profile.py. 첫BUS 이전의 양수 access 도보만 합산하고 환승/마지막 도보·차량 대기 제외. W=Decimal 기준ceil(공급자 접근초×walking_duration_factor), 계수기본1.0/0.5~2.0. B=본인first_boarding_buffer_seconds·기본300초/0~1800. 권장시각=t_vehicle-W-B, now는지금선택·recommended시각이미지나면지금으로여유재평가. 음수여유는0으로바꾸지않고not_enough_time, 설정여유미달은below_buffer/경고. 권장/선택시각 구분과 원래s보존. 부족/만료/미지원은출발숫자 없음. 도착v2의수신추정/생성검증을구분하고 캐시·도착/검색기한/계산120초를공유한다.

서비스 경계: 신규GET는 쿠키본인·no-store·CSRF불필요. 클라이언트시간/계수/접근초/정류소ID를사용하지않으며소유권/장소버전/검색후보fingerprint/기한과프로필버전·계수·여유를공급자호출전후재검사해변경409/타인·없음·만료404/인증401/잘못된basis422. 새도보산정/루틴저장·AI호출·TTL연장없음. 프로필계수변경시새GET는원래공급자기준초로재계산·60초도착재사용(이중계수곱/AI·지도호출없음). 계수설정변경API/학습은후속이며내부변경시profile.version 증가.

프론트: src/lib/departure.js와기존arrivals.js/FirstArrivals/JourneyCandidates 확장. 도착·출발은first-departure한GET으로조회해별도중복요청없음. 기존 info-box/walking-guidance/Clock3 재사용·CSS/테마/폰트변경없음. KST예상출발시각·다른서울날짜는날짜표시·접근약N분·설정여유는초정확히표시·공급자개인계수추정/수신추정/조회경과.60초/탭복귀재계산·숨김/이탈취소·기한초과/선택차량예측경과/현재접근불가/인증·경로변경오류이면출발숫자제거. 권장시각이지났거나여유미달이면5분확보를주장하지않는다.

검증: backend/tests/test_departure.py 신규15개는13분차량-5분접근-5분여유=3분출발, now여유8분/권장시각보존, 지난권장시각지금재평가/여유미달·음수, 접근누락/0초·기한/차량경과/시계오류·큰수overflow 차단, 접근초올림/구간제외, 본인GET/캐시/DB검색무변경/계수재계산/호출중프로필변경409·권한/잘못된basis무호출·GET nowquery/CSRF불필요, 계수DB기본/범위NaN·Infinity거절 확인. 최초15개4.903초 통과 후HTTP nowquery/잘못된basis검증추가까지15개5.530초 통과. 최종전체백엔드329개123.044초통과. frontend/tests/{departure.test.js,components/FirstDeparture.test.jsx} 신규14개 포함 최종전체196개11.25초·빌드427ms 통과. 한GET·출발/접근추정라벨·기한/실패/경과/설정미달/날짜/여유초정확표시·충돌숫자제거·응답수식/선택ID/기한연장·계수검증확인. 이번 실제교통키/AI호출0회, 실제경로의양수출발숫자·물리보행/예측정확도는미검증.

초기실패/수정: 첫15개검증은범위제약CheckViolation을database컨텍스트가안전한AuthError로바꾸는테스트기대오류1개와project가합법적estimated를재평가하는데bool만false로덮은합성입력오류1개였다. DB제약은격리rawconnection에서검사하고불충분상태합성으로바꿔운영검사를완화하지않았다. 첫전체329개124.495초는새Envelope이름중복으로기존OpenAPI$ref변경1개·head기대0011→0012미갱신1개·기존place-map-pin쿼터테스트분경계503/429기대1개 실패했다. 신규DepartureEnvelope로기존도착Envelope유지, migration기대및기존프로필컬럼backfill/왕복검증 추가, 해당quota테스트DB시간고정으로수정 후전체통과. 운영제한/권한/시간검사를우회하지않았다. 기존backend/tests/test_migrations.py/test_place_map_pin.py가관련보존/회귀검증수정파일이다.

시각확인: 실제브라우저에서합성응답·실컴포넌트·기존CSS로1280×800/390×844의예상출발/접근·여유·추정표시·줄바꿈/가로넘침없음확인. 전체실로그인/실경로/루틴선택시각검증은이번수행하지않았다. 임시departure-preview.html/jsx·검사탭삭제, viewport원복. 화면이없는미지원/부족/만료·시각경과는모의컴포넌트검증과구분한다.

로컬DB/서버: 개인계수0011→0012컬럼추가적용. 회원20/장소35/루틴12전후보존·계수범위정상확인. 최초보존확인스크립트는rawconnection tuple을dict로접근해TypeError였으며쓰기이전에중단, tuple접근으로고쳐성공했다. 기존프로젝트uvicorn확인후재시작하여새API적용, /api/v1/health200·프론트5173/200·비인증first-departure401 확인. 새컬럼은기존회원기본1.0이고프로필version/기존데이터를변경하지않는다.

문서/완료: departure_api.md·planning.md·personalization.md·policy_decisions.md·provider_plan.md·arrivals_api.md·logging.md·README.md/backend/README.md·design_guide.md/screen_plan.md·todo.md/feature_breakdown.md와Notion v0.73을동기화했다. 선택이유는검증된개인접근연결부재를사용자승인공급자추정으로해소해실제후보계산을진행하기위함이다. 원천unknown/물리보행미확인한계는숨기지않는다. F07-02 후보첫버스계산완료, 루틴자동재검색·검증도보연결을F07-02a로명시, F07-03이후환승/목표도착/다음차량·이동중과F07-01c강화는미완료유지. 다음작업F07-03. 신규브랜치커밋·푸시 후MR/병합은사용자만수행한다(직전main병합명시요청은이새기능병합승인으로확대하지않는다).

배운개념: 개인화접근과차량대기/환승/여유는서로다른시간이다. 원래공급자시간에계수를한번만곱하고여유는별도로빼야한다. 권장시각이지났으면현재기준여유를다시계산해야하며음수여유/설정미달을5분확보로말하면안된다. 한차량의접근가능성과전체여정환승/목표도착가능성도구분한다. 프로필이호출중바뀌면같은차량캐시라도오래된접근시간안내를차단해야한다.


## 2026-10-14 — F07-02 게시 마무리

전날 구현/검증/DB·서버 적용과 Notion v0.73 저장을 마쳤으나 마지막 원격 main 확인은 자동 승인 검토의 사용량 제한으로 검토 자체가 실패해 실행되지 않았다. 안전하지 않은 행동이라는 판정은 아니며 승인 절차를 우회하지 않았다. 오늘 상태 질문에 답하면서 기존 승인 작업의 남은 게시를 재개했다. 최신 main2a31fc4와 브랜치 시작점 일치·작업폴더 충돌 없음 확인, 최신 Notion v0.73 재조회와 로컬 API 미러 전체 일치 확인. 기존 백엔드329개/프론트196개/빌드 및 합성PC·모바일 검증 결과를 유지하며 이번 테스트 재실행으로 표시하지 않는다. 계약/코드 변경 없이 기능 브랜치에 커밋·푸시한다. MR/병합은 사용자 작업이며 이전 수신 추정 브랜치의 main 병합 승인을 새 기능에 확대하지 않는다. 다음은 F07-03, 루틴 자동갱신/F07-02a와 원천 강화/F07-01c도 미완료다.


## 2026-10-14 — F07-03 지원 경기버스 순차 환승 검사·채팅 마감 계획

목표/이유: 사용자 요청은 다음TODO를 더 빠르게 진행하고 다음 수요일2026-10-21까지 채팅 기능을 포함하는 것이다. 최신main146c59a에 F07-02/6bf4cfb가 포함된 것을 확인하고 codex/transfer-connections를 생성했다. TODO·최신Notion v0.73·관련 기획/개인화/공급자/로깅/디자인과 실제 코드 계약을 대조한 뒤 v0.74에 선택적 순차 환승 검사 계약을 먼저 추가했다. 첫 차량 성공만으로 전체 연결을 보장하지 않고 근거부족/미지원은unknown으로 처리해 추측 시간표 없이 실제 공급자 데이터 범위에서 진행한다.

구현 파일: backend/app/guidance/{connections,dto,service,router}.py·arrivals/{cache,mapping}.py·journeys/provider.py, frontend/src/lib/departure.js·components/FirstArrivals.jsx. 기존 first-departure에 include_connections=false 기본·true 순차검사를 추가하고 first.departure.v1에 connection_status/transfers/estimated_final_alighting_at를 추가했다. 예상하차+ceil(제공환승도보×개인계수)+본인환승여유120초로 최소승차를 계산하고 현재 제공 다음차량 중 가능한 가장 이른 예측을 선택한다. 전부 이르면 제공후보 연결불가, 앞근거 부족이면 뒤 숫자/조회 없음. 최종하차는 목적지 도착 보장이 아니다. 첫 valid_for_guidance와 전체 연결상태를 분리했다.

경계: 후속BUS 최대2개의 공개 정류소/차량1개/양끝점만 기존32검색/20후보/300초·본인fingerprint 메모리에 포함한다. 기존30m/이름순서/공식방향·방문유일성/운행·예측초 검증을 후속leg에도 적용한다. leg별60초 캐시·원래수신시각/ETA/기한 유지·잠금·갱신10회/분을 공유하고 전체20초/최대21회 고정공식HTTPS·매핑5초/도착3초 상한으로 추가조회 제한. 본인/장소/검색/후보/프로필 버전·계수·첫/환승여유를 전후 검사한다. 새DB/DDL/AI·원문/좌표/차량ID 추가저장·로그 없음.

실제 검증: backend/tests/test_connections.py 신규14개4.737초 통과. 최소승차 경계/선택예측·2회 순차/첫실패 뒤 중단·누락/0초/지하철·개인계수올림·메모리근거 비영구·만료·본인GET/후속캐시/오류시기존근거보존·중간프로필변경409/재시작/시간예산 무호출을 확인했다. 최종전체 백엔드343개124.115초, 프론트199개10.49초·빌드1907모듈1.05초 통과. frontend/tests/departure.test.js·components/FirstDeparture.test.jsx는 최소승차보다이른응답거절·연결상태/확인불가·만료숫자제거 검증. 최초신규실행의8개NameError는 가져온fixture클래스 제거후 참조 문제여서 함수참조를 보존해 수정했다. 운영검사 완화 없음. 이번 실제교통키/AI0회·기존49/49회/잔여0은 사용자승인 검증호출상한이며 공급자쿼터/요금이 아니다. 실경로 예측정확도/물리보행/지원지역전체는 검증하지 않았다.

시각/서버: 합성응답을 실FirstArrivals/기존CSS로 브라우저1280×800/390×844에서 렌더링해 예상연결 최소승차/다음차량·확인불가에숫자없음·추정주의/줄바꿈을 확인했다. 모바일 body.scrollWidth=innerWidth=390으로 가로넘침없음. 실제로그인/실경로 통합시각검증은 제외. 임시connections-preview.html/jsx와검증탭 삭제·viewport원복. 신규CSS/색상/글꼴/테마없음. 기존프로젝트uvicorn 프로세스를 확인해 숨김재시작, /api/v1/health200·프론트200·비인증first-departure401·OpenAPI include_connections query 존재 확인. 새DDL없어0012 유지.

문서/상태: Notion v0.74의5.7.2 정책/응답예시/구현결과·활성API목록·메모리규칙·상태·변경이력 수정 후 재조회해 저장을 확인했다. api_contract.md 전체미러를 정규화해 대조했다. connections_api.md·departure_api.md·planning.md·personalization.md·provider_plan.md·arrivals_api.md·logging.md·design_guide.md·screen_plan.md·todo.md·feature_breakdown.md를 동기화했다. F07-03은 지원경기BUS 순차검사 범위로완료, 미지원지하철/근거부족unknown과 원천시간/지원확대F07-01c·루틴F07-02a·목표도착 등 후속은 미완료유지. 명세:https://app.notion.com/p/3ebace1670c6806c8199cde33ebfbdfa.

마감계획/선택이유: 사용자마감에 맞춰 기능순번보다 실제 흐름 완성을 우선한다. 다음F07-02a 루틴선택→최신출발연결, 이후약속·참여자F12→채팅저장/전달/재접속F14→통합검증. TODO에14~15일출발/16~17일약속/18~19일채팅/20일통합/21일수정 계획을 기록하며 확정완료/보장으로 표시하지 않는다. 최신main146c59a 게시전재확인·git diff --check 통과. 기능브랜치커밋·푸시후 MR/병합은사용자가수행한다.

배운개념: 환승의 최소승차시각과 현재공급자가제공한차량예측을 비교할 수는 있지만 미래운행을 보장할 수는 없다. 제공후보 연결불가와 근거미확인은다르며 앞승차가확인되지 않으면 뒤연결 숫자를만들지 않아야한다. 여러외부조회에는개별timeout 외 전체시간상한과 원래캐시기한을 함께 적용해야한다.


## 2026-10-14 — F07-02a-1 루틴 선택에서 최신 첫 출발 안내 연결

목표와 담당: 사용자는 핵심 기능인 루틴 선택→최신 출발 안내를 이 에이전트에 맡기고 약속·참여자→채팅은 다른 LLM에 맡긴다고 명시했다. 전체 마감은2026-10-21 유지한다. 최신 TODO·Notion v0.74·루틴 저장/장소 버전·검색/도착/출발 코드와 기획·개인화·로깅·디자인 문서를 대조했다. 최신main146c59a에서 codex/routine-departure를 생성하고 필요한 미병합 환승aea218b를3d425a8로 포함했다. 게시 직전에는 사용자가 환승을main2460bd7로 병합한 것을 확인해 최신main 기준으로 정리한다.

선택 이유: 저장 당시 시간은 지금 출발 안내의 근거가 될 수 없다. 서버가 루틴의 현재 본인 저장장소로 새 경로를 검색하고 저장 노선·정류소 순서와 유일하게 일치하는 후보만 계산한다. 가장 빠른 다른 노선을 임의 선택하거나 루틴을 덮어쓰지 않는다. 별도 검증된 개인 도보의 물리 승차 연결은 현재 없어 앞서 사용자가 승인한 공급자 접근 도보×개인계수 추정을 재사용한다. 최신 출발 연결만 F07-02a-1로 완료하고 검증 개인 도보를 포함한 F07-02a 전체는 미체크로 유지한다. 목표도착/요일 예약출발·이동시작도 이번 완료 범위가 아니다.

명세와 구현: 구현 전에 Notion v0.75의5.7.3에 본인 POST /routines/{routine_id}/departure-searches(expected_version·Origin/CSRF·선택적 요청키)와 GET /routines/{routine_id}/departure-searches/{search_id}/first-departure?expected_version=N 계약을 추가했다. 첫 요청은 기존 비동기검색202·현재 저장장소/위치버전·검색10회/분·동시2/8·300초/작업60초를 사용한다. 요청키 fingerprint는 루틴ID/버전도 포함한다. 두 번째는 routine.departure.v1과 nullable first.departure.v1을 반환한다. 후보없음/노선변경/복수일치는 숫자없음200, 검색진행중은Retry-After2, 공급자실패는 안전한저장코드503. 본인/루틴·plan·장소버전/검색과 바인딩을 전후 검사하며 변경409, 타인/삭제/만료404, 인증401/CSRF403/입력422로 차단한다.

주요 파일: backend/app/guidance/routine.py·router.py, journeys/service.py의 선택적 내부 fingerprint context. 바인딩은 최근32검색 프로세스메모리에 본인/루틴ID·버전/planID·좌표없는 서명/장소버전/기한만 보관한다. 재시작/다른프로세스/퇴출은 새키·새검색 필요, DB에서 과거바인딩 복원없음. 현재 후보의 모든 구간 type/도보role/차량이름/정류소순서를 비교하고 바뀐ID/시간/거리는 무시한다. 이 비교는 노선선택이며 물리정류소/방향 인증은 기존 매핑이 수행한다. 원래 검색·도착 기한 유지, 프로필/첫도착/환승은 기존 검사 그대로다. 새DDL/루틴·plan 수정/AI호출 없음.

화면 파일: frontend/src/components/RoutineDeparture.jsx, lib/routineDeparture.js, App.jsx, FirstArrivals.jsx, lib/departure.js. 홈/내루틴 선택 후 이전 숫자를 제거하고 CSRF→새검색→기존jobpoll→출발GET을 연결한다. 최초 계산 응답을 기존 카드에 전달해 중복GET 없이 표시하며 60초/탭복귀 도착 재검사, 검색300초 만료 때 보이는 화면에서 새검색한다. 숨김/이탈/루틴교체/로그인모달은 취소하고 늦은응답을 무시한다. 복구루틴은 조회하지 않으며 다른출발지에는 집루틴 안내를 적용하지 않는다. 루틴 조회/도착 갱신 실패는 유효기한 전이라도 이전 숫자를 제거하고 명시적 다시확인을 제공한다. 실패 무한재시도 없음. 기존CSS·카드·색상·버튼·Clock3를 재사용하고 새CSS/폰트/테마는 없다. 도움말/푸터의 이전 준비중 표현을 실제 첫승차 추정 범위에 맞췄다.

실제 검증: backend/tests/test_routine_departure.py 신규11개 포함 전체354개137.158초 통과. 실제 격리 PostgreSQL/ASGI와 합성 공급자로 루틴선택→새검색→바뀐후보ID/도보초→본인GET·출발 계산·캐시·루틴원본보존을 확인했다. 노선변경/복수/없음 무도착호출, 인증/CSRF/버전 사전차단, 요청키 재현 무재호출/재시작 새키, 다른루틴 접근 차단, 조회·입장 중 버전변경, 검색 장소순서 변경·실패/만료,32개 제한/퇴출·경로서명 비교도 확인했다. 최초9개 실행은 비로그인 테스트 보조함수의 None 쿠키와 검증스키마를 깨뜨린 합성입력 오류2개였다. 직접 비로그인 ASGI 요청과 정상 정규화된 다른노선으로 수정했고 이어 편집중 괄호 누락을 고쳤다. 최종 운영 검증조건을 완화하지 않았다.

프론트 tests/routineDeparture.test.js·components/RoutineDeparture.test.jsx·FirstDeparture.test.jsx 신규13개 포함 최종212개10.81초·빌드1909모듈447ms 통과. CSRF/입력최소/요청키·poll 후GET·응답 본인/버전/기한·nested 검증·실패worker 무GET, 선택/만료 새검색·수동회복·모호한경로·복구 무조회·숨김복귀·교체취소/늦은응답·무한실패재시도없음·유효기한 전 갱신실패 숫자제거를 검증했다. 처음 복구 테스트는 실제 needs_attention 대신 잘못된 needs_review 합성상태여서 계약상태로 수정했다.

시각 확인: 합성 응답을 실제 RoutineDeparture→API 클라이언트→poll→FirstArrivals와 기존CSS에 연결해 브라우저1280×800/390×844의 예상출발·접근5분/설정여유5분·개인계수/수신추정·다시확인 버튼·후속범위 안내와 줄바꿈을 확인했다. 모바일 body.scrollWidth=innerWidth=390, 가로넘침없음. 실제 로그인·실운행 통합시각검증/실휴대전화는 제외. 임시routine-preview.html/jsx·검증탭 삭제, viewport 원복. 이번 직접 실행한 실제 교통키/AI 호출0회이며 실경로 예측정확도·물리보행은 미검증이다. 이전49/49회/잔여0은 사용자 승인 검증호출 상한이지 공급자쿼터/요금이 아니다.

서버/문서: 프로젝트 uvicorn 프로세스를 확인해 숨김재시작, /api/v1/health200·프론트200·비인증 루틴출발GET401·OpenAPI신규2경로 확인. 새DDL없어0012 유지. Notion v0.75의 활성API목록·정책·상태·완료기록·변경이력을 갱신하고 다시 읽어 저장을 확인, api_contract.md 전체본문 대조일치. routine_departure_api.md·routine_api.md·departure_api.md·planning.md·personalization.md·provider_plan.md·logging.md·design_guide.md·screen_plan.md·todo.md·feature_breakdown.md에 담당분리/구현/검증/후속범위를 동기화했다. 명세:https://app.notion.com/p/3ebace1670c6806c8199cde33ebfbdfa. git diff --check 통과, 기능브랜치 커밋·푸시하며 MR/병합은 사용자 수행.

배운 개념과 남은 일: 루틴은 반복 경로의 저장값이고 현재 교통 근거는 기한이 짧은 별도 조회다. 새 후보ID를 과거ID와 비교하면 같은 노선을 놓치므로 차량과 정류소순서로 선택하되 물리매핑 확인과 구분해야 한다. 유일성 없는 경로를 임의로 선택하면 사용자 의도와 다른 출발 안내가 된다. 검색갱신과 도착갱신의 간격/기한도 분리해야 한다. 남은 핵심은 검증 개인 도보 연결·목표도착/다음차량 등 F07 후속이며 약속·참여자/채팅은 사용자 지정 다른 LLM 담당이다.


## 2026-10-14 — 출발 안내 문구/부족 사유 수정·F07-05

목표와 조사: 사용자가 실제 루틴 화면의 상태를 질문하고 이전 준비중 문구 수정과 후속 진행을 요청했다. 최신 TODO·Notion v0.75·현재 루틴/첫출발/도보/매핑 코드와 개인화·로깅·디자인을 확인했다. 최신main2460bd7에서 codex/departure-guidance-clarity를 생성하고 필요한 루틴연결6c7146e를34afc4b로 포함했다. 읽기 전용 DB 조사에서는 최근 성공검색2개/후보28개 모두 접근도보누락, 첫버스 복수노선 후보12개를 확인했다. 개인 장소·좌표·노선명/ID·키/세션·원문은 출력하지 않고 개수만 확인했다. 이 집계는 사용자가 선택한 특정 후보의 매핑 실패 단계 확정이 아니다. 현재 프로세스의 과거매핑 진단은 저장되지 않아 정확한 실패단계는 기존 캡처로 확정할 수 없다.

결정과 이유: 첫승차 도착 매핑이 성공해도 접근도보가 없으면 출발계산은 불가능하다. 누락초를0/5분·직선거리로 대체하지 않는다. 검증 개인도보 AI 미실행과 사용자승인 공급자접근×개인계수 추정을 구분하고, 접근누락/매핑실패를 별개 원인으로 안내한다. 원인없는 일반 안내를 줄이기 위해 기존 매핑 한조회에서 안전한 고정 실패코드만 응답한다. 실제 공급자 추가호출/미검증매핑 허용범위 확대는 하지 않았다. 후속 F07-05는 유효한 첫출발에 N분뒤/1분이내/지금재확인과 현재기준 정류장여유를 함께 표시한다.

계약과 파일: 구현 전에 Notion v0.76의5.7.4에 기존 arrival.evidence.v2 reasons의 고정허용코드와 카운트/현재여유 정책을 추가했다. backend/app/arrivals/mapping.py·service.py·guidance/connections.py는 프로세스검색근거없음/복수노선/정류소/경유노선/정차순서/노선상세/방향미확인을 구분한다. 기존 PUBLIC_MAPPING_UNCONFIRMED/LEG_MAPPING_UNCONFIRMED·상태/차단·30m/방향/호출상한/캐시/원래기한 유지, 허용목록 밖 진단사유/원문/ID/좌표/개수/match_checks/키는 공개하지 않는다. 새조회/DB/DDL/AI없음.

화면: frontend/src/components/WalkingGuidance.jsx의 '실제 출발 안내 준비중'을 제거하고 공급자추정과 개인도보검증을 구분했다. FirstArrivals.jsx는 ACCESS_TIME_UNCONFIRMED를 구체적으로 안내하고 고정매핑사유만 한국어로표시한다. 유효근거에 selected_departure_at까지 남은시간은 올림분/1분이내, 도래하면 지금재확인. 여유=floor(차량ETA-max(선택출발,현재서버시각)-개인접근초). 미래권장시각에서는그때, 지난시각에서는지금으로 설명하고 초를보존·설정미달경고, 음수/만료/근거부족은숫자없음. 과거5분여유를 현재 확보한것처럼표시하지 않는다. 새CSS/팔레트/글꼴없음.

초기 검증과 수정: 신규 backend/tests/test_arrival_reasons.py 5개3.102초는 안전사유/개인정보비노출·실패캐시재사용/추가호출없음·원문진단거부·메모리근거없음/복수노선 무호출·허용목록을 확인했다. 기존 매핑모의함수2곳에 선택적 diagnostics 인자 수신을 반영했다. 최초 전체359개147.813초에서 기존 check_arrival_connection.py의 추적래퍼가 새diagnostics 인자를받지못해 격리오프라인프로브1개 실패했다. 실제검증도구의래퍼를 **kwargs/호출자진단병합으로수정해 기존도구진단과서비스진단을함께유지한다. 외부네트워크 없는 도구검증을 실제키실행으로 표시하지 않는다.

frontend/tests/components/FirstDeparture.test.jsx·WalkingGuidance.test.jsx 신규6개: 출발카운트/첫정류장여유·지난선택시각 현재여유감소·1분이내·접근누락과미지원노선사유동시표시·원문/상속속성거부·이전준비중문구제거를 확인했다. 초기카운트검증1개는60초재조회에서도모의server_time을과거에고정해서실패했으며 응답서버시각을61초시점으로 갱신했다. 기존여유미달모의입력도 실제차량ETA가3분여유가되도록수정했다. 현재여유 계산을 약화하지 않았다. 전체프론트218개13.85초 통과, 진단배열방어 추가 후 관련33개2.27초 재통과·최종빌드1909모듈438ms 통과.

시각 확인: 합성응답과 실제 WalkingGuidance/FirstArrivals·기존CSS로 브라우저1280×1100/390×1600에서 유효출발카운트/정류장예상여유와 부족접근/경기노선미확인 두상태를 확인했다. 모바일 body.scrollWidth=innerWidth=390, 줄바꿈/가로넘침없음. 실제사용자로그인·해당실경로 예측정확도/실휴대전화검증은 제외. 임시clarity-preview.html/jsx·검증탭삭제/viewport원복. 이번 직접 실제교통키/AI호출0회. 최근검색 집계로 미지원지역/특정 매핑오류를 확정하지 않는다.

협업 상태: 작업 중 같은 브랜치에 fd1d8d1 WIP 커밋이 외부에서 추가되어 현재 변경 일부가 포함된 것을 확인했다. 추가커밋의파일은 이 작업의중간수정과일치하며 기존커밋을삭제/수정하지않고 보존한다. 최종테스트/문서/나머지변경을 별도커밋으로완료하며 MR/병합은사용자수행이다.

후속: 접근누락복구흐름을 F07-02a-2에 미완료로 추가한다. 확인된승차지점의 공급자도보근거를 확보하는 API/물리근거/추가조회정책은 설계미정이며 임의값대체없음. 목표도착F07-04·다음차량F07-06과 검증개인도보연결도미완료다. 약속·참여자/채팅은사용자지정다른LLM담당. 배운개념: 경로전체예상시간은 접근도보초가 아니고, 출발가능성과매핑확인은 서로다른근거다. 선택시각이 지난뒤에는 현재시각으로여유를재계산해야한다. 공개진단은고정코드만허용해야원문·식별자를노출하지않는다. 최종회귀/서버/명세저장결과는아래기록을따른다.


최종 결과: 수정 후 전체백엔드359개132.743초 통과·기존오프라인진단프로브 포함. 프론트전체218개13.85초·배열방어후관련33개2.27초·최종빌드1909모듈438ms 통과. 기존프로젝트uvicorn 확인후숨김재시작, health200·프론트200·비인증first-departure401 확인. Notion v0.76 활성상태·5.7.4/완료기록/변경이력·F07-02a-2 미정후속을갱신하고재조회해저장확인·api_contract.md전체미러대조일치. 관련로컬문서/디자인/로그/개인화와TODO·feature_breakdown 동기화, F07-05 완료·접근누락복구/목표도착/다음차량은미완료유지. 게시전최신main2460bd7재확인·git diff --check 통과. 기능브랜치커밋·푸시, MR/병합은사용자수행. 명세:https://app.notion.com/p/3ebace1670c6806c8199cde33ebfbdfa.


## 2026-10-14 — F07-02a-2 루틴 누락 접근 도보 보완

목표와 명세: 사용자가 다음 우선 작업인 누락 접근도보 확보·연결을 진행하라고 요청했다. TODO·최신Notion v0.76·관련루틴/도착/출발/개인화/공급자/로깅·디자인 문서와실제코드를확인했다. 카카오 공식 REST 도보계약(https://developers.kakao.com/docs/ko/kakaomap/rest-api)의 /v2/routing/walk·REST키·WGS84·초/미터·status/route/legs/steps/path를다시읽었다. 최신main2460bd7에서codex/missing-access-walk를생성하고 미병합선행루틴/문구커밋34afc4b·fd1d8d1·433f581을7ba99d8/f0b560f/5bd56d4로보존해포함했다. 구현전Notion v0.77의5.7.5에 누락복구범위·개인화/저장/조회/기한/실패/호환정책을확정했다.

선택 이유: 경로 전체 예상시간의 남는값은 접근도보가 아니다. 공급자가 접근구간을 생략한 경우 본인루틴의 현재 저장출발지에서 검증된 실제승차정류소까지 도보경로를 별도로 확보한다. 기존양수접근은유지하고 명시0초/지하철·복수노선/매핑미확인이나일반후보GET에는 자동대체하지않는다. 지점이확인되지않으면 임의근사좌표/직선거리/5분·0초로만들지않는다. 공급자도보에 개인계수를 적용한 추정이며 검증개인AI도보/물리보행안전 인증으로승격하지않는다.

주요 파일: backend/app/arrivals/{cache,mapping,service}.py·guidance/{access,walk_provider,dto,service,routine}.py. 기존경기매핑의30m/이름순서/공식stationId·staOrder/회차·방향유일성을통과한 공식승차행좌표를별도 비공개endpoint sink로 전달한다. 공개Mapping/diagnostics/DB/로그에는추가하지않고 Entry의매핑identity/검색fingerprint·기한에묶는다. 루틴서버바인딩의본인출발장소/버전만내부first_departure에전달하며 공개좌표/장소ID입력추가없음. 후보/루틴/plan의원래DB스냅샷과missing_segments는변경하지않는다.

도보조회/검증: 고정dapi.kakao.com HTTPS/리다이렉트금지·서버REST키/최단경로·최대3초/1MiB, 중복JSON/NaN·미지정상태거부. 양수totalTime<=86400초/양수totalDistance<=100000m·20legs/500steps/20000points·정수비음수시간/거리·단계와구간/총합일치·유한좌표·단계연결/출발·승차양끝30m이내를검사한다. 결과없음/같은점/0초·손상/위치불일치/오류는접근시간없음으로처리한다. 조회중본인/장소/검색/프로필/루틴·매핑identity변경을전후검사해오래된출발을차단한다. 응답원문/사용자좌표/보행geometry는새저장/AI전달하지않는다.

응답/캐시: first.departure.v1에provider_approach_source(transit_segment/boarding_walk/null)·approach_fetched_at/approach_valid_until(nullable)을추가했다. 기존basis=provider_personalized와W=ceil(원래공급자초×개인계수)/설정여유는그대로다. 성공양수초/수신·기한/출발장소버전/매핑identity만기존32검색/20후보/검색300초메모리로보관하고 원문/사용자좌표는추가보관하지않는다. 새계수는원래초에한번만곱하며재조회/캐시기한연장없음. 실패도60초재시도차단·entry잠금/사용자갱신10회·분공유. 전체20초/클라이언트25초유지·외부최대22회(첫+후속2각최대7·도보1), 남은시간3초미만은추가조회없이부족. 최종기한은원래도착/검색/매핑/도보중최소다. 새HTTP경로/DDL/AI없음.

프론트: lib/departure.js는별도도보의허용출처/수신·기한을검증해미래수신·누락·기한연장을거부한다. components/FirstArrivals.jsx는기존카드/Clock3/CSS를재사용해별도조회한공급자도보의개인화추정과조회실패/시간부족/매핑미확인을구분한다. 접근도보실패시첫차량도착정보가있더라도출발카운트/시각을만들지않는다. 새CSS/폰트/색상/테마없음.

실제 검증: backend/tests/test_access_walk.py 신규16개 포함최종전체375개155.207초통과. 최초신규12개12.067초통과후공식행좌표가근사path좌표와다름/diagnostics비노출·장소버전변경·중복잠금429·0초차단4개추가까지최종전체에포함했다. 순수어댑터는초/합계/geometry·끝점방향/불연결·결과없음/0초·고정HTTPS/3초/1MiB·중복JSON/크기검사. 실제격리PostgreSQL/ASGI와합성공급자로 루틴접근누락→공식방향매핑→도보초→출발계산/원래DB후보보존, 계수변경원래초재계산/무재호출·원래수신/기한유지, 미매핑/비공개endpoint없음/시간부족무조회, 실패60초재시도차단·숫자없음, 조회중장소/프로필변경409, 일반후보GET무대체/잠금/0초차단을확인했다. 기존진단프로브는**kwargs로private sink를전달하지만진단응답에좌표가들어가지않음을유지한다. test_arrival_reasons.py 모의mapper에도새비공개인자를수신하도록반영했다.

전체 회귀 실패/수정: 최초375개159.440초는 기존test_places.py의장소쿼터테스트가10회요청도중분경계를넘어11번째가새버킷200이돼기대429와달랐다. 해당테스트의DB시간을고정해항상한분버킷에서검사하도록수정했다. 운영요청제한/버킷정책/계산코드변경없음. 수정후전체375개155.207초통과. 프론트신규4개 포함전체222개23.72초·빌드1909모듈750ms통과: 별도도보메타데이터/미래·만료·누락·알수없는출처거부, 별도조회출처와도보timeout숫자차단을검증했다.

시각/서버: 합성응답과실제FirstArrivals·엄격API클라이언트·기존CSS로브라우저1280×1100/390×1400에서성공출처/예상출발·여유와도보조회실패상태를확인했다. 모바일body.scrollWidth=innerWidth=390·줄바꿈/가로넘침없음. 실제사용자로그인·해당실경로 양수출발·보행정확도/실휴대전화는이번검증제외. 임시access-preview.html/jsx·검증탭삭제/viewport원복. 기존프로젝트uvicorn확인후숨김재시작, health/프론트200·비인증루틴출발GET401·OpenAPI출처필드존재확인. 이번직접실교통키/AI호출0회이며실사용요청에만도보1회를연결한다. 새DDL없어0012유지.

문서/완료: Notion v0.77의활성API목록/상태·5.7.5·기존21회조건의루틴22회예외/이전미정설계해소·구현검증·변경이력을갱신하고재조회해저장확인, api_contract.md전체미러대조일치. access_walk_api.md·departure_api.md·routine_departure_api.md·planning.md·personalization.md·provider_plan.md·arrivals_api.md·logging.md·design_guide.md·screen_plan.md·todo.md·feature_breakdown.md를동기화했다. F07-02a-2는지원경기BUS루틴누락복구범위로완료. 검증개인도보F07-02a전체·미지원매핑/지역지원·원천시간·목표도착/다음차량은미완료유지한다. 다음F07-04 목표도착후보평가, 약속·참여자/채팅은사용자지정다른LLM담당이다. 명세:https://app.notion.com/p/3ebace1670c6806c8199cde33ebfbdfa. 게시전main2460bd7재확인·git diff --check 통과, 기능브랜치커밋/푸시·MR/병합은사용자수행.

배운 개념: 누락된접근도보는경로전체예상시간과분리해확보해야한다. 매핑된공식승차점과길찾기제공근사점을구분하고도보양끝과진행방향을확인해야한다. 캐시에는개인화후초가아닌원래공급자초를보관해야계수변경시두번곱하지않는다. 매핑/도착/도보조회가각각빠르더라도전체시간제한과원래근거기한을공유해야안내가늦거나오래된정보를새정보처럼쓰지않는다.


## 2026-10-14 — F07-04 선택 루틴의 오늘 목표 도착 평가

목표/기준: 사용자가 다음 작업 진행을 요청해 TODO의F07-04와 최신Notion v0.77·목표/요일/시간단위/개인화·루틴/도착/출발/환승과디자인/로깅문서를확인했다. 최신main2460bd7에서codex/target-arrival-evaluation을생성하고 미병합선행루틴/문구/접근도보7ba99d8·f0b560f·5bd56d4·1e60b8c를b54be48/31bc7cf/f2801ab/d277426으로보존해포함했다. 구현전Notion v0.78의5.7.6에선택루틴의현재후보 목표평가범위/날짜·순차타임라인/기한/호환·실패계약을추가했다. 다른담당이추가한F12명세상태/기록을보존했고 해당기능을이작업에서구현/검증했다고주장하지않는다.

날짜 정책과 이유: 수동선택은이번에출발할루틴을고른동작이므로오늘Asia/Seoul의설정목표와비교한다. 반복요일은일정참고이고수동선택을차단하지않는다. 이미지난목표는target_passed로남기며다음날/다음주로이월해가능하다고표시하지않는다. 이는이번구현선택이며사용자가별도날짜정책을확정한사실로기록하지않는다. 미래예약시간표/arrive_by검색·다른노선자동선택은후속이며기존UNSUPPORTED_TIMING계약도유지한다. 선택후보의추정충족평가와목표기반최적경로/최적출발검색은구분한다.

구현 파일: backend/app/guidance/{target,dto,routine}.py. 기존 first.departure.v1에 nullable target_evaluation(target.arrival.v1)을추가했다. scope=selected_routine_candidate·status는not_configured/estimated_meets/estimated_late/target_passed/unknown/stale. evaluated_at·오늘목표·예상목적지도착·signed margin_seconds·egress_seconds·timing_basis/reasons를반환하고미확인시숫자null이다. 일반후보GET는null, 본인루틴GET의유일선택후보에서만계산한다. 기존첫승차valid_for_guidance/connection_status는별도범위로유지한다.

계산과 경계: 유효첫승차·현재접근가능·모든지원BUS의양수차량시간·전체환승estimated_feasible·연결ID/개인화도보/설정환승여유/하차·최소승차·선택다음승차타임라인·최종하차일치가필요하다. 마지막차량이후양수egress WALKING합에개인계수를한번곱해ceil, 목적지ETA=마지막하차+개인화마지막도보다. 마지막도보없음/0초·환승미확인·불일치/만료는목적지시각을만들지않는다. 하차를목적지도착으로대체하지않는다. provider total inconsistent는unknown, 미배분시간은임의도보/대기에더하지않고선택된차량/환승ETA와제공구간을쓰는추정으로고정사유를남긴다.

목표 비교: ETA<=오늘목표는estimated_meets, 늦으면estimated_late·floor(목표-ETA)초를음수그대로보존한다. 목표미설정/지난목표/근거부족·만료구분, 첫정류장버퍼와목표여유는다르며자동여유축소없음. 계산전후프로필버전/계수/버퍼와루틴·장소/검색/후보를재검사해변경409로차단한다. 기존출발기한을공유하며새기한연장/외부API/AI·DB·DDL추가없음.

프론트: lib/departure.js는목표모델/허용상태·시각/차이·마지막하차+egress수식·충족/늦음분류·미확인숫자null을검증한다. FirstArrivals.jsx는기존h3/카드/CSS로오늘목표·예상목적지도착·목표기준예상여유/늦음·추정한계를표시하고미설정/지난목표/마지막도보·환승부족/실패·만료를구분한다. 클라이언트시계경과로첫승차접근불가·목표/기한이지나면이전목적지숫자를숨긴다. RoutineDeparture.jsx의이전목표미지원설명을현재선택평가와미래예약미지원으로맞췄다. 새색상/CSS/폰트/내비게이션체계없음.

실제 검증: backend/tests/test_target_arrival.py 신규11개5.199초 포함 최종전체386개147.203초통과. 같은시각정확한목표경계·늦음음수보존·마지막도보개인계수올림1회·2회환승/불일치·마지막도보누락/0초·미설정/이미지난목표무이월·UTC날짜와다른한국자정·기한/현재첫승차접근불가/총합불일치·미배분시간무가산을확인했다. 실제격리PostgreSQL/ASGI·합성도착으로본인루틴GET 목표평가/도착캐시무추가호출·평가중목표/프로필변경409를검증했다. 최초신규/전체모두통과해운영조건/시간정책을완화하지않았다.

frontend/tests/departure.test.js·components/FirstDeparture.test.jsx 신규7개 포함 전체229개10.04초·빌드1909모듈438ms통과. 목표수식/분류·부족마지막하차/도보·미확인숫자거부, 목표여유와정류장5분여유구분·늦음음수표시·마지막도보부족목적지숫자없음·만료시목표도착/차이제거를확인했다. 이번새외부조회/직접실키/AI호출0회다.

시각/서버: 합성응답·실제엄격클라이언트/FirstArrivals와기존CSS로1280×1400/390×2100에서목표충족추정/정류장여유와목표여유구분을확인했다. 화면캡처의아래부분제한을고려해미확인상태를단독렌더링하여1280×800/390×844에서마지막도보부족·목적지숫자없음도시각확인했다. 모바일body.scrollWidth=innerWidth=390, 줄바꿈/가로넘침없음. 실제사용자로그인·실경로도착정확도/보행·실휴대전화는검증제외. 임시goal-preview.html/jsx·검증탭삭제/viewport원복. 기존프로젝트uvicorn확인후숨김재시작, health/프론트200·비인증루틴GET401·OpenAPI target_evaluation필드존재확인. 새DDL없어0012유지.

문서/완료: Notion v0.78의활성API목록/설명·상태/5.7.6·날짜선택과후속범위·구현검증/변경이력을수정하고다시읽어저장을확인했다. F12관련다른담당변경/헤더를보존해목표평가내용만추가하고 api_contract.md전체미러대조일치를확인했다. target_arrival_api.md·departure_api.md·routine_departure_api.md·planning.md·personalization.md·logging.md·design_guide.md·screen_plan.md·todo.md·feature_breakdown.md동기화, F07-04는선택루틴현재후보의오늘평가범위로완료한다. 미지원매핑/원천시간·검증개인도보/F07-02a전체·미래예약/대체노선자동조회와다음차량은미완료유지. 다음F07-06 다음차량선택/갱신, 약속·참여자/채팅은사용자지정다른LLM담당이다. 게시전main2460bd7재확인·git diff --check 통과, 기능브랜치커밋/푸시·MR/병합은사용자수행. 명세:https://app.notion.com/p/3ebace1670c6806c8199cde33ebfbdfa.

배운 개념: 정류소탑승가능·환승연결가능·목적지목표도착은서로다른조건이다. 마지막도보가없으면차량하차시각으로목표충족을판정하면안된다. UTC날짜가아닌사용자의한국날짜로오늘목표를만들고지난목표를이월하지않아야한다. 개인화초/환승여유와타임라인이하나의프로필버전으로일치해야하며미배분총시간을임의로추가해서새근거로만들면안된다.

## 2026-10-14 — 실제 저장 루틴 출발 검증 준비 (미완료)

사용자 요청: 합성 검증과 실제 추천 성공을 구분하고 실제 저장 루틴을 검증한다. TODO·Notion v0.78 최신 페이지·routine_departure_api.md 및 실제 서비스/공급자/격리 테스트 코드를 확인했다. 계약 변경 없음, Notion 수정 불필요.

확인 결과: 개발 서버 /api/v1/health와 프론트 모두200. 저장 루틴을 읽기 전용 DB 연결로 조사했고, 스크린샷의 교회 루틴과 이름상 대응하는 활성 저장 항목2개 중 최근 항목을 검증 대상으로 준비했다. 해당 저장 후보는 BUS2구간/환승1회이고 접근·환승·마지막 WALKING 구간이 없다. 최신 공급자 응답에서 보완되는지와 실제 매핑 실패 원인은 아직 확인하지 않았으며, 이 정적 결과만으로 최신 출발 불가능을 확정하지 않는다. 기존 브라우저 탭 없음, 새 앱 탭은 로그아웃 상태였다. 실제 본인 브라우저 로그인 흐름 검증은 수행하지 않았다.

원본 루틴·장소·개인 설정을 메모리로 읽고 기존 격리 PostgreSQL/인증 ASGI 하네스에 복사하여 실제 최신 경로→루틴 일치→공식 매핑→도착→접근 도보→출발/환승/목표 상태를 고정 코드/집계만 출력하는 임시 검증 도구를 준비했다. HTTPS 공식 공급자만 허용·최대25회·조회 단계별 횟수·캐시 재조회 추가 호출 여부·원본 보존 비교·격리 스키마 정리·로그 비활성 포함. 임시 파일은 OS TEMP에 있고 py_compile 문법 검사만 통과했다. 도구 자체의 실제 실행/성공은 미검증이다. 초기 읽기 명령의 PYTHONPATH 누락은 설정 후 재실행했고 API/운영 코드 변경 없음.

기존 사용자 승인 검증49회/49회·잔여0은 공급자 쿼터/요금이 아니다. 추가 최대25회 승인을 비동기 질문으로 요청했고 아직 응답 대기라 외부 실제키/AI0회, 검증 성공을 보고하지 않는다. 승인이 오면 위 도구를 실행해 막힌 단계를 기록한다. 전체 자동 테스트/시각 검증은 이번에 재실행하지 않았다. 구현/계약 변경 없음, 기존 F07-04 체크는 구현·합성 검증 범위로 유지하며 실제 추천 완료를 의미하지 않는다.

## 2026-10-14 — 실제 저장 루틴 최신 출발 검증 결과 (실제 추천 차단 확인)

사용자가 외부 API 최대25회 추가 검증을 승인했다. 준비된 임시 도구로 스크린샷 이름과 대응하는 활성 루틴2개 중 최근 항목의 원본 경로·장소 좌표·개인 설정을 메모리로 읽고, 별도 임시 PostgreSQL 스키마/정상 가입·로그인·쿠키/CSRF 인증 ASGI 환경에 복사해 운영 공급자를 조회했다. 원본 사용자 루틴·장소·개인 설정은 두 실행 모두 전후 비교 일치, 임시 스키마 정리 완료. 실제 사용자 브라우저 로그인·화면 검증이나 위치/예측 정확도 검증은 수행하지 않았다.

처음 기본 샌드박스 실행의 출발지 지역 조회1회가 PROVIDER_UNAVAILABLE로 실패했다. 해당 단계의 진단1회에서 URLError→PermissionError/errno13을 확인했다. 두 시도는 샌드박스 네트워크 권한 때문에 차단되어 공급자 성공 응답이 없었으며 키 오류로 확정하지 않았다. 승인 범위로 네트워크 허용 실행에 전환하면서 이2회도 총한도에서 보수적으로 차감했다.

실제 네트워크 허용 1차: 루틴 검색 생성202→지역2회/대중교통1회→최신 후보14개→저장 경로 유일 일치 ready→출발 GET200. 공식 매핑4회에서 승차정류장 후보1·해당노선 후보1·정류소 순서 매칭 후 노선 상세정보 단계 ROUTE_INFO_UNCONFIRMED. 출발 status=insufficient_data, valid_for_guidance=false, 접근초/출발시각 없음, 환승 unknown, 목표 not_configured/TARGET_NOT_SET. 도착/접근 도보 API는 호출하지 않았다. 공개 출발 사유 ACCESS_TIME_UNCONFIRMED만으로는 근본 매핑 실패를 알 수 없어 별도 고정 진단으로 구분했다. 같은 GET 재조회200·외부 추가0회. 실제 외부 호출7회.

동일 실패 단계 원인 확인 2차: 최신 후보14개/유일일치/매핑 실패가 다시 재현됐고 노선 상세 API 응답 msgHeader.resultCode='4', msgBody 비어 있음, busRouteInfoItem 없음/행0을 확인했다. 외부7회, 같은 GET 추가호출0. 운영 파서가 정상 상세정보를 잘못 읽었다고 볼 근거는 없으며, 공식 공급자가 이 조회에 결과없음을 반환한 것이다. 공식 GBIS 노선정보 매뉴얼은 결과코드4를 결과 없음으로 설명한다: https://www.gbis.go.kr/gbis2014/publicService.action?cmd=mBusRouteInfo. 결과가 없는 원인(연계 노선 제공 범위/공급자 등록 불일치/일시 상태)은 아직 확정하지 않았다. 다른 API로 회차·방향을 임의 추론하지 않았다.

호출 집계: 공급자에 접근한 외부 검증14회(지역4·대중교통2·경기매핑8), 샌드박스 차단 시도2회 별도. 승인25회에서 총16회 시도로 보수 차감해 이번 승인 잔여9회, 자동 소진하지 않고 실패 원인 확인에서 중단. AI0회·버스 도착0회·접근 도보0회. 실제 출발 추천 성공을 확인하지 못했으며 출발숫자 차단은 현재 명세와 일치한다. 이전 누적49회에 이번 실제14회를 합한 실제 검증 누적63회, 이번 차단2회를 실제 공급자 조회로 합산하지 않는다.

문서/다음: 최신 Notion v0.78 재확인, API/계산 계약·운영 코드 변경 없으므로 Notion 변경 없음. todo.md의 다음 작업은 F07-06보다 실제 루틴의 공식 노선 상세/방향 근거 확보(F07-01c 관련)를 우선한다. 목표가 미설정이고 마지막도보 근거도 없어 목표 추천은 별도 조건이 남는다. 기존 구현 TODO를 실제 성공으로 승격하지 않는다. 이번 변경 파일은 development_log.md·todo.md뿐이며 자동 테스트는 새로 실행하지 않았다. 임시 검증 도구 py_compile 통과와 실제 격리 인증/API 검증 결과만 기록한다. 최신 origin/main2460bd7 확인, 기존 codex/target-arrival-evaluation에 검증 기록을 커밋/푸시하며 MR/병합은 사용자 수행.

## 2026-10-14 — 노선 상세 결과없음 대응 후속 보류

사용자가 실제 루틴의 공식 노선 상세 결과없음 대응을 나중으로 넘기도록 지시했다. 해당 특정 루틴 지원 확대는 F07-01c 관련 후속으로 보류하고 다음 우선 작업은 기존 F07-06 다음 차량 선택·갱신·기한처리로 복귀한다. 보류 이유는 마감까지 지원 경로의 핵심 출발 흐름을 먼저 완성하기 위함이다. 상세정보/방향 검증을 생략하거나 확인되지 않은 루틴에 출발숫자를 제공하는 변경은 없다. 실제 출발 성공은 여전히 미확인이고 해당 루틴은 확인불가 상태를 유지한다. 추가 외부 호출0회, 이전 이번 승인 잔여9회 자동 사용 없음. 변경 파일 todo.md·development_log.md, API 계약/운영 코드/완료 체크 변경 없음·Notion 변경 불필요, 테스트 재실행 없음. 우선순위만 변경하며 기존 기능 브랜치에 기록한다.

## 2026-10-14 — F07-06a 다음 접근 가능 차량 선택 완료 (F07-06 전체는 미완료)

목표/명세: 사용자 다음 진행 요청으로 최신 Notion v0.78·TODO·기획/개인화/로깅/프롬프트·기존 UI/디자인·실제 guidance/arrivals 코드를 비교했다. 최신 origin/main2460bd7에서 codex/next-reachable-vehicle 생성, 미병합 선행 루틴/외부WIP/문구/도보/목표/실검증·보류 기록을 f000334/110cd8d/29812fc/e564dcf/783388f/ea342c8/4c38dc7로 포함했다. 다른 담당 F12 문서 내용을 보존했다.

범위 판단/이유: 기존 계산은 가장 이른 차량에 접근시간이 부족하면 다음 실제 제공 후보가 있어도 not_enough_time이었다. 먼저 실제 제공 후보의 접근 가능성을 확인하고 출발·환승·목표를 재계산하는 F07-06a를 구현한다. 기존 사용자 확정 now-s>W/2·유효 수동 departed 확인 없음 전환은 운영 /trips 및 이벤트 저장/조회가 현재 코드에 없어 F07-06b로 미완료 유지한다. F07-06 전체를 완료로 표시하지 않는다. 실제 미이동·놓침 관측을 만들지 않고 GPS 판단/공유/학습도 추가하지 않는다. 사용자지시대로 특정 루틴 노선 상세 결과없음 대응은 후속 보류 유지.

계약/구현: 구현 전에 Notion v0.79의5.7.7로 설계와 호환성을 저장 확인. backend/app/guidance/service.py는 유효 도착 목록을 ETA/ID 정렬하고 ETA-now>=개인화 접근W인 가장 이른 후보를 선택한다. 같은W 경계 허용·B별도/기존below_buffer 경고 유지, 가능한 후보가 없으면 기존첫후보 음수slack/not_enough_time 유지. 다음 선택 고정사유 NEXT_REACHABLE_VEHICLE 추가, 기존 추천/선택/차량ETA/여유 숫자를 선택후보로 계산한다. 기존 순차환승/루틴목표 평가에 새 첫차량ETA가 연결되며 원래 도착 후보/수신/TTL·프로필/본인/경로 전후검사 유지. 요청/응답필드/HTTP경로/권한/쿼터/캐시/DDL/AI 변경없고 새외부조회없음. frontend/src/components/FirstArrivals.jsx는 기존카드/색상/CSS로 유효안내에 앞차량 제외이유1문장 표시. 60초/탭복귀/숨김취소·기한/실패 흐름은 그대로 재사용.

실제 검증: backend/tests/test_next_vehicle.py 신규8개2.210초 통과. 접근불가첫차량→다음제공차량·수신/기한/목록보존, 접근가능첫차량의below_buffer 유지, 정확W/미세부족·now 기준, 가능한후보없음 음수보존, 입력순서/동일ETA-ID 결정성, 접근누락/기한/시계오류 무전환, 선택첫ETA로환승최소시각/목적지ETA/목표차이 재계산, 격리 실제PostgreSQL/정상쿠키·CSRF ASGI 루틴GET→다음선택/목표·캐시추가호출0 확인. backend/tests/test_departure.py는 다음후보가없는음수여유테스트 이름만명확히했다. 최종전체394개167.811초 통과, 이번 실패/운영검사완화없음. frontend/tests/departure.test.js 제공다음차량 응답수락·components/FirstDeparture.test.jsx 60초후다음차량/새시각/전환이유/이전숫자제거 검증 추가, 전체231개10.63초·빌드1909모듈436ms통과.

시각/서버: 합성순수계산응답을 실제readFirstDeparture 엄격클라이언트/FirstArrivals·기존CSS에 연결해PC1280×1000/모바일390×1100의 다음차량사유·새출발·여유·환승·목표·추정표기를 확인했다. 모바일body.scrollWidth=innerWidth390·줄바꿈/가로넘침없음. 임시next-preview.html/jsx/json 삭제·검증탭닫기/viewport원복. 실제사용자로그인·실경로양수추천/도착정확도/실기기보행은 미검증. 프로젝트uvicorn만확인후숨김재시작, health/프론트200·비인증루틴GET401 확인. 직접외부실키/AI0회, 이전승인 잔여9회사용없음, 새DDL없음.

문서/완료: Notion v0.79의5.7.7 구현상태·기존첫차량선택정책·버전/변경이력과이유/호환영향/선행미구현을맞추고재조회저장확인. api_contract.md전체1657행 해시대조일치, unrelated F12보존. next_vehicle_api.md·departure_api.md·routine_departure_api.md·planning.md·personalization.md·logging.md·design_guide.md·screen_plan.md·todo.md·feature_breakdown.md 동기화. F07-06a만체크하고F07-06b/전체06은미완료, 다음은실제이동/수동departed 선행연결 준비. 배운개념: 현재 접근불가능한 차량 제외와 출발확인누락의 절반경과 정책은 서로다르다. 차량ETA를바꿨으면환승/목표타임라인도반드시재계산해야한다. 기한이유효한기존후보재선택은수신시각갱신이아니다. 기능브랜치 커밋·푸시, MR/병합은사용자수행. 명세:https://app.notion.com/p/3ebace1670c6806c8199cde33ebfbdfa.

## 2026-10-14 — F08-01/F08-02a 안내 연결 이동·수동 출발 확인 완료

목표/근거: 사용자 다음 진행 요청으로 최신 Notion v0.79·TODO/F08·planning/personalization/logging·기존DTO/라우터/DB·UI/디자인을 비교했다. 운영 /trips와 수동 이벤트가 없어 F07-06b를 실제 출발 상태에 연결할 선행 기능을 구현한다. 최신 origin/main2460bd7에서 codex/manual-departure-session 생성하고 미병합 루틴/도보/목표/다음차량 및 사용자 보류 기록을95072d9·20b533c·4538dd4·384e83b·304bb0a·98a98a7·7ff5f57·4af96f1로 보존했다. Notion v0.80의5.8.1 계약을 구현 전 저장 확인하고 변경 중 24시간 생성키/현재 접근 가능성 검사를 다시 동기화했다. 다른 담당 F12 명세/이력 보존, 해당 기능을 구현/검증했다고 주장하지 않는다.

구현/이유: guidance/issued.py·dto.py·routine.py는 유효 루틴 안내에 본인/경로/루틴·장소/프로필 버전과 묶인 nullable guidance_id 토큰을 최근128개 메모리에 발급한다. 기한은 기존안내/검색최소·GET DB쓰기/실제출발 없음. trips/router·dto·service·repository는 POST /trips의기존guidance_id/mode 입력으로 불변 안내·좌표없는경로 스냅샷과 assisted/baseline 세션을원자저장한다. 본인당active1개·공유잠금현재버전/원래후보·현재접근가능성검사, 동일안내/mode 재전송200·다른mode409, 선택Idempotency-Key24시간·본문변경409. 안내가만료돼도이미저장된본인결과복구. 세션 생성은 출발신고가 아니다.

수동출발: POST /trips/{id}/events의최초departed/source manual·client_event UUID·첫ordered_leg만지원한다. 시간대있는ISO문자열·안내산정이상/수신이하 검증, received_at과발생시각·입력지연별도저장. 행/본인잠금으로동일본문200/다른본문409·다른ID중복출발/취소세션새출발409. 같은시각의다른UTC오프셋은정규화해동일재전송. 실제이동/속도/탑승인증·놓침/GPS판정·학습관측은생성하지않는다. 본인목록/상세복구·expected_version 취소제공, 과거출발기록은취소로삭제하지않는다. 90일만료읽기차단·다음쓰기본인만료행/스냅샷cascade정리. 접근완료/탑승/하차·정정/파생학습·내보내기/삭제작업/매일청소·약속안내토큰은후속이다.

프론트: trips.js 엄격응답/본인연결·CSRF/생성→저장첫구간GET→manual신고·같은이벤트ID/발생시각재시도, ManualDeparture.jsx 실제서버저장후성공·중복누름차단/이탈취소·진행중본인복구/취소. FirstArrivals/RoutineDeparture에연결, 이전실제이동미지원문구수정·departure.jsnullable토큰검증. 기존info-box/h3/button-row/primary/secondary/CSS재사용·새테마없음. 검증중취소된동일안내토큰재생성은서버가과거취소결과를반환하므로클라이언트에서새안내전까지재시작버튼차단/갱신안내를추가했다. 아직F07-06b자동전환은연결하지않는다.

실제검증: 신규backend/tests/test_manual_trips.py12개·격리PostgreSQL/정상인증ASGI로불변스냅샷/생성만으로미출발·토큰메모리소실뒤재전송·모드/헤더키충돌·동시동일생성201/200·active유일·버전/장소/프로필변경차단/쓰기없음·토큰기한/타인/CSRF/no-store·시각/구간/source/미지원type차단·첫출발재전송/순서/취소/기록보존·baseline·90일차단/cascade확인. 초기10개19.943초통과, 전체406개194.374초통과, 마지막ISO문자열검증강화와숫자시각거부추가후관련12개23.270초재통과. migrations전체왕복/기존저장/버전/테이블기대갱신포함. 실패나운영검사완화없음. 프론트전체242개37.85초통과후취소안내토큰차단/버튼행·제목최종수정관련6개1.73초통과, 최종빌드1911모듈423ms. 실API클라이언트단위로세션→저장구간→manual본문/시간·실패같은이벤트재시도/기존출발무재전송·취소버전/타인루틴·GPS거부검증. 컴포넌트서버확인전성공없음·중복/취소/이탈·만료무신규세션·새안내전취소토큰차단검증.

시각/DB: 실제ManualDeparture/trips클라이언트와합성API·기존CSS로PC1280×800/모바일390×844의출발버튼→저장성공/취소·실패→동일시도재시도성공을확인했다. 모바일body.scrollWidth=innerWidth390·줄바꿈/가로넘침없음. 취소후새안내전차단문구는최종관련컴포넌트테스트로확인, 해당추가문구의별도시각확인은미실행이다. 임시manual-preview.html/jsx삭제·탭닫기/viewport원복. 실제사용자로그인/실경로추천성공/실기기이동정확도는미검증. 개발DB기존head0012확인후0013_manual_trips적용·4개신규테이블·회원/장소/루틴/plan기존개수보존확인. 별도F12의미병합0013과향후merge시Alembic head통합필요, 무관한migration변경없음. 직접외부키/AI0회·이전추가검증승인잔여9회사용없음.

문서/완료: Notion v0.80의5.8.1 구현·범위/시간/중복/보관·기존선행미구현표현·버전/변경이력/호환영향을수정하고재조회저장확인. api_contract.md전체1671행해시대조일치/다른담당F12보존. trip_api.md·planning.md·personalization.md·logging.md·design_guide.md·screen_plan.md·routine_departure_api.md·todo.md·feature_breakdown.md동기화. F08-01과F08-02a만체크, 상위F08-02/04/05·F07-06b/전체06은미완료. 배운개념: 세션생성과실제출발신고는별도사실이며과거안내스냅샷을현재예측으로덮어쓰지않는다. 멱등키/이벤트ID와발생·수신시각을분리하면통신재시도로거짓중복관측을막을수있다. 코드·문서기능브랜치커밋/푸시·MR/병합은사용자수행. 다음은저장된수동departed를F07-06b절반경과선택에연결. 명세:https://app.notion.com/p/3ebace1670c6806c8199cde33ebfbdfa.

게시 전 최종 서버 확인: 프로젝트uvicorn숨김재시작 후 health/프론트200·비인증tripsGET401·OpenAPI이동3경로/안내토큰필드존재 확인. 최신origin/main2460bd7재확인. git diff --check 통과, 임시프리뷰없음. Notion게시전재조회와로컬미러일치확인 후기능브랜치커밋/푸시한다.

## 2026-10-14 — F07-06b 지원 루틴 절반 경과 다음 차량 전환

목표/이유: 사용자 요청에 따라 수동 출발 저장을 절반 경과 선택에 연결했다. 출발 확인 부재는 실제 미출발 증거가 아니며 관측/학습으로 저장하지 않는다. 최신 main2460bd7에서 codex/unconfirmed-departure-switch 생성, 미병합 선행 f990370/d27ef97/803b1d0/8cf836f/94720a1/4c6e983/ffcb61c/ea7c9f8/02e5461을 포함했다. 사용자 담당 분리 및 공식 노선 상세 결과없음 대응 후속 보류를 유지했다. MR/병합은 사용자 수행.

구현: arrivals/cache.py와service.py에 공식 매핑+차량 비식별 메모리키 추가. 공개 후보UUID는 검색마다 바뀌므로 같은 차량 비교에 그대로 사용할 수 없다. 원래 ID는 새 DB/응답/로그에 기록하지 않는다. guidance/selection.py의 본인/루틴128개 상태·제외16개·잠금429로 마지막 정상응답 s/W/ETA를 기억한다. now-s > W/2(같음 유지, B 제외)에서 다음 제공 차량 ETA가 현재보다 늦고 W+B를 확보하는지 검사한다. 이미 제외한 차량은 돌아가지 않고 후보/식별 부족은 숫자를 숨긴다. 동일 검색 수신/기한을 보존하고 새로운 첫 차량으로 환승/오늘 목표를 한 번 재계산한다. 프로필/접근/경로/장소/선택ETA경과/메모리소실은 초기화, 공급자 대기중 ETA 경과도 재검사한다. DB active trip/manual event·현재 루틴 버전/서명/장소를 대조하고 조회 전후 변경409에서는 선택 기준을 커밋하지 않는다. 세션만 생성/취소/만료/다른 경로는 출발 억제 근거가 아니다. 동일 차량 운행회 인증은 아니므로 선택 ETA가 끝나면 기준을 폐기한다.

파일: backend/app/arrivals/{cache,service}.py, guidance/{dto,routine,service,selection}.py, trips/repository.py, tests/test_unconfirmed_selection.py·test_walking_recalculation.py. first.departure.v1 departure_state 추가, 유효 신고 후 모든 출발전 시각/여유/환승/목표/토큰 차단 및 공급자 도착 조회 생략. frontend FirstArrivals/ManualDeparture/RoutineDeparture·lib/departure.js 및 관련4개 테스트: 저장/복구 즉시 숫자 제거·60초 도착/300초 검색 자동조회 중지·늦은 성공/오류 무시·취소 뒤 새 검색. 기존 CSS/테마 유지. 신규 DDL 없음.

실제 검증: 신규15개9.401초 후 조회중 ETA 경과 방어/테스트 추가 최종16개10.647초 통과. strict 절반/.001·새검색 차량키·W+B/후보없음·제외복귀차단·프로필/ETA변경·근거없음·동시신고409·잠금/용량/만료·실제 격리 PostgreSQL/인증ASGI의 신고복구/단순생성/취소/재계산 확인. 초기 fixture가 소수 공급자 초를 만들어 실패한 것은 정수 공급자 계약에 맞게 fixture를 고쳤다. 전체 첫 실행421개211.707초에서 기존 access lock 테스트 ASGI3초 타임아웃1개, 동일 테스트 단독2.113초 통과(안내716ms). 다음 전체421개224.349초에서 기존 stale profile/place 테스트409 대신422 한 건, 단독 재현은0.828초 통과하여 당시422 원인을 확정하지 않는다. 버전 테스트가 벽시계와 독립적이도록 해당 테스트의 repository.clock만 verified_at+1초로 고정, 단독0.769초 통과. 운영 검증/시간제한 완화 없음. 최종 전체421개219.786초 통과(마지막 ETA 방어 추가 전), 이후 관련16개 재통과. 전체422개 재실행은 하지 않았다.

프론트 전체248개15.21초 통과 후 마지막 신고 뒤 응답 무시/추가검증 포함 관련4파일57개3.09초 재통과·최종1911모듈 빌드514ms 성공. 최종 전체250개 일괄 실행으로 주장하지 않는다. 실제 엄격 API 클라이언트/실 FirstArrivals/기존 CSS·합성 응답으로 다음차량 전환/다음없음/출발확인 세 상태 PC1280×900 및 모바일390×900 또는844 확인. 모바일 가로넘침 없음(body.scrollWidth=innerWidth390), 임시 half-preview 파일 삭제·탭 종료/viewport 원복. 실제 로그인/사용자 루틴 추천 성공/실이동 정확도/실기기 검증은 미실행. 직접 외부키/AI0회, 기존 추가 승인 잔여9회 미사용.

문서: 구현 전 Notion 최신 v0.80 확인 후5.7.8 v0.81 설계를 먼저 저장했다. 구현 후 범위/상태/시간/메모리/출발저장전후/자동조회/호환성/검증/변경이력 수정 및 재조회 저장 확인. api_contract.md는 최신 페이지 내용과 맞추고 F12 다른 담당 내용 보존. planning/personalization/logging/design_guide/screen_plan/routine_departure_api/departure_api/trip_api/next_vehicle_api와TODO/feature 동기화. F07-06/06b는 지원 경기 BUS 루틴 범위로만 완료, 일반 후보 상세는06a 정책 유지. F07-07 및 나머지 F08 이벤트/정정/학습은 후속. 개념: 화면에 제공한 추정과 실제 행동 신고는 서로 다른 사실이다. 서버 메모리 후보 선택과 저장 이벤트 상태를 재검사해야 동시 신고가 이전 안내를 되살리는 것을 막을 수 있다. 명세 https://app.notion.com/p/3ebace1670c6806c8199cde33ebfbdfa.

게시 전 최종 확인: 최신 origin/main2460bd7 유지·Notion v0.81 재조회 변경없음·로컬미러1683행 해시일치. 프로젝트 uvicorn 숨김 재시작 후 backend health200·frontend200·비인증 routines401·OpenAPI departure_state enum/default 확인. git diff --check 통과·임시프리뷰 없음. 기능 브랜치 커밋/푸시, MR/병합은 사용자 수행.

## 2026-10-14 — F07-07a 첫 탑승 전 현재 위치 기반 남은 경로

목표/범위 결정 이유: 출발 신고만으로 현재 남은 도보나 탑승 구간을 알 수 없으므로 이전 W를 다시 빼거나 W-경과초로 진도를 추측하지 않는다. 최신 Notion v0.81·로컬 기획/개인화/여정/디자인/화면·TODO를 확인하고, 기존 origin_override/current/map 초안을 구체화한 v0.82 5.7.9를 구현 전에 저장·재조회했다. 첫 탑승 전이라는 명시 확인과 지금 위치 확인에 한정한 F07-07a로 분리했다. 차량 안/환승 중 F07-07b는 F08 접근 완료/탑승/하차 선행이 없어 상위F07-07 미체크 유지. 특정 공식 노선 상세 결과없음 대응과 실경로 정확도는 사용자 요청 후속 보류.

Git: 최신 origin/main2460bd7에서 codex/moving-remaining-guidance 생성 후 기존 기능 선행 f990370/d27ef97/803b1d0/8cf836f/94720a1/4c6e983/ffcb61c/ea7c9f8/02e5461/33db42f을 cherry-pick했다. 외부 WIP checkpoint도 보존했다. MR 생성/병합은 사용자 수행.

구현 파일/계약: backend/app/guidance/remaining.py·trips/dto.py/router.py에 현재점 검색 POST202 및 본인 버전 GET trip.remaining.v1 추가. 본인 active manual departed·루틴버전/원래경로·장소·프로필/신고 전후 검사, 잘못된stage/saved_place/확인없음/임의시간422, 취소/변경409·타인/만료404. 현재점→서버 루틴 목적지 검색만 만들고 첫 차량부터 나머지 구간이 같은 유일 후보의 새로운 접근 W만 사용한다. 여유S=ETA-(now+W), 현재계수·B·순차환승/오늘목표를 재사용. 누락/0/부족/미지원/만료 시 숫자 차단, 기존 first-departure/스냅샷/관측/프로필/토큰은 덮어쓰지 않는다. 검색/이동 생성 기존쿼터 공유, 직접 외부키/AI0회·새DDL없음. 기존 worker만 임시 좌표 처리, 서버 연결은 본인/검색/trip/event/버전/프로필·32개 메모리로 제한하고 원문좌표 새DB/일반로그/URL/AI 저장 없음. 현재 위치 확인 사용은 접수+120초·검색/도착 최소기한, 재시작/퇴출/만료는 새 위치 확인. 이는 GPS 측정 최신성/물리 위치·탑승 인증이 아니다.

프론트 파일: RemainingGuidance.jsx·lib/remaining.js 신설, ManualDeparture.jsx 신고 저장/복구 뒤 연결. OriginSelector.jsx currentPointOnly 옵션으로 기존 기본화면은 유지하고 남은 경로에서는 현재/지도만 허용·저장탭/저장버튼 숨김. 첫 탑승 전 확인 후 요청, 유효 동안60초/탭복귀 GET·숨김/이탈 취소·만료/실패/위치 재선택/안내중지 즉시 숫자 제거·늦은 응답 무시. 현재점 자동 재측정·원래 출발지 자동 재검색 없음. 클라이언트도 이전 위치기한 최소 유지, 여유/설정초 보존·자동 경과를 새 보행 관측으로 만들지 않는다. 중지 버튼은 화면 종료이며 boarded 이벤트 저장이 아니다. 기존 CSS·팔레트·버튼·카드 재사용, RemainingInfo 공통 표시로 검증/표시 일치.

실제 검증: backend/tests/test_remaining_guidance.py의8개 PostgreSQL 격리·정상인증ASGI/합성 공급자 테스트 최종24.829초 통과. 새로운 접근120초가 원래300초와 다름·현재점 전달·스냅샷 불변·유효숫자·CSRF/미확인/숫자1확인/미지원stage/저장장소/임의시간 차단·생성만/취소 비출발·멱등기한/재시작·0도보·다른trip/버전/프로필/현재점 만료·경로 없음/변경/중복·조회중취소409 확인. 첫 실행8개22.226초 실패4개는 fixture candidate 메서드가 기존 self.candidate 필드와 충돌하고 재가입409를 만든 테스트 구성 오류였다. 메서드 이름을 바꾸고 생성만 상태를 격리DB로 구성해 수정했으며 운영검증을 완화하지 않았다.

프론트 전체264개16.36초 통과(최종 UI 추출/여유초/기한보호 전), 최종 관련4파일33개4.43초 재통과·1913모듈 빌드521ms 성공. 첫33개 중2실패는 SDK fixture request_id 누락과 mock 재조회가 위치기한을 임의 연장하던 오류를 수정했다. 실제 RemainingInfo/엄격readRemaining·RemainingGuidance/OriginSelector·기존CSS 합성 프리뷰 PC1280×1000/모바일390×900의 현재점 선택 UI·유효/설정여유부족/근거부족·중지 복귀를 확인, body.scrollWidth<=innerWidth 가로넘침 없음. 클릭으로 실제 GPS 권한 요청/실사용자 로그인/지도 정밀 선택/실이동 정확도·실경로 추천 성공은 미검증. 기한/오류/늦은 응답/첫탑승전확인 차단은 컴포넌트 테스트로 확인했으며 별도 전체 실기기 흐름으로 주장하지 않는다. 임시 remaining-preview.html/jsx 제거·탭 닫기·viewport 원복.

전체 백엔드 첫430개263.913초 실행은 기존 access walk 변경중 테스트 ASGI3초 타임아웃1개와 origins 개인정보 테스트의 처리시간114.58에 합성 위치 정확도14.5 문자열이 포함된 오탐1개로 실패. access case는 운영/테스트 시간제한 변경 없이 단독 통과. origins 테스트는 JSON 레코드로 파싱해 latitude/longitude/accuracy/captured_at/origin 키 및 비밀값 유출을 검사하고 공개 timestamp/duration_ms 숫자와 구분하도록 수정했다. test_origins.py만 바꾸며 실제 로깅 계약 변경 없음. 초기 수정 후 json import 누락을 바로 보완, 전체 재실행 결과는 아래 최종 기록을 따른다. 개인정보 검사 자체를 삭제하지 않았다.

문서: moving_guidance_api.md 신설, planning/personalization/logging/design_guide/screen_plan/routine_departure_api/trip_api/TODO/feature 동기화. Notion v0.82 5.7.9·호환성/변경이력·상태·범위 재확인 및 로컬 미러 동기화 결과는 아래 기록. 배운 개념: 출발 시각은 진행 위치가 아니며 현재점부터 계산한 남은 경로와 원래 경로를 구분해야 한다. 메모리 연결의 짧은 기한과 상태 전후 검사로 오래된 위치/취소된 이동에서 숫자를 유지하지 않게 한다. 로그 개인정보 검사는 값의 필드를 구분해야 정상 처리시간의 우연한 숫자를 유출로 오인하지 않는다. 다음은 F08-02b 접근 완료/탑승 기록→F07-07b 현재 구간별 남은 경로. 명세 https://app.notion.com/p/3ebace1670c6806c8199cde33ebfbdfa.

최종 검증/서버: 전체 백엔드430개242.547초 재실행 통과(운영 시간제한 변경 없음). 프론트 최종 관련33개4.43초/빌드1913모듈521ms 재통과. 개발 서버 숨김 재시작·backend health200/frontend200·비인증 remaining GET401·OpenAPI 신규2경로/stage 상수 확인. Notion v0.82 구현 상태/전체F07-07 미완료 범위/새 API 목록/호환성·변경이력/검증 저장 및 재조회 확인. 로컬 api_contract.md 동기화·F12 보존, 추가 외부 승인 잔여9회 미사용.

게시 전 확인: 최신 origin/main2460bd7 유지, Notion v0.82 재조회 변경없음/로컬미러 1706행 해시일치, git diff --check 통과·임시 프리뷰 없음. codex/moving-remaining-guidance 기능 브랜치에 커밋·푸시하며 MR/병합은 사용자 수행.

## 2026-10-14 — F12 일회성 약속 코어 REST·초대

목표/이유: 사용자 지시로 F07-02a 이후 작업을 F12(일회성 약속)부터 진행하고 C:\Users\태휘\Desktop\day2-json-api-practice\middle-meeting\홍태휘\product의 완성 서비스("절반" — 방·정적 지하철 추천·채팅 컨텍스트·AI 해설)를 참고해 속도를 올리기로 했다. product는 F13 추천·F14 채팅 단계에서 본격 참조하고, F12 코어는 확정된 계약(meeting_api.md·Notion 16절)이 이미 상세하므로 계약을 그대로 구현했다. 사용자가 직접 F07-02a-1/-2를 구현·검증 완료(codex/departure-guidance-clarity·Notion v0.77)해 착수 순서를 F12로 조정했고, 표시 명확성 미커밋 파일은 해당 브랜치에 WIP 커밋(fd1d8d1)으로 보존했다. 작업 트리 공유 충돌을 피하려 git worktree(C:\projects\timeisnow-f12)에서 codex/meeting-core(최신 main2460bd7)로 진행했다.

구현 파일: backend/migrations/versions/0013_meeting_core.py(meetings·meeting_members·meeting_revisions·meeting_invites·meeting_idempotency_keys·jobs), backend/app/meetings/{__init__,dto,repository,service,router}.py, backend/app/main.py(라우터·no-store 경로), backend/app/common/errors.py(AuthError details), backend/app/journeys/service.py(/jobs가 약속 삭제 작업 폴백 조회), backend/tests/test_meetings.py 신규15개·test_migrations.py 갱신. 약속 생성은 Idempotency-Key 필수(meeting_idempotency_keys, 같은 본문 재현·다른 본문 409 IDEMPOTENCY_CONFLICT), 확정은 직접 목적지(name 1~100자·위도 -90~90·경도 -180~180·provider/place_ref null만·Asia/Seoul·미래 시각)로 revision_no 순차 저장, 상태 전이는 draft→completed를 409 MEETING_NOT_CONFIRMED로 차단, 삭제는 202 job(succeeded 동기 완료)과 즉시 CASCADE 차단. 초대는 token_urlsafe(32) 원문 응답·sha256 해시만 저장·24시간·활성 1개(재발급 시 기존 철회)·발급/철회마다 약속 버전 증가, 미리보기는 사용자당 10회/분, 수락은 약속 행 잠금 하 원자적 잔여 인원·토큰 소비·재수락 200/재활성(탈퇴 후 새 초대)·만석 409 MEETING_FULL, 탈퇴는 주최자 409 ORGANIZER_CANNOT_LEAVE·member 버전 검사.

실제 검증: test_meetings.py 신규15개 통과(생성 멱등·목록 커서/필터 재사용 422·확정 검증/과거 시각/타임존/좌표 경계·전이 규칙·초대 만석/재발급 철회/만료 404/멱등 409·수락 경쟁 만석 재현 fixture·재활성·탈퇴·삭제 job 조회·401/403/404/409/422). 전체 백엔드 358개 132.6초 통과. 프론트 변경 없음. 이번 실제 외부 키/AI 호출 0회.

디버그 기록: 초안 테스트에서 404/503이 났는데 원인은 테스트 헬퍼가 쿼리스트링을 path에 붙인 것(? 포함 경로는 ASGI scope.path에 그대로 들어가 라우트 미매칭)과 repository insert_invite의 SQL 자리표시자 5개/값 4개 불일치였다. 후자는 발급 응답에 token 해시 대신 원문이 들어가려던 실수로 수정했다. 비참여자 PATCH 403 기대도 비참여자는 404가 올바른 계약 동작이라 테스트에서 먼저 참여시키도록 고쳤다. DATABASE_ERROR 추적을 위해 database.py에 임시 traceback print를 넣었다가 되돌렸다.

문서/상태: Notion v0.78로 갱신(16절 상태·일부 구현, 3절 /jobs 설명, 4절 구현 상태, 직접 목적지 F12 검증 규칙, 초대 응답 캐시 미구현/409 동작, 변경 이력) 후 재조회해 저장 확인. api_contract.md를 v0.78 본문으로 전체 재생성(BOM 없음). meeting_api.md v0.3·database_schema.md 구현 상태·todo.md·feature_breakdown.md 동기화. product 포팅은 F13/F14에서 진행 예정이며 이번에는 참고만 했다. 명세: https://app.notion.com/p/3ebace1670c6806c8199cde33ebfbdfa.

남음: F12의 혼자 가는 일정·루틴 없는 개인별 출발 안내 연결, 초대 응답 캐시(암호화), 추천 기반 확정(F13)·개인 출발지·출발 안내·공유(F15)·채팅/WS(F14), 프론트 약속 화면. 다음은 사용자와 F13/F14 순서를 확인 후 진행한다. 기능 브랜치 커밋·푸시 후 MR/병합은 사용자가 수행한다.

배운개념: 버전 잠금이 있는 공동 자원은 상태 전이·멤버 변동·초대 발급까지 모두 약속 버전을 올려야 상대 화면이 변화를 감지한다. 멱등 재현을 할 수 없는 생성 응답(토큰 등)은 같은 키 재요청에 409로 명확히 응답하고 재시도 경로를 계약에 남기는 것이 조용한 중복 생성보다 낫다. 여러 테이블을 건드리는 수락/탈퇴는 고유 제약과 행 잠금 위에서 원자적으로 처리해야 동시 요청에 만석이 지켜진다.

## 2026-10-14 — F12 meetings 객체지향 리팩터링(ABC 포트 + 의존성 주입)

목표/이유: 사용자 요청으로 F12에서 새로 나눠진 meetings 부분을 python abc 추상 클래스·상속·의존성 주입 구조로 바꿨다. 계약 변경은 없다.

구조: app/common/ports.py에 협업 포트 4종(Clock·Database·Identity·TokenIssuer)과 기본 어댑터(UtcClock·PostgresDatabase·SessionIdentity·UrlSafeTokenIssuer)를 뒀다. app/meetings/repository.py는 MeetingRepository(ABC, 34개 추상 메서드)와 PostgresMeetingRepository 구현체로 나눴고 psycopg Jsonb 변환은 어댑터가 맡아 서비스는 일반 dict를 넘긴다. app/meetings/service.py는 모듈 함수들에서 MeetingService 클래스로 바꿨고 협업 객체 5개(repository·database·identity·clock·tokens)를 생성자로 주입받는다. 순수 계산(커서 코딩·버전 검사·응답 조립)은 모듈 수준 함수로 유지했다. app/meetings/wiring.py가 조립 지점이며 build_meeting_service()는 인자로 협업 객체 교체를 허용하고 get_meeting_service()가 FastAPI Depends로 쓰인다. 라우터는 service 모듈 참조 대신 Depends(get_meeting_service)로 받는다. journeys/service.py의 /jobs 폴백은 build_meeting_service().job_result로 호출을 고쳤다.

이유: F13(중간 만남 추천)·F14(채팅)가 같은 meeting 테이블과 인증·멱등·락 관심사를 재사용할 예정이라 저장소·인증·시계·토큰 발급을 교체 가능한 포트로 분리해두면 나중 구현과 테스트가 DB 없이 규칙만 검증할 수 있다. product 포팅 때도 이 경계를 그대로 쓴다.

실제 검증: tests/test_meetings_di.py 신규 7개(포트 인스턴스화 불가·Postgres 어댑터가 포트 충족·오래된 버전 409·종료 약속 변경 거부·draft 완료 전이 차단·주최자 탈퇴 차단+쓰기 락 선점 확인·쓰기 경로 CSRF 인증 거치는지 확인) — 메모리 저장소·고정 시계·가짜 인증을 주입해 DB·HTTP 없이 실행. 기존 test_meetings.py 15개(실제 ASGI+PostgreSQL)도 통과해 두 경로가 같은 규칙을 확인한다. 전체 백엔드 365개 137초 통과. 참고: 전체 실행 1회에서 test_connected_arrival_probe 1건 실패가 나왔으나 재실행 2회·단독 3회 모두 통과해 일시적 플레이키로 판단, 이번 변경과 무관한 파일이다.

명세 영향: 없음. 내부 구조 변경으로 요청·응답·오류 코드는 그대로다(AGENTS.md 3절에 따라 Notion 미수정). 문서 갱신도 이 일지뿐이다.

배운개념: 추상 포트는 '무엇이 필요한가'를 계약으로 남기고 어댑터는 '어떻게'를 담는다. 트랜잭션 연결도 Database 포트로 감싸면 서비스 테스트에서 실제 DB를 요구하지 않게 된다. 다만 외부 시간(now())을 SQL에 남겨두는 쿼리는 어댑터 내부에 유지했는데, 저장소별 시계 통일은 F13에서 다시 검토한다.


## 2026-10-14 — 미병합 브랜치 main 통합

사용자가 모든 브랜치를 확인해 미병합 커밋을 main에 합치도록 명시 요청했다. 이번 요청이 기존 기능별 사용자 MR/병합 규칙보다 우선하므로 MR 없이 직접 main 반영한다. 최신 main772885f에는 moving-remaining-guidance까지 이미 병합되어 있었다. 로컬/원격 전체 브랜치를 git cherry 패치 동등성으로 대조해 실제 미반영은 meeting-core 2cc3d3f/8420f17과 journey-method-priority-main 5126e5e만 확인했다. 과거 출발/루틴/도보 브랜치는 SHA가 달라도 패치가 이미 반영되어 중복 적용하지 않는다. 다른 담당 worktree는 읽기만 확인(깨끗함)했고 변경/메시지 전송 없음.

최신main 기반 codex/integrate-unmerged-branches에서 meeting-core merge. API/서버 라우터·마이그레이션 테스트/개발일지/TODO 충돌은 두 기능을 보존하여 해결하고 최신 Notion v0.82의 로컬 API 미러는 유지했다. trips와meetings 등록/no-store 모두 유지, 공통 AuthError.details를 전달해 약속 오래된 버전의 current_version을 보존한다. 최초 관련23개17.028초 실행의3개 오류는 충돌 해결 중 details 전달을 빠뜨린 것이며 수정 후23개17.172초 통과. 기존 정책/입력/오류계약을 변경하지 않은 통합 수정이다.

0013_manual_trips와0013_meeting_core는 둘다0012 부모를 가진 독립 migration이다. 기존 revision ID/부모를 다시 쓰지 않고 no-op0014_integrated_features merge revision으로 연결해 어느 기존 설치도 누락된 부모를 적용한 후 단일 head로 올라가게 했다. test_migrations는 두 도메인 테이블의 합집합과 통합 head·기존 데이터·반복 upgrade/downgrade를 검증한다. 개발DB 사전 head0013_manual_trips·회원21/장소35/루틴12/이동0/안내스냅샷0 확인. 적용/최종전체 검증은 후속기록에 남긴다.

Notion 최신 읽기 최초 시도는 도구 오류로 응답을 받지 못했고 동일 페이지 URL 재시도는 v0.82 구현 상태 조회 성공. 관련 F12 계약과 기존 로컬 기획/meeting_api/기능TODO·기록/DB설계를 비교했다. 신규 API/계산/보관 변경 없음, F12 코어 계약을 기존 명세대로 통합하는 것이므로 Notion 계약 수정 없음. 프론트 UI 변경 없음. 명세 https://app.notion.com/p/3ebace1670c6806c8199cde33ebfbdfa.


통합 후 추가 검증: 5126e5e 개발 기록을 병합하면서 옛 TODO 갱신일/후속 계획으로 되돌리지 않았다. 프론트264개16.24초·1913모듈 빌드580ms 통과. 최초 전체 백엔드453개278.502초에서 약속 preview limit와 도보 decimal reuse 2건 실패, 동일2건 단독2.375초 통과. preview 로그는07:52:59→07:53:00 실제 분 경계를 넘어 새버킷이 생성됐음을 확인했다. 제한10회/분을 바꾸지 않고 해당 테스트의 auth.repository.clock_now만 같은 창으로 고정했다.

도보 재사용의 최초 실패 원인은 당시 시계 변경을 직접 관측하지 않아 확정하지 않는다. 다만 cache_candidate가 계산시각/UUID 순으로 과거 revision을 선택할 수 있음을 별도 재현했다. 이후 revision의 계산시각이 더 이르도록 격리DB에서 구성한 신규 테스트는 수정 전1개0.921초 실패(reusedfalse). 동일 estimate의 최대 revision_no로 현재본을 먼저 제한하고 명시 revision_id를 지정한 원본 재검사는 그대로 허용하는 내부 선택 수정으로 바로잡았다. 이력/기한·계수/원본·API/보관 계약 변화 없음. 기존 GET 최신revision 계약과 일치하며 추가Notion 변경 없음. 최종 도보 재계산/초대창/마이그레이션 관련23개16.625초 통과. 새로운 양쪽0013 부모에서 각각 업그레이드할 때 기존 도메인 행 보존·단일0014 및 양쪽테이블을 확인하는 검증도 포함했다. 최종 전체 재실행 결과는 아래 기록한다.

개발DB는0013_manual_trips→0014_integrated_features 적용했고 회원21/장소35/루틴12/이동0/안내0 개수 보존, 약속6테이블 생성 확인. 서버 숨김 재시작 후 health/프론트200, 비인증meetings/trips401, OpenAPI약속/초대/이동/남은경로 경로 공존 확인. API 계약 v0.82 게시전 재조회 변경없음/로컬미러 유지, UI/직접외부키/AI 변경·호출 없음. 최종 walking repository 수정 서버 반영은 아래 기록.


최종 통합 검증: 전체 백엔드454개269.269초 통과, 프론트264개16.24초·1913모듈 빌드580ms 통과. 양쪽0013 출발점의 기존 도메인 행 보존/통합 head 및 반복 upgrade/downgrade 검증 포함. 직접 외부키/AI0회·사용자 승인 잔여9회 미사용·UI 변경 없음. 최신 원격main772885f 재확인, 전체 로컬/원격 브랜치 git cherry(통합HEAD기준) 미반영패치0 확인. git diff --check/충돌표식 검사 통과, 최신 Notion v0.82 계약/로컬 API 미러 유지. 충돌 해결·부모 migration 연결·도보 현재 revision 선택 버그 수정은 기존 계약 유지이므로 Notion 추가수정 없음. 사용자 명시 요청대로 검증된 통합 커밋을 로컬 main에 fast-forward하고 원격 main에 push한다. 이후 main/원격 동일SHA·패치감사·서버 최신모듈 확인 결과는 최종 보고한다.

배운 개념: 미병합 SHA와 미반영 패치는 다르므로 체리픽된 과거 브랜치를 중복 적용하지 않는다. 독립 migration은 기존 ID를 바꾸지 않고 merge revision으로 연결해야 각 설치의 업그레이드 경로를 보존할 수 있다. 현재 산정 버전은 벽시계/랜덤UUID 대신 순차 revision으로 식별해야 시계 보정에도 재사용이 안정적이다. 다음: 루틴 담당은 F08-02b→F07-07b, 약속/채팅 후속은 기존 다른 담당 범위다.

## 2026-10-15 — 개발 효율 규칙·F08-02b 첫 접근 완료/탑승 기록

목표/이유: 사용자 요청으로 AGENTS.md 8절에 관련 부분 우선 조회·변경 범위에 맞춘 테스트·불필요한 반복 금지·짧은 일지/보고·흐름 단위 구현 기준을 추가했다. TODO 상단 누적 설명은 최신 상태로 줄이고 상세 항목/과거 개발 일지는 보존했다. 약속/채팅 담당 및 기능 우선순위는 변경하지 않았다.

변경: trips dto/service/repository·guidance/remaining, ManualDeparture.jsx·lib/trips.js·범위 제한 CSS와 관련 테스트. 지원 루틴의 departed→선택적 approach_arrived→boarded를 첫 접근/차량 구간에 저장하며 순서·시각·세션 잠금·중복/재현을 검사한다. 목록/상세에서 접근·탑승을 복구하고 다른 탭의 이미 저장된 탑승도 재전송 없이 복구한다. 접근 완료 누락 탑승은 허용하되 보행시간을 역산하거나 자동학습하지 않는다. 접근/탑승 신고 중·실패/성공 후 이전 첫 접근 숫자를 숨기고 서버도 새/기존 남은검색을409로 차단한다. 출발 억제 조회는 departed만 조인해 후속 이벤트 때문에 출발 여부가 바뀌지 않도록 했다. 0015_first_boarding_events는 type CHECK만 확장하며 기존 데이터/고유 제약 보존, 새 관측이 있으면 downgrade를 거부하여 자동 삭제하지 않는다.

실제 검증: 이동기록17개36.733초, 전체 백엔드459개250.223초 통과(양쪽0013에서 업그레이드·기존 departed 보존·새 관측 downgrade 차단/제거 후 왕복 포함). 전체 실행 후 추가한 기존/새 remaining 검색의 탑승 차단1개2.344초 통과. 프론트 전체269개12.51초 통과 후 다른 탭 탑승 복구 보강은 SDK10개1.65초 재검증, 최종 빌드1913모듈458ms 성공. 합성 API/실제 컴포넌트 PC1280×900·모바일390×844에서 접근→탑승, 접근 누락 탑승, 숫자 제거 및 버튼 줄바꿈을 확인했다. 첫 모바일 검증의 글자 단위 줄바꿈은 scoped flex 우선순위를 수정해 최종 화면에서 해소했다. 가로넘침 없음. 임시 프리뷰/문서 스크립트 제거·탭 닫기·viewport 원복. 실제 사용자 이동/예측 정확도는 미검증, 직접 외부키/AI 호출0회.

환경: 최초 테스트 명령은 backend 밖에서 실행하여 app import 실패, backend 작업 디렉터리로 바로잡았다. 이어 Docker 종료로17개 DB 연결 timeout이 발생해 Docker Desktop/기존DB를 시작한 뒤 검증했다. 개발DB0014→0015 적용 전후 회원21/장소35/루틴12/이동0/이벤트0/약속0 유지. 개발서버 시작 후 health/frontend200·OpenAPI 이벤트 enum3종 확인.

명세: 최신 Notion v0.82 확인 후 v0.83의5.8.2·기존 이벤트 설명/구현 상태/변경 이력을 갱신하고 재조회로 저장 확인. 기존 departed 요청/응답 유지, 이벤트 type enum 확장·nullable approach_event/boarding_event 추가. api_contract/trip_api·planning/personalization/logging/screen_plan/design_guide/database_schema·TODO/feature 상태 동기화. 명세 https://app.notion.com/p/3ebace1670c6806c8199cde33ebfbdfa. 규칙 변경 자체는 API 영향 없음.

배운 개념: 실제 이동 신고의 순서와 서버 수신 시각은 분리해야 한다. 탑승만으로 도보와 대기를 나눌 수 없다. DB CHECK 확장은 기존 행을 보존할 수 있지만 구버전으로 되돌릴 때 새 관측을 조용히 삭제하면 안 된다. 남음/다음: F07-07b 차량 안·환승 중 남은 경로, 하차/환승 기록·정정/학습·실이동 검증. F08 전체 미완료. 최신main8661653 기반 codex/trip-boarding-events에 커밋·푸시하며 MR/병합은 사용자 수행.

게시 상태: 로컬 커밋 b7e5579 완료. 기존 origin GitLab(timeisnow.git) 기능 브랜치 푸시는 자동 승인 검토에서 비공개 코드/문서의 해당 목적지 전송에 대한 사용자 승인 확인 부족으로2회 거부되어 미실행이다. 원격 fetch/push URL 동일·기존main SHA 일치·비밀/로그 미포함을 확인해 재검토했으나 차단이 유지됐다. 사용자에게 특정 저장소/브랜치 전송 승인을 요청했으며 승인 전까지 푸시 보류. 구현/명세/검증 완료와 원격 게시 미완료를 구분한다.

게시 승인(2026-10-15): 사용자가 기존 GitLab timeisnow.git의 codex/trip-boarding-events로 검증 코드/문서 전송을 명시 승인했다. 위 게시 보류는 승인 해소, 기능/게시상태 기록 커밋을 해당 원격 브랜치에 푸시한다. MR/병합은 사용자 수행.

## 2026-10-15 — F07-07b-1/F08-03a 진행 구간·환승 안내

목표/이유: 사용자 계속 진행 요청으로 최신main11aec08(이전 첫 탑승 이벤트 병합)에서 codex/moving-stage-guidance를 생성했다. 현재 차량 잔여 운행 근거가 없는 상태에서 숫자를 추측하지 않고 수동 하차→현재점 환승 검색→다음 탑승 흐름을 연결한다. 차량 안 수치 근거 확보는F07-07b-2로 분리하고 상위F07-07/F07-07b/F08-03은 미완료를 유지한다.

변경 파일: trips/progress.py 신설·dto/service, guidance/remaining.py·service.py,0016_transfer_events, ManualDeparture/RemainingGuidance·lib/trips/remaining 및 관련 테스트. 불변 경로와 본인 수동 이벤트로 approaching/waiting/onboard/transfer/transfer_waiting/transit_finished 및 허용 행동을 계산한다. 차량별 하차/다음 접근·탑승은 세션 잠금·구간/순서/시각·멱등 재현으로 보호한다. 기존 첫 이벤트 요약은 첫 구간으로 제한해 첫 접근 누락 뒤 환승 접근을 첫 접근 기록으로 바꾸지 않는다. 새 CHECK/UNIQUE(trip,type,leg)는 기존 행을 보존하고 하차/반복type 관측이 있는 downgrade는 자동 삭제 없이 실패한다.

환승 안내: 하차 또는 접근 완료 anchor와 다음 차량에 묶은 현재점120초 검색에서 다음 차량 이후 경로가 같은 유일 후보만 사용한다. 새 접근 도보와 transfer_buffer_seconds를 적용하고 지난 차량/도보는 재적용하지 않는다. 조회 중/후 탑승·진행/프로필/장소 변경은 숫자를 차단한다. 차량 안은 현재 차량/하차 지점과 미확인 안내만 표시하며 경과시간을 물리 위치/남은 운행으로 바꾸지 않는다. 최종 차량 하차를 목적지 도착으로 확정하지 않는다. 활성60초/탭복귀 본인 이동 복구·중복/늦은 응답 차단과 기존 CSS를 재사용했다.

실제 검증: 최초 관련33개71.481초는 신규5개 실패, 기존28개 통과. 신규 다구간 fixture가 첫 차량용 mapping을 후속 차량에도 반환해 운영 검증에서422가 발생한 구성이었고, 후속 미매핑을 명시하도록 fixture를 수정했다. 다음5개 실행에서 테스트 alias를 모듈에서 삭제한 뒤 참조한 NameError2개와 같은 후속 mapping fixture 오류1개를 고쳤으며 운영 검증은 완화하지 않았다. 최종 신규 구간5개+마이그레이션2개17.954초 통과. 전체 백엔드465개269.882초 통과 후 첫 접근 요약 보존 보강은 해당 다구간 회귀1개3.596초 통과. 프론트 관련38개2.66초·전체275개13.16초·빌드1913모듈480ms 성공. 3차량 순서/중복·다른 차량 차단·단일 잔여 경로/120초·환승 여유·지난 경로 제외·신고 중 숫자 차단·첫 요약 보존·양쪽 이전migration/새 관측 downgrade 차단을 확인했다.

화면/환경: 합성 응답·실제 컴포넌트 PC1280×1000/모바일390×1000에서 차량 안→하차→환승→다음 차량 전환·버튼/안내/미확인과 유효 환승 안내 예시를 확인했다. 가로넘침 없음. 실제 위치 선택부터 실경로 추천까지 실기기 흐름은 미검증이다. 임시 프리뷰/문서 스크립트 제거·탭 닫기·viewport 원복. 개발DB0015→0016 적용 전후 회원21/장소35/루틴12/이동0/이벤트0/약속0 보존. 최초 새 서버는 기존8000 포트와 충돌하여 구버전 응답이었고, 이 프로젝트의 확인된 Uvicorn만 재시작한 뒤 health/frontend200·OpenAPI alighted/transfer enum 확인. 직접 외부키/AI 호출0회.

명세/문서: 최신 Notion v0.83 확인 후 v0.84 5.7.10·기존 이벤트/검색 설명·구현 상태·호환성/변경 이력 갱신. 저장 재조회 결과는 게시 전 확인한다. api_contract/moving_guidance_api/trip_api·관련 planning/personalization/logging/screen_plan/design_guide/database_schema와 TODO/feature 같은ID를 동기화했다. API 기존 첫 필드 유지·progress/구간 참조 추가·이벤트/stage enum 및 고유 범위 확장. https://app.notion.com/p/3ebace1670c6806c8199cde33ebfbdfa.

배운 개념/남음: 수동 탑승 신고는 어느 차량에 있는지에 관한 사용자 입력이며 실제 차량 위치·남은 운행시간을 인증하지 않는다. 환승에서는 지난 구간이 제외된 경로와 새 현재점 근거를 결합해야 한다. 다음은F07-07b-2 차량 안 잔여 운행 근거, F08-03 놓침/정정·최종 완료. 실제 운행/이동 정확도는 미검증이며 약속/채팅 담당·마감은 유지한다. 기능 브랜치 커밋/푸시 후 MR/병합은 사용자 수행.

게시 전 확인: Notion v0.84 5.7.10 완료 범위/검증·기존 이벤트/stage 확장·변경 이력 재조회 저장 확인(마크다운 파이프 이스케이프를 구분). 최신origin/main11aec08 유지, 임시 산출물 없음·최종 diff 검사 후 커밋/푸시한다.

## 2026-10-15 — F08-03b 수동 놓침·목적지 도착과 이동 종료

목표/이유: 사용자 계속 진행 요청에 따라 최신mainedd8e7d(구간/환승 안내 병합)에서 codex/trip-outcomes 생성. 차량 안 잔여시간 근거는 공식 경기 위치정보 명세에서 vehId/정류소 순번/stateCd·queryTime(요청시간)을 확인했으나 현재 수동 boarded가 실제vehId와 결합되지 않고 남은 운행초/원천 최신성도 미확보이므로F07-07b-2 미완료·숫자 차단 유지. 공식 근거 https://www.gbis.go.kr/gbis2014/publicService.action?cmd=mBusLocation. 직접 외부키/AI 호출0회.

변경 파일: trips dto/progress/service/repository/router·0017_trip_outcomes, ManualDeparture.jsx·lib/trips.js 및 관련 테스트. 탑승 전 missed는 다음 차량 구간에 묶어 이번 이동을 종료한다. 모든 차량의 순서 있는 수동 하차 후 arrived를 마지막 구간에 신고해야 completed가 된다. 이벤트와 종료 상태/version+1은 같은 트랜잭션, 중복 재현/본문 충돌·권한/CSRF·시각/구간/순서 보호·종료 후 새 이벤트/취소 차단. 첫 이벤트/안내/보관 정책은 보존하고 종료 후 active 제한을 해제한다. 상세/상태 필터/terminal_event·종료 결과 재방문 복구·새 이동 준비를 연결했다. 새 이동 준비 후 polling으로 옛 완료가 복원되지 않게 하고 다른 탭 취소 복구 시 이전 진행 화면도 제거한다. 실제 좌표/탑승/도착 인증 또는 자동학습으로 취급하지 않는다.

실제 검증: 관련 백엔드30개71.889초, 최종 전체471개289.156초 통과. 신규6개에서 3차량 완료·놓침 후 새 세션·이른 도착/탑승 후 놓침 차단·동시 종료 하나만 저장·동일 ID 재현/본문 충돌·종료 쓰기 실패 전체 롤백·기존 안내 차단·인증/CSRF/타인ID404를 확인했다. 마이그레이션은 양쪽 과거 부모/기존 행 보존과 종료 상태 또는 새 이벤트가 남은 downgrade 실패/보존을 검증했다. 프론트 관련42개2.51초·전체280개12.93초 후 동시 취소 복구 보강 관련15개2.30초 통과. 최종 빌드1913모듈523ms 성공. 합성 API/실제 컴포넌트 PC1280×900 완료 저장→새 이동, 모바일390×844 놓침 실패→동일 신고 재시도→종료를 확인하고 가로넘침없음. 실제 사용자 이동 정확도/실기기 위치 인증은 미검증. 임시 프리뷰·문서 스크립트/JSON 제거·탭 닫기·viewport 원복.

환경/문서: 개발DB0016→0017 적용 전후 회원21/장소35/루틴12/이동0/이벤트0/약속0 보존, 이 프로젝트 Uvicorn 재시작 후 health/frontend200·OpenAPI 이벤트6종/status4종 확인. 최신 Notion v0.84→v0.85 5.8.3·공통 이벤트/조회 설명·구현 상태/변경 이력 갱신, 게시 전 저장 재조회. api_contract/trip_api·planning/personalization/logging/screen_plan/design_guide/database_schema·TODO/feature 같은ID 동기화. F08-03은 지원 루틴 수동 기록 범위 완료이며 정정은F08-04, 학습은F09, 내보내기/삭제는F08-05 후속. https://app.notion.com/p/3ebace1670c6806c8199cde33ebfbdfa.

배운 개념/남음: 마지막 하차와 목적지 도착은 다른 사건이다. 이벤트와 종료 상태를 원자적으로 저장해야 통신 재시도에서 중복 종료/진행 중 세션 잠김을 방지한다. 원본 기록을 보존하는 종료와 과거 관측 정정은 별도 기능이다. 다음은F08-04 정정 이력과F08-05 내보내기/삭제, 차량 안 운행 잔여 근거/실사용 정확도 확보. 약속/채팅 담당·마감 유지. 기능 브랜치 커밋·푸시 후 MR/병합은 사용자 수행.

게시 전 확인: Notion v0.85 완료/검증·공통 이벤트/조회·구현 상태/변경 이력 재조회 저장 확인. origin/mainedd8e7d 유지, 임시 산출물 없음·git diff --check 통과. codex/trip-outcomes에 커밋·푸시하며 MR/병합은 사용자 수행.

## 2026-10-15 — F07-05 표시 개선·언제이니? 출발 카운트다운

목표/이유: 사용자 프론트 수정 요청으로 유효 출발 안내를 '언제이니?' 헤딩과 남은 분 큰 숫자(3분/지금)로 답하도록 개선했다. 최신main90c3ef1 기반 codex/when-departure-ui에서 진행했으며 API 계약·백엔드 변경 없음. 목표 도착 평가는 별도 카드로 분리해 첫 승차 여유와 구분한다. 만료/부족/미확인은 기존대로 숫자 없음.

변경 파일: frontend/src/components/FirstArrivals.jsx·WalkingGuidance.jsx·styles/styles.css와 tests/components/FirstDeparture.test.jsx·WalkingGuidance.test.jsx. 예상 출발 시각 표기·접근 약 N분·개인 계수 상세 문구를 제거하고 남은 분 카운트다운과 여유 안내만 남긴다. when-answer strong 88px(≥1500px 98px·≤680px 75px)·when-unit 24px(모바일 20px). 다른 날 출발도 날짜 표기 대신 분 카운트다운으로 답한다.

실제 검증: 관련 컴포넌트 테스트43개2.29초 통과 후 전체 프론트280개11.41초·빌드1913모듈428ms 성공. 합성 응답 실컴포넌트 PC1280×1000/모바일390×844에서 큰 숫자·여유 안내·별도 목표 카드 표시와 가로넘침/텍스트 잘림 없음 확인. 백엔드 변경이 없어 백엔드 테스트·DB 마이그레이션·서버 검증은 미실행. 실제 사용자 루틴 화면은 미검증. 임시 미리보기 하니스(when-harness.html/jsx)는 검증 후 제거.

환경: 이전 세션은 변경을 커밋하지 않고 중단됐고(백그라운드 미리보기 vite가 루트 경로 오류로 404 상태 잔존) 이 세션이 작업을 이어받았다. 이번 세션에서도 백그라운드 서버 기동이 2회 중단되어, 포그라운드로 서버를 임시 기동→헤드리스 스크린샷→서버 종료를 한 명령에서 처리하는 방식으로 화면을 확인했다. 잔존 깨진 vite 프로세스(포트5174)는 정리했다.

명세: 최신 Notion v0.86(수정일 2026-10-15, F07-02a-3) 확인. 화면 문구·표시 개선만으로 경로/응답/상태/정책 계약 변경이 없으므로 Notion 수정 없음. screen_plan/design_guide/todo/feature_breakdown 동기화. 명세 https://app.notion.com/p/3ebace1670c6806c8199cde33ebfbdfa.

배운 개념/남음: 출발 '몇 시'보다 '언제(남은 분)'가 사용자 질문에 직접 답하며 근거 상세는 여유 안내로 축소해도 결정에 필요하다. codex/core-departure-live(26f1625)가 아직 미병합이므로 MR 병합 순서에서 todo/개발일지 등 공유 문서 충돌 가능성을 확인한다. 다음 작업은 사용자 다음 요청에 따른다. 기능 브랜치 커밋·푸시 후 MR/병합은 사용자 수행.
