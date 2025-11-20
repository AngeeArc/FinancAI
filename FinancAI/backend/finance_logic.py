import numpy as np

def calculate_budget(income, rent, utilities, transport, debt, savings_goal):
    fixed_expenses = rent + utilities + transport
    disposable = income - fixed_expenses - debt

    if disposable < 0:
        disposable = 0

    if savings_goal == "Super Budget":
        savings_rate = 0.50
    elif savings_goal == "Relaxed":
        savings_rate = 0.10
    else:
        savings_rate = 0.25

    suggested_savings = disposable * savings_rate
    spending_budget = disposable - suggested_savings

    return {
        "fixed_expenses": fixed_expenses,
        "disposable": disposable,
        "suggested_savings": suggested_savings,
        "spending_budget": spending_budget
    }


def financial_wellbeing_score(income, debt, emergency_fund, savings, investments):
    score = 0

    # Debt-to-income
    dti = debt / income
    if dti < 0.1:
        score += 30
    elif dti < 0.3:
        score += 20
    elif dti < 0.5:
        score += 10

    # Emergency fund
    months = emergency_fund / income
    if months >= 6:
        score += 40
    elif months >= 3:
        score += 25
    else:
        score += 10

    # Savings rate
    if savings / income >= 0.20:
        score += 20
    elif savings / income >= 0.10:
        score += 10

    # Investments
    if investments > income * 6:
        score += 10

    return min(score, 100)


def recommendation(score):
    if score < 40:
        return "Super Budget – focus on emergency savings and debt reduction."
    elif score < 70:
        return "Normal Budget – maintain stable savings and moderate spending."
    else:
        return "Relaxed Budget – you're in good shape! Invest and enjoy responsibly."
