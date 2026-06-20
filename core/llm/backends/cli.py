import subprocess
from typing import List, Optional

from ..base import LLMBackend


class CliBackend(LLMBackend):
    """CLI 기반 LLM 백엔드 (Claude, 향후 다른 CLI도 지원)"""

    def __init__(self, cli_name: str, command: List[str], model: str = None):
        """
        CLI 백엔드 초기화
        
        Args:
            cli_name: CLI 이름 ("claude", 기타)
            command: 실행할 커맨드 리스트 (예: ["claude", "-p", "--output-format", "text"])
            model: 사용할 모델명 (선택사항)
        """
        self.cli_name = cli_name
        self.command = command
        self.model = model

    def call(self, prompt: str) -> str:
        """CLI를 호출하여 프롬프트 처리"""
        if self.cli_name == "claude":
            return self._call_claude_impl(prompt)
        else:
            print(f"Error: Unknown CLI backend '{self.cli_name}'")
            return ""

    def _call_claude_impl(self, prompt: str) -> str:
        """Claude CLI 호출 구현"""
        cmd = self.command.copy()
        if self.model:
            cmd.extend(["--model", self.model])

        try:
            res = subprocess.run(
                cmd,
                input=prompt,
                capture_output=True,
                text=True,
                timeout=180
            )
            if res.returncode != 0:
                print(f"Error calling claude CLI: {res.stderr.strip()}")
                return ""
            return res.stdout.strip()
        except FileNotFoundError:
            print("Error: claude CLI를 찾을 수 없습니다. Claude Code가 설치되어 있는지 확인해주세요.")
            return ""
        except Exception as e:
            print(f"Error calling claude CLI: {e}")
            return ""

    def validate_config(self) -> bool:
        """CLI 설정 검증 (기본적으로 커맨드만 확인)"""
        return bool(self.command)

    def get_name(self) -> str:
        """백엔드 이름 반환"""
        return self.cli_name
