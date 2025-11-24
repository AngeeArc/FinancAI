from fastapi import FastAPI
from finance_logic import calculate_budget, financial_wellbeing_score, recommendation

app = FastAPI()

@app.post("/calculate")
def calculate(data: dict):
    # Calculate budget
    results = calculate_budget(
        income=data["income"],
        rent=data["rent"],
        utilities=data["utilities"],
        transport=data["transport"],
        debt=data["debt"],
        mode=data.get("budget_mode", "Normal")
    )

    # Financial score
    score = financial_wellbeing_score(
        income=data["income"],
        debt=data["debt"],
        emergency_fund=data["emergency_fund"],
        savings=data["savings"],
        investments=data["investments"]
    )

    # Recommendation
    rec = recommendation(score)

    # Attach to results dictionary
    results["score"] = score
    results["recommendation"] = rec

    return results

