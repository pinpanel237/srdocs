import os
import subprocess
import re
import json
from collections import defaultdict

def load_gitignore(repo_path):
    patterns = ['.git/', '.git_wiki_cache.json']
    gitignore_path = os.path.join(repo_path, '.gitignore')
    if os.path.exists(gitignore_path):
        try:
            with open(gitignore_path, 'r', encoding='utf-8') as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith('#'):
                        patterns.append(line)
        except Exception:
            pass
    return patterns

def is_ignored(path, ignore_patterns):
    normalized = path.replace('\\', '/')
    for pattern in ignore_patterns:
        pat = pattern.strip()
        if pat.startswith('/'):
            pat = pat[1:]
        
        # Simple glob translation
        regex_pat = re.escape(pat)
        regex_pat = regex_pat.replace(r'\*', '.*')
        regex_pat = regex_pat.replace(r'\?', '.')
        
        if pat.endswith('/'):
            # matches directory prefix
            if normalized.startswith(pat) or ('/' + pat) in normalized:
                return True
        else:
            if re.search(r'^' + regex_pat + r'$', normalized) or \
               re.search(r'/' + regex_pat + r'$', normalized) or \
               re.search(r'^' + regex_pat + r'/', normalized) or \
               re.search(r'/' + regex_pat + r'/', normalized):
                return True
    return False

class GitAnalyzer:
    def __init__(self, repo_path):
        self.repo_path = os.path.abspath(repo_path)
        
    def check_is_repo(self):
        try:
            res = subprocess.run(
                ["git", "rev-parse", "--is-inside-work-tree"],
                cwd=self.repo_path,
                capture_output=True,
                text=True,
                check=True
            )
            return res.stdout.strip() == "true"
        except Exception:
            return False
            
    def get_repo_metadata(self):
        # Scan for project files to find name, version, description
        metadata = {
            'name': os.path.basename(self.repo_path),
            'version': 'unknown',
            'type': 'unknown',
            'dependencies': [],
            'readme': ''
        }
        
        # Read README.md
        for name in ['README.md', 'README.txt', 'readme.md']:
            readme_path = os.path.join(self.repo_path, name)
            if os.path.exists(readme_path):
                try:
                    with open(readme_path, 'r', encoding='utf-8') as f:
                        content = f.read()
                        metadata['readme'] = content
                        lines = [line.strip() for line in content.split('\n') if line.strip()]
                        for line in lines:
                            if line.startswith('#'):
                                continue
                            metadata['description'] = line
                            break
                    break
                except Exception:
                    pass
                    
        # Project type detection
        if os.path.exists(os.path.join(self.repo_path, 'Cargo.toml')):
            metadata['type'] = 'Rust'
            try:
                with open(os.path.join(self.repo_path, 'Cargo.toml'), 'r', encoding='utf-8') as f:
                    content = f.read()
                    name_match = re.search(r'\bname\s*=\s*"([^"]+)"', content)
                    ver_match = re.search(r'\bversion\s*=\s*"([^"]+)"', content)
                    if name_match: metadata['name'] = name_match.group(1)
                    if ver_match: metadata['version'] = ver_match.group(1)
            except Exception:
                pass
        elif os.path.exists(os.path.join(self.repo_path, 'package.json')):
            metadata['type'] = 'Node.js'
            try:
                with open(os.path.join(self.repo_path, 'package.json'), 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    metadata['name'] = data.get('name', metadata['name'])
                    metadata['version'] = data.get('version', 'unknown')
                    deps = list(data.get('dependencies', {}).keys()) + list(data.get('devDependencies', {}).keys())
                    metadata['dependencies'] = deps
            except Exception:
                pass
        elif os.path.exists(os.path.join(self.repo_path, 'setup.py')) or os.path.exists(os.path.join(self.repo_path, 'pyproject.toml')):
            metadata['type'] = 'Python'
            if os.path.exists(os.path.join(self.repo_path, 'setup.py')):
                try:
                    with open(os.path.join(self.repo_path, 'setup.py'), 'r', encoding='utf-8') as f:
                        content = f.read()
                        name_match = re.search(r'\bname\s*=\s*[\'"]([^\'"]+)[\'"]', content)
                        ver_match = re.search(r'\bversion\s*=\s*[\'"]([^\'"]+)[\'"]', content)
                        if name_match: metadata['name'] = name_match.group(1)
                        if ver_match: metadata['version'] = ver_match.group(1)
                except Exception:
                    pass
        elif os.path.exists(os.path.join(self.repo_path, 'pom.xml')):
            metadata['type'] = 'Java (Maven)'
            try:
                with open(os.path.join(self.repo_path, 'pom.xml'), 'r', encoding='utf-8') as f:
                    content = f.read()
                    name_match = re.search(r'<artifactId>([^<]+)</artifactId>', content)
                    ver_match = re.search(r'<version>([^<]+)</version>', content)
                    if name_match: metadata['name'] = name_match.group(1).strip()
                    if ver_match: metadata['version'] = ver_match.group(1).strip()
                    
                    # Basic extraction of dependencies
                    deps = re.findall(r'<artifactId>([^<]+)</artifactId>', content)
                    deps = [d.strip() for d in deps if d.strip() != metadata['name']]
                    metadata['dependencies'] = sorted(list(set(deps)))[:15]
            except Exception:
                pass
        elif os.path.exists(os.path.join(self.repo_path, 'build.gradle')) or os.path.exists(os.path.join(self.repo_path, 'build.gradle.kts')):
            metadata['type'] = 'Java (Gradle)'
            # Try to find version
            gradle_file = 'build.gradle' if os.path.exists(os.path.join(self.repo_path, 'build.gradle')) else 'build.gradle.kts'
            try:
                with open(os.path.join(self.repo_path, gradle_file), 'r', encoding='utf-8') as f:
                    content = f.read()
                    ver_match = re.search(r'\bversion\s*=\s*[\'"]([^\'"]+)[\'"]', content)
                    if ver_match: metadata['version'] = ver_match.group(1).strip()
            except Exception:
                pass
        return metadata

    def scan_files(self):
        ignore_patterns = load_gitignore(self.repo_path)
        file_list = []
        ext_counts = defaultdict(int)
        
        for root, dirs, files in os.walk(self.repo_path):
            rel_root = os.path.relpath(root, self.repo_path)
            if rel_root == '.':
                rel_root = ''
            
            filtered_dirs = []
            for d in dirs:
                dir_rel_path = os.path.join(rel_root, d) if rel_root else d
                if not is_ignored(dir_rel_path + '/', ignore_patterns):
                    filtered_dirs.append(d)
            dirs[:] = filtered_dirs
            
            for f in files:
                file_rel_path = os.path.join(rel_root, f) if rel_root else f
                if is_ignored(file_rel_path, ignore_patterns):
                    continue
                
                _, ext = os.path.splitext(f)
                ext = ext.lower()
                ext_counts[ext] += 1
                
                try:
                    size = os.path.getsize(os.path.join(root, f))
                except OSError:
                    continue
                
                file_list.append({
                    'path': file_rel_path,
                    'size': size,
                    'ext': ext
                })
                
        return file_list, ext_counts

    def get_git_log(self, limit=500):
        cmd = [
            "git", "log",
            f"-n {limit}" if limit else "",
            "--pretty=format:COMMIT:%h|%an|%ad|%s|%d",
            "--date=short",
            "--numstat"
        ]
        cmd = [c for c in cmd if c]
        
        try:
            res = subprocess.run(
                cmd,
                cwd=self.repo_path,
                capture_output=True,
                text=True,
                check=True,
                encoding='utf-8',
                errors='replace'
            )
            return self._parse_git_log(res.stdout)
        except Exception as e:
            print(f"Error running git log: {e}")
            return []

    def _parse_git_log(self, log_output):
        commits = []
        current_commit = None
        
        for line in log_output.split('\n'):
            line = line.strip()
            if line.startswith("COMMIT:"):
                if current_commit:
                    commits.append(current_commit)
                parts = line[7:].split('|')
                h = parts[0]
                author = parts[1]
                date = parts[2]
                subject = parts[3]
                decor = parts[4] if len(parts) > 4 else ""
                
                tag = None
                tag_match = re.search(r'tag:\s*(v[0-9a-zA-Z\.\-]+)', decor)
                if tag_match:
                    tag = tag_match.group(1)
                    
                current_commit = {
                    'hash': h,
                    'author': author,
                    'date': date,
                    'subject': subject,
                    'tag': tag,
                    'decor': decor,
                    'files': []
                }
            elif line == "":
                continue
            else:
                if current_commit:
                    parts = line.split('\t')
                    if len(parts) == 3:
                        added = parts[0]
                        deleted = parts[1]
                        filepath = parts[2]
                        added_val = int(added) if added.isdigit() else 0
                        deleted_val = int(deleted) if deleted.isdigit() else 0
                        current_commit['files'].append({
                            'path': filepath,
                            'added': added_val,
                            'deleted': deleted_val
                        })
                        
        if current_commit:
            commits.append(current_commit)
            
        return commits

    def search_code(self, query_str, limit_files=3, max_chars=1500):
        results = []
        ignore_patterns = load_gitignore(self.repo_path)
        pattern = re.compile(re.escape(query_str), re.IGNORECASE)
        
        count = 0
        for root, dirs, files in os.walk(self.repo_path):
            rel_root = os.path.relpath(root, self.repo_path)
            if rel_root == '.': rel_root = ''
            
            dirs[:] = [d for d in dirs if not is_ignored(os.path.join(rel_root, d) if rel_root else d, ignore_patterns)]
            
            for f in files:
                file_rel_path = os.path.join(rel_root, f) if rel_root else f
                if is_ignored(file_rel_path, ignore_patterns):
                    continue
                    
                _, ext = os.path.splitext(f)
                if ext.lower() in ['.png', '.jpg', '.zip', '.lock', '.exe', '.pdf', '.tar', '.gz']:
                    continue
                     
                file_abs_path = os.path.join(root, f)
                try:
                    with open(file_abs_path, 'r', encoding='utf-8', errors='ignore') as file_obj:
                        content = file_obj.read()
                        if pattern.search(content):
                            match_idx = content.lower().find(query_str.lower())
                            start = max(0, match_idx - 300)
                            end = min(len(content), match_idx + 1000)
                            snippet = content[start:end]
                            results.append({
                                'path': file_rel_path,
                                'snippet': snippet
                            })
                            count += 1
                            if count >= limit_files:
                                return results
                except Exception:
                    pass
        return results
