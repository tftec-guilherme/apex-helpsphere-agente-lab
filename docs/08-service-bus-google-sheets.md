# Capítulo 08 — Service Bus + Google Sheets Audit

> **Objetivo:** provisionar **Azure Service Bus tier Standard** (namespace `sbns-helpsphere-final-{rand}` no `rg-lab-final`) — Standard é **obrigatório** porque o Lab usa **Topics** (Basic só suporta Queues), criar o **Topic `ticket-events`** com **2 Subscriptions** (`sub-n8n` para tool `escalate_ticket` → n8n; `sub-sheets` para auditoria → Google Sheets), ativar a credential Service Bus do n8n com Connection String + cravar a role assignment `Azure Service Bus Data Sender` na Managed Identity `mi-helpsphere-ia` (tool `escalate_ticket` do agente Foundry publica como Sender), criar **Service Account Google** + planilha de auditoria + credential Google Sheets Service Account no n8n, fechar a tool `escalate_ticket` do agente Foundry escrevendo no Service Bus de verdade (não mais placeholder) e validar o smoke end-to-end: `agent_runner.py` → SB Topic → 2 Subscriptions (n8n + Sheets) → Adaptive Card Teams + linha nova na planilha Google.
>
> **Tempo:** 70-90 min (50-60 min se você já tem Google Cloud Project com Service Account ativa de outro lab)
>
> **Status:** `v0.2.0-piloto` ⚠️ EXPANDIDO (era `v0.1.0-init` outline) — derivado de `Lab_Final_Agente_Workflow_Guia_Portal.md` Parte 7 (Passos 7.1-7.6)

---

> [!IMPORTANT] **Tier / Licenciamento**
> Decisão **Service Bus tier Standard obrigatório** (Basic NÃO suporta Topics) consolidada em [`_disclaimers.md`](./_disclaimers.md). Veja **AMB-4** para detalhe completo: motivação fan-out pub/sub (1 produtor → N consumidores independentes), custo R$ 50/mês fixo enquanto ligado (baseline, NÃO por mensagem), comparação Premium (~R$ 2.500/mês — dedicated capacity, só faz sentido em produção com p99 latency crítico), e `delete-pause-recreate` strategy do Passo 8.7.

---

## Pré-requisitos

- ✅ Capítulo 02 concluído — RG `rg-lab-final` existe na sub, sufixo `{rand}` cravado em `.env`
- ✅ Capítulo 04 concluído — agente Foundry `helpsphere-tier1-agent` criado, `agent-code/` com `agent_runner.py` rodando localmente, tool `escalate_ticket` registrada com schema mas ainda em **placeholder** (não publica em SB de verdade — vamos fechar isso aqui)
- ✅ Capítulo 07 concluído — Container App `ca-n8n-helpsphere` rodando no `rg-lab-final` com workflow `Ticket Escalation` importado, owner setup completo, **TODO pendente** do Passo 7.4 (role `Azure Service Bus Data Receiver` no MI) será fechado aqui no Passo 8.4
- ✅ Conta Google ativa (qualquer Gmail pessoal ou Workspace) — vamos criar Service Account no Google Cloud Console
- ✅ Acesso Owner ou User Access Administrator na sub Azure (necessário no Passo 8.4 — duas role assignments)
- ✅ Variáveis de ambiente disponíveis em `agent-code/.env`:
  - `PROJECT_CONNECTION_STRING`
  - `AGENT_ID`
  - `RAG_FUNCTION_URL`, `MCP_SERVER_URL` (de capítulos anteriores)
  - **`SB_NAMESPACE_FQDN`** (vamos preencher aqui)
  - **`SB_TOPIC_NAME`** (vamos preencher aqui)
  - **`SHEET_ID`** (vamos preencher aqui)

> **Atenção breaking — referência cruzada:** a Managed Identity `mi-helpsphere-ia` foi criada cross-RG no `rg-lab-intermediario` (lab anterior). Aqui vamos **fechar** a credential Service Bus do n8n no Passo 8.3, cravar a role `Azure Service Bus Data Receiver` na MI (TODO pendente do capítulo anterior, Passo 7.4) **mais** uma role adicional `Azure Service Bus Data Sender` na MI para o agente Foundry publicar (Passo 8.4).

> **Atenção custo recorrente — Service Bus + ACA n8n + PG:** ao fim deste capítulo, o custo total do Lab Final ligado 24×7 fica em **R$ ~145/mês** (Service Bus Standard ~R$ 50 fixo enquanto ligado + PG B1ms ~R$ 60 + ACA n8n `min-replicas 1` ~R$ 35). Pause **TODOS** ao fim da sessão (Passo 8.7) — Service Bus aceita `delete-pause-recreate` (não tem feature `Stop` como o PG).

---

## Resumo dos 7 artefatos que vamos cravar

| Artefato | Implementação | Backend / Identidade | Custo (R$ por sessão lab 4-8h) |
|---|---|---|---|
| Service Bus namespace `sbns-helpsphere-final-{rand}` | Portal → Service Bus → Create namespace · **tier Standard** · East US 2 | RG `rg-lab-final`, sem zone redundancy (Standard não suporta) | **~R$ 5-8/sessão** (R$ 50/mês prorata + R$ 0,80/M operações; lab usa <100 msg/dia → ~R$ 0 em operações) |
| Topic `ticket-events` (1 produtor, N consumidores fan-out) | Portal → namespace → Entities → Topics → New · `max-size=1024 MB`, TTL 14 dias | Stored dentro do namespace | R$ 0 (incluso no namespace) |
| Subscription `sub-n8n` (n8n consome para Teams + dispatch) | Portal → topic → Subscriptions → New · `lock-duration=30s`, `max-delivery=3`, dead-letter ON | Stored dentro do topic | R$ 0 |
| Subscription `sub-sheets` (auditoria Google Sheets) | Mesma blade · mesma config (`lock-duration=30s`, `max-delivery=3`, dead-letter ON) | Stored dentro do topic | R$ 0 |
| Role `Azure Service Bus Data Receiver` em `mi-helpsphere-ia` | Portal → namespace → IAM → Add role assignment · **escopo namespace inteiro** (cobre as 2 subscriptions) | MI cross-RG `rg-lab-intermediario` · usado pelo n8n para LER `sub-n8n` e `sub-sheets` | R$ 0 (RBAC gratuito) |
| Role `Azure Service Bus Data Sender` em `mi-helpsphere-ia` | Mesmo blade IAM, segunda role assignment · escopo namespace | MI usada pelo agente Foundry para PUBLICAR no Topic `ticket-events` | R$ 0 |
| Google Service Account + planilha auditoria | Google Cloud Console → IAM → Service Accounts + Drive API + Sheets API | Conta Google (Gmail ou Workspace) — NÃO Azure | **R$ 0 — Google Sheets API gratuita** até 60 reqs/min/projeto |
| Credenciais SB + Sheets ativadas no n8n | n8n UI → Credentials → ativar `HelpSphere Service Bus` (Cap anterior rascunho) + criar `Google Sheets Service Account` | Stored cifrado no PG do n8n via `N8N_ENCRYPTION_KEY` | R$ 0 |

> **Nota pedagógica — por que Standard e não Basic?** Service Bus tem 3 tiers: Basic (~R$ 0,15 por milhão de operações; só Queues), Standard (~R$ 50/mês fixo enquanto ligado; Queues + Topics + Subscriptions + Sessions), Premium (~R$ 2.500/mês; dedicated capacity). Para o pattern pub/sub deste lab (1 produtor agente, 2 consumidores n8n + Sheets), Topics são essenciais — Basic **NÃO suporta Topics**. Standard é o tier mínimo viável. Em produção real, considere Premium se latência tail (p99) for crítica.

> **Nota pedagógica — Topic + 2 Subscriptions, por que esta arquitetura?** Queue é **1 emissor → 1 grupo de consumidores competindo** (cada msg lida por 1 só worker). Topic é **1 emissor → N subscriptions independentes** (cada subscription recebe **cópia própria** da mensagem). Aqui usamos Topic `ticket-events` com **2 subscriptions independentes**:
>
> - **`sub-n8n`** → n8n trigger consome e dispara Teams Adaptive Card (canal supervisora) + reatribuição no HelpSphere.
> - **`sub-sheets`** → n8n consome de novo (cópia independente da mesma mensagem) e faz append na planilha Google de auditoria.
>
> Cada subscription tem **lock-duration próprio** + **dead-letter próprio** — falha em uma não afeta a outra. Amanhã, adicionar **`sub-bi`** para Logic App escrever em SQL warehouse é gratuito e zero código no agente.

> **Nota pedagógica — Connection String vs Managed Identity, qual usar?** No capítulo anterior cravamos a credential do n8n em **rascunho** com Connection String porque a MI ainda não tinha role assignment. Vamos **manter Connection String no n8n** porque o trigger `Azure Service Bus` ainda **não suporta MI nativamente** (limitação do node oficial — issue aberto há ~2 anos). **No agente Foundry usamos MI** porque o SDK Python `azure-servicebus` suporta `DefaultAzureCredential` end-to-end. **Em produção real:** trocar n8n para Logic App + MI ou esperar o node n8n suportar MI.

> **Nota pedagógica — `Data Receiver` vs `Data Sender` na MESMA MI:** princípio **least privilege** sugere MIs separadas (uma sender, uma receiver). Mas no Lab **reusamos** `mi-helpsphere-ia` (criada anteriormente para AcrPull) porque criar 3 MIs polui o RG. **Em produção real:** 1 MI por workload (sender = MI do agente runner; receiver = MI do n8n; AcrPull = MI da deploy pipeline).

---

## Passo 8.1 — Provisionar Service Bus namespace `sbns-helpsphere-final-{rand}` (tier Standard)

**No Portal Azure:**

1. Abra `https://portal.azure.com` → confirme sub correta (canto superior direito) — **deve ser a mesma do RG `rg-lab-final`**
2. Barra superior → buscar **"Service Bus"** → clicar no resultado **Service Bus** (não confundir com **Service Bus Explorer**, que é uma blade interna)
3. Clique **+ Create**
4. Preencher tab **Basics**:
   - **Subscription:** sua sub
   - **Resource group:** `rg-lab-final`
   - **Namespace name:** `sbns-helpsphere-final-{rand}` ⚠️ **substitua `{rand}` pelo sufixo capturado no Cap 02** (ex.: `sbns-helpsphere-final-a8f3c`) — nome deve ser globalmente único no Azure
   - **Location:** `East US 2` (mesma região do `cae-helpsphere-final`)
   - **Pricing tier:** ⚠️ **Standard** (NÃO `Basic` — ver [`_disclaimers.md`](./_disclaimers.md) **AMB-4**)
5. Tab **Advanced:** deixe defaults (sem zone redundancy — Standard não suporta, só Premium)
6. Tab **Networking:**
   - **Connectivity method:** `Public access` (firewall padrão aceita tudo — para o lab OK; produção real usa Private Endpoint)
   - **Allow trusted Microsoft services to bypass this firewall:** ✅ **Yes**
7. Clique **Review + create** → **Create**
8. Aguarde provisioning **~1-2min** até banner verde **Your deployment is complete** → clique **Go to resource**

**Validação visual no Portal:** após o **Go to resource**, no Overview do namespace você deve ver:
- **Status:** `Active` (verde)
- **Pricing tier:** `Standard`
- **Location:** `East US 2`
- **Service Bus endpoint:** `sbns-helpsphere-final-{rand}.servicebus.windows.net` (anote — vai pro `.env`)

<!-- screenshot: cap08-passo8.1-criar-sb-namespace-standard.png -->

> **Alternativa via Azure CLI (PowerShell 7 — Windows-first):**
>
> ```powershell
> # Captura sufixo {rand} do .env (gerado no Cap 02)
> $Rand = (Get-Content .\.env | Select-String '^RAND=').ToString().Split('=')[1]
>
> az servicebus namespace create `
>   --resource-group rg-lab-final `
>   --name "sbns-helpsphere-final-$Rand" `
>   --location eastus2 `
>   --sku Standard
>
> # Capturar FQDN para .env
> $Endpoint = az servicebus namespace show `
>   --resource-group rg-lab-final `
>   --name "sbns-helpsphere-final-$Rand" `
>   --query serviceBusEndpoint -o tsv
> $env:SB_NAMESPACE_FQDN = $Endpoint -replace '^https://','' -replace ':443/?$',''
> Write-Host "SB_NAMESPACE_FQDN=$env:SB_NAMESPACE_FQDN"
> # Esperado: sbns-helpsphere-final-<rand>.servicebus.windows.net
> ```
>
> **Linux/Mac/WSL:** troque `` ` `` (backtick) por `\`, `$Var` por `VAR=`, `Write-Host` por `echo`, e use `sed 's|https://||;s|:443/||'` no lugar do `-replace`.

> **Custo:** Service Bus Standard **~R$ 50/mês fixo enquanto ligado** (NÃO por mensagem — cobra parado) + R$ 0,80/M operações. Em sessão lab típica de 4-8h com cleanup ao final, **~R$ 5-8 total**. Operações gratuitas até 1M/mês — lab gera <100 msg/dia → operações ~R$ 0. Detalhes da decisão tier em [`_disclaimers.md`](./_disclaimers.md) **AMB-4**.

---

## Passo 8.2 — Criar Topic `ticket-events` + 2 Subscriptions (`sub-n8n` + `sub-sheets`)

**Topic — No Portal Azure:**

1. Recurso `sbns-helpsphere-final-{rand}` → menu lateral → **Entities** → **Topics**
2. **+ Topic**
3. Preencher:
   - **Name:** `ticket-events` ⚠️ **literal — a tool `escalate_ticket` do agente Foundry vai usar este nome no SB SDK**
   - **Max topic size:** `1 GB` (default — suficiente para o lab, ajusta automático)
   - **Message time to live:** `14 days` (default — Service Bus auto-deleta msgs não consumidas após 14d)
   - **Duplicate detection:** `Disabled` (default — habilitar custa overhead, lab não precisa)
   - **Enable partitioning:** `Disabled` (default — partitioning é one-way; uma vez habilitado não dá pra desabilitar)
4. Clique **Create** → aguarde ~5s até aparecer na lista

<!-- screenshot: cap08-passo8.2a-criar-topic-ticket-events.png -->

**Subscription 1 — `sub-n8n` (consome para Teams + dispatch):**

1. Clique no Topic `ticket-events` (recém-criado) → menu **Subscriptions** (dentro do topic) → **+ Subscription**
2. Preencher:
   - **Name:** `sub-n8n` ⚠️ **literal — workflow n8n vai referenciar exatamente este nome**
   - **Max delivery count:** `3` (após 3 falhas, msg vai para dead-letter automaticamente)
   - **Lock duration:** `30 seconds` (n8n tem 30s para confirmar `complete`/`abandon`/`deadletter` — alinhado com `lockDuration` do node n8n)
   - **Message time to live:** `14 days` (default)
   - **Enable dead lettering on message expiration:** ✅ **Enabled**
   - **Enable dead lettering on filter evaluation exceptions:** ✅ **Enabled**
   - **Enable session:** `Disabled` (default — sessions são para FIFO ordenado por `SessionId`, não usado neste lab)
3. Clique **Create** → aguarde ~5s

**Subscription 2 — `sub-sheets` (auditoria Google Sheets, MESMA blade):**

1. Mesma página do Topic `ticket-events` → **+ Subscription**
2. Preencher (idêntico à `sub-n8n` exceto pelo nome):
   - **Name:** `sub-sheets` ⚠️ **literal — workflow Sheets vai referenciar exatamente este nome**
   - **Max delivery count:** `3`
   - **Lock duration:** `30 seconds`
   - **Message time to live:** `14 days`
   - **Enable dead lettering on message expiration:** ✅ **Enabled**
   - **Enable dead lettering on filter evaluation exceptions:** ✅ **Enabled**
   - **Enable session:** `Disabled`
3. Clique **Create**

<!-- screenshot: cap08-passo8.2b-criar-2-subscriptions.png -->

**Validação visual no Portal:** Topic `ticket-events` → tab **Subscriptions** deve mostrar 2 linhas:
- `sub-n8n` — Active count: 0, Dead-letter count: 0
- `sub-sheets` — Active count: 0, Dead-letter count: 0

> **Alternativa via Azure CLI (PowerShell 7 — Windows-first):**
>
> ```powershell
> $Rand = (Get-Content .\.env | Select-String '^RAND=').ToString().Split('=')[1]
> $SbName = "sbns-helpsphere-final-$Rand"
>
> # Topic
> az servicebus topic create `
>   --resource-group rg-lab-final `
>   --namespace-name $SbName `
>   --name ticket-events `
>   --max-size 1024 `
>   --default-message-time-to-live P14D
>
> # Subscription para n8n (Teams + dispatch)
> az servicebus topic subscription create `
>   --resource-group rg-lab-final `
>   --namespace-name $SbName `
>   --topic-name ticket-events `
>   --name sub-n8n `
>   --max-delivery-count 3 `
>   --lock-duration PT30S `
>   --dead-letter-on-message-expiration true `
>   --dead-letter-on-filter-evaluation-exceptions true
>
> # Subscription para Sheets (auditoria)
> az servicebus topic subscription create `
>   --resource-group rg-lab-final `
>   --namespace-name $SbName `
>   --topic-name ticket-events `
>   --name sub-sheets `
>   --max-delivery-count 3 `
>   --lock-duration PT30S `
>   --dead-letter-on-message-expiration true `
>   --dead-letter-on-filter-evaluation-exceptions true
> ```
>
> **Linux/Mac/WSL:** troque `` ` `` (backtick) por `\` no fim das linhas e `$Var` por `VAR=`.

> **Custo:** R$ 0 — Topics e Subscriptions são gratuitos dentro do namespace Standard (até 1.000 topics × 2.000 subscriptions/topic, suficiente para vida toda do lab).

> **Nota pedagógica — fan-out vai TER 2 cópias independentes:** quando o agente publicar 1 mensagem no Topic `ticket-events`, o Service Bus **automaticamente duplica** para cada subscription. `sub-n8n` recebe 1 cópia + `sub-sheets` recebe outra cópia. Cada subscription tem o próprio lock-duration, próprio dead-letter, próprio cursor de leitura. Falha em `sub-sheets` (ex.: API Google fora) **não bloqueia** `sub-n8n`.

> **Nota pedagógica — `lock-duration 30s` é arbitrário?** Não. n8n trigger Service Bus tem timeout default de **30s** para chamar `completeMessage()`. Se você setar `lock-duration < 30s` e o workflow do n8n levar 25s para rodar (ex.: HelpSphere API lenta), o lock expira **antes** do n8n confirmar — Service Bus reenvia a msg, n8n processa de novo, **escalação duplicada**. `30s` é o sweet spot para lab. Em produção: ajuste com base em P99 latency real do workflow (geralmente 5x o tempo médio).

> **Nota pedagógica — Dead-letter queue (DLQ) é OBRIGATÓRIO em produção:** sem DLQ, mensagens que falham (3x retry) **somem silently**. Com DLQ, vão para `ticket-events/Subscriptions/<sub-name>/$DeadLetterQueue` (acessível via Service Bus Explorer no Portal). **Setup minimum production:** alerta Application Insights na queue depth da DLQ — se > 0, página alguém. Lab não cria alerta para economizar tempo, mas a DLQ está lá esperando em ambas as subscriptions.

---

## Passo 8.3 — Capturar Connection String e ativar credential Service Bus no n8n

**Capturar Connection String — No Portal Azure:**

1. Namespace `sbns-helpsphere-final-{rand}` → menu **Settings** → **Shared access policies**
2. Clique em **RootManageSharedAccessKey** (criada por padrão pelo Azure)
3. Painel direito abre → clique **Show** ao lado de **Primary Connection String**
4. **Copy** → cole em um editor seguro local (vai ser anotado no n8n e descartado)

   Formato: `Endpoint=sb://sbns-helpsphere-final-{rand}.servicebus.windows.net/;SharedAccessKeyName=RootManageSharedAccessKey;SharedAccessKey=<long-key>=`

<!-- screenshot: cap08-passo8.3-copiar-sb-connection-string.png -->

> **Atenção segurança — RootManageSharedAccessKey é super-usuário:** essa key dá `Manage` (criar/deletar Topics, Subscriptions, queues — não só Read/Write). Para n8n, o ideal seria criar uma **Shared access policy nova** com **só `Listen`** (só read) no escopo da subscription. Lab usa Root para simplificar — **em produção, NUNCA**.

**Ativar credential no n8n:**

1. Abra `https://<N8N_URL>` (Application Url do `ca-n8n-helpsphere` — capturada no capítulo anterior)
2. Login com email + password do owner
3. Sidebar esquerdo → **Credentials** → procure pela credential rascunho `HelpSphere Service Bus` (se não criou, **+ Add credential** → procurar `Azure Service Bus`)
4. Clique para editar:
   - **Credential Name:** `HelpSphere Service Bus`
   - **Connection String:** cole a Connection String capturada acima
5. Clique **Test connection** — esperado: ✅ **Connection successful**
6. **Save**

<!-- screenshot: cap08-passo8.3-credential-sb-n8n-ativada.png -->

**Atualizar workflow `Ticket Escalation` (node Service Bus Trigger):**

1. Sidebar esquerdo → **Workflows** → clique em **Ticket Escalation**
2. Clique no node **Service Bus Trigger** (primeiro na esquerda do canvas)
3. No painel direito, campo **Credential**: selecione `HelpSphere Service Bus` (recém-ativada)
4. Confirme/ajuste os campos:
   - **Resource:** `Topic` (não Queue)
   - **Topic:** `ticket-events`
   - **Subscription:** `sub-n8n` ⚠️ — este workflow consome especificamente da subscription `sub-n8n` (a `sub-sheets` será consumida por workflow paralelo — Passo 8.5)
   - **Operation:** `Receive Messages`
   - **Lock duration:** `30` (segundos)
5. Ícone do node muda de vermelho para amarelo (próxima credential pendente é a do Google Sheets — Passo 8.5)
6. Clique **Save** no canvas (canto superior direito)

<!-- screenshot: cap08-passo8.3-workflow-sb-trigger-configurado.png -->

> **Custo:** R$ 0 — credential é só metadata cifrada no PG do n8n.

> **Nota pedagógica — Connection String vai ser substituída por MI quando?** O node n8n `Azure Service Bus Trigger` v1.x **só aceita Connection String** (issue oficial no repo do n8n aberto há ~2 anos). Quando o n8n suportar `DefaultAzureCredential` nativamente, trocaremos pelos roles do Passo 8.4 e descartaremos a Connection String. **Por enquanto:** Connection String ativa + RBAC paralelo cravado, dual-stack.

---

## Passo 8.4 — Cravar 2 role assignments na MI `mi-helpsphere-ia`

⚠️ **Heads-up:** este Passo fecha o **TODO pendente do capítulo anterior (Passo 7.4)** (Data Receiver) **MAIS** adiciona uma segunda role (Data Sender) — duas role assignments na mesma MI, uma para o n8n (futuro, quando node suportar MI) e outra para o agente Foundry (tool `escalate_ticket`).

**Role 1 — `Azure Service Bus Data Receiver` na MI:**

**No Portal Azure:**

1. Recurso `sbns-helpsphere-final-{rand}` → menu **Access control (IAM)** → **+ Add** → **Add role assignment**
2. Tab **Role:**
   - Categoria: **Job function roles**
   - Procurar: `Azure Service Bus Data Receiver`
   - Selecionar → **Next**
3. Tab **Members:**
   - **Assign access to:** `Managed identity`
   - **+ Select members** → **Subscription:** sua → **Managed identity:** `User-assigned managed identity` → selecione **`mi-helpsphere-ia`** (lembre: vive em `rg-lab-intermediario` cross-RG, não no `rg-lab-final`)
   - **Select** → **Next**
4. Tab **Review + assign** → **Review + assign**
5. Aguarde ~10-30s até banner verde **Role assignment added**

<!-- screenshot: cap08-passo8.4-role-data-receiver.png -->

**Role 2 — `Azure Service Bus Data Sender` na MI (mesma blade IAM):**

1. Mesma blade **Access control (IAM)** → **+ Add** → **Add role assignment**
2. Tab **Role:** procurar `Azure Service Bus Data Sender` → selecionar → **Next**
3. Tab **Members:** mesma flow do anterior — selecione **`mi-helpsphere-ia`** → **Next**
4. **Review + assign** → aguarde banner verde

<!-- screenshot: cap08-passo8.4-role-data-sender.png -->

**Validação visual no Portal — IAM blade deve mostrar 2 role assignments para `mi-helpsphere-ia`:**

1. Mesma blade **Access control (IAM)** → tab **Role assignments**
2. Filtre por scope: `This resource` → procure `mi-helpsphere-ia`
3. Esperado: 2 linhas, uma com `Azure Service Bus Data Receiver`, outra com `Azure Service Bus Data Sender`

> **Alternativa via Azure CLI (PowerShell 7 — Windows-first):**
>
> ```powershell
> $Rand = (Get-Content .\.env | Select-String '^RAND=').ToString().Split('=')[1]
> $SbName = "sbns-helpsphere-final-$Rand"
>
> $MiId = az identity show `
>   --resource-group rg-lab-intermediario `
>   --name mi-helpsphere-ia `
>   --query principalId -o tsv
>
> $SbScope = az servicebus namespace show `
>   --resource-group rg-lab-final `
>   --name $SbName `
>   --query id -o tsv
>
> # Receiver (n8n future + dual-stack)
> az role assignment create `
>   --assignee-object-id $MiId `
>   --assignee-principal-type ServicePrincipal `
>   --role "Azure Service Bus Data Receiver" `
>   --scope $SbScope
>
> # Sender (agente Foundry tool escalate_ticket)
> az role assignment create `
>   --assignee-object-id $MiId `
>   --assignee-principal-type ServicePrincipal `
>   --role "Azure Service Bus Data Sender" `
>   --scope $SbScope
> ```
>
> **Linux/Mac/WSL:** troque `` ` `` (backtick) por `\`, `$Var = az ...` por `VAR=$(az ...)`, e `$Var` por `"$VAR"`.

> **Custo:** R$ 0 — RBAC do Azure é gratuito sem limite de assignments por escopo.

> **Nota pedagógica — escopo namespace vs Topic vs Subscription:** atribuímos a role no escopo **namespace inteiro** (`sbns-helpsphere-final-{rand}`) — isso cobre as 2 subscriptions (`sub-n8n` + `sub-sheets`) e qualquer outra futura sem precisar revisitar. Em produção, **least privilege** sugere escopar até a Subscription específica (`/topics/ticket-events/subscriptions/sub-n8n`) — assim a MI só lê **dessa subscription**, não todas. Lab usa namespace para simplificar. **Production checklist:** escopar role ao mínimo recurso possível, revisar a cada 90 dias via **Azure Privileged Identity Management**.

---

## Passo 8.5 — Criar Google Service Account + planilha auditoria + workflow `sub-sheets`

> **⚠️ Setup externo requerido — Google Cloud:** este Passo requer **conta Google pessoal (Gmail) ou Workspace** com permissão para criar projetos no Google Cloud Console. **Se você nunca usou GCP antes**, vai precisar aceitar termos de uso na primeira visita e (em alguns casos) confirmar identidade via SMS. **NÃO requer cartão de crédito** — Sheets API é 100% free tier. Se a sua conta corporativa tem GCP bloqueado por policy, use Gmail pessoal apenas para o lab.

**Google Cloud Console — Service Account:**

1. Abra `https://console.cloud.google.com` → faça login com sua conta Google (Gmail pessoal ou Workspace)
2. Topo → seletor de projeto → **NEW PROJECT**:
   - **Project name:** `apex-helpsphere-lab`
   - **Location:** `No organization` (se conta Gmail pessoal) ou sua organização Workspace
   - Clique **CREATE** → aguarde ~10s
3. Selecione o projeto recém-criado no seletor (importante — caso contrário cria tudo no projeto errado)
4. Menu hambúrguer → **APIs & Services** → **Library**
5. Procure **Google Sheets API** → clique → **Enable**
6. Procure **Google Drive API** → clique → **Enable** (necessário para o Service Account criar/listar planilhas)
7. Menu hambúrguer → **IAM & Admin** → **Service Accounts**
8. **+ CREATE SERVICE ACCOUNT:**
   - **Service account name:** `n8n-helpsphere-sheets`
   - **Service account ID:** preenchido automático (`n8n-helpsphere-sheets@apex-helpsphere-lab.iam.gserviceaccount.com`)
   - **Description:** `Conta de serviço para n8n escrever na planilha de auditoria HelpSphere`
   - Clique **CREATE AND CONTINUE**
9. **Grant this service account access to project:** pule (clique **CONTINUE** sem adicionar role — não precisamos de role no projeto Google, só compartilhamento direto na planilha)
10. **Grant users access to this service account:** pule → **DONE**

**Gerar JSON key (credential):**

1. Lista de Service Accounts → clique em `n8n-helpsphere-sheets@...`
2. Tab **KEYS** → **ADD KEY** → **Create new key**
3. **Key type:** `JSON`
4. **CREATE** — download automático de arquivo `apex-helpsphere-lab-<random>.json` (~2KB)
5. **Anote o email da Service Account** (formato `n8n-helpsphere-sheets@apex-helpsphere-lab.iam.gserviceaccount.com`) — vai compartilhar a planilha com ele no próximo step

<!-- screenshot: cap08-passo8.5-gcp-service-account-json-key.png -->

**Criar planilha Google + compartilhar:**

1. Abra `https://sheets.google.com` → **Blank spreadsheet**
2. Nomeie: `Apex IA - Auditoria de Escalações HelpSphere`
3. Linha 1 (header) — preencha as 7 colunas:
   ```
   timestamp | ticket_id | severity | category | persona | summary | escalated_by
   ```
4. Top-direita → **Share**:
   - **Add people and groups:** cole o email da Service Account (`n8n-helpsphere-sheets@apex-helpsphere-lab.iam.gserviceaccount.com`)
   - **Permission:** `Editor`
   - **Notify people:** ❌ **uncheck** (Service Accounts não recebem email)
   - **Send / Share** → confirme
5. Anote o **Sheet ID** da URL: `https://docs.google.com/spreadsheets/d/<SHEET_ID>/edit#gid=0`
   - **SHEET_ID** = a string entre `/d/` e `/edit` (ex.: `1aB3cD4eF5gH6iJ7kL8mN9oP0qR1sT2uV3wX4yZ5`)

<!-- screenshot: cap08-passo8.5-planilha-criada-compartilhada.png -->

**Configurar credential Google Sheets no n8n:**

1. n8n UI → **Credentials** → **+ Add credential** → procure `Google Sheets` → selecione **Google Sheets Service Account**
2. Preencher:
   - **Credential Name:** `Google Sheets Service Account`
   - **Email:** cole o email da Service Account (`n8n-helpsphere-sheets@apex-helpsphere-lab.iam.gserviceaccount.com`)
   - **Private Key:** abra o JSON baixado (`apex-helpsphere-lab-<random>.json`) → copie o valor do campo `private_key` (incluindo `-----BEGIN PRIVATE KEY-----` e `-----END PRIVATE KEY-----` e os `\n` literais) → cole aqui
3. Clique **Save** (n8n não tem `Test connection` para Sheets SA — testaremos no smoke do Passo 8.6)

<!-- screenshot: cap08-passo8.5-credential-sheets-n8n.png -->

**Atualizar node Google Sheets do workflow `Ticket Escalation` (consome `sub-n8n`):**

1. **Workflows** → **Ticket Escalation** → clique no último node **Google Sheets — append row**
2. **Credential:** selecione `Google Sheets Service Account`
3. **Resource:** `Sheet`
4. **Operation:** `Append`
5. **Document:** cole o `SHEET_ID` da URL
6. **Sheet:** `Sheet1` (default do Google Sheets)
7. **Range:** `A:G`
8. **Mapping**: confirme as 7 colunas mapeadas dos campos do JSON da mensagem SB
9. **Save**

**Criar workflow paralelo `Audit Sheets` (consome `sub-sheets`):**

A subscription `sub-sheets` precisa de **workflow próprio** que consume independente da `sub-n8n`. Cria um workflow novo só com 2 nodes (SB Trigger → Sheets Append):

1. **Workflows** → **+ Add workflow** → nomeie `Audit Sheets`
2. Adicione node **Azure Service Bus Trigger**:
   - **Credential:** `HelpSphere Service Bus`
   - **Resource:** `Topic`
   - **Topic:** `ticket-events`
   - **Subscription:** `sub-sheets` ⚠️ ESTA subscription (não `sub-n8n`)
   - **Operation:** `Receive Messages`
   - **Lock duration:** `30`
3. Adicione node **Google Sheets** → **Append row** (idêntico ao do workflow `Ticket Escalation`, mesmas colunas e Sheet ID)
4. Conecte os 2 nodes
5. Toggle **Active** (canto superior direito) → ON
6. **Save**

> **Custo:** R$ 0 — Google Sheets API é **gratuita até 60 reqs/min/projeto** + 300 reqs/min/usuário. Lab gera <10 reqs/dia → free tier eterno.

> **Nota pedagógica — Service Account vs OAuth2 user, qual escolher?** OAuth2 user requer login interativo via browser (refresh token expira em 7 dias se publicação não validada). Service Account é **server-to-server**, sem expiração, mas **só funciona se a planilha for explicitamente compartilhada com o email da SA** (não herda permissões do criador). Para automação 24×7: SA. Para lab/demo de 1 dia: OAuth2 user pode ser mais rápido. Aqui usamos SA para alinhar com pattern produção.

> **Nota pedagógica — por que 2 workflows separados (não 1 com 2 saídas)?** Você poderia teoricamente fazer 1 workflow com `Service Bus Trigger` em `sub-n8n` e adicionar um node Sheets em paralelo ao Teams. **Mas** isso quebra o pattern pub/sub independente: se o node Sheets falhar (API Google fora), o `complete` do Trigger não acontece, a msg fica em lock-duration → reenvio → Teams duplica. Com **2 workflows independentes** em **2 subscriptions independentes**, falha de Sheets afeta SÓ `sub-sheets` (DLQ acumula lá) e Teams continua imune. Architectural separation.

---

## Passo 8.6 — Atualizar `agent_runner.py` para publicar em SB de verdade (placeholder → real)

No Capítulo 04 cravamos a tool `escalate_ticket` com schema mas o handler era **placeholder** que printava no stdout. Aqui fechamos com publicação real no Topic via SDK Python `azure-servicebus`.

**No VS Code, no diretório `agent-code/`:**

1. Atualize `requirements.txt` adicionando:
   ```text
   azure-servicebus==7.12.2
   ```
2. Reinstale no venv:
   ```powershell
   pip install -r requirements.txt
   ```
3. Edite `agent_runner.py` — localize a função `handle_escalate_ticket(args)` (criada no Capítulo 04 com `print` placeholder) e substitua pelo handler real:

```python
# agent-code/func-agent-runner/agent_runner.py (trecho)
import json
import os
from azure.identity import DefaultAzureCredential
from azure.servicebus import ServiceBusClient, ServiceBusMessage

SB_FQDN = os.environ["SB_NAMESPACE_FQDN"]   # sbns-helpsphere-final-<rand>.servicebus.windows.net
SB_TOPIC = os.environ["SB_TOPIC_NAME"]      # ticket-events

def handle_escalate_ticket(args: dict) -> dict:
    """Tool handler — publica msg no Topic SB; SB faz fan-out para sub-n8n + sub-sheets."""
    payload = {
        "ticket_id": args["ticket_id"],
        "severity": args.get("severity", "HIGH"),
        "category": args.get("category", "geral"),
        "persona": args.get("persona", "cliente"),
        "summary": args.get("summary", ""),
        "escalated_by": "helpsphere-tier1-agent",
    }

    cred = DefaultAzureCredential()
    with ServiceBusClient(fully_qualified_namespace=SB_FQDN, credential=cred) as client:
        with client.get_topic_sender(topic_name=SB_TOPIC) as sender:
            msg = ServiceBusMessage(
                body=json.dumps(payload),
                content_type="application/json",
                subject=f"escalation-{payload['ticket_id']}",
            )
            sender.send_messages(msg)

    return {"status": "escalated", "topic": SB_TOPIC, "ticket_id": payload["ticket_id"]}
```

4. Atualize `.env` com as 3 novas variáveis (use o `{rand}` capturado no Cap 02):
   ```text
   SB_NAMESPACE_FQDN=sbns-helpsphere-final-<rand>.servicebus.windows.net
   SB_TOPIC_NAME=ticket-events
   SHEET_ID=<id-da-planilha-google-do-passo-8.5>
   ```
5. **Importante:** `DefaultAzureCredential` cai em `AzureCliCredential` quando você roda local — então precisa **`az login`** com uma conta que tenha **`Azure Service Bus Data Sender`** no namespace. Como o Lab atribuiu Sender a `mi-helpsphere-ia` (não ao seu user), você tem 2 opções:
   - **Opção A — atribua Sender ao seu user também (lab dev local, PowerShell 7):**
     ```powershell
     $Rand = (Get-Content .\.env | Select-String '^RAND=').ToString().Split('=')[1]
     $MyUserId = az ad signed-in-user show --query id -o tsv
     $SbScope = az servicebus namespace show --resource-group rg-lab-final --name "sbns-helpsphere-final-$Rand" --query id -o tsv
     az role assignment create --assignee-object-id $MyUserId --assignee-principal-type User --role "Azure Service Bus Data Sender" --scope $SbScope
     ```
     **Linux/Mac/WSL:** troque `$Var = az ...` por `VAR=$(az ...)` e `$Var` por `"$VAR"`.
   - **Opção B — empacote o agente em ACA (lab seguinte) e use a MI nativa.**

> **Custo:** R$ 0 (operações SB são free até 1M/mês — lab usa <100).

> **Nota pedagógica — `DefaultAzureCredential` chain de fallback:** local dev → `AzureCliCredential` (porque você fez `az login`); em ACA → `ManagedIdentityCredential` (MI atribuída ao container app); em GitHub Actions → `WorkloadIdentityCredential` (federated cred). **Mesmo código** funciona em todos os 3 ambientes. Por isso usamos sempre `DefaultAzureCredential()` em vez de `AzureCliCredential()` direto.

---

## Passo 8.7 — Smoke test end-to-end + pause/delete

**Smoke local — agente Foundry → Topic `ticket-events` → fan-out (`sub-n8n` + `sub-sheets`) → Teams + Sheet:**

1. **Ative o n8n e PG do capítulo anterior se estiverem `Stopped`** (Windows PowerShell 7):
   ```powershell
   $Rand = (Get-Content .\.env | Select-String '^RAND=').ToString().Split('=')[1]
   az postgres flexible-server start --resource-group rg-lab-final --name "pg-n8n-$Rand"
   az containerapp revision activate --resource-group rg-lab-final --name ca-n8n-helpsphere --revision <rev-name>
   ```
   **Linux/Mac/WSL:** troque `$Rand = ...` por `RAND=$(...)` e `$Rand` por `"$RAND"`.
2. Abra n8n UI → **Workflows** → confirme **AMBOS** workflows ativos:
   - `Ticket Escalation` (consome `sub-n8n` → Teams + dispatch) → toggle **Active** ON
   - `Audit Sheets` (consome `sub-sheets` → Google Sheets) → toggle **Active** ON
3. No VS Code, terminal no diretório `agent-code/` com venv ativo (Windows PowerShell 7):
   ```powershell
   python agent_runner.py
   ```
4. Quando o agente perguntar `Qual ticket você precisa?`, responda algo que force escalação:
   ```text
   Cliente reclamando de erro 500 reproduzível em produção, perdeu R$ 50.000 em vendas no Black Friday. Ticket #1042. Quero escalar agora.
   ```
5. Esperado no terminal:
   - Tool call `get_ticket(1042)` → MCP responde
   - Tool call `escalate_ticket(...)` → retorna `{"status": "escalated", "topic": "ticket-events", "ticket_id": 1042}`
   - Resposta do agente: "Escalei o ticket #1042 para a supervisora Marina (categoria: técnico/produção)..."
6. **Validação visual no Portal — Service Bus Explorer:**
   - Namespace `sbns-helpsphere-final-{rand}` → **Service Bus Explorer** → Topic `ticket-events`
   - Tab **Subscriptions** → você vai ver as 2 subscriptions:
     - `sub-n8n` — **Active count: 0** (msg já consumida pelo workflow `Ticket Escalation`)
     - `sub-sheets` — **Active count: 0** (msg já consumida pelo workflow `Audit Sheets`)
   - Se `sub-n8n` ou `sub-sheets` ficar com Active count > 0 por mais de 30s, o workflow correspondente não está rodando — verifique no n8n UI
7. **Validação visual no n8n UI — 2 execuções paralelas:**
   - **Workflows** → **Ticket Escalation** → tab **Executions** → 1 execução verde recente
   - **Workflows** → **Audit Sheets** → tab **Executions** → 1 execução verde recente (timestamp ~mesmo segundo)
8. **No Google Sheets (`Apex IA - Auditoria...`):**
   - Linha nova com colunas preenchidas: `<timestamp atual> | 1042 | HIGH | técnico | cliente | Cliente reclamando... | helpsphere-tier1-agent`
9. **No Teams (canal da supervisora Marina):**
   - Adaptive Card postada com botões `Aceitar` / `Rejeitar` / `Reatribuir`

<!-- screenshot: cap08-passo8.7-smoke-end-to-end-success.png -->

**Pause/delete ao fim da sessão (CRÍTICO — R$ 50/mês fixo enquanto ligado, cobra parado):**

Service Bus Standard **não tem feature `Stop`** (diferente do PG). Duas estratégias:

- **Opção A — `delete-pause-recreate` (recomendada se vai voltar amanhã, PowerShell 7):**
  ```powershell
  $Rand = (Get-Content .\.env | Select-String '^RAND=').ToString().Split('=')[1]
  az servicebus namespace delete --resource-group rg-lab-final --name "sbns-helpsphere-final-$Rand"
  ```
  Deleta o namespace inteiro (R$ 0 a partir daí). Quando voltar, recrie via Passo 8.1 + 8.2 (~3min). **Você perde dead-letter messages acumuladas** mas não perde nada produtivo no lab (n8n workflows + Google Sheet sobrevivem).

- **Opção B — Resource Group delete (se vai pausar ≥7 dias, PowerShell 7):**
  ```powershell
  az group delete --name rg-lab-final --yes --no-wait
  ```
  Deleta TUDO (Service Bus + ACA n8n + PG + ACR + Speech). Cleanup completo do próximo capítulo.

> **Custo:** Opção A = R$ 0 ao deletar, R$ ~3 ao recriar amanhã (provisioning de 1-2min). Opção B = R$ 0 mas re-setup de 30min na volta.

---

## Validação end-to-end

```powershell
$Rand = (Get-Content .\.env | Select-String '^RAND=').ToString().Split('=')[1]
$SbName = "sbns-helpsphere-final-$Rand"

# 1. Service Bus namespace existe e está Standard
az servicebus namespace show `
  --resource-group rg-lab-final `
  --name $SbName `
  --query "{name:name, sku:sku.name, state:provisioningState, status:status}" -o table
# Esperado: sku=Standard, state=Succeeded, status=Active

# 2. Topic ticket-events existe
az servicebus topic show `
  --resource-group rg-lab-final `
  --namespace-name $SbName `
  --name ticket-events `
  --query "{name:name, status:status, maxSizeMb:maxSizeInMegabytes}" -o table

# 3. AMBAS subscriptions existem com config idêntica
az servicebus topic subscription show `
  --resource-group rg-lab-final `
  --namespace-name $SbName `
  --topic-name ticket-events `
  --name sub-n8n `
  --query "{name:name, maxDelivery:maxDeliveryCount, lockDuration:lockDuration}" -o table

az servicebus topic subscription show `
  --resource-group rg-lab-final `
  --namespace-name $SbName `
  --topic-name ticket-events `
  --name sub-sheets `
  --query "{name:name, maxDelivery:maxDeliveryCount, lockDuration:lockDuration}" -o table
# Esperado para AMBAS: maxDelivery=3, lockDuration=PT30S

# 4. 2 role assignments na MI (Receiver + Sender)
$MiId = az identity show --resource-group rg-lab-intermediario --name mi-helpsphere-ia --query principalId -o tsv
az role assignment list `
  --assignee $MiId `
  --query "[?contains(scope, '$SbName')].{role:roleDefinitionName, scope:scope}" -o table
# Esperado: 2 linhas — 'Azure Service Bus Data Receiver' + 'Azure Service Bus Data Sender'

# 5. Smoke da tool escalate_ticket via SB CLI (sem agente — só valida pipeline SB fan-out)
az servicebus topic send `
  --resource-group rg-lab-final `
  --namespace-name $SbName `
  --topic-name ticket-events `
  --body '{"ticket_id":9999,"severity":"HIGH","category":"smoke-test","persona":"validador","summary":"Validacao end-to-end","escalated_by":"validation-script"}'
# Esperado: 1 mensagem entra no Topic → fan-out automático → sub-n8n (Teams) + sub-sheets (planilha)
# Validar visualmente: linha nova na planilha + execução nova em CADA um dos 2 workflows n8n
```

> **Linux/Mac/WSL:** troque `` ` `` (backtick) por `\`, `$Var = az ...` por `VAR=$(az ...)`, e `$Var` por `"$VAR"`.

---

## Checklist final

```text
[ ] Service Bus namespace sbns-helpsphere-final-{rand} criado tier Standard (NÃO Basic)
[ ] Topic ticket-events criado (nome literal — agente Foundry referencia)
[ ] Subscription sub-n8n criada (consume por workflow Ticket Escalation → Teams)
[ ] Subscription sub-sheets criada (consume por workflow Audit Sheets → Google Sheets)
[ ] Lock duration 30s + max-delivery 3 + dead-letter ON em AMBAS subscriptions
[ ] Connection String RootManageSharedAccessKey copiada para credential n8n
[ ] Credential `HelpSphere Service Bus` ativa no n8n (Test connection OK)
[ ] Workflow Ticket Escalation node Service Bus Trigger configurado (Topic ticket-events + Subscription sub-n8n)
[ ] Role Azure Service Bus Data Receiver atribuída a mi-helpsphere-ia (TODO do capítulo anterior fechado)
[ ] Role Azure Service Bus Data Sender atribuída a mi-helpsphere-ia (para agente Foundry)
[ ] Google Cloud Project apex-helpsphere-lab criado, Sheets API + Drive API habilitadas
[ ] Service Account n8n-helpsphere-sheets criada com JSON key baixado
[ ] Planilha Apex IA - Auditoria de Escalações criada com 7 colunas header
[ ] Planilha compartilhada com email da Service Account como Editor
[ ] Credential Google Sheets Service Account configurada no n8n
[ ] Workflow Audit Sheets criado consumindo sub-sheets + node Google Sheets configurado com Sheet ID correto
[ ] agent_runner.py atualizado com handler real (azure-servicebus SDK)
[ ] .env preenchido com SB_NAMESPACE_FQDN + SB_TOPIC_NAME + SHEET_ID
[ ] Role Sender atribuída ao seu user (dev local) ou MI (futuro ACA)
[ ] Smoke end-to-end: agent → Topic ticket-events → fan-out → sub-n8n (Teams Card) + sub-sheets (linha planilha)
[ ] Estratégia pause escolhida e executada ao fim da sessão (delete namespace ou RG inteiro)
```

---

## Surpresas pedagógicas (capturadas em smoke runs)

- ⚠️ **Service Bus Basic NÃO suporta Topics — falha silenciosa no provisionamento** — se você criar namespace Basic e tentar `az servicebus topic create`, recebe `BadRequest: Topics are not supported in basic SKU`. No Portal, o botão **+ Topic** simplesmente não aparece (não há mensagem explicativa). Sempre cravar `--sku Standard` no namespace SB quando o pattern envolve fanout pub/sub. Decisão cravada em [`_disclaimers.md`](./_disclaimers.md) **AMB-4**.
- ⚠️ **Service Bus Standard cobra R$ 50/mês FIXO enquanto ligado — NÃO por mensagem** — diferente de Storage Queues (R$ 0,15 por milhão de operações), Standard é flat-rate. Ligado parado custa o mesmo que ligado processando 1M msg/dia. Em lab típico (cleanup 4-8h por sessão), custo real é **~R$ 5-8 total**. Esquecer o namespace ligado 1 mês inteiro = R$ 50. Pause via Opção A do Passo 8.7 (`namespace delete` + recreate em 3min) zera o custo.
- ⚠️ **Topic + 2 Subscriptions fazem fan-out automático — não precisa código duplicado no agente** — o agente publica 1 vez no `ticket-events`, o Service Bus duplica para `sub-n8n` E `sub-sheets`. Cada subscription tem cursor próprio. Falha em uma não bloqueia a outra. Adicionar `sub-bi` amanhã para Logic App = 1 comando az CLI, zero código novo no agente.
- ⚠️ **`lock-duration < 30s` causa duplicação silent** — se o n8n trigger leva 25s para processar (HelpSphere API + MCP + Teams API encadeados), e a subscription tem lock 15s, o Service Bus reenvia a msg **antes** do n8n confirmar `complete`, e a escalação dispara duas vezes (linha duplicada no Sheet, Adaptive Card duplicado no Teams). **Workaround:** sempre `lock-duration ≥ 30s` no lab. Em produção: medir P99 do workflow e setar 5x.
- ⚠️ **n8n `Azure Service Bus Trigger` ainda NÃO suporta Managed Identity** — issue oficial no repo do n8n aberto há ~2 anos. Por isso usamos **Connection String** mesmo tendo MI com role correta. **Workaround:** dual-stack — Connection String ativa + RBAC paralelo cravado. Quando o PR draft de MI no n8n der merge, trocamos sem mexer em mais nada (RBAC já está lá).
- ⚠️ **Google Service Account NÃO recebe email de share — checkbox padrão é confuso** — quando você compartilha a planilha e deixa **`Notify people`** marcado (default), o Google tenta mandar email para `n8n-helpsphere-sheets@apex-helpsphere-lab.iam.gserviceaccount.com` e dá bounce. Não bloqueia o share, mas polui a inbox do owner com NDR (non-delivery report). **Workaround:** sempre **uncheck Notify** ao compartilhar com Service Account.
- ⚠️ **`private_key` do JSON da Service Account quebra ao colar no n8n se editor remove `\n`** — alguns editores (VSCode com extensão JSON formatadora ativa) quebram a string `\n` literal em quebra de linha real ao colar. n8n esperando `-----BEGIN PRIVATE KEY-----\nAAAA...\n-----END...` falha com `Error: PEM_read_bio_PrivateKey`. **Workaround:** copie o valor da chave **direto do arquivo JSON cru** (Notepad), não passe por VSCode. Ou use o campo dedicado `Service Account JSON file upload` do n8n (se disponível na sua versão).
- ⚠️ **`DefaultAzureCredential` em `agent_runner.py` local falha sem `az login` recente** — `AzureCliCredential` herda token do `az login`, mas se a sessão expirou (>1h), `DefaultAzureCredential` cai em `InteractiveBrowserCredential` e abre o browser do nada no meio do `python agent_runner.py`. Pior: se você rodou `az logout` por engano, falha com `CredentialUnavailableError` cifrado. **Workaround:** rode `az account get-access-token --resource https://servicebus.azure.net` antes do smoke para confirmar token válido.
- ⚠️ **Service Bus Standard NÃO tem feature `Stop` (diferente do PG)** — você não consegue pausar parcialmente; única forma de zerar custo é deletar o namespace e recriar. Workaround: Opção A do Passo 8.7 (`az servicebus namespace delete` + recreate) é rápida (~3min) e zera o custo até a próxima sessão. Detalhes da decisão em [`_disclaimers.md`](./_disclaimers.md) **AMB-4**. Em produção: orçar o R$ 50/mês fixo como custo operacional, ou migrar para queue Storage Account (R$ 1/mês, sem Topics) se Topics não são essenciais.

---

## Gaps para follow-up

- 🔄 **`n8n-workflows/escalation-servicebus-sheets.json` precisa atualização** — o JSON empacotado no repo usa nomenclatura antiga (`topic: "escalations"` + `subscription: "n8n-consumer"`). Trocar para `topic: "ticket-events"` + 2 entradas (`sub-n8n` no workflow `Ticket Escalation` e `sub-sheets` no workflow novo `Audit Sheets`). Workaround atual: Passos 8.3 + 8.5 instruem aluno a editar no n8n UI direto (sobrescreve o JSON).
- 🔄 **Adaptive Card payload do node Microsoft Graph (Teams)** — o JSON do workflow tem placeholder. Cravar payload real com botões `Aceitar`/`Rejeitar`/`Reatribuir` que façam PATCH de volta no HelpSphere.
- 🔄 **Dead-letter alerting** — lab não cria alerta Application Insights na DLQ depth de `sub-n8n` ou `sub-sheets`. Production-grade: cravar no Lab Avançado.

---

## Próximo capítulo

[09 — Cleanup Obrigatório](./09-cleanup-obrigatorio.md)
