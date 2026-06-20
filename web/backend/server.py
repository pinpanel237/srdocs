import os
import sys
import http.server
import socketserver
import urllib.parse
import webbrowser

def get_resource_path(relative_path):
    try:
        # PyInstaller creates a temp folder and stores path in _MEIPASS
        base_path = sys._MEIPASS
    except Exception:
        # Fallback to the project root directory (three levels up: core/backend/server.py -> root)
        base_path = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    return os.path.join(base_path, relative_path)

class WikiHTTPRequestHandler(http.server.SimpleHTTPRequestHandler):
    def translate_path(self, path):
        # URL 디코딩
        parsed_path = urllib.parse.urlparse(self.path).path
        decoded_path = urllib.parse.unquote(parsed_path)
        
        # /vault/ 경로에 대한 요청은 실제 파일 시스템의 vault_dir 경로로 매핑
        if decoded_path.startswith("/vault/") or decoded_path == "/vault":
            relative_path = decoded_path[len("/vault/"):] if decoded_path.startswith("/vault/") else ""
            actual_path = os.path.join(self.server.vault_dir, relative_path)
            return os.path.abspath(actual_path)
            
        # 그 외의 모든 요청(HTML, JS, CSS 등 정적 웹 리소스)은 web/frontend/dist 폴더로 매핑
        relative_path = decoded_path.lstrip("/")
        actual_path = os.path.join(self.server.web_dist_dir, relative_path)
        
        return os.path.abspath(actual_path)

    def log_message(self, format, *args):
        # 불필요한 콘솔 로그 생략
        pass

class WikiHTTPServer(socketserver.TCPServer):
    allow_reuse_address = True
    def __init__(self, server_address, RequestHandlerClass, vault_dir, web_dist_dir):
        self.vault_dir = os.path.abspath(vault_dir)
        self.web_dist_dir = os.path.abspath(web_dist_dir)
        super().__init__(server_address, RequestHandlerClass)

def run_server(vault_dir, web_dist_dir, port=8000):
    server_address = ("", port)
    
    if not os.path.isdir(web_dist_dir):
        print(f"⚠️ 오류: 웹 뷰어 빌드 디렉토리를 찾을 수 없습니다: {web_dist_dir}")
        print("💡 정적 웹 리소스가 빌드되어 있는지 확인하세요 (npm run build).")
        sys.exit(1)
        
    if not os.path.isdir(vault_dir):
        print(f"⚠️ 오류: 위키 데이터 디렉토리를 찾을 수 없습니다: {vault_dir}")
        print("💡 먼저 위키 문서를 빌드해 주세요 (예: python3 run.py).")
        sys.exit(1)
        
    print(f"🌐 로컬 웹 서버 시작 중...")
    print(f"   - 웹 리소스 경로: {web_dist_dir}")
    print(f"   - 위키 데이터 경로: {vault_dir}")
    print(f"   - 주소: http://localhost:{port}")
    
    try:
        server = WikiHTTPServer(server_address, WikiHTTPRequestHandler, vault_dir, web_dist_dir)
    except Exception as e:
        print(f"❌ 오류: 서버를 시작하지 못했습니다 (포트 {port}가 사용 중일 수 있습니다): {e}")
        sys.exit(1)
        
    try:
        webbrowser.open(f"http://localhost:{port}")
    except Exception as e:
        print(f"⚠️ 브라우저를 자동으로 열지 못했습니다: {e}")
        
    print("💡 서버 작동 중... 종료하려면 Ctrl+C를 누르세요.")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n👋 서버를 종료합니다.")
        server.server_close()
