from fastapi import FastAPI, Request
from openai import OpenAI
from dotenv import load_dotenv
import os

# ✅ Load .env file first
load_dotenv()

app = FastAPI()

# ✅ Read the key from environment
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

@app.get("/")
def root():
    return {"message": "Company AI API running successfully!"}

@app.post("/ask-ai")
async def ask_ai(request: Request):
    data = await request.json()
    user_input = data.get("question")

    try:
        response = client.chat.completions.create(
            model="gpt-4o",  # ✅ change from gpt-4o-mini → gpt-4o
            messages=[
                {"role": "system", "content": "You are the company's internal AI assistant."},
                {"role": "user", "content": user_input}
            ]
        )
        return {"answer": response.choices[0].message.content}
    except Exception as e:
        import traceback
        traceback.print_exc()  # prints full error in console
        return {"error": str(e)}
