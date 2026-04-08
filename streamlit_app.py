import streamlit as st
import json
import re
import requests

CLAUDE_API_KEY = st.secrets["CLAUDE_API_KEY"]

SYSTEM_PROMPT = """
You are a personal English coach.

For each user message:
1. Correct the sentence
2. Explain briefly the mistake
3. Then reply naturally

At the very end, always include a JSON block wrapped in <json> tags like this:
<json>
{
  "correction": "...",
  "mistakes": [
    {"type": "grammar", "original": "...", "correct": "..."}
  ]
}
</json>

Keep it short.
"""

st.set_page_config(page_title="English Coach", page_icon="🇬🇧", layout="centered")

st.markdown("""
<style>
    .block-container { padding-top: 0.8rem; padding-bottom: 0; }
    h1 { margin-bottom: 0.3rem; font-size: 1.4rem; }
    h3 { margin: 0.2rem 0; font-size: 1rem; }
    hr { margin: 0.3rem 0; }
    .stAlert { padding: 0.3rem 0.6rem; font-size: 0.85rem; }
    .stChatMessage { padding: 0.3rem; }
</style>
""", unsafe_allow_html=True)

st.title("🇬🇧 English Coach")

if "messages" not in st.session_state:
    st.session_state.messages = []
if "last_correction" not in st.session_state:
    st.session_state.last_correction = None
if "last_mistakes" not in st.session_state:
    st.session_state.last_mistakes = []

# ── TOP : correction ──────────────────────────────────────────────────────────
st.markdown("### ✅ Corrected sentence")
if st.session_state.last_correction:
    st.success(st.session_state.last_correction)
else:
    st.info("Your corrected sentence will appear here.")

st.divider()

# ── MILIEU HAUT : corrections ─────────────────────────────────────────────────
st.markdown("### 📝 Corrections")
corrections_container = st.container(height=160)
with corrections_container:
    if st.session_state.last_mistakes:
        for m in st.session_state.last_mistakes:
            st.error(f"✗ {m.get('original', '')}")
            st.success(f"✓ {m.get('correct', '')}")
            st.caption(m.get("type", ""))
            st.divider()
    else:
        st.info("Corrections will appear here.")

st.divider()

# ── MILIEU BAS : conversation ─────────────────────────────────────────────────
st.markdown("### 💬 Conversation")
chat_container = st.container(height=220)
with chat_container:
    for msg in st.session_state.messages:
        with st.chat_message(msg["role"]):
            st.write(msg["content"])

# ── BOTTOM : saisie ───────────────────────────────────────────────────────────
user_input = st.chat_input("Write your message in English...")

if user_input:
    st.session_state.messages.append({"role": "user", "content": user_input})

    with st.spinner("Thinking..."):
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
