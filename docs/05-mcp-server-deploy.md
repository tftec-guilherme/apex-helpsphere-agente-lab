# Capítulo 05 — MCP Server Deploy

> **Objetivo:** buildar a imagem `mcp-helpsphere:v1` via **ACR Tasks remoto**, criar **2 App Registrations** (server `app-mcp-helpsphere-server` com 3 scopes + client `app-mcp-helpsphere-client` com client secret), deployar Container App `ca-mcp-helpsphere` no `cae-helpsphere-final` com a Managed Identity `mi-helpsphere-ia` puxando do ACR, capturar o **`MCP_SERVER_URL` canônico** referenciado pelo Capítulo 04, validar via `tools/list` + `tools/call get_ticket` autenticado com Bearer token Entra OAuth, e atualizar o `.env` do `agent-code/` para destrancar as 3 tools que estavam em placeholder.
>
> **Tempo:** 90-120 min (60-75 min se `acrhelpsphere<rand>` + `cae-helpsphere-final` + `mi-helpsphere-ia` já estão prontos do Capítulo 02 — caminho normal)
>
> **Status:** `v0.2.0-portal` ⚠️ EXPANDIDO (era `v0.1.0-init` outline) — derivado de `Lab_Final_Agente_Workflow_Guia_Portal.md` Parte 4 (Passos 4.1-4.8)

---

## Pré-requisitos

- ✅ Capítulo 02 concluído — RG `rg-lab-final`, ACR `acrhelpsphere<rand>` (Basic), ACA Environment `cae-helpsphere-final`, role `AcrPull` cravado em `mi-helpsphere-ia` no scope do ACR
- ✅ Capítulo 04 concluído — agente `helpsphere-tier1-agent` criado com schema das 4 tools, `agent-code/.env` com `MCP_SERVER_URL="https://placeholder.azurecontainerapps.io"` e `MCP_TOKEN=""` aguardando preenchimento
- ✅ HelpSphere SQL connection string disponível — capturada do Bloco 2 (apex-helpsphere SaaS): Portal → `rg-lab-intermediario` → `sql-helpsphere-{rand}` → DB `helpsphere` → **Connection strings** → ADO.NET (autenticação SQL ou Entra com MI — ver Passo 5.4)
- ✅ Permissão para criar **App Registrations** no tenant Entra (role mínima `Application Developer` ou `Cloud Application Administrator`; `Global Administrator` resolve mas é overkill)
- ✅ Docker Desktop 4.30+ rodando (Capítulo 01) — usado **somente para inspeção local da imagem opcional**; o build oficial é remoto via `az acr build` (mais rápido + sem problema de WSL/proxy corporate)
- ✅ `jq` instalado para parse dos curl smoke tests (`winget install jqlang.jq` no Windows · `brew install jq` no macOS · `apt install jq` no Linux/WSL) — ou use o fallback PowerShell nativo `ConvertFrom-Json` mostrado nos smoke tests

> **Atenção breaking — `MCP_SERVER_URL` é o contrato do Capítulo 04:** o `agent_runner.py` do Cap 04 já consome `os.environ["MCP_SERVER_URL"]` com fallback para `placeholder`. O **valor canônico final** que vamos cravar aqui é `https://ca-mcp-helpsphere.<rand>.<region>.azurecontainerapps.io` (formato FQDN do ACA Consumption — Azure gera o `<rand>` automaticamente). **Não invente nome próprio** — o aluno copia da Overview do Container App no Portal (Passo 5.4).

---

## Resumo dos 5 artefatos que vamos cravar

| Artefato | Implementação | Backend / Identidade | Custo (R$/mês ligado) |
|---|---|---|---|
| Imagem `mcp-helpsphere:v1` no ACR | `az acr build` remoto (~3-5min) | Buildado no ACR `acrhelpsphere<rand>` | R$ 0 build (incluso no Basic) · ~50 MiB armazenamento (R$ 0,03/mês) |
| App Reg `app-mcp-helpsphere-server` | Portal Entra → 3 OAuth scopes (`tickets.read`, `tickets.write`, `kb.read`) + Application ID URI `api://mcp-helpsphere` | Tenant Entra (sem cobrança) | R$ 0 |
| App Reg `app-mcp-helpsphere-client` | Portal Entra → client secret 90d + admin consent das 3 permissions | Tenant Entra | R$ 0 |
| Container App `ca-mcp-helpsphere` | Portal ACA → image=`mcp-helpsphere:v1`, MI=`mi-helpsphere-ia`, ingress=External, port=8000, scale 0→1 | ACA Env `cae-helpsphere-final` (Consumption) | R$ 0 parado · ~R$ 0,02/min ativo (0,5 vCPU + 1 GiB) |
| `MCP_SERVER_URL` no `.env` do `agent-code/` | Edição manual `agent-code/.env` | Consumido pelas tools `get_ticket` + `list_similar_tickets` do Cap 04 | R$ 0 |

> **Nota pedagógica — por que 2 App Registrations e não 1?** O **server app reg** define **quem é a API protegida** (Application ID URI + scopes que ela exporta). O **client app reg** define **quem está chamando** (identidade do agente Foundry, com client secret/credentials). Em OAuth 2.0 client-credentials flow, **misturar os dois numa app só** funciona em cenários triviais mas falha quando você adiciona um 2º cliente (ex.: workflow n8n do Cap 07 também consumir o MCP) — a app teria que ser cliente de si mesma e a Microsoft bloqueia esse padrão como anti-pattern. **Em produção:** 1 App Reg server por API, N App Regs client por consumidor. **No lab Apex:** consumidor único (Foundry agent), mas mantemos a separação porque o Cap 07 vai adicionar o n8n como 2º cliente.

> **Nota pedagógica — `External` ingress vs `Internal`:** o MCP é chamado pelo `agent_runner.py` que **roda local no laptop do aluno** durante o lab, e em produção rodaria de um Function App ou outro ACA (ainda externos ao `cae-helpsphere-final`). External (ingress público com FQDN `*.azurecontainerapps.io`) resolve direto. Internal exigiria VNet integration + Private Endpoint + DNS resolver — complexidade fora do escopo do lab. **Auth segura via OAuth Bearer token mantém o External robusto** (sem token, request 401).

---

## Passo 5.1 — Estrutura do `mcp-server/` no fork local

Confira no clone local do `apex-helpsphere-agente-lab` que a pasta `mcp-server/` existe com este conteúdo (já no scaffold v0.1.0-init):

```text
mcp-server/
├── Dockerfile
├── requirements.txt
├── server.py                 # FastMCP com 4 tools
├── auth.py                   # Validação de token Entra (JWT signature + audience + scope)
├── helpsphere_db.py          # Wrapper do SQL HelpSphere (pyodbc)
└── README.md
```

`server.py` (referência — confira que bate com este conteúdo):

```python
"""
MCP Server HelpSphere — FastMCP + Entra OAuth + SQL backend.
"""
from fastmcp import FastMCP
from auth import require_scope
from helpsphere_db import HelpSphereDB
import os

mcp = FastMCP("helpsphere")
db = HelpSphereDB(os.environ["HELPSPHERE_SQL_CONNECTION"])

@mcp.tool()
@require_scope("helpsphere.tickets.read")
def get_ticket(ticket_id: int) -> dict:
    """Recupera dados completos de um ticket."""
    return db.get_ticket(ticket_id)

@mcp.tool()
@require_scope("helpsphere.tickets.read")
def list_tickets(status: str = "Open", limit: int = 10, category: str = None) -> list[dict]:
    """Lista tickets filtrando por status e opcionalmente categoria."""
    return db.list_tickets(status=status, limit=limit, category=category)

@mcp.tool()
@require_scope("helpsphere.tickets.write")
def add_comment(ticket_id: int, comment: str, author: str) -> dict:
    """Adiciona comentário a um ticket."""
    return db.add_comment(ticket_id, comment, author)

@mcp.tool()
@require_scope("helpsphere.tickets.write")
def update_status(ticket_id: int, new_status: str) -> dict:
    """Atualiza status do ticket. Status válidos: Open, InProgress, Resolved, Escalated."""
    return db.update_status(ticket_id, new_status)

if __name__ == "__main__":
    mcp.run(transport="http", host="0.0.0.0", port=8000)
```

`Dockerfile` (referência):

```dockerfile
# mcp-server/Dockerfile
FROM python:3.11-slim

# ODBC driver para pyodbc (SQL Server)
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl gnupg2 unixodbc-dev \
 && curl https://packages.microsoft.com/keys/microsoft.asc | apt-key add - \
 && curl https://packages.microsoft.com/config/debian/12/prod.list > /etc/apt/sources.list.d/mssql-release.list \
 && apt-get update \
 && ACCEPT_EULA=Y apt-get install -y msodbcsql18 \
 && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 8000
CMD ["python", "server.py"]
```

`requirements.txt`:

```text
fastmcp>=0.4.0
pyodbc>=5.1.0
PyJWT[crypto]>=2.8.0
cryptography>=42.0.0
requests>=2.31.0
```

> **Nota pedagógica — `transport="http"` em vez de `transport="stdio"`:** FastMCP tem 2 transports. `stdio` (default) é usado quando o cliente MCP roda como subprocess (ex.: Claude Desktop). `http` expõe um endpoint HTTP `/mcp` que aceita JSON-RPC POSTs — **obrigatório quando o servidor está em outro container/máquina** (nosso caso: ACA cloud). **Anti-pattern:** copiar exemplo do Anthropic Claude Desktop com stdio e tentar deployar em ACA → cliente nunca consegue conectar.

---

## Passo 5.2 — Build da imagem via ACR Tasks remoto

**No terminal local com `az` logado (Windows PowerShell 7):**

```powershell
# Garante variáveis (substitua pelo seu sufixo do Cap 02)
$AcrName = "acrhelpsphere<rand>"   # ex.: acrhelpsphere8a3f2d
$RgLab = "rg-lab-final"

# Build remoto — sobe o contexto via .tar.gz e builda no Azure
Set-Location mcp-server
az acr build `
  --registry "$AcrName" `
  --image mcp-helpsphere:v1 `
  --file Dockerfile `
  .
```

> **Linux/Mac/WSL:** substitua `$Var = "value"` por `VAR=value`, backticks (`` ` ``) por backslashes (`\`), e `Set-Location` por `cd`.

Tempo: **~3-5 min** (msodbcsql18 é a etapa mais lenta — ~90s).

Saída esperada (final):

```text
2026/05/09 14:23:45 Successfully pushed image: acrhelpsphere8a3f2d.azurecr.io/mcp-helpsphere:v1
Run ID: ca1 was successful after 4m12s
```

Validar imagem no registry:

```powershell
az acr repository list --name "$AcrName" -o table
# Esperado: linha mcp-helpsphere

az acr repository show-tags --name "$AcrName" --repository mcp-helpsphere -o table
# Esperado: tag v1
```

<!-- screenshot: cap05-passo5.2-acr-build-success.png -->

> **Alternativa via build local (NÃO recomendado, mas documentado):**
>
> ```powershell
> # Build local
> docker build -t mcp-helpsphere:v1 .
>
> # Login no ACR
> az acr login --name "$AcrName"
>
> # Tag + push
> docker tag mcp-helpsphere:v1 "$AcrName.azurecr.io/mcp-helpsphere:v1"
> docker push "$AcrName.azurecr.io/mcp-helpsphere:v1"
> ```
>
> Por que **não recomendado**: build local exige Docker Desktop rodando + WSL 2 + proxy corporate liberado para `*.docker.io` — falha em ~30% dos laptops corporate em sala de aula. ACR Tasks builda na nuvem e funciona mesmo com Docker Desktop down.

> **Custo:** ACR Tasks no tier Basic = **6.000 build-min/mês incluído** (R$ 0 para o lab). Imagem final ~50 MiB ocupa R$ 0,03/mês de storage. **Anti-pattern:** alunos pushando imagens de 2-3 GiB (Python full + base CUDA + dev tools) → estouram o cap de 10 GiB do Basic em poucos pushes.

> **Nota pedagógica — `python:3.11-slim` em vez de `python:3.11`:** slim é Debian sem ferramentas de dev (~150 MiB final image vs ~900 MiB). Para um servidor MCP que só roda HTTP + pyodbc, slim cobre. **Em produção:** considere `python:3.11-alpine` (~80 MiB) — mas atenção: alpine usa musl libc e o driver `msodbcsql18` da Microsoft só dá suporte glibc → fica em slim para SQL Server.

---

## Passo 5.3 — Criar App Registration server (`app-mcp-helpsphere-server`)

**No Portal Azure (https://portal.azure.com):**

1. Barra superior → buscar **"Microsoft Entra ID"** → clicar
2. Menu lateral → **App registrations** → **+ New registration**
3. Preencher:
   - **Name:** `app-mcp-helpsphere-server`
   - **Supported account types:** `Accounts in this organizational directory only (Single tenant)`
   - **Redirect URI:** **deixe vazio** (server-side OAuth não usa redirect)
4. Clique **Register**
5. Aguarde ~5s até abrir a página **Overview**
6. **Anote da Overview** (você vai precisar nos próximos passos):
   - **Application (client) ID** → vamos chamar de `MCP_SERVER_APP_ID`
   - **Directory (tenant) ID** → vamos chamar de `TENANT_ID`

<!-- screenshot: cap05-passo5.3-app-reg-server-overview.png -->

**Definir Application ID URI:**

1. Ainda em `app-mcp-helpsphere-server` → menu lateral **Expose an API**
2. Em **Application ID URI** clique **Add** (Portal sugere `api://{guid}`)
3. **Edite o valor sugerido** para `api://mcp-helpsphere` → **Save**
   - ⚠️ Se o tenant tiver policy bloqueando custom URIs, mantenha o `api://{guid}` default e cravar **esse GUID** no `EXPECTED_AUDIENCE` do Passo 5.4

<!-- screenshot: cap05-passo5.3-application-id-uri.png -->

**Adicionar 3 scopes:**

1. Ainda em **Expose an API** → **+ Add a scope** (você fará isso 3 vezes)
2. **Scope 1:**
   - **Scope name:** `helpsphere.tickets.read`
   - **Who can consent:** `Admins and users`
   - **Admin consent display name:** `Read tickets`
   - **Admin consent description:** `Permite ler dados de tickets do HelpSphere`
   - **User consent display name:** `Read tickets`
   - **User consent description:** `Permite que o app leia seus tickets`
   - **State:** `Enabled`
   - Clique **Add scope**
3. **Scope 2** (repita o fluxo): `helpsphere.tickets.write` — display `Write tickets`, descrição `Permite criar/editar tickets e comentários`
4. **Scope 3** (repita o fluxo): `helpsphere.kb.read` — display `Read KB`, descrição `Permite ler base de conhecimento`

<!-- screenshot: cap05-passo5.3-scopes-3-criados.png -->

> **Alternativa via Azure CLI** (parcial — scopes ainda exigem Portal · Windows PowerShell 7):
>
> ```powershell
> # Cria server app reg
> $ServerAppObjectId = az ad app create `
>   --display-name "app-mcp-helpsphere-server" `
>   --identifier-uris "api://mcp-helpsphere" `
>   --query id -o tsv
>
> $McpServerAppId = az ad app show --id "$ServerAppObjectId" --query appId -o tsv
> $TenantId = az account show --query tenantId -o tsv
>
> Write-Host "MCP_SERVER_APP_ID=$McpServerAppId"
> Write-Host "TENANT_ID=$TenantId"
> ```
>
> **Linux/Mac/WSL:** substitua `$Var = az ...` por `VAR=$(az ...)` e backticks (`` ` ``) por backslashes (`\`).
>
> ⚠️ A CLI **não tem comando direto** para `oauth2PermissionScopes` (scopes `Expose an API`). Você ainda precisa abrir Portal → **Expose an API** → adicionar os 3 scopes manualmente. (Workaround avançado: editar o **Manifest** JSON e cravar `oauth2Permissions[]` direto, mas é frágil — Portal é mais confiável.)

> **Custo:** App Registrations são **gratuitas** no Entra ID — sem cobrança por número de apps ou scopes. Cobrança aparece só com features Premium P1/P2 (Conditional Access, PIM) que **não usamos no lab**.

> **Nota pedagógica — `Who can consent: Admins and users` vs `Admins only`:** "Admins and users" permite que o flow `authorization_code` (delegate) consinta sem admin. "Admins only" força admin consent obrigatório. **No lab, escolhemos "Admins and users"** porque o flow client-credentials que usaremos no Passo 5.6 **bypassa consent de usuário** mas o Portal oferece o switch independente — manter aberto não tem downside já que **a posse do client secret** é o gate real de segurança.

---

## Passo 5.4 — Deploy do Container App `ca-mcp-helpsphere`

**No Portal Azure:**

1. Barra superior → buscar **"Container Apps"** → clicar
2. Clique **+ Create** → **Container App**
3. Preencher tab **Basics:**
   - **Subscription:** sua sub
   - **Resource group:** `rg-lab-final`
   - **Container app name:** `ca-mcp-helpsphere`
   - **Region:** `East US 2`
   - **Container Apps Environment:** `cae-helpsphere-final` (do Cap 02)
4. Tab **Container:**
   - **Use quickstart image:** `Off`
   - **Image source:** `Azure Container Registry`
   - **Registry:** selecione `acrhelpsphere<rand>` no dropdown
   - **Image:** `mcp-helpsphere`
   - **Image tag:** `v1`
   - **CPU and Memory:** `0.5 CPU cores · 1 Gi memory`
   - **Environment variables** (adicione 3):
     - `HELPSPHERE_SQL_CONNECTION` = `<connection-string-do-helpsphere-sql>` (ver nota abaixo)
     - `AZURE_TENANT_ID` = `<TENANT_ID>` capturado no Passo 5.3
     - `EXPECTED_AUDIENCE` = `api://mcp-helpsphere` (mesmo Application ID URI)
5. Tab **Ingress:**
   - **Ingress:** `Enabled`
   - **Ingress traffic:** `Accepting traffic from anywhere`
   - **Ingress type:** `HTTP`
   - **Target port:** `8000` (o `server.py` escuta nessa porta)
   - **Transport:** `Auto` (default)
6. Tab **Identity:**
   - **System assigned:** `Off`
   - **User assigned:** clique **+ Add user-assigned managed identity** → no painel direito selecione `mi-helpsphere-ia` (RG `rg-lab-intermediario`) → **Add**
   - ⚠️ Em **Registry credentials** (na própria aba **Container** acima), troque para **Use managed identity** → selecione `mi-helpsphere-ia` (essa é a MI que tem `AcrPull` cravado no Cap 02 Passo 2.4)
7. Tab **Scaling:**
   - **Min replicas:** `0` (scale-to-zero)
   - **Max replicas:** `1` (lab — em prod 3-5)
8. Tab **Tags:** herde do RG
9. Clique **Review + create** → **Create**
10. Aguarde provisioning **~2-3min** até status **Succeeded**. Banner verde no topo: `Your deployment is complete`

<!-- screenshot: cap05-passo5.4-aca-deploy-basics.png -->
<!-- screenshot: cap05-passo5.4-aca-deploy-mi-acrpull.png -->

**Capturar o `MCP_SERVER_URL` canônico:**

1. Após criar, clique **Go to resource** (ou abra o `ca-mcp-helpsphere`)
2. Em **Overview** localize **Application Url** — formato canônico:
   ```
   https://ca-mcp-helpsphere.<rand>.eastus2.azurecontainerapps.io
   ```
   (o `<rand>` é gerado pelo ACA, ex.: `politehill-1a2b3c4d`)
3. **Copie esse valor inteiro** — é o `MCP_SERVER_URL` que vai no `.env` do `agent-code/` no Passo 5.8
4. **Endpoint MCP completo:** `${MCP_SERVER_URL}/mcp` (path `/mcp` é onde o FastMCP HTTP transport escuta)

<!-- screenshot: cap05-passo5.4-application-url-anotar.png -->

> **Como obter a `HELPSPHERE_SQL_CONNECTION`:**
>
> Portal → `rg-lab-intermediario` → SQL Database `helpsphere` → menu **Connection strings** → tab **ADO.NET (SQL authentication)**. Substitua `{your_password}` pela senha do `apex-helpsphere`.
>
> ⚠️ **Em produção** use Entra Auth com MI: troque connection string para `Server=tcp:sql-helpsphere-{rand}.database.windows.net,1433;Database=helpsphere;Authentication=Active Directory Default;` e cravar role `db_datareader`+`db_datawriter` para `mi-helpsphere-ia` no banco. **No lab,** SQL auth é aceitável pelo prazo curto (24-48h) + cleanup obrigatório no Cap 09.

> **Alternativa via Azure CLI (Windows PowerShell 7):**
>
> ```powershell
> $HelpSphereSqlConn = "Server=tcp:sql-helpsphere-{rand}.database.windows.net,1433;Database=helpsphere;User Id=apexadmin;Password=<senha>;Encrypt=True;"
> $MiResourceId = az identity show -n mi-helpsphere-ia -g rg-lab-intermediario --query id -o tsv
>
> az containerapp create `
>   --name ca-mcp-helpsphere `
>   --resource-group rg-lab-final `
>   --environment cae-helpsphere-final `
>   --image "$AcrName.azurecr.io/mcp-helpsphere:v1" `
>   --target-port 8000 `
>   --ingress external `
>   --transport http `
>   --registry-server "$AcrName.azurecr.io" `
>   --registry-identity "$MiResourceId" `
>   --user-assigned "$MiResourceId" `
>   --env-vars `
>     "HELPSPHERE_SQL_CONNECTION=$HelpSphereSqlConn" `
>     "AZURE_TENANT_ID=$TenantId" `
>     "EXPECTED_AUDIENCE=api://mcp-helpsphere" `
>   --min-replicas 0 `
>   --max-replicas 1 `
>   --cpu 0.5 `
>   --memory 1Gi
>
> # Capturar o FQDN gerado
> $McpFqdn = az containerapp show `
>   --name ca-mcp-helpsphere `
>   --resource-group rg-lab-final `
>   --query "properties.configuration.ingress.fqdn" -o tsv
>
> $McpServerUrl = "https://$McpFqdn"
> Write-Host "MCP_SERVER_URL=$McpServerUrl"
> ```
>
> **Linux/Mac/WSL:** substitua `$Var = "value"` por `VAR=value`, `$Var = az ...` por `VAR=$(az ...)`, backticks por backslashes, e `Write-Host` por `echo`.

> **Custo:** ACA Consumption com 0,5 vCPU + 1 GiB cobra **~R$ 0,02/min ativo** (escalado para 1 replica) e **R$ 0 parado** (scale-to-zero após ~5min sem requests). No lab realista (smoke runs ~10min/dia × 3 dias) o custo total fica **~R$ 0,60**. ACR Basic já está no fixo de R$ 35/mês do Cap 02 — pull de imagem está incluso. **Anti-pattern:** trocar `min-replicas 0` para `1` "só por segurança" → cobrança vira ~R$ 30/mês.

> **Nota pedagógica — `--registry-identity` vs `--registry-username/password`:** com `--registry-identity` apontando para o MI que tem `AcrPull`, o ACA pula 100% credenciais armazenadas (não há senha em lugar algum — auth é via token Entra de curta duração emitido pelo MSI sidecar). Com `--registry-username/--registry-password`, o ACA armazena uma senha **ACR admin** (anti-pattern do Cap 02 — admin user disabled). **Cravar pattern MI em todos os deploys ACA cross-RG.**

> **Nota pedagógica — `Min replicas: 0` vs `1` em workload profile Consumption:** com `0`, o cold-start adiciona ~3-5s na primeira request após ociosidade (download da imagem + container start + Python boot). No lab, isso é aceitável — a tool `get_ticket` chamada pelo agente espera o cold-start sem timeout. Em **produção tier 1** com SLA <500ms p99, suba para `min=1` (aceitar custo fixo). Em **produção tier 2** com SLA <100ms, considere Dedicated workload profile + warm pool.

---

## Passo 5.5 — Criar App Registration client (`app-mcp-helpsphere-client`) + Client Secret

**No Portal Azure:**

1. Entra ID → **App registrations** → **+ New registration**
2. Preencher:
   - **Name:** `app-mcp-helpsphere-client`
   - **Supported account types:** `Accounts in this organizational directory only (Single tenant)`
   - **Redirect URI:** deixe vazio (client-credentials flow não usa)
3. **Register**
4. **Anote da Overview:**
   - **Application (client) ID** → vamos chamar de `CLIENT_APP_ID`

<!-- screenshot: cap05-passo5.5-app-reg-client-overview.png -->

**Criar Client Secret:**

1. App reg `app-mcp-helpsphere-client` → menu lateral **Certificates & secrets** → tab **Client secrets**
2. Clique **+ New client secret**
3. Preencher:
   - **Description:** `mcp-client-secret-lab`
   - **Expires:** `90 days` (suficiente para curso semestral; em produção use Federated Credentials sem secret)
4. Clique **Add**
5. ⚠️ **CRÍTICO:** copie o **Value** **AGORA, ANTES DE NAVEGAR PARA OUTRA PÁGINA** — só aparece uma vez. Vamos chamar de `CLIENT_SECRET`.
   - Se você sair da página antes de copiar, **delete e recrie o secret** — não tem como recuperar o valor

<!-- screenshot: cap05-passo5.5-client-secret-value-copy.png -->

**Adicionar API permissions (3 scopes do server):**

1. App reg `app-mcp-helpsphere-client` → menu **API permissions** → **+ Add a permission**
2. Tab **My APIs** → selecione `app-mcp-helpsphere-server`
3. Selecione **Application permissions** (não Delegated — estamos usando client-credentials sem usuário)
4. Marque os 3 scopes:
   - ✅ `helpsphere.tickets.read`
   - ✅ `helpsphere.tickets.write`
   - ✅ `helpsphere.kb.read`
5. Clique **Add permissions**
6. **Grant admin consent for <tenant>** (botão azul) → **Yes**
7. Confirme: status das 3 permissions deve virar verde **Granted for <tenant>**

<!-- screenshot: cap05-passo5.5-api-permissions-granted.png -->

> **Atenção breaking — Application permissions vs Delegated:** se você marcou **Delegated** por engano, o flow client-credentials do Passo 5.6 vai falhar com `AADSTS65001: The user or administrator has not consented to use the application`. Workaround: volte ao **API permissions**, **remove** as 3 delegated, **re-add** como Application. Re-grant admin consent.

> **Custo:** R$ 0 (App Reg + secret são gratuitos no Entra).

> **Nota pedagógica — Client secret 90d vs Federated Credentials:** secrets têm 3 problemas: (1) precisam rotação periódica, (2) podem vazar em logs/`.env`, (3) admin precisa lembrar de renovar antes do expiry. **Federated Credentials** (FIC) emitem token sem secret usando trust direto entre o IdP origem (GitHub/Azure DevOps/MI) e o Entra. **Lab Avançado D06 Cap 03** ensina FIC para CI/CD; aqui no Lab Final mantemos secret porque o consumer é um script local em laptop (sem IdP origem federável). **Em produção corporate: SEMPRE FIC, NUNCA secret de longa duração.**

---

## Passo 5.6 — Obter Bearer token client-credentials (smoke)

**No terminal local (Windows PowerShell 7):**

```powershell
$TenantId = "<TENANT_ID-do-Passo-5.3>"
$ClientAppId = "<CLIENT_APP_ID-do-Passo-5.5>"
$ClientSecret = "<CLIENT_SECRET-do-Passo-5.5>"

$TokenResponse = curl.exe -s -X POST "https://login.microsoftonline.com/$TenantId/oauth2/v2.0/token" `
  -d "grant_type=client_credentials" `
  -d "client_id=$ClientAppId" `
  -d "client_secret=$ClientSecret" `
  -d "scope=api://mcp-helpsphere/.default"

$Token = ($TokenResponse | ConvertFrom-Json).access_token

Write-Host "Token (primeiros 50 chars): $($Token.Substring(0, 50))..."
Write-Host ""

# Validar payload do token (decode base64 do middle segment)
$Segments = $Token.Split('.')
# Padding base64url para base64 standard (PowerShell exige length múltiplo de 4)
$PayloadB64 = $Segments[1].Replace('-', '+').Replace('_', '/')
switch ($PayloadB64.Length % 4) { 2 { $PayloadB64 += '==' } 3 { $PayloadB64 += '=' } }
$Payload = [Text.Encoding]::UTF8.GetString([Convert]::FromBase64String($PayloadB64))
$Payload | ConvertFrom-Json | Select-Object aud, iss, roles
```

> **Nota:** `jq` requer instalação no Windows. Instale via `winget install jqlang.jq` ou use o fallback PowerShell nativo `ConvertFrom-Json` (já aplicado acima).

Saída esperada (objeto com `aud`, `iss`, `roles`):

```text
aud   : api://mcp-helpsphere
iss   : https://sts.windows.net/<TENANT_ID>/
roles : {helpsphere.tickets.read, helpsphere.tickets.write, helpsphere.kb.read}
```

> **Atenção troubleshooting:** se o token vier `null` ou se aparecer `AADSTS7000215: Invalid client secret`, **a causa é 99% das vezes copy-paste com espaço final** ou secret expirado. Workaround: regenere o secret no Passo 5.5 e copie com cuidado (Portal coloca um botão de copy direto — use ele). Se vier `AADSTS500011: The resource principal named api://mcp-helpsphere was not found`, falta admin consent → Passo 5.5 último item.

> **Nota pedagógica — `roles` vs `scp` no payload do token:** Application permissions emitem o claim `roles` (array). Delegated permissions emitem `scp` (string). O middleware `auth.py` do `server.py` precisa **olhar para o claim certo** — confira que ele faz `if "roles" in payload` para o caso `client_credentials`. Anti-pattern: middleware que só olha `scp` e silenciosamente nega tudo em fluxo client-credentials.

---

## Passo 5.7 — Smoke test do MCP Server (cURL `tools/list` + `tools/call`)

**No terminal local (token já capturado no Passo 5.6):**

**Smoke 1 — listar tools (Windows PowerShell 7):**

```powershell
$McpServerUrl = "https://ca-mcp-helpsphere.<rand>.eastus2.azurecontainerapps.io"

$Body = @{
  jsonrpc = "2.0"
  method  = "tools/list"
  id      = 1
} | ConvertTo-Json -Compress

$Response = curl.exe -sS -X POST "$McpServerUrl/mcp" `
  -H "Authorization: Bearer $Token" `
  -H "Content-Type: application/json" `
  -d $Body

# Parse via PowerShell nativo (sem dependência de jq):
($Response | ConvertFrom-Json).result.tools | ForEach-Object { $_.name }

# Alternativa com jq (se instalado via `winget install jqlang.jq`):
# $Response | jq '.result.tools[].name'
```

> **Nota:** `jq` requer instalação no Windows. Instale via `winget install jqlang.jq` ou use o fallback PowerShell nativo `ConvertFrom-Json` (aplicado acima).

Saída esperada:

```text
"get_ticket"
"list_tickets"
"add_comment"
"update_status"
```

**Smoke 2 — chamar `get_ticket`:**

```powershell
$CallBody = @{
  jsonrpc = "2.0"
  method  = "tools/call"
  params  = @{
    name      = "get_ticket"
    arguments = @{ ticket_id = 1 }
  }
  id      = 2
} | ConvertTo-Json -Compress -Depth 5

$CallResponse = curl.exe -sS -X POST "$McpServerUrl/mcp" `
  -H "Authorization: Bearer $Token" `
  -H "Content-Type: application/json" `
  -d $CallBody

($CallResponse | ConvertFrom-Json).result
```

Saída esperada (depende do seed do HelpSphere SQL):

```json
{
  "ticket_id": 1,
  "title": "Pedido 84512 não entregue",
  "status": "Open",
  "category": "logistics",
  "priority": "high",
  "created_at": "2026-04-15T09:23:11Z"
}
```

**Smoke 3 — confirmar negação sem token (auth ativa):**

```powershell
$HttpCode = curl.exe -sS -w "%{http_code}" -o $null -X POST "$McpServerUrl/mcp" `
  -H "Content-Type: application/json" `
  -d '{"jsonrpc":"2.0","method":"tools/list","id":1}'
Write-Host $HttpCode
# Esperado: 401
```

<!-- screenshot: cap05-passo5.7-curl-tools-list-success.png -->

> **Custo:** smoke = R$ 0 (3 requests HTTP em ACA Consumption já provisionado, ~5s totais ativos · ~R$ 0,002).

> **Nota pedagógica — JSON-RPC 2.0 vs REST puro:** MCP usa **JSON-RPC 2.0 sobre HTTP POST** (single endpoint `/mcp`, payload com `method` + `params` + `id`). Diferente de REST (múltiplos endpoints com path semântico), JSON-RPC vira commodities os tools — **adicionar uma 5ª tool no `server.py` não exige novo endpoint**, só decorator `@mcp.tool()`. Trade-off: menos descoberta REST-friendly (menos auto-doc tipo OpenAPI). **Por que MCP escolheu JSON-RPC:** alinhamento com LSP (Language Server Protocol) e padrão preexistente no ecossistema dev tools.

---

## Passo 5.8 — Atualizar `agent-code/.env` com `MCP_SERVER_URL` real

**No VS Code (clone local):**

Abra `agent-code/.env` e edite as 2 linhas que estavam em placeholder:

```dotenv
# ANTES (Passo 4.4):
MCP_SERVER_URL="https://placeholder.azurecontainerapps.io"
MCP_TOKEN=""

# DEPOIS (cravando os valores reais dos Passos 5.4 + 5.6):
MCP_SERVER_URL="https://ca-mcp-helpsphere.<rand>.eastus2.azurecontainerapps.io"
MCP_TOKEN="<TOKEN-capturado-no-Passo-5.6>"
```

**Re-rodar o smoke do agente do Cap 04 (`agent_runner.py`) — Windows PowerShell 7:**

```powershell
Set-Location agent-code
python agent_runner.py
```

> **Linux/Mac/WSL:** `cd agent-code && python agent_runner.py`

Agora o agente deve **conseguir chamar `get_ticket` via MCP** — observe o stdout:

```text
Thread: thread_xxxxxxx

  [tool] search_kb({'query': '...'})
  [tool] get_ticket({'ticket_id': 84512})

=== Response ===
O ticket 84512 (Pedido 84512 não entregue) está com status Open na categoria logistics.
Para reembolso após 7 dias sem entrega, siga estes passos:
1. ...
[Manual de Reembolsos, seção 3.2] [Ticket #84512 - dados via MCP]
```

> **Atenção breaking — `MCP_TOKEN` expira em 1h:** o token client-credentials do Passo 5.6 vence em **3600s**. Para o smoke do lab é OK (tudo roda em <30min). Para uso prolongado, **adicione lógica de refresh** no `agent_runner.py`: capturar `expires_in` do response do token endpoint e re-chamar antes do TTL acabar. Lab Avançado D06 Cap 06 ensina pattern com `azure-identity ClientSecretCredential` que faz refresh automático.

> **Nota pedagógica — por que cravar `MCP_TOKEN` no `.env` em vez do agente buscar token sozinho?** Por simplicidade pedagógica: separar **smoke do MCP (Cap 05)** de **integração SDK (Cap 06+)**. **Em produção:** o `agent_runner.py` deve receber `(TENANT_ID, CLIENT_APP_ID, CLIENT_SECRET)` e usar `ClientSecretCredential` do SDK que faz fetch + cache + refresh automático — nunca um token estático no `.env`.

---

## Validação end-to-end

```powershell
# 1. Imagem no ACR
az acr repository show-tags --name $AcrName --repository mcp-helpsphere -o tsv
# Esperado: v1

# 2. Container App rodando
az containerapp show --name ca-mcp-helpsphere --resource-group rg-lab-final `
  --query "{name:name, fqdn:properties.configuration.ingress.fqdn, state:properties.runningStatus, mi:identity.userAssignedIdentities}" -o table
# Esperado: state=Running, fqdn populado, mi com mi-helpsphere-ia

# 3. Health do MCP via curl (sem auth — espera 401, confirma que auth ativa)
curl.exe -sS -w "%{http_code}" -o $null "https://$MCP_FQDN/mcp" `
  -X POST -H "Content-Type: application/json" -d '{}'
# Esperado: 401

# 4. tools/list autenticado
$ValidationResp = curl.exe -sS -X POST "https://$MCP_FQDN/mcp" `
  -H "Authorization: Bearer $Token" `
  -H "Content-Type: application/json" `
  -d '{"jsonrpc":"2.0","method":"tools/list","id":1}'
($ValidationResp | ConvertFrom-Json).result.tools.Count
# Esperado: 4

# 5. Re-smoke do agente Cap 04 com MCP real
cd agent-code; python agent_runner.py | Select-String '\[tool\] get_ticket'
# Esperado: 1+ linhas com [tool] get_ticket(...)

# 6. App Regs criadas
az ad app list --filter "startswith(displayName,'app-mcp-helpsphere')" --query "[].{name:displayName, appId:appId}" -o table
# Esperado: 2 linhas (server + client)
```

---

## Checklist final

```text
[ ] Imagem mcp-helpsphere:v1 buildada via az acr build e visível em az acr repository show-tags
[ ] App Reg app-mcp-helpsphere-server criada com Application ID URI api://mcp-helpsphere
[ ] 3 scopes (tickets.read, tickets.write, kb.read) cravados em Expose an API
[ ] App Reg app-mcp-helpsphere-client criada com Client Secret 90d (Value copiado)
[ ] API permissions Application × 3 + admin consent granted (tudo verde)
[ ] Container App ca-mcp-helpsphere rodando em cae-helpsphere-final (state=Running)
[ ] User-assigned MI mi-helpsphere-ia atribuída ao Container App + usada como registry-identity
[ ] Application Url canônico capturado (formato https://ca-mcp-helpsphere.<rand>.<region>.azurecontainerapps.io)
[ ] Smoke curl tools/list retorna 4 tools com Bearer token válido
[ ] Smoke curl get_ticket {ticket_id:1} retorna dados do seed HelpSphere
[ ] Curl sem token retorna 401 (auth Entra confirmada ativa)
[ ] agent-code/.env atualizado com MCP_SERVER_URL real + MCP_TOKEN válido
[ ] python agent_runner.py do Cap 04 mostra [tool] get_ticket sendo chamado com sucesso
```

---

## Surpresas pedagógicas (capturadas em smoke runs)

- ⚠️ **`az acr build` falha com `unauthorized: authentication required` em sub corporate** — causa: tenant-policy bloqueando a Service Connection que o ACR Tasks cria temporariamente. Workaround: pedir ao tenant-admin para liberar `Microsoft.ContainerRegistry/registries/tasks/scheduledRuns/action` na sub OU fallback para build local + `docker push` (Passo 5.2 alternativa).
- ⚠️ **`api://mcp-helpsphere` rejeitado pelo Portal com `Identifier URI is not a valid URI`** — causa: tenant tem policy de **Application Identifier URI** exigindo `api://{guid}` (não custom name). Workaround: aceitar o `api://{guid}` sugerido e cravar **esse GUID** como `EXPECTED_AUDIENCE` no env var do Container App. Atualizar também `scope=api://{guid}/.default` no Passo 5.6.
- ⚠️ **`tools/list` retorna 200 mas `tools` vazio** — causa: `EXPECTED_AUDIENCE` no env do Container App não bate com o `aud` claim do token (typo de `api://mcp-helpsphere` vs `api://mcp-helpsphere/`). O `auth.py` rejeita silenciosamente e retorna lista vazia. Workaround: comparar `jq '.aud'` do payload do token (Passo 5.6) com `az containerapp show --query "properties.template.containers[0].env"` — devem ser **idênticos byte-a-byte** (sem trailing slash).
- ⚠️ **Container App em `Provisioning` infinito (>10min)** — causa típica: imagem do ACR não pulla porque o `--registry-identity` foi setado mas o role `AcrPull` não propagou ainda (Cap 02 Passo 2.4). Sintoma: `az containerapp logs show` mostra `failed to authenticate to registry`. Workaround: aguardar 60s após criar o `AcrPull` no Cap 02; se passou de 5min ainda falhando, deletar o Container App, esperar mais 60s e re-criar.
- ⚠️ **`AADSTS500011: The resource principal named api://mcp-helpsphere was not found`** ao pegar token — causa: server App Reg foi criada mas **Application ID URI não foi salvo** (botão Save em Expose an API esquecido). Workaround: voltar ao Passo 5.3 → **Expose an API** → confirmar que `api://mcp-helpsphere` aparece no topo (não vazio).
- ⚠️ **Application permissions exigem admin consent — User pode marcar mas não conceder** — em tenants com restrições, "Grant admin consent" fica cinza para usuários sem `Cloud Application Administrator`. Workaround: peça ao tenant-admin para abrir a página `app-mcp-helpsphere-client` → API permissions → clicar Grant admin consent. Sem esse step, token sai mas `roles` vem vazio → 403 no MCP.
- ⚠️ **Cold-start do ACA scale-to-zero adiciona 3-5s na primeira request após ~5min ociosidade** — não é bug, é expected behavior do Consumption profile. Sintoma: smoke depois de pausa demorada parece "travado" 3s antes de responder. Workaround se latência é crítica: subir `min-replicas=1` (custo ~R$ 30/mês fixo) OU manter heartbeat (cron chamando `tools/list` a cada 4min — anti-pattern).
- ⚠️ **`PyJWT` valida assinatura mas `audience` precisa ser passado explicitamente** — anti-pattern comum no `auth.py`: `jwt.decode(token, key, algorithms=["RS256"])` sem `audience=` → aceita **qualquer audience**, vetor crítico de impersonation. Workaround: cravar `jwt.decode(token, key, algorithms=["RS256"], audience=os.environ["EXPECTED_AUDIENCE"])`. Verificar `auth.py` do scaffold tem essa linha antes de deployar em prod.

---

## Troubleshooting rápido

| Sintoma | Causa provável | Fix |
|---|---|---|
| `az acr build` trava em "Queued" >5min | Quota regional ACR Tasks esgotada (raro) | Trocar região do ACR no Cap 02 OU aguardar 10min |
| `401 Unauthorized` no curl com Bearer válido | `EXPECTED_AUDIENCE` env != `aud` do token | Comparar exato (com/sem trailing slash) |
| `403 Forbidden` no curl com 200 OK em `tools/list` | Falta `roles` no token (admin consent) | Passo 5.5 último item — Grant admin consent |
| `pyodbc.OperationalError: Login failed` nos logs | `HELPSPHERE_SQL_CONNECTION` malformada ou IP do ACA bloqueado no SQL firewall | Add regra `0.0.0.0/0` temporária no SQL OU configurar VNet |
| `MCP_TOKEN` vence durante demo da aula | TTL 1h client-credentials | Re-rodar Passo 5.6, atualizar `.env`, re-rodar smoke |
| `Cannot find image acrhelpsphere<rand>.azurecr.io/mcp-helpsphere:v1` | MI sem `AcrPull` propagado ainda | Aguardar 60s após Cap 02 Passo 2.4; `az role assignment list --assignee <principalId>` confirma |
| Container App `Failed` com `Internal Server Error` na primeira request | `requirements.txt` faltou `cryptography` (PyJWT signature) | Re-build (`az acr build`) com `cryptography>=42.0.0` adicionado |

---

## Próximo capítulo

[06 — Speech (STT/TTS)](./06-speech-stt-tts.md)
