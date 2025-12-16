# FinancAI
Roles: 
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

