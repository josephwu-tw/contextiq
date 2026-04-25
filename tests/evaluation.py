"""
Retrieval evaluation harness for ContextIQ / DocuBot.

Compares naive generation, retrieval-only, and RAG modes by checking whether
DocuBot surfaces the correct source files for each sample query.
"""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from samples import SAMPLE_QUERIES


# -----------------------------------------------------------
# Expected document signals for evaluation
# -----------------------------------------------------------
# Maps a query substring to the filename(s) that should be relevant.
# Used to measure retrieval hit rate; does not need to be exhaustive.

EXPECTED_SOURCES = {
    "auth token": ["AUTH.md"],
    "environment variables": ["AUTH.md"],
    "database": ["DATABASE.md"],
    "users": ["API_REFERENCE.md"],
    "projects": ["API_REFERENCE.md"],
    "refresh": ["AUTH.md"],
    "users table": ["DATABASE.md"],
}


def expected_files_for_query(query):
    """Returns expected filenames based on simple substring matching."""
    query_lower = query.lower()
    matches = []
    for key, files in EXPECTED_SOURCES.items():
        if key in query_lower:
            matches.extend(files)
    return matches


# -----------------------------------------------------------
# Evaluation function
# -----------------------------------------------------------

def evaluate_retrieval(bot, top_k=3):
    """
    Runs DocuBot's retrieval system against SAMPLE_QUERIES.
    Returns (hit_rate, detailed_results).

    hit_rate: fraction of queries where at least one retrieved snippet's
              filename matched an expected filename.
    detailed_results: list of dicts with per-query structured info.
    """
    results = []
    hits = 0

    for query in SAMPLE_QUERIES:
        expected = expected_files_for_query(query)
        retrieved = bot.retrieve(query, top_k=top_k)

        retrieved_files = [fname for fname, _ in retrieved]

        hit = any(f in retrieved_files for f in expected) if expected else False
        if hit:
            hits += 1

        results.append({
            "query": query,
            "expected": expected,
            "retrieved": retrieved_files,
            "hit": hit
        })

    hit_rate = hits / len(SAMPLE_QUERIES)
    return hit_rate, results


# -----------------------------------------------------------
# Pretty printing
# -----------------------------------------------------------

def print_eval_results(hit_rate, results):
    """Formats and prints evaluation results to stdout."""
    print("\nEvaluation Results")
    print("------------------")
    print(f"Hit rate: {hit_rate:.2f}\n")

    for item in results:
        print(f"Query: {item['query']}")
        print(f"  Expected:  {item['expected']}")
        print(f"  Retrieved: {item['retrieved']}")
        print(f"  Hit:       {item['hit']}")
        print()


# -----------------------------------------------------------
# CLI entry point
# -----------------------------------------------------------

if __name__ == "__main__":
    from docubot import DocuBot

    print("Running retrieval evaluation...\n")
    bot = DocuBot()

    hit_rate, results = evaluate_retrieval(bot)
    print_eval_results(hit_rate, results)
