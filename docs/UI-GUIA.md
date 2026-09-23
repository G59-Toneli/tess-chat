# Guia de UI

Vale para todo ticket que toca `web/`. Meta do Toneli: tela bonita, clara e visível, que ele não precise revisar.

## Fontes
- Componentes: shadcn/ui (https://ui.shadcn.com/docs/components), base Radix. Importar, não reescrever.
- Chat: AI Elements (conversation, message, prompt-input, response, sources, tool, reasoning, loader).
- Inspiração de acabamento: https://www.beautifului.dev/ (loadings, animação de "digitando", estados vazios, transições). Reaproveitar padrões, não copiar código sem licença clara.

## Regras
- **Dark mode padrão.** Tema via `next-themes` ou equivalente, toggle no menu do usuário. Light funciona, mas dark é o que o Toneli e o avaliador vão ver.
- Densidade média. Tipografia do shadcn. Sem gradiente chamativo, sem cor fora dos tokens do tema.
- Todo estado tem tela: vazio ("nenhuma conversa ainda", com ação), carregando (skeleton ou loader do AI Elements), erro (mensagem em pt-BR, ação de tentar de novo).
- Streaming: texto aparece token a token; indicador de "pensando" enquanto não chega o primeiro token; tool call aparece como bloco recolhível com nome, args e duração.
- pt-BR em toda string visível. Data e hora no fuso do browser.
- Desktop primeiro. Mobile só se sair de graça com o layout do shadcn (sidebar recolhível). Não gastar ticket com mobile.
- Acessibilidade básica: foco visível, labels em inputs, contraste do tema padrão.

## Telas
| Rota | Conteúdo |
|---|---|
| `/login` | e-mail + senha, alternar cadastro, conta demo em destaque |
| `/` e `/c/:id` | sidebar de conversas (buscar, nova, renomear, apagar), chat, painel lateral de tools ativas da conversa |
| `/s/:shareId` | conversa pública read-only, banner "compartilhada por", sem sidebar |
| `/config` | modelo, nível de thinking, limiar de compactação, limiar do roteador, tema |
| `/tools` | tools nativas e MCP: ligar/desligar global, ver schema |
| `/mcp` | servidores MCP: adicionar URL + header, testar, listar tools, remover |
| `/conectores` | Google: conectar, escopos, revogar, status do token |
| `/creditos` | saldo, cap, gasto por dia e por modelo, últimas linhas do ledger |
| `/auditoria` | tabela de eventos com filtros, detalhe do payload em drawer |
| `/compartilhados` | meus links: abrir, copiar, revogar |
| `/perfil` | e-mail, trocar senha, sair |
| `/admin` (só admin) | cap global, usuários, gasto total |

## Verificação visual
Antes de fechar um ticket de front: rodar a app, abrir cada tela tocada com Playwright (MCP `plugin_playwright`), usando o **Brave** como browser (executável `C:Program FilesBraveSoftwareBrave-BrowserApplicationbrave.exe`), nunca o Google Chrome, tirar screenshot em dark mode 1440x900, salvar em `.scratch/desafio/screens/NN-<tela>.png`, e checar: sem texto cortado, sem overflow horizontal, estados vazio/carregando/erro visíveis. Screenshot vai no relatório ao orquestrador como caminho, não colado.
