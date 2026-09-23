"""H4: onde usage_metadata aparece no stream do Gemini e se thoughts está dentro de candidates."""
import os
from dotenv import load_dotenv
from google import genai
from google.genai import types

load_dotenv("../../.env")
client = genai.Client(api_key=os.environ["GEMINI_PAID_API_KEY"])  # chave paga explícita
MODEL = "gemini-3.8-flash"
PROMPT = "Um trem sai as 9h a 80 km/h e outro as 10h a 120 km/h no mesmo sentido. Que horas o segundo alcanca o primeiro? Responda curto."
cfg = types.GenerateContentConfig(thinking_config=types.ThinkingConfig(thinking_level="high"))

def fields(u):
    if u is None:
        return None
    return {k: v for k, v in u.model_dump().items() if v is not None}

def check(u):
    p, c, t, tot = (u.prompt_token_count or 0), (u.candidates_token_count or 0), (u.thoughts_token_count or 0), (u.total_token_count or 0)
    print(f"  prompt+candidates        = {p+c}  (total={tot}) -> {'IGUAL' if p+c==tot else 'diferente'}")
    print(f"  prompt+candidates+thoughts = {p+c+t}  (total={tot}) -> {'IGUAL' if p+c+t==tot else 'diferente'}")

print("== STREAM ==")
last = None
for i, ch in enumerate(client.models.generate_content_stream(model=MODEL, contents=PROMPT, config=cfg)):
    txt = (ch.text or "").replace("\n", " ")[:40]
    print(f"chunk {i}: text={txt!r} usage={fields(ch.usage_metadata)}")
    if ch.usage_metadata is not None:
        last = ch.usage_metadata
print("ultimo usage do stream:"); check(last)

print("== NAO-STREAM ==")
r = client.models.generate_content(model=MODEL, contents=PROMPT, config=cfg)
print("text:", r.text.replace("\n", " ")[:80])
print("usage:", fields(r.usage_metadata)); check(r.usage_metadata)
