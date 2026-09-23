"""H5b: cache implícito do Gemini aparece no RunUsage? Prompt longo repetido 2x."""
import asyncio, os
from dotenv import load_dotenv
from pydantic_ai import Agent
from pydantic_ai.models.google import GoogleModel, GoogleModelSettings
from pydantic_ai.providers.google import GoogleProvider

load_dotenv("../../.env")
model = GoogleModel("gemini-3.8-flash", provider=GoogleProvider(api_key=os.environ["GEMINI_PAID_API_KEY"]))
agent = Agent(model, model_settings=GoogleModelSettings(google_thinking_config={"thinking_level": "low"}), retries=0)
LONG = " ".join(f"Item {i}: o produto codigo {i*7} custa {i*3} reais e pesa {i%13} kg." for i in range(300))
async def main():
    for n in (1, 2):
        r = await agent.run(LONG + "\nQual o preco do item 42? So o numero.")
        u = r.usage() if callable(r.usage) else r.usage
        print(f"[run {n}] out={r.output!r} input={u.input_tokens} output={u.output_tokens} cache_read={u.cache_read_tokens} details={u.details}")
asyncio.run(main())
