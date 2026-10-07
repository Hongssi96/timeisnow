# 프론트엔드

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

이번 구조 정리는 main의 F03-03까지를 기준으로 합니다. 미병합 codex/current-origin(F03-04)의 OriginSelector는 src/components, currentOrigin은 src/lib, 테스트는 tests의 대응 폴더로 옮기고 App/지도 및 테스트 import도 위 경로에 맞춰 병합해야 합니다. 해당 기능은 기존 브랜치에 보존되어 있습니다.
