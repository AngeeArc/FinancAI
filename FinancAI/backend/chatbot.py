# backend/chatbot.py
import json
import os
from groq import Groq

# Groq client reads GROQ_API_KEY from environment
client = Groq()

SYSTEM_PROMPT = (
    "You are a financial education assistant for young adults.\n"
    "You MUST NOT do any calculations or change any numeric values.\n"
    "All numbers (amounts, percentages, months, scores) in the JSON are "
    "already computed and correct.\n\n"
    "Your job:\n"
    "- Explain the situation in simple, friendly language.\n"
    "- Summarize key strengths and risks.\n"
    "- Use spending_patterns.breakdown to talk about where they are spending money "
    "and where they might cut back.\n"
    "- Give practical, realistic suggestions based ONLY on the provided data.\n"
    "- Do NOT give legal, tax, or investment advice. This is general budgeting "
    "education only.\n"
    "- Do NOT invent new numbers. If you mention numbers, copy them exactly "
    "from the JSON.\n"
)

# Use a free Groq-hosted model, e.g. Llama 3.1 8B
GROQ_MODEL_NAME = "llama-3.1-8b-instant"

def get_llm_explanation(llm_input: dict) -> str:
    """
    Call Groq's hosted LLM (server-based, free tier) to get a markdown explanation.
    """

    # Convert numeric results into JSON for the model to read
    json_str = json.dumps(llm_input, ensure_ascii=False, indent=2)

    user_prompt = (
        "Here is a user's financial situation and computed plan in JSON:\n\n"
        f"{json_str}\n\n"
        "Please respond in Markdown with:\n"
        "1. A short summary (2–4 sentences) of their situation.\n"
        "2. A bullet list: main positives in their current finances.\n"
        "3. A bullet list: biggest risks or weak spots.\n"
        "4. Suggestions to adjust their variable spending using spending_patterns.breakdown.\n"
        "5. 3–5 concrete next steps they can take in the next 1–3 months.\n"
        "6. One short motivational sentence at the end.\n\n"
        "Do NOT invent or recompute numbers. Use only the numbers from the JSON.\n"
    )

    try:
        response = client.chat.completions.create(
            model=GROQ_MODEL_NAME,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": user_prompt},
            ],
            temperature=0.6,
        )
    except Exception as e:
        return (
            "I couldn't reach the Groq LLM API. "
            f"Error: {e}. Please check your GROQ_API_KEY and internet connection."
        )

    return response.choices[0].message.content.strip()
