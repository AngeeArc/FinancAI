import streamlit as st
import pandas as pd
import yfinance as yf
import openai
from backend.finance_logic import calculate_budget, financial_wellbeing_score, recommendation
import os
import requests


# --------------------------
# Streamlit Config
# --------------------------
st.set_page_config(page_title="FinancAI", page_icon="💸", layout="wide")

openai.api_key = os.getenv("OPENAI_API_KEY")


# --------------------------
# Currency Helper
# --------------------------
def currency_symbol(currency):
    return currency.split(" ")[1]   # extracts $, €, £, etc.


# --------------------------
# Title
# --------------------------
st.title("💸 FinancAI — Your Personal Financial Assistant")


# ==========================
# 1. USER INPUT SECTION
# ==========================
st.header("1. Enter Your Financial Details")

currency = st.selectbox(
    "Select Your Currency",
    ["USD $", "EUR €", "GBP £", "CAD $", "AUD $", "JPY ¥", "INR ₹"],
    key="currency"
)

col1, col2 = st.columns(2)

with col1:
    income = st.number_input("Monthly Income", min_value=0.0, key="income")
    rent = st.number_input("Rent", min_value=0.0, key="rent")
    utilities = st.number_input("Utilities", min_value=0.0, key="utilities")
    transport = st.number_input("Transportation", min_value=0.0, key="transport")

with col2:
    debt = st.number_input("Monthly Debt Payments", min_value=0.0, key="debt")
    savings = st.number_input("Current Monthly Savings", min_value=0.0, key="savings")
    investments = st.number_input("Total Investments", min_value=0.0, key="investments")
    emergency_fund = st.number_input("Emergency Fund Savings Amount", min_value=0.0, key="emergency")

mode = st.radio(
    "Choose your budget mode",
    ["Super Budget", "Normal", "Relaxed"],
    key="mode"
)

generate = st.button("Generate Financial Plan")


# ==========================
# 2. RESULTS SECTION
# ==========================
if generate:
    payload = {
        "income": income,
        "rent": rent,
        "utilities": utilities,
        "transport": transport,
        "debt": debt,
        "savings": savings,
        "investments": investments,
        "emergency_fund": emergency_fund,
        "budget_mode": mode
    }

    # Send data to FastAPI backend
    response = requests.post("http://127.0.0.1:8000/calculate", json=payload)

    if response.status_code == 200:
        data = response.json()
        results = {
            "fixed_expenses": data["fixed_expenses"],
            "disposable": data["disposable"],
            "suggested_savings": data["suggested_savings"],
            "spending_budget": data["spending_budget"]
        }
        score = data["score"]
        rec = data["recommendation"]
    else:
        st.error("Error contacting backend. Please make sure FastAPI is running.")
        st.stop()


    symbol = currency_symbol(currency)


    # --------------------------
    # Budget Table
    # --------------------------
    st.subheader("📊 Budget Breakdown")

    df = pd.DataFrame({
        "Category": ["Fixed Expenses", "Disposable Income", "Recommended Savings", "Spending Budget"],
        "Amount": [
            f"{symbol}{results['fixed_expenses']:.2f}",
            f"{symbol}{results['disposable']:.2f}",
            f"{symbol}{results['suggested_savings']:.2f}",
            f"{symbol}{results['spending_budget']:.2f}"
        ]
    })

    st.table(df)

    # --------------------------
    # Financial Well-Being Score
    # --------------------------
    st.subheader("📈 Financial Well-Being Score")

# Color logic
if score < 40:
    gauge_color = "#ff4d4d"   # red
elif score < 70:
    gauge_color = "#ffcc00"   # yellow
else:
    gauge_color = "#00cc66"   # green

# Gauge bar
st.markdown(
    f"""
    <div style="width: 100%; background-color: #eee; border-radius: 10px; height: 25px;">
        <div style="
            width: {score}%;
            background-color: {gauge_color};
            height: 25px;
            border-radius: 10px;">
        </div>
    </div>
    """,
    unsafe_allow_html=True
)

# Text below gauge
st.write(f"### **Score: {score}/100**")
st.write(f"**Recommendation:** {rec}")

import matplotlib.pyplot as plt
import io

# ---------------------------
#  Spending Pie Chart
# ---------------------------

st.subheader("Monthly Spending Breakdown (Pie Chart)")

# Only show if user generated plan
if income > 0:
    labels = ["Fixed Expenses", "Recommended Savings", "Spending Budget"]
    values = [
        results["fixed_expenses"],
        results["suggested_savings"],
        results["spending_budget"]
    ]

    # Create chart
    fig, ax = plt.subplots(figsize=(2, 2))   # smaller pie chart
    ax.pie(values, labels=labels, autopct="%1.0f%%", startangle=90)
    ax.axis("equal")

    # Display in Streamlit
    st.pyplot(fig)

# ---------------------------
#  12-Month Savings Projection
# ---------------------------

st.subheader("📈 12-Month Savings Projection")

if income > 0:
    # Starting amount
    starting_savings = savings

    # Monthly savings = recommended savings from your budget function
    monthly_save = results["suggested_savings"]

    # Generate projection for 12 months
    months = list(range(1, 13))
    projected_savings = [starting_savings + monthly_save * m for m in months]

    # Create line chart
    fig2, ax2 = plt.subplots(figsize=(4, 2))
    ax2.plot(months, projected_savings, marker="o")
    ax2.set_title("Savings Growth Over 12 Months")
    ax2.set_xlabel("Month")
    ax2.set_ylabel(f"Savings ({currency})")
    ax2.grid(True)

    st.pyplot(fig2)

# ==========================
# 3. STOCK MARKET SECTION
# ==========================
st.header("2. Check Stock Prices")

symbol_input = st.text_input("Enter stock symbol (e.g., AAPL, TSLA):", key="symbol_input")

if st.button("Get Price"):
    if symbol_input:
        stock = yf.Ticker(symbol_input)
        data = stock.history(period="1d")
        if not data.empty:
            price = data["Close"][0]
            st.success(f"📉 **Current price of {symbol_input.upper()}: {symbol}{price:.2f}**")
        else:
            st.error("❗ Stock symbol not found.")


# ==========================
# 4. AI CHATBOT
# ==========================
st.header("3. FinancAI Chatbot")

chat_input = st.text_input("Ask any financial question:", key="chat_input")

if st.button("Ask FinancAI"):
    if chat_input:
        response = openai.ChatCompletion.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "You are a helpful financial assistant."},
                {"role": "user", "content": chat_input}
            ]
        )
        st.write(response.choices[0].message["content"])
