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

clients = load_available_clients()
bot = DocuBot(docs_folder=os.path.join(SCRIPT_DIR, "docs"))

MODES = ["RAG", "Naive LLM", "Retrieval Only"]
PROVIDER_NAMES = list(clients.keys())


def _status_md() -> str:
    if PROVIDER_NAMES:
        return "**Active:** " + " · ".join(PROVIDER_NAMES)
    return "**No providers active** — add API keys to `.env` and restart."


# -----------------------------------------------------------
# Chat handler
# -----------------------------------------------------------

def respond(message: str, history: list, provider_name: str, mode: str) -> list:
    if not message.strip():
        return history

    client = clients.get(provider_name)
    bot.llm_client = client  # swap provider before every call

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
        with gr.Column(scale=1, min_width=230):
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
            gr.Markdown(_status_md())
            gr.Markdown(
                "**Mode guide**\n"
                "- **RAG** — retrieval + AI synthesis\n"
                "- **Naive LLM** — AI only, no retrieval\n"
                "- **Retrieval Only** — raw snippets, no AI"
            )

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


if __name__ == "__main__":
    demo.launch(theme=gr.themes.Soft())
