import os
import urllib.parse
import json
from collections import defaultdict

class WikiGenerator:
    def __init__(self, metadata, files, ext_counts, commits, repo_path, link_type='abs'):
        self.metadata = metadata
        self.files = files
        self.ext_counts = ext_counts
        self.commits = commits
        self.repo_path = os.path.abspath(repo_path)
        self.link_type = link_type
        self.max_tree_depth = 3

    def get_file_link(self, path):
        if self.link_type == 'abs':
            abs_path = os.path.join(self.repo_path, path)
            return f"[{path}](file://{abs_path})"
        else:
            rel_path = urllib.parse.quote(path.replace('\\', '/'))
            return f"[{path}]({rel_path})"

    def generate(self, llm_summary=None):
        md = []
        md.append(f"# 📖 {self.metadata['name']} 프로젝트 분석 위키 (Wiki)")
        
        # Project Type Badges
        badges = []
        if self.metadata['type'] != 'unknown':
            badges.append(f"![Type](https://img.shields.io/badge/Project--Type-{self.metadata['type']}-blue)")
        if self.metadata['version'] != 'unknown':
            badges.append(f"![Version](https://img.shields.io/badge/Version-{self.metadata['version']}-green)")
        badges.append(f"![Files](https://img.shields.io/badge/Files-{len(self.files)}-orange)")
        badges.append(f"![Commits](https://img.shields.io/badge/Commits-{len(self.commits)}-purple)")
        
        if badges:
            md.append(" ".join(badges) + "\n")
            
        md.append("> [!NOTE]")
        md.append(f"> 이 문서는 `{self.metadata['name']}` 프로젝트의 아키텍처, 구성 파일, 그리고 Git 커밋 히스토리를 정밀 분석하여 자동으로 생성된 개발 위키입니다.\n")
        
        md.append("---")
        
        # 1. Project Overview
        md.append("\n## 1. 프로젝트 개요")
        if llm_summary and 'overview' in llm_summary:
            md.append(llm_summary['overview'])
        elif 'description' in self.metadata and self.metadata['description']:
            md.append(self.metadata['description'])
        else:
            md.append(f"`{self.metadata['name']}` 프로젝트는 `{self.metadata['type']}` 기반 프로젝트입니다.")
            
        if self.metadata.get('dependencies'):
            md.append("\n**주요 의존성 (Dependencies):**")
            deps_list = ", ".join([f"`{d}`" for d in self.metadata['dependencies']])
            md.append(f"- {deps_list}")

        # 2. Directory Structure
        md.append("\n## 2. 프로젝트 폴더 구조")
        dir_tree = self._build_dir_tree()
        md.append("```")
        md.append(dir_tree)
        md.append("```")

        # 3. Codebase Modification Frequency Analysis
        md.append("\n## 3. 코드베이스 변경 및 빈도 분석")
        
        file_change_counts = defaultdict(int)
        module_change_counts = defaultdict(int)
        author_commit_counts = defaultdict(int)
        
        for c in self.commits:
            author_commit_counts[c['author']] += 1
            for f in c['files']:
                path = f['path']
                file_change_counts[path] += 1
                
                parts = path.replace('\\', '/').split('/')
                module = parts[0] if len(parts) > 1 else 'root'
                module_change_counts[module] += 1
                
        md.append("\n### 🔝 가장 자주 수정된 파일 Top 10")
        md.append("| 파일 경로 | 변경 횟수 | 바로가기 |")
        md.append("|---|---|---|")
        sorted_files = sorted(file_change_counts.items(), key=lambda x: x[1], reverse=True)[:10]
        for path, count in sorted_files:
            md.append(f"| `{path}` | {count} 회 | {self.get_file_link(path)} |")
            
        md.append("\n### 📊 컴포넌트(디렉토리)별 수정 빈도")
        md.append("| 디렉토리 / 컴포넌트 | 변경 횟수 |")
        md.append("|---|---|")
        sorted_modules = sorted(module_change_counts.items(), key=lambda x: x[1], reverse=True)
        for mod, count in sorted_modules:
            md.append(f"| `{mod}` | {count} 회 |")
            
        md.append("\n### 👥 개발자 기여도 (커밋 기준)")
        md.append("| 개발자 이름 | 커밋 수 | 비율 |")
        md.append("|---|---|---|")
        total_commits = len(self.commits)
        if total_commits > 0:
            sorted_authors = sorted(author_commit_counts.items(), key=lambda x: x[1], reverse=True)
            for author, count in sorted_authors:
                pct = (count / total_commits) * 100
                md.append(f"| `{author}` | {count} 개 | {pct:.1f}% |")
        else:
            md.append("| - | 0 | 0% |")

        # 4. Git Commit History (grouped by tags)
        md.append("\n## 4. Git 커밋 히스토리 및 버전별 세부 분석")
        
        tag_indices = []
        for idx, c in enumerate(self.commits):
            if c['tag']:
                tag_indices.append((idx, c['tag']))
                
        tag_indices.sort(key=lambda x: x[0])
        tag_indices_desc = sorted(tag_indices, key=lambda x: x[0], reverse=True)
        
        grouped_commits = defaultdict(list)
        for idx, c in enumerate(self.commits):
            version = None
            for tag_idx, tag_name in tag_indices_desc:
                if tag_idx <= idx:
                    version = tag_name
                    break
            if version is None:
                version = "unreleased"
            grouped_commits[version].append(c)
            
        versions_order = [t[1] for t in tag_indices]
        if "unreleased" in grouped_commits:
            versions_order.insert(0, "unreleased")
            
        for v in grouped_commits:
            if v not in versions_order:
                versions_order.append(v)
                
        for version in versions_order:
            comms = grouped_commits[version]
            if not comms:
                continue
            
            dates = [c['date'] for c in comms]
            start_date = min(dates) if dates else ""
            end_date = max(dates) if dates else ""
            
            md.append(f"\n### 🏷️ Version: {version}")
            md.append(f"- **활동 기간**: `{start_date}` ~ `{end_date}`")
            md.append(f"- **커밋 수**: `{len(comms)}` 개")
            
            if llm_summary and version in llm_summary:
                md.append(f"\n**릴리즈 요약:**\n{llm_summary[version]}")
                
            md.append("\n#### 🔨 세부 커밋 내역")
            md.append("<details>")
            md.append("<summary>커밋 로그 상세 보기 (클릭)</summary>\n")
            md.append("| 커밋 | 개발자 | 날짜 | 작업 내용 |")
            md.append("|---|---|---|---|")
            for c in comms:
                md.append(f"| `{c['hash']}` | `{c['author']}` | `{c['date']}` | {c['subject']} |")
            md.append("\n</details>")
            
            changed_files = set()
            for c in comms:
                for f in c['files']:
                    changed_files.add(f['path'])
                    
            md.append("\n#### 📂 주요 수정 파일 목록")
            md.append("<details>")
            md.append("<summary>수정 파일 목록 보기 (클릭)</summary>\n")
            for f in sorted(changed_files):
                md.append(f"- {self.get_file_link(f)}")
            md.append("\n</details>\n")
            md.append("---")
            
        return "\n".join(md)

    def _build_dir_tree(self):
        paths = [f['path'] for f in self.files]
        tree = {}
        for path in paths:
            parts = path.replace('\\', '/').split('/')
            curr = tree
            for part in parts:
                if part not in curr:
                    curr[part] = {}
                curr = curr[part]
                
        lines = [self.metadata['name'] + "/"]
        max_depth = getattr(self, 'max_tree_depth', 3)
        self._format_tree_node(tree, "", lines, depth=0, max_depth=max_depth)
        return "\n".join(lines)

    def _format_tree_node(self, node, prefix, lines, depth=0, max_depth=3):
        if depth >= max_depth:
            if node:
                lines.append(prefix + "└── ... (하위 디렉토리 생략)")
            return
            
        keys = sorted(node.keys())
        for i, key in enumerate(keys):
            is_last = (i == len(keys) - 1)
            char = "└── " if is_last else "├── "
            is_dir = len(node[key]) > 0
            name = key + "/" if is_dir else key
            lines.append(prefix + char + name)
            if is_dir:
                next_prefix = prefix + ("    " if is_last else "│   ")
                self._format_tree_node(node[key], next_prefix, lines, depth + 1, max_depth)

    def generate_directory(self, output_dir, llm_summary=None):
        os.makedirs(output_dir, exist_ok=True)
        os.makedirs(os.path.join(output_dir, 'versions'), exist_ok=True)
        os.makedirs(os.path.join(output_dir, 'components'), exist_ok=True)
        os.makedirs(os.path.join(output_dir, 'decisions'), exist_ok=True)
        
        # 1. Write overview.md
        overview_path = os.path.join(output_dir, 'overview.md')
        overview_content = self.generate_overview_content(llm_summary)
        with open(overview_path, 'w', encoding='utf-8') as f:
            f.write(overview_content)
            
        # 2. Write versions/
        versions_order = self.generate_version_files(output_dir, llm_summary)
        
        # 3. Write components/
        components_list = self.generate_component_files(output_dir)
        
        # 4. Write log.md
        log_path = os.path.join(output_dir, 'log.md')
        log_content = self.generate_log_content(versions_order)
        with open(log_path, 'w', encoding='utf-8') as f:
            f.write(log_content)
            
        # 5. Write index.md
        index_path = os.path.join(output_dir, 'index.md')
        index_content = self.generate_index_content(versions_order, components_list, output_dir)
        with open(index_path, 'w', encoding='utf-8') as f:
            f.write(index_content)

        # 6. Collect decisions and generate vault_meta.json
        decisions_list = []
        decisions_dir = os.path.join(output_dir, 'decisions')
        if os.path.exists(decisions_dir):
            for filename in sorted(os.listdir(decisions_dir)):
                if filename.endswith('.md'):
                    decisions_list.append(filename[:-3])

        meta = {
            "projectName": self.metadata.get('name', 'Unknown'),
            "projectType": self.metadata.get('type', 'Unknown'),
            "version": self.metadata.get('version', 'Unknown'),
            "overviewFile": "overview.md",
            "logFile": "log.md",
            "indexFile": "index.md",
            "versions": versions_order,
            "components": components_list,
            "decisions": decisions_list
        }
        
        meta_path = os.path.join(output_dir, 'vault_meta.json')
        with open(meta_path, 'w', encoding='utf-8') as f:
            json.dump(meta, f, ensure_ascii=False, indent=2)

        # 7. Update projects.json in the parent directory (docs/)
        parent_dir = os.path.dirname(os.path.abspath(output_dir))
        if os.path.exists(parent_dir):
            try:
                projects = []
                for name in os.listdir(parent_dir):
                    sub_path = os.path.join(parent_dir, name)
                    if os.path.isdir(sub_path) and os.path.exists(os.path.join(sub_path, 'vault_meta.json')):
                        projects.append(name)
                
                projects_json_path = os.path.join(parent_dir, 'projects.json')
                with open(projects_json_path, 'w', encoding='utf-8') as f:
                    json.dump(sorted(projects), f, ensure_ascii=False, indent=2)
            except Exception as e:
                pass
            
    def generate_overview_content(self, llm_summary):
        md = []
        md.append(f"# 📖 {self.metadata['name']} 프로젝트 개요")
        md.append(f"![Type](https://img.shields.io/badge/Project--Type-{self.metadata['type']}-blue) ![Version](https://img.shields.io/badge/Version-{self.metadata['version']}-green)")
        md.append("\n## 1. 아키텍처 및 상세 소개")
        if llm_summary and 'overview' in llm_summary:
            md.append(llm_summary['overview'])
        elif 'description' in self.metadata and self.metadata['description']:
            md.append(self.metadata['description'])
        else:
            md.append(f"`{self.metadata['name']}` 프로젝트는 `{self.metadata['type']}` 기반 프로젝트입니다.")
            
        if self.metadata.get('dependencies'):
            md.append("\n**주요 의존성 (Dependencies):**")
            deps_list = ", ".join([f"`{d}`" for d in self.metadata['dependencies']])
            md.append(f"- {deps_list}")

        # Directory structure
        md.append("\n## 2. 프로젝트 폴더 구조")
        dir_tree = self._build_dir_tree()
        md.append("```")
        md.append(dir_tree)
        md.append("```")
        return "\n".join(md)

    def generate_version_files(self, output_dir, llm_summary):
        tag_indices = []
        for idx, c in enumerate(self.commits):
            if c['tag']:
                tag_indices.append((idx, c['tag']))
        tag_indices.sort(key=lambda x: x[0])
        tag_indices_desc = sorted(tag_indices, key=lambda x: x[0], reverse=True)
        
        grouped_commits = defaultdict(list)
        versions_order = []
        
        if len(tag_indices) > 0:
            for idx, c in enumerate(self.commits):
                version = None
                for tag_idx, tag_name in tag_indices_desc:
                    if tag_idx <= idx:
                        version = tag_name
                        break
                if version is None:
                    version = "unreleased"
                grouped_commits[version].append(c)
                
            versions_order = [t[1] for t in tag_indices]
            if "unreleased" in grouped_commits:
                versions_order.insert(0, "unreleased")
            for v in grouped_commits:
                if v not in versions_order:
                    versions_order.append(v)
        else:
            for c in self.commits:
                ym = c['date'][:7] if len(c['date']) >= 7 else "unreleased"
                grouped_commits[ym].append(c)
            versions_order = sorted(grouped_commits.keys(), reverse=True)
                
        # Write files incrementally
        for version in versions_order:
            comms = grouped_commits[version]
            if not comms:
                continue
                
            version_file_path = os.path.join(output_dir, 'versions', f"{version}.md")
            
            dates = [c['date'] for c in comms]
            start_date = min(dates) if dates else ""
            end_date = max(dates) if dates else ""
            
            md = []
            md.append(f"# 🏷️ Version: {version}")
            md.append(f"- **활동 기간**: `{start_date}` ~ `{end_date}`")
            md.append(f"- **커밋 수**: `{len(comms)}` 개")
            
            if llm_summary and version in llm_summary:
                md.append(f"\n## 📝 릴리즈 요약\n{llm_summary[version]}")
                
            md.append("\n## 🔨 세부 커밋 내역")
            md.append("<details>")
            md.append("<summary>커밋 로그 상세 보기 (클릭)</summary>\n")
            md.append("| 커밋 | 개발자 | 날짜 | 작업 내용 |")
            md.append("|---|---|---|---|")
            for c in comms:
                md.append(f"| `{c['hash']}` | `{c['author']}` | `{c['date']}` | {c['subject']} |")
            md.append("\n</details>")
            
            changed_files = set()
            for c in comms:
                for f in c['files']:
                    changed_files.add(f['path'])
                    
            md.append("\n## 📂 주요 수정 파일 목록")
            md.append("<details>")
            md.append("<summary>수정 파일 목록 보기 (클릭)</summary>\n")
            for f in sorted(changed_files):
                md.append(f"- {self.get_file_link(f)}")
            md.append("\n</details>")
            
            with open(version_file_path, 'w', encoding='utf-8') as f:
                f.write("\n".join(md))
                
        return versions_order

    def generate_component_files(self, output_dir):
        file_change_counts = defaultdict(int)
        module_files = defaultdict(list)
        
        for c in self.commits:
            for f in c['files']:
                path = f['path']
                file_change_counts[path] += 1
                
        for f in self.files:
            path = f['path']
            parts = path.replace('\\', '/').split('/')
            module = parts[0] if len(parts) > 1 else 'root'
            module_files[module].append(f)
            
        components_list = sorted(module_files.keys())
        
        for comp in components_list:
            comp_file_path = os.path.join(output_dir, 'components', f"{comp}.md")
            files_in_comp = module_files[comp]
            
            md = []
            md.append(f"# 🧩 컴포넌트: {comp}")
            md.append(f"이 디렉토리에는 총 `{len(files_in_comp)}`개의 활성 소스 파일이 존재합니다.\n")
            
            # Group files by directory
            dir_groups = defaultdict(list)
            for f in files_in_comp:
                dir_path = os.path.dirname(f['path']).replace('\\', '/')
                if not dir_path:
                    dir_path = 'root'
                dir_groups[dir_path].append(f)
                
            # If the component is small, render as one simple table
            if len(files_in_comp) <= 20:
                md.append("## 📂 소스 파일 및 변경 빈도 목록")
                md.append("| 파일 경로 | 크기 (Bytes) | Git 변경 빈도 | 바로가기 |")
                md.append("|---|---|---|---|")
                sorted_comp_files = sorted(files_in_comp, key=lambda x: file_change_counts[x['path']], reverse=True)
                for f in sorted_comp_files:
                    path = f['path']
                    size = f['size']
                    count = file_change_counts[path]
                    md.append(f"| `{path}` | {size:,} | {count} 회 | {self.get_file_link(path)} |")
            else:
                # Group and use folding
                md.append("## 📂 디렉토리별 소스 파일 목록 (아코디언 접기)")
                for dir_path in sorted(dir_groups.keys()):
                    dir_files = dir_groups[dir_path]
                    md.append(f"\n### 📁 {dir_path} ({len(dir_files)}개 파일)")
                    md.append("<details>")
                    md.append(f"<summary>파일 목록 보기 (클릭하여 열기)</summary>\n")
                    md.append("| 파일 경로 | 크기 (Bytes) | Git 변경 빈도 | 바로가기 |")
                    md.append("|---|---|---|---|")
                    sorted_dir_files = sorted(dir_files, key=lambda x: file_change_counts[x['path']], reverse=True)
                    for f in sorted_dir_files:
                        path = f['path']
                        size = f['size']
                        count = file_change_counts[path]
                        md.append(f"| `{path}` | {size:,} | {count} 회 | {self.get_file_link(path)} |")
                    md.append("\n</details>")
                    
            with open(comp_file_path, 'w', encoding='utf-8') as f:
                f.write("\n".join(md))
                
        return components_list

    def generate_log_content(self, versions_order):
        md = []
        md.append("# 📜 Chronological Release Log")
        md.append("> 프로젝트 변경 사항의 역순 연대기 로그 문서입니다. 간단한 grep 명령으로도 히스토리를 파싱할 수 있는 형식으로 구성되어 있습니다.\n")
        
        tag_indices = []
        for idx, c in enumerate(self.commits):
            if c['tag']:
                tag_indices.append((idx, c['tag']))
        tag_indices_desc = sorted(tag_indices, key=lambda x: x[0], reverse=True)
        
        grouped_commits = defaultdict(list)
        for idx, c in enumerate(self.commits):
            version = None
            for tag_idx, tag_name in tag_indices_desc:
                if tag_idx <= idx:
                    version = tag_name
                    break
            if version is None:
                version = "unreleased"
            grouped_commits[version].append(c)
            
        for version in versions_order:
            comms = grouped_commits[version]
            if not comms:
                continue
            dates = [c['date'] for c in comms]
            end_date = max(dates) if dates else "unknown"
            
            md.append(f"## [{end_date}] release | Version {version}")
            md.append(f"- **커밋 개수**: {len(comms)}개")
            md.append(f"- **최근 커밋**: `{comms[0]['subject']}` (by {comms[0]['author']})")
            md.append("")
            
        return "\n".join(md)

    def generate_index_content(self, versions_order, components_list, output_dir):
        md = []
        md.append(f"# 📖 {self.metadata['name']} 개발 위키 홈 (Home)")
        md.append(f"> `{self.metadata['name']}` 프로젝트에 관한 정보 분석 및 Git 커밋 히스토리를 바탕으로 LLM이 구축한 로컬 위키 포털 페이지입니다.\n")
        md.append("---")
        
        md.append("\n## 🧭 네비게이션 가이드")
        md.append(f"- **[프로젝트 상세 구조 및 아키텍처 개요](./overview.md)**")
        md.append(f"- **[역순 연대기 릴리즈 로그 (Release Log)](./log.md)**")
        
        md.append("\n## 🏷️ 버전별 릴리즈 이력 (Versions)")
        md.append("| 버전 태그 | 상세 내역 바로가기 |")
        md.append("|---|---|")
        for version in versions_order:
            md.append(f"| `{version}` | [versions/{version}.md](./versions/{version}.md) |")
            
        md.append("\n## 🧩 디렉토리 컴포넌트 목록 (Components)")
        md.append("| 컴포넌트 이름 | 구성 파일 목록 바로가기 |")
        md.append("|---|---|")
        for comp in components_list:
            md.append(f"| `{comp}` | [components/{comp}.md](./components/{comp}.md) |")
            
        decisions_dir = os.path.join(output_dir, 'decisions')
        dec_files = []
        if os.path.exists(decisions_dir):
            for f in os.listdir(decisions_dir):
                if f.endswith('.md'):
                    dec_files.append(f)
                    
        if dec_files:
            md.append("\n## 💡 의사결정 및 기술 탐색 기록 (Decisions)")
            md.append("| 질의 기록 및 탐색 문서 | 바로가기 |")
            md.append("|---|---|")
            for f in sorted(dec_files):
                title = f.replace('.md', '').replace('_', ' ').title()
                md.append(f"| {title} | [decisions/{f}](./decisions/{f}) |")
                
        return "\n".join(md)
