# FinancAI

## How to Start

download everything from requirements.txt

## Testing the Backend

open a terminal in the backend folder and enter: ``set GROQ_API_KEY=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 echo %GROQ_API_KEY%`` or ``export GROQ_API_KEY=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``

type in ``uvicorn main:app --reload`` and run

assuming no error occurs, you should see an IP Address where you can test the backend out. 

## Opening the frontend

Open a terminal in the main folder for the program and enter: ``streamlit run app.py``
**Note**: Make sure to run the Backend *before* the frontend. Also make sure that the backend stays running in the background whenever the site is being used.
