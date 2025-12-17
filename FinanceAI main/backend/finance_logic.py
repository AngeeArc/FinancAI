# backend/finance_logic.py

from __future__ import annotations
from typing import Dict, Any, Optional


def safe_div(a: float, b: float) -> float:
    """
    Safe division helper.
    Returns 0.0 if denominator is zero or invalid.
    """
    try:
        return (a / b) if b else 0.0
    except Exception:
        return 0.0


def clamp(v: float, lo: float, hi: float) -> float:
    """
    Clamp value into [lo, hi].
    """
    return max(lo, min(hi, v))


def percent(x: float) -> float:
    """
    Convert ratio -> percent.
    Example: 0.2 -> 20.0
    """
    return x * 100.0


def round2(x: float) -> float:
    """
    Round to 2 decimals.
    """
    try:
        return round(float(x), 2)
    except Exception:
        return 0.0


def compute_financial_score(payload: Dict[str, Any]) -> Dict[str, Any]:
    """
    Compute a simple financial well-being score from monthly inputs.

    Expected keys:
      - monthly_income
      - fixed_expenses
      - variable_expenses
      - debt_monthly_payment
      - savings_monthly
      - savings_total
      - emergency_months_target
    """
    # -----------------------------
    # Step 1: Extract inputs
    # -----------------------------
    income = float(payload.get("monthly_income", 0) or 0)
    fixed = float(payload.get("fixed_expenses", 0) or 0)
    variable = float(payload.get("variable_expenses", 0) or 0)
    debt_payment = float(payload.get("debt_monthly_payment", 0) or 0)
    savings_monthly = float(payload.get("savings_monthly", 0) or 0)
    savings_total = float(payload.get("savings_total", 0) or 0)
    emergency_target = float(payload.get("emergency_months_target", 3) or 3)

    # -----------------------------
    # Step 2: Compute basic ratios
    # -----------------------------
    savings_rate = safe_div(savings_monthly, income)
    debt_to_income = safe_div(debt_payment, income)
    housing_pct = safe_div(fixed, income)

    # Emergency fund months = savings_total / monthly expenses
    monthly_expenses = max(1.0, fixed + variable)
    emergency_months = safe_div(savings_total, monthly_expenses)

    # -----------------------------
    # Step 3: Score components
    # -----------------------------
    # Savings rate score: 20% savings -> 100, linear up to that
    savings_rate_score = clamp((savings_rate / 0.20) * 100.0, 0.0, 100.0)

    # Debt score: <=10% debt-to-income is best, >=40% is worst
    if debt_to_income <= 0.10:
        debt_score = 100.0
    elif debt_to_income >= 0.40:
        debt_score = 0.0
    else:
        # linear between 0.10 and 0.40
        debt_score = (1.0 - (debt_to_income - 0.10) / 0.30) * 100.0
    debt_score = clamp(debt_score, 0.0, 100.0)

    # Housing score: <=30% fixed/income best, >=50% worst
    if housing_pct <= 0.30:
        housing_score = 100.0
    elif housing_pct >= 0.50:
        housing_score = 0.0
    else:
        housing_score = (1.0 - (housing_pct - 0.30) / 0.20) * 100.0
    housing_score = clamp(housing_score, 0.0, 100.0)

    # Emergency score: >= target is 100, else linear
    if emergency_months >= emergency_target:
        emergency_score = 100.0
    else:
        emergency_score = clamp((emergency_months / emergency_target) * 100.0, 0.0, 100.0)

    # -----------------------------
    # Step 4: Weighted total score
    # -----------------------------
    overall = (
        emergency_score * 0.30 +
        debt_score * 0.28 +
        savings_rate_score * 0.22 +
        housing_score * 0.20
    )
    overall = clamp(overall, 0.0, 100.0)

    # -----------------------------
    # Step 5: State label
    # -----------------------------
    if overall < 40:
        state = "critical"
    elif overall < 60:
        state = "vulnerable"
    elif overall < 80:
        state = "stable"
    else:
        state = "strong"

    # -----------------------------
    # Step 6: Return full breakdown
    # -----------------------------
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


def generate_budget(payload: Dict[str, Any], mode: str = "normal") -> Dict[str, Any]:
    """
    Budget generator with 3 modes:
      - super   : maximize savings (aggressive)
      - normal  : balanced
      - relaxed : more spending, lower savings
    """
    income = float(payload.get("monthly_income", 0) or 0)
    fixed = float(payload.get("fixed_expenses", 0) or 0)
    current_variable = float(payload.get("variable_expenses", 0) or 0)
    debt = float(payload.get("debt_monthly_payment", 0) or 0)
    current_savings = float(payload.get("savings_monthly", 0) or 0)

    # Money left after fixed + debt
    flexible_pool = max(0.0, income - fixed - debt)

    # Determine target savings rate based on mode
    mode = (mode or "normal").lower()
    if mode == "super":
        target_savings_rate = 0.30
    elif mode == "relaxed":
        target_savings_rate = 0.10
    else:
        mode = "normal"
        target_savings_rate = 0.20

    # Ideal savings by target rate
    ideal_savings = income * target_savings_rate

    # If ideal_savings exceeds flexible pool, cap realistically
    if ideal_savings > flexible_pool:
        recommended_savings = flexible_pool * 0.60
    else:
        recommended_savings = ideal_savings

    # Clamp recommended savings to [0, flexible_pool]
    recommended_savings = clamp(recommended_savings, 0.0, flexible_pool)
    recommended_variable = max(0.0, flexible_pool - recommended_savings)

    # Leftover if anything remains (should usually be 0)
    total_planned = fixed + debt + recommended_savings + recommended_variable
    leftover = max(0.0, income - total_planned)

    # Deltas vs current
    savings_change = recommended_savings - current_savings
    variable_change = recommended_variable - current_variable

    # monthly capacity that can be allocated to goals inside this plan
    monthly_goal_capacity = max(0.0, recommended_savings) + max(0.0, leftover)

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
            "monthly_goal_capacity": round2(monthly_goal_capacity),  # ✅ added
        }
    }



def build_savings_goal_plan(
    *,
    goal_amount: float,
    goal_months: int,
    current_monthly_savings: float,
    recommended_savings: float,
    leftover: float,
    goal_name: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Compute a simple plan for an optional savings goal.

    Inputs:
      - goal_amount: target amount the user wants to save
      - goal_months: timeframe (months) to reach it
      - current_monthly_savings: user's currently entered monthly savings
      - recommended_savings: backend recommended savings from generate_budget
      - leftover: backend leftover from generate_budget
      - goal_name: optional label (e.g. "Laptop", "Trip")

    Output:
      - required_monthly: how much per month is needed
      - gap_vs_current: required_monthly - current_monthly_savings
      - suggested_split: how to allocate the plan's savings capacity
    """
    goal_amount = float(goal_amount or 0.0)
    goal_months = int(goal_months or 0)

    current_monthly_savings = float(current_monthly_savings or 0.0)
    recommended_savings = float(recommended_savings or 0.0)
    leftover = float(leftover or 0.0)

    # basic validation
    if goal_amount <= 0 or goal_months <= 0:
        return {
            "enabled": False,
            "error": "Invalid goal parameters. Please provide a positive goal amount and target months."
        }

    required_monthly = safe_div(goal_amount, float(goal_months))
    gap_vs_current = required_monthly - current_monthly_savings

    # If leftover is 0, user can still fund goal from recommended savings (redirecting part of it)
    savings_capacity = max(0.0, leftover) + max(0.0, recommended_savings)

    # Suggested split:
    # fund goal up to required_monthly, remaining stays as general savings
    goal_funding = min(required_monthly, savings_capacity)
    general_savings = max(0.0, savings_capacity - goal_funding)

    status = "on_track" if current_monthly_savings >= required_monthly else "needs_increase"

    return {
        "enabled": True,
        "name": goal_name,
        "amount": round2(goal_amount),
        "months": int(goal_months),
        "required_monthly": round2(required_monthly),
        "current_monthly_savings": round2(current_monthly_savings),
        "gap_vs_current": round2(gap_vs_current),
        "status": status,
        "suggested_split": {
            "goal_funding": round2(goal_funding),
            "general_savings": round2(general_savings),
            "notes": [
                "Goal funding is prioritized first up to the monthly amount needed.",
                "Any remaining savings capacity stays as general savings."
            ],
        },
        "capacity_used": {
            "recommended_savings": round2(recommended_savings),
            "leftover": round2(leftover),
            "max_capacity_for_savings": round2(savings_capacity),
        },
    }
