import os
from openai import OpenAI
from .base import BaseLLMClient

OPENAI_MODEL = "gpt-4o-mini"


class OpenAIClient(BaseLLMClient):
    @property
    def provider_name(self) -> str:
        return "ChatGPT"

    def __init__(self):
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key or api_key.startswith("your_"):
            raise RuntimeError(
                "Missing OPENAI_API_KEY. Set it in your .env file to enable ChatGPT."
            )
        self.client = OpenAI(api_key=api_key)

    def _generate(self, prompt: str) -> str:
        response = self.client.chat.completions.create(
            model=OPENAI_MODEL,
            messages=[{"role": "user", "content": prompt}],
        )
        return (response.choices[0].message.content or "").strip()

    def naive_answer_over_full_docs(self, query: str, all_text: str) -> str:
        response = self.client.chat.completions.create(
            model=OPENAI_MODEL,
            messages=[
                {"role": "system", "content": "You are a documentation assistant."},
                {"role": "user", "content": f"Answer this developer question: {query}"},
            ],
        )
        return (response.choices[0].message.content or "").strip()

    def answer_from_snippets(self, query: str, snippets: list) -> str:
        if not snippets:
            return "I do not know based on the docs I have."
        response = self.client.chat.completions.create(
            model=OPENAI_MODEL,
            messages=[
                {"role": "system", "content": "You are a cautious documentation assistant."},
                {"role": "user", "content": self._build_rag_prompt(query, snippets)},
            ],
        )
        return (response.choices[0].message.content or "").strip()
