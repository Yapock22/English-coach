from flask import Flask, request, jsonify
import os
from dotenv import load_dotenv
import json
import datetime
import re
import requests  # Utilisé pour faire des requêtes HTTP

# 🔑 Charger variables d'environnement
load_dotenv()

app = Flask(__name__)
CLAUDE_API_KEY = os.getenv("CLAUDE_API_KEY")

# 🧠 Prompt IA
SYSTEM_PROMPT = """
You are a personal English coach.

For each user message:
1. Correct the sentence
2. Explain briefly the mistake
3. Then reply naturally

Also return a JSON at the end like this:
{
  "correction": "...",
  "mistakes": [
    {"type": "grammar", "original": "...", "correct": "..."}
  ]
}

Keep it short.
"""

# 💾 Sauvegarde des erreurs
def save_mistakes(user_input, mistakes):
    today = str(datetime.date.today())

    try:
        with open("data.json", "r") as f:
            data = json.load(f)
    except:
        data = {}

    if today not in data:
        data[today] = []

    data[today].append({
        "input": user_input,
        "mistakes": mistakes
    })

    with open("data.json", "w") as f:
        json.dump(data, f, indent=2)

# 💸 Calcul du coût réel
def calculate_cost(usage):
    input_cost = 0.00000015
    output_cost = 0.0000006

    prompt_tokens = usage.get("prompt_tokens", 0)
    completion_tokens = usage.get("completion_tokens", 0)

    return (prompt_tokens * input_cost) + (completion_tokens * output_cost)

# 💸 Mise à jour du budget
def update_usage(cost):
    try:
        with open("usage.json", "r") as f:
            usage = json.load(f)
    except:
        usage = {"total": 0}

    usage["total"] += cost

    with open("usage.json", "w") as f:
        json.dump(usage, f, indent=2)

    return usage["total"]

# 💬 Route chat
@app.route("/chat", methods=["POST"])
def chat():
    user_message = request.json.get("message")

    # Appel à l'API Claude
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
            "messages": [
                {"role": "user", "content": user_message}
            ]
        }
    )

    content = response.json().get("content", [{}])[0].get("text", "")

    # 🧠 Extraction JSON propre
    try:
        json_match = re.search(r"\{.*\}", content, re.DOTALL)

        if json_match:
            json_part = json_match.group()
            data = json.loads(json_part)
            text_part = content.replace(json_part, "").strip()
        else:
            data = {"mistakes": []}
            text_part = content

    except Exception as e:
        print("JSON ERROR:", e)
        data = {"mistakes": []}
        text_part = content

    # 💾 sauvegarde erreurs
    save_mistakes(user_message, data.get("mistakes", []))

    # 💸 calcul coût (à adapter selon le modèle de tarification de Claude)
    cost = calculate_cost({"prompt_tokens": len(user_message.split()), "completion_tokens": len(text_part.split())})
    total_spent = update_usage(cost)

    # 🚨 alertes budget
    warning = None

    if total_spent >= 10:
        return jsonify({
            "reply": "❌ Monthly budget reached.",
            "mistakes": []
        })

    elif total_spent >= 9.5:
        warning = "⚠️ You are close to your 10€ limit!"

    return jsonify({
        "reply": text_part,
        "mistakes": data.get("mistakes", []),
        "warning": warning,
        "total_spent": total_spent
    })

# 📊 Résumé quotidien
def generate_daily_summary():
    try:
        with open("data.json", "r") as f:
            data = json.load(f)
    except:
        return "No data yet."

    today = str(datetime.date.today())

    if today not in data:
        return "No activity today."

    mistakes = data[today]

    prompt = f"""
    Analyze this English learning data:

    {mistakes}

    Give:
    - main weaknesses
    - most common mistakes
    - 3 things to improve
    - 5 vocabulary words to review

    Keep it short and clear.
    """

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
            "messages": [{"role": "user", "content": prompt}]
        }
    )

    return response.json().get("content", [{}])[0].get("text", "")

# 📊 Route summary
@app.route("/summary", methods=["GET"])
def summary():
    result = generate_daily_summary()
    return jsonify({"summary": result})

# 🚀 Lancement serveur (TOUJOURS À LA FIN)
if __name__ == "__main__":
    print("Server starting...")
    app.run(debug=True)