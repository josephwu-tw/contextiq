"""
Gradio web UI for ContextIQ.
Run with: python app.py
"""

import os
from dotenv import load_dotenv
load_dotenv()

import gradio as gr
from docubot import DocuBot
from providers import load_available_clients

# -----------------------------------------------------------
# Startup — runs once when the app launches
# -----------------------------------------------------------

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
DEFAULT_DOCS = os.path.join(SCRIPT_DIR, "docs")

clients = load_available_clients()
bot = DocuBot(docs_folder=DEFAULT_DOCS)

MODES = ["RAG", "Naive LLM", "Retrieval Only"]
PROVIDER_NAMES = list(clients.keys())


def _provider_status_md() -> str:
    if PROVIDER_NAMES:
        return "**Active:** " + " · ".join(PROVIDER_NAMES)
    return "**No providers active** — add API keys to `.env` and restart."


def _doc_status_md() -> str:
    default_count = len(DocuBot(docs_folder=DEFAULT_DOCS).documents)
    custom_count = bot.source_count - default_count
    if custom_count > 0:
        return f"**Sources:** {default_count} default + {custom_count} custom"
    return f"**Sources:** {bot.source_count} default docs"


# -----------------------------------------------------------
# Chat handler
# -----------------------------------------------------------

def respond(message: str, history: list, provider_name: str, mode: str) -> list:
    if not message.strip():
        return history

    client = clients.get(provider_name)
    bot.llm_client = client

    if mode == "Retrieval Only":
        answer = bot.answer_retrieval_only(message)

    elif client is None:
        answer = (
            f"⚠️ **{provider_name}** is not configured.\n\n"
            "Add its API key to your `.env` file and restart the app.\n"
            "You can still use **Retrieval Only** mode without any API key."
        )

    elif mode == "Naive LLM":
        answer = client.naive_answer_over_full_docs(message, bot.full_corpus_text())

    elif mode == "RAG":
        answer = bot.answer_rag(message)

    else:
        answer = "Unknown mode selected."

    history.append({"role": "user", "content": message})
    history.append({"role": "assistant", "content": answer})
    return history


# -----------------------------------------------------------
# Document upload handlers
# -----------------------------------------------------------

def upload_docs(files) -> str:
    """Loads uploaded .md/.txt files into the bot alongside the default docs."""
    if not files:
        return _doc_status_md()

    bot.reset_to_default_docs()
    new_docs = []
    for f in files:
        path = f if isinstance(f, str) else f.name
        try:
            with open(path, "r", encoding="utf-8", errors="ignore") as fh:
                text = fh.read()
            new_docs.append((os.path.basename(path), text))
        except OSError:
            pass

    if new_docs:
        bot.add_documents(new_docs)

    return _doc_status_md()


def reset_docs() -> str:
    """Removes all uploaded documents, restoring only the default corpus."""
    bot.reset_to_default_docs()
    return _doc_status_md()


# -----------------------------------------------------------
# UI layout
# -----------------------------------------------------------

with gr.Blocks(title="ContextIQ") as demo:

    gr.Markdown("# ContextIQ")
    gr.Markdown(
        "Context-aware documentation retrieval and AI-powered Q&A "
        "for developer knowledge bases."
    )

    with gr.Row():

        # --- Left panel: controls ---
        with gr.Column(scale=1, min_width=240):
            gr.Markdown("### Settings")

            provider_dd = gr.Dropdown(
                choices=PROVIDER_NAMES or ["None"],
                value=PROVIDER_NAMES[0] if PROVIDER_NAMES else "None",
                label="AI Provider",
                interactive=bool(PROVIDER_NAMES),
            )
            mode_dd = gr.Dropdown(
                choices=MODES,
                value="RAG",
                label="Mode",
            )

            gr.Markdown("---")
            gr.Markdown(_provider_status_md())
            gr.Markdown(
                "**Mode guide**\n"
                "- **RAG** — retrieval + AI synthesis\n"
                "- **Naive LLM** — AI only, no retrieval\n"
                "- **Retrieval Only** — raw snippets, no AI"
            )

            gr.Markdown("---")
            gr.Markdown("### Custom Documents")
            gr.Markdown(
                "Upload `.md` or `.txt` files to extend the knowledge base. "
                "Try `sample_uploads/DEPLOYMENT.md` to see the hit rate improve."
            )

            file_upload = gr.File(
                file_types=[".md", ".txt"],
                file_count="multiple",
                label="Upload docs",
            )
            doc_status = gr.Markdown(_doc_status_md())
            reset_btn = gr.Button("Reset to default docs", size="sm")

        # --- Right panel: chat ---
        with gr.Column(scale=3):
            chatbot = gr.Chatbot(
                label="ContextIQ",
                height=440,
                placeholder=(
                    "Ask anything about the docs — "
                    "e.g. *Where is the auth token generated?*"
                ),
                buttons=["copy_all"],
            )

            with gr.Row():
                msg_box = gr.Textbox(
                    placeholder="Ask a question about the docs...",
                    show_label=False,
                    scale=5,
                    autofocus=True,
                    submit_btn=False,
                )
                send_btn = gr.Button("Send", variant="primary", scale=1)

            clear_btn = gr.Button("Clear conversation", size="sm")

    # --- Event wiring ---
    send_btn.click(
        respond,
        inputs=[msg_box, chatbot, provider_dd, mode_dd],
        outputs=[chatbot],
    ).then(lambda: "", outputs=[msg_box])

    msg_box.submit(
        respond,
        inputs=[msg_box, chatbot, provider_dd, mode_dd],
        outputs=[chatbot],
    ).then(lambda: "", outputs=[msg_box])

    clear_btn.click(lambda: [], outputs=[chatbot])

    file_upload.change(upload_docs, inputs=[file_upload], outputs=[doc_status])
    reset_btn.click(reset_docs, outputs=[doc_status])


if __name__ == "__main__":
    demo.launch(theme=gr.themes.Soft())
