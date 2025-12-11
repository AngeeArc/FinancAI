import streamlit as st
import matplotlib.pyplot as plt
import requests

# ============================================================
# CONFIG
# ============================================================
BACKEND_URL = "http://localhost:8000/calculate-budget"   # Update if hosted

st.set_page_config(
    page_title="FinancAI",
    page_icon="💰",
    layout="centered",
)

# ============================================================
# STYLING
# ============================================================
st.markdown("""
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
</style>
""", unsafe_allow_html=True)

# ============================================================
# SESSION STATE
# ============================================================
if "results" not in st.session_state:
    st.session_state.results = None

if "messages" not in st.session_state:
    st.session_state.messages = []

# ============================================================
# HEADER
# ============================================================
st.title("💰 FinancAI — Your AI Financial Planner")
st.write("Enter your financial details to generate a personalized breakdown and chat with your AI assistant.")

# ============================================================
# INPUT FORM
# ============================================================
st.markdown("<div class='section-box'>", unsafe_allow_html=True)
st.header("📋 Financial Inputs")

# Create two main columns
left, right = st.columns(2)

# ---------------------------
# LEFT COLUMN
# ---------------------------
with left:

    # Currency
    currency = st.selectbox(
        "Currency",
        ["USD ($)", "EUR (€)", "GBP (£)", "CAD ($)", "AUD ($)", "JPY (¥)", "INR (₹)", "Other"]
    )
    if currency == "Other":
        currency = st.text_input("Enter currency symbol or code:")

    # Income
    income = st.number_input(f"Monthly Income {currency}", min_value=0.0, step=100.0)

    # ---------------------------
    # FIXED EXPENSES
    # ---------------------------
    st.subheader("🏠 Fixed Expenses")
    fixed_categories = ["Rent", "Utilities", "Transportation", "Insurance", "Phone", "Internet", "Other"]
    fixed_expenses = {}
    fixed_count = st.number_input("Number of Fixed Expenses", min_value=0, max_value=20, key="fixed_count")

    for i in range(fixed_count):
        colA, colB = st.columns(2)
        cat = colA.selectbox(f"Category {i+1}", fixed_categories, key=f"fcat{i}")
        amt = colB.number_input(f"Amount {i+1} {currency}", min_value=0.0, step=10.0, key=f"famt{i}")
        fixed_expenses[cat] = amt

    # ---------------------------
    # VARIABLE EXPENSES
    # ---------------------------
    st.subheader("🛒 Variable Expenses")
    variable_categories = ["Groceries", "Hobbies", "Entertainment", "Subscriptions", "Type Other Variable Here (e.g. Smoking, Coffee, Eating Out)"]
    variable_expenses = {}
    var_count = st.number_input("Number of Variable Expenses", min_value=0, max_value=20, key="var_count")

    for i in range(var_count):
        colA, colB = st.columns(2)
        cat = colA.selectbox(f"Category {i+1}", variable_categories, key=f"vcat{i}")
        amt = colB.number_input(f"Amount {i+1} {currency}", min_value=0.0, step=10.0, key=f"vamt{i}")
        variable_expenses[cat] = amt


# ---------------------------
# RIGHT COLUMN
# ---------------------------
with right:

    st.subheader("💳 Debt")
    monthly_debt = st.number_input(f"Monthly Debt Payments {currency}", min_value=0.0, step=10.0)
    total_debt = st.number_input(f"Total Debt {currency}", min_value=0.0, step=100.0)

    st.subheader("💵 Savings")
    monthly_savings = st.number_input(f"Monthly Savings {currency}", min_value=0.0, step=10.0)
    total_savings = st.number_input(f"Total Savings {currency}", min_value=0.0, step=100.0)

# ============================================================
# GENERATE BUTTON → CALL BACKEND
# ============================================================
if st.button("✨ Generate Budget Plan"):
    payload = {
        "monthly_income": income,
        "fixed_expenses": sum(fixed_expenses.values()),
        "variable_expenses": sum(variable_expenses.values()),
        "variable_breakdown": [
            {"name": name, "amount": amount}
            for name, amount in variable_expenses.items()
        ],
        "debt_monthly_payment": monthly_debt,
        "debt_total_balance": total_debt,
        "savings_monthly": monthly_savings,
        "savings_total": total_savings,
        "budget_mode": budget_type.lower()
    }

    try:
        response = requests.post(BACKEND_URL, json=payload)
        response.raise_for_status()
        st.session_state.results = response.json()
        st.success("Your budget plan is ready! Scroll down 👇")

    except Exception as e:
        st.error(f"Failed to connect to backend: {e}")

# Budget mode
budget_type = st.radio("Budget Style", ["Super", "Normal", "Relaxed"])

st.markdown("</div>", unsafe_allow_html=True)

# ============================================================
# RESULTS SECTION
# ============================================================
if st.session_state.results:
    results = st.session_state.results

    # ---------------------------
    # SCORE
    # ---------------------------
    st.markdown("<div class='section-box'>", unsafe_allow_html=True)
    st.header("📊 Financial Well-Being Score")

    score_value = results["score"]
    st.progress(score_value / 100)
    st.write(f"**Score:** {score_value} / 100 — *{results['state'].capitalize()}*")
    st.markdown("</div>", unsafe_allow_html=True)

    # ---------------------------
    # RECOMMENDED SAVINGS
    # ---------------------------
    st.markdown("<div class='section-box'>", unsafe_allow_html=True)
    st.header("📈 Current vs Recommended Monthly Savings")

    recommended = results["recommended_savings"]

    fig, ax = plt.subplots()
    ax.pie(
        [monthly_savings, recommended],
        labels=["Current Savings", "Recommended Savings"],
        autopct="%1.1f%%"
    )
    st.pyplot(fig)
    st.markdown("</div>", unsafe_allow_html=True)

    # ---------------------------
    # RAW JSON
    # ---------------------------
    st.markdown("<div class='section-box'>", unsafe_allow_html=True)
    st.header("📄 Generated Budget JSON")
    st.json(results)
    st.markdown("</div>", unsafe_allow_html=True)

# ============================================================
# CHATBOT
# ============================================================
st.markdown("<div class='section-box'>", unsafe_allow_html=True)
st.header("🤖 AI Chatbot")

# History
for msg in st.session_state.messages:
    st.chat_message(msg["role"]).write(msg["content"])

# Input
user_message = st.chat_input("Ask something like: 'How can I improve my savings rate?'")
if user_message:
    st.session_state.messages.append({"role": "user", "content": user_message})
    ai_response = "I'm analyzing your financial profile! (Backend integration for chatbot is coming soon...)"
    st.session_state.messages.append({"role": "assistant", "content": ai_response})
    st.experimental_rerun()

st.markdown("</div>", unsafe_allow_html=True)
