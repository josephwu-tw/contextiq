import os
import anthropic
from .base import BaseLLMClient

CLAUDE_MODEL = "claude-haiku-4-5-20251001"


class ClaudeClient(BaseLLMClient):
    @property
    def provider_name(self) -> str:
        return "Claude"

    def __init__(self):
        api_key = os.getenv("ANTHROPIC_API_KEY")
        if not api_key or api_key.startswith("your_"):
            raise RuntimeError(
                "Missing ANTHROPIC_API_KEY. Set it in your .env file to enable Claude."
            )
        self.client = anthropic.Anthropic(api_key=api_key)

    def _generate(self, prompt: str) -> str:
        response = self.client.messages.create(
            model=CLAUDE_MODEL,
            max_tokens=512,
            messages=[{"role": "user", "content": prompt}],
        )
        return response.content[0].text.strip()

    def naive_answer_over_full_docs(self, query: str, all_text: str) -> str:
        response = self.client.messages.create(
            model=CLAUDE_MODEL,
            max_tokens=1024,
            messages=[{"role": "user", "content": self._build_naive_prompt(query, all_text)}],
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
