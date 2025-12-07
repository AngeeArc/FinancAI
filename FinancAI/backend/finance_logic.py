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

def compute_financial_score(payload: dict) -> dict:
    income = float(payload.get("monthly_income", 0) or 0)
    fixed = float(payload.get("fixed_expenses", 0) or 0)
    variable = float(payload.get("variable_expenses", 0) or 0)
    debt_payment = float(payload.get("debt_monthly_payment", 0) or 0)
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
            "housing_pct": round2(housing_pct),
            "emergency_fund_months": round2(emergency_months),
        }
    }

def generate_budget(payload: dict, mode: str = "normal") -> dict:
    """
    Budget generator with 3 modes:
      - "super"   : maximize savings (aggressive)
      - "normal"  : balanced (default)
      - "relaxed" : more spending, lower savings

    Expected keys in payload:
      - monthly_income
      - fixed_expenses
      - variable_expenses (current variable spending total)
      - debt_monthly_payment
      - savings_monthly (current savings)
    """

    income = float(payload.get("monthly_income", 0) or 0)
    fixed = float(payload.get("fixed_expenses", 0) or 0)
    current_variable = float(payload.get("variable_expenses", 0) or 0)
    debt = float(payload.get("debt_monthly_payment", 0) or 0)
    current_savings = float(payload.get("savings_monthly", 0) or 0)

    # Money left after fixed + debt (what can move between savings & variable)
    flexible_pool = max(0.0, income - fixed - debt)

    # Choose target savings rate by mode
    mode = (mode or "normal").lower()
    if mode == "super":
        target_savings_rate = 0.30   # aim for 30% of income saved
    elif mode == "relaxed":
        target_savings_rate = 0.10   # ~10% savings
    else:
        mode = "normal"
        target_savings_rate = 0.20   # ~20% savings

    ideal_savings = income * target_savings_rate

    # not let savings exceed flexible_pool
    if ideal_savings > flexible_pool:
        # If target is too high, save ~60% of flexible_pool, 40% stays variable
        recommended_savings = flexible_pool * 0.6
    else:
        recommended_savings = ideal_savings

    recommended_savings = clamp(recommended_savings, 0.0, flexible_pool)
    recommended_variable = max(0.0, flexible_pool - recommended_savings)

    # Leftover if anything remains unallocated
    total_planned = fixed + debt + recommended_savings + recommended_variable
    leftover = max(0.0, income - total_planned)

    # Changes vs current behaviour
    savings_change = recommended_savings - current_savings
    variable_change = recommended_variable - current_variable

    return {
        "mode": mode,
        "totals": {
            "income": round2(income),
            "fixed": round2(fixed),
            "debt": round2(debt),
            "recommended_savings": round2(recommended_savings),
            "recommended_variable": round2(recommended_variable),
            "leftover": round2(leftover),
        },
        "deltas": {
            "savings_change": round2(savings_change),
            "variable_change": round2(variable_change),
        },
        "meta": {
            "flexible_pool": round2(flexible_pool),
            "target_savings_rate_pct": round2(percent(target_savings_rate)),
        }
    }
