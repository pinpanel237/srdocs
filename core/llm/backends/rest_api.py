import urllib.request
import json
import ssl

from ..base import LLMBackend


class RestApiBackend(LLMBackend):
    """REST API 기반 LLM 백엔드 (Gemini, 향후 OpenAI, Anthropic 등)"""

    def __init__(self, provider: str, model: str, api_key: str, api_url: str = None):
        """
        REST API 백엔드 초기화
        
        Args:
            provider: 제공자명 ("gemini", "openai", "anthropic" 등)
            model: 사용할 모델명
            api_key: API 키
            api_url: API 주소 (None일 경우 provider 기본값 사용)
        """
        self.provider = provider
        self.model = model
        self.api_key = api_key
        self.api_url = api_url or self._get_default_url(provider)

    def _get_default_url(self, provider: str) -> str:
        """제공자별 기본 API URL 반환"""
        defaults = {
            "gemini": "https://generativelanguage.googleapis.com/v1beta/models",
            "openai": "https://api.openai.com/v1/chat/completions",
            "anthropic": "https://api.anthropic.com/v1/messages",
        }
        return defaults.get(provider, "")

    def call(self, prompt: str) -> str:
        """REST API를 호출하여 프롬프트 처리"""
        if self.provider == "gemini":
            return self._call_gemini_impl(prompt)
        elif self.provider == "openai":
            return self._call_openai_impl(prompt)
        elif self.provider == "anthropic":
            return self._call_anthropic_impl(prompt)
        else:
            print(f"Error: Unknown provider '{self.provider}' for REST API backend")
            return ""

    def _call_gemini_impl(self, prompt: str) -> str:
        """Gemini API 호출 구현"""
        url = f"{self.api_url}/{self.model}:generateContent?key={self.api_key}"
        data = {
            "contents": [{
                "parts": [{
                    "text": prompt
                }]
            }]
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

        context = ssl._create_unverified_context()

        try:
            with urllib.request.urlopen(req, context=context, timeout=180) as response:
                res = json.loads(response.read().decode('utf-8'))
                text = res['candidates'][0]['content']['parts'][0]['text']
                return text
        except Exception as e:
            print(f"Error calling Gemini API: {e}")
            return ""

    def _call_openai_impl(self, prompt: str) -> str:
        """OpenAI API 호출 구현 (향후 지원 예정)"""
        print("Error: OpenAI backend not yet implemented")
        return ""

    def _call_anthropic_impl(self, prompt: str) -> str:
        """Anthropic API 호출 구현 (향후 지원 예정)"""
        print("Error: Anthropic backend not yet implemented")
        return ""

    def validate_config(self) -> bool:
        """REST API 설정 검증"""
        return bool(self.provider and self.model and self.api_key and self.api_url)

    def get_name(self) -> str:
        """백엔드 이름 반환"""
        return self.provider
