import argparse
import os
import sys
import json
from collections import defaultdict
from .analyzer import GitAnalyzer
from .generator import WikiGenerator
from .summarizer import LLMSummarizer
from .server import run_server, get_resource_path

# 설정 파일 및 위키 저장을 위한 통합 디렉토리 정의
VAULT_BASE_DIR = os.path.join(os.path.expanduser("~"), "srdocs-vault")
CONFIG_FILE = os.path.join(os.path.expanduser("~"), ".srdocs")

def load_config():
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            print(f"⚠️ 설정 파일을 읽지 못했습니다: {e}")
            return {}
    return {}

def save_config(config):
    try:
        os.makedirs(os.path.dirname(CONFIG_FILE), exist_ok=True)
        with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
            json.dump(config, f, indent=2, ensure_ascii=False)
        print(f"✅ 설정이 저장되었습니다: {CONFIG_FILE}")
    except Exception as e:
        print(f"⚠️ 설정을 저장하지 못했습니다: {e}")

def run_wizard():
    print("==================================================")
    print("🧙 srdocs (Git Wiki Generator) 초기 설정 마법사")
    print("==================================================")
    print("설정 파일(.srdocs)이 존재하지 않거나 초기화 요청이 있어")
    print("대화형 설정을 시작합니다.")
    print("엔터(Enter)를 누르면 괄호 () 안의 기본값이 적용됩니다.")
    print("자동화 환경(CI/CD)에서는 이 마법사가 실행되지 않습니다.")
    print("--------------------------------------------------")
    
    config = {}
    
    # 1. 대상 Git 저장소 목록 (쉼표 구분)
    print("\n[1] 로컬 Git 저장소 경로 목록")
    print("    - 위키 문서를 생성하기 위해 분석할 로컬 Git 저장소들의 최상위 폴더 경로입니다.")
    print("    - 여러 프로젝트를 한 번에 빌드하고 싶다면 경로를 쉼표(,)로 구분해 입력해 주세요.")
    repos_input = input("    저장소 경로 목록 (기본값: 현재 폴더 .): ").strip()
    if repos_input:
        config['repos'] = [r.strip() for r in repos_input.split(",") if r.strip()]
    else:
        config['repos'] = ["."]
    
    # 2. 저장 경로
    default_output = "DEFAULT"
    print("\n[2] 위키 문서 저장 경로")
    print(f"    - 생성된 위키 폴더/파일이 저장될 위치입니다.")
    print(f"    - 기본값인 'DEFAULT'를 사용할 경우, 홈 디렉토리 하위의")
    print(f"      '{os.path.join(VAULT_BASE_DIR, '<project_name>')}' 경로에 각각 분할되어 생성됩니다.")
    output = input("    원하는 경로 입력 (엔터 입력 시 기본값 DEFAULT 적용): ").strip()
    config['output'] = output if output else default_output
    
    # 3. 링크 타입
    print("\n[3] 위키 문서 내 파일 링크 형식")
    print("    - 위키에서 소스 코드로 바로가기 할 때 생성되는 하이퍼링크의 형식입니다.")
    print("    - abs: 로컬 개발 환경용 절대 경로 바로가기 링크 (file://...)")
    print("    - rel: Obsidian Vault 등 로컬 개인 위키 연동을 위한 상대 경로 링크")
    link_type = input("    형식 입력 (abs / rel) (기본값: abs): ").strip()
    config['link_type'] = link_type if link_type in ['abs', 'rel'] else "abs"
    
    # 4. LLM 백엔드
    print("\n[4] LLM 요약 백엔드 선택")
    print("    - 소스 코드 핵심 요약 및 커밋 로그 릴리즈 노트를 생성할 AI 모델 서비스입니다.")
    print("    - none: AI 요약 분석을 건너뛰고 기본 통계 및 아키텍처 다이어그램만 빠르게 빌드합니다.")
    print("    - gemini / ollama / claude: 각각 해당 LLM 서비스를 연동해 세부 요약을 생성합니다.")
    llm = input("    백엔드 선택 (none, gemini, ollama, claude) (기본값: none): ").strip()
    config['llm'] = llm if llm in ['gemini', 'ollama', 'claude', 'none'] else "none"
    
    if config['llm'] == 'gemini':
        print("\n    - Gemini API 설정")
        api_key = input("      * Gemini API 인증 키 (환경변수 GEMINI_API_KEY가 있다면 생략 가능): ").strip()
        if api_key:
            config['api_key'] = api_key
        model = input("      * 사용할 모델명 (기본값: gemini-1.5-flash): ").strip()
        config['model'] = model if model else "gemini-1.5-flash"
    elif config['llm'] == 'ollama':
        print("\n    - Ollama API 설정")
        model = input("      * 사용할 Ollama 로컬 모델명 (기본값: gemma4:e4b): ").strip()
        config['model'] = model if model else "gemma4:e4b"
        api_url = input("      * Ollama API 주소 (기본값: http://localhost:11434/api/generate): ").strip()
        if api_url:
            config['api_url'] = api_url
    elif config['llm'] == 'claude':
        print("\n    - Claude API 설정")
        model = input("      * 사용할 Claude 모델명 (기본값: claude-sonnet-4-6): ").strip()
        config['model'] = model if model else "claude-sonnet-4-6"

    save_config(config)
    print("==================================================\n")
    return config

def main():
    config = load_config()
    
    # --init 플래그가 있는 경우에만 대화형 설정 마법사 실행
    is_init = "--init" in sys.argv
    if is_init:
        run_wizard()
        sys.exit(0)
            
    parser = argparse.ArgumentParser(
        description="로컬 Git 저장소의 파일 구조와 커밋 로그를 분석하여 Markdown 위키 문서를 자동 생성합니다."
    )
    parser.add_argument(
        "--init",
        action="store_true",
        help="대화형 설정 마법사를 실행하여 .srdocs 파일을 생성합니다."
    )
    parser.add_argument(
        "--repo",
        default=None,
        help="분석할 로컬 Git 저장소 경로 (기본값: .srdocs 내의 repos 목록)"
    )
    default_output = "DEFAULT"
    parser.add_argument(
        "--output",
        default=config.get("output", default_output),
        help=f"생성할 마크다운 위키 파일 이름/경로 (기본값: {os.path.join(VAULT_BASE_DIR, '<project_name>')})"
    )
    parser.add_argument(
        "--link-type",
        choices=["abs", "rel"],
        default=config.get("link_type", "abs"),
        help="위키 문서 내 파일 링크 형식 (abs: 절대 경로 file:// 링크, rel: 상대 경로 링크) (기본값: abs)"
    )
    parser.add_argument(
        "--llm",
        choices=["gemini", "ollama", "claude", "none"],
        default=config.get("llm", "none"),
        help="LLM을 활용한 설명 및 릴리즈 요약 자동 생성 백엔드 선택 (기본값: none)"
    )
    parser.add_argument(
        "--api-key",
        default=config.get("api_key") or os.environ.get("GEMINI_API_KEY"),
        help="Gemini API 키 (기본값: config 파일 설정 또는 GEMINI_API_KEY 환경변수)"
    )
    parser.add_argument(
        "--model",
        default=config.get("model"),
        help="사용할 LLM 모델명 (Gemini 기본값: gemini-1.5-flash, Ollama 기본값: gemma4:e4b, Claude 기본값: claude-sonnet-4-6)"
    )
    parser.add_argument(
        "--api-url",
        default=config.get("api_url"),
        help="LLM API 주소 (Ollama, 기타 REST API 등) (기본값: Ollama는 http://localhost:11434/api/generate)"
    )
    parser.add_argument(
        "--ollama-url",
        default=None,
        help=argparse.SUPPRESS  # 하위 호환성 유지, 도움말에서는 숨김
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=500,
        help="분석할 최대 Git 커밋 개수 (기본값: 500)"
    )
    parser.add_argument(
        "--tree-depth",
        type=int,
        default=3,
        help="폴더 구조 다이어그램의 최대 깊이 (기본값: 3)"
    )
    parser.add_argument(
        "--lint",
        action="store_true",
        help="생성된 위키 폴더의 정합성(깨진 링크, 고아 파일 등)을 검사합니다."
    )
    parser.add_argument(
        "--query",
        help="프로젝트 소스 코드 및 Git 로그를 기반으로 자연어 질문에 답하고, 그 결과를 decisions/ 폴더에 위키 페이지로 저장합니다."
    )
    parser.add_argument(
        "--serve",
        action="store_true",
        help="로컬 웹 서버를 구동하여 웹 뷰어를 브라우저에서 실행합니다."
    )
    parser.add_argument(
        "--port",
        type=int,
        default=8000,
        help="로컬 웹 서버가 사용할 포트 번호 (기본값: 8000)"
    )
    
    args = parser.parse_args()
    
    # 웹 서버 구동은 분석 대상 루프를 돌기 전에 단 한 번만 실행합니다.
    if args.serve:
        web_dist_dir = get_resource_path("web/dist")
        print(f"📡 웹 뷰어 서버 구동 중: {VAULT_BASE_DIR} 포트: {args.port}")
        run_server(VAULT_BASE_DIR, web_dist_dir, port=args.port)
        sys.exit(0)
        
    # 하위 호환성: --ollama-url이 주어지면 --api-url로 사용
    api_url = args.api_url
    if args.ollama_url and not args.api_url:
        api_url = args.ollama_url
        
    # 대상 저장소 리스트 결정
    if args.repo:
        repos_config = [args.repo]
    else:
        repos_config = config.get("repos")
        if not repos_config:
            # 하위 호환성 (단일 repo 키만 존재 시)
            old_repo = config.get("repo")
            repos_config = [old_repo] if old_repo else ["."]
        elif isinstance(repos_config, str):
            repos_config = [repos_config]
            
    print(f"📋 총 {len(repos_config)}개의 저장소를 차례대로 빌드합니다.")
    
    for repo_path_raw in repos_config:
        repo_path = os.path.abspath(repo_path_raw)
        
        # Git 저장소 최상위 경로(Toplevel) 자동 교정 (dist 폴더 실행 등 대응)
        import subprocess
        try:
            if os.path.isdir(repo_path):
                res = subprocess.run(
                    ["git", "rev-parse", "--show-toplevel"],
                    cwd=repo_path,
                    capture_output=True,
                    text=True,
                    check=True
                )
                git_toplevel = res.stdout.strip()
                if git_toplevel and os.path.isdir(git_toplevel):
                    repo_path = git_toplevel
        except Exception:
            pass
            
        if not os.path.isdir(repo_path):
            print(f"⚠️ 경고: 지정한 경로가 디렉토리가 아닙니다. 건너뜁니다: {repo_path}")
            continue
            
        # 각 저장소별 개별 위키 출력 경로 설정
        repo_name = os.path.basename(repo_path)
        output_path = args.output
        if output_path == "DEFAULT":
            project_output_path = os.path.join(VAULT_BASE_DIR, repo_name)
        else:
            if output_path.endswith('.md'):
                dir_part, file_part = os.path.split(output_path)
                project_output_path = os.path.join(dir_part, f"{repo_name}_{file_part}")
            else:
                project_output_path = os.path.join(output_path, repo_name)
                
        # 린트 모드
        if args.lint:
            run_lint(repo_path, project_output_path)
            continue
            
        # 자연어 질의 모드
        if args.query:
            run_query(repo_path, project_output_path, args.query, args.llm, args.api_key, args.model, api_url)
            continue
            
        # 메인 분석 및 생성
        analyzer = GitAnalyzer(repo_path)
        if not analyzer.check_is_repo():
            print(f"⚠️ 경고: 지정한 경로가 Git 저장소가 아닙니다. 건너뜁니다: {repo_path}")
            continue
            
        print(f"\n🔍 저장소 분석 시작: {repo_path}")
        
        # Analyze
        metadata = analyzer.get_repo_metadata()
        print(f"   - 프로젝트 이름: {metadata['name']}")
        print(f"   - 프로젝트 타입: {metadata['type']}")
        
        print("📂 파일 스캔 중...")
        files, ext_counts = analyzer.scan_files()
        print(f"   - 총 스캔 파일: {len(files)} 개")
        
        print("🔨 Git 커밋 로그 수집 중...")
        commits = analyzer.get_git_log(limit=args.limit)
        print(f"   - 수집된 커밋: {len(commits)} 개")
        
        # Initialize cache
        from .cache import WikiCache
        cache = WikiCache(repo_path)
        
        # Group commits by tags or Year-Month if no tags exist
        tag_indices = []
        for idx, c in enumerate(commits):
            if c['tag']:
                tag_indices.append((idx, c['tag']))
        tag_indices_desc = sorted(tag_indices, key=lambda x: x[0], reverse=True)
        
        grouped_commits = defaultdict(list)
        if len(tag_indices) > 0:
            for idx, c in enumerate(commits):
                version = None
                for tag_idx, tag_name in tag_indices_desc:
                    if tag_idx <= idx:
                        version = tag_name
                        break
                if version is None:
                    version = "unreleased"
                grouped_commits[version].append(c)
        else:
            for c in commits:
                ym = c['date'][:7] if len(c['date']) >= 7 else "unreleased"
                grouped_commits[ym].append(c)
    
        # Load cached summaries first (allows reuse even without LLM option)
        llm_summaries = {}
        
        current_overview_key = cache.calculate_overview_key(metadata, files)
        cached_overview = cache.get_overview(current_overview_key)
        if cached_overview:
            llm_summaries['overview'] = cached_overview
            print("   - 프로젝트 개요 요약: 캐시 사용")
            
        for version, comms in grouped_commits.items():
            rel_key = cache.calculate_release_key(version, comms)
            cached_rel = cache.get_release_summary(rel_key)
            if cached_rel:
                llm_summaries[version] = cached_rel
                print(f"   - 버전 {version} 요약: 캐시 사용")
    
        # LLM summaries generation for missing/outdated cache
        if args.llm != "none":
            print(f"🤖 LLM 요약 진행 중 ({args.llm} 백엔드)...")
            
            # 공통 백엔드 파라미터
            backend_kwargs = {}
            if args.llm == "gemini":
                if not args.api_key:
                    print("경고: Gemini API 키가 제공되지 않아 LLM 요약을 건너뜁니다.")
                    backend_kwargs = None
                else:
                    backend_kwargs = {
                        "api_key": args.api_key,
                        "model": args.model,
                        "api_url": api_url
                    }
            elif args.llm == "ollama":
                backend_kwargs = {
                    "model": args.model,
                    "api_url": api_url
                }
            elif args.llm == "claude":
                backend_kwargs = {
                    "model": args.model
                }
            
            if backend_kwargs is not None:
                summarizer = LLMSummarizer(backend=args.llm, repo_path=repo_path, **backend_kwargs)
                # Check overview
                if not llm_summaries.get('overview'):
                    print("   - 프로젝트 개요 요약 생성 중...")
                    overview = summarizer.summarize_overview(metadata, files)
                    if overview:
                        llm_summaries['overview'] = overview
                        cache.set_overview(current_overview_key, overview)
                        cache.save()
                        
                # Check releases
                print("   - 버전별 릴리즈 내용 요약 생성 중...")
                for version, comms in grouped_commits.items():
                    rel_key = cache.calculate_release_key(version, comms)
                    if not llm_summaries.get(version):
                        print(f"     * 버전 {version} 요약 생성 중...")
                        rel_summary = summarizer.summarize_release(version, comms)
                        if rel_summary:
                            llm_summaries[version] = rel_summary
                            cache.set_release_summary(rel_key, rel_summary)
                            cache.save()
                        
        # Generate
        generator = WikiGenerator(
            metadata=metadata,
            files=files,
            ext_counts=ext_counts,
            commits=commits,
            repo_path=repo_path,
            link_type=args.link_type
        )
        generator.max_tree_depth = args.tree_depth
        
        if project_output_path.endswith('.md'):
            print("📝 단일 마크다운 위키 파일 작성 중...")
            wiki_content = generator.generate(llm_summary=llm_summaries if llm_summaries else None)
            try:
                with open(project_output_path, 'w', encoding='utf-8') as f:
                    f.write(wiki_content)
                print(f"🎉 단일 위키 생성이 완료되었습니다! 저장된 경로: {os.path.abspath(project_output_path)}")
            except Exception as e:
                print(f"오류: 위키 파일을 저장하지 못했습니다: {e}")
        else:
            print(f"📂 폴더 구조 개발 위키 작성 중... 디렉토리: {project_output_path}")
            try:
                generator.generate_directory(project_output_path, llm_summary=llm_summaries if llm_summaries else None)
                print(f"🎉 개발 위키 디렉토리가 성공적으로 구축되었습니다! 저장된 경로: {os.path.abspath(project_output_path)}")
            except Exception as e:
                print(f"오류: 위키 디렉토리를 구축하지 못했습니다: {e}")

def run_lint(repo_path, wiki_dir):
    import re
    print(f"🧹 Wiki 린트(상태 검사) 시작: {wiki_dir}")
    if not os.path.exists(wiki_dir):
        print("오류: 위키 디렉토리가 존재하지 않습니다. 먼저 위키를 생성해주세요.")
        return
        
    md_files = []
    for root, _, files in os.walk(wiki_dir):
        for f in files:
            if f.endswith('.md'):
                md_files.append(os.path.join(root, f))
                
    print(f"   - 스캔된 위키 마크다운 파일: {len(md_files)} 개")
    
    broken_links_count = 0
    orphan_files = set(os.path.abspath(f) for f in md_files)
    
    index_path = os.path.abspath(os.path.join(wiki_dir, 'index.md'))
    if index_path in orphan_files:
        orphan_files.remove(index_path)
        
    for md_file in md_files:
        try:
            with open(md_file, 'r', encoding='utf-8') as f:
                content = f.read()
                
            links = re.findall(r'\[([^\]]*)\]\(([^)]*)\)', content)
            for text, target in links:
                if target.startswith(('http://', 'https://', 'mailto:', 'file://')):
                    continue
                    
                target_clean = target.split('#')[0]
                if not target_clean:
                    continue
                    
                target_abs = os.path.abspath(os.path.join(os.path.dirname(md_file), target_clean))
                
                if not os.path.exists(target_abs):
                    print(f"   ⚠️ 깨진 링크 발견: [{os.path.basename(md_file)}] -> '{target}' (존재하지 않음)")
                    broken_links_count += 1
                else:
                    if target_abs in orphan_files:
                        orphan_files.remove(target_abs)
        except Exception as e:
            print(f"   ⚠️ 파일 읽기 실패: {md_file} ({e})")
            
    for orphan in orphan_files:
        rel_orphan = os.path.relpath(orphan, wiki_dir)
        print(f"   ⚠️ 고아 파일 발견: '{rel_orphan}' (어떤 위키 페이지에서도 링크되지 않음)")
        
    print(f"\n📊 린트 완료 결과:")
    print(f"   - 깨진 링크: {broken_links_count} 개")
    print(f"   - 고아 위키 파일: {len(orphan_files)} 개")
    if broken_links_count == 0 and len(orphan_files) == 0:
        print("   ✅ 위키 정합성이 완벽합니다!")

def run_query(repo_path, wiki_dir, query_str, llm_backend, api_key, model, api_url):
    import re
    import datetime
    
    if llm_backend == 'none':
        print("오류: 자연어 질문에 답하려면 --llm 옵션으로 백엔드(gemini, ollama, claude)를 지정해야 합니다.")
        sys.exit(1)
        
    print(f"🔍 Wiki 자연어 질의 시작: '{query_str}'")
    analyzer = GitAnalyzer(repo_path)
    metadata = analyzer.get_repo_metadata()
    
    print("   - 관련 코드 컨텍스트 검색 중...")
    words = [w for w in re.split(r'\s+', query_str) if len(w) > 1]
    context_results = []
    if words:
        context_results = analyzer.search_code(query_str, limit_files=3)
        if not context_results:
            context_results = analyzer.search_code(words[0], limit_files=3)
            
    print(f"   - 검색된 관련 파일: {len(context_results)} 개")
    
    print(f"🤖 LLM 답변 생성 중 ({llm_backend} 백엔드)...")
    summarizer = LLMSummarizer(backend=llm_backend, api_key=api_key, model=model, api_url=api_url, repo_path=repo_path)
    answer = summarizer.answer_query(query_str, metadata, context_results)
    
    if not answer:
        print("오류: LLM 답변을 오지 못했습니다.")
        return
        
    decisions_dir = os.path.join(wiki_dir, 'decisions')
    os.makedirs(decisions_dir, exist_ok=True)
    
    slug = query_str.lower().strip()
    slug = re.sub(r'[^\w\s-]', '', slug)
    slug = re.sub(r'[\s-]+', '_', slug)
    slug = slug[:50]
    
    decision_path = os.path.join(decisions_dir, f"{slug}.md")
    date_str = datetime.date.today().strftime("%Y-%m-%d")
    
    doc_content = f"""# 💡 의사결정 및 기술 탐색 기록: {query_str}

- **일자**: `{date_str}`
- **질의 내용**: {query_str}

---

## 📝 LLM 분석 및 답변

{answer}

---
*이 문서는 사용자의 질의를 기반으로 소스 코드 컨텍스트를 검색하여 LLM이 자동 생성한 분석 페이지입니다.*
"""
    
    try:
        with open(decision_path, 'w', encoding='utf-8') as f:
            f.write(doc_content)
        print(f"🎉 답변이 위키 페이지로 영구 저장되었습니다: decisions/{slug}.md")
    except Exception as e:
        print(f"오류: 답변 파일을 저장하지 못했습니다: {e}")
        return
        
    print("📝 위키 인덱스 재빌드 중...")
    files, ext_counts = analyzer.scan_files()
    commits = analyzer.get_git_log(limit=500)
    
    generator = WikiGenerator(
        metadata=metadata,
        files=files,
        ext_counts=ext_counts,
        commits=commits,
        repo_path=repo_path,
        link_type='rel'
    )
    
    from .cache import WikiCache
    cache = WikiCache(repo_path)
    llm_summaries = {}
    current_overview_key = cache.calculate_overview_key(metadata, files)
    cached_overview = cache.get_overview(current_overview_key)
    if cached_overview:
        llm_summaries['overview'] = cached_overview
        
    tag_indices = []
    for idx, c in enumerate(commits):
        if c['tag']:
            tag_indices.append((idx, c['tag']))
    tag_indices_desc = sorted(tag_indices, key=lambda x: x[0], reverse=True)
    
    grouped_commits = defaultdict(list)
    if len(tag_indices) > 0:
        for idx, c in enumerate(commits):
            version = None
            for tag_idx, tag_name in tag_indices_desc:
                if tag_idx <= idx:
                    version = tag_name
                    break
            if version is None:
                version = "unreleased"
            grouped_commits[version].append(c)
    else:
        for c in commits:
            ym = c['date'][:7] if len(c['date']) >= 7 else "unreleased"
            grouped_commits[ym].append(c)
        
    for version, comms in grouped_commits.items():
        rel_key = cache.calculate_release_key(version, comms)
        cached_rel = cache.get_release_summary(rel_key)
        if cached_rel:
            llm_summaries[version] = cached_rel
            
    try:
        generator.generate_directory(wiki_dir, llm_summary=llm_summaries)
        print("✅ 위키 인덱스 갱신 완료!")
    except Exception as e:
        print(f"경고: 위키 인덱스 갱신 실패: {e}")

if __name__ == '__main__':
    main()
