from typing import List

from .base import LLMBackend
from .backends import OllamaBackend, RestApiBackend, CliBackend


class LLMBackendFactory:
    """LLM 백엔드 팩토리"""

    @staticmethod
    def create(backend_name: str, **kwargs) -> LLMBackend:
        """
        백엔드 이름으로 LLM 백엔드 인스턴스를 생성합니다.
        
        Args:
            backend_name: 백엔드 이름 ("ollama", "gemini", "claude", ...)
            **kwargs: 백엔드별 파라미터
                - ollama: model, api_url
                - gemini: model, api_key, api_url (선택사항)
                - claude: model
                
        Returns:
            생성된 LLMBackend 인스턴스
            
        Raises:
            ValueError: 알 수 없는 백엔드명
        """
        if backend_name == "ollama":
            return OllamaBackend(
                model=kwargs.get("model", "gemma4:e4b"),
                api_url=kwargs.get("api_url", "http://localhost:11434/api/generate")
            )
        elif backend_name == "gemini":
            api_key = kwargs.get("api_key")
            if not api_key:
                raise ValueError("gemini backend requires 'api_key' parameter")
            return RestApiBackend(
                provider="gemini",
                model=kwargs.get("model", "gemini-1.5-flash"),
                api_key=api_key,
                api_url=kwargs.get("api_url")
            )
        elif backend_name == "claude":
            return CliBackend(
                cli_name="claude",
                command=["claude", "-p", "--output-format", "text"],
                model=kwargs.get("model", "claude-sonnet-4-6")
            )
        else:
            raise ValueError(f"Unknown LLM backend: {backend_name}")

    @staticmethod
    def list_backends() -> List[str]:
        """지원하는 백엔드 목록을 반환합니다."""
        return ["ollama", "gemini", "claude"]
