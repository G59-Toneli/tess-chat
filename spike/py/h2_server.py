"""H2: FastAPI + VercelAIAdapter(sdk_version=7). MODEL=test (default, zero custo) ou MODEL=gemini."""
import os
from dotenv import load_dotenv
from fastapi import FastAPI, Request
from pydantic_ai import Agent
from pydantic_ai.models.test import TestModel
from pydantic_ai.ui.vercel_ai import VercelAIAdapter

load_dotenv("../../.env")
if os.environ.get("MODEL") == "gemini":
    from pydantic_ai.models.google import GoogleModel
    from pydantic_ai.providers.google import GoogleProvider
    model = GoogleModel("gemini-3.8-flash", provider=GoogleProvider(api_key=os.environ["GEMINI_PAID_API_KEY"]))
else:
    model = TestModel(custom_output_text="Ola Toneli, este texto chega token a token pelo protocolo v1.")
agent = Agent(model, retries=0)
app = FastAPI()

@app.post("/api/chat")
async def chat(request: Request):
    return await VercelAIAdapter.dispatch_request(request, agent=agent, sdk_version=7)
