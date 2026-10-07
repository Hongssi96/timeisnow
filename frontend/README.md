# 프론트엔드

F04-03: 홈 ‘경로 후보 비교’ → 출발/도착 직접 선택 → 경로 후보 조회 → 정렬/구간 자세히. JourneyComparison/JourneyCandidates는 src/components, 모델 검증/조회 중지는 src/lib/journeys.js, 대응 테스트는 tests/components·lib·app, 합성 공통 모델 fixture는 tests/fixtures. 서버/API가 실행 중이어야 하며 AI/실시간/출발 안내·루틴 저장은 후속이다. 프론트97개 테스트·빌드, 실제15후보/PC·모바일 확인. 상세 [journey_api.md](../journey_api.md).

실행 코드와 테스트를 별도 디렉터리로 관리합니다.

```text
frontend/
├─ src/                  # 브라우저에서 실행하는 코드
│  ├─ main.jsx           # React 진입점
│  ├─ app/               # 앱 화면과 화면 전환 상태
│  ├─ components/        # 계정·장소·지도 UI
│  ├─ lib/               # API 클라이언트·지도 SDK 로더
│  └─ styles/            # 공통 CSS
├─ tests/                # Vitest 테스트 (src 구조에 대응)
│  ├─ setup.js           # DOM 테스트 공통 환경
│  ├─ app/
│  ├─ components/
│  └─ lib/
├─ index.html            # Vite HTML 진입점
├─ vite.config.js        # 개발 서버·빌드·테스트 설정
└─ package.json          # 의존성과 실행 명령
```

`node_modules/`는 설치한 의존성, `dist/`는 빌드 결과입니다. 둘 다 생성 폴더이며 Git에 넣지 않습니다. Vite가 사용하는 HTML·설정·패키지 파일은 frontend 루트에 둡니다.

프로젝트 루트에서 실행합니다.

```powershell
npm --prefix frontend run dev
npm --prefix frontend test
npm --prefix frontend run build
```

새 UI는 src/components, 공유 통신/SDK 코드는 src/lib에 추가하고 테스트는 대응하는 tests 하위 폴더에 둡니다. 테스트 파일명은 `*.test.js` 또는 `*.test.jsx`를 사용합니다. 테스트 import와 vi.mock은 같은 실제 소스 경로를 가리켜야 합니다. 테스트 공통 설정은 tests/setup.js에서 관리합니다.

F03-04와 폴더 정리는 main0402d67에 포함됐습니다. OriginSelector/OriginReview는 src/components, currentOrigin은 src/lib, 관련 테스트는 tests/app·components·lib에 위치합니다. F03-05a 수동 확인은 codex/origin-quality에서 전체79개 테스트와 빌드를 확인했습니다. GPS 수치/자동 일치 판정은 보류하며 사용자 검토 후 main에 병합합니다.
