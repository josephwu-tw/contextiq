import os
from google import genai
from .base import BaseLLMClient

GEMINI_MODEL = "gemini-2.5-flash"


class GeminiClient(BaseLLMClient):
    @property
    def provider_name(self) -> str:
        return "Gemini"

    def __init__(self):
        api_key = os.getenv("GEMINI_API_KEY")
        if not api_key or api_key.startswith("your_"):
            raise RuntimeError(
                "Missing GEMINI_API_KEY. Set it in your .env file to enable Gemini."
            )
        self.client = genai.Client(api_key=api_key)

    def _generate(self, prompt: str) -> str:
        response = self.client.models.generate_content(model=GEMINI_MODEL, contents=prompt)
        return (response.text or "").strip()

    def naive_answer_over_full_docs(self, query: str, all_text: str) -> str:
        response = self.client.models.generate_content(
            model=GEMINI_MODEL,
            contents=self._build_naive_prompt(query, all_text),
        )
        return (response.text or "").strip()

    def answer_from_snippets(self, query: str, snippets: list) -> str:
        if not snippets:
            return "I do not know based on the docs I have."
        response = self.client.models.generate_content(
            model=GEMINI_MODEL,
            contents=self._build_rag_prompt(query, snippets),
        )
        return (response.text or "").strip()
