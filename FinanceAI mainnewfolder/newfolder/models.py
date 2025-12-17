from pydantic import BaseModel

class BudgetRequest(BaseModel):
    monthly_income: float
    fixed_expenses: float
    variable_expenses: float
    debt_monthly_payment: float
    debt_total_balance: float
    savings_monthly: float
    savings_total: float
    emergency_months_target: float
    budget_mode: str

class ChatRequest(BaseModel):
    message: str
