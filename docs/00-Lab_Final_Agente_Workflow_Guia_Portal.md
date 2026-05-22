# Lab Final — Agente Autônomo + Workflow de Escalação
## Guia Passo-a-Passo no Azure Portal

> **Slides cobertos:** #25-#33 + #34-#38 (Blocos 4 + 5 — Agentes + Automação)
>
> **Disciplina 06** · **Lab 2 de 3** · **Duração estimada:** 9 horas · **Modalidade:** gravada · **Version-anchor:** Q2-2026
>
> **Cenário:** o RAG do Lab Intermediário cobre cerca de 40% dos tickets simples. Para chegar em 70%+ de auto-resolução, construímos agente híbrido (Copilot Studio + Foundry Agent Service) com tools, MCP, canal de voz, e workflow de escalação humana via n8n self-hosted em Azure Container Apps.

---

> ## ⚠️ CUSTO E FREE TRIAL
> | Item | Valor |
> |------|-------|
> | Custo mensal (recursos deixados rodando) | ~R$ 380/mês |
> | **Custo realista do lab (provisionar e deletar no mesmo dia)** | **R$ 22-30 saindo do bolso** |
> | Compatível com Free Trial USD 200? | **NÃO** — Foundry Agent Service + ACA exigem Pay-As-You-Go |
> | Custo se esquecer ligado 1 mês | R$ 380+/mês (ACA mais Speech rateado) |
>
> **Atenção especial:** Copilot Studio licenciamento separado — ver Passo 2.0. Para o lab, usaremos trial 30 dias gratuito do Copilot Studio.

---

## Pré-requisitos

- ✅ Lab Intermediário concluído (entendimento de RAG, Function App, métricas)
- ✅ `rg-lab-intermediario` ainda existindo com Foundry Hub
- ✅ Quota Azure OpenAI com `gpt-4.1-mini` deployado (do Lab Intermediário) ou re-deploy neste lab
- ✅ Conta Microsoft 365 com permissão de criar agentes em Copilot Studio (ou trial 30 dias)
- ✅ Permissão para criar Service Principal e App Registration em Entra ID
- ✅ Docker Desktop instalado (para build da imagem MCP local antes do push para ACR)
- ✅ VS Code com extensão Azure Container Apps

### Recursos pré-prontos disponíveis (não implementar)

Esta disciplina entrega 2 componentes pré-prontos. Você **NÃO implementa** — apenas configura e usa:

1. **MCP Server HelpSphere** (`mcp-server/`)
   - Python + FastMCP + ACA-ready
   - Imagem Docker pública: `tftecr.azurecr.io/mcp-helpsphere:v1.0`
   - 4 tools: `get_ticket`, `list_tickets`, `add_comment`, `update_status`

2. **Workflow de escalação n8n** (`n8n-workflows/escalation-servicebus-sheets.json`)
   - Importável no n8n após provisão
   - 7 nodes determinísticos

### 🔗 Repositório companion (estado finalizado do Lab Final)

> **GitHub:** [`apex-helpsphere-agente-lab`](https://github.com/tftec-guilherme/apex-helpsphere-agente-lab) — repo público com código completo do agente + MCP server + workflows n8n + Speech config + tests. Use para:
>
> - **Fork-and-adapt** após completar o lab (substitua secrets pelos seus, faça `azd up`)
> - **Consulta** durante o lab quando travar em algum Passo
> - **Referência** do estado final esperado (compare com seu progresso)
>
> ⚠️ Este repo é um **scaffold inicial** (`v0.1.0-init`) — código completo será preenchido durante a gravação dos Blocos do Lab Final.

---

## Tabela de recursos que serão criados

| Recurso | Nome canônico | SKU/Tier | Custo mensal | Custo no lab |
|---|---|---|---|---|
| Resource Group | `rg-lab-final` | N/A | Gratuito | — |
| **Copilot Studio Agent** | `cps-helpsphere-tier1` | Trial 30 dias OR Premium licença | R$ 90/usuário (após trial) | gratuito (trial) |
| **Foundry Agent Service** | (no Project `aifproj-helpsphere-agente`) | gpt-4.1-mini consumption | varia | R$ 5-8 |
| Azure OpenAI deployment | `gpt-4.1-mini` (re-deploy ou compartilhado) | 30K TPM | varia | já contado no Lab Inter |
| Azure AI Speech | `spch-helpsphere` | S0 Standard | pago por uso | R$ 2-3 |
| ACA Environment | `cae-helpsphere-final` | — | R$ 0 (ambiente) | — |
| ACA n8n | `ca-n8n-helpsphere` | 0.5 vCPU, 1 Gi RAM, scale 0-1 | ~R$ 80 | R$ 3-4 |
| ACA MCP Server | `ca-mcp-helpsphere` | 0.5 vCPU, 1 Gi RAM, scale 0-1 | ~R$ 80 | R$ 3-4 |
| Azure Container Registry | `acrhelpsphere{rand}` | Basic | ~R$ 25 | R$ 1 |
| Azure Database PostgreSQL | `pg-n8n-{rand}` | Burstable B1ms | ~R$ 75 | R$ 3 |
| Service Bus | `sb-helpsphere-final` | Standard | ~R$ 55 | R$ 2 |
| Application Insights (compartilhado) | `ai-helpsphere-rag` (do Lab Inter) | Workspace-based | já criado | — |
| Entra App Registration MCP | `app-mcp-helpsphere-client` | — | gratuito | — |
| **Total** | | | **~R$ 380/mês ligado** | **R$ 22-30 lab realista** |

---

## Diagrama da arquitetura

```mermaid
flowchart TB
    subgraph User["Diego abre ticket no HelpSphere"]
        DIEGO[Diego no Teams<br/>ou voz no telefone]
    end

    subgraph Channels["Canais de entrada"]
        TEAMS[Microsoft Teams<br/>Copilot Studio channel]
        VOICE[Telefone<br/>Speech STT/TTS]
    end

    subgraph CopilotStudio["Front-end conversacional"]
        CS[Copilot Studio<br/>cps-helpsphere-tier1<br/>Topics + Generative AI]
    end

    subgraph Foundry["Back-end de agente"]
        FA[Foundry Agent Service<br/>helpsphere-tier1-agent<br/>gpt-4.1-mini + tools]

        subgraph Tools["Tools do agente"]
            T1[Tool: search_kb<br/>chama Lab Intermediário]
            T2[Tool: MCP HelpSphere<br/>get/list/comment/update]
            T3[Tool: classify_intent]
            T4[Tool: estimate_confidence]
        end
    end

    subgraph MCP["MCP Server pré-pronto"]
        MCPSERVER[ca-mcp-helpsphere<br/>FastMCP em ACA<br/>Bearer Entra OAuth]
    end

    subgraph Speech["Serviços de áudio"]
        SPEECH[Azure AI Speech<br/>spch-helpsphere<br/>STT + TTS]
    end

    subgraph Workflow["Automação de negócio"]
        SB[Service Bus<br/>queue: ticket-escalations]
        N8N[ca-n8n-helpsphere<br/>n8n self-hosted<br/>workflow 7 nodes<br/>+ notificação Teams]
        SHEETS[Google Sheets<br/>auditoria]
    end

    subgraph Existing["Existentes (Lab Intermediário)"]
        RAG[Function App<br/>func-helpsphere-rag<br/>RAG endpoint]
        HSAPI[HelpSphere API<br/>func-helpsphere-prod]
    end

    subgraph Marina["Supervisora Marina"]
        TEAMS_MARINA[Adaptive Card<br/>no canal Teams]
    end

    DIEGO --> TEAMS
    DIEGO --> VOICE
    VOICE --> SPEECH
    SPEECH --> CS
    TEAMS --> CS
    CS -->|tool: invocar agente| FA
    FA --> T1 --> RAG
    FA --> T2
    T2 --> MCPSERVER
    MCPSERVER --> HSAPI
    FA --> T3
    FA --> T4
    FA -->|confidence < 0.5| SB
    FA -->|response| CS
    CS -->|via TTS| VOICE
    CS --> TEAMS

    SB --> N8N
    N8N -->|GET ticket| HSAPI
    N8N -->|notify Adaptive Card| TEAMS_MARINA
    N8N -->|append| SHEETS
```

---

## Estrutura do lab — 8 partes ao longo de 9 horas

| Parte | Duração | Atividade |
|---|---|---|
| Parte 1 | 15min | Provisionar fundação RG + ACR (ACA Environment foi movido para a Parte 4) |
| Parte 2 | 1.5h | Copilot Studio — agente + topics + canal Teams |
| Parte 3 | 2h | Foundry Agent Service — agent code-first + 4 tools |
| Parte 4 | 1.5h | ACA Environment + RBAC + MCP Server HelpSphere (deploy do pré-pronto em ACA) |
| Parte 5 | 1h | Azure AI Speech — canal de voz |
| Parte 6 | 1.5h | n8n self-hosted em ACA + workflow de escalação |
| Parte 7 | 1h | Service Bus + n8n notificação Teams + Google Sheets connector |
| Parte 8 | 30min | Demo end-to-end com 5 tickets + cleanup |

---

# Parte 1 — Provisionar fundação (30min)

## Passo 1.1 — Criar Resource Group

**No Portal Azure:**

1. Barra superior → buscar **"Resource groups"** → clicar
2. **+ Create**
3. Preencher tab **Basics**:
   - **Subscription:** sua
   - **Resource group:** `rg-lab-final`
   - **Region:** `East US 2`
4. Tab **Tags** (opcional, mas recomendado para cost tracking):
   - `cost-center` = `apex-helpsphere-ia`
   - `environment` = `lab`
   - `application` = `helpsphere-ia`
5. **Review + create** → **Create**
6. Aguardar provisioning ~15s até **Succeeded**

<!-- screenshot: passo-1.1-criar-resource-group-portal.png -->

> **Alternativa via Azure CLI (Linux/Mac/WSL — bash):**
>
> ```bash
> az login
> az group create \
>   --name rg-lab-final \
>   --location eastus2 \
>   --tags cost-center=apex-helpsphere-ia environment=lab application=helpsphere-ia
> ```

## Passo 1.2 — Criar Azure Container Registry

**No Portal Azure:**

1. Barra superior → buscar **"Container registries"** → clicar
2. **+ Create**
3. Preencher tab **Basics**:
   - **Subscription:** sua
   - **Resource group:** `rg-lab-final`
   - **Registry name:** `acrhelpsphere<rand>` (ex.: `acrhelpsphere8a3f2d` — deve ser globalmente único, sem hífen, lowercase, 5-50 chars)
   - **Location:** `East US 2`
   - **Pricing plan:** `Basic`
4. Tab **Authentication**:
   - **Admin user:** `Enabled` (para o lab — em produção use Managed Identity puro)
5. **Review + create** → **Create**
6. Aguardar provisioning ~1-2min até **Succeeded**

<!-- screenshot: passo-1.2-criar-acr-portal.png -->

> **Atenção custo:** ACR Basic cobra ~R$ 25/mês. Delete RG ao final.

> **Por que Basic?** Para o lab é suficiente. Em produção, use Standard ou Premium para geo-replication, content trust, etc.

> **Alternativa via Azure CLI (Linux/Mac/WSL — bash):**
>
> ```bash
> RAND=$(echo $RANDOM | md5sum | head -c 6)
> ACR_NAME="acrhelpsphere${RAND}"
>
> az acr create \
>   --name $ACR_NAME \
>   --resource-group rg-lab-final \
>   --sku Basic \
>   --admin-enabled true
>
> echo "ACR: $ACR_NAME"
> ```

## ✅ Checkpoint Parte 1

- [ ] RG `rg-lab-final` existe
- [ ] ACR `acrhelpsphere{rand}` existe

> **Nota:** o **ACA Environment** (`cae-helpsphere-final`) e o **RBAC AcrPull** da Managed Identity foram movidos para o **início da Parte 4** (Passos 4.4 e 4.5), porque o Portal Azure não permite criar um Container Apps Environment standalone sem associá-lo a um Container App. Criamos os dois juntos do primeiro Container App de fato (MCP Server).

---

# Parte 2 — Copilot Studio agent (1.5h)

## Passo 2.0 — Trial Copilot Studio

Copilot Studio é Power Platform, com licenciamento separado do Azure. Para esta disciplina:

1. Acesse **`copilotstudio.microsoft.com`**
2. Login com sua conta Microsoft 365 (corporativa ou trial)
3. Se primeiro acesso, ativar **30-day free trial**
4. Confirme que está em um environment de **Development** (não Default — Development tem permissões mais soltas)

> **Em produção real:** licenciamento Premium ~R$ 90/usuário/mês ou pay-as-you-go por mensagem. Para PoCs corporativos, trial é suficiente. Discussão detalhada em comitê — material no Apêndice E.

## Passo 2.1 — Criar agent

**No Copilot Studio Maker (copilotstudio.microsoft.com):**

1. Acesse **`https://copilotstudio.microsoft.com`** → entre no environment de **Development**
2. **Create** → **New agent** (a partir do "skeleton")
3. Preencher:
   - **Name:** `HelpSphere Tier 1 Agent`
   - **Description:** `Assistente de tier 1 da Apex HelpSphere — sugere respostas, escala para tier 2 quando necessário.`
   - **Language:** `Portuguese (Brazil)`
   - **Instructions:** (system prompt)
     ```
     Você é o assistente do tier 1 do HelpSphere da Apex Group, central de atendimento.
     Sua função é ajudar atendentes (ex.: Diego) a responder tickets de lojistas e colaboradores internos.

     Regras críticas:
     - Sempre responda em pt-BR a menos que o usuário escreva em outro idioma.
     - Sempre cite a fonte da informação.
     - Se a confidence da sua resposta for menor que 0.5, escale para tier 2.
     - Nunca prometa prazos abaixo de 24h.
     - Se ticket envolver dados pessoais sensíveis, peça redação humana.
     ```
4. **Confirm** para criar
5. Aguardar provisioning ~10-20s até agent abrir no canvas

<!-- screenshot: passo-2.1-criar-copilot-agent.png -->

> **Atenção licença:** Copilot Studio Trial é gratuito 30 dias. Após trial, cobrança ~R$ 90/usuário/mês (Premium) ou pay-as-you-go por mensagem.

## Passo 2.2 — Confirmar Generative mode + Knowledge sources

> **Nota Q2-2026:** novos agentes do Copilot Studio já nascem em **modo Generative por default**. Esse passo é mais **confirmação** do que configuração — provavelmente já está OK.

**No Copilot Studio Maker (agente aberto):**

### Sub-passo 2.2.1 — Confirmar modo Generative

1. Header do agente → ícone **⚙️ Settings** (ou menu **...** → **Settings**)
2. Tab **Generative AI** → seção **"Generative answers"**
3. Verificar:
   - ✅ **"Allow the AI to use general knowledge"** = ligado (= modo Generative free-flowing)
   - ❌ **"Only respond when a topic matches"** = desligado (= NÃO modo Classic)
4. Caminho alternativo: página inicial do agente → card **"Generative AI"** → **Configure**

> Se ambos switches já estão como descrito acima, **não há nada a fazer aqui** — pule pra 2.2.2.

### Sub-passo 2.2.2 — Confirmar Knowledge sources VAZIO

Na mesma página de Generative AI (ou em **Knowledge** no menu lateral, depende da versão UI):

1. Localize a seção **"Knowledge sources"**
2. **Deixe TODOS os toggles desligados / lista vazia.**

> **Por que vazio?** O conhecimento técnico do HelpSphere virá via **Foundry Agent como Tool/Plugin** (Parte 3 + Parte 4 MCP) — não como knowledge source nativo do Copilot Studio. Misturar os 2 mecanismos confunde o routing do agente.

### Sub-passo 2.2.3 — Persistência (não há "Save")

Mudanças em Settings / Generative AI do Copilot Studio Q2-2026 **persistem automaticamente** quando você sai da página. Não procure botão "Save" — não existe mais nessa tela (diferente de Topics, que ainda têm Save explícito).

<!-- screenshot: passo-2.2-generative-ai-mode.png -->

> **Surpresa Q2-2026 catalogada:** UI anterior tinha "Menu lateral → Generative AI" + botão Save explícito. Atual usa **Settings header (⚙️) → Generative AI** + auto-persist. Ver `docs/_disclaimers.md`.

## Passo 2.3 — Criar Topic estruturado para "Saudação"

Topics são fluxos guiados. Criamos um para padronizar saudação inicial.

**No Copilot Studio Maker — agente aberto no canvas:**

1. Menu lateral → **Topics** → **+ New topic** → **Create from blank**
2. Preencher:
   - **Topic name:** `Saudacao_inicial`
   - **Trigger phrases:**
     - `oi`
     - `olá`
     - `bom dia`
     - `boa tarde`
     - `boa noite`
   - **Trigger by message:** `Yes`
3. No canvas do topic, adicionar nodes:
   - **+ Add node** → **Send a message** → texto: `Olá! Sou o assistente do HelpSphere. Em que posso ajudar com seu ticket?`
4. **Save**

<!-- screenshot: passo-2.3-topic-saudacao.png -->

## Passo 2.4 — Criar Topic "Resolver_ticket"

Esse é o topic principal — ele chama o Foundry Agent (criado na Parte 3) via custom action.

**No Copilot Studio Maker — agente aberto no canvas:**

### Sub-passo 2.4.1 — Criar o topic

1. Menu lateral → **Topics** → **+ Add a topic** → **From blank** (em algumas UIs aparece como `+ New topic → Create from blank`)
2. **Topic name** (canto superior esquerdo): `Resolver_ticket`

### Sub-passo 2.4.2 — Configurar o trigger via Description (sem dropdown "Description-based")

A UI Q2-2026 **não tem mais dropdown "Description-based"**. O orquestrador Generative AI usa o campo **Description** do node Trigger automaticamente.

1. No canvas, **clique no primeiro node "Trigger"** (já existe — não precisa adicionar)
2. Painel da direita abre com 2 campos principais:
   - **Phrases:** deixe **VAZIO** (não adicione frases de gatilho)
   - **Description:** cole exatamente:
     ```
     Use este topic quando o usuário descreve um problema ou pergunta sobre um ticket específico do HelpSphere.
     ```
3. Se aparecer dropdown **"Trigger by"** com opções `Phrases` / `Event` / `Activity` → mantenha `Phrases` (mesmo sem frases preenchidas). A **Description** é o que o Generative AI consulta no modo orquestrador.

> **Por que isso funciona:** com o agente em modo **Generative AI** (Passo 2.2), o orquestrador faz **semantic match** da pergunta do usuário contra a `Description` de cada topic. Não precisa de phrases nem dropdown explícito.

### Sub-passo 2.4.3 — Adicionar node "Ask a question"

1. Abaixo do node Trigger, clique no **+** (adicionar node)
2. No menu que abre, procure por **"Ask a question"**:
   - Se não aparecer direto, clique **"See more"** no rodapé do menu OU digite `ask` no campo de busca
3. Selecione **"Ask a question"** → painel direita:
   - **Question:** `Qual o problema do ticket que você precisa de ajuda?`
   - **Identify:** `User's entire response` (dropdown — escolhe a resposta inteira como entidade)
   - **Save response as:** `userQuery` (cria a variável automaticamente)

### Sub-passo 2.4.4 — Adicionar node "Call an action" (placeholder)

1. Abaixo do node "Ask a question", clique no **+** novamente
2. No menu, procure **"Call an action"**:
   - Localização atual: categoria **"Advanced"** OU digite `call` no campo de busca
   - Em algumas UIs aparece agrupado como **"Add a tool"** ou **"Call a Power Automate flow"** — selecione o que tiver `Call an action` ou `tool` no nome
3. **Deixe como placeholder** — não configure a action agora. Será preenchido no **Passo 8.1** (após criar o Foundry Agent na Parte 3 + MCP na Parte 4)

### Sub-passo 2.4.5 — Salvar

1. Botão **Save** (canto superior direito do canvas do topic)
2. Aguarde toast "Topic saved" antes de fechar

<!-- screenshot: passo-2.4-topic-resolver-ticket.png -->

> **Surpresa Q2-2026 catalogada:** UI anterior tinha dropdown explícito **"Trigger: Description-based"** + nodes "Ask a question" / "Call an action" visíveis no menu raiz. Atual usa **campo Description no node Trigger** (orquestrador implícito) + nodes agrupados sob categorias com **"See more"** ou busca. Ver `docs/_disclaimers.md` SUR-CS-Q2-2026-TOPICS.

Volte na Parte 2 após Parte 3 (configurar a Call an action).

## Passo 2.5 — Configurar canal Teams (volte aqui após Parte 3)

> Esse passo **depende** de você ter feito Parte 3 (Foundry Agent) e Parte 4 (MCP) primeiro.

**No Copilot Studio Maker — agente aberto no canvas:**

1. Menu lateral → **Channels**
2. Card **Microsoft Teams** → **+ Add channel**
3. **Confirm** — Copilot Studio gera um App package
4. **Open in Teams admin** → instalar para a organização (admin precisa aprovar) OU para si mesmo via **Test in Teams**
5. Após aprovado/testado, agent fica acessível como bot Teams

<!-- screenshot: passo-2.5-canal-teams.png -->

> **Atenção licença Teams:** instalação org-wide exige role Microsoft 365 Tenant Admin. Para o lab, use **Test in Teams** (sem admin necessário).

## ✅ Checkpoint Parte 2 (parcial — completa após Parte 3)

- [ ] Agent `HelpSphere Tier 1 Agent` criado
- [ ] Generative AI mode ativo
- [ ] Topic `Saudacao_inicial` criado e testado
- [ ] Topic `Resolver_ticket` criado (sem ação ainda)

---

# Parte 3 — Foundry Agent Service (2h)

## Passo 3.1 — Criar Foundry Project dedicado

**No Azure AI Foundry portal (ai.azure.com):**

1. Acesse `https://ai.azure.com` → entre no Hub `aifhub-apex-prod` (criado no Bloco 2)
2. **+ New project**
3. Preencher:
   - **Project name:** `aifproj-helpsphere-agente`
   - **Hub:** `aifhub-apex-prod` (já selecionado)
4. **Create**
5. Aguardar provisioning ~1-2min até project abrir

<!-- screenshot: passo-3.1-criar-foundry-project.png -->

## Passo 3.2 — Confirmar deployment gpt-4.1-mini

**No Azure AI Foundry portal (ai.azure.com):**

1. Entre no Project `aifproj-helpsphere-agente`
2. Menu lateral → **Models + endpoints**
3. Verifique se já existe deployment `gpt-4.1-mini` (compartilhado do Lab Intermediário)
4. Se NÃO existe:
   - **+ Deploy model** → buscar `gpt-4.1-mini` → **Confirm**
   - **Deployment name:** `gpt-4.1-mini`
   - **Deployment type:** `Standard`
   - **Tokens per Minute Rate Limit:** `30K`
   - **Deploy**
   - Aguardar ~1min até **Succeeded**
5. Anote da página do deployment:
   - **Target URI** (endpoint)
   - **Key** (API key)

<!-- screenshot: passo-3.2-confirmar-deployment-gpt41mini.png -->

> **Atenção custo:** `gpt-4.1-mini` cobra por 1M tokens (input + output). Para o lab, R$ 5-8 com cap em 30K TPM.

## Passo 3.3 — Registrar agent no Foundry (via SDK Python)

> **Código já está no repo.** Clone (ou `git pull`) o `apex-helpsphere-agente-lab` e abra `agent-code/create_agent.py`. O arquivo registra o agent no Foundry Agent Service com 4 tools + system prompt — você não digita 122 linhas, só configura e roda. Há **1 TODO marcado** (`SYSTEM_PROMPT`) que você customiza durante o lab.

### Estrutura `agent-code/`

```
agent-code/
├── create_agent.py             # ESTE PASSO — registra agent + 4 tools + SYSTEM_PROMPT (TODO)
├── agent_runner.py             # Passo 3.5 — handlers das tools + event loop
├── requirements.txt            # azure-ai-projects + azure-identity + azure-servicebus + openai + requests
├── README.md
└── func-agent-runner/          # Passo 3.6 — wrapper Function App HTTP
```

### O que `create_agent.py` faz

Chama `client.create_agent()` (SDK `azure-ai-agents` v1 GA) registrando 4 tools com schemas JSON (formato OpenAI function calling):

| Tool | O que faz | Backend |
|------|-----------|---------|
| `search_kb` | Busca no kb corporativo (manuais, FAQs, políticas) com citações + confidence | Function App RAG (Lab Intermediário) |
| `get_ticket` | Recupera ticket completo por ID | MCP Server (Parte 4) |
| `list_similar_tickets` | Tickets resolvidos da mesma categoria | MCP Server (Parte 4) |
| `escalate_ticket` | Dispara workflow n8n com motivo + confidence | Service Bus topic (Parte 7) |

> **TODO pedagógico:** abra o arquivo na seção `SYSTEM_PROMPT` (próximo à linha 95). O texto baseline orienta o agent a usar `search_kb` primeiro, escalar quando `confidence < 0.5`, citar fontes e responder em pt-BR. Customize tom, regras de negócio da HelpSphere fictícia, limite de palavras, SLAs — o que fizer sentido para a turma.

> **Nota SDK:** o Foundry mudou em Q2-2026 para **Foundry Direct Projects**. SDK GA atual: `azure-ai-agents>=1.0.0` + `azure-ai-projects>=2.1.0`. O constructor usa **endpoint URI direto** (formato `https://<hub>.services.ai.azure.com/api/projects/<project>`), NÃO mais a `connection string` legacy `<region>.api.azureml.ms;...` que o SDK preview `1.0.0b9` exigia.

## Passo 3.4 — Setup env vars e rodar

Pegue o **endpoint URI do seu Project** no Portal Foundry (em **ai.azure.com → Project aberto → Project endpoint** na barra lateral). Formato:

```
https://<hub-name>.services.ai.azure.com/api/projects/<project-name>
```

```powershell
cd agent-code
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt

# Endpoint URI do Foundry Direct Project
$env:AI_PROJECT_ENDPOINT = "https://<hub-name>.services.ai.azure.com/api/projects/<project-name>"

# URLs/keys do Lab Intermediário
$env:RAG_FUNCTION_URL = "https://func-helpsphere-rag-{rand}.azurewebsites.net"
$env:RAG_FUNCTION_KEY = "<key>"

# MCP server URL — vamos definir depois da Parte 4. Por enquanto, placeholder:
$env:MCP_SERVER_URL = "https://placeholder"

python create_agent.py
```

Saída:

```
[+] Agent criado: asst_xxxxxxx
    Model: gpt-4.1-mini
    Tools: 4
    Anote esse ID — usado no Copilot Studio (Passo 2.5) e no Function App (Passo 3.6).
```

Anote o `agent.id` (formato `asst_xxxxxxx`) — você vai usar no Copilot Studio E como env var `AGENT_ID` no Function App da próxima parte.

## Passo 3.5 — Handler de tools + event loop

> **Código já está no repo.** Abra `agent-code/func-agent-runner/agent_runner.py`. O arquivo implementa os 4 handlers reais + função `run_agent(thread_id, user_message)` que orquestra o loop completo (user message → tool calls → tool outputs → resposta final). Há **1 TODO marcado** (`ESCALATION_THRESHOLD`).
>
> **Por que dentro de `func-agent-runner/`?** O `func azure functionapp publish` da Parte 3.6 zipa **apenas a pasta atual**. Como o `function_app.py` faz `from agent_runner import ...`, o helper precisa estar lado-a-lado dele. Se o arquivo ficar na pasta pai, o worker Python falha com `ModuleNotFoundError: No module named 'agent_runner'`.

### O que `agent_runner.py` faz

O Passo 3.3 registrou apenas o **schema** das 4 tools. Aqui está a **implementação** de cada uma + o event loop que o agent invoca:

| Função | Conecta em | Lógica resumida |
|--------|-----------|-----------------|
| `tool_search_kb(query, ticket_id)` | RAG Function App | `POST {RAG_URL}/api/search?code={key}` com payload `{query, ticket_id}` → retorna `{suggestion, citations, confidence}` |
| `tool_get_ticket(ticket_id)` | MCP Server | `POST {MCP_URL}/tools/get_ticket` com `Authorization: Bearer {MCP_TOKEN}` |
| `tool_list_similar(category, limit)` | MCP Server | `POST {MCP_URL}/tools/list_tickets` filtrando `status="Resolved"` |
| `tool_escalate(ticket_id, reason, confidence)` | Service Bus topic `escalations` | Publica mensagem JSON; n8n consome (Parte 6/7) |
| `run_agent(thread_id, msg)` | Foundry | Loop: cria run → enquanto `requires_action` → despacha tools → submete outputs → retorna texto final |

### TODO pedagógico — `ESCALATION_THRESHOLD`

Procure por `ESCALATION_THRESHOLD = 0.5` (linha ~36). Esse é o limite abaixo do qual o agent escala automaticamente. Trade-offs para discutir com a turma:

- `0.3` → agente confia mais em si (escala menos, risco maior de resposta ruim)
- `0.5` → baseline equilibrada
- `0.7` → agente cético (escala mais, custo maior em tier 2)

Qual valor faz sentido para a HelpSphere fictícia? Ajuste no arquivo + redeploy no Passo 3.6.

### Smoke local opcional

```powershell
# Ainda em agent-code/ com .venv ativo + env vars setadas + AGENT_ID anotado:
$env:AGENT_ID = "asst_xxxxxxx"
python agent_runner.py
```

Saída esperada: `Thread criada: thread_xxxxxx` + resposta do agent ao prompt de smoke.

## Passo 3.6 — Deploy do runner como Function App

Para integração com Copilot Studio, o runner precisa estar acessível por HTTP. Vamos empacotar como Function App.

> **Código já está no repo.** Abra `agent-code/func-agent-runner/`. A pasta contém os 3 arquivos prontos para `func azure functionapp publish`:

```
agent-code/func-agent-runner/
├── function_app.py     # Wrapper HTTP minimal: POST /agent/chat → run_agent()
├── host.json           # Bundle Functions v4 + Application Insights
└── requirements.txt    # azure-functions + azure-ai-projects + azure-identity + azure-servicebus + openai + requests
```

### O que `function_app.py` faz

Wrapper HTTP enxuto (~25 linhas) que:

1. Recebe `POST /api/agent/chat` com body `{message, thread_id?}`
2. Se `thread_id` vazio, cria uma thread nova no Foundry
3. Chama `run_agent(thread_id, message)` (importado de `agent_runner.py` da pasta pai)
4. Retorna `{thread_id, response}` em JSON

`http_auth_level=FUNCTION` — Copilot Studio precisa do `?code={functionKey}` na URL.

> **Importante:** o `requirements.txt` desta pasta DEVE incluir `azure-servicebus` (o `agent_runner.tool_escalate` usa). Já vem certo no repo.

**Deploy: Criar Function App via Portal Azure**

**No Portal Azure:**

1. Barra superior → buscar **"Function App"** → clicar
2. **+ Create** → escolher hosting plan **Consumption**
3. Preencher tab **Basics**:
   - **Subscription:** sua
   - **Resource group:** `rg-lab-final`
   - **Function App name:** `func-helpsphere-agent-<rand>` (ex.: `func-helpsphere-agent-8a3f2d`)
   - **Runtime stack:** `Python`
   - **Version:** `3.11`
   - **Region:** `East US 2`
   - **Operating System:** `Linux`
4. Tab **Storage**:
   - **Storage account:** selecione um existente OU **Create new** com nome auto-gerado
5. Tab **Networking**: deixe defaults (public)
6. Tab **Monitoring**: deixe Application Insights `Enabled` (auto-criado)
7. **Review + create** → **Create**
8. Aguardar provisioning ~3-5min até **Succeeded**

<!-- screenshot: passo-3.6-criar-function-app-portal.png -->

> **Atenção custo:** Function App Consumption cobra ~R$ 0,50 por milhão de execuções + R$ 0,000016 por GB-segundo. Para o lab é praticamente gratuito.

**Configurar app settings (env vars) via Portal:**

1. Function App `func-helpsphere-agent-<rand>` → menu **Settings** → **Environment variables** → **App settings**
2. **+ Add** cada variável:
   - `AI_PROJECT_ENDPOINT` = `https://<hub>.services.ai.azure.com/api/projects/<project>`
   - `AGENT_ID` = `<asst_xxxxxxx>`
   - `RAG_FUNCTION_URL` = `<URL do Lab Intermediário>`
   - `RAG_FUNCTION_KEY` = `<key>`
   - `MCP_SERVER_URL` = `<a-definir-na-Parte-4>`
   - `MCP_TOKEN` = `<a-definir-na-Parte-4>`
   - `AzureWebJobsFeatureFlags` = `EnableWorkerIndexing` — **obrigatória em Flex Consumption** para o host descobrir o `@app.route` do `function_app.py` (programming model Python v2). Sem ela, deploy completa mas `az functionapp function list` retorna vazio.
3. **Apply** (rolar até o topo) → **Confirm**
4. Aguardar restart ~30s

<!-- screenshot: passo-3.6-app-settings-portal.png -->

**Deploy do código (CLI local — não tem caminho Portal puro):**

```powershell
Set-Location func-agent-runner/
func azure functionapp publish func-helpsphere-agent-<rand> --python
```

> **Linux/Mac/WSL:** troque `Set-Location` por `cd`.

> **Alternativa via Azure CLI (Linux/Mac/WSL — bash, criação do recurso):**
>
> ```bash
> # Criar Function App
> FUNC_AGENT_NAME="func-helpsphere-agent-${RAND}"
> az functionapp create \
>   --name $FUNC_AGENT_NAME \
>   --resource-group rg-lab-final \
>   --runtime python \
>   --runtime-version 3.11 \
>   --consumption-plan-location eastus2 \
>   --storage-account $STORAGE_NAME
>
> # Configurar env vars
> az functionapp config appsettings set \
>   --name $FUNC_AGENT_NAME \
>   --resource-group rg-lab-final \
>   --settings \
>     AI_PROJECT_ENDPOINT="https://<hub>.services.ai.azure.com/api/projects/<project>" \
>     AGENT_ID="<asst_id>" \
>     RAG_FUNCTION_URL="<...>" \
>     RAG_FUNCTION_KEY="<...>" \
>     MCP_SERVER_URL="<a-definir>" \
>     MCP_TOKEN="<a-definir>" \
>     AzureWebJobsFeatureFlags="EnableWorkerIndexing"
>
> # Deploy
> cd func-agent-runner/
> func azure functionapp publish $FUNC_AGENT_NAME --python
> ```

## ✅ Checkpoint Parte 3

- [ ] Project `aifproj-helpsphere-agente` criado
- [ ] Agent `helpsphere-tier1-agent` registrado com 4 tools
- [ ] `agent_runner.py` testado localmente (uma run completa)
- [ ] Function App `func-agent-runner` deployada e acessível

---

# Parte 4 — MCP Server HelpSphere (deploy do pré-pronto) (1h)

> O código fonte do MCP está em `mcp-server/` (do repo `apex-helpsphere-agente-lab` clonado localmente). **Você não implementa** — apenas builda a imagem, deploya em ACA, e configura conexão no agent.

## Passo 4.1 — Estrutura do MCP Server pré-pronto

> **Código já está no repo.** Abra `mcp-server/` (do `apex-helpsphere-agente-lab` clonado). Você não implementa o MCP — apenas builda a imagem, deploya em ACA, e configura conexão no agent. Há **1 TODO marcado** (`ticket_resource`) que você pode customizar.

```
mcp-server/
├── server.py            # FastMCP + 4 tools com @require_scope + 1 resource (TODO em ticket_resource)
├── auth.py              # Validação JWT Entra + decorator require_scope (~55L)
├── helpsphere_db.py     # Wrapper SQL HelpSphere com 4 ops (~90L)
├── Dockerfile           # Base python:3.11-slim + msodbcsql18 + WORKDIR /app + ENTRYPOINT
├── requirements.txt     # fastmcp + pyodbc + pyjwt[crypto] + requests + azure-identity
└── README.md            # Build + deploy ACA + troubleshooting
```

### As 4 tools expostas (`server.py`)

| Tool | Scope Entra requerido | Operação SQL |
|------|----------------------|---------------|
| `get_ticket(ticket_id)` | `helpsphere.tickets.read` | `SELECT ... FROM tickets WHERE id = ?` |
| `list_tickets(status, limit, category?)` | `helpsphere.tickets.read` | `SELECT TOP (?) ... WHERE status = ? [AND category = ?] ORDER BY created_at DESC` |
| `add_comment(ticket_id, comment, author)` | `helpsphere.tickets.write` | `INSERT INTO comments (...)` |
| `update_status(ticket_id, new_status)` | `helpsphere.tickets.write` | `UPDATE tickets SET status = ?, updated_at = SYSUTCDATETIME() WHERE id = ?` |

+ 1 resource `helpsphere://tickets/{ticket_id}` que retorna o ticket serializado (formato customizável via TODO).

### Como `auth.py` valida o token

`@require_scope("helpsphere.tickets.read")` é um decorator que envolve cada tool:

1. Lê o `bearer_token` do contexto MCP
2. Busca a `kid` correta no JWKS endpoint do Entra ID (`login.microsoftonline.com/.../discovery/v2.0/keys`)
3. Valida assinatura RS256 + audience (`EXPECTED_AUDIENCE` env) + issuer (tenant)
4. Confere que `scp` (scopes) do token contém o scope requerido pela tool
5. Se tudo passa → invoca a função real; senão → `PermissionError`

> **TODO pedagógico:** abra `server.py` em `ticket_resource()` (~linha 64). A implementação atual retorna `str(dict)` cru. Sugestões para expandir: incluir últimos N comentários (`helpsphere_db.list_comments`), adicionar SLA metadata por priority, formatar como Markdown.

## Passo 4.2 — Build da imagem Docker

```powershell
Set-Location mcp-server/

# Capturar nome do ACR criado no Passo 1.2 (era acrhelpsphere{rand})
$AcrName = az acr list -g rg-lab-final --query "[0].name" -o tsv

az acr build `
  --registry $AcrName `
  --image mcp-helpsphere:v1 `
  --file Dockerfile `
  .
```

> **Linux/Mac/WSL:** troque `Set-Location` por `cd`, `` ` `` (backtick) por `\` (backslash), e `$AcrName` por `$ACR_NAME`.

Tempo: ~3-5min. Verifique:
```powershell
az acr repository list --name $AcrName --output table
```

Deve listar `mcp-helpsphere`.

## Passo 4.3 — Criar App Registration para auth

**No Portal Azure:**

1. Barra superior → buscar **"Microsoft Entra ID"** → clicar
2. Menu lateral → **App registrations** → **+ New registration**
3. Preencher:
   - **Name:** `app-mcp-helpsphere-server`
   - **Supported account types:** `Accounts in this organizational directory only (Single tenant)`
   - **Redirect URI:** deixar vazio (server-side only)
4. **Register**
5. Anote da **Overview** page:
   - **Application (client) ID** — vamos chamar de `MCP_SERVER_APP_ID`
   - **Directory (tenant) ID**

<!-- screenshot: passo-4.3-app-reg-server-portal.png -->

**Definir Application ID URI:**

1. App reg `app-mcp-helpsphere-server` → menu **Expose an API**
2. **Application ID URI** → **Add** → o Portal pré-preenche `api://<APP_ID>` (GUID anotado no Passo 4.3 step 5) → **Save**

<!-- screenshot: passo-4.3-app-id-uri.png -->

> [!IMPORTANT] **Identifier URI policy — default vs custom**
>
> Tenants Entra ID corporativos (incluindo trial/MSDN) têm **default policy** que bloqueia URIs custom sem domínio verificado. Erro típico se você tentar `api://mcp-helpsphere`:
>
> > Failed to add identifier URI api://mcp-helpsphere. All newly added URIs must contain a tenant verified domain, tenant ID, or app ID, as per the default tenant policy of your organization.
>
> **3 formas aceitas pelo default policy:**
> 1. ✅ **`api://<APP_ID>`** (recomendado — funciona em qualquer tenant, sem setup adicional)
> 2. ✅ **`api://<TENANT_ID>/<custom>`** (ex: `api://12345.../mcp-helpsphere`)
> 3. ✅ **`api://<verified-domain>/<custom>`** (ex: `api://apex.com.br/mcp-helpsphere`, se domínio verificado no tenant)
>
> **Workaround tentador (não recomendado):** setar `requestedAccessTokenVersion=2` no manifest pode relaxar a restrição em alguns tenants, mas depende de policy custom configurada pelo admin — não é portável.
>
> **Decisão deste lab:** usamos `api://<APP_ID>` (forma 1) porque funciona universalmente. Todas as referências `api://mcp-helpsphere` em outros Passos deste guia devem ser substituídas pelo valor `api://<MCP_SERVER_APP_ID>` que você anotou no step 5 acima. Para escopos use `api://<MCP_SERVER_APP_ID>/helpsphere.tickets.read` etc.

**Adicionar scopes:**

1. Ainda em **Expose an API** → **+ Add a scope**
2. Preencher (3 vezes, um por scope):
   - **Scope 1:**
     - Scope name: `helpsphere.tickets.read`
     - Who can consent: `Admins and users`
     - Admin consent display name: `Read tickets`
     - Admin consent description: `Permite ler dados de tickets`
     - State: `Enabled`
     - **Add scope**
   - **Scope 2:** `helpsphere.tickets.write` — display `Write tickets`, descrição `Permite criar/editar tickets`
   - **Scope 3:** `helpsphere.kb.read` — display `Read KB`, descrição `Permite ler base de conhecimento`

<!-- screenshot: passo-4.3-scopes.png -->

> **Alternativa via Azure CLI (Linux/Mac/WSL — bash):**
>
> ```bash
> APP_NAME="app-mcp-helpsphere-server"
>
> # Passo 1: criar app sem identifier-uri (vamos definir depois com api://<APP_ID>)
> APP_OBJECT_ID=$(az ad app create \
>   --display-name $APP_NAME \
>   --query id -o tsv)
>
> APP_ID=$(az ad app show --id $APP_OBJECT_ID --query appId -o tsv)
>
> # Passo 2: setar identifier-uri usando o APP_ID (passa default tenant policy)
> az ad app update --id $APP_OBJECT_ID --identifier-uris "api://$APP_ID"
>
> echo "MCP Server app ID: $APP_ID"
> echo "Identifier URI:   api://$APP_ID"
> ```
>
> **PowerShell equivalente:**
> ```powershell
> $AppName = "app-mcp-helpsphere-server"
> $AppObjectId = az ad app create --display-name $AppName --query id -o tsv
> $AppId = az ad app show --id $AppObjectId --query appId -o tsv
> az ad app update --id $AppObjectId --identifier-uris "api://$AppId"
> Write-Host "MCP Server app ID: $AppId"
> Write-Host "Identifier URI:   api://$AppId"
> ```
>
> (Scopes ainda precisam ser adicionados via Portal — `az ad app` não tem comando direto para `oauth2PermissionScopes`.)

## Passo 4.4 — Criar ACA Environment

> **Nota pedagógica (Q2-2026):** o Portal Azure **não permite** criar um Container Apps Environment standalone sem associar a um Container App. Por isso fazemos a criação do Environment **junto** com o primeiro Container App (Passo 4.6) ou usando o caminho específico **"Container Apps Environments"** (plural) no Marketplace.

**Opção A — via Portal (caminho direto):**

1. Acesse `https://portal.azure.com/#create/Microsoft.ManagedEnvironment` (link direto pro blade do Environment standalone)
2. Preencher tab **Basics**:
   - **Subscription:** sua
   - **Resource group:** `rg-lab-final`
   - **Environment name:** `cae-helpsphere-final`
   - **Region:** `East US 2`
3. Tab **Monitoring**:
   - **Logs destination:** `Azure Log Analytics`
   - **Log Analytics workspace:** selecione `log-helpsphere-ia` do RG `rg-lab-intermediario` (compartilhado, criado no Bloco 2)
4. Tab **Networking**: deixe defaults (managed network, public)
5. **Review + create** → **Create**
6. Aguardar provisioning ~3-5min até **Succeeded**

<!-- screenshot: passo-4.4-criar-aca-environment-portal.png -->

> **Atenção:** o ACA Environment usa o Log Analytics Workspace do `rg-lab-intermediario` (compartilhado, criado no Bloco 2). Se ainda não criou esse RG/workspace, faça o Bloco 2 antes.

**Opção B — via Azure CLI (alternativa mais rápida) — PowerShell:**

```powershell
$WorkspaceId = az monitor log-analytics workspace show `
  --resource-group rg-lab-intermediario `
  --workspace-name log-helpsphere-ia `
  --query customerId -o tsv

$WorkspaceKey = az monitor log-analytics workspace get-shared-keys `
  --resource-group rg-lab-intermediario `
  --workspace-name log-helpsphere-ia `
  --query primarySharedKey -o tsv

az containerapp env create `
  --name cae-helpsphere-final `
  --resource-group rg-lab-final `
  --location eastus2 `
  --logs-workspace-id $WorkspaceId `
  --logs-workspace-key $WorkspaceKey
```

> **Linux/Mac/WSL:** troque `$Var = az ...` por `VAR=$(az ...)`, `` ` `` (backtick) por `\` (backslash), e `$VarName` por `$VAR_NAME` em referências.

**Opção C — durante o Passo 4.6 (Create Container App):** ao escolher o Environment no dropdown, clicar **+ Create new** e preencher inline. Funciona, mas dá menos visibilidade do que aconteceu no Environment standalone.

## Passo 4.5 — Atribuir RBAC AcrPull ao Managed Identity (do Bloco 2)

A Managed Identity `mi-helpsphere-ia` (criada no Bloco 2 em `rg-lab-intermediario`) precisa de role `AcrPull` no ACR `acrhelpsphere{rand}` (criado no Passo 1.2) para que o Container App consiga puxar a imagem privada.

```powershell
$PrincipalId = az identity show `
  --name mi-helpsphere-ia `
  --resource-group rg-lab-intermediario `
  --query principalId -o tsv

$AcrName = az acr list -g rg-lab-final --query "[0].name" -o tsv
$AcrId = az acr show --name $AcrName --resource-group rg-lab-final --query id -o tsv

az role assignment create `
  --assignee $PrincipalId `
  --role AcrPull `
  --scope $AcrId
```

> **Linux/Mac/WSL:** troque `$Var = az ...` por `VAR=$(az ...)` e `` ` `` por `\`.

## Passo 4.6 — Deploy MCP Server em Container App

**No Portal Azure:**

1. Barra superior → buscar **"Container Apps"** → clicar
2. **+ Create** → **Container App**
3. Preencher tab **Basics**:
   - **Subscription:** sua
   - **Resource group:** `rg-lab-final`
   - **Container app name:** `ca-mcp-helpsphere`
   - **Region:** `East US 2`
   - **Container Apps Environment:** `cae-helpsphere-final` (criado no Passo 4.4)
4. Tab **Container**:
   - **Use quickstart image:** `Off`
   - **Image source:** `Azure Container Registry`
   - **Registry:** `acrhelpsphere<rand>.azurecr.io` (criado no Passo 1.2)
   - **Image:** `mcp-helpsphere`
   - **Image tag:** `v1`
   - **CPU and Memory:** `0.5 CPU / 1 Gi memory`
   - **Environment variables:**
     - `HELPSPHERE_SQL_CONNECTION` = `<connection string do HelpSphere SQL>` — **veja a nota abaixo para obter este valor**
     - `AZURE_TENANT_ID` = `<seu tenant ID>` (Portal → Microsoft Entra ID → Overview → Tenant ID, OU `az account show --query tenantId -o tsv`)
     - `EXPECTED_AUDIENCE` = `api://<MCP_SERVER_APP_ID>` (mesmo Application ID URI definido no Passo 4.3 — substitua `<MCP_SERVER_APP_ID>` pelo GUID do app reg)
     - `FASTMCP_STATELESS_HTTP` = `true` (modo stateless — evita 'Session not found' com scale-to-zero; ver nota pedagógica no Passo 4.9)

> **Connection string `HELPSPHERE_SQL_CONNECTION` (AAD + MI — sem senha):**
>
> ```powershell
> # Capturar FQDN do SQL Server do stack apex-helpsphere
> $SqlFqdn = az sql server list -g rg-helpsphere-saas --query "[0].fullyQualifiedDomainName" -o tsv
> ```
>
> Cole no env var `HELPSPHERE_SQL_CONNECTION` (substitua `<FQDN>` pelo output acima):
>
> ```text
> Driver={ODBC Driver 18 for SQL Server};Server=tcp:<FQDN>,1433;Database=helpsphere;Authentication=ActiveDirectoryMsi;Encrypt=yes;
> ```
>
> O Container App autentica via `mi-helpsphere-ia` (anexada no Tab Identity, step 6 acima). A MI já tem grants no DB porque você fez isso no Lab Intermediário.

5. Tab **Ingress**:
   - **Ingress:** `Enabled`
   - **Ingress traffic:** `Accepting traffic from anywhere`
   - **Target port:** `8080`
6. Tab **Identity**:
   - **User-assigned managed identity:** **+ Add** → selecionar `mi-helpsphere-ia` (do RG `rg-lab-intermediario`, criado no Bloco 2)
7. Tab **Scaling**:
   - **Min replicas:** `0`
   - **Max replicas:** `1`
8. **Review + create** → **Create**
9. Aguardar provisioning ~2-3min até **Succeeded**

<!-- screenshot: passo-4.4-deploy-aca-mcp-portal.png -->

> **Atenção custo:** ACA cobra ~R$ 80/mês com scale-to-zero. No lab realista (provisiona+deleta no dia), R$ 3-4.

**Após criado, anotar URL:**

1. Container app `ca-mcp-helpsphere` → **Overview**
2. Anote **Application Url** (formato `https://ca-mcp-helpsphere.<region-fqdn>.azurecontainerapps.io`) — vamos chamar de `MCP_URL`
3. URL completa do MCP endpoint: `${MCP_URL}/mcp`

<!-- screenshot: passo-4.4-mcp-url-anotar.png -->

> **Alternativa via Azure CLI (Linux/Mac/WSL — bash):**
>
> ```bash
> HELPSPHERE_SQL_CONN="<connection-string-do-HelpSphere-SQL>"
>
> az containerapp create \
>   --name ca-mcp-helpsphere \
>   --resource-group rg-lab-final \
>   --environment cae-helpsphere-final \
>   --image $ACR_NAME.azurecr.io/mcp-helpsphere:v1 \
>   --target-port 8080 \
>   --ingress external \
>   --registry-server $ACR_NAME.azurecr.io \
>   --registry-identity $(az identity show -n mi-helpsphere-ia -g rg-lab-intermediario --query id -o tsv) \
>   --user-assigned $(az identity show -n mi-helpsphere-ia -g rg-lab-intermediario --query id -o tsv) \
>   --env-vars \
>     HELPSPHERE_SQL_CONNECTION="$HELPSPHERE_SQL_CONN" \
>     AZURE_TENANT_ID="<seu-tenant-id>" \
>     EXPECTED_AUDIENCE="api://mcp-helpsphere" \
>     FASTMCP_STATELESS_HTTP="true" \
>   --min-replicas 0 \
>   --max-replicas 1 \
>   --cpu 0.5 \
>   --memory 1Gi
>
> MCP_URL=$(az containerapp show \
>   --name ca-mcp-helpsphere \
>   --resource-group rg-lab-final \
>   --query "properties.configuration.ingress.fqdn" -o tsv)
>
> echo "MCP Server URL: https://$MCP_URL/mcp"
> ```

## Passo 4.7 — Criar App Registration cliente (para o agent autenticar)

**No Portal Azure:**

1. Barra superior → buscar **"Microsoft Entra ID"** → clicar
2. Menu lateral → **App registrations** → **+ New registration**
3. Preencher:
   - **Name:** `app-mcp-helpsphere-client`
   - **Supported account types:** `Accounts in this organizational directory only (Single tenant)`
   - **Redirect URI:** deixar vazio (client-credentials flow only)
4. **Register**
5. Anote da **Overview** page:
   - **Application (client) ID** — vamos chamar de `CLIENT_APP_ID`

<!-- screenshot: passo-4.5-app-reg-client-portal.png -->

**Criar Client Secret:**

1. App reg `app-mcp-helpsphere-client` → menu **Certificates & secrets** → tab **Client secrets**
2. **+ New client secret**
3. Preencher:
   - **Description:** `mcp-client-secret-lab`
   - **Expires:** `90 days` (ou `12 months` se quiser reutilizar)
4. **Add**
5. **IMPORTANTE:** copie o **Value** (NÃO o Secret ID) IMEDIATAMENTE — só aparece uma vez. Vamos chamar de `CLIENT_SECRET`.

<!-- screenshot: passo-4.5-client-secret.png -->

**Adicionar API permissions:**

1. App reg `app-mcp-helpsphere-client` → menu **API permissions** → **+ Add a permission**
2. Tab **My APIs** → selecionar `app-mcp-helpsphere-server`
3. **Delegated permissions** (ou **Application permissions** se for client-credentials puro — para o lab, ambos funcionam):
   - Marcar `helpsphere.tickets.read`
   - Marcar `helpsphere.tickets.write`
   - Marcar `helpsphere.kb.read`
4. **Add permissions**
5. **Grant admin consent for <tenant>** (botão azul) → **Yes** — status deve virar verde **Granted**

<!-- screenshot: passo-4.5-api-permissions-consent.png -->

> **Alternativa via Azure CLI (Linux/Mac/WSL — bash):**
>
> ```bash
> CLIENT_APP_NAME="app-mcp-helpsphere-client"
> CLIENT_APP_OBJECT_ID=$(az ad app create \
>   --display-name $CLIENT_APP_NAME \
>   --query id -o tsv)
>
> CLIENT_APP_ID=$(az ad app show --id $CLIENT_APP_OBJECT_ID --query appId -o tsv)
>
> # Criar client secret
> CLIENT_SECRET=$(az ad app credential reset \
>   --id $CLIENT_APP_OBJECT_ID \
>   --append \
>   --query password -o tsv)
>
> echo "Client App ID: $CLIENT_APP_ID"
> echo "Client Secret: $CLIENT_SECRET"
> ```
>
> (API permissions + admin consent ainda precisam ser feitos via Portal — fluxo CLI é mais complexo.)

## Passo 4.8 — Obter token de teste

**Antes de testar: ajustar env var stateless no Container App**

O `server.py` que subimos foi atualizado pós-Cap 04 e agora opera em **modo stateless** — ajuste necessário para o smoke funcionar com nosso setup atual (`ca-mcp-helpsphere` com `min-replicas=0`). FastMCP é stateful por default, mantendo a session em memória; quando o ACA desliga o replica (scale-to-zero), a session morre e o próximo request vira `Session not found`. A env var `FASTMCP_STATELESS_HTTP=true` força 1 request = 1 response (sem session), que combina com o cold-start.

**Portal:**

1. Portal → **`ca-mcp-helpsphere`** → menu lateral **Containers** → **Edit and deploy**
2. Selecione o container na lista → aba **Environment variables**
3. Clique **+ Add** → preencha:
   - **Name:** `FASTMCP_STATELESS_HTTP`
   - **Source:** `Manual entry`
   - **Value:** `true`
4. **Save** (cria nova revisão automaticamente)
5. Aguardar **~30s** até a nova revisão ficar **Healthy** (menu **Revisions and replicas** → status verde) antes de seguir

> **Linux/Mac/WSL (bash) — alternativa via Azure CLI:**
> ```bash
> az containerapp update \
>   --name ca-mcp-helpsphere \
>   --resource-group rg-lab-final \
>   --set-env-vars FASTMCP_STATELESS_HTTP=true
> ```
> Aguardar nova revisão Healthy: `az containerapp revision list --name ca-mcp-helpsphere --resource-group rg-lab-final --query "[?properties.active].{name:name, healthy:properties.healthState}" -o table`.

Com a nova revisão Healthy, prosseguir com a captura do token:

```powershell
# 🔑 Capture as variáveis (sessão nova? rode este bloco)
# Cole aqui os 3 GUIDs anotados nos Passos 4.3 e 4.7:
$TenantId        = "<paste TENANT_ID anotado no Passo 4.3>"
$McpServerAppId  = "<paste MCP_SERVER_APP_ID anotado no Passo 4.3>"
$ClientAppId     = "<paste CLIENT_APP_ID anotado no Passo 4.7>"
$ClientSecret    = "<paste CLIENT_SECRET anotado no Passo 4.7>"

# (Opcional) capturar TenantId via CLI em vez de paste manual:
# $TenantId = az account show --query tenantId -o tsv

$TokenResponse = curl.exe -s -X POST "https://login.microsoftonline.com/$TenantId/oauth2/v2.0/token" `
  -d "grant_type=client_credentials" `
  -d "client_id=$ClientAppId" `
  -d "client_secret=$ClientSecret" `
  -d "scope=api://$McpServerAppId/.default"

$Token = ($TokenResponse | ConvertFrom-Json).access_token

Write-Host "Token (primeiros 40 chars): $($Token.Substring(0,40))..."
```

> **⚠️ Atenção scope:** o scope no Passo 4.3 ficou `api://<MCP_SERVER_APP_ID>` (forma 1 do default policy). Por isso aqui usamos `api://$McpServerAppId/.default` — NÃO `api://mcp-helpsphere/.default` (esse valor nem foi aceito pelo Entra; ver nota Identifier URI policy no Passo 4.3).

> **Linux/Mac/WSL:** troque `curl.exe` por `curl`, `$Var = curl ...` por `TOKEN=$(curl ... | jq -r .access_token)` (atribuição inline bash + jq), e `` ` `` (backtick) por `\` (backslash). Variáveis equivalentes: `TENANT_ID`, `MCP_SERVER_APP_ID`, `CLIENT_APP_ID`, `CLIENT_SECRET`.

## Passo 4.9 — Testar MCP Server

```powershell
# 🔑 Capture as variáveis (sessão nova? rode este bloco)
$McpUrl = az containerapp show `
  --name ca-mcp-helpsphere `
  --resource-group rg-lab-final `
  --query "properties.configuration.ingress.fqdn" -o tsv

# Se $Token foi perdido (sessão nova após o Passo 4.8), refaça a captura do bloco anterior antes de continuar.
Write-Host "McpUrl: https://$McpUrl/mcp"
if (-not $Token) { Write-Warning "Token vazio — volte ao Passo 4.8 e recapture." }

$Headers = @{
  Authorization  = "Bearer $Token"
  'Content-Type' = 'application/json'
  Accept         = 'application/json, text/event-stream'
}

$ListBody = @{
  jsonrpc = '2.0'
  method  = 'tools/list'
  id      = 1
} | ConvertTo-Json

Invoke-RestMethod -Method Post -Uri "https://$McpUrl/mcp" `
  -Headers $Headers `
  -Body $ListBody
```

> **Atenção — header `Accept` obrigatório:** o MCP **Streamable HTTP transport** (FastMCP) exige `Accept: application/json, text/event-stream` em todo request. Sem isso o servidor retorna **`406 Not Acceptable`** com `{"error":{"code":-32600,"message":"Client must accept both application/json and text/event-stream"}}`. O protocolo permite ao server escolher entre devolver JSON imediato (tool simples) ou stream SSE (tool longa) — daí o duplo Accept.

> **Nota pedagógica — modo stateless (`FASTMCP_STATELESS_HTTP=true`):** o `server.py` chama `FastMCP("helpsphere")` sem kwarg e o modo stateless é ativado pela env var `FASTMCP_STATELESS_HTTP=true` setada no Container App (Passo 4.6). Isso significa **1 request = 1 response**, sem session ID, sem `initialize` handshake prévio, sem `notifications/initialized`. O cliente chama `tools/list` ou `tools/call` direto e pronto. Por que? O Container App roda com `min-replicas=0` (scale-to-zero p/ economizar), e a session in-memory do FastMCP morre quando o replica é desligado — daí o erro `Session not found` em smoke tests intermitentes. **Por que env var e não kwarg?** O FastMCP v2+ removeu `stateless_http` do construtor `FastMCP()` — agora o flag vive na env var OU no `run_http_async()`/`http_app()`. Optamos pela env var: código limpo e o aluno controla pelo Portal sem rebuild de imagem. **Em produção real**, o Foundry SDK (Parte 6) cuida do session management automaticamente quando aplicável; o lab usa stateless por simplicidade e robustez no cold-start. **Trade-off:** stateless inviabiliza tools long-running com progresso incremental ou *sampling* (server pedindo LLM no client) — para o lab, OK.

> **Linux/Mac/WSL:** troque o bloco PowerShell por bash + curl + heredoc:
> ```bash
> curl -X POST "https://${MCP_URL}/mcp" \
>   -H "Authorization: Bearer ${TOKEN}" \
>   -H "Content-Type: application/json" \
>   -H "Accept: application/json, text/event-stream" \
>   -d '{"jsonrpc":"2.0","method":"tools/list","id":1}'
> ```

Saída esperada: lista das 4 tools (`get_ticket`, `list_tickets`, `add_comment`, `update_status`).

Testar uma tool (reaproveita `$Headers` do bloco anterior):
```powershell
$CallBody = @{
  jsonrpc = '2.0'
  method  = 'tools/call'
  params  = @{
    name      = 'get_ticket'
    arguments = @{ ticket_id = 1 }
  }
  id      = 2
} | ConvertTo-Json -Depth 5

Invoke-RestMethod -Method Post -Uri "https://$McpUrl/mcp" `
  -Headers $Headers `
  -Body $CallBody
```

> **Linux/Mac/WSL:** equivalente bash com curl + payload JSON inline (igual ao bloco anterior, mudando `method` para `tools/call` e adicionando `params` — manter o header `Accept: application/json, text/event-stream`).

Deve retornar dados do ticket 1 (do seed do HelpSphere).

## Passo 4.10 — Atualizar Function App `func-agent-runner` com URL e token MCP

```powershell
# 🔑 Capture as variáveis (sessão nova? rode este bloco)
$FuncAgentName = az functionapp list -g rg-lab-final --query "[?starts_with(name, 'func-agent-runner')].name | [0]" -o tsv
$McpUrl        = az containerapp show --name ca-mcp-helpsphere -g rg-lab-final --query "properties.configuration.ingress.fqdn" -o tsv

# $Token vem do Passo 4.8 — se sessão nova, refaça aquele bloco antes.
if (-not $Token) { Write-Warning "Token vazio — volte ao Passo 4.8 e recapture antes de seguir." }

Write-Host "FuncAgentName: $FuncAgentName"
Write-Host "McpUrl:        $McpUrl"

az functionapp config appsettings set `
  --name $FuncAgentName `
  --resource-group rg-lab-final `
  --settings `
    MCP_SERVER_URL="https://$McpUrl" `
    MCP_TOKEN="$Token"
```

> **Linux/Mac/WSL:** troque `$FuncAgentName` por `$FUNC_AGENT_NAME`, `$McpUrl` por `${MCP_URL}`, `$Token` por `${TOKEN}`, e `` ` `` (backtick) por `\` (backslash).

> **Atenção:** o token aqui é estático (válido ~1h). Em produção, o agent renova token via OAuth flow. Para o lab, ok usar token estático e renovar se expirar.

## ✅ Checkpoint Parte 4

- [ ] **ACA Environment `cae-helpsphere-final`** existe e está em estado `Succeeded` (Passo 4.4)
- [ ] **Managed Identity `mi-helpsphere-ia`** tem role `AcrPull` no ACR (Passo 4.5)
- [ ] Imagem `mcp-helpsphere:v1` no ACR
- [ ] App Registration `app-mcp-helpsphere-server` com 3 scopes
- [ ] App Registration `app-mcp-helpsphere-client` com permissões consented
- [ ] ACA `ca-mcp-helpsphere` rodando, URL pública acessível
- [ ] cURL `tools/list` retorna 4 tools
- [ ] cURL `tools/call get_ticket` retorna ticket do banco

---

# Parte 5 — Azure AI Speech (canal de voz) (1h)

## Passo 5.1 — Criar Azure AI Speech

**No Portal Azure:**

1. Barra superior → buscar **"Speech Services"** → clicar
2. **+ Create**
3. Preencher tab **Basics**:
   - **Subscription:** sua
   - **Resource group:** `rg-lab-final`
   - **Region:** `East US 2`
   - **Name:** `spch-helpsphere`
   - **Pricing tier:** `Standard S0`
4. Tab **Network**: deixar `All networks` (default)
5. Tab **Identity**: opcional — habilitar `System assigned` se quiser
6. **Review + create** → **Create**
7. Aguardar provisioning ~30s-1min até **Succeeded**

<!-- screenshot: passo-5.1-criar-speech-portal.png -->

> **Atenção custo:** Speech Standard S0 cobra por uso (~R$ 5 por hora STT, ~R$ 16 por 1M chars TTS). Para o lab, R$ 2-3.

**Anotar credentials:**

1. Recurso `spch-helpsphere` → menu **Resource Management** → **Keys and Endpoint**
2. Anote:
   - `SPEECH_KEY` = **KEY 1**
   - `SPEECH_REGION` = `eastus2`

<!-- screenshot: passo-5.1-keys-endpoint.png -->

> **Alternativa via Azure CLI (Linux/Mac/WSL — bash):**
>
> ```bash
> az cognitiveservices account create \
>   --name spch-helpsphere \
>   --resource-group rg-lab-final \
>   --kind SpeechServices \
>   --sku S0 \
>   --location eastus2 \
>   --yes
> ```

## Passo 5.2 — Atribuir RBAC

Atribui à Managed Identity `mi-helpsphere-ia` (do Bloco 2) o role `Cognitive Services User` no Speech Service, para que a Function `func-agent-runner` consiga chamar STT/TTS via MI sem precisar de key.

```powershell
# 🔑 Capture as variáveis (sessão nova? rode este bloco)
$PrincipalId = az identity show `
  --name mi-helpsphere-ia `
  --resource-group rg-lab-intermediario `
  --query principalId -o tsv

$SpchId = az cognitiveservices account show -n spch-helpsphere -g rg-lab-final --query id -o tsv

Write-Host "PrincipalId: $PrincipalId"
Write-Host "SpchId:      $SpchId"

# Atribui RBAC
az role assignment create --assignee $PrincipalId --role "Cognitive Services User" --scope $SpchId
```

> **Linux/Mac/WSL:** troque `$Var = az ...` por `VAR=$(az ...)` e `$VarName` por `$VAR_NAME`.

## Passo 5.3 — Grave seu próprio áudio (5-10s pt-BR)

Em vez de baixar um WAV pré-pronto, vamos gravar o seu próprio. Por quê? Speech STT é mais convincente quando o aluno ouve sua própria voz sendo transcrita.

**Windows:** abra **Voice Recorder** (busca no Start) → Recorde 5-10s da pergunta: *"Como faço para devolver um produto da Apex Mart?"* → Salve como `sample-question-pt.wav` na pasta do lab.

**macOS:** use **QuickTime Player** → File → New Audio Recording → idem.

**Linux/WSL:** use **Audacity** ou `arecord -d 8 -f cd sample-question-pt.wav`.

**No Portal Azure:** suba o WAV no Speech Service via UI Test → Real-time Speech-to-text → upload audio file → veja a transcrição em pt-BR.

Para testar via CLI:

```powershell
# 🔑 Capture as variáveis Speech (sessão nova? rode este bloco)
$env:SPEECH_REGION = az cognitiveservices account show -n spch-helpsphere -g rg-lab-final --query location -o tsv
$env:SPEECH_KEY    = az cognitiveservices account keys list -n spch-helpsphere -g rg-lab-final --query key1 -o tsv

Write-Host "SPEECH_REGION: $env:SPEECH_REGION"
Write-Host "SPEECH_KEY:    $($env:SPEECH_KEY.Substring(0,8))..."   # mascarado

curl.exe -X POST "https://$env:SPEECH_REGION.stt.speech.microsoft.com/speech/recognition/conversation/cognitiveservices/v1?language=pt-BR" `
  -H "Ocp-Apim-Subscription-Key: $env:SPEECH_KEY" `
  -H "Content-Type: audio/wav" `
  --data-binary "@sample-question-pt.wav"
```

> **Linux/Mac/WSL:** troque `curl.exe` por `curl`, `$env:VAR` por `${VAR}`, `` ` `` por `\`, e `"@file"` por `@file` (sem aspas — em pwsh `@` é splatting operator, precisa estar entre aspas). Capture equivalente em bash:
> ```bash
> export SPEECH_REGION=$(az cognitiveservices account show -n spch-helpsphere -g rg-lab-final --query location -o tsv)
> export SPEECH_KEY=$(az cognitiveservices account keys list -n spch-helpsphere -g rg-lab-final --query key1 -o tsv)
> ```

Saída esperada: transcrição em pt-BR.

## Passo 5.4 — Testar TTS (Text-to-Speech)

```powershell
# 🔑 Capture as variáveis Speech (sessão nova? rode este bloco — se já rodou no 5.3 na mesma sessão, pode pular)
if (-not $env:SPEECH_REGION) {
  $env:SPEECH_REGION = az cognitiveservices account show -n spch-helpsphere -g rg-lab-final --query location -o tsv
  $env:SPEECH_KEY    = az cognitiveservices account keys list -n spch-helpsphere -g rg-lab-final --query key1 -o tsv
  Write-Host "SPEECH_REGION: $env:SPEECH_REGION"
}

$Ssml = @'
<speak version="1.0" xmlns="http://www.w3.org/2001/10/synthesis" xml:lang="pt-BR">
  <voice name="pt-BR-FranciscaNeural">
    Olá, sou a assistente do HelpSphere. Como posso ajudar?
  </voice>
</speak>
'@

$Ssml | Set-Content -Path ssml.xml -Encoding UTF8

curl.exe -X POST "https://$env:SPEECH_REGION.tts.speech.microsoft.com/cognitiveservices/v1" `
  -H "Ocp-Apim-Subscription-Key: $env:SPEECH_KEY" `
  -H "Content-Type: application/ssml+xml" `
  -H "X-Microsoft-OutputFormat: audio-24khz-48kbitrate-mono-mp3" `
  --data-binary "@ssml.xml" `
  --output greeting.mp3
```

> **Linux/Mac/WSL:** troque o here-string PowerShell por heredoc bash (`cat <<EOF ... EOF`), `curl.exe` por `curl`, `$env:VAR` por `${VAR}`, e `` ` `` por `\`. Verifique `${SPEECH_REGION}` antes — se vazio, recapture com o bloco bash do Passo 5.3.

Reproduza o `greeting.mp3` — você deve ouvir a frase.

## Passo 5.5 — Integração com Copilot Studio (canal voz)

Em produção, integraria com Azure Communication Services para receber chamadas. Para o lab demonstramos via API direta — o Copilot Studio chamará a Function no Passo 8.4 (Ticket 4 — caso de voz).

**Você vai executar 5 ações em sequência:**

### Ação 1 — Configurar `SPEECH_KEY` e `SPEECH_REGION` como App Settings da Function

```powershell
# 🔑 Capture as variáveis Speech + Function (sessão nova? rode este bloco)
$env:SPEECH_REGION = az cognitiveservices account show -n spch-helpsphere -g rg-lab-final --query location -o tsv
$env:SPEECH_KEY    = az cognitiveservices account keys list -n spch-helpsphere -g rg-lab-final --query key1 -o tsv
$FuncAgentName     = az functionapp list -g rg-lab-final --query "[?starts_with(name, 'func-agent-runner')].name | [0]" -o tsv

Write-Host "FuncAgentName: $FuncAgentName"
Write-Host "SPEECH_REGION: $env:SPEECH_REGION"

# Configurar App Settings da Function (a rota voice vai ler via os.environ)
az functionapp config appsettings set `
  --name $FuncAgentName `
  --resource-group rg-lab-final `
  --settings SPEECH_REGION="$env:SPEECH_REGION" SPEECH_KEY="$env:SPEECH_KEY"
```

> **Linux/Mac/WSL:**
> ```bash
> export SPEECH_REGION=$(az cognitiveservices account show -n spch-helpsphere -g rg-lab-final --query location -o tsv)
> export SPEECH_KEY=$(az cognitiveservices account keys list -n spch-helpsphere -g rg-lab-final --query key1 -o tsv)
> FUNC_AGENT_NAME=$(az functionapp list -g rg-lab-final --query "[?starts_with(name, 'func-agent-runner')].name | [0]" -o tsv)
> az functionapp config appsettings set --name $FUNC_AGENT_NAME -g rg-lab-final --settings SPEECH_REGION="$SPEECH_REGION" SPEECH_KEY="$SPEECH_KEY"
> ```

### Ação 2 — Abrir `agent-code/func-agent-runner/function_app.py` no editor

Abra o arquivo no Cursor / VS Code / editor de sua preferência. Você vai fazer duas edições (Ações 3 e 4) no mesmo arquivo.

### Ação 3 — Adicionar `import os` e `import requests` no topo do arquivo

No topo de `function_app.py`, após `import json`, adicione as 2 linhas marcadas (`os` é stdlib, `requests` já está no `requirements.txt`):

```python
import json
import os                  # ← adicionar
import requests            # ← adicionar
import azure.functions as func
```

Salve o arquivo.

### Ação 4 — Adicionar a rota `/api/agent/voice` ao final do arquivo

Adicione o bloco abaixo **ao final** de `function_app.py` (depois da rota `chat()` existente):

```python
@app.route(route="agent/voice", methods=["POST"])
def voice(req: func.HttpRequest) -> func.HttpResponse:
    """Recebe áudio WAV → STT → agent → TTS → áudio MP3."""
    from agent_runner import client, run_agent

    audio_bytes = req.get_body()

    # 1) STT — transcrever WAV para texto pt-BR
    stt_response = requests.post(
        f"https://{os.environ['SPEECH_REGION']}.stt.speech.microsoft.com/speech/recognition/conversation/cognitiveservices/v1?language=pt-BR",
        headers={
            "Ocp-Apim-Subscription-Key": os.environ["SPEECH_KEY"],
            "Content-Type": "audio/wav",
        },
        data=audio_bytes,
    )
    transcription = stt_response.json().get("DisplayText", "")

    # 2) Agent — pega resposta do agent runner
    thread = client.threads.create()
    response_text = run_agent(thread.id, transcription)

    # 3) TTS — sintetizar resposta como MP3 pt-BR
    ssml = f"""<speak version="1.0" xmlns="http://www.w3.org/2001/10/synthesis" xml:lang="pt-BR">
        <voice name="pt-BR-FranciscaNeural">{response_text}</voice>
    </speak>"""
    tts_response = requests.post(
        f"https://{os.environ['SPEECH_REGION']}.tts.speech.microsoft.com/cognitiveservices/v1",
        headers={
            "Ocp-Apim-Subscription-Key": os.environ["SPEECH_KEY"],
            "Content-Type": "application/ssml+xml",
            "X-Microsoft-OutputFormat": "audio-24khz-48kbitrate-mono-mp3",
        },
        data=ssml.encode("utf-8"),
    )

    return func.HttpResponse(
        body=tts_response.content,
        mimetype="audio/mpeg",
        status_code=200,
    )
```

Salve o arquivo.

> **Por que `from agent_runner import client, run_agent` dentro da função?**
> Mesma razão do lazy import na rota `chat()` (topo do arquivo): em **Flex Consumption** o indexing inicial roda em modo "placeholder" onde as App Settings ainda não estão expostas. Se `agent_runner` for importado no top-level, o host registra `0 functions found` silenciosamente. Mover `from agent_runner import ...` para dentro do handler garante que o indexing só lê os decorators `@app.route(...)`.

> **Por que `client.threads.create()` (e não a API legada de threads via `client.agents`)?**
> O projeto usa SDK v2 (`azure-ai-agents>=1.0.0` + `azure-ai-projects>=2.1.0`), onde `client.threads.create()` é a API correta. A forma antiga (`create_thread` em `client.agents`) era válida em `azure-ai-projects<1.0.0` (deprecated). Veja a rota `chat()` existente para o pattern.

### Ação 5 — Re-deployar a Function

```powershell
# Re-usa $FuncAgentName capturado na Ação 1 (se mesma sessão).
# Se sessão nova, recapture com:
# $FuncAgentName = az functionapp list -g rg-lab-final --query "[?starts_with(name, 'func-agent-runner')].name | [0]" -o tsv

func azure functionapp publish $FuncAgentName --python
```

> **Linux/Mac/WSL:** troque `$FuncAgentName` por `$FUNC_AGENT_NAME`. Capture: `FUNC_AGENT_NAME=$(az functionapp list -g rg-lab-final --query "[?starts_with(name, 'func-agent-runner')].name | [0]" -o tsv)`.

Output esperado: `Deployment completed successfully` ao final do publish.

> **Validação:** este passo apenas implementa o endpoint. Você vai testá-lo end-to-end no **Passo 8.4 — Ticket 4 (caso de voz)** através do Copilot Studio, que será integrado com a Function no **Passo 8.1**. Por enquanto, basta confirmar que o deploy completou sem erros (`Deployment completed successfully` no output do PowerShell).

## ✅ Checkpoint Parte 5

- [ ] Speech Service `spch-helpsphere` criado
- [ ] STT cURL retornou transcrição em pt-BR
- [ ] TTS cURL gerou MP3 reproduzível
- [ ] Endpoint `/api/agent/voice` deployado

---

# Parte 6 — n8n self-hosted em ACA + workflow (1.5h)

## Passo 6.1 — Criar PostgreSQL para n8n metadata

**No Portal Azure:**

1. Barra superior → buscar **"Azure Database for PostgreSQL flexible servers"** → clicar
2. **+ Create** → **Flexible server**
3. Preencher tab **Basics**:
   - **Subscription:** sua
   - **Resource group:** `rg-lab-final`
   - **Server name:** `pg-n8n-<rand>` (ex.: `pg-n8n-8a3f2d` — globalmente único, lowercase)
   - **Region:** `East US 2`
   - **PostgreSQL version:** `16`
   - **Workload type:** `Development`
   - **Compute + storage:** `Burstable, B1ms (1 vCore, 2 GiB RAM)` — `Configure server` para confirmar
   - **Storage size:** `32 GiB`
   - **Authentication method:** `PostgreSQL authentication only`
   - **Admin username:** `n8nadmin`
   - **Password:** gere senha forte (≥12 chars, com letras+números+símbolos) — anote!
4. Tab **Networking**:
   - **Connectivity method:** `Public access (allowed IP addresses)`
   - **Allow public access from any Azure service:** `Yes` (necessário para ACA n8n acessar)
   - ⚠️ **Em produção:** usar `Private access (VNet)` em vez de public.
5. **Review + create** → **Create**
6. Aguardar provisioning ~5-7min até **Succeeded**

<!-- screenshot: passo-6.1-criar-postgres-portal.png -->

> **Atenção custo:** PostgreSQL B1ms cobra ~R$ 75/mês ligado. No lab realista (provisiona+deleta no dia), R$ 3.

**Criar database `n8n`:**

1. Recurso `pg-n8n-<rand>` → menu **Settings** → **Databases** → **+ Add**
2. **Name:** `n8n` → **Save**

<!-- screenshot: passo-6.1-criar-db-n8n.png -->

**Anote:**
- `PG_HOST` = `pg-n8n-<rand>.postgres.database.azure.com` (página Overview do server)
- `PG_PASSWORD` = senha que você definiu

> **Alternativa via Azure CLI (Linux/Mac/WSL — bash):**
>
> ```bash
> PG_NAME="pg-n8n-${RAND}"
> PG_PASSWORD=$(openssl rand -base64 16)
>
> az postgres flexible-server create \
>   --name $PG_NAME \
>   --resource-group rg-lab-final \
>   --location eastus2 \
>   --admin-user n8nadmin \
>   --admin-password $PG_PASSWORD \
>   --sku-name Standard_B1ms \
>   --tier Burstable \
>   --storage-size 32 \
>   --version 16 \
>   --public-access 0.0.0.0  # demo - em prod use VNet
>
> az postgres flexible-server db create \
>   --resource-group rg-lab-final \
>   --server-name $PG_NAME \
>   --database-name n8n
>
> PG_HOST="${PG_NAME}.postgres.database.azure.com"
> echo "PG: $PG_HOST"
> echo "Password: $PG_PASSWORD"
> ```

## Passo 6.2 — Deploy n8n em ACA

**No Portal Azure:**

1. Barra superior → buscar **"Container Apps"** → clicar
2. **+ Create** → **Container App**
3. Preencher tab **Basics**:
   - **Subscription:** sua
   - **Resource group:** `rg-lab-final`
   - **Container app name:** `ca-n8n-helpsphere`
   - **Region:** `East US 2`
   - **Container Apps Environment:** `cae-helpsphere-final` (criado no Passo 4.4)
4. Tab **Container**:
   - **Use quickstart image:** `Off`
   - **Image source:** `Docker Hub or other registries`
   - **Image type:** `Public`
   - **Registry login server:** `docker.io`
   - **Image and tag:** `n8nio/n8n:1.69.2` (NÃO use `:latest` nem tag curta `:1.6` — ver troubleshooting #4)
   - **CPU and Memory:** `0.5 CPU / 1 Gi memory`
   - **Environment variables:**
     - `DB_TYPE` = `postgresdb`
     - `DB_POSTGRESDB_HOST` = `<PG_HOST>`
     - `DB_POSTGRESDB_DATABASE` = `n8n`
     - `DB_POSTGRESDB_USER` = `n8nadmin`
     - `DB_POSTGRESDB_PASSWORD` = `<PG_PASSWORD>`
     - `DB_POSTGRESDB_SSL_ENABLED` = `true` (força TLS — exigido por Azure PG Flexible Server com `require_secure_transport=on`)
     - `DB_POSTGRESDB_SSL_REJECT_UNAUTHORIZED` = `false` (aceita cert da CA Microsoft sem pinar root CA no container Alpine — lab-only; em prod, montar cert via secret + apontar `DB_POSTGRESDB_SSL_CA`)
     - `N8N_ENCRYPTION_KEY` = `<gerar string aleatória 32 chars base64>` (use `openssl rand -base64 32` localmente)
     - `N8N_HOST` = `0.0.0.0`
     - `N8N_PROTOCOL` = `https`
     - `WEBHOOK_URL` = (vazio — atualizamos abaixo)
     - `GENERIC_TIMEZONE` = `America/Sao_Paulo`
5. Tab **Ingress**:
   - **Ingress:** `Enabled`
   - **Ingress traffic:** `Accepting traffic from anywhere`
   - **Target port:** `5678`
6. Tab **Scaling**:
   - **Min replicas:** `1` (NÃO 0 — ver nota abaixo)
   - **Max replicas:** `1`
7. **Review + create** → **Create**
8. Aguardar provisioning ~3-5min até **Succeeded**

<!-- screenshot: passo-6.2-deploy-n8n-aca-portal.png -->

> **Atenção custo:** ACA n8n com min-replicas 1 cobra ~R$ 80/mês ligado (não faz scale-to-zero). No lab realista, R$ 3-4.

> **Por que `min-replicas 1`?** ACA com `min-replicas 0` faz scale-to-zero. Pra n8n recebendo webhooks de escalação de tickets em produção, scale-to-zero perde mensagens (Service Bus messages chegam enquanto container dorme). Em produção real, use **KEDA Service Bus scaler** com min-replicas 0 mas trigger por queue length. Para este lab, `min-replicas 1` é simples e correto.

**Após criado, anotar URL e atualizar WEBHOOK_URL:**

1. Container app `ca-n8n-helpsphere` → **Overview** → anote **Application Url** (vamos chamar de `N8N_URL`)
2. Menu **Application** → **Containers** → tab **Environment variables** → editar `WEBHOOK_URL` → setar para `https://<N8N_URL>/` → **Save**
3. Container faz restart automático ~30s

<!-- screenshot: passo-6.2-n8n-url-webhook.png -->

> **Alternativa via Azure CLI (Linux/Mac/WSL — bash):**
>
> ```bash
> az containerapp create \
>   --name ca-n8n-helpsphere \
>   --resource-group rg-lab-final \
>   --environment cae-helpsphere-final \
>   --image n8nio/n8n:1.69.2 \
>   --target-port 5678 \
>   --ingress external \
>   --env-vars \
>     DB_TYPE=postgresdb \
>     DB_POSTGRESDB_HOST="$PG_HOST" \
>     DB_POSTGRESDB_DATABASE=n8n \
>     DB_POSTGRESDB_USER=n8nadmin \
>     DB_POSTGRESDB_PASSWORD="$PG_PASSWORD" \
>     DB_POSTGRESDB_SSL_ENABLED=true \
>     DB_POSTGRESDB_SSL_REJECT_UNAUTHORIZED=false \
>     N8N_ENCRYPTION_KEY="$(openssl rand -base64 32)" \
>     N8N_HOST="0.0.0.0" \
>     N8N_PROTOCOL=https \
>     WEBHOOK_URL="" \
>     GENERIC_TIMEZONE="America/Sao_Paulo" \
>   --min-replicas 1 \
>   --max-replicas 1 \
>   --cpu 0.5 \
>   --memory 1Gi
>
> N8N_URL=$(az containerapp show \
>   --name ca-n8n-helpsphere \
>   --resource-group rg-lab-final \
>   --query "properties.configuration.ingress.fqdn" -o tsv)
>
> az containerapp update \
>   --name ca-n8n-helpsphere \
>   --resource-group rg-lab-final \
>   --set-env-vars WEBHOOK_URL="https://${N8N_URL}/"
>
> echo "n8n URL: https://$N8N_URL"
> ```

## Passo 6.3 — Setup inicial n8n

1. Abrir `https://$N8N_URL` no navegador
2. Primeira tela: criar **owner account** (email + password) — guardar bem
3. Pular tutorial inicial

## Passo 6.4 — Importar workflow de escalação

Baixe `escalation-servicebus-sheets.json` (em `n8n-workflows/` do repo clonado).

No n8n:
1. **Workflows** → **+ New** → menu três pontos → **Import from file**
2. Selecionar `escalation-servicebus-sheets.json`
3. Workflow `Ticket Escalation` aparece com 7 nodes:
   - AMQP Trigger (display name "Service Bus Trigger")
   - HTTP Request (GET ticket)
   - PostgreSQL (SELECT similar)
   - Switch (categoria → supervisor)
   - HTTP Request (Microsoft Graph — post Teams)
   - HTTP Request (PATCH HelpSphere status)
   - Google Sheets (append row)

> **Por que AMQP Trigger e nao "Azure Service Bus Trigger"?** O n8n nao tem node first-party para Azure Service Bus — o caminho oficial documentado e usar **AMQP Trigger** (AMQP 1.0, suportado nativamente pelo Service Bus). Ref: issue n8n-io/n8n#12959 + docs.microsoft.com/azure/service-bus-messaging/service-bus-amqp-overview. O display name no canvas continua "Service Bus Trigger" para manter narrativa pedagogica e preservar refs `$('Service Bus Trigger')` em nodes downstream.

## Passo 6.5 — Configurar credentials no n8n

Para cada node, configurar credentials. Cada credential é um secret armazenado por n8n.

**Credential 1: Service Bus** (vamos criar Service Bus na Parte 7 — volte aqui depois)

**Credential 2: HTTP Header Auth (HelpSphere API)**
- Type: HTTP Header Auth
- Name: `helpsphere-api`
- Header: `x-functions-key`
- Value: `<HelpSphere function key>`

**Credential 3: PostgreSQL** (HelpSphere DB)
- Connection settings do banco do HelpSphere

**Credential 4: OAuth2 Microsoft (Graph)**
- Type: OAuth2 API
- Authorization URL: `https://login.microsoftonline.com/{tenant}/oauth2/v2.0/authorize`
- Token URL: `https://login.microsoftonline.com/{tenant}/oauth2/v2.0/token`
- Client ID: novo App Registration `app-n8n-graph`
- Scopes: `ChatMessage.Send User.Read`

**Credential 5: Google Sheets OAuth**
- Connect via OAuth Google (configuração separada — Apêndice F do projeto)

## Passo 6.6 — Editar nodes do workflow

Cada node tem placeholders que você precisa substituir pelos valores reais. Detalhamento dos nodes principais:

**Node 1 — AMQP Trigger (display name "Service Bus Trigger"):**
- Tipo do node: `n8n-nodes-base.amqpTrigger` (NAO `azureServiceBusTrigger` — esse node nao existe no n8n first-party)
- Sink: `ticket-escalations` (Queue) ou `<topic>/Subscriptions/<sub>` (Topic+Subscription)
- Credential: AMQP 1.0 (configurada no Passo 7.3)

**Node 5 — HTTP Request (Microsoft Graph para Teams):**
- Method: POST
- URL: `https://graph.microsoft.com/v1.0/teams/{team-id}/channels/{channel-id}/messages`
- Body (Adaptive Card):
```json
{
  "body": {
    "contentType": "html",
    "content": "🚨 <b>Ticket escalado</b><br/>Ticket: {{ $json.ticket_id }}<br/>Motivo: {{ $json.reason }}<br/>Confidence: {{ $json.confidence }}"
  }
}
```

## Passo 6.7 — Ativar workflow

No canvas do workflow → **Active** toggle (canto superior direito) → ON

## ✅ Checkpoint Parte 6

- [ ] PostgreSQL `pg-n8n-{rand}` rodando
- [ ] ACA `ca-n8n-helpsphere` rodando
- [ ] n8n acessível em URL pública
- [ ] Workflow `Ticket Escalation` importado e ativo

---

# Parte 7 — Service Bus + n8n notificação + Sheets (1h)

## Passo 7.1 — Criar Service Bus namespace

**No Portal Azure:**

1. Barra superior → buscar **"Service Bus"** → clicar
2. **+ Create**
3. Preencher tab **Basics**:
   - **Subscription:** sua
   - **Resource group:** `rg-lab-final`
   - **Namespace name:** `sb-helpsphere-final`
   - **Location:** `East US 2`
   - **Pricing tier:** `Standard`
4. **Review + create** → **Create**
5. Aguardar provisioning ~1-2min até **Succeeded**

<!-- screenshot: passo-7.1-criar-service-bus-namespace.png -->

> **Atenção custo:** Service Bus Standard cobra ~R$ 55/mês ligado. No lab realista, R$ 2.

**Criar Queue `ticket-escalations`:**

1. Namespace `sb-helpsphere-final` → menu **Entities** → **Queues** → **+ Queue**
2. Preencher:
   - **Name:** `ticket-escalations`
   - **Max delivery count:** `3`
   - **Enable dead lettering on message expiration:** `Enabled`
   - Demais campos: defaults
3. **Create**
4. Aguardar criação ~10s

<!-- screenshot: passo-7.1-criar-queue.png -->

**Anotar connection string:**

1. Namespace `sb-helpsphere-final` → menu **Settings** → **Shared access policies**
2. Clicar `RootManageSharedAccessKey`
3. Anote **Primary Connection String** — vamos chamar de `SB_CONN`

<!-- screenshot: passo-7.1-connection-string.png -->

> **Alternativa via Azure CLI (Linux/Mac/WSL — bash):**
>
> ```bash
> SB_NAME="sb-helpsphere-final"
>
> az servicebus namespace create \
>   --name $SB_NAME \
>   --resource-group rg-lab-final \
>   --location eastus2 \
>   --sku Standard
>
> az servicebus queue create \
>   --name ticket-escalations \
>   --namespace-name $SB_NAME \
>   --resource-group rg-lab-final \
>   --max-delivery-count 3 \
>   --enable-dead-lettering-on-message-expiration true
>
> SB_CONN=$(az servicebus namespace authorization-rule keys list \
>   --namespace-name $SB_NAME \
>   --resource-group rg-lab-final \
>   --name RootManageSharedAccessKey \
>   --query primaryConnectionString -o tsv)
>
> echo "Service Bus connection: $SB_CONN"
> ```

## Passo 7.2 — Atualizar Function `func-agent-runner` com SB connection

```powershell
# 🔑 Capture as variáveis (sessão nova? rode este bloco)
$FuncAgentName = az functionapp list -g rg-lab-final --query "[?starts_with(name, 'func-agent-runner')].name | [0]" -o tsv
$SbConn = az servicebus namespace authorization-rule keys list `
  --namespace-name sb-helpsphere-final `
  --resource-group rg-lab-final `
  --name RootManageSharedAccessKey `
  --query primaryConnectionString -o tsv

Write-Host "FuncAgentName: $FuncAgentName"
Write-Host "SbConn (primeiros 60 chars): $($SbConn.Substring(0,60))..."

az functionapp config appsettings set `
  --name $FuncAgentName `
  --resource-group rg-lab-final `
  --settings SB_CONNECTION_STRING="$SbConn"
```

> **Linux/Mac/WSL:** troque `$FuncAgentName` por `$FUNC_AGENT_NAME`, `$SbConn` por `$SB_CONN`, e `` ` `` por `\`. Capture equivalente em bash:
> ```bash
> FUNC_AGENT_NAME=$(az functionapp list -g rg-lab-final --query "[?starts_with(name, 'func-agent-runner')].name | [0]" -o tsv)
> SB_CONN=$(az servicebus namespace authorization-rule keys list --namespace-name sb-helpsphere-final -g rg-lab-final --name RootManageSharedAccessKey --query primaryConnectionString -o tsv)
> ```

## Passo 7.3 — Configurar credential AMQP 1.0 no n8n

> **Atencao — qual credential criar?** O n8n nao tem credential type "Azure Service Bus" first-party. O caminho oficial e **AMQP 1.0** (Service Bus suporta AMQP nativo). Ref: issue n8n-io/n8n#12959.

**Capturar SAS Key e montar URI AMQP (PowerShell):**

```powershell
# 🔑 Capture as variaveis (sessao nova? rode este bloco)
$SbName = "sb-helpsphere-final"
$SbKey = az servicebus namespace authorization-rule keys list `
  --resource-group rg-lab-final `
  --namespace-name $SbName `
  --name RootManageSharedAccessKey `
  --query primaryKey -o tsv
$SbKeyEncoded = [uri]::EscapeDataString($SbKey)
$AmqpUri = "amqps://RootManageSharedAccessKey:$SbKeyEncoded@$SbName.servicebus.windows.net:5671"
Write-Host "URI AMQP capturada (cole no campo Connection URL do n8n): $AmqpUri"
```

> **Diferenca vs SB Connection String comum:** o `RootManageSharedAccessKey` aceito pela credential AMQP usa o **mesmo SAS Key** mas o **formato e diferente**: AMQP usa URI `amqps://user:pass@host:5671` (porta 5671 = AMQPS, TLS); a Connection String classica e `Endpoint=sb://...;SharedAccessKeyName=...;SharedAccessKey=...`. Service Bus aceita os dois protocolos no mesmo namespace.

**No n8n:**

1. Settings → Credentials → New → procurar **AMQP 1.0**
2. **Name:** `HelpSphere Service Bus AMQP`
3. **Connection URL:** cole o `$AmqpUri` capturado acima
4. **Save**

Atualize o Node 1 (display name "Service Bus Trigger" / type `n8n-nodes-base.amqpTrigger`) do workflow para usar essa credential.

## Passo 7.4 — Testar disparo de escalação

Manualmente publique mensagem na queue para testar:
```powershell
# 🔑 Capture as variáveis (sessão nova? rode este bloco)
$SbName = "sb-helpsphere-final"   # nome fixo do Passo 7.1; se você mudou, ajuste

az servicebus queue send-message `
  --namespace-name $SbName `
  --resource-group rg-lab-final `
  --queue-name ticket-escalations `
  --body '{"ticket_id": 1, "reason": "Teste manual de escalação", "confidence": 0.3}'
```

> **Linux/Mac/WSL:** troque `$SbName` por `$SB_NAME` e `` ` `` por `\`. Capture: `SB_NAME="sb-helpsphere-final"`.

Em ~5s, no n8n você deve ver execução do workflow disparada (em **Executions**).

## Passo 7.5 — Google Sheets connector

1. Criar uma planilha Google Sheets vazia: `Apex IA - Auditoria de Escalações`
2. Compartilhar com email da service account Google (ver Apêndice F)
3. Anotar Sheet ID (da URL)
4. No n8n, atualizar node "Google Sheets" do workflow:
   - Sheet ID: o anotado
   - Sheet name: `Sheet1`
   - Operation: Append
   - Columns: timestamp, ticket_id, supervisor, reason, confidence

> **Por que n8n para notificação Teams + Sheets em vez de Logic Apps?** n8n já é o orquestrador deste lab (cap 06) e cobre Microsoft Graph Teams + Google Sheets nativamente em um único workflow visual. Logic Apps Consumption seria viável mas duplicaria infra para ganho zero: 2 plataformas + 2 sets de credenciais + custos adicionais (Consumption fee + storage account). Lab Final fica n8n-first para coerência arquitetural e menor superfície de manutenção.

## ✅ Checkpoint Parte 7

- [ ] Service Bus + queue `ticket-escalations` criados
- [ ] Mensagem teste disparou workflow n8n
- [ ] n8n postou em canal Teams (verificar visualmente no Teams)
- [ ] Linha apareceu na planilha Google

---

## Troubleshooting

8 erros comuns ao executar este Lab Final, com sintomas e fix rápido.

### 1. Copilot Studio knowledge não atualiza após upload

**Sintoma:** Você sobe um PDF/URL como knowledge source no Copilot Studio mas o agente continua respondendo "não sei" ou usando dados antigos.

**Fix:** Aguardar **reindex 5-15 min** após upload. Copilot Studio reindexa knowledge assincronamente. Em **Knowledge** → veja status do source — deve ficar `Ready` (não `Processing`). Se passar 20 min e ainda em `Processing`, remova e re-upload.

### 2. Foundry Agent SDK install fail

**Sintoma:** `pip install azure-ai-projects` falha com erro de version conflict ou `ImportError: cannot import name 'AIProjectClient'`.

**Fix:** Pin versão exata `azure-ai-projects==1.0.0b9` no `requirements.txt` (ver Passo 3.3). Versões `>=1.0.0` resolvem para GA com breaking changes incompatíveis com este lab.

### 3. MCP server não responde

**Sintoma:** cURL para `https://${MCP_URL}/mcp` retorna timeout após 30s, ou `502 Bad Gateway`.

**Fix:** Verificar deploy ACA com:
```powershell
az containerapp logs show --name ca-mcp-helpsphere --resource-group rg-lab-final --follow
```
Causas comuns: container em CrashLoopBackoff (logs mostram exception), `--target-port` errado, ou ingress não configurado como `external`.

### 4. n8n não pulla imagem (`MANIFEST_UNKNOWN`) OU não importa escalation-servicebus-sheets.json

**Sintomas (variam conforme a tag escolhida):**
- Sintoma 1: Container App fica em `Provisioning` infinito ou crash loop com `manifest for n8nio/n8n:1.6 not found: manifest unknown` nos logs.
- Sintoma 2: Container sobe, mas ao fazer **Import from file** no n8n, erro "Invalid workflow format" ou nodes aparecem como `unknown`.

**Causa:** n8n publica no Docker Hub apenas tags `major.minor.patch` (ex.: `1.69.2`, `1.70.0`) — tags curtas estilo `1.6` **nunca existiram**. Usar `:latest` quebra com breaking changes silently.

**Fix:** Pinar tag patch completa publicada. `escalation-servicebus-sheets.json` foi exportado de `n8nio/n8n:1.69.2`. Re-deploy:
```powershell
az containerapp update --name ca-n8n-helpsphere --resource-group rg-lab-final --image n8nio/n8n:1.69.2
```

### 5. n8n não inicia com erro `self-signed certificate` ou `no pg_hba.conf entry / no encryption`

**Sintomas (aparecem em série, conforme você corrige o anterior):**
- Sintoma 1: `Error: self-signed certificate in certificate chain` no boot do container.
- Sintoma 2 (após relaxar verificação de cert): `error: no pg_hba.conf entry for host "<ip>", user "n8nadmin", database "n8n", no encryption`.

**Causa:** Azure Database for PostgreSQL Flexible Server tem `require_secure_transport=on` por padrão (exige TLS) e entrega cert assinado por CA Microsoft, que não está no truststore Alpine da imagem `n8nio/n8n`. O n8n precisa de **duas** envs para conectar com sucesso:

| Env | Valor | Função |
|-----|-------|--------|
| `DB_POSTGRESDB_SSL_ENABLED` | `true` | Força driver `pg` a abrir conexão TLS (sem isso, manda plain TCP e Postgres recusa com "no encryption") |
| `DB_POSTGRESDB_SSL_REJECT_UNAUTHORIZED` | `false` | Aceita cert Azure PG sem pinar root CA Microsoft (lab-only) |

**Fix retroativo (caso já tenha deployado sem essas envs):**

```bash
az containerapp update \
  --name ca-n8n-helpsphere \
  --resource-group rg-lab-final \
  --set-env-vars DB_POSTGRESDB_SSL_ENABLED=true DB_POSTGRESDB_SSL_REJECT_UNAUTHORIZED=false
```

Após restart (~30s), abra `https://<N8N_URL>/setup` — deve aparecer tela "Set up owner account".

**Em produção real:** monte o root CA Microsoft via Container Apps Secrets, aponte `DB_POSTGRESDB_SSL_CA=/path/to/ca.pem` e remova `DB_POSTGRESDB_SSL_REJECT_UNAUTHORIZED=false`.

### 6. Speech STT retorna texto vazio

**Sintoma:** cURL pro endpoint STT retorna `{"DisplayText": "", "RecognitionStatus": "InitialSilenceTimeout"}` mesmo com áudio claro.

**Fix:** WAV deve ser **mono 16kHz PCM 16-bit**. Voice Recorder do Windows grava estéreo 48kHz por padrão. Converter com ffmpeg:
```powershell
ffmpeg -i sample-question-pt.wav -ac 1 -ar 16000 -sample_fmt s16 sample-mono16k.wav
```
Use o arquivo convertido no cURL.

### 7. Teams Webhook 401

**Sintoma:** Node n8n "Microsoft Graph Teams" retorna `401 Unauthorized` ao postar mensagem.

**Fix:** OAuth token expirado ou permissions faltando. No n8n → **Credentials** → editar credential OAuth2 → **Reconnect** (refresh do token). Validar que App Registration tem permissions `ChatMessage.Send` (delegated) e admin consent foi concedido.

### 8. Confidence score sempre 1.0

**Sintoma:** Tool `search_kb` retorna `confidence: 1.0` em 100% das queries, mesmo quando RAG não encontra contexto bom.

**Fix:** Model `temperature=0` produz over-confident scoring. No deployment do `gpt-4.1-mini` (Foundry → Models + endpoints), ajustar inference parameters: `temperature=0.3`, `top_p=0.9`. Re-deploy. Confidence vira distribuição mais realista 0.4-0.95.

---

# Parte 8 — Demo end-to-end com 5 tickets + Cleanup (30min)

## Passo 8.1 — Configurar Copilot Studio com Foundry Agent + MCP

> **⚠️ Pre-flight obrigatório:** antes de adicionar a HTTP action no Copilot Studio, garanta que o Function App `func-helpsphere-agent-<rand>` tem **Managed Identity habilitada + RBAC no Foundry Project**. Sem essas 3 sub-etapas, todo `POST /api/agent/chat` retorna **HTTP 500** com `ClientAuthenticationError: Principal does not have access to API/Operation` (visível no Application Insights). O guia anterior (Passo 3.6) deixou o Function App provisionado mas **sem identity nem RBAC** — corrige-se aqui no Bloco 8 porque é onde o erro aparece (no momento da chamada do Copilot Studio).

### Pre-flight 8.1.A — Habilitar System-Assigned Managed Identity no Function App

**No Portal Azure:**

1. Barra superior → buscar **`func-helpsphere-agent-<rand>`** → clicar
2. Menu **Settings** → **Identity** → aba **System assigned**
3. **Status:** alterar para `On` → **Save** → confirmar `Yes`
4. Aguardar ~10s — vai aparecer **Object (principal) ID** (UUID `xxxxxxxx-xxxx-...`)
5. **Anotar o Object (principal) ID** — usado para troubleshooting (não é o que recebe RBAC neste lab, ver 8.1.B abaixo)

<!-- screenshot: passo-8.1-a-identity-system-assigned.png -->

> **Por que System-Assigned se vamos usar User-Assigned?** Em **Flex Consumption** com User-Assigned MI já atrelada (foi feito no Bloco 4 para o `mi-helpsphere-ia` acessar Storage/ACR), o `DefaultAzureCredential` do SDK Python fica ambíguo sobre qual MI usar e levanta `ManagedIdentityCredential: No managed identity endpoint found` na primeira chamada. Habilitar System-Assigned força o runtime do Flex a injetar as env vars `IDENTITY_ENDPOINT` + `IDENTITY_HEADER` corretamente. A escolha de qual MI usar vem do 8.1.B abaixo.

> **Alternativa via Azure CLI (Linux/Mac/WSL — bash):**
>
> ```bash
> az functionapp identity assign \
>   --name $FUNC_AGENT_NAME \
>   --resource-group rg-lab-final
> ```

### Pre-flight 8.1.B — Setar `AZURE_CLIENT_ID` (desambigua qual MI usar)

A Function App tem **2 Managed Identities** atreladas (System-Assigned habilitada em 8.1.A + User-Assigned `mi-helpsphere-ia` herdada do Bloco 2). O `DefaultAzureCredential` precisa de uma pista explícita sobre qual usar — sem isso, escolhe aleatoriamente e a chain falha.

Capture o `clientId` da User-Assigned MI **antes** de configurar o App Setting:

```powershell
# 🔑 Capture o clientId da User-Assigned mi-helpsphere-ia (sessão nova? rode este bloco)
$ClientId = az identity show `
  --name mi-helpsphere-ia `
  --resource-group rg-lab-intermediario `
  --query clientId -o tsv

Write-Host "ClientId mi-helpsphere-ia: $ClientId"
```

**No Portal Azure:**

1. Function App `func-helpsphere-agent-<rand>` → menu **Settings** → **Environment variables** → aba **App settings**
2. **+ Add**:
   - **Name:** `AZURE_CLIENT_ID`
   - **Value:** `<colar o $ClientId capturado acima>`
3. **Apply** (botão no topo) → **Confirm**
4. Aguardar restart automático ~30s

<!-- screenshot: passo-8.1-b-azure-client-id-appsetting.png -->

> **Alternativa via Azure CLI (Linux/Mac/WSL — bash):**
>
> ```bash
> CLIENT_ID=$(az identity show \
>   --name mi-helpsphere-ia \
>   --resource-group rg-lab-intermediario \
>   --query clientId -o tsv)
>
> az functionapp config appsettings set \
>   --name $FUNC_AGENT_NAME \
>   --resource-group rg-lab-final \
>   --settings AZURE_CLIENT_ID="$CLIENT_ID"
> ```

### Pre-flight 8.1.C — Atribuir role `Foundry User` no PROJECT scope

Mesmo com identity desambiguada, o token gerado precisa ter permissão no **Project** do Foundry (`aifproj-helpshere-rag`) — não basta role na conta AIServices pai. O role correto para data plane do Foundry Agent Service v2 GA é **`Foundry User`** (dataActions `Microsoft.CognitiveServices/*` — cobre `AIServices/agents/*` que o SDK precisa).

> **❌ Não use estes roles** — são legacy e NÃO cobrem as data actions do Foundry Agent Service v2 GA:
> - `Azure AI Developer` (dataActions só cobrem `OpenAI/SpeechServices/ContentSafety/MaaS` — falta `AIServices/agents/*`)
> - `Azure AI Administrator` (control plane apenas, sem data actions)
> - `Cognitive Services User` (não cobre AIServices)
> - "Azure AI User" (**não existe** como role built-in)

Capture o `principalId` da User-Assigned MI:

```powershell
# 🔑 Capture o principalId da User-Assigned mi-helpsphere-ia
$PrincipalId = az identity show `
  --name mi-helpsphere-ia `
  --resource-group rg-lab-intermediario `
  --query principalId -o tsv

Write-Host "PrincipalId mi-helpsphere-ia: $PrincipalId"
```

**No Portal Azure:**

1. Barra superior → buscar **`aihub-apex-prod`** → clicar no recurso (kind = **AIServices**)
2. No painel lateral, expandir **Projects** → clicar em **`aifproj-helpshere-rag`** (entra na página do project)
3. Menu **Resource Management** → **Access control (IAM)**
4. **+ Add** → **Add role assignment**
5. Aba **Role:** procurar e selecionar **`Foundry User`** → **Next**
6. Aba **Members:**
   - **Assign access to:** `Managed identity`
   - **+ Select members** → painel lateral → **Managed identity:** `User-assigned managed identity` → procurar **`mi-helpsphere-ia`** → **Select**
7. **Review + assign** → **Review + assign** (botão final)
8. Aguardar ~30s-60s para propagação RBAC data plane

<!-- screenshot: passo-8.1-c-rbac-foundry-user-project.png -->

> **Atenção scope:** o role TEM que ser no **project** (`aihub-apex-prod/projects/aifproj-helpshere-rag`), não na conta pai (`aihub-apex-prod`). Atribuir na conta pai retorna `Principal does not have access to API/Operation` mesmo com role correta — é o erro mais comum ao seguir docs antigas que mostram só o scope da account.

> **Alternativa via Azure CLI — funciona apenas com REST PUT direto** (o `az role assignment create` retorna `MissingSubscription` falsamente em projects do Foundry, bug do CLI 2.61+):
>
> ```bash
> TOKEN=$(az account get-access-token --query accessToken -o tsv)
> PRINCIPAL_ID=$(az identity show -n mi-helpsphere-ia -g rg-lab-intermediario --query principalId -o tsv)
> SUB_ID=$(az account show --query id -o tsv)
> ROLE_DEF_ID="/subscriptions/${SUB_ID}/providers/Microsoft.Authorization/roleDefinitions/53ca6127-db72-4b80-b1b0-d745d6d5456d"  # Foundry User
> PROJECT_SCOPE="/subscriptions/${SUB_ID}/resourceGroups/rg-lab-intermediario/providers/Microsoft.CognitiveServices/accounts/aihub-apex-prod/projects/aifproj-helpshere-rag"
> RA_NAME=$(python -c "import uuid; print(uuid.uuid4())")
>
> curl -X PUT \
>   "https://management.azure.com${PROJECT_SCOPE}/providers/Microsoft.Authorization/roleAssignments/${RA_NAME}?api-version=2022-04-01" \
>   -H "Authorization: Bearer $TOKEN" \
>   -H "Content-Type: application/json" \
>   -d "{\"properties\":{\"roleDefinitionId\":\"${ROLE_DEF_ID}\",\"principalId\":\"${PRINCIPAL_ID}\",\"principalType\":\"ServicePrincipal\"}}"
> ```

### Pre-flight 8.1.D — Stop + Start (NÃO Restart) no Function App

**Crítico em Flex Consumption:** o botão **Restart** do portal (e `az functionapp restart`) faz apenas **soft restart** — o host reinicia mas workers Python já carregados mantêm o cliente `DefaultAzureCredential` com **token cached**. Mesmo com RBAC novo aplicado, próxima invocação reutiliza o token velho (sem o data action) e falha de novo.

Para forçar cold start completo e descartar credential cache:

**No Portal Azure:**

1. Function App `func-helpsphere-agent-<rand>` → menu **Overview**
2. Botão **Stop** (topo da página) → confirmar → aguardar status `Stopped` (~30s)
3. Botão **Start** → aguardar status `Running` (~30s)
4. Aguardar mais ~30s para o cold start completar (primeira chamada será lenta)

<!-- screenshot: passo-8.1-d-stop-start-flex-consumption.png -->

> **Alternativa via Azure CLI (Linux/Mac/WSL — bash):**
>
> ```bash
> az functionapp stop  --name $FUNC_AGENT_NAME --resource-group rg-lab-final
> sleep 10
> az functionapp start --name $FUNC_AGENT_NAME --resource-group rg-lab-final
> sleep 30
> ```

### Pre-flight 8.1.E — Validar HTTP 200 antes de configurar Copilot Studio

```powershell
# 🔑 Capture function key + URL
$FuncName = "$FUNC_AGENT_NAME"
$FuncKey  = az functionapp keys list --name $FuncName --resource-group rg-lab-final --query functionKeys.default -o tsv

# Test
curl.exe -X POST "https://${FuncName}.azurewebsites.net/api/agent/chat?code=${FuncKey}" `
  -H "Content-Type: application/json" `
  -d '{"message":"oi"}'
```

**Saída esperada (HTTP 200):**

```json
{"thread_id": "thread_xxxxxxxxxxxxxxxxxxxx", "response": "Olá! Como posso ajudar você hoje?"}
```

Se HTTP 500 persistir, abrir **Application Insights** → **Logs** → query:

```kusto
exceptions
| where timestamp > ago(5m)
| where cloud_RoleName == "func-helpsphere-agent-<rand>"
| project timestamp, innermostMessage
| order by timestamp desc
```

Mensagens conhecidas e correção:

| Mensagem | Sub-etapa que faltou |
|----------|----------------------|
| `No managed identity endpoint found` | 8.1.A (habilitar System-Assigned MI) — pode estar habilitada mas worker warm; force Stop+Start (8.1.D) |
| `ManagedIdentityCredential authentication unavailable` ambígua | 8.1.B (`AZURE_CLIENT_ID` não setada ou valor errado) |
| `lacks the required data action 'AIServices/agents/read'` | 8.1.C (role atribuída foi `Azure AI Developer`/`Administrator` em vez de `Foundry User`) |
| `Principal does not have access to API/Operation` | 8.1.C (role correta mas scope na account pai em vez do project) — OU credential cache (faça 8.1.D) |

---

### Configurar HTTP action no Copilot Studio (após 8.1.E retornar HTTP 200)

> Volte agora para o portal Copilot Studio para finalizar a integração.

No agente `HelpSphere Tier 1 Agent`:

1. **Topics** → `Resolver_ticket` → botão **`</> Edit code`** (canto superior direito do editor de topic)
2. Apaga o YAML existente e cola o YAML abaixo (já vem pronto com HTTP action + captura de response em `Topic.agentResponse` + `SendActivity` enviando `response` ao usuário):

```yaml
kind: AdaptiveDialog
modelDescription: Use este topic quando o usuário descreve um problema ou pergunta sobre um ticket específico do HelpSphere.
beginDialog:
  kind: OnRecognizedIntent
  id: main
  intent: {}
  actions:
    - kind: Question
      id: question_T0SNYH
      interruptionPolicy:
        allowInterruption: true

      variable: init:Topic.userQuery
      prompt: Qual o problema do ticket que você precisa de ajuda?
      entity: StringPrebuiltEntity

    - kind: HttpRequestAction
      id: QKUlmL
      method: Post
      url: https://<FUNC_AGENT_NAME>.azurewebsites.net/api/agent/chat
      headers:
        x-functions-key: <FUNCTION_KEY>

      body:
        kind: JsonRequestContent
        content:
          message: =Topic.userQuery

      response: Topic.agentResponse

    - kind: SendActivity
      id: send_agent_response
      activity: "{Topic.agentResponse.response}"

inputType: {}
outputType: {}
```

3. Substituir os 2 placeholders no YAML:
   - `<FUNC_AGENT_NAME>` → nome real da Function App (ex.: `func-helpsphere-agent-final`)
   - `<FUNCTION_KEY>` → function key default (Function App → menu **Functions** → função `chat` → **Function Keys** → copiar `default`)
4. **Save** → **Test** (painel direito)
5. Digite no chat: `Como faço para devolver um produto?` → bot deve responder com texto do agente Foundry (não em silêncio)

> **3 pontos críticos do YAML (não mexer):**
>
> - `message: =Topic.userQuery` (**com `=` no início** — sintaxe Power Fx, sem isso o `Topic.userQuery` vira string literal)
> - `response: Topic.agentResponse` (captura o JSON `{"thread_id":"...","response":"..."}` em variável de topic)
> - `activity: "{Topic.agentResponse.response}"` (acessa o campo `response` do JSON capturado e envia ao usuário)

> **Alternativa designer visual (sem editor YAML):**
>
> 1. **Topics** → `Resolver_ticket` → editar
> 2. Adicionar nó **Question** → variável `userQuery` (String) → prompt "Qual o problema do ticket que você precisa de ajuda?"
> 3. Adicionar nó **Call an action** → **HTTP request (custom)**:
>    - URL: `https://<FUNC_AGENT_NAME>.azurewebsites.net/api/agent/chat`
>    - Method: POST
>    - Headers: `x-functions-key: <FUNCTION_KEY>`
>    - Body: `{"message": "{Topic.userQuery}"}`
>    - **Response data:** ativar → **Save response as:** `agentResponse` (Record) → properties: `thread_id` (String) + `response` (String)
> 4. Adicionar nó **Send a message**: `{Topic.agentResponse.response}`
> 5. **Save** → **Test**

6. Conectar MCP Server diretamente em Copilot Studio → **ver Passo 8.2 abaixo** (precisa de pre-config OAuth no App Registration antes de a UI "Connect to an MCP server" funcionar).

## Passo 8.2 — Configurar OAuth do MCP Connector no Copilot Studio

> **⚠️ Por que este passo existe:** o App Registration `app-mcp-helpsphere-client` (criado no Passo 4.7) foi configurado apenas com o redirect URI do n8n (Passo 6 — `/rest/oauth2-credential/callback`). Quando você tenta **Connect** no Copilot Studio MCP UI, o Entra ID rejeita o OAuth dance com erro genérico (`Encountered internal server error. Correlation Id: xxx`) porque `https://global.consent.azure-apim.net/redirect` não está registrado. Também os 3 scopes do server (`helpsphere.kb.read`, `helpsphere.tickets.read`, `helpsphere.tickets.write`) precisam de **admin consent** no tenant para o connector poder pedi-los em nome do bot.

> **Esclarecimento sobre `azure-apim.net`:** apesar do nome, `https://global.consent.azure-apim.net/redirect` é um **endpoint global SaaS da Microsoft para Power Platform connectors** (Copilot Studio, Logic Apps, Power Automate). **Não é o Azure API Management** que você provisiona — é gerenciado pela MS e não tem custo nem provisioning.

### Passo 8.2.A — Adicionar redirect URIs do Copilot Studio ao App Registration cliente

**No Portal Azure:**

1. Barra superior → buscar **`app-mcp-helpsphere-client`** → clicar (em **App registrations**)
2. Menu lateral → **Authentication**
3. Em **Platform configurations** → encontrar `Web` (já existe com URI do n8n)
4. Clicar **Add URI** dentro do bloco Web → adicionar:
   - `https://global.consent.azure-apim.net/redirect`
5. Clicar **Add URI** novamente → adicionar:
   - `https://token.botframework.com/.auth/web/redirect`
6. Botão **Save** (topo da página)
7. Confirmar que os 3 URIs aparecem listados:
   - `https://ca-n8n-helpsphere.<env>.azurecontainerapps.io/rest/oauth2-credential/callback` (n8n, já existia)
   - `https://global.consent.azure-apim.net/redirect` (Copilot Studio MCP connector — URL base)
   - `https://token.botframework.com/.auth/web/redirect` (Bot Framework — caso publique como Teams app)

<!-- screenshot: passo-8.2-a-redirect-uris.png -->

> **⚠️ Sufixo dinâmico do Copilot Studio MCP connector:** ao clicar **Connect** no Passo 8.2.D pela primeira vez, o Copilot Studio gera um redirect URI com um **sufixo único** baseado no nome do connector, no formato:
>
> ```
> https://global.consent.azure-apim.net/redirect/<connector-id-encoded>
> ```
>
> Exemplo: `https://global.consent.azure-apim.net/redirect/cr7d4-5fmcp-20help-5f93348c82a09d9032` (onde `cr7d4-5fmcp-20help-...` é o nome do MCP connector "MCP Help" codificado).
>
> A URL base `https://global.consent.azure-apim.net/redirect` (item 4 acima) **não é suficiente** — o Entra ID compara o redirect URI bit-for-bit. Ao tentar **Connect** você vai bater no erro:
>
> ```
> AADSTS50011: The redirect URI 'https://global.consent.azure-apim.net/redirect/<sufixo>'
> specified in the request does not match the redirect URIs configured for the application
> '<client-app-id>'.
> ```
>
> **Solução:** copie o redirect URI completo da mensagem de erro AADSTS50011 e adicione como 4º URI no App Registration cliente. O sufixo é **fixo por connector** (não muda a cada Connect), então uma vez registrado, funciona indefinidamente — exceto se você deletar e recriar o connector com mesmo nome (pode gerar sufixo diferente).
>
> **Loop pedagógico explícito:** este passo é intencionalmente iterativo. Você adiciona a URL base no item 4, tenta Connect no 8.2.D, vê o erro AADSTS50011, copia o URI completo da mensagem, volta aqui e adiciona como 5º URI. Não há jeito de pré-calcular o sufixo antes do primeiro Connect (Microsoft não documenta o algoritmo de encoding).
>
> **Alternativa via Azure CLI após capturar a URL específica do erro:**
>
> ```bash
> # ⚠️ Substitua <URI-DO-ERRO> pelo redirect URI exato da mensagem AADSTS50011
> EXISTING_URIS=$(az ad app show --id $CLIENT_APP_ID --query "web.redirectUris" -o json)
> NEW_URI="https://global.consent.azure-apim.net/redirect/<URI-DO-ERRO>"
>
> # Anexa o novo URI mantendo os existentes
> az ad app update --id $CLIENT_APP_ID --web-redirect-uris \
>   $(az ad app show --id $CLIENT_APP_ID --query "web.redirectUris[]" -o tsv) \
>   "$NEW_URI"
> ```

> **Alternativa via Azure CLI (Linux/Mac/WSL — bash):**
>
> ```bash
> CLIENT_APP_ID=$(az ad app list --display-name app-mcp-helpsphere-client --query "[0].appId" -o tsv)
> N8N_URI=$(az ad app show --id $CLIENT_APP_ID --query "web.redirectUris[0]" -o tsv)
>
> az ad app update --id $CLIENT_APP_ID --web-redirect-uris \
>   "$N8N_URI" \
>   "https://global.consent.azure-apim.net/redirect" \
>   "https://token.botframework.com/.auth/web/redirect"
> ```

### Passo 8.2.B — Grant admin consent para os scopes do server

**No Portal Azure:**

1. Ainda em `app-mcp-helpsphere-client` → menu **API permissions**
2. Confirmar que aparecem **3 permissões** para `app-mcp-helpsphere-server` (status atual: `Not granted for <tenant>`):
   - `helpsphere.kb.read`
   - `helpsphere.tickets.read`
   - `helpsphere.tickets.write`
3. Botão **Grant admin consent for "<seu-tenant>"** (topo da lista, requer ser Owner/Privileged Role Admin da sub)
4. Confirmar `Yes`
5. Status das 3 permissões muda para `Granted for <tenant>` com ✅ verde

<!-- screenshot: passo-8.2-b-admin-consent.png -->

> **Se botão estiver desabilitado:** você não é Owner ou Privileged Role Administrator do tenant — peça a um admin para clicar, ou troque para uma sub onde seja Owner.

> **Alternativa via Azure CLI (Linux/Mac/WSL — bash):**
>
> ```bash
> az ad app permission admin-consent --id $CLIENT_APP_ID
> ```

### Passo 8.2.C — Criar Client Secret no App Registration cliente

O Copilot Studio MCP connector usa OAuth 2.0 **Authorization Code flow on behalf of the user**, que exige um **client secret** no App Registration cliente. O `app-mcp-helpsphere-client` foi criado no Passo 4.7 com 1 secret dedicado ao n8n — você precisa criar um **secret novo dedicado ao Copilot Studio** (boa prática: 1 secret por consumer permite rotação independente).

**No Portal Azure:**

1. Buscar `app-mcp-helpsphere-client` → clicar
2. Menu **Certificates & secrets** → aba **Client secrets**
3. **+ New client secret**
4. **Description:** `copilot-studio`
5. **Expires:** `6 months` (ou `12 months` se quiser menos rotação)
6. **Add**
7. **⚠️ COPIE O VALOR DA COLUNA `Value` IMEDIATAMENTE** (não a coluna `Secret ID` — é o `Value` que vira o `client_secret` do OAuth). O valor fica blurado após você sair da página e **não pode ser recuperado depois**.
8. Cole o valor num bloco de notas temporário ou direto no campo `Client Secret` do Copilot Studio (Passo 8.2.D)

<!-- screenshot: passo-8.2-c-client-secret.png -->

> **Alternativa via Azure CLI (Linux/Mac/WSL — bash):**
>
> ```bash
> # ⚠️ O comando mostra o secret value no stdout — APENAS uma vez.
> # Use em ambiente confiável, copie imediatamente, e nunca commite o valor.
> az ad app credential reset \
>   --id $CLIENT_APP_ID \
>   --display-name "copilot-studio" \
>   --years 1 \
>   --append \
>   --query "{appId:appId, password:password}" -o json
> ```
>
> Saída esperada: `{"appId":"a164...", "password":"abc.XYZ..."}` — `password` é o `client_secret`.

### Passo 8.2.D — Conectar MCP Server no Copilot Studio

**No Copilot Studio (`https://copilotstudio.microsoft.com`):**

1. Selecionar agente `HelpSphere Tier 1 Agent`
2. Menu lateral → **Actions** → **+ Add an action**
3. Painel direito → categoria **Model Context Protocol** → **Connect to an MCP server**
4. Preencher (substitua `<TENANT_ID>` pelo seu Tenant ID e `<APPID_SERVER>` pelo appId do `app-mcp-helpsphere-server`):
   - **Server URL:** `https://${MCP_URL}/mcp` (`MCP_URL` capturado no Passo 4.9)
   - **Authentication:** `OAuth 2.0`
   - **Authorization URL:** `https://login.microsoftonline.com/<TENANT_ID>/oauth2/v2.0/authorize`
   - **Token URL:** `https://login.microsoftonline.com/<TENANT_ID>/oauth2/v2.0/token`
   - **Refresh URL:** `https://login.microsoftonline.com/<TENANT_ID>/oauth2/v2.0/token` (**igual ao Token URL** — Entra ID usa o mesmo endpoint para refresh)
   - **Scope:** `api://<APPID_SERVER>/.default`
   - **Client ID:** `<appId de app-mcp-helpsphere-client>`
   - **Client Secret:** `<o Value que você copiou no Passo 8.2.C>`
5. Clicar **Connect** → popup de consentimento Entra → **Accept** (se 8.2.B já fez admin consent, popup pode nem aparecer)
6. Aguardar Copilot Studio fazer test connection → deve aparecer **4 tools** listadas:
   - `get_ticket`
   - `list_tickets`
   - `add_comment`
   - `update_status`
7. Selecionar as 4 tools (checkbox) → **Add**
8. **Save** no topo do agente

<!-- screenshot: passo-8.2-d-mcp-connect-copilot-studio.png -->

**Capturar Tenant ID e App IDs (rodar 1x no início):**

```powershell
# 🔑 Capture as variáveis OAuth (sessão nova? rode este bloco)
$TenantId      = az account show --query tenantId -o tsv
$ClientAppId   = az ad app list --display-name app-mcp-helpsphere-client --query "[0].appId" -o tsv
$ServerAppId   = az ad app list --display-name app-mcp-helpsphere-server --query "[0].appId" -o tsv

Write-Host "TenantId:    $TenantId"
Write-Host "ClientAppId: $ClientAppId"
Write-Host "ServerAppId: $ServerAppId"
Write-Host ""
Write-Host "Authorization URL: https://login.microsoftonline.com/$TenantId/oauth2/v2.0/authorize"
Write-Host "Token URL:         https://login.microsoftonline.com/$TenantId/oauth2/v2.0/token"
Write-Host "Refresh URL:       https://login.microsoftonline.com/$TenantId/oauth2/v2.0/token"
Write-Host "Scope:             api://$ServerAppId/.default"
```

> **Atenção scope `.default`:** o sufixo `/.default` pede TODAS as permissões já consented em 8.2.B (`helpsphere.kb.read` + `helpsphere.tickets.read` + `helpsphere.tickets.write`). É o jeito recomendado para confidential/daemon clients. Alternativa: listar scopes individuais separados por espaço (`api://<APPID_SERVER>/helpsphere.tickets.read api://<APPID_SERVER>/helpsphere.tickets.write`).

> **Por que Refresh URL = Token URL?** Entra ID v2.0 usa o **mesmo endpoint `/token`** para emitir access token (grant_type=`authorization_code`) e renovar (grant_type=`refresh_token`). O Copilot Studio pede campo separado para compatibilidade com providers OAuth 2.0 que têm endpoints distintos (Google, GitHub etc) — para Entra, repete a mesma URL.

### Passo 8.2.E — Validar conexão MCP

1. No agente `HelpSphere Tier 1 Agent` → **Test** (painel direito)
2. Digite: `Status do ticket 1?`
3. O bot deve:
   - Reconhecer o intent `Resolver_ticket` (Passo 8.1 já configurou)
   - Foundry Agent recebe pergunta, decide chamar tool `get_ticket`
   - Tool chega ao MCP Server, autenticação OAuth Bearer passa
   - SQL retorna dados do ticket #1
   - Resposta: "Ticket #1 — Status: Open · Categoria: Devolução · ..."

**Mensagens de erro conhecidas e correção:**

| Mensagem no Copilot Studio | Sub-etapa que faltou |
|----------------------------|----------------------|
| `Encountered internal server error. Correlation Id: xxx` ao clicar Connect | 8.2.A (redirect URI `global.consent.azure-apim.net/redirect` faltando) |
| `AADSTS65001: User or admin has not consented` | 8.2.B (admin consent não foi dado) |
| `AADSTS50011: Reply URL does not match` | 8.2.A (URI digitada errada — verificar se não tem barra final ou espaço) |
| Connect funciona mas Test → bot diz "não tenho acesso a essas informações" | Foundry Agent não está usando a tool — verificar Passo 8.1 (Configurar Copilot Studio com Foundry Agent) |
| Connect funciona mas tools retornam erro 500 | MCP Server SQL grants — ver Passo 4.9 (CREATE USER FROM EXTERNAL PROVIDER) |

## Passo 8.3 — Como tudo se conecta (mapa mental antes da demo)

Antes de rodar os 5 tickets, **entenda visualmente** quais peças do que você construiu nos Blocos 1-7 são acionadas em cada caso. Cada ticket "acende" uma rota diferente do diagrama abaixo.

```mermaid
flowchart LR
  subgraph Canais["🎤 Entrada do usuário"]
    TEAMS[Teams chat]
    WEB[Web chat]
    VOZ[Áudio]
  end
  subgraph CS["🤖 Copilot Studio (HelpSphere Tier 1 Agent)"]
    TOPIC[Topic Resolver_ticket]
    HTTP[HTTP Action]
    MCPDIR[MCP connector]
  end
  subgraph Speech["🗣️ Speech"]
    STT[STT]
    TTS[TTS]
  end
  subgraph Func["⚡ Function func-helpsphere-agent"]
    PROXY["/api/agent/chat"]
  end
  subgraph Foundry["🧠 Foundry Agent (GPT-4.1-mini)"]
    AGENT[Agent + 4 tools]
  end
  subgraph MCP["🔌 MCP Server (ACA)"]
    MCPSRV[mcp-helpsphere OAuth]
  end
  subgraph Apex["🏢 apex-helpsphere"]
    API[Tickets-Service .NET]
    DB[(SQL tbl_tickets)]
  end
  subgraph RAG["📚 RAG (Lab Inter)"]
    SEARCH[AI Search 8 PDFs]
  end
  subgraph Async["📨 Escalação assíncrona"]
    SB[(Service Bus queue<br/>ticket-escalations)]
    N8N[n8n workflow 7 nodes]
    GRAPH[Teams via MS Graph]
    SHEETS[Google Sheets]
  end
  TEAMS --> CS
  WEB --> CS
  VOZ --> STT --> CS
  CS --> TTS --> VOZ
  TOPIC --> HTTP --> PROXY --> AGENT
  MCPDIR -.OAuth.-> MCPSRV
  AGENT -- search_kb --> SEARCH
  AGENT -- get_ticket --> MCPSRV --> API --> DB
  AGENT -- escalate --> SB --> N8N --> GRAPH
  N8N --> SHEETS
```

**Como ler o diagrama:**

- **Copilot Studio** é a **porta** — toda interação começa aqui
- **Foundry Agent** é o **cérebro** — recebe a pergunta e decide qual das 4 tools usar (`search_kb`, `get_ticket`, `translate`, `escalate_ticket`)
- **Service Bus** é o **único caminho assíncrono** — separa "responder ao usuário agora" de "humano resolver depois"

### Matriz: qual ticket exercita qual peça

| Componente | T1 FAQ | T2 MCP | T3 Multilíngue | T4 Voz | T5 Escalação |
|---|:---:|:---:|:---:|:---:|:---:|
| Copilot Studio | ✅ | ✅ | ✅ | ✅ | ✅ |
| Speech STT/TTS | — | — | — | ✅ | — |
| Function `func-helpsphere-agent` | ✅ | ✅ | ✅ | ✅ | ✅ |
| Foundry Agent (LLM) | ✅ | ✅ | ✅ | ✅ | ✅ |
| Tool `search_kb` (AI Search) | ✅ | — | ✅ | parcial | ✅ tenta antes |
| Tool `get_ticket` (MCP) | — | ✅ | — | — | — |
| MCP Server | — | ✅ | — | — | — |
| apex-helpsphere SQL | — | ✅ leitura | — | — | — |
| Tool `escalate_ticket` | — | — | — | — | ✅ |
| Service Bus queue | — | — | — | — | ✅ |
| n8n workflow | — | — | — | — | ✅ |
| MS Graph → Teams | — | — | — | — | ✅ |
| Google Sheets | — | — | — | — | ✅ |
| App Insights audit | ✅ | ✅ | ✅ | ✅ | ✅ |

> **Propriedade pedagógica:** cada ticket adiciona **uma e somente uma** camada nova. Se você entender T1 (RAG), T2 já é incremental (substitui search_kb por MCP), e assim por diante.

## Passo 8.4 — Demo dos 5 tickets (com "onde olhar")

Para cada ticket abaixo, abra **3 abas no navegador**:

1. **Copilot Studio Test pane** (`https://copilotstudio.microsoft.com` → seu agente → **Test**)
2. **Portal Azure** (`https://portal.azure.com`)
3. **Foundry portal** (`https://ai.azure.com` → seu project → Agents → seu agent → Threads)

### Ticket 1 — FAQ simples auto-resolvido

**Pergunta:** copie e cole no Copilot Studio Test pane:

> Qual horário de atendimento do suporte?

**Resposta esperada (em ~2s):** texto citando `faq_horario_atendimento.pdf`, ex: *"O suporte HelpSphere atende de segunda a sexta das 8h às 18h, conforme [faq_horario_atendimento.pdf]."*

**Recursos exercitados nesta jogada:**

- Copilot Studio → Function → Foundry Agent → Tool `search_kb` → AI Search

**Onde ver o caminho ao vivo:**

1. **Foundry portal** → seu agent → **Threads** → última conversa → expandir o turn → seção **Tool calls** mostra `search_kb({"query":"horario atendimento"})` e o resultado retornado
2. **Portal Azure** → resource `appi-helpsphere-final` → blade **Logs** → execute:

   ```kql
   requests
   | where name == "agent/chat"
   | top 1 by timestamp desc
   | project timestamp, duration, customDimensions
   ```

   A linha mostra `duration ≈ 1500ms`, `customDimensions.tool_called = "search_kb"`

3. **Portal Azure** → resource `srch-helpsphere` (Lab Inter) → **Search explorer** → query `"horário atendimento"` → mostra o chunk vindo do PDF (campo `content`)

> **Observação:** estamos **reusando o índice do Lab Inter**. RAG não foi recriado — é tijolo emprestado da Parte 10 do Lab Anterior.

### Ticket 2 — Consulta dados HelpSphere via MCP

**Pergunta:**

> Status do ticket 4521?

**Resposta esperada:** dados reais do banco, ex: *"Ticket #4521 — Status: Em análise · Lojista: Marília Tech · Aberto há 2 dias · Categoria: Devolução."*

**Recursos exercitados:**

- Copilot Studio → Function → Foundry Agent → Tool `get_ticket` → MCP Server (OAuth Entra) → apex-helpsphere Tickets-Service .NET → SQL `tbl_tickets`

**Onde ver o caminho ao vivo:**

1. **Foundry portal** → agent → Threads → último turn → Tool calls → `get_ticket({"id":4521})` com payload de retorno
2. **Portal Azure** → Container App `aca-mcp-helpsphere` → blade **Log stream** → linha aparece em real-time:

   ```
   [tool] name=get_ticket id=4521 tenant=marilia user=alex@apexretail.com
   ```

3. **Portal Azure** → SQL Database `sql-helpsphere-saas` → **Query editor** → executar:

   ```sql
   SELECT id, subject, status, tenant_id FROM tbl_tickets WHERE id = 4521;
   ```

   Resultado bate com a resposta do agent — é o **mesmo banco**.

> **Diferença chave RAG vs MCP:** RAG (`search_kb`) lê **documento estático** (PDF indexado). MCP (`get_ticket`) lê **sistema vivo** (banco transacional). Mesmo agent, ferramentas com naturezas diferentes.

### Ticket 3 — Caso multilíngue (espanhol)

**Pergunta (em espanhol):**

> Hola, no puedo acceder al sistema POS de la tienda.

**Resposta esperada:** texto em espanhol, citando troubleshooting POS do KB, ex: *"Hola. Para problemas de acceso al POS, intenta los siguientes pasos según [troubleshooting_pos.pdf]: ..."*

**Recursos exercitados:**

- Mesmo caminho do T1, com tool `translate` adicional na saída

**Onde ver o caminho ao vivo:**

1. **Foundry portal** → System prompt do agent (blade **Instructions**) → procure as linhas:

   ```
   - Detect input language and respond in the SAME language
   - Tool search_kb returns Portuguese chunks; translate to user language before responding
   ```

2. **Portal Azure** → App Insights → blade **Logs** → query:

   ```kql
   customEvents
   | where name == "agent_invocation"
   | extend lang = tostring(customDimensions.detected_language)
   | top 5 by timestamp desc
   ```

   Linha do T3 mostra `lang=es`

> **Insight:** multilíngue **não é feature técnica nova** — é instrução pro LLM. Não criamos código novo entre T1 e T3.

### Ticket 4 — Canal de voz (STT + TTS)

**Pré-requisito:** abra `https://speech.microsoft.com` → resource `speech-helpsphere` → **Speech-to-text** test pane.

**Demo passo a passo:**

1. **Speech Studio** → tab **Speech-to-text** → clique no microfone → fale:

   > Qual o procedimento de devolução pra cliente?

2. Texto transcrito aparece em <2s. Copie.
3. **Copilot Studio Test pane** → cole o texto transcrito → envie → resposta em texto chega.
4. Copie a resposta.
5. **Speech Studio** → tab **Text-to-speech** → cole a resposta → selecione voz `pt-BR-FranciscaNeural` → **Play** → áudio toca.

**Recursos exercitados:**

- Speech STT (entrada) → Copilot Studio → Function → Foundry Agent → Tool `search_kb` → resposta texto → Speech TTS (saída)

**Onde ver o caminho ao vivo:**

- **Portal Azure** → `speech-helpsphere` → blade **Metrics** → métrica `Audio Seconds Transcribed` (sobe na hora da demo)

> **Pergunta reflexiva:** se você tirar o Speech daqui, o que muda no agent? **Nada**. O agent recebe texto e devolve texto. Speech é só **decoração de borda** — em produção viria de Teams Voice, IVR ou app móvel.

### Ticket 5 — Escalação assíncrona (o ticket mais rico)

**Pergunta:**

> Lojista pediu reembolso de R$ 50.000 que não está claro nas políticas. Pode aprovar?

**Resposta esperada (em ~2s):** *"Esse caso requer aprovação especial. Vou escalar para a Marina (líder de suporte tier 2), você terá retorno em até 1 hora. ID da escalação: #esc-N."*

> **Importante:** repare que o agent **respondeu na hora** ao usuário. Em paralelo, uma cascata assíncrona começa.

**Setup ANTES do envio (abra 4 abas):**

1. **Copilot Studio Test pane** (já aberta)
2. **Portal Azure** → Service Bus namespace `sb-helpsphere` → queue `ticket-escalations` → **Service Bus Explorer** → modo **Peek**
3. **n8n UI** (`https://ca-n8n-azirion.<random>.azurecontainerapps.io`) → workflow `Escalation` → tab **Executions**
4. **Microsoft Teams** → canal `HelpSphere Escalations` (onde Marina recebe)

**Demo (sequência cronometrada, ~30s de show):**

| Tempo | Onde olhar | O que ver |
|-------|-----------|-----------|
| **0s** | Copilot | Envia a pergunta |
| **2s** | Copilot | Resposta "Vou escalar pra Marina..." aparece |
| **3s** | Service Bus Explorer (refresh) | Aparece **1 mensagem** na queue. Clique nela → payload JSON: `{"ticket_id":..., "tenant":..., "reason":"..."}` |
| **5s** | n8n Executions (refresh) | Nova execution verde aparece. Clique → expanda os 7 nodes:<br>1. **AMQP Trigger** (consumiu da queue) ✅<br>2. Parse payload ✅<br>3. Build Teams message ✅<br>4. HTTP POST Graph (notificou Marina) ✅<br>5. Build Sheets row ✅<br>6. Sheets append ✅<br>7. Ack ✅ |
| **8s** | Teams Marina (refresh) | Mensagem do bot aparece: *"Ticket #N escalado — prioridade alta"* com botões `Aceitar` `Rejeitar` |
| **12s** | Google Sheets `escalations` tab | Linha nova com timestamp, tenant, motivo |

**Recursos exercitados (todos):**

- Copilot Studio → Function → Foundry Agent → Tool `escalate_ticket` → Service Bus queue → n8n workflow (7 nodes) → MS Graph (Teams) + Google Sheets

> **Punchline pedagógica:**
>
> - O usuário pegou resposta em **2 segundos**.
> - Marina foi notificada **8 segundos depois** (acontece em paralelo).
> - Se Marina não tivesse Teams, **Sheets já tem o registro**.
> - Se o n8n cair, a mensagem **fica na Service Bus queue até retry** (TTL padrão 14 dias).
>
> **Esse desacoplamento é o motivo de usar mensageria** em vez de mais um HTTP call síncrono.

## Passo 8.5 — Os 3 "aha moments" do Lab Final

Antes de partir pro cleanup, fixe estes 3 conceitos:

### 1. "Tool é só uma função que o LLM decide chamar"

Abra **Foundry portal** → seu agent → blade **Tools** → veja as 4 tools registradas:

```json
[
  {"name": "search_kb", "description": "Busca KB Apex para FAQs e troubleshooting..."},
  {"name": "get_ticket", "description": "Consulta dados HelpSphere via MCP..."},
  {"name": "translate", "description": "Traduz texto entre idiomas..."},
  {"name": "escalate_ticket", "description": "Escala ticket pro humano via Service Bus..."}
]
```

A descrição é em **natural language**. O LLM lê isso e decide qual usar com base na pergunta. **Não tem `if/else` em código nosso** — toda lógica de roteamento mora no LLM.

### 2. "Mesma stack, três contratos diferentes pra três naturezas diferentes"

| Contrato | Quem chama quem | Natureza | Quando usar |
|----------|-----------------|----------|-------------|
| **Function HTTP** | Copilot → Function → Foundry Agent | Síncrono request/response | Latência baixa exigida (<3s) |
| **MCP** | Foundry Agent → MCP Server → HelpSphere | Síncrono **com OAuth + descoberta de tools** | Quando o LLM precisa descobrir capacidades dinamicamente |
| **Service Bus** | Foundry Agent → SB queue → n8n | **Assíncrono** com garantia de entrega | Quando o consumidor pode demorar / pode falhar / não pode bloquear o usuário |

> **Erro comum:** usar Function HTTP onde precisa de Service Bus. Se o n8n leva 5s para responder, o usuário trava esperando. Service Bus desacopla.

### 3. "Reuso, não rebuild"

| Lab | O que deu pra este | O que este reusou |
|-----|---------------------|-------------------|
| **apex-helpsphere** (base SaaS) | SQL + API + Auth Entra + Frontend | Lab Final consultou banco via MCP |
| **Lab Intermediário** | RAG (AI Search index com 8 PDFs Apex) | Lab Final exercitou via tool `search_kb` |
| **Lab Final** | Copilot + Foundry + MCP + Speech + SB + n8n | (no Lab Avançado você fecha a história: como essa stack vira **produção real** — governança, custo, safety, runbook, lifecycle) |

> **Nenhum lab inventou do zero.** Você pode reaplicar essa arquitetura em outro domínio trocando o KB e os tools — a costura permanece.

## Passo 8.6 — Cleanup

> **Cleanup — OPCIONAL:**
> Se você vai fazer Lab Avançado em sequência, **mantenha** `rg-lab-intermediario` rodando.
>
> Se terminou:
> ```powershell
> az group delete --name rg-lab-intermediario --yes --no-wait
> ```
> **NÃO esqueça** — custo ~R$ 80-120/mês ativo.

**Cleanup do RG específico do Lab Final — No Portal Azure:**

1. Barra superior → buscar **"Resource groups"** → clicar
2. Clicar `rg-lab-final` → botão **Delete resource group** (topo)
3. Digitar `rg-lab-final` para confirmar → **Delete**
4. Aguardar ~3-5min para todos recursos serem deletados

<!-- screenshot: passo-8.3-delete-rg-portal.png -->

> **Alternativa via Azure CLI (Linux/Mac/WSL — bash):**
>
> ```bash
> az group delete --name rg-lab-final --yes --no-wait
> echo "✅ Lab Final cleanup iniciado"
> ```

**E desativar Copilot Studio agent (para não deixar consumindo licença trial):**

1. Acesse `https://copilotstudio.microsoft.com` → agent `HelpSphere Tier 1 Agent`
2. Menu **Settings** → **Disable** (ou **Delete** se quiser remover)

> **Atenção:** o `rg-lab-intermediario` (Bloco 2) e o `func-helpsphere-rag` (Lab Intermediário) ainda existem e são consumidos no Lab Avançado. Não delete se for fazer o Lab Avançado em sequência.
>
> Se você deletou `rg-lab-intermediario` ao final do Lab Inter, no Lab Avançado teremos que considerar isso — o Lab Avançado parametriza tudo via Bicep e re-provisiona.

## ✅ Checkpoint final do Lab Final

- [ ] Demo dos 5 tickets executada e funcionou
- [ ] Vídeo de evidência gravado (se desejado pelo professor)
- [ ] `rg-lab-final` deletado
- [ ] Copilot Studio agent desativado
- [ ] Custo total: ≤ R$ 30

---

## Recap do Lab Final

Você implementou em 9h:

✅ Copilot Studio agent multi-canal (Teams + Web)
✅ Foundry Agent Service code-first com 4 tools
✅ MCP Server HelpSphere pré-pronto deployado em ACA
✅ Configuração OAuth Entra ID com scopes granulares
✅ Speech STT + TTS para canal de voz
✅ n8n self-hosted em ACA com workflow de escalação 7 nodes
✅ Service Bus para mensageria assíncrona
✅ Microsoft Graph integration para Teams
✅ Google Sheets connector para auditoria
✅ Demo end-to-end de 5 tickets cobrindo casos diversos

**Próximo:** [Lab Avançado — IA em Produção](Lab_Avancado_IA_Producao_Guia_Portal.md)

---

*Custo total: R$ 22-30 saindo do bolso · Tempo: 9h · Recursos deletados ao final: ✅*
