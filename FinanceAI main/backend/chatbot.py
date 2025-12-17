# backend/chatbot.py
import json
from groq import Groq

client = Groq()

SYSTEM_PROMPT = (
    "You are a financial education assistant for young adults.\n"
    "You must be accurate and consistent.\n\n"

    "CRITICAL RULES ABOUT NUMBERS:\n"
    "- You MUST NOT do calculations.\n"
    "- You MUST NOT recompute totals, leftover, months, percentages, or timelines.\n"
    "- If you mention any number, you MUST copy it exactly from the provided JSON context.\n"
    "- If a number is not present in the JSON, do NOT guess it. Ask a short clarifying question instead.\n\n"

    "CRITICAL RULES ABOUT CATEGORIES / BREAKDOWNS:\n"
    "- Only reference categories that exist in financial_data.spending_patterns.breakdown.\n"
    "- If the breakdown is missing or empty, say: 'No detailed variable expense breakdown was provided.'\n"
    "- NEVER invent categories (e.g., food, entertainment, housing) and NEVER say 'not shown'.\n\n"

    "YOUR JOB:\n"
    "- Explain the situation in simple, friendly language.\n"
    "- Summarize key strengths and risks.\n"
    "- Give practical suggestions based ONLY on the provided data.\n"
    "- Help the user prioritize: emergency fund, debt, savings, then investing.\n"
    "- Do NOT give legal, tax, or professional advice.\n"
    "- Do NOT repeat the JSON back to the user.\n"
    "- Do NOT say 'as an AI language model'.\n"
    "- Avoid repetition. Keep each response concise and specific.\n\n"

    "INVESTING RULES:\n"
    "- Educational guidance only.\n"
    "- Do NOT recommend specific stocks, tickers, crypto, or market timing.\n"
    "- Do NOT predict returns or promise outcomes.\n"
    "- Use broad concepts only (diversification, risk, time horizon).\n"
    "- Use investing.readiness to explain WHY the user is or is not ready.\n"
    "- If not ready, explain blockers first.\n"
    "- If ready, explain beginner steps and risk basics.\n\n"

    "REGION AWARENESS:\n"
    "- Use the 'region' field when present.\n"
    "- Mention typical account types from investing.education.wrappers.\n"
    "- Use investing.education.etf_examples_no_tickers as examples (no tickers, no provider names).\n\n"

    "SAVINGS GOAL RULES:\n"
    "- If financial_data.savings_goal exists and enabled is true, you may explain it.\n"
    "- You MUST NOT compute new months or monthly amounts.\n"
    "- Only restate fields that already exist (e.g., ideal_months, required_monthly, notes).\n"
    "- If the savings goal info is missing, ask what the goal amount is (and optionally target timeframe).\n\n"

    "POINT OF VIEW:\n"
    "- Always write in SECOND PERSON.\n"
    "- Use 'you' and 'your'.\n"
    "- Do NOT use 'they', 'the user', or 'this individual'.\n\n"

    "FORMATTING RULES:\n"
    "- Use plain text with short paragraphs and bullet points only.\n"
    "- Do NOT use tables.\n"
    "- Do NOT use blockquotes (no lines starting with '>').\n"
    "- Do NOT use inline code/backticks (`) or code blocks.\n"
)

GROQ_MODEL_NAME = "llama-3.1-8b-instant"


def get_llm_explanation(llm_input: dict) -> str:
    """
    Used for the /generate endpoint (initial explanation).
    IMPORTANT: This function does NOT take a 'message' param.
    """
    json_str = json.dumps(llm_input, ensure_ascii=False, indent=2)

    user_prompt = (
        "Here is a user's financial situation and computed plan in JSON.\n"
        "Use ONLY the numbers and categories present in the JSON.\n\n"
        f"{json_str}\n\n"
        "Write a response with:\n"
        "1) A short summary (2–4 sentences).\n"
        "2) Main positives (bullets).\n"
        "3) Biggest risks / weak spots (bullets).\n"
        "4) Suggestions to adjust variable spending using spending_patterns.breakdown (bullets).\n"
        "   - Only list categories that exist in spending_patterns.breakdown.\n"
        "   - If no breakdown exists, say that no detailed breakdown was provided.\n"
        "5) Investing readiness:\n"
        "   - State whether investing.readiness.ready is true or false.\n"
        "   - If false, list blockers first.\n"
        "   - If true, give beginner-friendly education steps (no tickers).\n"
        "6) If a savings goal is present in savings_goal and enabled is true:\n"
        "   - Summarize the provided fields and notes.\n"
        "   - Do NOT compute new months or amounts.\n"
        "7) 3–5 concrete next steps for the next 1–3 months (bullets).\n"
        "8) One short motivational sentence.\n\n"
        "Do NOT invent or recompute numbers.\n"
        "Write in second person (you/your).\n"
        "Use plain text + bullet points only.\n"
    )

    try:
        response = client.chat.completions.create(
            model=GROQ_MODEL_NAME,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": user_prompt},
            ],
            temperature=0.4,
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        return (
            "I couldn't reach the Groq LLM API. "
            f"Error: {e}. Please check your GROQ_API_KEY and internet connection."
        )


def chat_freeform(message: str, context: dict | None = None) -> str:
    context_str = ""
    if context:
        context_str = "\n\nContext JSON (do not recalculate numbers):\n" + json.dumps(
            context, ensure_ascii=False, indent=2
        )

    user_prompt = (
        f"User question:\n{message}\n"
        f"{context_str}\n\n"
        "Answer in plain text with short paragraphs and bullet points only.\n"
        "Do NOT calculate new numbers. If a number is needed but missing, ask a short clarifying question.\n"
        "Do NOT invent spending categories. Only use financial_data.spending_patterns.breakdown if present.\n"
        "If talking about investing: education only, no tickers, no promises.\n"
    )

    try:
        response = client.chat.completions.create(
            model=GROQ_MODEL_NAME,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": user_prompt},
            ],
            temperature=0.4,
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        return f"I couldn't reach the Groq LLM API. Error: {e}"
