import os
from .llm.factory import LLMBackendFactory

class LLMSummarizer:
    def __init__(self, backend='gemini', api_key=None, api_url=None, model=None, repo_path=None):
        """
        LLMSummarizer 초기화
        
        Args:
            backend: 백엔드 이름 ('gemini', 'ollama', 'claude')
            api_key: API 키 (Gemini용)
            api_url: API 또는 CLI 주소
            model: 사용할 모델명
            repo_path: 저장소 경로
        """
        self.repo_path = repo_path
        
        # 팩토리를 통해 백엔드 생성
        backend_kwargs = {"model": model} if model else {}
        
        if backend == 'gemini':
            if not api_key:
                print("Warning: Gemini backend requires api_key")
            backend_kwargs["api_key"] = api_key
            if api_url:
                backend_kwargs["api_url"] = api_url
        elif backend == 'ollama':
            if api_url:
                backend_kwargs["api_url"] = api_url
        
        try:
            self.backend_impl = LLMBackendFactory.create(backend, **backend_kwargs)
        except ValueError as e:
            print(f"Error creating LLM backend: {e}")
            self.backend_impl = None

    def _collect_file_snippets(self, metadata, files_list, max_files=12, max_lines=60):
        """프로젝트 타입과 디렉토리 분포를 고려해 대표 파일들의 코드 스니펫을 수집합니다."""
        if not self.repo_path:
            return {}

        project_type = metadata.get('type', '').lower()

        if 'python' in project_type:
            priority_exts = {'.py'}
        elif 'node' in project_type:
            priority_exts = {'.js', '.ts', '.jsx', '.tsx', '.mjs', '.cjs'}
        elif 'rust' in project_type:
            priority_exts = {'.rs'}
        elif 'java' in project_type:
            priority_exts = {'.java'}
        elif 'go' in project_type:
            priority_exts = {'.go'}
        else:
            priority_exts = {'.py', '.js', '.ts', '.go', '.rs', '.java', '.rb', '.php', '.swift', '.kt', '.cs'}

        ENTRY_NAMES = {'main', 'app', 'index', 'server', 'cli', 'run', '__main__', 'mod', 'lib', 'application'}

        if 'java' in project_type:
            selected = self._select_java_files(files_list, max_files)
        else:
            selected = self._select_generic_files(files_list, priority_exts, ENTRY_NAMES, max_files)

        snippets = {}
        for path in selected:
            abs_path = os.path.join(self.repo_path, path)
            try:
                with open(abs_path, 'r', encoding='utf-8', errors='ignore') as f:
                    lines = []
                    for i, line in enumerate(f):
                        if i >= max_lines:
                            lines.append(f'... ({os.path.basename(path)} 이하 생략)\n')
                            break
                        lines.append(line)
                    snippets[path] = ''.join(lines)
            except Exception:
                pass

        return snippets

    # 백업·빌드·정적 산출물 디렉토리 — 소스 대표성이 낮아 패널티 부여
    SKIP_DIR_KEYWORDS = {'bak', 'backup', 'old', 'dist', 'build', 'out', 'generated',
                         'node_modules', '.next', '__pycache__', 'vendor', 'target'}

    def _select_generic_files(self, files_list, priority_exts, entry_names, max_files):
        candidates = []
        for f in files_list:
            if f['ext'] not in priority_exts:
                continue
            path = f['path'].replace('\\', '/')
            parts = path.split('/')
            basename = os.path.splitext(parts[-1])[0].lower()
            depth = len(parts)
            top_dir = parts[0].lower() if len(parts) > 1 else 'root'

            # 백업/빌드 디렉토리는 제외
            if any(kw in top_dir for kw in self.SKIP_DIR_KEYWORDS):
                continue

            score = 0
            if basename in entry_names:
                score += 100
            if depth == 1:
                score += 50
            elif depth == 2:
                score += 20
            score -= depth * 2

            candidates.append((score, path, top_dir))

        candidates.sort(key=lambda x: -x[0])

        # 1순위: 엔트리포인트(score >= 50) — 디렉토리 무관하게 포함
        selected = []
        dir_counts: dict = {}
        for score, path, top_dir in candidates:
            if score >= 50:
                selected.append(path)
                dir_counts[top_dir] = dir_counts.get(top_dir, 0) + 1

        # 2순위: 나머지를 점수순으로 채우되, 디렉토리별 최대 3개 제한
        for score, path, top_dir in candidates:
            if len(selected) >= max_files:
                break
            if path in selected:
                continue
            if dir_counts.get(top_dir, 0) < 3:
                selected.append(path)
                dir_counts[top_dir] = dir_counts.get(top_dir, 0) + 1

        return selected[:max_files]

    def _select_java_files(self, files_list, max_files):
        """Java Spring 프로젝트용 파일 선택: Application > Controller > Service > 기타."""
        app_files = [f['path'] for f in files_list if f['path'].endswith('.java')
                     and any(k in f['path'] for k in ('Application.java', 'Main.java'))]
        controllers = [f['path'] for f in files_list if 'Controller.java' in f['path']]
        services = [f['path'] for f in files_list if 'Service.java' in f['path']
                    and 'Impl' not in f['path']]

        selected = app_files[:1]
        selected += self._diverse_by_dir(controllers, (max_files - len(selected)) // 2)
        selected += self._diverse_by_dir(services, max_files - len(selected))
        return selected[:max_files]

    def _diverse_by_dir(self, paths, limit):
        """디렉토리별로 하나씩 라운드로빈 샘플링합니다."""
        from collections import defaultdict
        groups = defaultdict(list)
        for p in paths:
            parts = p.replace('\\', '/').split('/')
            top = parts[0] if len(parts) > 1 else 'root'
            groups[top].append(p)

        result = []
        keys = sorted(groups.keys())
        idx = 0
        while len(result) < limit:
            added = False
            for k in keys:
                if idx < len(groups[k]):
                    result.append(groups[k][idx])
                    added = True
                    if len(result) >= limit:
                        break
            if not added:
                break
            idx += 1
        return result

    def _extract_routes(self, metadata, files_list):
        """페이지/라우트 파일을 추출하여 메뉴 구조를 파악합니다."""
        project_type = metadata.get('type', '').lower()
        routes = []

        if 'node' in project_type:
            # Next.js App Router: app/**/page.tsx, app/**/layout.tsx
            # Next.js Pages Router: pages/**/*.tsx
            # 일반 라우트 파일
            route_names = {'page.tsx', 'page.jsx', 'page.ts', 'page.js',
                           'layout.tsx', 'layout.jsx', 'route.ts', 'route.js',
                           'index.tsx', 'index.jsx', 'index.js', 'index.ts'}
            for f in files_list:
                path = f['path'].replace('\\', '/')
                basename = os.path.basename(path)
                top_dir = path.split('/')[0].lower() if '/' in path else ''
                if any(kw in top_dir for kw in self.SKIP_DIR_KEYWORDS):
                    continue
                if basename.lower() in route_names:
                    routes.append(path)
        elif 'python' in project_type:
            # Flask/Django: views.py, urls.py, routes.py
            route_names = {'views.py', 'urls.py', 'routes.py'}
            for f in files_list:
                path = f['path'].replace('\\', '/')
                basename = os.path.basename(path)
                if basename.lower() in route_names:
                    routes.append(path)
        elif 'java' in project_type:
            for f in files_list:
                if 'Controller.java' in f['path']:
                    routes.append(f['path'].replace('\\', '/'))
        else:
            # 기타: 라우트 관련 이름 패턴
            for f in files_list:
                path = f['path'].replace('\\', '/')
                basename = os.path.basename(path).lower()
                if any(kw in basename for kw in ('route', 'page', 'view', 'controller', 'handler')):
                    routes.append(path)

        return sorted(routes)

    def _all_source_paths(self, metadata, files_list):
        """소스 파일 경로 전체 목록을 프로젝트 타입별로 필터링해 반환합니다."""
        project_type = metadata.get('type', '').lower()
        if 'node' in project_type:
            exts = {'.js', '.ts', '.jsx', '.tsx', '.mjs', '.cjs', '.vue'}
        elif 'python' in project_type:
            exts = {'.py'}
        elif 'rust' in project_type:
            exts = {'.rs'}
        elif 'java' in project_type:
            exts = {'.java', '.kt'}
        elif 'go' in project_type:
            exts = {'.go'}
        else:
            exts = {'.py', '.js', '.ts', '.go', '.rs', '.java', '.rb', '.php', '.swift', '.kt', '.cs'}

        paths = []
        for f in files_list:
            path = f['path'].replace('\\', '/')
            top_dir = path.split('/')[0].lower() if '/' in path else ''
            if any(kw in top_dir for kw in self.SKIP_DIR_KEYWORDS):
                continue
            if f['ext'] in exts:
                paths.append(path)
        return sorted(paths)

    def _summarize_routes_in_chunks(self, routes, metadata, chunk_size=35):
        """라우트 파일 목록이 너무 길 때, 이를 쪼개서 각 부분 요약을 먼저 얻고 합칩니다."""
        total = len(routes)
        
        # 라우트 파일이 50개를 초과하면 디렉토리(패키지) 단위로 그룹화하여 요약
        if total > 50:
            print(f"   - 🛠️ 라우트 파일이 너무 많아 ({total}개) 디렉토리/패키지 단위로 그룹화하여 요약을 진행합니다.")
            from collections import defaultdict
            
            # 적응형 패키지 레벨 결정 (그룹 수가 30개 이하가 될 때까지 depth 축소)
            dir_groups = defaultdict(list)
            for level in [3, 2, 1]:
                dir_groups = defaultdict(list)
                for r in routes:
                    dirname = os.path.dirname(r).replace('\\', '/')
                    # 소스 마커 기반 공통 접두사 제거
                    for marker in ['/src/main/java/', '/src/main/', '/src/', '/app/', '/pages/']:
                        if marker in dirname:
                            dirname = dirname.split(marker)[-1]
                            break
                    else:
                        for marker in ['src/main/java/', 'src/main/', 'src/', 'app/', 'pages/']:
                            if dirname.startswith(marker):
                                dirname = dirname[len(marker):]
                                break
                    
                    parts = dirname.split('/')
                    if len(parts) > level:
                        dirname = "/".join(parts[:level])
                    filename = os.path.basename(r)
                    dir_groups[dirname].append(filename)
                
                if len(dir_groups) <= 30:
                    break
            
            group_lines = []
            for display_dir in sorted(dir_groups.keys()):
                files_in_dir = dir_groups[display_dir]
                if len(files_in_dir) > 5:
                    files_str = ", ".join(files_in_dir[:5]) + f" 외 {len(files_in_dir)-5}개"
                else:
                    files_str = ", ".join(files_in_dir)
                group_lines.append(f"  - {display_dir}/ ({files_str})")
            
            routes_summary_input = "\n".join(group_lines)
            prompt = f"""다음 프로젝트의 페이지/라우트 디렉토리 및 주요 파일 목록을 분석하여, 각 디렉토리(패키지)가 어떤 화면군이나 역할을 담당할지 한글로 간결하게 요약해주세요.
이 요약본은 프로젝트의 종합 아키텍처 개요 문서에 반영됩니다.

프로젝트 이름: {metadata['name']}
프로젝트 타입: {metadata['type']}

[디렉토리 및 소속 라우트 파일 목록]
{routes_summary_input}

작성 요령:
- 각 디렉토리/패키지별로 어떤 업무나 기능 그룹을 처리하는지 명확히 파악하여 한글로 보기 좋게 요약해주세요.
- 확인되지 않은 세부 기능은 추측하지 마세요.
"""
            return self._generate(prompt)

        summaries = []
        print(f"   - 🛠️ 라우트 파일이 너무 많아 ({total}개) 분할 요약을 진행합니다... (그룹당 {chunk_size}개)")
        
        for i in range(0, total, chunk_size):
            chunk = routes[i:i+chunk_size]
            chunk_num = (i // chunk_size) + 1
            total_chunks = (total + chunk_size - 1) // chunk_size
            print(f"     * 라우트 그룹 요약 진행 중 ({chunk_num}/{total_chunks})...")
            
            chunk_text = "\n".join(f"  - {r}" for r in chunk)
            prompt = f"""다음 프로젝트의 일부 페이지/라우트 파일 목록을 분석하여, 각 파일들이 어떤 화면이나 역할을 담당할지 한글로 간결하게 요약해주세요.
이 요약본들은 최종적으로 합쳐져 프로젝트의 종합 아키텍처 개요 문서에 반영됩니다.

프로젝트 이름: {metadata['name']}
프로젝트 타입: {metadata['type']}

[분석 대상 페이지/라우트 목록]
{chunk_text}

작성 요령:
- 각 파일별로 어떤 화면/기능인지 명확히 파악하여 한두 줄 내외로 보기 좋게 요약해주세요.
- 확인되지 않은 세부 기능은 추측하지 마세요.
"""
            chunk_summary = self._generate(prompt)
            if chunk_summary:
                summaries.append(chunk_summary)
            else:
                summaries.append(f"(라우트 파일 {i+1}~{min(total, i+chunk_size)} 요약 실패)")
                
        return "\n\n".join(summaries)

    def summarize_overview(self, metadata, files_list):
        from collections import defaultdict
        
        snippets = self._collect_file_snippets(metadata, files_list)
        routes = self._extract_routes(metadata, files_list)
        all_sources = self._all_source_paths(metadata, files_list)

        snippets_text = ""
        for path, content in snippets.items():
            snippets_text += f"\n--- {path} ---\n{content}\n"

        # 라우트 파일이 많다면 쪼개서 사전 분석 진행 (누락 방지)
        if len(routes) > 35:
            routes_analysis = self._summarize_routes_in_chunks(routes, metadata, chunk_size=35)
            routes_text = f"[사전 분석된 라우트 요약 내용]\n{routes_analysis}"
        else:
            routes_text = "\n".join(f"  - {r}" for r in routes) if routes else "  (라우트 파일 없음)"

        # 소스 파일 목록을 디렉토리 구조 및 파일 개수로 요약 (생략 없이 전체 구조 반영)
        snippet_paths = set(snippets.keys())
        remaining_sources = [p for p in all_sources if p not in snippet_paths]
        
        dir_counts = defaultdict(int)
        for p in remaining_sources:
            dir_name = os.path.dirname(p).replace('\\', '/')
            if not dir_name:
                dir_name = 'root'
            dir_counts[dir_name] += 1
            
        remaining_text_lines = []
        for d in sorted(dir_counts.keys()):
            remaining_text_lines.append(f"  - {d}/ (총 {dir_counts[d]}개 소스 파일)")
        remaining_text = "\n".join(remaining_text_lines) if remaining_text_lines else "  (없음)"

        deps_str = ', '.join(metadata['dependencies'][:20]) if metadata['dependencies'] else '없음'

        prompt = f"""다음 프로젝트의 소스 코드와 메타데이터를 분석하여 개발자를 위한 한글 프로젝트 개요를 Markdown으로 작성해주세요.

프로젝트 이름: {metadata['name']}
프로젝트 타입: {metadata['type']}
버전: {metadata['version']}
의존성: {deps_str}

README:
{metadata.get('readme', '')[:3000]}

[페이지/라우트 파일 요약 또는 목록]
{routes_text}

[핵심 소스 파일 내용 — 실제 코드 스니펫]
{snippets_text if snippets_text else '(소스 파일 스니펫 없음)'}

[디렉토리별 소스 파일 분포]
{remaining_text}

작성 요령:
- 제공된 [페이지/라우트 파일 요약 또는 목록]에 설명된 모든 화면과 메뉴 구성을 프로젝트의 기능 소개 부분에 종합적이고 누락 없이 설명해 주세요.
- 이 프로젝트가 실제로 무엇을 하는지, 어떤 비즈니스 기능들을 제공하는지 구체적으로 설명하세요.
- 주요 모듈/클래스/함수를 직접 언급하며 전체 아키텍처를 설명하세요.
- 기술 스택 나열보다 실제 동작 방식และ 데이터 흐름 위주로 작성하세요.
- 확인되지 않은 내용은 추측하지 말고, 코드에서 확인된 내용만 기술하세요.
"""
        return self._generate(prompt)

    def summarize_release(self, version_name, commits):
        # 커밋 메시지 전처리 (길이 제한)
        processed_commits = []
        for c in commits:
            subject = c['subject']
            if len(subject) > 120:
                subject = subject[:120] + "..."
            processed_commits.append(f"- {c['hash']}: {subject} (by {c['author']})")

        total = len(processed_commits)
        # 커밋이 35개 이하면 한 번에 요약
        if total <= 35:
            commit_log = "\n".join(processed_commits)
            return self._generate_prompt_for_release(version_name, commit_log)
        
        # 커밋이 많으면 30개 단위로 나누어 부분 요약 후 병합
        print(f"   - 🛠️ 버전에 포함된 커밋이 너무 많아 ({total}개) 분할 요약을 진행합니다...")
        chunk_size = 30
        summaries = []
        for i in range(0, total, chunk_size):
            chunk = processed_commits[i:i+chunk_size]
            chunk_num = (i // chunk_size) + 1
            total_chunks = (total + chunk_size - 1) // chunk_size
            print(f"     * 커밋 그룹 요약 진행 중 ({chunk_num}/{total_chunks})...")
            
            commit_log = "\n".join(chunk)
            chunk_summary = self._generate_prompt_for_release(version_name, commit_log)
            if chunk_summary:
                summaries.append(chunk_summary)
            else:
                summaries.append(f"(커밋 {i+1}~{min(total, i+chunk_size)} 요약 실패)")
                
        # 부분 요약본들을 다시 최종 요약
        combined_summaries = "\n\n".join(summaries)
        merge_prompt = f"""다음은 프로젝트의 '{version_name}' 버전에 대해 분할하여 요약한 부분 변경 사항들입니다.
이들을 종합하여 핵심 변경 사항(기능 추가, 버그 수정, 리팩토링 등)을 카테고리별로 일목요연하게 정리한 하나의 통합 릴리즈 노트(Markdown 한글)를 작성해주세요.

[부분 요약본 목록]
{combined_summaries}

작성 형식:
- 가독성이 좋은 Markdown 글머리 기호로 정리해주세요.
- 중복되거나 무의미한 내용은 합치고, 깔끔하게 정리해 주세요.
        """
        return self._generate(merge_prompt)

    def _generate_prompt_for_release(self, version_name, commit_log):
        prompt = f"""프로젝트의 '{version_name}' 버전에 해당하는 다음 커밋 목록을 분석하여, 이 버전에서 어떤 핵심 변경 사항(기능 추가, 버그 수정, 리팩토링 등)이 적용되었는지 한글로 요약해주세요.

버전 이름: {version_name}
커밋 목록:
{commit_log}

작성 형식:
- 요점만 Markdown 글머리 기호(bullet points)로 읽기 쉽게 정리해주세요.
- 커밋 메시지가 영어라면 핵심을 파악하여 한글로 번역 및 정리해주세요.
        """
        return self._generate(prompt)

    def answer_query(self, query, metadata, context_results):
        context_str = ""
        for r in context_results:
            context_str += f"--- 파일: {r['path']} ---\n{r['snippet']}\n\n"

        prompt = f"""프로젝트 '{metadata['name']}'에 대해 다음 질문에 기술적으로 상세히 답변해주세요.
프로젝트 타입: {metadata['type']}
의존성: {metadata['dependencies']}

질문: {query}

관련 코드 및 파일 컨텍스트:
{context_str}

작성 형식:
- 한국어로 기술적인 세부사항을 명확히 설명해주세요.
- 마크다운 서식을 활용해 보기 쉽게 작성하고, 코드 스니펫이나 클래스/함수명 등을 구체적으로 언급해주세요.
- **[중요 - 환각 및 추론 방지]**: 만약 제공된 '관련 코드 및 파일 컨텍스트'가 비어 있거나, 질문 내용과 직접적으로 관련된 실제 구현 코드가 포함되어 있지 않다면, **절대 어떠한 구현 로직이나 비즈니스 흐름도 추론(Deduction)하여 작성하지 마세요.**
  이 경우에는 오직 다음 내용만을 작성하고 즉시 답변을 끝마치십시오:
  1. "제공된 파일 컨텍스트 내에서 질문과 관련된 실제 구현 코드를 찾을 수 없습니다." 문구를 첫 행에 작성합니다.
  2. 코드를 찾지 못한 명확한 기술적 이유(예: 분석 대상 범위 `--repo` 제한, 무관한 코드 검색 결과 등)를 설명합니다.
  3. 올바른 결과를 얻기 위한 해결 방안(예: 분석 저장소 경로 확대 등)을 제시합니다.
  *그 이외의 추측성 구현 설명, 일반론적인 아키텍처 이론 등은 단 한 줄도 작성하지 말고 문서를 종결해야 합니다.*
        """
        return self._generate(prompt)

    def _generate(self, prompt):
        """백엔드를 통해 프롬프트 처리"""
        if not self.backend_impl:
            return ""
        return self.backend_impl.call(prompt)


