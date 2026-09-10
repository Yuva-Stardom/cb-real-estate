"""
app.py

Flask backend that serves the chat UI and talks to the Gemini API.
"""

import os
from flask import Flask, render_template, request, jsonify
import google.generativeai as genai
from dotenv import load_dotenv

from chatbot_config import SYSTEM_PROMPT

# Load environment variables from .env
load_dotenv()

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
MODEL_NAME = os.getenv("GEMINI_MODEL", "gemini-2.5-flash-lite")

if not GEMINI_API_KEY:
    raise RuntimeError(
        "GEMINI_API_KEY is not set. Please add it to your .env file."
    )

genai.configure(api_key=GEMINI_API_KEY)

app = Flask(__name__)

# Create the Gemini model once, with the system prompt baked in.
model = genai.GenerativeModel(
    model_name=MODEL_NAME,
    system_instruction=SYSTEM_PROMPT,
)

# In-memory chat sessions keyed by a simple session id from the client.
chat_sessions = {}


def get_chat_session(session_id: str):
    """Return an existing chat session or create a new one."""
    if session_id not in chat_sessions:
        chat_sessions[session_id] = model.start_chat(history=[])
    return chat_sessions[session_id]


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/chat", methods=["POST"])
def chat():
    data = request.get_json(silent=True) or {}
    user_message = (data.get("message") or "").strip()
    session_id = data.get("session_id") or "default"

    if not user_message:
        return jsonify({"reply": "Please type a message before sending."}), 400

    try:
        chat_session = get_chat_session(session_id)
        response = chat_session.send_message(user_message)
        reply_text = response.text.strip() if response.text else (
            "Sorry, I couldn't generate a response. Please try again."
        )
    except Exception as exc:  # noqa: BLE001
        app.logger.error("Gemini API error: %s", exc)
        reply_text = (
            "Something went wrong while contacting the AI service. "
            "Please try again in a moment."
        )

    return jsonify({"reply": reply_text})


@app.route("/reset", methods=["POST"])
def reset():
    data = request.get_json(silent=True) or {}
    session_id = data.get("session_id") or "default"
    chat_sessions.pop(session_id, None)
    return jsonify({"status": "reset"})


if __name__ == "__main__":
    app.run(debug=True)
