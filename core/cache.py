import os
import json
import hashlib

class WikiCache:
    def __init__(self, repo_path):
        self.repo_path = os.path.abspath(repo_path)
        
        # 실제 개발 코드가 있는 프로젝트 폴더에 캐시 파일을 저장하지 않고
        # 사용자 홈 디렉토리의 .cache/git-llm-wiki 폴더에 저장합니다.
        cache_dir = os.path.expanduser("~/.cache/git-llm-wiki")
            
        try:
            os.makedirs(cache_dir, exist_ok=True)
        except Exception as e:
            # 권한 문제 등으로 생성 불가한 경우 임시 디렉토리 사용
            import tempfile
            cache_dir = os.path.join(tempfile.gettempdir(), "git-llm-wiki-cache")
            os.makedirs(cache_dir, exist_ok=True)
            
        path_hash = hashlib.sha256(self.repo_path.encode("utf-8")).hexdigest()
        repo_name = os.path.basename(self.repo_path)
        if not repo_name:
            repo_name = "root"
            
        self.cache_path = os.path.join(cache_dir, f"{repo_name}_{path_hash}.json")
        self.data = {
            "overview": "",
            "overview_key": "",
            "releases": {}  # hash_key -> summary
        }
        self.load()
        
    def load(self):
        if os.path.exists(self.cache_path):
            try:
                with open(self.cache_path, "r", encoding="utf-8") as f:
                    self.data = json.load(f)
            except Exception as e:
                print(f"⚠️ 캐시 파일을 불러오는 중 오류 발생: {e}")
                
    def save(self):
        try:
            with open(self.cache_path, "w", encoding="utf-8") as f:
                json.dump(self.data, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"⚠️ 캐시 파일을 저장하는 중 오류 발생: {e}")

    def calculate_release_key(self, version_name, commits):
        # 커밋 해시들의 조합으로 고유한 해시 키 생성
        commit_hashes = "".join([c["hash"] for c in commits])
        key_src = f"{version_name}:{commit_hashes}"
        return hashlib.sha256(key_src.encode("utf-8")).hexdigest()

    def get_release_summary(self, key):
        return self.data.get("releases", {}).get(key)

    def set_release_summary(self, key, summary):
        if "releases" not in self.data:
            self.data["releases"] = {}
        self.data["releases"][key] = summary

    def calculate_overview_key(self, metadata, files_list):
        # 파일 경로 + 크기 조합으로 고유 키 생성 (파일 내용 변경도 감지)
        file_entries = "".join(
            f"{f['path']}:{f.get('size', 0)}"
            for f in sorted(files_list[:100], key=lambda x: x['path'])
        )
        key_src = f"{metadata['name']}:{metadata['type']}:{metadata['version']}:{file_entries}"
        return hashlib.sha256(key_src.encode("utf-8")).hexdigest()

    def get_overview(self, current_key):
        if self.data.get("overview_key") == current_key:
            return self.data.get("overview", "")
        return ""

    def set_overview(self, current_key, overview):
        self.data["overview_key"] = current_key
        self.data["overview"] = overview
