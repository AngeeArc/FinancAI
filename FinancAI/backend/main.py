# backend/main.py
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Literal

import subprocess

from .finance_logic import compute_financial_score, generate_budget
from .chatbot import get_llm_explanation   # <- Groq / OpenAI / HF helper


app = FastAPI()

# Allow frontend access
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---------------------------
# Pydantic models for /generate
# ---------------------------

class VariableItem(BaseModel):
    name: str
    amount: float


class GenerateRequest(BaseModel):
    monthly_income: float
    fixed_expenses: float

    # Frontend can send a total, but we will recompute from breakdown
    variable_expenses: float
    variable_breakdown: List[VariableItem] = []

    debt_monthly_payment: float
    debt_total_balance: float
    savings_monthly: float
    savings_total: float

    # "super" | "normal" | "relaxed"
    budget_mode: Literal["super", "normal", "relaxed"] = "normal"


# ---------------------------
# 1) FINANCIAL SCORE ENDPOINT (simple, totals only)
# ---------------------------

@app.post("/score")
async def score(payload: dict):
    """
    Simple scoring endpoint (legacy).
    Expects a dict with the same keys as compute_financial_score payload.
    """
    try:
        result = compute_financial_score(payload)
        return {"result": result}
    except Exception as e:
        return {"error": str(e)}


# ---------------------------
# 2) FULL PIPELINE ENDPOINT: score + budget + LLM explanation
# ---------------------------

@app.post("/generate")
async def generate(req: GenerateRequest):
    """
    Main endpoint for the app.

    - Recomputes total variable expenses from variable_breakdown
    - Computes financial score (hardcoded logic)
    - Computes budget plan based on budget_mode (super / normal / relaxed)
    - Calls the LLM to generate a personalised explanation using:
        * score
        * budget_plan
        * variable breakdown
    """

    # 1) Recompute variable total from breakdown (defensive)
    breakdown_total = sum(item.amount for item in req.variable_breakdown)
    variable_total = breakdown_total if breakdown_total > 0 else req.variable_expenses

    # 2) Build payload for hardcoded logic (only numeric totals)
    scoring_input = {
        "monthly_income": req.monthly_income,
        "fixed_expenses": req.fixed_expenses,
        "variable_expenses": variable_total,
        "debt_monthly_payment": req.debt_monthly_payment,
        "debt_total_balance": req.debt_total_balance,
        "savings_monthly": req.savings_monthly,
        "savings_total": req.savings_total,
        "emergency_months_target": 3,
    }

    # 3) Deterministic score + budget
    score = compute_financial_score(scoring_input)
    budget = generate_budget(scoring_input, mode=req.budget_mode)

    # 4) Build input for LLM (includes detailed variable breakdown)
    llm_input = {
        "inputs": scoring_input,
        "score": score,
        "budget_plan": budget,
        "budget_mode": req.budget_mode,
        "spending_patterns": {
            "variable_total": variable_total,
            "breakdown": [
                {"name": item.name, "amount": item.amount}
                for item in req.variable_breakdown
            ],
        },
    }

    explanation = get_llm_explanation(llm_input)

    return {
        "score": score,
        "budget": budget,
        "llm_explanation": explanation,
    }


# ---------------------------
# 3) CHATBOT ENDPOINT (your old Ollama-based chat)
#     – left as-is for now
# ---------------------------

@app.post("/chat")
async def chat(payload: dict):
    user_msg = payload.get("message", "")

    if not user_msg.strip():
        return {"response": "Please enter a message."}

    try:
        # Call Ollama (make sure model exists: mistral/llama3/etc.)
        process = subprocess.Popen(
            ["ollama", "run", "mistral"],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )

        output, _ = process.communicate(user_msg)

        return {"response": output}

    except Exception as e:
        return {"response": f"Error talking to Ollama: {e}"}
