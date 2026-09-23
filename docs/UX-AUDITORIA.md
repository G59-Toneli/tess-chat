# Auditoria de UX (ticket 27)

Data: 23/09/2026. Ambiente: Vite em `localhost:5191` com proxy para a API em `localhost:8000` (banco de dev, Postgres `5433`). Brave headless via playwright-core, dark, 1440x900; telas largas também em 1280x800. Contas: `demo@toneli.dev.br` (admin) e `naoadmin27@teste.dev` (comum, criada para esta auditoria). Nenhuma mensagem nova enviada ao modelo.

Screenshots em `.scratch/desafio/screens/27-*.png`. Par antes/depois: `27-<tela>-antes.png` e `27-<tela>.png`.

Severidade: **alta** trava ou engana o fluxo principal; **média** atrapalha ou confunde; **baixa** acabamento.

## Achados

| # | Sev. | Tela | Problema | Status | Correção ou proposta |
|---|---|---|---|---|---|
| 1 | média | todas | Scrollbar nativa do sistema, larga, com trilho cinza e setas. | corrigido | Scrollbar de 8 px, sem trilho e sem setas; polegar aparece no hover da área rolável. Dark e light. `27-scrollbar*.png`. |
| 2 | média | chat novo e com histórico | Ao abrir `/` ou `/c/:id` o foco fica no `body`. O usuário precisa clicar no input para digitar. | corrigido | `autoFocus` no campo de mensagem. Conferido: `activeElement` é o `TEXTAREA` nas duas rotas. |
| 3 | média | menu do usuário | "Perfil" leva a uma tela que diz "Esta tela chega num próximo ticket". | corrigido | Item fora do menu até a tela existir. E-mail, tema e Sair já estão no menu. `27-menu-usuario-antes.png` / `27-menu-usuario.png`. |
| 4 | média | rota inexistente | Endereço errado mostra "Página não encontrada" com o texto "Esta tela chega num próximo ticket". | corrigido | Tela 404 própria: "Este endereço não existe" e botão "Voltar ao chat". `27-404-antes.png` / `27-404.png`. |
| 5 | média | sidebar | Falha ao carregar conversas mostra "Nenhuma conversa ainda", que é falso. | corrigido | Estado de erro com "Tentar de novo". Lista antiga fica se a falha for num recarregamento. |
| 6 | baixa | sidebar | Título truncado sem forma de ler inteiro. | corrigido | `title` no item: o título completo aparece no hover. |
| 7 | média | `/tools` | Descrição manda desligar "no painel lateral", que não existe. O seletor é o botão de tools na barra da mensagem. | corrigido | Texto aponta para o botão de tools na barra da mensagem. `27-tools-comum-antes.png` / `27-tools-comum.png`. |
| 8 | média | `/tools` (não-admin) | Switches desabilitados sem explicação. | corrigido | Para não-admin a descrição diz que só a administração liga e desliga para todas as conversas. |
| 9 | baixa | `/tools` vazio | Estado vazio fala em "migração". | corrigido | "Nenhuma tool está disponível no momento." |
| 10 | média | `/conectores` | Diz que `gmail_send` nasce "desligada em cada conversa até você ligar". A emenda do ADR 0013 (migração 0015) fez ela nascer ligada. | corrigido | "Só prepara o rascunho; o e-mail sai quando você clica em Enviar." `27-conectores-comum-antes.png` / `27-conectores-comum.png`. |
| 11 | baixa | chat com tool | Linha do Roteador: "roteado para web_search (1.00)". Decimal com ponto, fora do pt-BR usado em `/config` (0,7). | corrigido | "Roteador escolheu web_search · confiança 1,00". `27-chat-tool-antes.png` / `27-chat-tool.png`. |
| 12 | baixa | `/creditos` | Coluna "Thinking" em inglês; `/config` chama de "raciocínio". Rótulo "US$ 0,08" do eixo cortado a 1280 px. | corrigido | Coluna "Raciocínio"; margem direita do gráfico maior. `27-creditos-1280*.png`. |
| 13 | baixa | `/auditoria` | A 1280 px o filtro "Até" cai para outra linha. Coluna "Tokens" mostra "1.482 / 113" sem dizer o que é cada número. | corrigido | Filtros mais estreitos, cabem numa linha. Coluna "Tokens (entrada / saída)". `27-auditoria-1280*.png`. |
| 14 | baixa | `/mcp` | Toggle diz "Ativo/Desligado"; `/tools` diz "Ligada/Desligada". Toggle sem feedback. Confirmar remoção sem cor de ação destrutiva, ao contrário de Apagar conversa e Revogar link. Dica "Guardado cifrado" colada no rodapé do card. | corrigido | "Ligado/Desligado"; toast ao ligar e desligar; botão Remover vermelho; espaço antes do rodapé. |
| 15 | **alta** | navegação | As 8 telas internas ficam só no menu do avatar. Nada na tela mostra que Tools, Servidores MCP, Conectores ou Créditos existem. O avaliador pode não achar metade do produto. | proposta | Bloco fixo no rodapé da sidebar com os itens em grupos: Conversa (Configuração, Tools, Servidores MCP, Conectores), Conta (Créditos, Compartilhados, Auditoria), Administração. O avatar fica com tema e Sair. |
| 16 | **alta** | login | "Entrar com conta demo" só preenche os campos; é preciso clicar em "Entrar" de novo. O rótulo promete entrar. O guia pede a conta demo em destaque e o botão é secundário. | proposta | Um clique: o botão entra direto e vira o botão primário da tela. Não feito aqui: muda o fluxo e os scripts de screenshot dos outros agentes dependem do comportamento atual. |
| 17 | média | chat com histórico | Área do chat sem título da conversa e sem ações. Só o destaque na sidebar diz onde você está. Renomear, compartilhar e configurar a conversa ficam escondidos no "…" da sidebar ou em `/config`. | proposta | Header do chat com o título e um menu: Renomear, Compartilhar, Configuração desta conversa (`/config?conversa=`). |
| 18 | média | `/tools` e seletor de tools | A descrição mostrada é o texto escrito para o modelo: "NÃO envia", "Depois de chamar, diga ao usuário que…". | proposta | Campo de descrição para o usuário na tabela de tools, separado da descrição para o modelo. Exige mudança em `api/`. |
| 19 | média | chat novo | Sem conversa criada, o contador ("6 tools") e o seletor usam o catálogo global. Contam as tools do Google para quem não conectou o Google. Dentro da conversa a API já filtra. | proposta | Endpoint "tools disponíveis para mim" com a mesma regra da API, usado pela tela nova. Copiar a regra no front divergiria com o tempo. |
| 20 | média | `/admin` | 1.410 contas numa tabela só, sem paginação nem busca. | proposta | Paginação e busca por e-mail. Exige mudança em `api/`. |
| 21 | média | chat com anexo | PDF antigo aparece como "Documento". A parte gravada tem `filename: null`. | proposta | Persistir o nome do arquivo na parte da Mensagem. Origem em `api/`. |
| 22 | baixa | `/compartilhados` | Cada clique em Compartilhar cria um link novo. A lista acumula links da mesma conversa. | proposta | Mostrar o link vigente da conversa e oferecer "gerar novo link". |
| 23 | baixa | chat com tool (histórico) | Duração do bloco de tool só existe no stream ao vivo. Ao recarregar, some. | proposta | Persistir a duração da chamada junto do resultado. Exige `api/`. |
| 24 | baixa | seletor, bloco de tool, `/tools` | Nomes de tool em snake_case (`drive_search_read`) como rótulo principal. | proposta | Rótulo em pt-BR ("Buscar no Drive") e o nome técnico em mono, menor. |
| 25 | baixa | páginas internas | Três larguras e dois paddings: formulários `max-w-3xl px-4 py-8`, Compartilhados `max-w-4xl p-8`, tabelas `max-w-6xl p-8`. O título muda de posição entre telas. | proposta | Componente de página com duas larguras (leitura e tabela). Não feito: mexeria em nove arquivos sem mudar comportamento. |
| 26 | baixa | chat com compactação | O marcador "Histórico compactado aqui" não mostra o Resumo. | proposta | Marcador expansível com o texto do Resumo. |
| 27 | baixa | `/perfil` | Trocar senha não existe; a rota segue placeholder. | proposta | Tela de perfil com e-mail e troca de senha, depois volta ao menu. |

## Telas sem achado novo

| Tela | O que foi conferido |
|---|---|
| login | Estados de entrada, cadastro e erro ("E-mail ou senha incorretos."). Achado só no botão demo (16). |
| chat com rascunho de e-mail | Cartão com Para, Assunto, corpo, estado "Enviado"; botões Enviar e Descartar só quando pendente. |
| `/config` | Título, descrição, escopo conta ou conversa; "Em uso" com herdado/próprio; Salvar desabilitado até mudar algo; toast ao salvar. |
| share público | Banner "Compartilhada por … Somente leitura", sem sidebar; link inexistente mostra "Link indisponível" com ação. |
| `/admin` (não-admin) | "Acesso restrito" com ação "Ver meu crédito". |
| `/auditoria` (não-admin) | Só os próprios eventos, sem filtro de usuário, paginação visível. |
| `/creditos` (não-admin) | Sem alternância para Global. |
| diálogos | Renomear foca o campo; Radix prende o foco e fecha com Esc; foco visível no Tab. |
| 1280 px | Sem overflow horizontal em nenhuma tela medida (`scrollWidth <= innerWidth`). |

## Não verificado visualmente

- **Chat com compactação.** Nenhuma conversa do demo nem do não-admin tem Resumo no banco de dev. As que têm são de usuários de teste sem senha conhecida. Avaliado pelo código de `MarcadorCompactacao` e pela screenshot `12-chat-marcador.png` do ticket 12.
- **Estados de erro das páginas internas.** Não simulados nesta auditoria: foram capturados nos tickets 13, 14, 15 e 17. O código de cada lista tem vazio, carregando e erro com "Tentar de novo".
