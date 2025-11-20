from fastapi import FastAPI
from finance_logic import calculate_budget, financial_wellbeing_score, recommendation

app = FastAPI()

@app.post("/calculate")
def calculate(data: dict):
    results = calculate_budget(
        income=data["income"],
        rent=data["rent"],
        utilities=data["utilities"],
        transport=data["transport"],
        debt=data["debt"],
        savings_goal=data.get("budget_mode", "Normal")
    )

    score = financial_wellbeing_score(
        income=data["income"],
        debt=data["debt"],
        emergency_fund=data["emergency_fund"],
        savings=data["savings"],
        investments=data["investments"]
    )

    rec = recommendation(score)

    # Return all needed data
    results["score"] = score
    results["recommendation"] = rec
    return results
