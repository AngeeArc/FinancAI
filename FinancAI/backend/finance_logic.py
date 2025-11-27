# finance_logic.py
from typing import Dict, Any
import math

def safe_div(a, b):
    try:
        return a / b if b else 0.0
    except Exception:
        return 0.0

def clamp(v, lo, hi):
    return max(lo, min(hi, v))

def percent(x):
    return x * 100.0

def round2(x):
    return round(x, 2)

def compute_financial_score(payload: Dict[str, Any]) -> Dict[str, Any]:
    income = float(payload.get("monthly_income", 0) or 0)
    fixed = float(payload.get("fixed_expenses", 0) or 0)
    variable = float(payload.get("variable_expenses", 0) or 0)
    debt_payment = float(payload.get("debt_monthly_payment", 0) or 0)
    debt_balance = float(payload.get("debt_total_balance", 0) or 0)
    savings_monthly = float(payload.get("savings_monthly", 0) or 0)
    savings_total = float(payload.get("savings_total", 0) or 0)
    emergency_target = float(payload.get("emergency_months_target", 3) or 3)

    total_spending = fixed + variable + debt_payment
    disposable = max(0.0, income - fixed - debt_payment)
    savings_rate = safe_div(savings_monthly, income) if income > 0 else 0.0
    debt_to_income = safe_div(debt_payment, income) if income > 0 else 0.0
    housing_pct = safe_div(fixed, income) if income > 0 else 0.0
    emergency_months = safe_div(savings_total, max(1.0, fixed + variable)) if (fixed+variable)>0 else 0.0

    savings_rate_score = clamp((savings_rate / 0.20) * 100.0, 0, 100)

    if debt_to_income <= 0.10:
        debt_score = 100.0
    elif debt_to_income >= 0.40:
        debt_score = 0.0
    else:
        debt_score = (1.0 - (debt_to_income - 0.10) / 0.30) * 100.0
    debt_score = clamp(debt_score, 0, 100)

    if housing_pct <= 0.30:
        housing_score = 100.0
    elif housing_pct >= 0.50:
        housing_score = 0.0
    else:
        housing_score = (1.0 - (housing_pct - 0.30) / 0.20) * 100.0
    housing_score = clamp(housing_score, 0, 100)

    if emergency_months >= emergency_target:
        emergency_score = 100.0
    else:
        emergency_score = clamp((emergency_months / max(0.1, emergency_target)) * 100.0, 0, 100)

    weights = {
        "emergency": 0.30,
        "debt": 0.28,
        "savings_rate": 0.22,
        "housing": 0.20
    }
    aggregate = (
        emergency_score * weights["emergency"] +
        debt_score * weights["debt"] +
        savings_rate_score * weights["savings_rate"] +
        housing_score * weights["housing"]
    )
    overall_score = clamp(aggregate, 0, 100)

    if overall_score < 40:
        state = "critical"
    elif overall_score < 60:
        state = "vulnerable"
    elif overall_score < 80:
        state = "stable"
    else:
        state = "strong"

    explanations = []
    if savings_rate < 0.05:
        explanations.append("Your monthly savings rate is very low — consider increasing contributions or reducing variable spending.")
    elif savings_rate < 0.15:
        explanations.append("Your savings are modest; increasing to 10–20% would strengthen your position.")
    else:
        explanations.append("Your savings rate looks healthy for now.")

    if debt_to_income > 0.35:
        explanations.append("Debt payments are a large share of income. Prioritize paying down high-interest debt.")
    elif debt_to_income > 0.15:
        explanations.append("Debt payments are notable — monitor repayment plans and avoid new consumer debt.")
    else:
        explanations.append("Your regular debt burden is low relative to income.")

    if housing_pct > 0.45:
        explanations.append("Housing/fixed costs are very high relative to income; consider cheaper options if possible.")
    elif housing_pct > 0.30:
        explanations.append("Housing and fixed costs are above typical benchmarks; keep an eye on them.")
    else:
        explanations.append("Housing and fixed costs are within a healthy range.")

    if emergency_months < max(0.5, emergency_target * 0.5):
        explanations.append("Emergency savings are insufficient — prioritize building 3 months of expenses.")
    else:
        explanations.append("Emergency savings are in decent shape relative to your target.")

    return {
        "score": round(overall_score, 2),
        "state": state,
        "components": {
            "savings_rate_pct": round(percent(savings_rate), 2),
            "debt_to_income_pct": round(percent(debt_to_income), 2),
            "housing_pct": round(percent(housing_pct), 2),
            "emergency_fund_months": round(emergency_months, 2),
            "savings_rate_score": round(savings_rate_score, 2),
            "debt_score": round(debt_score, 2),
            "housing_score": round(housing_score, 2),
            "emergency_score": round(emergency_score, 2)
        },
        "explanations": explanations
    }
