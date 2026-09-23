"""H5: RunUsage do Pydantic AI com Google e UsageLimits(count_tokens_before_request=True)."""
import asyncio, os
from dotenv import load_dotenv
from pydantic_ai import Agent
from pydantic_ai.models.google import GoogleModel, GoogleModelSettings
from pydantic_ai.providers.google import GoogleProvider
from pydantic_ai.usage import UsageLimits
from pydantic_ai.exceptions import UsageLimitExceeded

load_dotenv("../../.env")
model = GoogleModel("gemini-3.8-flash", provider=GoogleProvider(api_key=os.environ["GEMINI_PAID_API_KEY"]))
settings = GoogleModelSettings(google_thinking_config={"thinking_level": "high"})
agent = Agent(model, model_settings=settings, retries=0)
PROMPT = "Um trem sai as 9h a 80 km/h e outro as 10h a 120 km/h no mesmo sentido. Que horas o segundo alcanca o primeiro? Responda curto."

def show(tag, u):
    print(f"[{tag}] input={u.input_tokens} output={u.output_tokens} cache_read={u.cache_read_tokens} cache_write={u.cache_write_tokens} requests={u.requests} details={u.details}")

async def main():
    limits = UsageLimits(count_tokens_before_request=True, input_tokens_limit=10_000)
    r = await agent.run(PROMPT, usage_limits=limits)
    print("nao-stream text:", r.output[:60]); show("nao-stream RunUsage", (r.usage() if callable(r.usage) else r.usage))
    print("  ultimo ModelResponse.usage:", r.response.usage)
    async with agent.run_stream(PROMPT, usage_limits=limits) as s:
        out = await s.get_output()
    print("stream text:", out[:60]); show("stream RunUsage", (s.usage() if callable(s.usage) else s.usage))
    try:
        await agent.run(PROMPT, usage_limits=UsageLimits(count_tokens_before_request=True, input_tokens_limit=5))
        print("limite baixo: NAO recusou")
    except UsageLimitExceeded as e:
        print("limite baixo: recusou antes de gerar ->", e)

asyncio.run(main())
