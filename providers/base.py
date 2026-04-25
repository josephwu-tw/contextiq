from abc import ABC, abstractmethod


class BaseLLMClient(ABC):
    """Shared interface all LLM providers must implement."""

    @property
    @abstractmethod
    def provider_name(self) -> str: ...

    @abstractmethod
    def naive_answer_over_full_docs(self, query: str, all_text: str) -> str: ...

    @abstractmethod
    def answer_from_snippets(self, query: str, snippets: list) -> str: ...

    def _build_naive_prompt(self, query: str) -> str:
        return f"You are a documentation assistant.\nAnswer this developer question: {query}"

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
