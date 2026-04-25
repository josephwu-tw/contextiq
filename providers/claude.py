import os
import anthropic
from .base import BaseLLMClient

CLAUDE_MODEL = "claude-haiku-4-5-20251001"


class ClaudeClient(BaseLLMClient):
    provider_name = "Claude"

    def __init__(self):
        api_key = os.getenv("ANTHROPIC_API_KEY")
        if not api_key:
            raise RuntimeError(
                "Missing ANTHROPIC_API_KEY. Set it in your .env file to enable Claude."
            )
        self.client = anthropic.Anthropic(api_key=api_key)

    def naive_answer_over_full_docs(self, query: str, all_text: str) -> str:
        response = self.client.messages.create(
            model=CLAUDE_MODEL,
            max_tokens=1024,
            messages=[{"role": "user", "content": self._build_naive_prompt(query)}],
        )
        return response.content[0].text.strip()

    def answer_from_snippets(self, query: str, snippets: list) -> str:
        if not snippets:
            return "I do not know based on the docs I have."
        response = self.client.messages.create(
            model=CLAUDE_MODEL,
            max_tokens=1024,
            messages=[{"role": "user", "content": self._build_rag_prompt(query, snippets)}],
        )
        return response.content[0].text.strip()
