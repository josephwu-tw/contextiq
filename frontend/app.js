/* ──────────────────────────────────────────────────────────
   ContextIQ — frontend
   Talks to the FastAPI backend at the same origin (/api/*)
────────────────────────────────────────────────────────── */

let providers = [];
let selectedProvider = "";
let selectedMode = "RAG";

// ── Init ────────────────────────────────────────────────────

async function init() {
  await loadProviders();
  await loadDocStatus();
  setupListeners();
}

// ── Providers ───────────────────────────────────────────────

async function loadProviders() {
  try {
    const res = await fetch("/api/providers");
    providers = await res.json();
  } catch {
    providers = [];
  }

  const select = document.getElementById("provider-select");
  select.innerHTML = "";

  for (const p of providers) {
    const opt = document.createElement("option");
    opt.value = p.name;
    opt.textContent = `${p.available ? "✓" : "✗"}  ${p.name}`;
    select.appendChild(opt);
  }

  selectedProvider = providers[0]?.name ?? "";
  renderProviderStatus(selectedProvider);
}

function renderProviderStatus(name) {
  const p = providers.find((p) => p.name === name);
  const el = document.getElementById("provider-status");
  if (!p) { el.textContent = ""; return; }

  if (p.available) {
    el.innerHTML = `<span class="status-ok">● ${p.name} is ready</span>`;
  } else {
    el.innerHTML =
      `<span class="status-err">● ${p.name} is unavailable — ` +
      `set <code>${p.key_name}</code> in .env and restart</span>`;
  }
}

// ── Doc status ──────────────────────────────────────────────

async function loadDocStatus() {
  try {
    const res = await fetch("/api/docs");
    const data = await res.json();
    document.getElementById("doc-status").textContent = data.message;
  } catch {
    document.getElementById("doc-status").textContent = "Could not load doc status.";
  }
}

// ── Event listeners ─────────────────────────────────────────

function setupListeners() {
  document.getElementById("provider-select").addEventListener("change", (e) => {
    selectedProvider = e.target.value;
    renderProviderStatus(selectedProvider);
  });

  document.getElementById("mode-select").addEventListener("change", (e) => {
    selectedMode = e.target.value;
  });

  document.getElementById("send-btn").addEventListener("click", sendMessage);

  document.getElementById("message-input").addEventListener("keydown", (e) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      sendMessage();
    }
  });

  document.getElementById("message-input").addEventListener("input", autoResize);

  document.getElementById("file-input").addEventListener("change", uploadFiles);

  document.getElementById("reset-btn").addEventListener("click", resetDocs);
}

function autoResize() {
  const el = document.getElementById("message-input");
  el.style.height = "auto";
  el.style.height = Math.min(el.scrollHeight, 160) + "px";
}

// ── Chat ────────────────────────────────────────────────────

async function sendMessage() {
  const input = document.getElementById("message-input");
  const message = input.value.trim();
  if (!message) return;

  // Remove welcome screen on first message
  document.getElementById("welcome")?.remove();

  input.value = "";
  input.style.height = "auto";

  appendMessage("user", message);
  const typingId = showTyping();

  const btn = document.getElementById("send-btn");
  btn.disabled = true;

  try {
    const res = await fetch("/api/chat", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        message,
        provider: selectedProvider,
        mode: selectedMode,
      }),
    });

    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      throw new Error(err.detail ?? `HTTP ${res.status}`);
    }

    const data = await res.json();
    hideTyping(typingId);
    appendMessage("assistant", data.answer);
  } catch (err) {
    hideTyping(typingId);
    appendMessage("assistant", `⚠️ Request failed: ${err.message}`);
  } finally {
    btn.disabled = false;
    input.focus();
  }
}

function appendMessage(role, text) {
  const messages = document.getElementById("messages");

  const wrap = document.createElement("div");
  wrap.className = `message ${role}`;

  const label = document.createElement("div");
  label.className = "role-label";
  label.textContent = role === "user" ? "You" : "ContextIQ";

  const bubble = document.createElement("div");
  bubble.className = "bubble";
  bubble.innerHTML = renderMarkdown(text);

  wrap.appendChild(label);
  wrap.appendChild(bubble);
  messages.appendChild(wrap);
  messages.scrollTop = messages.scrollHeight;
}

function showTyping() {
  const messages = document.getElementById("messages");
  const id = `typing-${Date.now()}`;

  const wrap = document.createElement("div");
  wrap.className = "message assistant typing";
  wrap.id = id;

  const label = document.createElement("div");
  label.className = "role-label";
  label.textContent = "ContextIQ";

  const bubble = document.createElement("div");
  bubble.className = "bubble";
  bubble.innerHTML =
    '<div class="dot"></div><div class="dot"></div><div class="dot"></div>';

  wrap.appendChild(label);
  wrap.appendChild(bubble);
  messages.appendChild(wrap);
  messages.scrollTop = messages.scrollHeight;
  return id;
}

function hideTyping(id) {
  document.getElementById(id)?.remove();
}

// ── Markdown renderer (no external deps) ────────────────────

function escapeHtml(text) {
  const el = document.createElement("div");
  el.textContent = text;
  return el.innerHTML;
}

function renderMarkdown(text) {
  let s = escapeHtml(text);
  // Fenced code blocks
  s = s.replace(/```[\w]*\n([\s\S]*?)```/g, "<pre><code>$1</code></pre>");
  // Inline code
  s = s.replace(/`([^`]+)`/g, "<code>$1</code>");
  // Bold
  s = s.replace(/\*\*(.*?)\*\*/g, "<strong>$1</strong>");
  // Italic
  s = s.replace(/\*(.*?)\*/g, "<em>$1</em>");
  // Line breaks (outside pre blocks)
  s = s.replace(/\n/g, "<br>");
  return s;
}

// ── Document management ──────────────────────────────────────

async function uploadFiles() {
  const input = document.getElementById("file-input");
  if (!input.files.length) return;

  const formData = new FormData();
  for (const f of input.files) formData.append("files", f);

  setDocStatus("Uploading…");

  try {
    const res = await fetch("/api/docs/upload", { method: "POST", body: formData });
    const data = await res.json();
    setDocStatus(data.message);
  } catch (err) {
    setDocStatus(`Upload failed: ${err.message}`);
  }

  input.value = "";
}

async function resetDocs() {
  setDocStatus("Resetting…");
  try {
    const res = await fetch("/api/docs/reset", { method: "POST" });
    const data = await res.json();
    setDocStatus(data.message);
  } catch (err) {
    setDocStatus(`Reset failed: ${err.message}`);
  }
}

function setDocStatus(msg) {
  document.getElementById("doc-status").textContent = msg;
}

// ── Start ────────────────────────────────────────────────────
init();
