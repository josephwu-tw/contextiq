"""
Retrieval evaluation harness for ContextIQ / DocuBot.

Compares naive generation, retrieval-only, and RAG modes by checking whether
DocuBot surfaces the correct source files for each sample query.

Also includes compare_sources() which demonstrates the RAG Enhancement:
running evaluation before and after uploading a custom document to show
measurable improvement in retrieval hit rate.
"""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from samples import SAMPLE_QUERIES

# -----------------------------------------------------------
# Expected document signals — default corpus
# -----------------------------------------------------------

EXPECTED_SOURCES = {
    "auth token": ["AUTH.md"],
    "environment variables": ["AUTH.md"],
    "database": ["DATABASE.md"],
    "users": ["API_REFERENCE.md"],
    "projects": ["API_REFERENCE.md"],
    "refresh": ["AUTH.md"],
    "users table": ["DATABASE.md"],
}

# -----------------------------------------------------------
# Extended queries — only answerable after uploading DEPLOYMENT.md
# -----------------------------------------------------------

EXTENDED_QUERIES = [
    "How do I run the app with Docker?",
    "What is the health check endpoint?",
    "How do I set the log level?",
]

EXTENDED_EXPECTED_SOURCES = {
    "docker": ["DEPLOYMENT.md"],
    "health check": ["DEPLOYMENT.md"],
    "log level": ["DEPLOYMENT.md"],
}


def expected_files_for_query(query, source_map=None):
    """Returns expected filenames based on simple substring matching."""
    if source_map is None:
        source_map = EXPECTED_SOURCES
    query_lower = query.lower()
    matches = []
    for key, files in source_map.items():
        if key in query_lower:
            matches.extend(files)
    return matches


# -----------------------------------------------------------
# Core evaluation function
# -----------------------------------------------------------

def evaluate_retrieval(bot, queries, source_map, top_k=3):
    """
    Runs retrieval against a query list and expected source map.
    Returns (hit_rate, detailed_results).
    """
    results = []
    hits = 0

    for query in queries:
        expected = expected_files_for_query(query, source_map)
        retrieved = bot.retrieve(query, top_k=top_k)
        retrieved_files = [fname for fname, _ in retrieved]

        hit = any(f in retrieved_files for f in expected) if expected else False
        if hit:
            hits += 1

        results.append({
            "query": query,
            "expected": expected,
            "retrieved": retrieved_files,
            "hit": hit,
        })

    hit_rate = hits / len(queries) if queries else 0.0
    return hit_rate, results


# -----------------------------------------------------------
# Pretty printing
# -----------------------------------------------------------

def print_eval_results(hit_rate, results):
    print(f"Hit rate: {hit_rate:.0%}  ({sum(r['hit'] for r in results)}/{len(results)} queries)\n")
    for item in results:
        status = "✓" if item["hit"] else "✗"
        print(f"  [{status}] {item['query']}")
        if not item["hit"]:
            print(f"        expected:  {item['expected']}")
            print(f"        retrieved: {item['retrieved']}")


# -----------------------------------------------------------
# RAG Enhancement: before/after comparison
# -----------------------------------------------------------

def compare_sources(docs_folder="docs", custom_doc_path=None):
    """
    Demonstrates measurable improvement when a custom document is added.

    Runs two evaluations over the combined default + extended query set:
      1. Baseline  — default docs only
      2. Extended  — default docs + DEPLOYMENT.md (or custom_doc_path)

    Queries that require DEPLOYMENT.md will fail in the baseline and pass
    after the document is added, showing a clear hit-rate improvement.
    """
    from docubot import DocuBot

    all_queries = SAMPLE_QUERIES + EXTENDED_QUERIES
    combined_sources = {**EXPECTED_SOURCES, **EXTENDED_EXPECTED_SOURCES}

    if custom_doc_path is None:
        custom_doc_path = os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            "sample_uploads", "DEPLOYMENT.md",
        )

    # --- Baseline ---
    bot = DocuBot(docs_folder=docs_folder)
    baseline_rate, baseline_results = evaluate_retrieval(
        bot, all_queries, combined_sources
    )

    # --- With custom doc ---
    with open(custom_doc_path, "r", encoding="utf-8") as f:
        custom_text = f.read()
    bot.add_documents([(os.path.basename(custom_doc_path), custom_text)])
    extended_rate, extended_results = evaluate_retrieval(
        bot, all_queries, combined_sources
    )

    # --- Print comparison ---
    print("=" * 60)
    print("RAG Enhancement: Source Comparison")
    print("=" * 60)

    print(f"\nBaseline  (default docs only, {bot.source_count - 1} sources):")
    print_eval_results(baseline_rate, baseline_results)

    print(f"\nExtended  (+ {os.path.basename(custom_doc_path)}, {bot.source_count} sources):")
    print_eval_results(extended_rate, extended_results)

    delta = extended_rate - baseline_rate
    print(f"\nImprovement: {baseline_rate:.0%} → {extended_rate:.0%}  ({delta:+.0%})")
    print("=" * 60)


# -----------------------------------------------------------
# CLI entry point
# -----------------------------------------------------------

if __name__ == "__main__":
    from docubot import DocuBot

    DOCS_FOLDER = os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "docs"
    )

    print("\n── Standard Retrieval Evaluation ──────────────────────")
    bot = DocuBot(docs_folder=DOCS_FOLDER)
    rate, results = evaluate_retrieval(bot, SAMPLE_QUERIES, EXPECTED_SOURCES)
    print_eval_results(rate, results)

    print("\n── RAG Enhancement Demo ────────────────────────────────")
    compare_sources(docs_folder=DOCS_FOLDER)
