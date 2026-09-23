# Glossário do domínio

Termos do produto. Um significado por termo. Sem detalhe de implementação.

- **Usuário**: pessoa com conta no app. Dono de Conversas, Conectores e de um saldo de Crédito.
- **Conversa**: sequência ordenada de Mensagens de um Usuário com o assistente. Tem Configuração própria e conjunto de Tools ativas.
- **Mensagem**: um turno na Conversa. Origem: usuário, assistente, tool. Pode carregar Anexos.
- **Anexo**: imagem ou PDF enviado numa Mensagem e entregue ao modelo para análise.
- **Tool**: capacidade que o modelo pode invocar durante um turno. Origem `nativa` (fornecida pelo app), `google` (habilitada por um Conector) ou `mcp` (exposta por um Servidor MCP). O Usuário ativa e desativa por Conversa.
- **Servidor MCP**: endpoint externo cadastrado pelo Usuário que publica Tools via Model Context Protocol.
- **Conector**: vínculo autorizado do Usuário com uma plataforma externa (Google Drive, Gmail). Um Conector habilita Tools nativas que leem dados dessa plataforma e preparam Rascunhos.
- **Rascunho**: e-mail preparado pela Tool `gmail_send` que só sai pelo clique do Usuário em Enviar. Estado `pendente`, `enviado` ou `descartado` (ADR 0013).
- **Roteador**: etapa antes da chamada ao modelo principal que classifica o turno: precisa de Tool ou não, e qual. Devolve confiança. Abaixo do limiar, a decisão volta ao modelo principal.
- **Compactação**: substituição das Mensagens antigas de uma Conversa por um Resumo quando o histórico passa do limiar configurado. As Mensagens originais continuam persistidas; só o que vai ao modelo muda.
- **Resumo**: texto gerado que representa as Mensagens compactadas.
- **Crédito**: unidade de consumo expressa em dinheiro. Todo uso de modelo debita Crédito a partir do uso real informado pelo provedor e da Tabela de Preço vigente.
- **Tabela de Preço**: preço por token de cada modelo, com data de vigência.
- **Ledger**: registro somente-inserção de cada débito de Crédito. O saldo é a soma do Ledger.
- **Cap**: limite de Crédito. Existe por Usuário e global. Ao atingir, novas chamadas ao modelo são recusadas.
- **Compartilhamento**: link público somente-leitura de uma Conversa, cortado na última Mensagem existente no momento da criação. Pode ser revogado.
- **Evento de auditoria**: registro somente-inserção de uma ação relevante: login, mensagem, chamada de modelo, chamada de tool, compactação, compartilhamento, conector, cap atingido.
- **Configuração**: parâmetros persistidos por Usuário e por Conversa: modelo, nível de raciocínio, limiar de Compactação, Cap.
