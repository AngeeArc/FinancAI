# backend/scoring.py

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

def compute_financial_score(payload):
    income = float(payload.get("monthly_income", 0) or 0)
    fixed = float(payload.get("fixed_expenses", 0) or 0)
    variable = float(payload.get("variable_expenses", 0) or 0)
    debt_payment = float(payload.get("debt_monthly_payment", 0) or 0)
    debt_balance = float(payload.get("debt_total_balance", 0) or 0)
    savings_monthly = float(payload.get("savings_monthly", 0) or 0)
    savings_total = float(payload.get("savings_total", 0) or 0)
    emergency_target = float(payload.get("emergency_months_target", 3) or 3)

    savings_rate = safe_div(savings_monthly, income)
    debt_to_income = safe_div(debt_payment, income)
    housing_pct = safe_div(fixed, income)
    emergency_months = safe_div(savings_total, max(1.0, fixed + variable))

    savings_rate_score = clamp((savings_rate / 0.20) * 100, 0, 100)

    if debt_to_income <= 0.10:
        debt_score = 100
    elif debt_to_income >= 0.40:
        debt_score = 0
    else:
        debt_score = (1 - (debt_to_income - 0.10) / 0.30) * 100
    debt_score = clamp(debt_score, 0, 100)

    if housing_pct <= 0.30:
        housing_score = 100
    elif housing_pct >= 0.50:
        housing_score = 0
    else:
        housing_score = (1 - (housing_pct - 0.30) / 0.20) * 100
    housing_score = clamp(housing_score, 0, 100)

    if emergency_months >= emergency_target:
        emergency_score = 100
    else:
        emergency_score = clamp((emergency_months / emergency_target) * 100, 0, 100)

    overall = (
        emergency_score * 0.30 +
        debt_score * 0.28 +
        savings_rate_score * 0.22 +
        housing_score * 0.20
    )
    overall = clamp(overall, 0, 100)

    if overall < 40:
        state = "critical"
    elif overall < 60:
        state = "vulnerable"
    elif overall < 80:
        state = "stable"
    else:
        state = "strong"

    return {
        "score": round2(overall),
        "state": state,
        "components": {
            "savings_rate_pct": round2(percent(savings_rate)),
            "debt_to_income_pct": round2(percent(debt_to_income)),
            "housing_pct": round2(percent(housing_pct)),
            "emergency_fund_months": round2(emergency_months),
        }
    }
