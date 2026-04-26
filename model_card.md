# ContextIQ Model Card

This model card is a short reflection on your DocuBot system. Fill it out after you have implemented retrieval and experimented with all three modes:

1. Naive LLM over full docs  
2. Retrieval only  
3. RAG (retrieval plus LLM)

Use clear, honest descriptions. It is fine if your system is imperfect.

---

## 1. System Overview

**What is DocuBot trying to do?**  
DocuBot answers developer questions about a codebase by retrieving relevant
paragraphs from a docs/ folder and optionally using an LLM to synthesize a
grounded answer. The goal is to reduce hallucination by grounding LLM output
in actual documentation rather than training data.

**What inputs does DocuBot take?**  
A natural language developer question, a folder of .md/.txt documentation
files, and an optional Gemini API key for LLM-powered modes.

**What outputs does DocuBot produce?**  
Either raw retrieved text snippets (Mode 2) or a synthesized plain-English
answer grounded in those snippets (Mode 3), with an explicit refusal when the
docs don't contain enough evidence.

---

## 2. Retrieval Design

**How does your retrieval system work?**

- **Indexing:** Documents are split on `\n\n` into paragraph-level chunks.
  Each chunk is tokenized (split on whitespace, punctuation stripped,
  lowercased) and stored in an inverted index mapping word → set of chunk
  indices.
- **Scoring:** `score_document` counts how many query words appear anywhere
  in a candidate chunk's text (substring match, not word boundary).
- **Selection:** Candidate chunks are found via index lookup, scored, filtered
  to `min_score >= 1`, sorted descending, and the top-3 are returned.

**What tradeoffs did you make?**

- **Paragraph chunks over full documents** — smaller units reduce noise but
  also mean some answers span multiple chunks that may not all be retrieved.
- **Exact keyword matching over fuzzy/semantic matching** — simple and fast,
  but breaks on synonyms ("generated" vs "created") and inflections.
- **min_score=1 guardrail** — filters purely stop-word hits, but stop words
  still contribute to scores on irrelevant chunks, so false positives remain.

---

## 3. Use of the LLM (Gemini)

**When does DocuBot call the LLM and when does it not?**

- **Naive LLM mode:** Calls Gemini with only the user query. The full docs
  text is passed but ignored in the prompt — Gemini answers from training
  data alone, with no grounding.
- **Retrieval only mode:** No LLM. Returns the raw top-3 chunks directly.
- **RAG mode:** Calls Gemini with retrieved chunks as context and strict
  instructions to answer only from those chunks.

**What instructions do you give the LLM to keep it grounded?**

The RAG prompt tells the model to:
- Use only the information in the provided snippets
- Never invent functions, endpoints, or configuration values
- Reply exactly "I do not know based on the docs I have." when snippets are
  insufficient
- Mention which files it relied on when it does answer

---

## 4. Experiments and Comparisons

Three identical queries were run across all three modes.

| Query | Naive LLM: helpful or harmful? | Retrieval only: helpful or harmful? | RAG: helpful or harmful? | Notes |
|-------|--------------------------------|--------------------------------------|---------------------------|-------|
| Where is the auth token generated? | Harmful — confident answer citing Node.js, Spring Security, Auth0; none exist in project | Partially helpful — correct source (AUTH.md), but missed the key paragraph due to "generated" vs "created" mismatch | Harmful by omission — correctly refused, but the answer IS in the docs | Keyword mismatch is the root failure |
| Which fields are stored in the users table? | Harmful — plausible generic schema (id, email, etc.) not grounded in project | Harmful — retrieved db.py helper and SETUP.md troubleshooting chunks, not the schema | Correct refusal — refused because wrong chunks were retrieved | Stop words ("stored in the") matched irrelevant paragraphs |
| Is there any mention of payment processing in these docs? | Unhelpful — asked user to provide docs, gave no answer | Harmful — returned unrelated SETUP.md and API_REFERENCE chunks with no signal of irrelevance | Helpful — correctly refused with explicit "I do not know" | Clearest case where RAG outperforms both other modes |

**What patterns did you notice?**

- **Naive LLM looks impressive but untrustworthy** when the question is about
  a common concept (auth tokens, database schemas). The model produces
  fluent, detailed answers from training data that sound project-specific but
  are entirely fabricated. This is the highest-risk scenario.

- **Retrieval only is clearly better** for questions where the query words
  appear verbatim in the relevant doc section. It surfaces actual project
  text, which a developer can read and evaluate. It fails silently — it never
  signals when its results are irrelevant.

- **RAG is clearly better** when the question has no answer in the docs (like
  payment processing). It explicitly refuses rather than returning misleading
  content or asking the user for more information. The refusal itself is
  useful information.

---

## 5. Failure Cases and Guardrails

**Describe at least two concrete failure cases you observed.**

> **Failure case 1: Keyword mismatch (Query 1)**
> Question: "Where is the auth token generated?"
> What happened: Retrieval returned AUTH.md overview and token-signing
> paragraphs, missing the paragraph stating "Tokens are created by the
> `generate_access_token` function in `auth_utils.py`." The word "created"
> doesn't match "generated". RAG then correctly refused — but the answer
> existed in the docs all along.
> What should have happened: The generation/creation paragraph should have
> ranked highest. A semantic embedding or synonym expansion would fix this.

> **Failure case 2: Stop word pollution (Query 2 and 3)**
> Question: "Is there any mention of payment processing in these docs?"
> What happened: Mode 2 returned SETUP.md intro, an API user list, and an
> API error code section — none relevant. These matched on "is", "any",
> "in", "docs". The min_score=1 guardrail did not help because those
> stop words cleared the threshold.
> What should have happened: The system should have returned no results
> (correct) or at minimum flagged low confidence. TF-IDF weighting would
> downrank stop words and raise the effective threshold for meaningful hits.

**When should DocuBot say "I do not know based on the docs I have"?**

1. When the retrieved chunks contain none of the query's meaningful terms
   (topic doesn't exist in the docs at all).
2. When the retrieved chunks are from unrelated sections and the LLM cannot
   construct a coherent answer without inventing information.

**What guardrails did you implement?**

- `min_score=1` in `retrieve`: chunks that score zero after candidate
  selection are excluded. Prevents returning content that matched only
  incidentally via the index.
- Empty results check in `answer_retrieval_only` and `answer_rag`: returns
  "I do not know" immediately if no chunks pass the score threshold.
- RAG prompt rule: LLM is explicitly instructed to refuse rather than guess
  when snippets are insufficient, using a fixed refusal string.

---

## 6. Limitations and Future Improvements

**Current limitations**

1. **Keyword-only retrieval fails on synonyms and paraphrases.** "Generated"
   vs "created", "login" vs "authentication" — any vocabulary mismatch causes
   a miss.
2. **Stop words contribute to scores.** A query like "Is there any X" matches
   many documents on "is", "there", "any" even when X is absent, producing
   false positive retrieval results.
3. **Chunk boundary fragmentation.** A single answer can span two paragraphs.
   Splitting on `\n\n` may separate a header from its detail, meaning
   retrieved chunks are incomplete even when the right document is found.
4. **Mode 1 ignores `all_text` entirely.** The naive prompt passes the query
   but discards the corpus, so Mode 1 is purely training-data recall — it
   cannot answer project-specific questions at all.

**Future improvements**

1. **Semantic embeddings for retrieval.** Replace keyword scoring with
   cosine similarity over sentence embeddings. Resolves synonym mismatches
   and handles paraphrase.
2. **TF-IDF weighting.** Downrank stop words so high-frequency terms don't
   pollute scores. Immediately improves precision on vague queries.
3. **Fix Mode 1 to actually use the corpus.** Pass `all_text` into the prompt
   so the baseline is at least grounded, making the Mode 1 vs Mode 3
   comparison meaningful.

---

## 7. Responsible Use

**Where could this system cause real world harm if used carelessly?**

Mode 1 (Naive LLM) returns confident, fluent answers about auth, database
schemas, and API endpoints that look project-specific but come from training
data. A developer acting on Mode 1 output could configure incorrect
environment variables, implement the wrong auth flow, or miss a required
security step. Mode 2 failure is subtler: returning irrelevant chunks with no
confidence signal could mislead a developer into believing they've found the
answer when they haven't.

**What instructions would you give real developers who want to use DocuBot safely?**

- Always verify answers against the actual source files before acting on them,
  especially for security-critical topics like auth and database configuration.
- Treat Mode 2 output as a pointer to investigate further, not a complete
  answer — check which file the chunk came from and read the surrounding
  context.
- When DocuBot says "I do not know," trust it and read the docs directly
  rather than rephrasing and retrying until it gives an answer.
- Do not use Mode 1 (Naive LLM) for project-specific questions — it has no
  access to your docs and will fabricate plausible-sounding but wrong details.

---

## 8. AI Collaboration

**How did you use AI assistance during development?**

Claude (Anthropic) was used as a development collaborator throughout the project. Key contributions:

- **Incremental index update** — Claude suggested appending to the existing inverted index in `add_documents()` rather than rebuilding from scratch. This was a genuine efficiency improvement and was kept as-is.
- **Provider abstraction design** — Claude proposed the `BaseLLMClient` abstract base class with shared prompt builders, making each new provider a self-contained change with no impact on `docubot.py` or the API layer.
- **Agentic pipeline** — Claude helped design the two-step reasoning chain (plan → retrieve → answer) where the LLM first decides what to search for before executing retrieval.
- **One suggestion I did not use** — Claude suggested adding a `conftest.py` for pytest configuration. The evaluation script runs as a plain Python module, so this was unnecessary and was ignored.

**What biases or limitations did you observe in AI-assisted development?**

- Claude defaulted to adding explanatory comments to every function. These were removed in a cleanup pass since the code is self-documenting.
- Claude occasionally over-engineered solutions — for example, proposing Gradio for the frontend before I clarified the portfolio requirement. Explicit constraints were needed to redirect it.
- When given free rein, Claude gravitated toward more complex patterns until prompted to consider simpler alternatives.

**What did you verify independently?**

All provider SDK calls, the placeholder API key detection logic (`startswith("your_")`), and the DEV_MODE hot-reload behavior were tested manually against real API keys before being accepted.
