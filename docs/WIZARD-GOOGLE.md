# Wizard — Conector Google (Gmail + Drive), parte humana

Refs: ADR 0010, issue 18. Tempo estimado: 30 min. **INFERIDO**, sem número oficial do Google.

Este guia cobre só as etapas que exigem humano no console do Google Cloud. O código do conector é a parte AFK da issue 18.

Script interativo equivalente: `scripts/wizard-google.sh`. Ele abre cada URL, pede os valores e grava o `.env`. Roda da raiz do repo:

```bash
bash scripts/wizard-google.sh
```

Os rótulos abaixo estão em inglês. Com o console em português, procura o rótulo equivalente. Para evitar dúvida, troca o idioma do console para inglês antes de começar.

## Antes de começar

- Faz login no navegador com a conta Google do Toneli. Essa conta vira dona do projeto.
- Tem em mãos os e-mails dos testadores. Sem o e-mail na lista de test users, a pessoa não consegue autorizar.

## Valores gerados

| Valor | Onde aparece | Destino | Secreto |
|---|---|---|---|
| `GOOGLE_CLIENT_ID` | Tela do client OAuth criado | `.env` na raiz | não |
| `GOOGLE_CLIENT_SECRET` | Tela do client OAuth criado, ou JSON baixado | `.env` na raiz | sim |

---

## Passo 1 — Criar o projeto

URL: https://console.cloud.google.com/projectcreate

1. Em **Project name**, digita `desafio-chat`.
2. Em **Location**, deixa `No organization`.
3. Clica **Create**.
4. Espera a notificação de projeto criado. Clica **Select project** na notificação.

**Confirma:** o seletor de projeto no topo da tela mostra `desafio-chat`. Todos os passos seguintes usam esse projeto. Confere o seletor antes de cada passo.

## Passo 2 — Habilitar Gmail API e Google Drive API

URL Gmail API: https://console.cloud.google.com/apis/library/gmail.googleapis.com
URL Drive API: https://console.cloud.google.com/apis/library/drive.googleapis.com

1. Abre a URL da Gmail API.
2. Clica **Enable**.
3. Abre a URL da Drive API.
4. Clica **Enable**.

**Confirma:** abre https://console.cloud.google.com/apis/dashboard. A lista mostra `Gmail API` e `Google Drive API`.

## Passo 3 — Configurar a consent screen (External, Testing)

URL: https://console.cloud.google.com/auth/overview

1. Clica **Get started**.
2. Em **App Information**, digita **App name** `Desafio Chat`.
3. Em **User support email**, seleciona o e-mail do Toneli. Clica **Next**.
4. Em **Audience**, seleciona **External**. Clica **Next**.
5. Em **Contact Information**, digita o e-mail do Toneli. Clica **Next**.
6. Marca o aceite da **Google API Services: User Data Policy**. Clica **Continue**.
7. Clica **Create**.

Não clica **Publish app**. O app fica em Testing.

**Confirma:** abre https://console.cloud.google.com/auth/audience. **Publishing status** mostra `Testing`. **User type** mostra `External`.

## Passo 4 — Adicionar os escopos

URL: https://console.cloud.google.com/auth/scopes

1. Clica **Add or remove scopes**.
2. No filtro, digita `gmail.readonly`. Marca `https://www.googleapis.com/auth/gmail.readonly`.
3. No filtro, digita `drive.readonly`. Marca `https://www.googleapis.com/auth/drive.readonly`.
4. Clica **Update**.
5. Clica **Save** no fim da página.

Sem as APIs do passo 2, os escopos não aparecem no filtro. Nesse caso, volta ao passo 2.

**Confirma:** a seção **Your restricted scopes** lista os dois escopos. Escopo restrito em Testing não exige verificação do Google.

## Passo 5 — Adicionar os test users

URL: https://console.cloud.google.com/auth/audience

1. Na seção **Test users**, clica **Add users**.
2. Digita o e-mail do Toneli.
3. Adiciona os e-mails dos testadores.
4. Clica **Save**.

**Confirma:** a lista **Test users** mostra os dois e-mails. Só e-mail dessa lista consegue autorizar o app.

## Passo 6 — Criar o client OAuth "Web application"

URL: https://console.cloud.google.com/auth/clients/create

1. Em **Application type**, seleciona **Web application**.
2. Em **Name**, digita `desafio-chat-web`.
3. Em **Authorized JavaScript origins**, não adiciona nada. O fluxo é server-side.
4. Em **Authorized redirect URIs**, clica **Add URI**. Cola a URI de produção:
   ```
   https://chat.toneli.dev.br/api/connectors/google/callback
   ```
5. Clica **Add URI** de novo. Cola a URI de dev:
   ```
   http://localhost:8000/api/connectors/google/callback
   ```
6. Clica **Create**.
7. Na janela do client criado, clica **Download JSON**. Guarda o arquivo fora do repo.
8. Copia o **Client ID** e o **Client secret**.

O console novo pode não mostrar o secret de novo depois de fechar a janela. **INFERIDO.** Por isso baixa o JSON no passo 7. Perdeu o secret, cria um secret novo na página do client.

**Confirma:** abre https://console.cloud.google.com/auth/clients. A lista mostra `desafio-chat-web` com tipo `Web application`. Abre o client e confere as duas redirect URIs, caractere por caractere. Diferença de barra final ou de `http`/`https` gera `redirect_uri_mismatch`.

## Passo 7 — Gravar no `.env`

1. Abre o `.env` na raiz do repo.
2. Adiciona as duas linhas com os valores do passo 6:
   ```
   GOOGLE_CLIENT_ID=<client id>.apps.googleusercontent.com
   GOOGLE_CLIENT_SECRET=<client secret>
   ```
3. Não commita o `.env`.

**Confirma:**

```bash
grep -E '^GOOGLE_CLIENT_(ID|SECRET)=' .env | cut -d= -f1
```

A saída mostra os dois nomes.

## Passo 8 — Teste de fumaça sem o app

Este passo prova o client, a redirect URI de dev, os escopos e o test user, antes do código existir.

1. Troca `<CLIENT_ID>` pelo valor real e abre a URL no navegador:
   ```
   https://accounts.google.com/o/oauth2/v2/auth?client_id=<CLIENT_ID>&redirect_uri=http://localhost:8000/api/connectors/google/callback&response_type=code&access_type=offline&prompt=consent&scope=https://www.googleapis.com/auth/gmail.readonly%20https://www.googleapis.com/auth/drive.readonly
   ```
2. Faz login com a conta do Toneli.
3. O Google mostra o aviso "Google hasn't verified this app". Esse aviso é esperado em Testing. Clica **Continue**.
4. Marca os dois acessos e clica **Continue**.

**Confirma:** o navegador vai para `http://localhost:8000/api/connectors/google/callback?code=...`. A página pode dar erro de conexão se a API não estiver rodando. O `code=` na barra de endereço prova que a configuração está certa.

Erros comuns:

| Erro | Causa |
|---|---|
| `redirect_uri_mismatch` | URI do passo 6 diferente da URL. Mudança de URI pode levar alguns minutos para valer. |
| `access_denied` / "has not completed the Google verification process" | E-mail fora da lista de test users do passo 5. |
| `invalid_client` | Client ID errado ou incompleto. |

Referência do fluxo: https://developers.google.com/identity/protocols/oauth2/web-server

---

## Limites do modo Testing

- A autorização do test user expira em 7 dias. O refresh token também. Depois disso, o usuário refaz o consentimento. Fonte: https://support.google.com/cloud/answer/15549945
- Máximo de 100 test users. Fonte: mesma URL.
- Limite de 100 refresh tokens por conta por client ID. O mais antigo é invalidado sem aviso. Fonte: https://developers.google.com/identity/protocols/oauth2
- Avaliação depois de 7 dias da conexão da demo exige novo consentimento. Grava o vídeo da demo como garantia (ADR 0010).
