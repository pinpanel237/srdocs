from abc import ABC, abstractmethod


class LLMBackend(ABC):
    """모든 LLM 백엔드의 추상 베이스 클래스"""

    @abstractmethod
    def call(self, prompt: str) -> str:
        """
        LLM을 호출하고 결과를 반환합니다.
        
        Args:
            prompt: LLM에 전달할 프롬프트
            
        Returns:
            LLM의 응답 (실패시 빈 문자열)
        """
        pass

    @abstractmethod
    def validate_config(self) -> bool:
        """
        백엔드 설정이 유효한지 검증합니다.
        
        Returns:
            설정이 유효하면 True, 아니면 False
        """
        pass

    @abstractmethod
    def get_name(self) -> str:
        """
        백엔드 이름을 반환합니다.
        
        Returns:
            백엔드 이름 (예: "ollama", "gemini", "claude")
        """
        pass
