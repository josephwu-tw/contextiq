from abc import ABC, abstractmethod
import re


class BaseLLMClient(ABC):
    """Shared interface all LLM providers must implement."""

    @property
    @abstractmethod
    def provider_name(self) -> str: ...

    @abstractmethod
    def _generate(self, prompt: str) -> str: ...

    @abstractmethod
    def naive_answer_over_full_docs(self, query: str, all_text: str) -> str: ...

    @abstractmethod
    def answer_from_snippets(self, query: str, snippets: list) -> str: ...

    def plan_retrieval(self, query: str) -> dict:
        prompt = (
            f'You are a retrieval planner for a documentation assistant.\n\n'
            f'A user asked: "{query}"\n\n'
            f'Decide what to search for in the documentation index.\n\n'
            f'Reply in this exact format (no extra text):\n'
            f'REASONING: <one sentence explaining what the question is looking for>\n'
            f'SEARCH_TERMS: <3-6 keywords most likely to appear in the relevant docs>'
        )
        raw = self._generate(prompt)
        reasoning_m = re.search(r'REASONING:\s*(.+)', raw)
        terms_m = re.search(r'SEARCH_TERMS:\s*(.+)', raw)
        return {
            "reasoning": reasoning_m.group(1).strip() if reasoning_m else "",
            "search_terms": terms_m.group(1).strip() if terms_m else query,
        }

    def _build_naive_prompt(self, query: str, all_text: str = "") -> str:
        docs_section = f"\n\nDocumentation:\n{all_text}" if all_text else ""
        return f"You are a documentation assistant.{docs_section}\n\nAnswer this developer question: {query}"

    def _build_rag_prompt(self, query: str, snippets: list) -> str:
        context = "\n\n".join(f"File: {fname}\n{text}" for fname, text in snippets)
        return f"""You are a cautious documentation assistant helping developers understand a codebase.

You will receive:
- A developer question
- A small set of snippets from project files

Your job:
- Answer the question using only the information in the snippets.
- If the snippets do not provide enough evidence, refuse to guess.

Snippets:
{context}

Developer question:
{query}

Rules:
- Use only the information in the snippets. Do not invent new functions, endpoints, or configuration values.
- If the snippets are not enough to answer confidently, reply exactly: "I do not know based on the docs I have."
- When you do answer, briefly mention which files you relied on."""
