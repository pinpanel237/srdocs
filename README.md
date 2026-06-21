# 📖 srdocs (md Wiki Generator)

로컬 프로젝트의 파일 구조와 변경 이력을 분석하여 Markdown 형식의 개발 위키 문서(`.md`)를 자동으로 생성해주는 Python 기반 CLI 도구입니다.

로컬 프로젝트의 파일 구조와 리비전 변경 이력을 분석하여 마크다운(Markdown) 포맷의 개발 위키 문서를 자동으로 생성해주는 파이썬(Python) 기반의 CLI 도구입니다.

---

## 🌟 주요 특징 (Key Features)

- **순수 표준 라이브러리 사용 (Zero Dependencies)**: 외부 라이브러리 설치 필요 없이 Python 3만 있으면 즉시 실행 가능합니다.
- **초기 대화형 설정 마법사 및 설정 파일 지원 (Wizard & Configuration)**:
  - 첫 실행 시 대화형 설정 마법사(`run_wizard`)가 실행되어 여러 프로젝트 경로 목록, 문서 저장 폴더, LLM 연동 정보 등을 입력받습니다.
  - 입력값은 홈 디렉토리의 `.srdocs/config.json` 파일에 저장되어 이후 실행의 기본값으로 적용되며, 자동화(CI/CD) 환경에서는 멈추지 않고 생략됩니다.
- **로컬 캐싱 및 증분 분석 (Caching & Token Saving)**: 
  - 버전 태그와 파일 목록의 SHA-256 해시 키를 기준으로 이미 분석된 버전/프로젝트 요약을 로컬 캐시(사용자 홈 디렉토리의 `~/.cache/srdocs/`)에 저장합니다.
  - 다음 실행 시 캐시된 요약을 로드하여 중복 LLM 호출과 토큰 소모를 방지합니다.
- **폴더 분할형 위키 생성 (Vault Mode)**:
  - 출력 경로에 확장자(`.md`) 대신 폴더명을 지정하면 카르파시의 LLM Wiki 설계에 부합하는 `index.md`, `overview.md`, `log.md`, `versions/`, `components/`, `decisions/` 구조의 Obsidian 호환 Vault 디렉토리를 구축합니다.
- **위키 정합성 검사 (Linting)**:
  - `--lint` 옵션으로 위키 내부의 깨진 상대 링크 및 어느 페이지에서도 참조되지 않는 고아 파일(Orphan)을 자동 검출합니다.
- **자연어 질문 답변 및 저장 (Querying & Compounding)**:
  - `--query` 옵션을 통해 프로젝트에 관해 질문하면 소스 코드 컨텍스트를 자동 검색하여 LLM이 분석 답변을 제공하고, 이를 `decisions/<query_slug>.md` 위키 페이지로 자동 누적 저장 및 색인합니다.
- **아키텍처 및 폴더 트리 다이어그램**: 프로젝트 내부 디렉토리 구조를 트리 텍스트 다이어그램으로 시각화합니다 (최대 깊이 조절 가능).
- **변경 이력 및 기여도 통계**: 
  - 각 파일별 수정 빈도 Top 10 추출.
  - 디렉토리(컴포넌트)별 수정 빈도 통계.
  - 작성자별 기여도 및 변경 내역 분포 계산.
- **유연한 링크 형식 (Absolute/Relative file:// links)**: 
  - 로컬 환경 내 개발을 위한 절대 경로 파일 링크 생성(`file://`).
  - Obsidian Vault 등 로컬 위키 연동을 위한 상대 경로 파일 링크 생성.

---

## 🛠️ 운영 모드 (Operating Modes)

이 프로젝트는 위키 문서를 빌드하고 배포할 때 최종 운영 요구사항에 따라 두 가지 작동 모드를 지원하도록 기획되었습니다.

### 1. 수동 모드 (Manual Mode) - [현재 구현 완료]
- **어떻게 동작하나요?**: CLI 명령 또는 초기 대화형 마법사(`--init`)를 통해 특정 폴더 경로 또는 저장소 주소를 수동 지정하여 일회성으로 문서를 빌드합니다.
- **주요 용도**: 개발 및 로컬 테스트 환경, 소형 독립 위키 배포.
- **명령 예시**: `srdocs --repo /path/to/repo --output vault/my-project`

### 2. 자동 모드 (Auto Mode) - [개발 계획 / 로드맵]
- **어떻게 동작하나요?**: 개발자가 코드를 푸시하면 배포 환경이 감지하여 위키를 실시간 갱신합니다.
  - **방안 A (Webhook)**: GitHub/GitLab Webhook 수신 전용 경량 백엔드 API 서버를 컨테이너 내부에 구동하여 Push 이벤트 수신 시 자동으로 `git pull` 및 `run.py` 빌드를 트리거합니다.
  - **방안 B (Polling)**: 백그라운드 크론(Cron) 또는 데몬 프로세스가 주기적으로 커밋 SHA 값을 대조하여 변경 사항이 발생할 때 최신화합니다.

---

## 🗺️ 향후 개발 로드맵 (Roadmap)

더 강력한 지식 저장소(Knowledge Repository)로 도약하기 위해 계획된 확장 기능 로드맵입니다.

### 1. 자동화 모드 및 CI/CD 연동 (Auto Mode & CI/CD)
- **목표**: 개발자가 변경 사항을 원격 저장소에 반영(Push)하면 백그라운드에서 이를 감지하여 변경된 사항을 가져오고 위키 빌드(`run.py`)를 자동으로 수행합니다.
- **상세**: CI/CD 워크플로우 템플릿을 연동하거나 Webhook/Polling 기반 경량 백엔드 API 서버를 구동하여, 코드가 반영될 때 중앙 호스팅 서버나 문서 페이지로 문서가 실시간 자동 갱신되는 환경을 구축합니다.

### 2. 웹 뷰어 내 풀텍스트 검색 (Full-text Search)
- **목표**: 현재의 단순 제목/컴포넌트명 필터링 수준을 넘어, 위키 내 모든 마크다운 문서 본문 내용까지 브라우저단에서 고속으로 검색할 수 있는 경량 전문 검색 엔진(예: `MiniSearch`, `flexsearch`)을 웹 뷰어에 연동합니다.

### 3. 웹 뷰어 양방향 편집 및 피드백 (Write/Edit Support)
- **목표**: Read-Only 상태인 웹 뷰어에서 개발자가 직접 오타나 누락 사항을 실시간으로 수정하거나 메모를 기입할 수 있는 기능입니다.
- **상세**: 웹 뷰어 화면에서 마크다운 및 아키텍처 다이어그램을 직접 편집하고, 이를 로컬 소스 코드의 문서 파일에 직접 반영하여 변경 이력 관리와 연동하여 양방향 지식 관리를 완성할 계획입니다.

---

## 🚀 빠른 시작 (Quick Start)

### 0. 초기 대화형 설정 구성
프로젝트를 처음 구동할 때 아래 명령을 실행하면 분석할 프로젝트 경로 목록, 위키 저장 경로(기본값: `srdocs-vault`), LLM 설정을 입력받아 구성 파일(`.srdocs/config.json`)을 생성합니다.
```bash
srdocs --init
```
이후부터는 매번 CLI 옵션을 길게 적지 않고도 `srdocs`만으로 설정된 기본값에 맞춰 등록된 프로젝트들의 위키가 프로젝트별 폴더로 자동 생성됩니다.

### 1. 단일 마크다운 파일 위키 생성
```bash
srdocs --repo /path/to/your/project-dir --output WIKI.md
```

### 2. 폴더 분할형 위키 Vault 구축 (카르파시 LLM Wiki 스타일)
```bash
# 기본 설정된 srdocs-vault/ 디렉토리 하위에 문서 일괄 빌드
srdocs
```

### 3. 생성된 위키 정합성 린트 검사
```bash
srdocs --repo /path/to/your/project-dir --output wiki_vault --lint
```

### 4. 코드 분석 질의 및 위키 누적 저장
```bash
export GEMINI_API_KEY="your-api-key"
srdocs --repo /path/to/your/project-dir --output wiki_vault --query "하이브리드 검색 구현 방식을 알려줘" --llm gemini
```

### 5. Obsidian 연동용 상대 링크로 Vault 구축
```bash
srdocs --repo /path/to/your/project-dir --output wiki_vault --link-type rel
```

### 6. 내장 웹 뷰어로 위키 시각화 및 검토 (로컬 서버 구동)
생성된 위키 폴더 데이터를 파이썬 내장 HTTP 서버를 통해 웹 뷰어 앱으로 시각화하여 로컬 브라우저에서 바로 확인합니다.
```bash
# 기본 srdocs-vault 폴더를 읽어 로컬 웹 서버(8000포트)를 구동하고 브라우저로 연결
srdocs --serve

# 특정 위키 폴더 지정 및 포트(예: 9000) 변경 시
srdocs --serve --output wiki_vault --port 9000
```

---

## ⚙️ CLI 옵션 상세 (Command Line Options)

| 옵션 | 설명 | 기본값 |
|---|---|---|
| `--init` | 대화형 설정 마법사를 실행하여 `.srdocs/config.json`을 생성 | False (store_true) |
| `--repo` | 분석 대상 로컬 프로젝트 폴더 경로 | `.srdocs/config.json` 설정 내의 repos 목록 또는 `.` |
| `--output` | 생성할 위키 파일 경로(.md) 또는 위키 폴더 경로 | `.srdocs/config.json` 설정값 또는 `srdocs-vault` |
| `--link-type` | 위키 내부 파일 바로가기 형식 (`abs`: 절대 경로 `file://` 링크, `rel`: 상대 경로 링크) | `.srdocs/config.json` 설정값 또는 `abs` |
| `--llm` | LLM 요약 백엔드 (`gemini` / `ollama` / `claude` / `none`) | `.srdocs/config.json` 설정값 또는 `none` |
| `--api-key` | Gemini API 인증 키 (미지정 시 환경변수 및 설정값 참조) | 설정값 또는 `GEMINI_API_KEY` |
| `--model` | LLM 모델명 | 설정값 또는 백엔드별 기본 모델 |
| `--api-url` | LLM API 주소 (Ollama, 기타 REST API 등) | 설정값 또는 None |
| `--limit` | 분석할 최대 프로젝트 변경 내역(커밋) 개수 | `500` |
| `--tree-depth` | 폴더 구조 다이어그램의 최대 깊이 | `3` |
| `--lint` | 위키 폴더의 깨진 링크 및 고아 파일 검사 여부 | False (store_true) |
| `--query` | 코드 컨텍스트 검색 기반 자연어 질의 수행 및 위키 저장 | None |
| `--serve` | 로컬 웹 서버를 구동하여 내장된 웹 뷰어를 브라우저에서 실행 | False (store_true) |
| `--port` | 로컬 웹 서버가 사용할 포트 번호 | `8000` |

## 📦 단일 실행 파일 빌드 및 배포 (Standalone Binary Packaging)

이 프로젝트는 파이썬 3 기본 라이브러리만을 활용(Zero Dependencies)하므로 `PyInstaller`를 사용해 독립 실행이 가능한 단일 바이너리 파일로 쉽게 패키징할 수 있습니다.

### 빌드 및 패키징 명령어
우분투(Ubuntu 23.04 이상 등)의 외부 패키지 격리(PEP 668) 정책에 충돌하지 않도록 임시 가상환경을 사용하여 빌드하는 방법입니다.

```bash
# 1. 가상환경 생성 (pip가 없는 우분투 환경을 위해 --without-pip 사용 후 수동 설치)
python3 -m venv venv --without-pip
curl -sS https://bootstrap.pypa.io/get-pip.py -o get-pip.py
./venv/bin/python3 get-pip.py && rm get-pip.py

# 2. PyInstaller 설치 및 웹 뷰어 데이터 포함 단일 파일 빌드
# (Vite로 React 앱이 빌드된 web/frontend/dist 폴더가 사전에 생성되어 있어야 합니다)
./venv/bin/pip install pyinstaller
./venv/bin/pyinstaller --onefile --name srdocs --add-data "web/frontend/dist:web/frontend/dist" run.py

# 3. 임시 빌드 환경 정리 (최종 파일은 dist/srdocs 에 위치)
rm -rf venv build srdocs.spec
```

### ⚠️ 배포 및 실행 시 주의점
1. **OS 및 아키텍처 의존성**: 생성된 실행 파일(`dist/srdocs` 등)은 빌드된 플랫폼(예: Linux x86_64)에 종속됩니다. 다른 환경(Windows, macOS, ARM 계열 등)에서 사용하려면 해당 OS 환경에서 각각 별도로 빌드해야 합니다.
2. **외부 CLI 명령어 의존성**: 단일 파일 내에 파이썬 인터프리터와 프로그램 소스 코드는 내장되어 컴파일되지만, 시스템의 변경 내역 추적용 `git` 명령어, LLM 백엔드 호출을 위한 `claude` CLI 등 외부 프로그램들은 패키징에 포함되지 않습니다. 실행할 호스트 머신에 해당 명령어들이 존재해야 합니다.
3. **내장 웹 뷰어 실행 (`--serve`)**: `--add-data "web/frontend/dist:web/frontend/dist"` 플래그를 추가하여 빌드하면 실행 파일 하나만으로도 웹 UI 분석 서버를 실행할 수 있습니다. 별도의 `web/frontend/` 폴더를 함께 배포하지 않아도 실행 파일이 임시 디렉토리에 웹 정적 리소스를 해제한 뒤 로컬 서버를 띄워 자동으로 브라우저에 연결해 줍니다.
   ```bash
   # 로컬 8000 포트에서 내장 웹 뷰어 호스팅
   ./dist/srdocs --serve
   ```

---

## 📂 프로젝트 구조 (Project Structure)

- [core/analyzer.py](file:///Users/mypc/projects/srdocs/core/analyzer.py): 프로젝트 변경 내역 및 파일 구조 분석
- [core/generator.py](file:///Users/mypc/projects/srdocs/core/generator.py): 통계 산출 및 Markdown 위키 서식 생성
- [core/cache.py](file:///Users/mypc/projects/srdocs/core/cache.py): SHA-256 키 기반 캐싱 및 증분 처리
- [core/summarizer.py](file:///Users/mypc/projects/srdocs/core/summarizer.py): LLM 요약 제어 및 조율
- [core/llm/](file:///Users/mypc/projects/srdocs/core/llm): Gemini/Ollama/Claude API 등 LLM 백엔드 구현
- [core/cli.py](file:///Users/mypc/projects/srdocs/core/cli.py): CLI 서브커맨드 및 흐름 제어
- [web/backend/server.py](file:///Users/mypc/projects/srdocs/web/backend/server.py): 웹 뷰어 서빙용 로컬 HTTP API 서버
- [web/frontend/](file:///Users/mypc/projects/srdocs/web/frontend): React 웹 뷰어 UI 소스 코드
- [run.py](file:///Users/mypc/projects/srdocs/run.py): 프로젝트 실행 스크립트 진입점
