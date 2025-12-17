import streamlit as st
import requests
import pandas as pd
from contextlib import contextmanager
import json
import hashlib

# ============================================================
# CONFIG
# ============================================================
BACKEND_URL = "http://localhost:8000/generate"
CHAT_URL = "http://localhost:8000/chat"

st.set_page_config(page_title="FinancAI", page_icon="💰", layout="centered")

# ============================================================
# STYLING
# ============================================================
st.markdown(
    """
<style>
    .main { background-color: #f9f9f9; }
    .section-box {
        background-color: white;
        padding: 20px;
        border-radius: 14px;
        box-shadow: 0px 0px 10px rgba(0,0,0,0.06);
        margin-bottom: 20px;
    }
    .stButton > button {
        background-color: #4CAF50;
        color: white;
        padding: 0.7rem 1.6rem;
        border-radius: 10px;
        border: none;
        font-size: 17px;
    }
    .stButton > button:hover {
        background-color: #45a049;
    }
    .disclaimer {
        font-size: 13px;
        opacity: 0.85;
        line-height: 1.35;
        margin-top: 8px;
    }
</style>
""",
    unsafe_allow_html=True,
)

# ============================================================
# HELPERS
# ============================================================
@contextmanager
def section_box():
    st.markdown("<div class='section-box'>", unsafe_allow_html=True)
    try:
        yield
    finally:
        st.markdown("</div>", unsafe_allow_html=True)


def clean_llm_text(text: str) -> str:
    """Remove formatting that looks bad in Streamlit (inline code + blockquotes)."""
    if not text:
        return ""
    text = text.replace("`", "")
    text = text.replace("\n> ", "\n").replace("> ", "")
    return text


def strip_visual_from_financial_data(financial_data):
    """Remove allocation_visual so chatbot doesn't repeat/mangle it."""
    try:
        if not isinstance(financial_data, dict):
            return financial_data
        fd = dict(financial_data)
        inv = fd.get("investing")
        if isinstance(inv, dict):
            inv2 = dict(inv)
            inv2.pop("allocation_visual", None)
            fd["investing"] = inv2
        return fd
    except Exception:
        return financial_data


def make_fingerprint(payload: dict) -> str:
    """Stable fingerprint to reset chat when plan changes."""
    s = json.dumps(payload, sort_keys=True, ensure_ascii=False)
    return hashlib.sha256(s.encode("utf-8")).hexdigest()


def fmt_money(x, currency_label: str):
    try:
        return f"{float(x):.2f} {currency_label}"
    except Exception:
        return f"{x} {currency_label}"


DISCLAIMER_TEXT = (
    "DISCLAIMER: This tool is for educational purposes only. This app provides general financial education and is not "
    "personalized financial, legal, or tax advice. Consider consulting a qualified professional before making "
    "financial decisions."
)

# ============================================================
# SESSION STATE
# ============================================================
if "results" not in st.session_state:
    st.session_state.results = None
if "messages" not in st.session_state:
    st.session_state.messages = []
if "latest_financial_data" not in st.session_state:
    st.session_state.latest_financial_data = None
if "budget_fingerprint" not in st.session_state:
    st.session_state.budget_fingerprint = None
if "plan_id" not in st.session_state:
    st.session_state.plan_id = None

# ============================================================
# HEADER
# ============================================================
st.title("💰 FinancAI — Your AI Financial Planner")
st.write("Enter your financial details to generate a personalized breakdown and chat with your AI assistant.")
st.info(DISCLAIMER_TEXT)

# ============================================================
# INPUT FORM
# ============================================================
with section_box():
    st.header("📋 Financial Inputs")

    left, right = st.columns(2)

    with left:
        country = st.text_input("Enter Country of Residence", key="country")

        currency_choice = st.selectbox(
            "Currency",
            ["USD ($)", "EUR (€)", "GBP (£)", "CAD ($)", "AUD ($)", "JPY (¥)", "INR (₹)", "Other"],
            key="currency_choice",
        )
        other_currency = ""
        if currency_choice == "Other":
            other_currency = st.text_input("Enter currency symbol or code:", key="other_currency")

        currency_label = other_currency if currency_choice == "Other" else currency_choice

        income = st.number_input(f"Monthly Income {currency_label}", min_value=0.0, step=100.0, key="income")

        # ---------------------------
        # FIXED EXPENSES (breakdown)
        # ---------------------------
        st.subheader("🏠 Fixed Expenses")
        fixed_categories = ["Rent", "Utilities", "Transportation", "Insurance", "Phone", "Internet", "Other"]
        fixed_items = []

        fixed_count = st.number_input(
            "Number of Fixed Expenses", min_value=0, max_value=20, value=0, step=1, key="fixed_count"
        )

        for i in range(int(fixed_count)):
            colA, colB = st.columns(2)
            cat = colA.selectbox(f"Category {i+1}", fixed_categories, key=f"fcat{i}")
            amt = colB.number_input(f"Amount {i+1} {currency_label}", min_value=0.0, step=10.0, key=f"famt{i}")
            fixed_items.append({"name": cat, "amount": float(amt)})

        fixed_total = sum(x["amount"] for x in fixed_items)

        # ---------------------------
        # VARIABLE EXPENSES (breakdown)
        # ---------------------------
        st.subheader("🛒 Variable Expenses")
        variable_categories = [
            "Groceries", "Hobbies", "Entertainment", "Subscriptions",
            "Type Other Variable Here (e.g. Smoking, Coffee, Eating Out)"
        ]
        variable_items = []

        var_count = st.number_input(
            "Number of Variable Expenses", min_value=0, max_value=20, value=0, step=1, key="var_count"
        )

        for i in range(int(var_count)):
            colA, colB = st.columns(2)
            cat = colA.selectbox(f"Category {i+1}", variable_categories, key=f"vcat{i}")
            amt = colB.number_input(f"Amount {i+1} {currency_label}", min_value=0.0, step=10.0, key=f"vamt{i}")
            variable_items.append({"name": cat, "amount": float(amt)})

        variable_total = sum(x["amount"] for x in variable_items)

        # ---------------------------
        # OPTIONAL SAVINGS GOAL (months optional)
        # ---------------------------
        st.subheader("🎯 Optional Savings Goal")
        enable_goal = st.checkbox("I have a savings goal", key="enable_goal")

        goal_name = ""
        goal_amount = 0.0
        goal_months = None  # optional
        if enable_goal:
            goal_name = st.text_input("What are you saving for? (optional)", key="goal_name")
            goal_amount = st.number_input(
                f"Goal amount {currency_label}", min_value=0.0, step=50.0, key="goal_amount"
            )

            use_months = st.checkbox("I have a target timeframe (months)", value=False, key="use_goal_months")
            if use_months:
                goal_months = st.number_input(
                    "Target months to reach it", min_value=1, max_value=120, step=1, key="goal_months"
                )

    with right:
        st.subheader("💳 Debt")
        monthly_debt = st.number_input(
            f"Monthly Debt Payments {currency_label}", min_value=0.0, step=10.0, key="monthly_debt"
        )
        total_debt = st.number_input(f"Total Debt {currency_label}", min_value=0.0, step=100.0, key="total_debt")

        st.subheader("💵 Savings")
        monthly_savings = st.number_input(
            f"Monthly Savings {currency_label}", min_value=0.0, step=10.0, key="monthly_savings"
        )
        total_savings = st.number_input(
            f"Total Savings {currency_label}", min_value=0.0, step=100.0, key="total_savings"
        )

    budget_type = st.radio("Budget Style", ["Super", "Normal", "Relaxed"], key="budget_type")

    if st.button("✨ Generate Budget Plan", key="generate_btn"):
        payload = {
            "currency": currency_label,
            "country": country if country.strip() else None,
            "monthly_income": float(income),
            "fixed_expenses": float(fixed_total),
            "variable_expenses": float(variable_total),
            "variable_breakdown": variable_items,  # backend uses this if present
            "debt_monthly_payment": float(monthly_debt),
            "debt_total_balance": float(total_debt),
            "savings_monthly": float(monthly_savings),
            "savings_total": float(total_savings),
            "budget_mode": budget_type.lower(),
        }

        # backend expects savings_goal_cost + optional savings_goal_months
        if enable_goal and goal_amount > 0:
            payload["savings_goal_cost"] = float(goal_amount)

            if goal_months is not None:
                payload["savings_goal_months"] = int(goal_months)

            if goal_name.strip():
                payload["savings_goal_name"] = goal_name.strip()    
        new_fp = make_fingerprint(payload)

        try:
            res = requests.post(BACKEND_URL, json=payload, timeout=30)
            res.raise_for_status()
            data = res.json()

            st.session_state.results = data
            st.session_state.latest_financial_data = data
            st.session_state.plan_id = data.get("plan_id")

            # reset chat when budget changes
            if st.session_state.budget_fingerprint != new_fp:
                st.session_state.messages = []
                st.session_state.budget_fingerprint = new_fp

            st.success("Your budget plan is ready! Scroll down 👇")
        except Exception as e:
            st.error(f"Failed to connect to backend: {e}")

# ============================================================
# RESULTS
# ============================================================
if st.session_state.results:
    results = st.session_state.results
    st.session_state.latest_financial_data = results

    # ---------------------------
    # SCORE
    # ---------------------------
    with section_box():
        st.header("📊 Financial Well-Being Score")
        score_dict = results.get("score", {})
        score_value = float(score_dict.get("score", 0.0))
        state = score_dict.get("state", "unknown")

        st.progress(score_value / 100.0)
        st.write(f"**Score:** {score_value:.2f} / 100 — *{state.capitalize()}*")

    # ---------------------------
    # BUDGET PLAN
    # ---------------------------
    budget = results.get("budget", {})
    totals = budget.get("totals", {})
    deltas = budget.get("deltas", {})
    meta = budget.get("meta", {})

    with section_box():
        st.header("📌 Your Budget Plan")

        df_totals = pd.DataFrame(
            {
                "Category": [
                    "Income", "Fixed Expenses", "Debt Payments",
                    "Recommended Savings", "Recommended Variable Spending", "Leftover"
                ],
                "Amount": [
                    totals.get("income", 0),
                    totals.get("fixed", 0),
                    totals.get("debt", 0),
                    totals.get("recommended_savings", 0),
                    totals.get("recommended_variable", 0),
                    totals.get("leftover", 0),
                ],
            }
        )
        st.table(df_totals)

       # ======================================================
        #  SAVINGS GOAL (deterministic display, months optional)
        # ======================================================
        savings_goal = results.get("savings_goal") or {}
        if savings_goal.get("enabled"):
            st.subheader("🎯 Savings Goal (based on your plan)")

            #show what you're saving for (if provided)
            goal_name = (savings_goal.get("goal_name") or "").strip()
            if goal_name:
                st.write(f"**Saving for:** {goal_name}")

            cur = savings_goal.get("currency", results.get("currency", ""))
            goal_cost = savings_goal.get("goal_cost")

            planned_cap = savings_goal.get("planned_monthly_capacity")
            current_cap = savings_goal.get("current_monthly_savings")

            ideal_plan_months = savings_goal.get("ideal_months_using_planned_savings")
            ideal_current_months = savings_goal.get("ideal_months_using_current_savings")

            if goal_cost is not None:
                st.write(f"**Goal amount:** {fmt_money(goal_cost, cur)}")

            # The 2 numbers below are what make the “ideal time” meaningful
            if planned_cap is not None:
                st.write(f"**Planned monthly savings capacity:** {fmt_money(planned_cap, cur)}")
            if current_cap is not None:
                st.write(f"**Your current monthly savings input:** {fmt_money(current_cap, cur)}")

            if ideal_plan_months is not None:
                st.write(f"**Ideal time to reach goal (using your plan):** {ideal_plan_months} months")
            if ideal_current_months is not None:
                st.write(f"**Time to reach goal (using your current savings):** {ideal_current_months} months")

            notes = savings_goal.get("notes") or []
            if notes:
                st.write("**Notes:**")
                for n in notes:
                    st.write(f"- {n}")

        st.subheader("Adjustments Suggested")
        df_deltas = pd.DataFrame(
            {
                "Category": ["Savings Change", "Variable Spending Change"],
                "Amount": [deltas.get("savings_change", 0), deltas.get("variable_change", 0)],
            }
        )
        st.table(df_deltas)

        st.caption(
            f"Mode: {budget.get('mode', 'normal')} | "
            f"Flexible pool: {meta.get('flexible_pool', 0)} | "
            f"Target savings rate: {meta.get('target_savings_rate_pct', 0)}%"
        )

    # ---------------------------
    # INVESTING READINESS + VISUAL
    # ---------------------------
    investing = results.get("investing", {})
    readiness = (investing.get("readiness") or {})
    allocation_visual = investing.get("allocation_visual")

    if readiness or allocation_visual:
        with section_box():
            st.header("🧭 Investing Readiness")

            if readiness:
                ready = readiness.get("ready", False)
                st.write("**Ready to invest?** " + ("✅ Yes" if ready else "❌ Not yet"))

                blockers = readiness.get("blockers", [])
                reasons = readiness.get("reasons", [])

                if blockers:
                    st.write("**Blockers:**")
                    for b in blockers:
                        st.write(f"- {b}")

                if reasons:
                    st.write("**Reasons / Notes:**")
                    for r in reasons:
                        st.write(f"- {r}")

            if allocation_visual:
                st.subheader("📊 Sample Investment Portfolio Allocation")
                st.text(allocation_visual)

    # ---------------------------
    # LLM EXPLANATION (language only; numbers must come from backend)
    # ---------------------------
    if results.get("llm_explanation"):
        with section_box():
            st.header("✅ Personalized Advice")
            st.markdown(clean_llm_text(results["llm_explanation"]))

# ============================================================
# CHATBOT (chat_input MUST be last widget)
# ============================================================
st.divider()
st.header("🤖 AI Chatbot")
st.caption(DISCLAIMER_TEXT)

for msg in st.session_state.messages:
    st.chat_message(msg["role"]).markdown(clean_llm_text(msg["content"]))

user_message = st.chat_input("Ask something like: 'How can I improve my savings rate?'")

if user_message:
    st.session_state.messages.append({"role": "user", "content": user_message})

    safe_financial_data = strip_visual_from_financial_data(st.session_state.latest_financial_data)

    payload = {
        "message": user_message,
        "financial_data": safe_financial_data,
        "history": st.session_state.messages,
        "plan_id": st.session_state.plan_id,
    }

    try:
        res = requests.post(CHAT_URL, json=payload, timeout=30)
        res.raise_for_status()
        ai_response = res.json().get("response", "No response received.")
    except Exception as e:
        ai_response = f"Error connecting to backend: {e}"

    st.session_state.messages.append({"role": "assistant", "content": ai_response})
    st.rerun()

