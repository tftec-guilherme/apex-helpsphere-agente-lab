# Capítulo 07 — n8n Escalation

> **Objetivo:** provisionar **PostgreSQL Flexible Server Burstable B1ms** (backend de metadata do n8n) no RG `rg-lab-final`, deployar **n8n** como Container App `ca-n8n-helpsphere` no `cae-helpsphere-final` (imagem `n8nio/n8n:1.6` pinada — não `:latest`), atribuir **Azure Service Bus Data Receiver** à Managed Identity `mi-helpsphere-ia` referenciando o Topic `tickets-escalated` que o **Capítulo 08** vai criar, completar o **owner setup wizard** do n8n, importar o workflow `escalation-servicebus-sheets.json` deste repo, deixar credentials parcialmente configuradas (PostgreSQL HelpSphere + HTTP Header Auth — o resto fica para o Cap 08) e **pausar o ambiente** ao fim para zerar custo recorrente.
>
> **Tempo:** 60-90 min (45-60 min se PostgreSQL Burstable já provisionado de uma sessão anterior — caminho normal "retomei o lab no dia seguinte")
>
> **Status:** `v0.2.0-portal` ⚠️ EXPANDIDO (era `v0.1.0-init` outline) — derivado de `Lab_Final_Agente_Workflow_Guia_Portal.md` Parte 6 (Passos 6.1-6.7)

---

## Pré-requisitos

- ✅ Capítulo 02 concluído — RG `rg-lab-final` existe, ACA Environment `cae-helpsphere-final` provisionado, Managed Identity `mi-helpsphere-ia` (cross-RG em `rg-helpsphere-ia`) já com role `AcrPull`
- ✅ Capítulo 04 concluído — agente `helpsphere-tier1-agent` existe e tem schema da tool `escalate_ticket` registrada (mas ainda em placeholder até Cap 08)
- ✅ Capítulo 05 concluído — MCP Server `ca-mcp-helpsphere` rodando; o workflow do n8n vai chamá-lo em alguns nodes para enriquecer dados de ticket
- ✅ HelpSphere SQL connection string disponível (do Bloco 2) — o workflow precisa consultar tickets resolvidos similares
- ✅ `openssl` disponível localmente (Git Bash, WSL ou macOS) — vamos gerar `N8N_ENCRYPTION_KEY` aleatória de 32 bytes base64
- ✅ Permissão para criar role assignments na sub (Owner ou User Access Administrator) — necessária no Passo 7.4

> [!IMPORTANT] **Tier / Licenciamento — custo recorrente**
> Este capítulo introduz o maior custo fixo do Lab Final (PostgreSQL B1ms ~R$ 60/mês ligado 24×7). Decisão consolidada em [`_disclaimers.md`](./_disclaimers.md) **AMB-3** (cleanup obrigatório). Use uma das duas estratégias do Passo 7.7 obrigatoriamente ao fim de cada sessão.

> **Atenção breaking — referência cruzada com Cap 08:** este capítulo cria o n8n e importa o workflow, mas o **Service Bus Topic `tickets-escalated` ainda não existe** quando você chega aqui. Vamos cravar a credential do Service Bus em modo "rascunho" no Passo 7.6 e a credential **só fica funcional após o Cap 08** terminar de criar o Topic + Subscription. Isso é proposital — separar o setup do n8n (infraestrutura pesada) da modelagem do mensageria (lógica de domínio) replica o pattern Microsoft de **infrastructure-first, integrations-last**.

---

## Resumo dos 5 artefatos que vamos cravar

| Artefato | Implementação | Backend / Identidade | Custo (R$/mês ligado) |
|---|---|---|---|
| PostgreSQL Flexible Server `pg-n8n-<rand>` | Portal Azure → DB for PostgreSQL flexible servers · **Burstable B1ms** · 32 GiB · PG auth only | Database `n8n` consumido pelo container n8n via env vars | **R$ 60 fixo ligado 24×7** · R$ 0 se `Stop` |
| Container App `ca-n8n-helpsphere` | Portal ACA → image=`n8nio/n8n:1.6` (pinned), env vars apontando ao PG, ingress=External, port=5678, scale 1→1 | ACA Env `cae-helpsphere-final` (Consumption) | R$ 0 parado · ~R$ 0,02/min ativo (0,5 vCPU + 1 GiB) — **mas `min-replicas 1` mantém ativo** |
| Role `Azure Service Bus Data Receiver` em `mi-helpsphere-ia` | Portal Service Bus (Cap 08) → IAM → Add role assignment · escopo: namespace `sb-helpsphere-final` | Managed Identity já existente em `rg-helpsphere-ia` | R$ 0 (RBAC gratuito) |
| Workflow `Ticket Escalation` importado no n8n | n8n UI → Workflows → Import from file → `n8n-workflows/escalation-servicebus-sheets.json` deste repo | Stored em PostgreSQL `n8n` database | R$ 0 (incluso PG) |
| `N8N_URL` capturada e webhook configurado | Portal ACA Overview + Application → Containers → Environment variables (`WEBHOOK_URL`) | FQDN ACA público `*.azurecontainerapps.io` | R$ 0 |

> **Nota pedagógica — por que PostgreSQL Flexible Server e não SQLite default do n8n?** A imagem `n8nio/n8n:latest` por padrão usa SQLite local no filesystem do container — perfeito em laptop dev, **falha catastroficamente no ACA**: cada restart do container (deploy, scale, manutenção da plataforma) **perde todo o estado** (workflows, credentials, executions). Em Container Apps, o filesystem é efêmero por design. PostgreSQL externo é o único caminho para n8n produzir resultado pedagogicamente válido neste lab — o aluno precisa sair com workflows persistidos. **Em produção:** mesma arquitetura. **Alternativa premium:** Azure Database for PostgreSQL com HA zona-redundante (~R$ 600/mês) — overkill para o lab.

> **Nota pedagógica — Burstable B1ms vs General Purpose D2s_v3:** B1ms (1 vCore burstable + 2 GiB RAM) entrega ~R$ 60/mês e suporta até 30 baseline credits/h — mais que suficiente para n8n metadata + 5-10 workflows ativos do lab. General Purpose D2s_v3 (2 vCores dedicados + 8 GiB) custa ~R$ 350/mês e só faz sentido em produção com ≥100 workflows concorrentes. Para o lab e produção pequena (single-tenant, ≤20 workflows): Burstable B1ms é canônico. Cleanup obrigatório em [`_disclaimers.md`](./_disclaimers.md) **AMB-3**.

> **Nota pedagógica — `min-replicas 1` quebra o scale-to-zero do ACA:** ACA Consumption normalmente é gratuito parado por causa do `min-replicas 0`. Aqui forçamos `1` porque n8n recebe **webhooks externos** (Service Bus polling + HTTP triggers de Adaptive Cards no Teams) — se o container dorme, mensagens enfileiram no Service Bus mas o **trigger node do n8n não desperta o container** (n8n não usa KEDA-aware patterns). Em produção real: implementar **KEDA Service Bus scaler** com min-replicas 0 e trigger por queue length. Para o lab, `min-replicas 1` mantém o n8n acordado durante a sessão e evita "por que minhas escalações não disparam?"

---

## Passo 7.1 — Provisionar PostgreSQL Flexible Server Burstable

**No Portal Azure:**

1. Abra `https://portal.azure.com` → confirme que está na sub correta (canto superior direito)
2. Barra superior → buscar **"Azure Database for PostgreSQL flexible servers"** → clicar no resultado
3. Clique **+ Create** → escolha **Flexible server**
4. Preencher tab **Basics**:
   - **Subscription:** sua sub
   - **Resource group:** `rg-lab-final` (mesmo do Cap 02)
   - **Server name:** `pg-n8n-<rand>` (ex.: `pg-n8n-8a3f2d` — globalmente único, lowercase, sem hífen no final). Use o mesmo `<rand>` do ACR `acrhelpsphere<rand>` para rastreabilidade.
   - **Region:** `East US 2` (alinhado com `cae-helpsphere-final`)
   - **PostgreSQL version:** `16`
   - **Workload type:** `Development` (preset Burstable)
   - **Compute + storage:** clique **Configure server** → **Burstable** → **Standard_B1ms (1 vCore, 2 GiB RAM)** → **Storage size:** `32 GiB` → **Save**
   - **Authentication method:** `PostgreSQL authentication only` (sem Entra — mais simples para o lab; produção real: Entra-only)
   - **Admin username:** `n8nadmin`
   - **Password:** gere senha forte ≥16 chars (letras + números + símbolos). **Anote em editor seguro** — não dá pra recuperar depois.
5. Tab **Networking**:
   - **Connectivity method:** `Public access (allowed IP addresses)`
   - **Allow public access from any Azure service within Azure to this server:** ✅ **Yes** (necessário para o ACA n8n alcançar o PG sem VNet integration)
   - **Add current client IP address:** ✅ Yes (para você conectar via `psql` local nos smoke tests, opcional)
6. **Review + create** → **Create**
7. Aguarde provisioning **~5-7min** até banner verde **Succeeded**

<!-- screenshot: cap07-passo7.1-criar-postgres-burstable.png -->

**Criar database `n8n` dentro do servidor:**

1. Recurso `pg-n8n-<rand>` → menu lateral → **Settings** → **Databases** → **+ Add**
2. **Name:** `n8n` → **Save**
3. Aguarde ~5s até aparecer na lista

<!-- screenshot: cap07-passo7.1-criar-database-n8n.png -->

**Anote em editor seguro (vai usar no Passo 7.2):**

- `PG_HOST` = `pg-n8n-<rand>.postgres.database.azure.com` (página Overview do server, campo **Server name**)
- `PG_USER` = `n8nadmin`
- `PG_PASSWORD` = senha que você definiu

> **Alternativa via Azure CLI:**
>
> ```bash
> RAND=8a3f2d  # use o mesmo <rand> do ACR do Cap 02
> PG_NAME="pg-n8n-${RAND}"
> PG_PASSWORD=$(openssl rand -base64 16 | tr -d '/+=' | head -c 20)Aa1!  # 20+ chars seguros
>
> az postgres flexible-server create \
>   --name "$PG_NAME" \
>   --resource-group rg-lab-final \
>   --location eastus2 \
>   --admin-user n8nadmin \
>   --admin-password "$PG_PASSWORD" \
>   --sku-name Standard_B1ms \
>   --tier Burstable \
>   --storage-size 32 \
>   --version 16 \
>   --public-access 0.0.0.0  # demo only — em prod, VNet
>
> az postgres flexible-server db create \
>   --resource-group rg-lab-final \
>   --server-name "$PG_NAME" \
>   --database-name n8n
>
> PG_HOST="${PG_NAME}.postgres.database.azure.com"
> echo "PG_HOST=$PG_HOST"
> echo "PG_PASSWORD=$PG_PASSWORD"  # anote!
> ```

> **Custo:** PostgreSQL B1ms cobra R$ 60/mês ligado 24×7. No lab realista (provisiona+pause/delete no fim do dia), R$ 2-3 por sessão de 8h. `Stop` zera compute, mas storage 32 GiB cobra R$ 5/mês mesmo parado (idle storage) — único jeito de zerar 100% é `delete`. Detalhes da decisão em [`_disclaimers.md`](./_disclaimers.md) **AMB-3**.

> **Nota pedagógica — Public access "any Azure service" é seguro neste lab?** Não em produção. Em produção real, use **Private access (VNet)** com integração ao subnet do ACA Environment. Aqui no lab fazemos public porque (1) a VNet do ACA `cae-helpsphere-final` foi criada gerenciada (sem subnets manuais expostas), (2) Workload Profile Consumption não suporta VNet custom sem migrar para Dedicated. **A senha forte + Allow only Azure services + Firewall só com seu IP** é defesa em camada suficiente para o lab. **Cap do Lab Avançado** mostra a versão production-grade com Private Endpoint.

---

## Passo 7.2 — Deploy n8n no ACA `cae-helpsphere-final`

**No Portal Azure:**

1. Barra superior → buscar **"Container Apps"** → clicar
2. **+ Create** → **Container App**
3. Preencher tab **Basics**:
   - **Subscription:** sua sub
   - **Resource group:** `rg-lab-final`
   - **Container app name:** `ca-n8n-helpsphere`
   - **Region:** `East US 2`
   - **Container Apps Environment:** `cae-helpsphere-final` (criado no Cap 02 — é o mesmo do `ca-mcp-helpsphere`)
4. Tab **Container**:
   - **Use quickstart image:** `Off`
   - **Image source:** `Docker Hub or other registries`
   - **Image type:** `Public`
   - **Registry login server:** `docker.io`
   - **Image and tag:** `n8nio/n8n:1.6` ⚠️ **NÃO use `:latest`** (ver Surpresa pedagógica abaixo + ver Cap 10 troubleshooting #4)
   - **CPU and Memory:** `0.5 CPU / 1 Gi memory`
   - Seção **Environment variables** → clique **+ Add** para cada uma:
     - `DB_TYPE` = `postgresdb`
     - `DB_POSTGRESDB_HOST` = `<PG_HOST do Passo 7.1>`
     - `DB_POSTGRESDB_DATABASE` = `n8n`
     - `DB_POSTGRESDB_USER` = `n8nadmin`
     - `DB_POSTGRESDB_PASSWORD` = `<PG_PASSWORD>` ⚠️ **marque como Secret reference** (não plain text — clique no link "Secret reference" e crie secret `pg-password`)
     - `DB_POSTGRESDB_SSL_CA` = (deixe vazio — PG Flexible Server usa CA pública confiável pelo container)
     - `N8N_ENCRYPTION_KEY` = gere localmente: `openssl rand -base64 32` → cole o resultado ⚠️ **marque como Secret reference** `n8n-encryption-key`
     - `N8N_HOST` = `0.0.0.0`
     - `N8N_PROTOCOL` = `https`
     - `WEBHOOK_URL` = (deixe vazio por enquanto — atualizamos no fim deste Passo)
     - `GENERIC_TIMEZONE` = `America/Sao_Paulo`
5. Tab **Ingress**:
   - **Ingress:** `Enabled`
   - **Ingress traffic:** `Accepting traffic from anywhere`
   - **Target port:** `5678`
6. Tab **Scaling**:
   - **Min replicas:** `1` (NÃO use `0` — ver nota pedagógica no Resumo desta página)
   - **Max replicas:** `1` (single-instance — n8n não suporta multi-instance sem queue mode + Redis)
7. **Review + create** → **Create**
8. Aguarde provisioning **~3-5min** até **Succeeded**

<!-- screenshot: cap07-passo7.2-deploy-n8n-aca.png -->

**Após criado, capturar URL e fechar o ciclo do `WEBHOOK_URL`:**

1. Container app `ca-n8n-helpsphere` → **Overview** → copie o valor de **Application Url** (formato `https://ca-n8n-helpsphere.<rand>.eastus2.azurecontainerapps.io`) — vamos chamar de `N8N_URL`
2. Menu lateral → **Application** → **Containers** → tab **Environment variables** → localize `WEBHOOK_URL` → **Edit** → setar valor para `https://<N8N_URL>/` (com a barra final, importante!)
3. Clique **Save** → na confirmação **Create new revision** → **Create**
4. Container faz restart automático ~30s — aguarde até voltar a status **Running** na aba **Revision and replicas**

<!-- screenshot: cap07-passo7.2-update-webhook-url.png -->

> **Alternativa via Azure CLI:**
>
> ```bash
> ENC_KEY=$(openssl rand -base64 32)
>
> az containerapp create \
>   --name ca-n8n-helpsphere \
>   --resource-group rg-lab-final \
>   --environment cae-helpsphere-final \
>   --image n8nio/n8n:1.6 \
>   --target-port 5678 \
>   --ingress external \
>   --secrets pg-password="$PG_PASSWORD" n8n-encryption-key="$ENC_KEY" \
>   --env-vars \
>     DB_TYPE=postgresdb \
>     DB_POSTGRESDB_HOST="$PG_HOST" \
>     DB_POSTGRESDB_DATABASE=n8n \
>     DB_POSTGRESDB_USER=n8nadmin \
>     DB_POSTGRESDB_PASSWORD=secretref:pg-password \
>     DB_POSTGRESDB_SSL_CA="" \
>     N8N_ENCRYPTION_KEY=secretref:n8n-encryption-key \
>     N8N_HOST="0.0.0.0" \
>     N8N_PROTOCOL=https \
>     WEBHOOK_URL="" \
>     GENERIC_TIMEZONE="America/Sao_Paulo" \
>   --min-replicas 1 \
>   --max-replicas 1 \
>   --cpu 0.5 \
>   --memory 1Gi
>
> N8N_FQDN=$(az containerapp show \
>   --name ca-n8n-helpsphere \
>   --resource-group rg-lab-final \
>   --query "properties.configuration.ingress.fqdn" -o tsv)
>
> az containerapp update \
>   --name ca-n8n-helpsphere \
>   --resource-group rg-lab-final \
>   --set-env-vars WEBHOOK_URL="https://${N8N_FQDN}/"
>
> echo "N8N_URL=https://${N8N_FQDN}"
> ```

> **Custo:** ACA n8n com `min-replicas 1` cobra ~R$ 80/mês ligado (não faz scale-to-zero). No lab, ~R$ 0,02/min × 8h sessão = ~R$ 10/dia. **Ao parar o PG no fim do dia, o n8n quebra (DB indisponível) — então pause AMBOS juntos** (Passo 7.7).

> **Nota pedagógica — `N8N_ENCRYPTION_KEY` é o ponto único de falha:** essa chave criptografa todas as credentials armazenadas no PostgreSQL (Service Bus connection string, Google OAuth tokens, HelpSphere API key, etc.). **Perdê-la** = todas as credentials no DB ficam ilegíveis e o aluno tem que recriar tudo. **Trocá-la** com credentials já gravadas = mesmas credentials viram lixo cifrado. Por isso usamos Secret reference do ACA (gerenciado pela plataforma, sobrevive a restarts e revisions). Em produção real: armazene a chave também em **Azure Key Vault** com `keyvaultRef` para evitar dependência única do ACA secrets store.

---

## Passo 7.3 — Owner setup wizard do n8n

**No navegador:**

1. Abra `https://<N8N_URL>` (a Application Url do Passo 7.2)
2. Primeira tela carrega o **Owner Setup** — preencha:
   - **Email:** seu email do curso (vai ser o admin do n8n — não pode trocar facilmente depois)
   - **First name / Last name:** nome real
   - **Password:** senha forte ≥8 chars (n8n exige, sem 2FA neste lab)
3. Clique **Next**
4. Tela 2 (Survey opcional sobre uso) → **Skip** (canto inferior direito)
5. Tela 3 (Activate license / free plan) → **Skip** ou **Send me a free license** se quiser as features gratuitas extras (ex.: log to file). Free license é OK para o lab.
6. Você cai no dashboard `Workflows` vazio

<!-- screenshot: cap07-passo7.3-n8n-owner-setup.png -->

> **Custo:** R$ 0 — n8n self-hosted é open source AGPL v3, sem cobrança da Plataforma do n8n.

> **Nota pedagógica — owner setup só funciona uma vez:** se você esquecer a senha do owner, a única recuperação documentada é (a) deletar a tabela `n8n_users` direto no PostgreSQL via `psql`, (b) restartar o container, (c) refazer o setup. Em produção, integre **n8n com SAML SSO** (feature paga) ou pelo menos **n8n External User Auth** via webhook. No lab, anote a senha e siga em frente.

---

## Passo 7.4 — Atribuir RBAC `Azure Service Bus Data Receiver` à `mi-helpsphere-ia`

⚠️ **Heads-up cross-cap:** este Passo **referencia o namespace `sb-helpsphere-final` que ainda não existe** — ele será criado no **Capítulo 08, Passo 8.1**. Você tem **2 opções**:

- **Opção A (recomendada — segue ordem do guia):** **PULE este Passo 7.4 agora**, vá direto ao Passo 7.5 (Importar workflow). Volte aqui **depois do Cap 08 Passo 8.1** para fechar a role assignment. Cravamos um TODO no checklist final.
- **Opção B (se você já fez o Cap 08 antes — rara):** execute agora normalmente.

**Quando voltar (após Cap 08 Passo 8.1) — No Portal Azure:**

1. Barra superior → buscar **"Service Bus"** → clicar no namespace `sb-helpsphere-final`
2. Menu lateral → **Access control (IAM)** → **+ Add** → **Add role assignment**
3. Tab **Role**:
   - Categoria: **Job function roles**
   - Procurar: `Azure Service Bus Data Receiver`
   - Selecionar → **Next**
4. Tab **Members**:
   - **Assign access to:** `Managed identity`
   - **+ Select members** → **Subscription:** sua → **Managed identity:** `User-assigned managed identity` → escolher **`mi-helpsphere-ia`** (lembre: vive em `rg-helpsphere-ia`, não em `rg-lab-final`)
   - **Select** → **Next**
5. Tab **Review + assign** → **Review + assign**
6. Aguarde ~10-30s até banner verde **Role assignment added**

<!-- screenshot: cap07-passo7.4-rbac-sb-data-receiver.png -->

> **Alternativa via Azure CLI:**
>
> ```bash
> MI_ID=$(az identity show \
>   --name mi-helpsphere-ia \
>   --resource-group rg-helpsphere-ia \
>   --query principalId -o tsv)
>
> SB_SCOPE=$(az servicebus namespace show \
>   --name sb-helpsphere-final \
>   --resource-group rg-lab-final \
>   --query id -o tsv)
>
> az role assignment create \
>   --assignee-object-id "$MI_ID" \
>   --assignee-principal-type ServicePrincipal \
>   --role "Azure Service Bus Data Receiver" \
>   --scope "$SB_SCOPE"
> ```

> **Custo:** R$ 0 — RBAC do Azure é gratuito sem limite de assignments.

> **Nota pedagógica — `Data Receiver` vs `Data Owner` vs `Data Sender`:** o n8n só **lê mensagens** do Topic `tickets-escalated` (Cap 08), portanto a role mínima é `Data Receiver` (princípio de **least privilege** do Zero Trust). `Data Sender` seria para o `agent_runner.py` do Cap 04 enviar mensagens (mas no Cap 04 ainda usamos placeholder; o Cap 08 trocará para Sender também via MI). `Data Owner` (super-usuário Service Bus) **NUNCA** atribua a workloads — só usuários humanos durante troubleshooting.

---

## Passo 7.5 — Importar workflow `escalation-servicebus-sheets.json`

O workflow já está cravado neste repo em `n8n-workflows/escalation-servicebus-sheets.json` (scaffold v0.1.0-init feito no Story 06.11 Bloco C). Ele tem 7 nodes:

| Ordem | Node | Tipo | Função |
|---|---|---|---|
| 1 | Service Bus Trigger | n8n-nodes-base.azureServiceBusTrigger | Polling no Topic `tickets-escalated` (subscription `n8n-escalation-sub` do Cap 08) |
| 2 | HTTP Request — GET ticket | HTTP Request | Chama MCP Server `get_ticket(ticket_id)` para detalhes |
| 3 | PostgreSQL — SELECT similar | PostgreSQL (HelpSphere DB) | Busca tickets resolvidos com mesma categoria |
| 4 | Switch — categoria → supervisor | Switch | Roteia: `Faturamento → Marina`, `Logística → Diego`, `default → Marina` |
| 5 | HTTP Request — Microsoft Graph (Teams) | HTTP Request OAuth2 | POST Adaptive Card no canal Teams da supervisora |
| 6 | HTTP Request — PATCH HelpSphere | HTTP Request | Atualiza status do ticket para `Escalated` no HelpSphere API |
| 7 | Google Sheets — append row | n8n-nodes-base.googleSheets | Append linha na planilha de auditoria (Cap 08 Passo 8.5) |

**No n8n UI:**

1. Sidebar esquerdo → **Workflows** → **+ New** (canto superior direito) → menu três pontos `⋮` no topo → **Import from file**
2. Selecione o arquivo `escalation-servicebus-sheets.json` do clone local deste repo (caminho típico: `C:\Projetos\apex-helpsphere-agente-lab\n8n-workflows\escalation-servicebus-sheets.json`)
3. n8n carrega o canvas com os 7 nodes. Cada node aparece com **ícone vermelho de erro** ⚠️ — esperado, faltam credentials (próximo Passo).
4. Clique em **Save** (canto superior direito) → nome sugerido: `Ticket Escalation` → **Save**

<!-- screenshot: cap07-passo7.5-importar-workflow-7-nodes.png -->

> **Custo:** R$ 0 — workflow é stored como JSON na tabela `workflow_entity` do PG.

> **Nota pedagógica — JSON do workflow vs construir nó-por-nó:** importar JSON garante **pareamento exato com o que o professor validou** (nomes de nodes, expressões `{{ $json.field }}`, IDs internos). Construir manualmente arrastando nodes é didático mas **divergências sutis** (ex.: `{{ $node["HTTP1"].json["ticket_id"] }}` vs `{{ $('HTTP1').first().json.ticket_id }}` — diferentes versões do n8n) **quebram o workflow** sem mensagem clara. Em produção: **versionar o JSON em git** + import via API n8n no CI/CD (`POST /workflows`).

---

## Passo 7.6 — Configurar credentials parciais (PostgreSQL HelpSphere + HTTP Header Auth)

Cada node com ícone vermelho precisa de uma credential. Vamos configurar **3 das 5** agora — as 2 restantes (Service Bus + Microsoft Graph OAuth + Google Sheets) ficam para o Cap 08 quando os recursos backend existirem.

**Credential 1 — PostgreSQL (HelpSphere DB):**

1. n8n sidebar → **Credentials** → **+ Add credential**
2. Procurar **Postgres** → selecionar
3. Preencher:
   - **Credential Name:** `HelpSphere PostgreSQL` (ou `HelpSphere SQL` se usar o SQL Server do Bloco 2 — depende do que existe na sua sub)
   - **Host:** `<seu HelpSphere DB host>` (do Bloco 2 — provavelmente `sql-helpsphere-<rand>.database.windows.net` se for SQL Server, ou `pg-helpsphere-<rand>.postgres.database.azure.com` se PG)
   - **Database:** `helpsphere`
   - **User:** seu admin do DB do Bloco 2
   - **Password:** correspondente
   - **SSL:** `require` (Azure DB sempre exige TLS)
   - **Port:** `5432` (PG) ou `1433` (SQL — mas n8n PG node não conecta SQL Server; **se for SQL Server, use o node "Microsoft SQL" em vez deste**)
4. Clique **Test connection** — esperado: ✅ **Connection successful**
5. **Save**

**Credential 2 — HTTP Header Auth (HelpSphere API):**

1. **+ Add credential** → procurar **Header Auth** → selecionar
2. Preencher:
   - **Credential Name:** `HelpSphere API Key`
   - **Name:** `x-functions-key`
   - **Value:** `<HelpSphere function key>` (capturada do Bloco 2 — Portal → Function App `func-helpsphere-rag` → **App keys** → copy `default`)
3. **Save**

**Credential 3 — HTTP Header Auth (MCP Server token) — opcional aqui:**

Se o node **HTTP Request — GET ticket** estiver configurado para chamar o MCP via Bearer (recomendado), crie:

1. **+ Add credential** → procurar **Header Auth** → selecionar
2. Preencher:
   - **Credential Name:** `MCP Server Bearer`
   - **Name:** `Authorization`
   - **Value:** `Bearer <MCP_TOKEN>` (capturado no Cap 05, pode ser placeholder se você ainda não rodou o smoke do Cap 05)
3. **Save**

**Credentials pendentes (ficam para Cap 08):**

- ⏸ **Service Bus** — depende de `sb-helpsphere-final` existir + RBAC do Passo 7.4 cravado
- ⏸ **Microsoft Graph OAuth2** — depende do App Registration `app-n8n-graph` (Cap 08 Passo 8.4)
- ⏸ **Google Sheets OAuth2** — depende de OAuth client criado no Google Cloud Console (Cap 08 Passo 8.5)

<!-- screenshot: cap07-passo7.6-credentials-parciais.png -->

> **Custo:** R$ 0 — credentials são metadata cifrada com `N8N_ENCRYPTION_KEY` no PG.

> **Nota pedagógica — credentials por workflow vs globais:** n8n armazena credentials **globalmente** no escopo do owner (não por workflow). Isso é prático no lab, **arriscado em produção** com múltiplos usuários: qualquer editor com acesso pode reusar credentials que outro criou. Em produção real: **n8n External User Auth** + **Workflow Sharing scoped per credential** (feature paga) ou **separar n8n instances por equipe** (mais comum).

---

## Passo 7.7 — Pause/resume strategy ao fim da sessão (CRÍTICO)

Você acabou de provisionar o **maior custo recorrente do Lab Final**: PostgreSQL B1ms a R$ 60/mês ligado 24×7. Ao fim de **cada sessão de estudo**, escolha **uma das 2 opções**:

### Opção A — Stop temporário (recomendado se vai voltar amanhã)

Para o PG E o ACA do n8n. Storage do PG continua cobrando ~R$ 5/mês mas compute zera.

**No Portal Azure:**

1. Recurso `pg-n8n-<rand>` → **Overview** → botão **Stop** (topo) → confirmar
   - Status muda para **Stopped** em ~30s
   - ⚠️ **Auto-start em 7 dias:** Azure reinicia o servidor automaticamente após 7 dias parado (limitação da feature). Se sumir do radar por mais que isso, ele liga sozinho e cobra de novo.
2. Recurso `ca-n8n-helpsphere` → **Application** → **Revisions and replicas** → revision ativa → **Deactivate**
   - Status muda para **Inactive** em ~10s
   - Custo zera (replicas = 0)

**No CLI:**

```bash
az postgres flexible-server stop \
  --name "pg-n8n-${RAND}" \
  --resource-group rg-lab-final

az containerapp revision deactivate \
  --name ca-n8n-helpsphere \
  --resource-group rg-lab-final \
  --revision $(az containerapp revision list \
    --name ca-n8n-helpsphere \
    --resource-group rg-lab-final \
    --query "[?properties.active].name | [0]" -o tsv)
```

**Para retomar:** **Start** no PG (5min provisioning), depois **Activate revision** no ACA (1min). Workflow estado preservado integralmente.

### Opção B — Delete completo (recomendado se vai pausar ≥7 dias)

Deleta tudo. Storage zera. **Você perde o estado do n8n** (workflows, credentials, executions), tem que reimportar tudo no próximo Setup.

**No Portal Azure:**

1. RG `rg-lab-final` → **Overview** → **Delete resource group** → digitar nome → **Delete**
2. ⚠️ Isto deleta **TODOS** os recursos do Lab Final: ACR, ACA Env, n8n, MCP Server, Speech (Cap 06). Se ainda quiser preservar partes, **delete recursos individualmente** em vez do RG inteiro.

**No CLI:**

```bash
az group delete --name rg-lab-final --yes --no-wait
```

> **Custo:** Opção A = ~R$ 5/mês (storage idle do PG) + R$ 0 ACA. Opção B = R$ 0 total mas re-setup ~30min na volta.

> **Nota pedagógica — por que pausar e não baixar SKU para Free tier?** PostgreSQL Flexible Server não tem Free tier no Azure (ver [`_disclaimers.md`](./_disclaimers.md) **AMB-3** para a decisão completa). Em produção real: dev/staging/prod usam Burstable e suspendem fora de horário comercial via Azure Automation runbook com schedule cron.

<!-- screenshot: cap07-passo7.7-stop-postgres-portal.png -->

---

## Validação end-to-end

```bash
# 1. PostgreSQL existe e está Ready/Running
az postgres flexible-server show \
  --name "pg-n8n-${RAND}" \
  --resource-group rg-lab-final \
  --query "{name:name, state:state, sku:sku.name, version:version}" -o table
# Esperado: state=Ready, sku=Standard_B1ms, version=16

# 2. Database n8n criado dentro do server
az postgres flexible-server db list \
  --resource-group rg-lab-final \
  --server-name "pg-n8n-${RAND}" \
  -o table
# Esperado: linha com name=n8n

# 3. Container App n8n rodando
az containerapp show \
  --name ca-n8n-helpsphere \
  --resource-group rg-lab-final \
  --query "{fqdn:properties.configuration.ingress.fqdn, replicas:properties.template.scale, image:properties.template.containers[0].image}" -o json
# Esperado: fqdn=ca-n8n-helpsphere.<rand>.eastus2.azurecontainerapps.io, image=n8nio/n8n:1.6, scale.minReplicas=1

# 4. n8n responde HTTP 200 na rota /healthz
curl -i "https://${N8N_FQDN}/healthz"
# Esperado: HTTP/2 200 + body { "status": "ok" }

# 5. Workflow importado aparece via n8n REST API (Bearer = email/password do owner em Basic Auth)
curl -u "<owner-email>:<owner-password>" \
  "https://${N8N_FQDN}/rest/workflows" | jq '.data[] | {id, name, active}'
# Esperado: linha { id: "...", name: "Ticket Escalation", active: false }

# 6. Role assignment do MI (apenas se Cap 08 já feito + Passo 7.4 cravado)
az role assignment list \
  --assignee "$MI_ID" \
  --query "[?roleDefinitionName=='Azure Service Bus Data Receiver']" -o table
# Esperado: 1 linha com scope contendo sb-helpsphere-final
```

---

## Checklist final

```text
[ ] PostgreSQL pg-n8n-<rand> Burstable B1ms criado e em estado Ready
[ ] Database n8n existe dentro do server
[ ] Allow public access from any Azure service: Yes (firewall PG)
[ ] Container App ca-n8n-helpsphere rodando com image n8nio/n8n:1.6 (NÃO :latest)
[ ] N8N_ENCRYPTION_KEY armazenada como ACA Secret (não plain env var)
[ ] DB_POSTGRESDB_PASSWORD armazenada como ACA Secret
[ ] WEBHOOK_URL atualizado com FQDN ACA real (https://...azurecontainerapps.io/)
[ ] n8n owner setup completo (email + password anotados)
[ ] Workflow Ticket Escalation importado com 7 nodes
[ ] Credential PostgreSQL (HelpSphere DB) configurada e Test Connection OK
[ ] Credential HTTP Header Auth (HelpSphere API key) configurada
[ ] Credential MCP Server Bearer configurada (opcional aqui)
[ ] TODO — voltar após Cap 08 Passo 8.1 para cravar role Azure Service Bus Data Receiver no MI
[ ] Estratégia pause/resume escolhida e executada ao fim da sessão (Opção A ou B)
```

---

## Surpresas pedagógicas (capturadas em smoke runs)

- ⚠️ **`n8nio/n8n:latest` quebra a cada release minor** — dia 15/04/2025 a tag `latest` introduziu breaking change no schema do PG metadata, container subiu, owner setup OK, mas todos os workflows existentes ficaram **invisíveis** (`workflow_entity` schema migration falhou silently). **Workaround:** sempre pinar tag major.minor (`1.6`, `1.7`, etc.) e atualizar via novo deploy planejado. Acompanhe `https://github.com/n8n-io/n8n/releases` antes de bumpar.
- ⚠️ **PostgreSQL `Allow public access from any Azure service: No` quebra ACA** — se você esquecer essa flag, o n8n container sobe mas **fica em loop de restart** com erro `connection refused` (PG firewall bloqueia). Workaround: ative a flag em **Networking** do PG. Em prod real, use VNet integration + Private Endpoint em vez disso.
- ⚠️ **`min-replicas 0` perde Service Bus messages mesmo com `Active workflow` no n8n** — n8n usa long-polling no Service Bus trigger, não KEDA. Quando `min-replicas 0`, container dorme após 5min idle, polling para, mensagens enfileiram mas **dead-letter após 3 retries** sem nunca acordar o n8n. Workaround: `min-replicas 1` no lab. Em prod: implementar KEDA Service Bus scaler com **separate Function App** que desperta o n8n via webhook.
- ⚠️ **`WEBHOOK_URL` vazio gera URLs internas inacessíveis** — se você esquecer de atualizar `WEBHOOK_URL` para a Application Url real do ACA, n8n gera webhooks com host `0.0.0.0:5678` (do `N8N_HOST`) que **funcionam dentro do container mas não de fora**. Adaptive Cards do Teams clicam no webhook e dão 404. Workaround: sempre cravar `WEBHOOK_URL=https://<FQDN>/` (com barra final) **após** o ACA criar e ter FQDN.
- ⚠️ **`N8N_ENCRYPTION_KEY` perdida = todas as credentials viram lixo cifrado** — não dá pra recuperar. Workaround: sempre gere via `openssl rand -base64 32`, **anote em Key Vault** ou password manager pessoal **antes** de colar no ACA Secret. Em prod: use `keyvaultRef` no ACA Secret apontando pra Azure Key Vault.
- ⚠️ **Owner setup do n8n não tem "esqueci minha senha"** — se você perder a senha do owner, único caminho é `psql -h <PG_HOST> -U n8nadmin n8n -c "DELETE FROM \"public\".\"user\" WHERE email='<seu-email>';"` e refazer setup. Em prod: integre SSO Entra ID ou pelo menos external auth via webhook.
- ⚠️ **Service Bus Topic vs Queue — confusão sem aviso no UI do n8n** — o n8n node `Azure Service Bus Trigger` aceita ambos no campo `Resource`, mas o **Topic exige `Subscription Name` adicional** (nem sempre visível no primeiro carregamento do node). Se você vier do Cap 08 e usou Topic (ver [`_disclaimers.md`](./_disclaimers.md) **AMB-4**), preencha o campo `Subscription` com `n8n-escalation-sub` — **se deixar vazio, polling falha silently**.
- ⚠️ **PostgreSQL `Stop` reinicia automaticamente após 7 dias** — feature da Microsoft (não bug) para evitar servers órfãos. Se você pausa um lab e volta em 10 dias, **PG está rodando e cobrando** sem você saber. Ver [`_disclaimers.md`](./_disclaimers.md) **AMB-3** para detalhe + Cost Anomaly Alert R$ 50 (proteção permanente).

---

## Próximo capítulo

[08 — Service Bus + Google Sheets Audit](./08-service-bus-google-sheets.md)
