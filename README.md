# ContextIQ

> Context-aware documentation retrieval and AI-powered Q&A for developer knowledge bases.

ContextIQ is a full-stack AI application that answers developer questions about a codebase by retrieving relevant documentation snippets and synthesizing grounded answers through a large language model. It supports three AI providers (Gemini, Claude, ChatGPT) and four query modes, with a FastAPI backend and a vanilla JS frontend.

---

## Origin

ContextIQ is an extension of **DocuBot**, a CodePath AI110 tinker activity. The original DocuBot was a CLI-only tool that demonstrated three approaches to documentation Q&A — naive LLM generation, keyword-based retrieval, and retrieval-augmented generation — using a single Gemini provider. ContextIQ builds on that foundation by adding multi-provider support, a production-grade REST API, a web frontend, custom document upload, and a formal evaluation harness.

---

## Features

- **Four query modes** — RAG, Agentic (multi-step reasoning chain), Naive LLM (AI only), Retrieval Only (raw snippets, no AI)
- **Agentic mode** — LLM plans what to search for, executes retrieval with those terms, then synthesizes — intermediate steps visible in the chat UI
- **Multi-provider** — Gemini, Claude (Anthropic), ChatGPT (OpenAI); missing keys are gracefully skipped
- **Custom document upload** — extend the knowledge base at runtime with `.md` or `.txt` files
- **Provider badge** — each chat response is labeled with the provider that answered it
- **REST API** — FastAPI backend with auto-generated Swagger docs at `/docs`
- **Evaluation harness** — retrieval hit rate scoring with before/after source comparison
- **Hot reload** — `DEV_MODE=true` enables file-watching auto-restart via uvicorn

---

## Architecture

```
User (browser)
     │  HTTP (fetch)
     ▼
FastAPI  ─── /api/chat ──────► DocuBot.retrieve()
(api/main.py)                       │
     │                              ▼
     │                     Inverted index
     │                     score + top-k chunks
     │                              │
     └── /api/chat (LLM modes) ─► providers/
                                  ├── gemini.py   (google-genai)
                                  ├── claude.py   (anthropic)
                                  └── openai.py   (openai)
```

The retrieval pipeline splits documents into paragraph-level chunks, builds an inverted word index, scores candidates by query-word overlap, and returns the top-k results. In RAG mode, those chunks are passed as grounded context to the selected LLM with a strict prompt that forbids hallucination.

![System Architecture](assets/architecture.svg)

---

## Project Structure

```
contextiq/
├── api/
│   └── main.py          FastAPI app — 6 REST endpoints
├── frontend/
│   ├── index.html
│   ├── style.css
│   └── app.js
├── providers/
│   ├── base.py          Shared interface + prompt builders
│   ├── gemini.py
│   ├── claude.py
│   └── openai.py
├── docs/                Default documentation corpus
├── sample_uploads/      Demo docs for custom upload feature
├── tests/
│   └── evaluation.py    Retrieval evaluation harness
├── docubot.py           Retrieval engine
├── samples.py           Sample queries
├── cli.py               Terminal interface
└── server.py            Uvicorn entry point
```

---

## Setup

**Requirements:** Python 3.9+

### 1. Create and activate a virtual environment

```bash
python -m venv .venv
source .venv/bin/activate      # macOS / Linux
.venv\Scripts\activate         # Windows
```

### 2. Install dependencies

```bash
pip install -r requirements.txt
```

### 3. Configure environment variables

```bash
cp .env.example .env
```

Open `.env` and fill in at least one API key:

```
GEMINI_API_KEY="your_key_here"       # https://aistudio.google.com/
ANTHROPIC_API_KEY="your_key_here"    # https://console.anthropic.com/
OPENAI_API_KEY="your_key_here"       # https://platform.openai.com/
```

Leave unused keys as `"your_xxx_api_key_here"` — the app will mark those providers as unavailable but continue running. Retrieval Only mode works with no keys at all.

---

## Running

### Web app

```bash
python server.py
```

Open **http://127.0.0.1:8000** in your browser.

**Development mode** (hot reload on file save):

```bash
# In .env, set DEV_MODE="true", then:
python server.py
```

### CLI

```bash
python cli.py
```

### Evaluation harness

```bash
python tests/evaluation.py
```

Prints retrieval hit rate across sample queries, plus a before/after comparison showing improvement when a custom document is uploaded.

---

## API Reference

The full interactive API reference is available at **http://127.0.0.1:8000/docs** (Swagger UI) when the server is running.

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/api/health` | Health check |
| `GET` | `/api/providers` | List providers and availability |
| `GET` | `/api/docs` | Current document source count |
| `POST` | `/api/chat` | Send a query (provider, mode, message) |
| `POST` | `/api/docs/upload` | Upload custom `.md` / `.txt` files |
| `POST` | `/api/docs/reset` | Reset to default docs |

---

## Sample Interactions

**RAG mode — question answered from docs**
```
Q: Where is the auth token generated?
A: Based on AUTH.md, tokens are created by the generate_access_token
   function inside auth_utils.py and signed using AUTH_SECRET_KEY.
```

**RAG mode — correct refusal**
```
Q: Is there any mention of payment processing in these docs?
A: I do not know based on the docs I have.
```

**Agentic mode — observable reasoning chain**
```
Q: Where is the auth token generated?

① Plan
   The question asks about token creation in the auth flow.
   Searching: "token generate auth utils"

② Retrieved
   AUTH.md · 3 chunks

A: Based on AUTH.md, tokens are created by the generate_access_token
   function inside auth_utils.py and signed using AUTH_SECRET_KEY.
```

**Custom doc upload — extended knowledge**
```
Q: How do I run the app with Docker?
A: (fails before upload)

After uploading sample_uploads/DEPLOYMENT.md:
A: Run the application using: docker run -p 8080:8080 contextiq-app
```

---

## Design Decisions

**Keyword retrieval over embeddings** — The retrieval engine uses an inverted word index and overlap scoring instead of semantic embeddings. This keeps the system dependency-free (no vector DB, no embedding API calls) and makes the failure modes transparent, which is useful for evaluation and teaching. The tradeoff is synonym blindness: "generated" does not match "created".

**Paragraph-level chunking** — Documents are split on blank lines rather than at the document level. Smaller units reduce noise in retrieval but can fragment answers that span multiple paragraphs.

**Strict RAG prompt** — The LLM is explicitly instructed to refuse when retrieved snippets are insufficient, and to cite source files in its answer. This reduces hallucination at the cost of some false refusals.

**FastAPI over all-in-one frameworks** — Replacing Gradio with a decoupled FastAPI backend and vanilla JS frontend improves scalability: the API can be consumed by any client (browser, CLI, tests, external tools) and the auto-generated Swagger UI documents the contract for free.

**Provider abstraction** — All three LLM providers share a base class with shared prompt builders. Swapping a provider requires changing one line, and new providers can be added without touching `docubot.py` or the API layer.

**Agentic mode separates planning from retrieval** — Rather than passing the raw user query directly to the index, the LLM first decides what terms are most likely to appear in the relevant documentation. This decouples query intent from keyword matching and produces observable intermediate steps (reasoning + search terms + retrieved sources) that make the decision chain auditable.

---

## Testing Summary

The evaluation harness in `tests/evaluation.py` runs all sample queries against the retrieval system and reports hit rate — the fraction of queries where at least one retrieved chunk came from the expected source file.

| Corpus | Queries | Hit rate |
|--------|---------|----------|
| Default docs only (4 sources) | 8 | 75% |
| Default + DEPLOYMENT.md (5 sources) | 11 | 73%* |

*The extended set includes 3 new queries that only resolve after uploading `DEPLOYMENT.md`. Adding that document raised the hit rate on the extended query set from 55% to 73% (+18%).

**What failed:** Two query types consistently miss — "how do I connect to the database?" (keyword mismatch: the doc says "DATABASE_URL", not "connect to") and queries with hyphenated env vars like `LOG_LEVEL` (indexed as one token, not matched by individual words). Both are known limitations of keyword-only retrieval.
