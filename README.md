# FinancAI
Group Distribution: 
- Backend - Ryan, 
- Frontend - Angee,
- Integration - Koen,
- Documentation - El

# FinancAI — AI-Assisted Budgeting & Financial Health Analyzer

FinancAI is a personal finance planning tool that combines **deterministic financial logic** with **AI-generated explanations**.

It helps users:
- Understand where their money goes
- Get a recommended budget based on different saving styles
- See a financial health score with clear reasoning
- Receive human-readable AI explanations of their situation

---




## How to Start

download everything from requirements.txt

---


## Testing the Backend
visit https://groq.com/ to generate a free API key

open a terminal in the backend folder and enter: ``set GROQ_API_KEY=your key`` or ``export GROQ_API_KEY=your key``

type in ``uvicorn main:app --reload`` and run

assuming no error occurs, you should see an IP Address ``http://127.0.0.1:8000`` where you can test the backend out. To actually see the contents of the backend go to ``http://127.0.0.1:8000/docs#/`` 

## Opening the frontend

Open a terminal in the main folder for the program and enter: ``streamlit run app.py``
**Note**: Make sure to run the Backend *before* the frontend. Also make sure that the backend stays running in the background whenever the site is being used.


---

## How the System Works

FinancAI is split into **two independent parts**:

### 1. Frontend (Streamlit)
- Collects user financial inputs
- Sends them to the backend as JSON
- Displays scores, charts, and results

### 2. Backend (FastAPI)
- Computes the budget using fixed formulas
- Computes a financial well-being score
- Calls an AI model (Groq) to explain the results in plain English
- Returns structured JSON back to the frontend

---

## Frontend — `app.py`

The frontend is built using **Streamlit**.

### User Inputs
The user provides:
- Currency
- Monthly income
- Fixed expenses (dynamic list)
- Variable expenses (dynamic list + category breakdown)
- Monthly and total debt
- Monthly and total savings
- Savings Goals (optional)
- Budget style:
  - **Super** (aggressive saving)
  - **Normal** (balanced)
  - **Relaxed** (more spending flexibility)

### Data Flow
When the user clicks **“Generate Budget Plan”**:
1. Inputs are aggregated into a JSON payload
2. Payload is sent to the backend via `POST`
3. Backend response is stored in `st.session_state.results`
4. Results are displayed:
   - Financial score + state
   - Savings comparison chart
   - Raw JSON output (for transparency)


---

## Backend — `backend/main.py`

The backend is a **FastAPI application** that exposes multiple endpoints.

### Running as a Package
The backend is a Python package (`backend/` contains `__init__.py`) and must be started from the project root.

---

## API Endpoints

### `POST /generate` — Main Pipeline

This endpoint:
1. Validates input using Pydantic
2. Computes the financial score
3. Computes the budget plan
4. Calls the LLM to explain the results
5. Returns all outputs together

#### Example Request
```json
{
  "monthly_income": 3000,
  "fixed_expenses": 1200,
  "variable_expenses": 400,
  "variable_breakdown": [
    {"name": "Groceries", "amount": 250},
    {"name": "Entertainment", "amount": 150}
  ],
  "debt_monthly_payment": 200,
  "debt_total_balance": 5000,
  "savings_monthly": 150,
  "savings_total": 1000,
  "budget_mode": "normal"
}
```
### Financial Logic & Design Rationale
FinancAI is intentionally built around **deterministic financial logic**, not AI-generated calculations.  
All numbers shown to the user (budgets, savings targets, timelines, and scores) are computed using fixed formulas in the backend.  
The AI component is used **only to explain results**, not to generate them.

This design ensures consistency, transparency, and prevents hallucinated financial advice.

---

### Financial Well-Being Score

The financial well-being score is calculated using four core indicators commonly used in personal finance education:

1. **Emergency Fund Coverage (30%)**
   - Calculated as total savings divided by monthly expenses.
   - A target of 3 months is used as a baseline.
   - This is weighted highest because emergency liquidity is critical for financial stability.

2. **Debt-to-Income Ratio (28%)**
   - Monthly debt payments divided by monthly income.
   - Lower ratios result in higher scores.
   - High debt reduces financial flexibility and increases risk.

3. **Savings Rate (22%)**
   - Monthly savings divided by monthly income.
   - A 20% savings rate is treated as a strong benchmark.
   - Encourages sustainable long-term financial behavior.

4. **Housing / Fixed Expense Ratio (20%)**
   - Fixed expenses divided by income.
   - Lower fixed costs improve resilience and discretionary flexibility.

Each component is normalized to a 0–100 scale and combined using weighted averages.
The final score is mapped to one of four states:
- **Critical**
- **Vulnerable**
- **Stable**
- **Strong**

---

### Budget Recommendation Logic

FinancAI generates budgets using a rule-based model with three selectable styles:

- **Super** — aggressive savings focus
- **Normal** — balanced approach
- **Relaxed** — increased spending flexibility

The system:
- Reserves fixed expenses and debt first
- Allocates savings based on the selected target rate
- Assigns remaining funds to variable spending
- Calculates any leftover capacity

This ensures budgets are **realistic** and **do not exceed available income**.

---

### Savings Goal Logic

Savings goals are handled entirely in deterministic code.

If a goal amount is provided:
- The system calculates how long it would take to reach the goal using:
  - Planned savings capacity (recommended savings + leftover)
  - Current monthly savings input
- If no timeframe is provided by the user, the system computes an **ideal timeline**
- If savings capacity is zero, no timeline is generated

The system never guesses prices, timelines, or monthly amounts.
All results are derived strictly from the user’s inputs and computed budget.

---

### Investing Readiness Logic

Investing readiness is determined using clear rule-based checks:

- Emergency fund level
- Financial score state
- Monthly cash flow
- Savings capacity

If the user is not ready, the system explains the blockers.
If the user is ready, the system provides **educational guidance only**, without recommending specific assets or predicting returns.

---

### AI Usage & Hallucination Prevention

The AI model is **never allowed to calculate numbers**.

Strict safeguards are enforced:
- The AI receives only pre-computed values
- The AI is instructed not to recompute, estimate indicate new figures
- If required data is missing, the AI must ask a clarifying question

This prevents hallucinations and ensures financial accuracy.

---

### Development Note

ChatGPT was used during development for:
- Code assistance
- Debugging support
- Refactoring and documentation

All financial logic, formulas, and validation rules were explicitly designed and reviewed by the development team.

---

### Ethical, Legal & Regulatory Considerations


### Data Protection (GDPR)
FinancAI processes only user-provided financial inputs and does not store, track, or persist personal data beyond the active session. All data is processed locally or in-memory for the sole purpose of generating results. No data is intentionally logged or retained by FinancAI after processing.

For AI-generated explanations, relevant input data is temporarily transmitted to the Groq API to produce natural-language output.


### AI Act
FinancAI uses AI only for explanatory text. All financial calculations, scores, and recommendations are generated using deterministic, rule-based logic.

The AI does not make decisions, perform profiling, or generate financial figures. The system is intended as a low-risk, AI-assisted informational tool.


### Open-Source & Usage
This project was developed as part of an academic course. No explicit open-source license is provided.

The code is shared for educational and review purposes only and is not intended for commercial use.

