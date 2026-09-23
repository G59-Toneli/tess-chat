"""H9: Jev roteando 10 frases pt-BR entre 4 tools (Choice). Uma chamada por frase."""
import asyncio, json, os
from dotenv import load_dotenv
from typesafe_sdk import AsyncTypeSafeClient, Choice

load_dotenv("../../.env")
CRITERIA = {
    "web_search": "Buscar informacao atual ou factual na internet (noticias, precos, cotacoes, eventos recentes).",
    "web_fetch": "Ler o conteudo de uma URL especifica que o usuario forneceu na mensagem.",
    "ler_pdf": "Ler um arquivo PDF que o usuario anexou nesta mensagem.",
    "nenhuma": "Responder direto, sem ferramenta: conversa, opiniao, explicacao, calculo ou texto criativo.",
}
# (frase, anexos, esperado)
CASOS = [
    ("Qual foi o resultado do jogo do Flamengo ontem?", [], "web_search"),
    ("Quanto está o dólar hoje?", [], "web_search"),
    ("Quais as novidades do Python 3.15 que saíram essa semana?", [], "web_search"),
    ("Resume pra mim esse artigo: https://pt.wikipedia.org/wiki/Cabo_Frio", [], "web_fetch"),
    ("O que diz a página https://docs.python.org/3/whatsnew/3.14.html sobre o GIL?", [], "web_fetch"),
    ("Me faz um resumo desse contrato que eu te mandei.", ["contrato_locacao.pdf"], "ler_pdf"),
    ("Qual o valor total da nota fiscal em anexo?", ["nf_setembro.pdf"], "ler_pdf"),
    ("Bom dia! Tudo certo por aí?", [], "nenhuma"),
    ("Me explica a diferença entre lista e tupla em Python.", [], "nenhuma"),
    ("Resume esse PDF pra mim.", [], "ambiguo: pede PDF sem anexo"),
]

async def main():
    rows = []
    async with AsyncTypeSafeClient(api_key=os.environ["TYPESAFE_API_KEY"]) as client:
        for frase, anexos, esperado in CASOS:
            r = await client.system_one(
                state={"mensagem_do_usuario": frase, "anexos_na_mensagem": anexos or "nenhum"},
                questions={"tool": Choice(
                    instructions="Qual ferramenta o assistente deve usar para atender esta mensagem do usuario?",
                    criteria=CRITERIA)},
            )
            a = r.choices["tool"]
            rows.append({"frase": frase, "anexos": anexos, "esperado": esperado, "escolha": a.choice,
                         "confidence": round(a.confidence, 3),
                         "probs": {k: round(v, 3) for k, v in a.probabilities.items()},
                         "model": getattr(r, "model", None), "usage": getattr(r, "usage", None) and r.usage.model_dump()})
            print(json.dumps(rows[-1], ensure_ascii=False))
    ok = sum(1 for x in rows if x["escolha"] == x["esperado"])
    print(f"acertos: {ok}/9 (o caso ambiguo nao entra)")
    from collections import Counter
    print("distribuicao:", dict(Counter(x["escolha"] for x in rows)))

asyncio.run(main())
