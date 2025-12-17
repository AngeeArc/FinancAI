# backend/main.py
from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from typing import List, Literal, Optional, Dict, Any
import hashlib
import json
import math
import re

from .finance_logic import compute_financial_score, generate_budget
from .chatbot import get_llm_explanation, chat_freeform

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


# ------------------------------------------------------------
# Helpers: region inference
# ------------------------------------------------------------
def infer_region(country: Optional[str], currency: str) -> str:
    if country:
        c = country.strip().lower()

        us_alias = {"united states", "usa", "us", "america"}
        uk_alias = {"united kingdom", "uk", "britain", "great britain", "england", "scotland", "wales", "northern ireland"}
        in_alias = {"india", "bharat"}
        jp_alias = {"japan"}

        if c in us_alias:
            return "US"
        if c in uk_alias:
            return "UK"
        if c in in_alias:
            return "IN"
        if c in jp_alias:
            return "JP"

        eu_countries = {
            "germany","france","spain","italy","netherlands","belgium","austria","ireland",
            "finland","sweden","denmark","portugal","poland","czech republic","greece","romania",
            "hungary","slovakia","slovenia","croatia","bulgaria","latvia","lithuania","estonia",
            "luxembourg","malta","cyprus"
        }
        if c in eu_countries:
            return "EU"

    cur = (currency or "").upper().strip()
    if cur.startswith("USD"):
        return "US"
    if cur.startswith("CAD"):
        return "CA"
    if cur.startswith("AUD"):
        return "AU"
    if cur.startswith("EUR"):
        return "EU"
    if cur.startswith("GBP"):
        return "UK"
    if cur.startswith("JPY"):
        return "JP"
    if cur.startswith("INR"):
        return "IN"
    return "GLOBAL"


def safe_div(n: float, d: float) -> float:
    return (n / d) if d else 0.0


# ------------------------------------------------------------
# Investing readiness
# ------------------------------------------------------------
def investment_readiness(
    *,
    score_state: str,
    emergency_months: float,
    leftover: float,
    recommended_savings: float,
) -> Dict[str, Any]:
    blockers: List[str] = []
    reasons: List[str] = []

    if emergency_months < 1:
        blockers.append("Emergency fund is below 1 month of expenses.")
    elif emergency_months < 3:
        reasons.append("Emergency fund is between 1–3 months (okay to start small, keep building it).")
    else:
        reasons.append("Emergency fund is 3+ months (solid foundation).")

    if score_state in ["critical", "vulnerable"]:
        blockers.append(f"Financial state is '{score_state}' — stabilize budget before investing.")
    else:
        reasons.append(f"Financial state is '{score_state}' (stable enough).")

    if leftover < 0:
        blockers.append("Your monthly budget is negative (expenses exceed income).")
    elif leftover == 0:
        if recommended_savings > 0:
            reasons.append("You have no extra leftover, but you can invest by redirecting part of your planned savings.")
        else:
            blockers.append("No positive monthly cash flow or savings available to invest.")
    else:
        reasons.append("Positive monthly cash flow available.")

    return {"ready": len(blockers) == 0, "blockers": blockers, "reasons": reasons}


def region_investing_education(region: str) -> Dict[str, Any]:
    if region == "US":
        return {
            "wrappers": ["401(k)", "IRA / Roth IRA", "Taxable brokerage account"],
            "etf_examples_no_tickers": [
                "Total-market equity index fund",
                "Global equity index fund",
                "Broad bond index fund",
            ],
        }
    if region == "EU":
        return {
            "wrappers": ["Country-specific tax-advantaged accounts", "Pension schemes", "Brokerage account"],
            "etf_examples_no_tickers": [
                "All-world equity index fund",
                "Regional equity index fund",
                "Government + investment-grade bond fund",
            ],
        }
    if region == "IN":
        return {
            "wrappers": ["Mutual fund SIP", "Provident / retirement accounts", "Brokerage account"],
            "etf_examples_no_tickers": [
                "Broad Indian equity index fund",
                "Diversified equity index fund",
                "Short-duration or broad bond fund",
            ],
        }

    return {
        "wrappers": ["Tax-advantaged retirement account (if available)", "Brokerage account"],
        "etf_examples_no_tickers": [
            "Global equity index fund",
            "Balanced stock/bond fund",
            "Broad bond index fund",
        ],
    }


def portfolio_allocation_dynamic(
    *,
    score_state: str,
    emergency_months: float,
    savings_rate: float,
    debt_to_income: float,
) -> Dict[str, int]:
    if score_state in ["critical", "vulnerable"]:
        return {"stocks_pct": 0, "bonds_pct": 0, "cash_pct": 100}

    if emergency_months < 3 or debt_to_income > 0.30:
        return {"stocks_pct": 40, "bonds_pct": 50, "cash_pct": 10}

    if savings_rate < 0.15:
        return {"stocks_pct": 60, "bonds_pct": 35, "cash_pct": 5}

    return {"stocks_pct": 80, "bonds_pct": 20, "cash_pct": 0}


def ascii_portfolio(allocation: Dict[str, int]) -> str:
    def bar(p: float) -> str:
        blocks = int(p / 5)
        return "█" * blocks + "░" * (20 - blocks)

    return (
        f"Stocks  {allocation['stocks_pct']:>3}% |{bar(allocation['stocks_pct'])}|\n"
        f"Bonds   {allocation['bonds_pct']:>3}% |{bar(allocation['bonds_pct'])}|\n"
        f"Cash    {allocation['cash_pct']:>3}% |{bar(allocation['cash_pct'])}|"
    )


def strip_visual_from_financial_data(financial_data: Any) -> Any:
    try:
        if not isinstance(financial_data, dict):
            return financial_data

        fd = dict(financial_data)
        inv = fd.get("investing")

        if isinstance(inv, dict):
            inv2 = dict(inv)
            inv2.pop("allocation_visual", None)
            fd["investing"] = inv2

        return fd
    except Exception:
        return financial_data


# ------------------------------------------------------------
# Savings goal: ideal timeline WITHOUT requiring goal months
# ------------------------------------------------------------
def compute_goal_timeline_ideal(
    *,
    goal_cost: Optional[float],
    currency: str,
    recommended_savings: float,
    leftover: float,
    current_monthly_savings: float,
) -> Dict[str, Any]:
    if not goal_cost or goal_cost <= 0:
        return {
            "enabled": False,
            "goal_cost": goal_cost,
            "currency": currency,
            "planned_monthly_capacity": None,
            "current_monthly_savings": None,
            "ideal_months_using_planned_savings": None,
            "ideal_months_using_current_savings": None,
            "notes": ["Add a goal amount to estimate an ideal timeline."],
        }

    planned_capacity = max(0.0, recommended_savings) + max(0.0, leftover)
    current_capacity = max(0.0, current_monthly_savings)

    months_planned = math.ceil(goal_cost / planned_capacity) if planned_capacity > 0 else None
    months_current = math.ceil(goal_cost / current_capacity) if current_capacity > 0 else None

    notes: List[str] = []
    if planned_capacity > 0 and months_planned is not None:
        notes.append(f"Using your planned savings capacity, you could reach the goal in about {months_planned} months.")
    else:
        notes.append("Your planned savings capacity is 0, so a timeline can't be estimated until savings increases.")

    if current_capacity > 0 and months_current is not None:
        notes.append(f"Using your current monthly savings input, you could reach the goal in about {months_current} months.")
    else:
        notes.append("Your current monthly savings input is 0, so a timeline can't be estimated from current savings.")

    return {
        "enabled": True,
        "goal_cost": goal_cost,
        "currency": currency,
        "planned_monthly_capacity": planned_capacity,
        "current_monthly_savings": current_capacity,
        "ideal_months_using_planned_savings": months_planned,
        "ideal_months_using_current_savings": months_current,
        "notes": notes,
    }


def looks_like_goal_timeline_question(msg: str) -> bool:
    if not msg:
        return False
    m = msg.lower().strip()
    patterns = [
        r"\bhow long\b",
        r"\bhow many months\b",
        r"\bhow fast\b",
        r"\btime to\b",
        r"\bsave up\b",
        r"\breach (my )?goal\b",
        r"\bwhen can i\b",
    ]
    return any(re.search(p, m) for p in patterns)


def format_goal_timeline_response(goal_obj: Dict[str, Any]) -> str:
    if not goal_obj.get("enabled"):
        return "To estimate a timeline, enter a savings goal amount in the Savings Goal section and click Generate."

    cur = goal_obj.get("currency", "")
    goal_cost = goal_obj.get("goal_cost", 0)

    planned_cap = goal_obj.get("planned_monthly_capacity", 0)
    current_save = goal_obj.get("current_monthly_savings", 0)

    m_planned = goal_obj.get("ideal_months_using_planned_savings")
    m_current = goal_obj.get("ideal_months_using_current_savings")

    lines = []
    lines.append("Savings goal timeline (estimated using your computed plan):")
    lines.append(f"- Goal amount: {goal_cost} {cur}")
    lines.append(f"- Planned savings capacity per month (recommended savings + leftover): {planned_cap:.2f} {cur}")
    lines.append(f"- Ideal time using planned savings: about {m_planned} months" if m_planned is not None else "- Ideal time using planned savings: not available (capacity is 0)")
    lines.append(f"- Your current monthly savings input: {current_save:.2f} {cur}")
    lines.append(f"- Ideal time using current savings: about {m_current} months" if m_current is not None else "- Ideal time using current savings: not available (current savings is 0)")
    return "\n".join(lines)


# ------------------------------------------------------------
# Models
# ------------------------------------------------------------
class VariableItem(BaseModel):
    name: str
    amount: float = Field(ge=0)


class GenerateRequest(BaseModel):
    currency: str = "USD"
    country: Optional[str] = None

    monthly_income: float = Field(ge=0)
    fixed_expenses: float = Field(ge=0)

    variable_expenses: float = Field(ge=0)
    variable_breakdown: List[VariableItem] = []

    debt_monthly_payment: float = Field(ge=0)
    debt_total_balance: float = Field(ge=0)

    savings_monthly: float = Field(ge=0)
    savings_total: float = Field(ge=0)

    budget_mode: Literal["super", "normal", "relaxed"] = "normal"

    savings_goal_cost: Optional[float] = None
    savings_goal_months: Optional[int] = None
    savings_goal_name: Optional[str] = None 


# ------------------------------------------------------------
# Endpoint: generate
# ------------------------------------------------------------
@app.post("/generate")
async def generate(req: GenerateRequest) -> Dict[str, Any]:
    breakdown_total = sum(v.amount for v in req.variable_breakdown)
    variable_total = breakdown_total if breakdown_total > 0 else req.variable_expenses

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

    score_obj = compute_financial_score(scoring_input)
    budget_obj = generate_budget(scoring_input, mode=req.budget_mode)

    region = infer_region(req.country, req.currency)

    recommended_savings = float(budget_obj.get("totals", {}).get("recommended_savings", 0.0))
    leftover = float(budget_obj.get("totals", {}).get("leftover", 0.0))
    emergency_months = float(score_obj.get("components", {}).get("emergency_fund_months", 0.0))

    readiness = investment_readiness(
        score_state=score_obj.get("state", "unknown"),
        emergency_months=emergency_months,
        leftover=leftover,
        recommended_savings=recommended_savings,
    )

    savings_rate = safe_div(req.savings_monthly, req.monthly_income)
    debt_to_income = safe_div(req.debt_monthly_payment, req.monthly_income)

    education = region_investing_education(region)

    allocation = portfolio_allocation_dynamic(
        score_state=score_obj.get("state", "unknown"),
        emergency_months=emergency_months,
        savings_rate=savings_rate,
        debt_to_income=debt_to_income,
    )
    allocation_visual = ascii_portfolio(allocation)

    savings_goal = compute_goal_timeline_ideal(
        goal_cost=req.savings_goal_cost,
        currency=req.currency,
        recommended_savings=recommended_savings,
        leftover=leftover,
        current_monthly_savings=float(req.savings_monthly),
    )

    if savings_goal.get("enabled") and getattr(req, "savings_goal_name", None):
        savings_goal["goal_name"] = req.savings_goal_name
    

    plan_fingerprint = {
        "currency": req.currency,
        "country": req.country,
        "mode": req.budget_mode,
        "income": req.monthly_income,
        "fixed": req.fixed_expenses,
        "variable": variable_total,
        "debt": req.debt_monthly_payment,
        "savings": req.savings_monthly,
        "savings_total": req.savings_total,
        "goal_cost": req.savings_goal_cost,
    }
    plan_id = hashlib.sha256(json.dumps(plan_fingerprint, sort_keys=True).encode("utf-8")).hexdigest()[:16]

    llm_input = {
        "plan_id": plan_id,
        "currency": req.currency,
        "region": region,
        "inputs": scoring_input,
        "score": score_obj,
        "budget_plan": budget_obj,
        "budget_mode": req.budget_mode,
        "spending_patterns": {
            "variable_total": variable_total,
            "breakdown": [v.dict() for v in req.variable_breakdown],
        },
        "investing": {
            "readiness": readiness,
            "education": education,
            "allocation_example": allocation,
            "allocation_visual": allocation_visual,
            "education_only": True,
        },
        "savings_goal": savings_goal,
    }

    explanation = get_llm_explanation(llm_input)

    return {
        "plan_id": plan_id,
        "score": score_obj,
        "budget": budget_obj,
        "investing": {
            "region": region,
            "readiness": readiness,
            "education": education,
            "allocation_example": allocation,
            "allocation_visual": allocation_visual,
        },
        "savings_goal": savings_goal,
        "llm_explanation": explanation,
    }


# ------------------------------------------------------------
# Endpoint: chat
# ------------------------------------------------------------
@app.post("/chat")
async def chat(payload: Dict[str, Any]) -> Dict[str, str]:
    user_msg = (payload.get("message") or "").strip()
    financial_data = payload.get("financial_data") or {}
    history = payload.get("history", [])
    incoming_plan_id = payload.get("plan_id")

    if not user_msg:
        return {"response": "Please enter a message."}

    # Keep model away from ASCII bar + big blobs
    fd = strip_visual_from_financial_data(financial_data)

    # Building a SMALL, SAFE context the model can’t “template hallucinate” from
    budget = (fd.get("budget") or {})
    totals = (budget.get("totals") or {})
    deltas = (budget.get("deltas") or {})
    investing = (fd.get("investing") or {})
    readiness = (investing.get("readiness") or {})
    education = (investing.get("education") or {})
    allocation_example = investing.get("allocation_example")  # keeps numbers only

    spending_patterns = fd.get("spending_patterns") or {}
    breakdown = spending_patterns.get("breakdown") or []

    # Providing a preformatted breakdown string (model should copy this)
    breakdown_lines = []
    for item in breakdown:
        name = (item.get("name") or "").strip()
        amt = item.get("amount")
        if name and isinstance(amt, (int, float)):
            breakdown_lines.append(f"- {name}: {amt}")
    spending_breakdown_text = "\n".join(breakdown_lines)

    context = {
        "plan_id": incoming_plan_id,
        "currency": fd.get("currency"),
        "region": fd.get("investing", {}).get("region"),
        "budget_totals": totals,
        "budget_deltas": deltas,
        "investing": {
            "readiness": readiness,
            "education": education,
            "allocation_example": allocation_example,
        },
        "spending_patterns": {
            "variable_total": spending_patterns.get("variable_total"),
            "breakdown": breakdown,  # raw list
            "breakdown_text": spending_breakdown_text,  # copy-ready bullets
        },
        "savings_goal": fd.get("savings_goal"),
    }

    response_text = chat_freeform(user_msg, context=context)
    return {"response": response_text}
