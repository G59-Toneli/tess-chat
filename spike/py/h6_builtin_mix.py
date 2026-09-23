"""H6: google_search built-in + function declaration nossa no mesmo request."""
import os
from dotenv import load_dotenv
from google import genai
from google.genai import types

load_dotenv("../../.env")
client = genai.Client(api_key=os.environ["GEMINI_PAID_API_KEY"])
fd = types.FunctionDeclaration(
    name="ler_pdf", description="Le um PDF anexado pelo usuario e devolve o texto.",
    parameters=types.Schema(type="OBJECT", properties={"arquivo_id": types.Schema(type="STRING")}, required=["arquivo_id"]),
)
cfg = types.GenerateContentConfig(
    tools=[types.Tool(google_search=types.GoogleSearch()), types.Tool(function_declarations=[fd])],
    automatic_function_calling=types.AutomaticFunctionCallingConfig(disable=True),
    thinking_config=types.ThinkingConfig(thinking_level="low"),
    tool_config=types.ToolConfig(include_server_side_tool_invocations=True),
)
try:
    r = client.models.generate_content(model="gemini-3.8-flash", contents=os.environ.get("H6_PROMPT", "Qual a cotacao do dolar hoje? Responda curto."), config=cfg)
    print("ACEITOU")
    print("text:", (r.text or "")[:120])
    print("function_calls:", r.function_calls)
    gm = r.candidates[0].grounding_metadata
    print("grounding queries:", gm.web_search_queries if gm else None)
    print("usage:", {k: v for k, v in r.usage_metadata.model_dump().items() if v is not None and not k.endswith('details')})
except Exception as e:
    print("ERRO:", type(e).__name__, e)
