# backend/main.py
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import subprocess
from .finance_logic import compute_financial_score

app = FastAPI()

# Allow frontend access
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---------------------------
# 1) FINANCIAL SCORE ENDPOINT
# ---------------------------
@app.post("/score")
async def score(payload: dict):
    try:
        result = compute_financial_score(payload)
        return {"result": result}
    except Exception as e:
        return {"error": str(e)}

# ---------------------------
# 2) CHATBOT ENDPOINT (OLLAMA)
# ---------------------------
@app.post("/chat")
async def chat(payload: dict):
    user_msg = payload.get("message", "")

    if not user_msg.strip():
        return {"response": "Please enter a message."}

    try:
        # Call Ollama (make sure model exists: mistral/llama3/etc.)
        process = subprocess.Popen(
            ["ollama", "run", "mistral"],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )

        output, _ = process.communicate(user_msg)

        return {"response": output}

    except Exception as e:
        return {"response": f"Error talking to Ollama: {e}"}

