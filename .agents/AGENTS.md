# 프로젝트 규칙 및 개발 가이드 (Project Rules & Development Guide)

## 📌 프로젝트 규칙 (Project Rules)

- **자동 Git 커밋 금지 (No Automatic Git Commits)**: 에이전트는 코드 수정이나 작업 완료 후 자동으로 Git 커밋(`git commit`)을 실행해서는 안 됩니다. 변경 사항을 확인한 후 커밋하는 권한은 전적으로 사용자에게 있으며, 사용자가 직접 수행하거나 명시적으로 요청한 경우에만 진행해야 합니다.

---

## 📖 에이전트 개발 가이드 및 아키텍처 (Development Guide)

이 저장소에서 에이전트(Antigravity 등)가 작업할 때 참고하는 개발 가이드 및 아키텍처 맵입니다.

### 빠른 시작

**초기 설정:** 아래 명령어로 설정 마법사를 최초 1회 실행하여 기본 환경설정 파일(`~/.git_wiki_config.json`)을 생성합니다.
```bash
python3 run.py --init
```

**실행:**
```bash
# 기본: 설정 파일에 따른 위키 생성 (기본값: ~/vault-git-llm-wiki 디렉토리 구조 위키 생성)
python3 run.py

# CLI 인자 직접 지정: 단일 마크다운 위키 생성
python3 run.py --repo /path/to/git-repo --output WIKI.md
```

진입점: `run.py` → `core/cli.py:main()`

### 아키텍처 개요

**파이프라인:** `core/cli.py:main()`이 네 단계를 순서대로 실행합니다:

1. **`GitAnalyzer`** (`core/analyzer.py`) — `git log --numstat` 실행, 커밋+파일 파싱, 워크트리 스캔 (`.gitignore` 준수), 매니페스트 파일로 프로젝트 타입 감지

2. **`WikiCache`** (`core/cache.py`) — 사용자 홈 디렉토리의 캐시 폴더(`~/.cache/git-llm-wiki/`)에 저장소 절대 경로 해시 기반의 JSON 파일로 저장되는 로컬 캐시. 개요 키 = 파일 메타데이터 해시, 릴리즈 키 = 커밋 해시 조합. LLM 호출 **이전에** 캐시를 먼저 확인 (중복 생성 방지)

3. **`LLMSummarizer`** (`core/summarizer.py` + `core/llm/`) — 세 가지 백엔드:
   - `gemini`, `ollama` → `urllib.request`로 REST API 호출
   - `claude` → 로컬 Claude CLI (`claude -p`) subprocess 호출
   - 모든 프롬프트와 출력은 한국어

4. **`WikiGenerator`** (`core/generator.py`) — 순수 렌더링 계층, 두 가지 출력 모드:
   - 단일 `.md` 파일: `generate()`
   - 디렉토리 Vault: `generate_directory()` → `index.md`, `overview.md`, `log.md`, `versions/<tag>.md`, `components/<dir>.md`, `decisions/<slug>.md`

독립 흐름: `run_lint()`과 `run_query()`는 메인 파이프라인을 우회합니다.

---

### 운영 모드 및 갱신 방식 (Operating Modes)

이 도구는 운영 환경 및 갱신 자동화 여부에 따라 두 가지 모드로 분류하여 관리 및 배포합니다.

#### 1. 수동 모드 (Manual Mode) - [현재 구현 완료]
* **개요**: 사용자가 CLI 인자 또는 최초 설정 마법사(`--init`)를 통해 특정 로컬 폴더 경로 또는 `.git` 주소를 지정하여 1회성/필요에 따라 직접 문서를 생성해내는 방식입니다.
* **사용 시나리오**: 로컬 개발자 문서 확인, 온프레미스 수동 빌드 배포, 소규모 프로젝트.
* **실행 예시**:
  ```bash
  python3 run.py --repo /path/to/my-project --output ~/vault-git-llm-wiki
  ```

#### 2. 자동 모드 (Auto Mode) - [로드맵 / 개발 계획 단계]
새로운 커밋이 원격 저장소에 감지되면 백그라운드에서 실시간으로 문서를 자동 빌드하여 서빙 경로로 업데이트하는 방식입니다. (현재는 계획 단계이며 구현 예정)

* **방안 A: Webhook 기반 실시간 트리거 (Push Trigger)**
  * **구조**: 컨테이너 또는 서버 내부에 경량 웹 API 서버(FastAPI, Flask 등)를 백그라운드로 구동.
  * **동작**: GitHub/GitLab에 `git push`가 발생할 때 등록된 웹훅 수신 ➡️ 즉시 `git pull` 후 `run.py`를 실행하여 해당 프로젝트 문서를 실시간으로 갱신.
* **방안 B: Polling 기반 주기적 갱신 (Polling Trigger)**
  * **구조**: 백그라운드 스케줄러 프로세스(Cron 또는 Python `schedule` 라이브러리) 활용.
  * **동작**: 일정 주기(예: 1시간 또는 매일 밤)로 원격 저장소의 헤드 커밋 해시를 체크 ➡️ 변경 사항 감지 시 자동으로 `run.py` 빌드를 실행하여 문서 폴더 갱신.

---

### 향후 개발 로드맵 (Roadmap)

더 강력한 지식 저장소(Knowledge Repository)로 도약하기 위해 계획된 확장 기능 로드맵입니다.

1. **자동화 모드 및 CI/CD 연동 (Auto Mode & CI/CD)**: Webhook/Polling 기반으로 GitHub Actions 등에 결합되어 커밋이 push될 때마다 문서가 중앙 호스팅 서버나 문서 페이지로 자동 갱신되는 파이프라인 구축.
2. **웹 뷰어 내 풀텍스트 검색 (Full-text Search)**: 단순 제목/컴포넌트명 필터링을 넘어 위키 내 모든 마크다운 본문 내용을 브라우저단에서 고속 검색할 수 있는 경량 검색 엔진(`MiniSearch`, `flexsearch` 등) 연동.
3. **웹 뷰어 양방향 편집 및 피드백 (Write/Edit Support)**: 읽기 전용 뷰어에서 문서 오타나 아키텍처 다이어그램을 직접 수정하고, 이를 로컬 소스 코드 저장소 파일에 반영하여 커밋/푸시까지 수행하는 양방향 지식 관리 워크플로우 구현.

---

### 웹 뷰어 (Web Viewer) 아키텍처

**구조:** React + Vite 기반의 정적 단일 페이지 애플리케이션(SPA)입니다. `web/` 디렉토리에 위치합니다.

**데이터 연동 및 로딩 방식:**
1. 브라우저에서 상대 경로 `./vault/projects.json`을 요청하여 위키 프로젝트 목록을 파악합니다.
2. 선택된 프로젝트 폴더 내부의 `./vault/<projectName>/vault_meta.json`을 읽어 컴포넌트, 버전, 의사결정 문서 목록 등의 사이드바 메뉴를 구성합니다.
3. 실제 문서는 개별 마크다운 파일(`.md`)을 가져와서 브라우저 단에서 동적으로 파싱 및 렌더링합니다.

**렌더러 확장 기술:**
* `remark-gfm` 적용: 테이블(표), 체크박스, 취소선 등 GitHub 마크다운 문법 100% 렌더링.
* `rehype-raw` 적용: 마크다운 내부의 가공되지 않은 raw HTML 구문(예: `<br>`) 실시간 렌더링.
* `mermaid` 그래픽 엔진 내장: ` ```mermaid ` 코드블록을 감지하여 브라우저 상에서 실시간 아키텍처 관계도 및 순서도로 시각화 변환.

**로컬 개발 확인 방법:**
* Vite 개발 서버(`npm run dev`)는 `web/`을 루트로 띄우므로, `web/public/vault` 경로에 위키 데이터가 존재해야 합니다.
* 일일이 복사할 필요 없이 심볼릭 링크(`ln -s ~/vault-git-llm-wiki web/public/vault` 형태 등)를 활용하여 연동할 수 있습니다.

---

### 주요 동작 특성

#### 설정 파일 관리 (`~/.srdocs/config.json`)
* CLI 실행 시 `~/.srdocs/config.json`을 로드하여 `argparse` 파서의 기본값(default)으로 매핑합니다.
* 사용자가 터미널에서 옵션 없이 실행했는데 설정이 없다면 대화형 마법사(`run_wizard`)가 실행되나, CI/CD 등 TTY(대화형 입력 가능 터미널)가 없는 환경에서는 마법사가 생략되고 기존 내장 기본값으로 논스톱 실행됩니다.
* 이 설정 파일에는 API Key 및 로컬 전용 절대경로가 포함되므로 홈 디렉토리에 생성되어 Git 추적에서 원천 차단됩니다.

#### 커밋 그룹핑
* **태그 기반:** Git 태그 중 `v[0-9a-zA-Z.-]+` 패턴 매칭 → 릴리즈 버전으로 인식
* **폴백:** 태그가 없으면 `YYYY-MM` (월별)로 그룹화
* 결과: `grouped_commits` 딕셔너리 (버전 → 커밋 목록)

#### 파일 링크
* `--link-type abs` (기본값) → `file:///절대경로` 링크 (로컬 개발 환경용)
* `--link-type rel` → URL 인코딩 상대 경로 (Obsidian Vault 연동용)

#### 캐싱 전략
* **호출 순서 중요:** 캐시는 LLM 인스턴스화 **이전에** 확인됩니다 (`cli.py` 149–163줄)
* 이전에 캐시된 릴리즈/개요는 `--llm none`이 전달되어도 재사용됩니다
* 캐시 무효화 조건: 파일 메타데이터 변경 (개요용), 커밋 세트 변경 (릴리즈용)

#### `--query` 흐름
1. 소스 파일에서 쿼리 키워드 검색
2. 매칭된 스니펫을 LLM 컨텍스트로 전달
3. 답변을 `decisions/<slug>.md`에 저장
4. 전체 Vault 인덱스 재빌드

**중요:** 쿼리는 디렉토리 Vault (`--output` 지정 폴더)에서만 작동합니다. `.md` 파일 모드에서는 작동하지 않습니다.

#### Java/Spring 휴리스틱
`core/summarizer.py:_select_java_files()`는 Spring 프로젝트 전용 파일 우선순위 지정 (Application, Controller, Service 등). 다른 프로젝트 타입에서는 안전하게 스킵됩니다.

---

### 흔한 실수와 대처법

1. **유효하지 않은 저장소로 실행:** `--repo` 경로가 Git 디렉토리인지 확인하세요. 도구는 초기에 `check_is_repo()`로 확인하고 오류 시 종료합니다.

2. **캐시 무효화 무시:** 출력 생성을 작업할 때, 캐시 파일은 실제 개발 코드가 있는 프로젝트 폴더가 아닌 사용자 홈 디렉토리의 캐시 폴더(`~/.cache/git-llm-wiki/`)에 저장소 별로 구분되어 저장됩니다. 캐시를 완전히 비우려면 해당 폴더의 JSON 캐시 파일들을 삭제하세요.

3. **LLM 백엔드 설정:** 
   - `--llm gemini` → `GEMINI_API_KEY` 환경변수 또는 `--api-key` 플래그 필요
   - `--llm claude` → 로컬 `claude` CLI 설치 필요 (subprocess 호출: `core/llm/backends/claude.py`)
   - `--llm ollama` → Ollama 실행 필요 (`http://localhost:11434/api/generate` 또는 `--api-url`로 오버라이드)

4. **출력 모드 불일치:** 린팅과 쿼리는 디렉토리 Vault에서만 작동합니다. `.md` 파일로 지정하면 도구가 자동으로 `wiki` 폴더로 변환합니다 (`cli.py` 91, 98줄).

5. **설정 마법사 및 자동화(CI/CD) 주의점:** `~/.srdocs/config.json`이 로컬에 이미 구성되어 있어도, CI/CD 환경이나 다른 컴퓨터에 배포 시에는 CLI 인자를 명시적으로 제공하여 작동하게 설정해야 합니다. (CI/CD 환경에서는 마법사 입력 대기가 자동으로 스킵되므로 CLI 인자가 필수적입니다.)

### 모듈별 역할

- `run.py` — 얇은 진입점, `core/cli.py:main()`으로 위임
- `core/cli.py` — 메인 CLI 조율, 인자 파싱, 파이프라인 실행, 마법사 및 설정 파일 제어
- `core/analyzer.py` — Git subprocess, 파일 스캔, `.gitignore` 준수, 메타데이터 감지
- `core/generator.py` — 통계 계산, 마크다운 템플릿, Vault 구조 및 `projects.json` 생성
- `core/cache.py` — JSON 캐시 I/O, 해시 키 생성
- `core/summarizer.py` — LLM 호출 조율, 프롬프트 템플릿 선택
- `core/llm/` — 백엔드 구현 (Gemini, Ollama, Claude)

### 테스트 및 검증

자동 테스트 스위트 없음. 실제 저장소를 대상으로 검증합니다.

**수동 검증 패턴:**
```bash
# 현재 저장소에 대해 테스트 (git-wiki-generator)
python3 run.py --repo . --output /tmp/test_wiki.md

# Vault 모드 테스트
python3 run.py --repo . --output /tmp/test_vault

# 린트 테스트
python3 run.py --repo . --output /tmp/test_vault --lint

# LLM 포함 테스트 (설정 필요)
python3 run.py --repo . --output /tmp/test_vault --llm gemini --api-key $GEMINI_API_KEY
```

### 바이너리 패키징 및 배포

이 도구는 외부 라이브러리 의존성이 없기 때문에 `PyInstaller`를 사용하여 단일 실행 파일(바이너리)로 패키징하여 배포할 수 있습니다.

#### 패키징 방법 (Ubuntu 등 PEP 668 환경 대응)
```bash
# 1. 가상환경 생성 (pip가 없는 우분투 환경을 위해 --without-pip 사용 후 수동 설치)
python3 -m venv venv --without-pip
curl -sS https://bootstrap.pypa.io/get-pip.py -o get-pip.py
./venv/bin/python3 get-pip.py && rm get-pip.py

# 2. PyInstaller 설치 및 웹 뷰어 리소스를 포함한 단일 파일 빌드
./venv/bin/pip install pyinstaller
./venv/bin/pyinstaller --onefile --name git-llm-wiki --add-data "web/dist:web/dist" run.py

# 3. 임시 빌드 환경 정리 (빌드 결과물은 dist/git-llm-wiki 에 생성됨)
rm -rf venv build git-llm-wiki.spec
```

#### 바이너리 배포 및 실행 시 주의점
1. **OS 및 아키텍처 의존성**: 컴파일된 바이너리는 빌드를 진행한 OS와 아키텍처 환경(예: Linux x86_64)에 완전히 종속됩니다. Windows(EXE)나 macOS 등 다른 환경에서 사용하기 위해서는 각각의 환경에서 개별적으로 빌드하여 배포해야 합니다.
2. **외부 CLI 명령어 의존성**: 빌드된 실행 파일 내에 파이썬 인터프리터와 소스 코드는 내장되어 있으나, 시스템의 `git` 명령어, LLM 호출을 위한 `claude` CLI 등 외부 프로그램은 패키징에 포함되지 않습니다. 바이너리를 실행하는 호스트 시스템에 해당 프로그램들이 설치되어 있는지 확인해야 합니다.
3. **내장 웹 뷰어 서버 구동 (`--serve`)**: `--add-data` 플래그로 내장된 리액트 정적 리소스들은 실행 시 임시 디렉토리에 풀리며, `--serve` 실행 시 파이썬 자체 내장 HTTP 서버를 통해 서빙됩니다. 사용자는 다른 웹 앱 리소스 파일들을 함께 배포할 필요 없이 실행 바이너리 하나만으로 온전한 웹 UI 화면을 로컬 브라우저로 띄워 감상할 수 있습니다.
   ```bash
   ./dist/git-llm-wiki --serve
   ```

### 참고 자료

- `README.md` — 사용자 대상 기능 설명 및 예제
- `.gitignore` — 테스트 및 로컬 빌드 산출물 제외 (`vault/`, `.git_wiki_cache.json`)

현재 `opencode.json`, CI 워크플로우, 사전 커밋 훅이 없습니다.
