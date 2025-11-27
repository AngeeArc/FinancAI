import gradio as gr
import requests


BACKEND_URL_SCORE = "http://127.0.0.1:8000/score"
BACKEND_URL_CHAT = "http://127.0.0.1:8000/chat"


def call_financial_score(monthly_income, fixed_expenses, variable_expenses,
                         debt_monthly_payment, debt_total_balance,
                         savings_monthly, savings_total, emergency_months_target):

    payload = {
        "monthly_income": monthly_income,
        "fixed_expenses": fixed_expenses,
        "variable_expenses": variable_expenses,
        "debt_monthly_payment": debt_monthly_payment,
        "debt_total_balance": debt_total_balance,
        "savings_monthly": savings_monthly,
        "savings_total": savings_total,
        "emergency_months_target": emergency_months_target
    }

    try:
        result = requests.post(BACKEND_URL_SCORE, json=payload).json()
        return result
    except Exception as e:
        return {"error": f"Backend not reachable: {e}"}


# ----------------------------- CHATBOT -----------------------------------

def chatbot_reply(message, history):

    try:
        response = requests.post(
            BACKEND_URL_CHAT,
            json={"message": message, "history": history}
        ).json()

        reply = response.get("reply", "No response from chatbot.")
        return reply

    except Exception as e:
        return f"Chat backend error: {e}"


# -------------------------------- UI --------------------------------------

def build_ui():

    with gr.Blocks() as demo:

        gr.Markdown("# 💰 FinancAI — Your Personal Finance Dashboard")

        with gr.Row():

            with gr.Column(scale=1):
                monthly_income = gr.Number(label="Monthly Income")
                fixed_expenses = gr.Number(label="Fixed Expenses")
                variable_expenses = gr.Number(label="Variable Expenses")
                debt_payment = gr.Number(label="Debt Monthly Payment")
                debt_balance = gr.Number(label="Debt Total Balance")
                savings_monthly = gr.Number(label="Monthly Savings")
                savings_total = gr.Number(label="Total Savings")
                emergency_target = gr.Number(label="Emergency Fund Target (months)", value=3)

                calculate_btn = gr.Button("Calculate Score")

            with gr.Column(scale=1):
                output_score = gr.JSON(label="Financial Score Output")

        # Chatbot Section
        gr.Markdown("## 🤖 Finance Chatbot")

        chat_history = gr.Chatbot(label="Chat with FinancAI")
        chat_input = gr.Textbox(label="Type your message…", placeholder="Ask anything about your finances!")

        chat_input.submit(
            lambda msg, hist: (hist + [[msg, chatbot_reply(msg, hist)]]),
            [chat_input, chat_history],
            [chat_history]
        )

        calculate_btn.click(
            call_financial_score,
            [
                monthly_income, fixed_expenses, variable_expenses,
                debt_payment, debt_balance, savings_monthly,
                savings_total, emergency_target
            ],
            output_score
        )

    return demo


app = build_ui()

if __name__ == "__main__":
    app.launch()
