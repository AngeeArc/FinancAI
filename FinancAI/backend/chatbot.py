# backend/chatbot.py
import requests

OLLAMA_URL = "http://localhost:11434/api/chat"
MODEL_NAME = "llama3.1"

BACKEND_SCORE_URL = "http://localhost:8000/score"

def ask_llm(user_msg: str, memory=None):

    system_prompt = """
You are a financial assistant.

You CAN request real numeric financial calculations from the backend by calling:
POST /score  with a JSON body containing fields like:
- monthly_income
- fixed_expenses
- variable_expenses
- debt_monthly_payment
- debt_total_balance
- savings_monthly
- savings_total
- emergency_months_target

If the user asks:
- “am I overspending?”
- “evaluate my finances”
- “compute my score”
- “how am I doing financially?”

Send a request to the /score endpoint and use the returned JSON to answer.
NEVER guess numbers — always ask the backend when calculations are needed.
"""

    payload = {
        "model": MODEL_NAME,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_msg}
        ],
        "stream": False
    }

    try:
        r = requests.post(OLLAMA_URL, json=payload).json()
        return r.get("message", {}).get("content", "No response.")
    except Exception as e:
        return f"LLM error: {e}"
