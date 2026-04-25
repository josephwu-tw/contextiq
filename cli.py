"""
CLI runner for ContextIQ.
Run with: python cli.py
"""

from dotenv import load_dotenv
load_dotenv()

from docubot import DocuBot
from providers import load_available_clients
from samples import SAMPLE_QUERIES


def choose_provider(clients: dict):
    """Prompts user to pick a provider when multiple are available."""
    if not clients:
        print("Warning: No LLM providers configured. LLM features are disabled.")
        print("Add API keys to your .env file to enable them.\n")
        return None, False

    names = list(clients.keys())
    if len(names) == 1:
        name = names[0]
        print(f"Using provider: {name}\n")
        return clients[name], True

    print("Available providers:")
    for i, name in enumerate(names, 1):
        print(f"  {i}) {name}")

    while True:
        choice = input("Choose a provider (number): ").strip()
        if choice.isdigit() and 1 <= int(choice) <= len(names):
            name = names[int(choice) - 1]
            return clients[name], True
        print(f"Please enter a number between 1 and {len(names)}.")


def choose_mode(has_llm: bool) -> str:
    print("Choose a mode:")
    if has_llm:
        print("  1) Naive LLM over full docs (no retrieval)")
    else:
        print("  1) Naive LLM over full docs  (unavailable — no API key configured)")
    print("  2) Retrieval only (no LLM)")
    if has_llm:
        print("  3) RAG (retrieval + LLM)")
    else:
        print("  3) RAG  (unavailable — no API key configured)")
    print("  q) Quit")
    return input("Enter choice: ").strip().lower()


def get_query_or_use_samples():
    print("\nPress Enter to run built-in sample queries.")
    custom = input("Or type a single custom query: ").strip()
    if custom:
        return [custom], "custom query"
    return SAMPLE_QUERIES, "sample queries"


def run_naive_llm_mode(bot, has_llm: bool):
    if not has_llm or bot.llm_client is None:
        print("\nNaive LLM mode is not available (no API key configured).\n")
        return
    queries, label = get_query_or_use_samples()
    print(f"\nRunning naive LLM mode on {label}...\n")
    all_text = bot.full_corpus_text()
    for query in queries:
        print("=" * 60)
        print(f"Question: {query}\n")
        print("Answer:")
        print(bot.llm_client.naive_answer_over_full_docs(query, all_text))
        print()


def run_retrieval_only_mode(bot):
    queries, label = get_query_or_use_samples()
    print(f"\nRunning retrieval only mode on {label}...\n")
    for query in queries:
        print("=" * 60)
        print(f"Question: {query}\n")
        print("Retrieved snippets:")
        print(bot.answer_retrieval_only(query))
        print()


def run_rag_mode(bot, has_llm: bool):
    if not has_llm or bot.llm_client is None:
        print("\nRAG mode is not available (no API key configured).\n")
        return
    queries, label = get_query_or_use_samples()
    print(f"\nRunning RAG mode on {label}...\n")
    for query in queries:
        print("=" * 60)
        print(f"Question: {query}\n")
        print("Answer:")
        print(bot.answer_rag(query))
        print()


def main():
    print("ContextIQ — CLI")
    print("===============\n")

    clients = load_available_clients()
    llm_client, has_llm = choose_provider(clients)
    bot = DocuBot(llm_client=llm_client)

    while True:
        choice = choose_mode(has_llm)
        if choice == "q":
            print("\nGoodbye.")
            break
        elif choice == "1":
            run_naive_llm_mode(bot, has_llm)
        elif choice == "2":
            run_retrieval_only_mode(bot)
        elif choice == "3":
            run_rag_mode(bot, has_llm)
        else:
            print("\nUnknown choice. Please pick 1, 2, 3, or q.\n")


if __name__ == "__main__":
    main()
