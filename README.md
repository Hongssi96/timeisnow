# 지금이니?

진행 현황과 남은 작업은 [TODO 체크리스트](./todo.md)를 확인하세요.

F03-01(2026-10-07): ‘내 설정 → 내 장소’에서 로그인 후 주소/장소 검색, 집·회사 이름과 위치 저장 및 본인 목록 조회를 제공합니다. 실행 전에0003_saved_places까지 DB 마이그레이션을 적용하세요. 상세 [장소 API](./place_api.md). 지도/출입구 수정·현재 위치·실제 경로 계산은 후속입니다.

집에서 기다리다가, 대중교통을 놓치지 않을 만큼 여유 있게 출발하도록 돕는 개인화 통근·등교 서비스.

- 프론트엔드: React
- 백엔드: Python FastAPI
- 프로젝트 루트: `C:/projects/timeisnow`. 기획 문서도 이 폴더에서 관리합니다.
- 이 README는 기획 소개이며 기능 구현 완료를 의미하지 않습니다.
- 작성일: 2026-10-01

## 시작한 이유

동생이나 어머니가 집을 나설 때 버스를 밖에서 오래 기다리는 경험을 줄이고 싶었습니다. 출발 시간을 맞추려고 휴대전화로 버스 도착 정보를 계속 확인하지만, 가끔은 늦게 출발해 버스를 놓치기도 했습니다.

‘지금이니?’는 언제 집에서 나가면 되는지를 바로 알려주는 것을 목표로 합니다. 통근·등교처럼 반복되는 이동을 루틴으로 저장하면 같은 장소와 경로의 도보 시간을 다시 계산할 필요가 줄어듭니다. 저장된 경로와 도보 시간은 재사용하고, 달라지는 버스·지하철 도착 정보는 새로 확인합니다.

## 핵심 기능

- 회원가입과 사용자별 장소·루틴 저장.
- 집·회사·학교 또는 현재 위치에서 출발.
- 버스·지하철과 환승 경로 확인.
- 실제 보행 경로 데이터를 근거로 AI가 도보 시간을 산정하고 저장.
- 초기 첫 탑승 여유 5분을 반영한 출발 안내.
- 출발·정류장 또는 승강장 도착·탑승 기록을 분리해 개인 이동 시간을 보정.
- AI 산정 결과와 실제 이동을 비교하는 품질 이력 및 실행 로그.

안내 예시:

> **3분 뒤 출발하세요.**  
> 그때 출발하면 정류장 도착 후 **약 5분의 여유가 있어요.**  
> 예상 도보 5분 · 버스 약 13분 후 도착

화면을 닫아도 받는 백그라운드 출발 알림의 첫 출시 포함 여부는 아직 미정입니다.

## 유스 케이스와 이용 흐름

아래는 Mermaid flowchart로 표현한 유스 케이스·이용 흐름입니다. 엄격한 UML 유스 케이스 표기보다는 사용자의 행동과 기능 연결을 함께 보여줍니다.

사용자는 왼쪽, 기능은 그룹 안에서 세로로 배치하도록 구성했습니다. 그룹 안의 실선 화살표는 이용 흐름, 그룹 사이 점선은 기능 연계, 사용자와 그룹의 실선은 이용 관계를 뜻합니다. 외부 연동의 점선은 정보 제공 관계이며 모든 화면에서 AI를 호출한다는 뜻은 아닙니다.

```mermaid
%%{init: {"theme":"base","themeVariables":{"fontFamily":"Arial","fontSize":"16px","primaryColor":"#EFF6FF","primaryTextColor":"#1E293B","primaryBorderColor":"#60A5FA","lineColor":"#64748B","clusterBkg":"#F8FAFC","clusterBorder":"#CBD5E1"},"flowchart":{"curve":"linear","nodeSpacing":25,"rankSpacing":45}}}%%

flowchart LR
    USER["사용자<br/>어머니 · 동생<br/>통근자 · 학생"]

    subgraph APP["지금이니?"]
        direction LR

        subgraph SETUP["① 처음 설정"]
            direction TB
            A(["회원가입 · 로그인"])
            B(["집 · 회사 · 학교 등록"])
            C(["통근 · 등교 루틴 저장"])
            D(["도보 시간 자동 산정 · 저장"])

            A --> B --> C --> D
        end

        subgraph DAILY["② 매일 이용"]
            direction TB
            E(["오늘의 루틴 확인"])
            F(["권장 출발 시각 확인"])
            G(["집에서 기다리기"])
            H(["출발하기<br/>예상 여유 시간 확인"])
            I(["정류장 · 승강장 도착 확인"])
            J(["실제 탑승 확인"])

            E --> F --> G --> H --> I --> J
        end

        subgraph CHANGE["③ 상황 변경"]
            direction TB
            K(["현재 위치에서 출발"])
            L(["늦게 출발하거나<br/>버스를 놓친 상황 확인"])
            M(["다음 차량 · 대체 경로 확인"])
            N(["새 출발 시각 · 여유 확인"])

            K --> M
            L --> M
            M --> N
        end

        subgraph LEARN["④ 반복 사용과 개인화"]
            direction TB
            O(["실제 이동 기록 확인"])
            P(["개인 이동 시간 보정"])
            Q(["저장된 경로 · 도보 시간<br/>다음 이용에 재사용"])

            O --> P --> Q
        end
    end

    subgraph SUPPORT["외부 연동"]
        direction TB
        MAP["지도 · 교통 정보<br/>경로 · 실시간 도착 정보"]
        AI["AI<br/>근거 기반 도보 시간 산정"]
        MAP ~~~ AI
    end

    USER --- SETUP
    USER --- DAILY
    USER --- CHANGE

    SETUP -.-> DAILY
    DAILY -.-> LEARN

    SUPPORT -.->|"경로 · 도보 근거"| SETUP
    SUPPORT -.->|"최신 교통 정보"| DAILY
    SUPPORT -.->|"대체 경로 정보"| CHANGE

    classDef actor fill:#DBEAFE,stroke:#2563EB,stroke-width:2px,color:#1E3A8A;
    classDef action fill:#FFFFFF,stroke:#94A3B8,stroke-width:1px,color:#1E293B;
    classDef emphasis fill:#DCFCE7,stroke:#16A34A,stroke-width:2px,color:#14532D;
    classDef external fill:#F1F5F9,stroke:#64748B,color:#334155;

    class USER actor;
    class A,B,C,D,E,G,I,J,K,L,M,N,O,P,Q action;
    class F,H emphasis;
    class MAP,AI external;

    style APP fill:#F8FAFC,stroke:#94A3B8,stroke-width:2px
    style SETUP fill:#EFF6FF,stroke:#93C5FD
    style DAILY fill:#F0FDF4,stroke:#86EFAC
    style CHANGE fill:#FFF7ED,stroke:#FDBA74
    style LEARN fill:#FAF5FF,stroke:#D8B4FE
    style SUPPORT fill:#FFFFFF,stroke:#CBD5E1
```

### draw.io에서 사용하기

1. 위 코드 블록 안의 내용만 복사합니다. 코드 블록을 감싸는 백틱은 제외합니다.
2. draw.io의 Mermaid 삽입 창에 붙여넣습니다.
3. Image 선택 옵션이 있다면 SVG 이미지로 삽입할 수 있습니다.

렌더러와 버전에 따라 간격·글꼴·배치는 달라질 수 있습니다. 이 README 추가 작업에서는 draw.io에서 다시 렌더링해 검증하지 않았습니다.

## 프론트엔드 화면 구성 초안

| 화면 | 핵심 역할 |
| --- | --- |
| 홈 | 오늘의 루틴, 출발까지 남은 시간, 예상 여유 |
| 루틴 등록·수정 | 출발·도착 장소, 요일, 목표 시각, 경로 선택 |
| 이동 중 | 탑승·환승 안내, 도착·탑승 확인 |
| 내 장소·설정 | 장소 관리, 여유 설정, 개인화 상태, 계정 |

회원가입·로그인과 첫 장소 등록은 초기 이용 흐름으로 별도 제공합니다.

## 문서 안내

| 문서 | 내용 |
| --- | --- |
| [기획서](./planning.md) | 요구사항, MVP 범위, 시스템 구성 |
| [기능별 개발 작업](./feature_breakdown.md) | 작업 분리, 선행 조건, 완료 기준 |
| [개인화 알고리즘](./personalization.md) | 실제 접근 시간 관측과 개인 보정 |
| [AI 프롬프트](./ai_prompts.md) | 입력·출력 계약과 AI 검증 기준 |
| [로깅 계획](./logging.md) | 요청 추적, 오류, 품질 이력 |
| [개발 일지](./development_log.md) | 변경 이유, 검증 결과, 배운 내용 |
| [Notion API 명세서](https://app.notion.com/p/3ebace1670c6806c8199cde33ebfbdfa) | API 계약의 기준 문서 |

## 개발 규칙

이 프로젝트의 [AGENTS.md](./AGENTS.md)를 따릅니다. 기획 문서와 README는 같은 프로젝트 폴더에서 관리합니다.

- 개발 전 최신 Notion API 명세와 관련 로컬 문서를 확인합니다.
- 기획·API 계약이 바뀌면 Notion과 관련 문서를 함께 갱신합니다.
- 작은 기능 단위로 구현하고 실행 로그와 실제 결과를 확인합니다.
- 실행하지 않은 테스트나 미구현 기능을 완료로 기록하지 않습니다.



## React 화면 미리보기

화면 구성은 [screen_plan.md](./screen_plan.md)에 정리했습니다. [frontend](./frontend)는 예시 데이터로 홈·루틴·이동 중·기록·설정을 확인하는 React 프로토타입입니다. 회원가입·로그인·회원 조회·로그아웃은 실제 API를 연결했습니다. 교통·AI 및 계정별 장소/루틴 저장은 아직 연결되지 않았습니다.

```powershell
cd C:\projects\timeisnow\frontend
npm install
npm run dev
```

출력된 로컬 주소를 브라우저에서 여세요. 테스트는 `npm test`, 빌드는 `npm run build`입니다. 루틴과 기록은 미리보기 메모리에만 저장되어 새로고침하면 초기화됩니다.

## 확장 기획: 약속과 출발 상태 공유

일회성 약속, 중간 만남 추천, 약속별 채팅과 출발 상태·예상 도착 공유를 기획에 추가했습니다. 반복 확인 연락과 기다림의 불확실성을 줄여 약속에 대한 신뢰 형성을 돕는 것이 목적입니다.

초기 출발 표시는 본인 입력이며 실제 이동의 자동 검증을 뜻하지 않습니다. 현재는 미구현 확장 기획입니다. [상세 기획](./meeting_plan.md)을 참고하세요.


## 백엔드 개발 환경

F00-01~04로 백엔드 기반·GET health·공통 오류/request_id·React 연결과 JSON 요청 완료/예상 밖 오류 로그를 구현했습니다. [백엔드 실행·로그 확인 안내](./backend/README.md)를 참고하세요. 공통 클라이언트는 요청 취소/10초 시간초과·실패/수동 재시도를 처리합니다. 로그는 원문 URL/본문/키/예외 메시지 없이 경로 템플릿·요청 ID로 대조하며 업무 API는 아직 미구현입니다.
## 개발 DB

PostgreSQL을 Docker 컨테이너로 실행합니다. [DB 실행·접속·종료 안내](./database.md)를 참고하세요. DB 연결과 마이그레이션 기반은 검증했으며 업무 테이블은 미생성입니다. [마이그레이션 안내](./migrations.md)를 참고하세요.

## 데이터 모델

[테이블·연관관계 설계](./database_schema.md)에서 통근 MVP와 약속 확장의 ERD·주요 컬럼·생성 순서를 확인할 수 있습니다. 실제 테이블 생성은 후속 작업입니다.

## 친구 약속·채팅 API

[상세 API 초안](./meeting_api.md)에 REST 요청·응답, 권한, 오류와 WebSocket 인증·알림·복구 규격을 정리했습니다. 제안 정책 검토와 실제 구현은 남아 있습니다.

AI 모델은 GPT-5.6 Luna (`gpt-5.6-luna`)로 확정했으며 사용자 승인된 커스텀 서버로 최소 연결을 확인했습니다. 예산·운영 데이터 처리 조건·서비스 품질 검증은 남아 있습니다. 연결 확인은 `backend/.venv/Scripts/python.exe backend/check_ai.py`로 실행하며 루트 `.env`의 키·baseURL·모델을 사용합니다.

## 디자인 기준

경기 공개 사례 ID 매핑 진단은 `backend/.venv/Scripts/python.exe backend/check_gyeonggi_mapping.py`입니다. 노선 후보를 이름·정류장 순서·양끝 좌표로 대조한 단일 사례 도착 ID 일치까지 확인했으며 전체/운영 매핑·최신성은 미완료입니다. 상세는 public_arrivals_plan.md를 따릅니다.

경기 기반정보 권한 진단 도구는 `backend/check_public_baseinfo.py`입니다. 노선 정차순서는 조회되며 정류소 검색/경유노선은 403으로 추가 활용승인 확인이 필요합니다. 만료 진단 헬퍼는 요청시각을 생성시각으로 대체하지 않으며 전체 매핑과 운영 정책은 미완료입니다.

공공 실시간 도착 API 신청·키 설정·검증 순서는 [public_arrivals_plan.md](./public_arrivals_plan.md)를 따릅니다. 개인 버스/지하철 키 발급과 카카오 ID 매핑은 미완료이며 서울역 공개 sample 응답 구조만 확인했습니다. 지하철 내부 이동 결과는 GPS 판정 대신 사용자 수동 탑승 확인으로 검증하는 정책입니다.

카카오 경로 최소 검증은 `backend/.venv/Scripts/python.exe backend/check_kakao_routes.py`로 실행합니다. 공개 역 주변 도보/대중교통을 각 1회 호출해 상태·시간·거리·좌표 형식과 ID 필드 존재 여부만 요약합니다. 원본 경로 저장/AI 전달 없음. 실제 출입구·역 내부 이동·실시간 도착/공공 매핑은 별도 검증 대상입니다.

카카오 REST 키의 장소 검색 연결 확인은 `backend/.venv/Scripts/python.exe backend/check_kakao.py`로 실행합니다. 루트 `.env`의 `KAKAO_REST_API_KEY`를 사용하며 공개 장소 검색 1회 결과의 개수/형식만 출력합니다. 지도 SDK와 도보/대중교통 경로 검증은 별도입니다.

프론트 작업 전 [디자인 가이드](./design_guide.md)를 읽어 현재 색상·글꼴·컴포넌트·반응형 톤을 유지합니다. 준수 규칙은 AGENTS.md 7절에 있습니다.

이메일·비밀번호 인증 결정과 API 설계: [auth_api.md](./auth_api.md). 기본 가입·로그인·회원 조회·로그아웃은 구현했고, 이메일 소유 확인·복구는 사용자 요청으로 후순위입니다.

지원 지역 서울·경기도 및 카카오맵 사용은 확정입니다. 공급자 실제 미검증과 조건 추가 확인 생략의 사용자 결정은 [공급자 검증 계획](./provider_plan.md)을 따릅니다. D03~D05 결정/F00-03~04 기반 작업은 완료됐고 현재/다음 구현은 todo.md를 따릅니다.


자연어 일정 입력 기획: [natural_language_schedule.md](./natural_language_schedule.md). 사용자 확인 후 저장하며 기능은 미구현입니다.
