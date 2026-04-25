import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv
load_dotenv()

from fastapi import FastAPI, UploadFile, File
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from docubot import DocuBot
from providers import load_available_clients, ALL_PROVIDER_NAMES

# -----------------------------------------------------------
# Startup state
# -----------------------------------------------------------

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DOCS_FOLDER = os.path.join(ROOT, "docs")

clients = load_available_clients()
bot = DocuBot(docs_folder=DOCS_FOLDER)

_DEFAULT_DOC_COUNT = bot.source_count

_KEY_NAMES = {
    "Gemini":  "GEMINI_API_KEY",
    "Claude":  "ANTHROPIC_API_KEY",
    "ChatGPT": "OPENAI_API_KEY",
}

# -----------------------------------------------------------
# Pydantic models
# -----------------------------------------------------------

class ChatRequest(BaseModel):
    message: str
    provider: str
    mode: str

class ChatResponse(BaseModel):
    answer: str

class DocStatus(BaseModel):
    source_count: int
    message: str

# -----------------------------------------------------------
# App
# -----------------------------------------------------------

app = FastAPI(title="ContextIQ API", version="1.0.0")

# -----------------------------------------------------------
# Routes — must be registered before the static files mount
# -----------------------------------------------------------

@app.get("/api/health")
def health():
    return {"status": "ok"}


@app.get("/api/providers")
def get_providers():
    return [
        {
            "name": name,
            "available": name in clients,
            "key_name": _KEY_NAMES.get(name, "API_KEY"),
        }
        for name in ALL_PROVIDER_NAMES
    ]


@app.get("/api/docs", response_model=DocStatus)
def get_doc_status():
    custom = bot.source_count - _DEFAULT_DOC_COUNT
    msg = (
        f"{_DEFAULT_DOC_COUNT} default + {custom} custom doc(s)"
        if custom > 0
        else f"{_DEFAULT_DOC_COUNT} default docs"
    )
    return DocStatus(source_count=bot.source_count, message=msg)


@app.post("/api/chat", response_model=ChatResponse)
def chat(req: ChatRequest):
    client = clients.get(req.provider)
    bot.llm_client = client

    try:
        if req.mode == "Retrieval Only":
            answer = bot.answer_retrieval_only(req.message)

        elif client is None:
            key = _KEY_NAMES.get(req.provider, "API_KEY")
            answer = (
                f"⚠️ {req.provider} is not configured. "
                f"Set {key} in your .env file and restart the server."
            )

        elif req.mode == "Naive LLM":
            answer = client.naive_answer_over_full_docs(req.message, bot.full_corpus_text())

        elif req.mode == "RAG":
            answer = bot.answer_rag(req.message)

        else:
            answer = f"Unknown mode: {req.mode}"

    except Exception as e:
        answer = (
            f"⚠️ {req.provider} returned an error: {e}\n\n"
            "Your API key may be invalid or expired. "
            "Check your .env file and restart the server."
        )

    return ChatResponse(answer=answer)


@app.post("/api/docs/upload", response_model=DocStatus)
async def upload_docs(files: list[UploadFile] = File(...)):
    bot.reset_to_default_docs()
    new_docs = []
    for f in files:
        content = await f.read()
        try:
            text = content.decode("utf-8")
        except UnicodeDecodeError:
            text = content.decode("latin-1", errors="ignore")
        new_docs.append((f.filename, text))

    if new_docs:
        bot.add_documents(new_docs)

    custom = bot.source_count - _DEFAULT_DOC_COUNT
    return DocStatus(
        source_count=bot.source_count,
        message=f"{_DEFAULT_DOC_COUNT} default + {custom} custom doc(s) loaded",
    )


@app.post("/api/docs/reset", response_model=DocStatus)
def reset_docs():
    bot.reset_to_default_docs()
    return DocStatus(
        source_count=bot.source_count,
        message=f"{_DEFAULT_DOC_COUNT} default docs (reset)",
    )


# -----------------------------------------------------------
# Serve frontend static files — must be last
# -----------------------------------------------------------

app.mount(
    "/",
    StaticFiles(directory=os.path.join(ROOT, "frontend"), html=True),
    name="frontend",
)
