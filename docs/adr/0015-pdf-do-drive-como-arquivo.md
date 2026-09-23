# ADR 0015 — PDF do Drive entra no modelo como arquivo, pelo caminho do Anexo

**Status:** aceito, 2026-09-23. Complementa o ADR 0010 (Conector Google).

## Contexto
`drive_search_read` só lia Docs, Sheets, Slides e texto. PDF caía em "outros achados". Feedback do Toneli em 23/09: pediu "a guia autorizada" do Drive e o modelo respondeu que não lê PDF. O mesmo modelo já lê PDF quando o Usuário anexa (Gemini, `media_resolution` medium). Guia e boleto costumam ser escaneados.

## Decisão
1. Sem arquivo de texto entre os achados, a Tool baixa o primeiro PDF (`alt=media`) e devolve `ToolReturn`: texto curto no `return_value` (nome, id, marcador `[arquivo do Drive: nome]`, outros achados) e o PDF em `content` como `BinaryContent` `application/pdf`, com `vendor_metadata` = `MEDIA_PDF` de `app/anexos.py`.
2. **Teto de 10 MB**, lido do `size` da busca antes de baixar. Acima disso, texto explicando o limite e nenhum download.
3. **Bytes só no turno da Tool.** Antes de gravar, `chat._sem_arquivo_de_tool` tira do turno o `UserPromptPart` com o arquivo. O banco guarda só o retorno com o marcador, como `sem_bytes` faz com o Anexo. Turno seguinte, histórico recarregado e Compactação leem o banco e nunca veem os bytes.
4. Evento `tool_call` existente ganha `mime` e `bytes` no payload (vêm do `ToolReturn.metadata`).

### Alternativas descartadas
- **Texto extraído no servidor (pypdf).** Vazio em PDF escaneado, que é o caso de uso. Decisão do Toneli.
- **PDF dentro do retorno da tool (`function_response.parts` nativo do Gemini 3).** Menos tokens de moldura, mas o Pydantic AI 2.47 não repassa `vendor_metadata` nesse caminho (`_map_file_to_function_response_part`): a `media_resolution` medium se perderia. O `ToolReturn.content` vira parte de usuário logo depois do `function_response`, pelo `_map_file_to_part`, que aplica a resolução.

## Consequências
- Um PDF de página cheia custa ~560 tokens de entrada por página (resolução medium), só no turno da Tool.
- Perguntas de seguimento sobre o PDF dependem do que o modelo já respondeu: o arquivo não volta. Para reler, o modelo chama a Tool de novo.
- Só o primeiro PDF é lido. Mais de um PDF relevante exige outra busca.
