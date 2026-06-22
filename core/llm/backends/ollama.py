import urllib.request
import urllib.error
import json

from ..base import LLMBackend


class OllamaBackend(LLMBackend):
    """Ollama REST API 백엔드"""

    def __init__(self, model: str = "gemma4:e4b", api_url: str = "http://localhost:11434/api/generate"):
        """
        Ollama 백엔드 초기화
        
        Args:
            model: 사용할 모델명 (기본값: gemma4:e4b)
            api_url: Ollama API 주소 (기본값: http://localhost:11434/api/generate)
        """
        self.model = model
        self.api_url = api_url

    def call(self, prompt: str) -> str:
        """Ollama API를 호출하여 프롬프트 처리"""
        url = self.api_url
        data = {
            "model": self.model,
            "prompt": prompt,
            "stream": False,
            "options": {
                "num_predict": 2048,
                "num_ctx": 8192,
                "temperature": 0.2
            }
        }

        headers = {
            "Content-Type": "application/json"
        }

        req = urllib.request.Request(
            url,
            data=json.dumps(data).encode('utf-8'),
            headers=headers,
            method='POST'
        )

        try:
            with urllib.request.urlopen(req, timeout=180) as response:
                res = json.loads(response.read().decode('utf-8'))
                if isinstance(res, dict) and 'error' in res:
                    print(f"❌ Ollama API Error: {res['error']}")
                    return ""
                text = res.get('response', '')
                if not text.strip():
                    print(f"⚠️ Warning: Ollama ({self.get_name()}) returned an empty response. The prompt might be too long for the model's context limit or server is overloaded.")
                return text
        except urllib.error.HTTPError as e:
            error_body = ""
            try:
                error_body = e.read().decode('utf-8')
            except Exception:
                pass
            print(f"❌ HTTP Error calling Ollama ({self.get_name()}): {e.code} - {e.reason}")
            if error_body:
                print(f"Details: {error_body}")
            return ""
        except Exception as e:
            print(f"❌ Error calling Ollama ({self.get_name()}): {e}")
            return ""

    def validate_config(self) -> bool:
        """Ollama 설정 검증 (기본적으로 모델명만 확인)"""
        return bool(self.model and self.api_url)

    def get_name(self) -> str:
        """백엔드 이름 반환"""
        return "ollama"
