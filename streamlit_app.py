import streamlit as st
import json
import re
import requests

CLAUDE_API_KEY = st.secrets["CLAUDE_API_KEY"]

SYSTEM_PROMPT = """
You are a personal English coach.

For each user message, do exactly two things:

1. Write ONLY a short natural conversational reply (do NOT mention corrections or mistakes in this text).

2. At the very end, add a <json> block with the correction and mistakes:
<json>
{
  "correction": "the fully corrected sentence",
  "mistakes": [
    {"type": "grammar", "original": "wrong phrase", "correct": "right phrase"}
  ]
}
</json>

Never explain corrections in the text. All correction data goes exclusively in the <json> block.
"""

st.set_page_config(page_title="The Academic Atelier", page_icon="📝", layout="wide")

st.markdown("""
<link href="https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;500;600;700;800&family=Manrope:wght@400;500;600;700&display=swap" rel="stylesheet">
<style>
    #MainMenu, footer { visibility: hidden; }
    .stDeployButton { display: none; }

    html, body, .stApp {
        background-color: #f7fafc !important;
        font-family: 'Manrope', sans-serif;
    }
    .block-container {
        padding: 1.5rem 2rem 0.5rem 2rem !important;
        max-width: 100% !important;
    }

    /* ── Header ── */
    .atelier-header {
        display: flex;
        align-items: center;
        gap: 10px;
        margin-bottom: 1.2rem;
    }
    .atelier-header h1 {
        font-family: 'Plus Jakarta Sans', sans-serif;
        font-size: 1.35rem;
        font-weight: 800;
        color: #00306b;
        letter-spacing: -0.02em;
        margin: 0;
    }
    .atelier-header .icon {
        width: 36px; height: 36px;
        background: linear-gradient(135deg, #005394, #2b6cb0);
        border-radius: 10px;
        display: flex; align-items: center; justify-content: center;
        color: white; font-size: 1.1rem;
    }

    /* ── Zones ── */
    .zone {
        background: #ffffff;
        border-radius: 1.5rem;
        padding: 1.1rem 1.3rem;
        margin-bottom: 1rem;
    }
    .zone-label {
        font-family: 'Manrope', sans-serif;
        font-size: 0.7rem;
        font-weight: 800;
        letter-spacing: 0.1em;
        text-transform: uppercase;
        color: #005394;
        display: flex;
        align-items: center;
        gap: 6px;
        margin-bottom: 0.6rem;
    }
    .badge {
        background: #8ef5b5;
        color: #00522f;
        font-size: 0.6rem;
        font-weight: 800;
        letter-spacing: 0.08em;
        padding: 2px 8px;
        border-radius: 999px;
        text-transform: uppercase;
    }

    /* ── Corrected sentence zone ── */
    .original-text {
        color: #727782;
        font-style: italic;
        font-size: 0.88rem;
        margin-bottom: 0.5rem;
        line-height: 1.6;
    }
    .corrected-box {
        background: #f1f4f6;
        border-left: 4px solid #006d40;
        border-radius: 0.75rem;
        padding: 0.75rem 1rem;
        font-size: 0.95rem;
        font-weight: 600;
        color: #181c1e;
        line-height: 1.6;
    }
    .empty-corrected {
        color: #c1c7d2;
        font-style: italic;
        font-size: 0.85rem;
    }

    /* ── Chat zone ── */
    .chat-scroll {
        max-height: 320px;
        overflow-y: auto;
        scrollbar-width: none;
    }
    .chat-scroll::-webkit-scrollbar { display: none; }
    .chat-msg-user {
        display: flex;
        justify-content: flex-end;
        margin-bottom: 0.75rem;
    }
    .chat-msg-user .bubble {
        background: linear-gradient(135deg, #005394, #2b6cb0);
        color: white;
        border-radius: 1.2rem 1.2rem 0.25rem 1.2rem;
        padding: 0.65rem 1rem;
        max-width: 80%;
        font-size: 0.88rem;
        line-height: 1.5;
    }
    .chat-msg-assistant {
        display: flex;
        gap: 10px;
        margin-bottom: 0.75rem;
        align-items: flex-start;
    }
    .ai-avatar {
        width: 32px; height: 32px; min-width: 32px;
        background: linear-gradient(135deg, #005394, #2b6cb0);
        border-radius: 50%;
        display: flex; align-items: center; justify-content: center;
        font-size: 0.85rem;
    }
    .chat-msg-assistant .bubble {
        background: #f1f4f6;
        color: #181c1e;
        border-radius: 1.2rem 1.2rem 1.2rem 0.25rem;
        padding: 0.65rem 1rem;
        max-width: 85%;
        font-size: 0.88rem;
        line-height: 1.6;
    }
    .chat-empty {
        color: #c1c7d2;
        font-style: italic;
        font-size: 0.85rem;
        text-align: center;
        padding: 2rem 0;
    }

    /* ── Error breakdown sidebar ── */
    .sidebar-zone {
        background: #ebeef0;
        border-radius: 1.5rem;
        overflow: hidden;
        height: 100%;
    }
    .sidebar-header {
        background: #e5e9eb;
        padding: 0.9rem 1.1rem;
        display: flex;
        align-items: center;
        gap: 8px;
    }
    .sidebar-header h2 {
        font-family: 'Plus Jakarta Sans', sans-serif;
        font-size: 0.95rem;
        font-weight: 700;
        color: #181c1e;
        margin: 0;
    }
    .sidebar-icon { color: #a70819; font-size: 1rem; }
    .sidebar-scroll {
        padding: 0.75rem;
        max-height: 420px;
        overflow-y: auto;
        scrollbar-width: none;
    }
    .sidebar-scroll::-webkit-scrollbar { display: none; }
    .error-card {
        background: #ffffff;
        border-radius: 1rem;
        padding: 0.8rem 0.9rem;
        margin-bottom: 0.6rem;
        display: flex;
        gap: 10px;
        align-items: flex-start;
    }
    .error-pill {
        width: 4px;
        min-width: 4px;
        height: 48px;
        background: #a70819;
        border-radius: 4px;
    }
    .error-type {
        font-size: 0.62rem;
        font-weight: 800;
        letter-spacing: 0.1em;
        text-transform: uppercase;
        color: #a70819;
        margin-bottom: 2px;
    }
    .error-original {
        font-size: 0.78rem;
        font-weight: 600;
        color: #181c1e;
        margin-bottom: 3px;
    }
    .error-desc {
        font-size: 0.75rem;
        color: #414750;
        line-height: 1.5;
    }
    .error-correct {
        font-weight: 700;
        color: #006d40;
    }
    .no-errors {
        background: #ffffff;
        border-radius: 1rem;
        padding: 1.5rem 1rem;
        text-align: center;
        color: #c1c7d2;
        font-style: italic;
        font-size: 0.82rem;
    }

    /* ── Input area ── */
    .stChatInput > div {
        background: #ffffff !important;
        border-radius: 1.5rem !important;
        border: 1.5px solid #e5e9eb !important;
        box-shadow: 0 4px 24px rgba(0,83,148,0.06) !important;
    }
    .stChatInput textarea {
        font-family: 'Manrope', sans-serif !important;
        font-size: 0.9rem !important;
        color: #181c1e !important;
    }
</style>
""", unsafe_allow_html=True)

# ── Helpers ───────────────────────────────────────────────────────────────────
def highlight_text(original, corrected, mistakes):
    orig_html = original
    corr_html = corrected
    for m in mistakes:
        wrong = m.get("original", "")
        right = m.get("correct", "")
        if wrong:
            orig_html = re.sub(
                re.escape(wrong),
                f'<span style="text-decoration:line-through;color:#a70819;font-weight:600">{wrong}</span>',
                orig_html, flags=re.IGNORECASE
            )
        if right:
            corr_html = re.sub(
                re.escape(right),
                f'<span style="color:#006d40;font-weight:700">{right}</span>',
                corr_html, flags=re.IGNORECASE
            )
    return orig_html, corr_html

# ── Session state ─────────────────────────────────────────────────────────────
if "messages" not in st.session_state:
    st.session_state.messages = []
if "last_correction" not in st.session_state:
    st.session_state.last_correction = None
if "last_mistakes" not in st.session_state:
    st.session_state.last_mistakes = []
if "last_user_msg" not in st.session_state:
    st.session_state.last_user_msg = None

# ── Header ────────────────────────────────────────────────────────────────────
st.markdown("""
<div class="atelier-header">
    <div class="icon">📝</div>
    <h1>The Academic Atelier</h1>
</div>
""", unsafe_allow_html=True)

# ── Main layout ───────────────────────────────────────────────────────────────
col_main, col_errors = st.columns([7, 3])

with col_main:
    # Zone 1 — Corrected sentence
    if st.session_state.last_correction and st.session_state.last_user_msg:
        orig_highlighted, corr_highlighted = highlight_text(
            st.session_state.last_user_msg,
            st.session_state.last_correction,
            st.session_state.last_mistakes
        )
        original_html = f'<div style="color:#727782;font-style:italic;font-size:0.88rem;margin-bottom:0.5rem;line-height:1.6;">"{orig_highlighted}"</div>'
        corrected_html = f'<div class="corrected-box">"{corr_highlighted}"</div>'
    else:
        original_html = ""
        corrected_html = ""

    st.markdown(f"""
    <div class="zone">
        <div class="zone-label">✦ Refined Input</div>
        {original_html}
        {corrected_html}
    </div>
    """, unsafe_allow_html=True)

    # Zone 2 — Chat
    msgs_html = ""
    if st.session_state.messages:
        for msg in st.session_state.messages:
            if msg["role"] == "user":
                msgs_html += f'<div class="chat-msg-user"><div class="bubble">{msg["content"]}</div></div>'
            else:
                msgs_html += f'<div class="chat-msg-assistant"><div class="ai-avatar">✦</div><div class="bubble">{msg["content"]}</div></div>'
    else:
        msgs_html = '<div style="color:#c1c7d2;font-style:italic;font-size:0.85rem;text-align:center;padding:2rem 0;">Ask the Atelier anything in English…</div>'

    st.markdown(f"""
    <div class="zone">
        <div class="zone-label">💬 Conversation</div>
        <div class="chat-scroll" id="chat-scroll">{msgs_html}</div>
    </div>
    <script>
        const el = document.getElementById("chat-scroll");
        if (el) el.scrollTop = el.scrollHeight;
    </script>
    """, unsafe_allow_html=True)

with col_errors:
    # Zone 4 — Error breakdown
    if st.session_state.last_mistakes:
        cards_html = ""
        for m in st.session_state.last_mistakes:
            cards_html += f"""
            <div class="error-card">
                <div class="error-pill"></div>
                <div>
                    <div class="error-type">{m.get('type', 'error')}</div>
                    <div class="error-original">"{m.get('original', '')}"</div>
                    <div class="error-desc">Should be: <span class="error-correct">{m.get('correct', '')}</span></div>
                </div>
            </div>"""
    else:
        cards_html = '<div style="padding:1.5rem 1rem;text-align:center;color:#c1c7d2;font-style:italic;font-size:0.82rem;">Errors will appear here after your first message.</div>'

    st.markdown(f"""
    <div class="sidebar-zone">
        <div class="sidebar-header">
            <span class="sidebar-icon">📊</span>
            <h2>Error Breakdown</h2>
        </div>
        <div class="sidebar-scroll">{cards_html}</div>
    </div>
    """, unsafe_allow_html=True)

# ── Input ─────────────────────────────────────────────────────────────────────
user_input = st.chat_input("Ask the Atelier anything in English…")

if user_input:
    st.session_state.last_user_msg = user_input
    st.session_state.messages.append({"role": "user", "content": user_input})

    with st.spinner(""):
        try:
            response = requests.post(
                "https://api.anthropic.com/v1/messages",
                headers={
                    "x-api-key": CLAUDE_API_KEY,
                    "anthropic-version": "2023-06-01",
                    "content-type": "application/json"
                },
                json={
                    "model": "claude-haiku-4-5-20251001",
                    "max_tokens": 1024,
                    "system": SYSTEM_PROMPT,
                    "messages": [{"role": "user", "content": user_input}]
                }
            )
            content = response.json().get("content", [{}])[0].get("text", "")
        except Exception as e:
            content = ""
            st.error(f"API error: {e}")

    try:
        json_match = re.search(r"<json>(.*?)</json>", content, re.DOTALL)
        if json_match:
            data = json.loads(json_match.group(1).strip())
            text_part = content[:json_match.start()].strip()
        else:
            data = {}
            text_part = content
    except Exception:
        data = {}
        text_part = content

    st.session_state.last_correction = data.get("correction", None)
    st.session_state.last_mistakes = data.get("mistakes", [])
    st.session_state.messages.append({"role": "assistant", "content": text_part})
    st.rerun()
