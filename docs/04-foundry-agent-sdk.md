# Capítulo 04 — Foundry Agent SDK

> **Objetivo:** criar AI Foundry Project filho do Hub `aifhub-apex-prod`, confirmar/deployar `gpt-4.1-mini`, criar o agente `helpsphere-tier1-agent` via SDK Python (`azure-ai-projects==1.0.0b9`) com 4 tools (`search_kb`, `get_ticket`, `list_similar_tickets`, `escalate_ticket`), implementar o handler de tools, e validar com smoke run end-to-end.
>
> **Tempo:** 90-120 min (60min se Foundry Hub `aifhub-apex-prod` já existe e `gpt-4.1-mini` já deployado)
>
> **Status:** `v0.2.0-piloto` ⚠️ EXPANDIDO (era `v0.1.0-init` outline) — derivado de `Lab_Final_Agente_Workflow_Guia_Portal.md` Parte 3 (Passos 3.1-3.5)

---

## Pré-requisitos

- ✅ Capítulo 02 concluído — RG `rg-lab-final` existe, ACR `acrhelpsphere{rand}` e ACA Environment `cae-helpsphere-final` provisionados
- ✅ Capítulo 03 concluído — Copilot Studio agent `cps-helpsphere-tier1` criado (será integrado ao agent Foundry no final do Capítulo 08)
- ✅ Foundry Hub `aifhub-apex-prod` existindo na sua sub (criado no Bloco 2 da disciplina; se não existe, ver Lab Intermediário Parte 1)
- ✅ Lab Intermediário deployado (precisamos da `RAG_FUNCTION_URL` para a tool `search_kb`)
- ✅ Python 3.11+ instalado localmente
- ✅ `az` CLI logado na sub correta (`az account show` confirma)
- ✅ VS Code com extensão **Python** instalada

> **Atenção SDK preview:** `azure-ai-projects==1.0.0b9` é **preview**. Pinned hard porque GA Q3-2026 vai introduzir breaking changes (ex.: `client.agents.create_message` virou `client.agents.threads.messages.create`). Quando GA sair, atualize seguindo migration guide oficial.

---

## Resumo dos 4 tools que o agente vai usar

| Tool | Implementação | Backend chamado |
|---|---|---|
| `search_kb` | HTTP POST | RAG Function App do Lab Intermediário (`func-helpsphere-rag`) |
| `get_ticket` | HTTP POST → MCP JSON-RPC | MCP Server `ca-mcp-helpsphere` (Capítulo 05) → HelpSphere API |
| `list_similar_tickets` | HTTP POST → MCP JSON-RPC | MCP Server `ca-mcp-helpsphere` → HelpSphere API |
| `escalate_ticket` | Service Bus message | Queue `ticket-escalations` → workflow n8n (Capítulo 07) |

> **Nota pedagógica — tool 1 vs tools 2-4:** `search_kb` chama Function App diretamente (latência ~500ms-1s). Tools 2-3 vão via MCP Server (latência adicional ~100-200ms, mas você ganha auth Bearer Entra OAuth padronizada + reuso por outros agentes). Tool 4 é fire-and-forget via Service Bus (latência ~50ms). Pattern: **chame direto quando crítico latência, via MCP quando reuso/auth importam, via fila quando assíncrono OK**.

---

## Passo 4.1 — Criar Foundry Project dedicado

**No Azure AI Foundry portal (https://ai.azure.com):**

1. Abra o navegador em `https://ai.azure.com` → faça login com a mesma conta Azure usada nos Capítulos anteriores
2. Tela inicial → seção **Hubs** → entre no Hub `aifhub-apex-prod` (criado no Bloco 2 da disciplina)
3. Dentro do Hub → botão **+ New project** (canto superior direito)
4. Preencher:
   - **Project name:** `aifproj-helpsphere-agente`
   - **Hub:** `aifhub-apex-prod` (já selecionado, não troque)
   - **Region:** `East US 2` (herdado do Hub — não alterável)
5. Clique **Create**
6. Aguarde provisioning ~1-2min até o project abrir automaticamente. Banner verde "Project created successfully" no topo.

<!-- screenshot: cap04-passo4.1-criar-foundry-project.png -->

> **Alternativa via Azure CLI (PowerShell 7 — Windows-first):**
>
> ```powershell
> $SubId = az account show --query id -o tsv
> $HubId = "/subscriptions/$SubId/resourceGroups/rg-lab-intermediario/providers/Microsoft.MachineLearningServices/workspaces/aifhub-apex-prod"
>
> az ml workspace create `
>   --kind project `
>   --hub-id $HubId `
>   --name aifproj-helpsphere-agente `
>   --resource-group rg-lab-intermediario `
>   --location eastus2
> ```
>
> **Linux/Mac/WSL:** troque `$Var` por `VAR=`, `` ` `` (backtick) por `\`, e use `$(...)` no lugar de `$SubId = az ...`.

> **Custo:** Project é gratuito (cobrança vem de deployments de modelo + storage de threads). No lab, R$ 0 só pelo Project.

> **Nota pedagógica — por que Project filho de Hub e não Project standalone?** Hub centraliza networking + storage + Application Insights + Key Vault. Projects herdam essa fundação e isolam **agentes** + **threads** + **deployments**. Pattern recomendado pela Microsoft para multi-equipe: 1 Hub corporate, N Projects por squad/iniciativa.

---

## Passo 4.2 — Confirmar/criar deployment `gpt-4.1-mini`

**No Azure AI Foundry portal (ai.azure.com):**

1. Dentro do Project `aifproj-helpsphere-agente` recém-criado
2. Menu lateral → **Models + endpoints**
3. Verifique se já existe deployment `gpt-4.1-mini` (compartilhado do Lab Intermediário — pode aparecer aqui se Hub está bem configurado)
4. **Se NÃO existe**, crie:
   - Botão **+ Deploy model** → buscar `gpt-4.1-mini` na lista → **Confirm**
   - Preencher tab **Deployment configuration:**
     - **Deployment name:** `gpt-4.1-mini` (mesmo nome do modelo — convenção da disciplina)
     - **Deployment type:** `Standard`
     - **Tokens per Minute Rate Limit:** `30K` (suficiente pro lab)
     - **Content filter:** `Default` (deixe — Lab Avançado refina isso)
   - Clique **Deploy**
   - Aguarde ~1min até **Status: Succeeded**
5. Após criado (ou se já existia), clique no nome do deployment e anote da página:
   - **Target URI** (endpoint, formato `https://aifhub-apex-prod.openai.azure.com/`)
   - **Key** (API key — botão **Show** para revelar)

<!-- screenshot: cap04-passo4.2-confirmar-deployment-gpt41mini.png -->

> **Alternativa via Azure CLI (PowerShell 7 — Windows-first):**
>
> ```powershell
> # Verificar deployments existentes
> az cognitiveservices account deployment list `
>   --name aifhub-apex-prod `
>   --resource-group rg-lab-intermediario `
>   -o table
>
> # Criar se não existe
> az cognitiveservices account deployment create `
>   --name aifhub-apex-prod `
>   --resource-group rg-lab-intermediario `
>   --deployment-name gpt-4.1-mini `
>   --model-name gpt-4.1-mini `
>   --model-version "2025-04-14" `
>   --model-format OpenAI `
>   --sku-capacity 30 `
>   --sku-name Standard
> ```
>
> **Linux/Mac/WSL:** troque `` ` `` (backtick) por `\` no fim das linhas.

> **Custo:** `gpt-4.1-mini` cobra por 1M tokens (input + output). Para o lab, **R$ 5-8** total com cap em 30K TPM. Para comparação, `gpt-4.1` (não-mini) custa ~5x mais — fique no mini.

> **Nota pedagógica — `gpt-4.1-mini` vs `gpt-4.1`:** mini tem 90% da qualidade em tasks de conversação/tool-calling tier 1 (resoluções simples), com 1/5 do custo. Para agentes tier 1 de helpdesk, é o sweet spot. Para tier 2 (raciocínio complexo, multi-step), suba pra `gpt-4.1` ou `gpt-5-thinking`.

---

## Passo 4.3 — Capturar Project Connection String

**No Azure AI Foundry portal (ai.azure.com):**

1. Project `aifproj-helpsphere-agente` → menu lateral → **Settings** → **Properties**
2. Localize seção **Project connection string** (perto do topo da página)
3. Clique no ícone **Copy** ao lado do valor — formato esperado:
   ```
   eastus2.api.azureml.ms;<subscription-id>;rg-lab-intermediario;aifproj-helpsphere-agente
   ```
4. Cole temporariamente em editor seguro — você vai usar no `.env` no Passo 4.5

<!-- screenshot: cap04-passo4.3-project-connection-string.png -->

> **Por que connection string e não endpoint puro?** SDK `azure-ai-projects` precisa resolver: (1) região AML, (2) sub, (3) RG, (4) project. A connection string carrega os 4 num único valor → menos config + menos chance de typo.

---

## Passo 4.4 — Setup local `agent-code/`

Crie a estrutura de pastas no clone local de `apex-helpsphere-agente-lab`:

```text
agent-code/
├── requirements.txt
├── create_agent.py          # cria o agente + tools (Passo 4.5)
├── agent_runner.py          # handler de tools + run loop (Passo 4.6)
├── .env.example             # template de env vars
└── .env                     # SEU env (gitignored)
```

**No terminal local (Windows PowerShell 7 — Windows-first):**

```powershell
# Na raiz do clone de apex-helpsphere-agente-lab
Set-Location agent-code

# Criar virtualenv
python -m venv .venv

# Ativar (Windows PowerShell)
.\.venv\Scripts\Activate.ps1

# Instalar deps
pip install -r requirements.txt
```

> **Linux/Mac/WSL:** troque `Set-Location` por `cd`, e ative o venv com `source .venv/bin/activate` no lugar de `.\.venv\Scripts\Activate.ps1`.

`requirements.txt` (já está no scaffold deste repo, conferir conteúdo):

```text
azure-ai-projects==1.0.0b9
azure-identity>=1.15.0
azure-servicebus>=7.11.0
openai>=1.40.0
requests>=2.31.0
python-dotenv>=1.0.0
```

`.env.example` (copie para `.env` e preencha — formato dotenv padrão lido por `python-dotenv`, independente de shell):

```dotenv
# Foundry Project (Passo 4.3)
AI_PROJECT_CONNECTION_STRING="eastus2.api.azureml.ms;<sub-id>;rg-lab-intermediario;aifproj-helpsphere-agente"
MODEL_DEPLOYMENT_NAME="gpt-4.1-mini"

# RAG Function App (Lab Intermediário)
RAG_FUNCTION_URL="https://func-helpsphere-rag-{rand}.azurewebsites.net"
RAG_FUNCTION_KEY="<sua-function-key>"

# MCP Server (Capítulo 05 — placeholder por enquanto)
MCP_SERVER_URL="https://placeholder.azurecontainerapps.io"
MCP_TOKEN=""

# Service Bus (Capítulo 08 — placeholder por enquanto)
SB_CONNECTION_STRING="placeholder"

# AGENT_ID — preenchido após Passo 4.5 rodar
AGENT_ID=""
```

> **Nota:** `MCP_SERVER_URL`, `MCP_TOKEN`, `SB_CONNECTION_STRING` ficam **placeholder** até os Capítulos 05 e 07/08. O smoke run do Passo 4.5 só exercita `search_kb` (que chama RAG real).

---

## Passo 4.5 — Criar agente via SDK Python (`create_agent.py`)

Este script define o agente Foundry com instruções (system prompt) + 4 tools (function-calling schemas) + modelo. **Roda 1 vez** — depois você reusa o `agent.id` retornado.

**No VS Code:** abra `agent-code/create_agent.py` (já no scaffold). Cole/confira o conteúdo:

```python
"""
Cria o helpsphere-tier1-agent no Foundry Agent Service.
Define system prompt + 4 tools (function calling).
"""
import os
from azure.ai.projects import AIProjectClient
from azure.identity import DefaultAzureCredential
from dotenv import load_dotenv

load_dotenv()

PROJECT_CONNECTION_STRING = os.environ["AI_PROJECT_CONNECTION_STRING"]
MODEL_DEPLOYMENT_NAME = os.environ.get("MODEL_DEPLOYMENT_NAME", "gpt-4.1-mini")

client = AIProjectClient.from_connection_string(
    credential=DefaultAzureCredential(),
    conn_str=PROJECT_CONNECTION_STRING,
)

# Tool 1: search_kb (chama RAG do Lab Intermediário)
search_kb_tool = {
    "type": "function",
    "function": {
        "name": "search_kb",
        "description": "Busca na base de conhecimento corporativa (manuais, runbooks, FAQs, políticas) sugestões de resposta para um problema descrito. Retorna sugestão com citações e score de confiança.",
        "parameters": {
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "Descrição do problema/pergunta a buscar"},
                "ticket_id": {"type": "string", "description": "ID do ticket (opcional)"},
            },
            "required": ["query"],
        },
    },
}

# Tool 2: get_ticket (via MCP)
get_ticket_tool = {
    "type": "function",
    "function": {
        "name": "get_ticket",
        "description": "Recupera dados completos de um ticket do HelpSphere pelo ID. Retorna descrição, status, categoria, prioridade, anexos, histórico.",
        "parameters": {
            "type": "object",
            "properties": {
                "ticket_id": {"type": "integer", "description": "ID numérico do ticket"},
            },
            "required": ["ticket_id"],
        },
    },
}

# Tool 3: list_similar_tickets (via MCP)
list_similar_tool = {
    "type": "function",
    "function": {
        "name": "list_similar_tickets",
        "description": "Lista tickets passados resolvidos com mesma categoria — útil para basear sugestão em casos análogos.",
        "parameters": {
            "type": "object",
            "properties": {
                "category": {"type": "string"},
                "limit": {"type": "integer", "default": 5},
            },
            "required": ["category"],
        },
    },
}

# Tool 4: escalate_ticket (dispara workflow n8n via Service Bus)
escalate_tool = {
    "type": "function",
    "function": {
        "name": "escalate_ticket",
        "description": "Escala ticket para tier 2 (supervisora Marina). Use quando confidence < 0.5 ou quando o caso envolver complexidade alta. Dispara workflow estruturado de notificação.",
        "parameters": {
            "type": "object",
            "properties": {
                "ticket_id": {"type": "integer"},
                "reason": {"type": "string", "description": "Motivo da escalação"},
                "confidence": {"type": "number", "description": "Confidence calculado (0-1)"},
            },
            "required": ["ticket_id", "reason", "confidence"],
        },
    },
}

# Cria agent
agent = client.agents.create_agent(
    model=MODEL_DEPLOYMENT_NAME,
    name="helpsphere-tier1-agent",
    instructions="""Você é o agente autônomo de tier 1 da Apex HelpSphere.

Quando recebe uma pergunta sobre ticket:
1. Use `search_kb` para buscar resposta na base de conhecimento corporativa
2. Se confidence retornado < 0.5, use `escalate_ticket` em vez de tentar responder
3. Para casos onde precisa contexto adicional, use `get_ticket` e `list_similar_tickets`
4. Sempre cite as fontes ([Manual X, seção Y]) na resposta final
5. Resposta em pt-BR, tom profissional, conciso (max 200 palavras)
6. Se a pergunta envolver dados pessoais sensíveis (CPF, salário, dados médicos), responda "Esse caso requer redação humana — escalando para tier 2." e use `escalate_ticket`.

NUNCA invente informação que não esteja no kb. Se não encontrar, escale.""",
    tools=[search_kb_tool, get_ticket_tool, list_similar_tool, escalate_tool],
)

print(f"[+] Agent criado: {agent.id}")
print(f"    Model: {agent.model}")
print(f"    Tools: {len(agent.tools)}")
print(f"")
print(f"    >>> Adicione ao .env: AGENT_ID={agent.id}")
```

**Rodar o script (Windows PowerShell 7):**

```powershell
# Garantir login Azure (DefaultAzureCredential usa az login na precedence)
az login

# Rodar
python create_agent.py
```

Saída esperada:

```text
[+] Agent criado: asst_xxxxxxxxxxxxxxxxxxxxxxxx
    Model: gpt-4.1-mini
    Tools: 4

    >>> Adicione ao .env: AGENT_ID=asst_xxxxxxxxxxxxxxxxxxxxxxxx
```

Anote o `agent.id` (formato `asst_xxxxxxx`) e atualize seu `.env`:

```dotenv
AGENT_ID=asst_xxxxxxxxxxxxxxxxxxxxxxxx
```

> **Custo:** criar agente em si é gratuito (metadata só). Tokens só rodam quando você chama `run_agent` no Passo 4.6.

> **Nota pedagógica — `DefaultAzureCredential` precedence:** o SDK tenta credenciais nesta ordem: (1) `EnvironmentCredential`, (2) `WorkloadIdentityCredential`, (3) `ManagedIdentityCredential`, (4) `AzureCliCredential` (`az login`), (5) `AzurePowerShellCredential`, (6) `InteractiveBrowserCredential`. Em dev local, `az login` resolve. Quando você for pra Function App (Capítulo 06+), Managed Identity assume.

> **Nota pedagógica — `instructions` (system prompt) é arquitetura, não enfeite:** as 6 regras numeradas são **políticas de produto** codificadas. Trocar regra 6 (PII handling) muda comportamento legal do agente. Trate o system prompt como código versionado, não como copy-paste casual.

---

## Passo 4.6 — Implementar handler de tools (`agent_runner.py`)

O agente do Passo 4.5 só **declara o schema** das tools. Agora você implementa o runner: loop que recebe mensagem do user, processa runs, executa tools quando o agente decidir chamar, retorna resposta final.

**No VS Code:** abra `agent-code/agent_runner.py` (já no scaffold). Cole/confira:

```python
"""
Loop de execução do agent — recebe user message, processa runs,
executa tools quando agent decide chamar, retorna resposta final.
"""
import os
import json
import requests
from azure.ai.projects import AIProjectClient
from azure.identity import DefaultAzureCredential
from dotenv import load_dotenv

load_dotenv()

client = AIProjectClient.from_connection_string(
    credential=DefaultAzureCredential(),
    conn_str=os.environ["AI_PROJECT_CONNECTION_STRING"],
)

AGENT_ID = os.environ["AGENT_ID"]
RAG_URL = os.environ["RAG_FUNCTION_URL"]
RAG_KEY = os.environ["RAG_FUNCTION_KEY"]
MCP_URL = os.environ.get("MCP_SERVER_URL", "")
MCP_TOKEN = os.environ.get("MCP_TOKEN", "")


# Implementação das tools
def tool_search_kb(args):
    response = requests.post(
        f"{RAG_URL}/api/tickets/agent/suggest",
        headers={"x-functions-key": RAG_KEY, "Content-Type": "application/json"},
        json={"description": args["query"], "attachment_urls": []},
        timeout=30,
    )
    data = response.json()
    return {
        "suggestion": data.get("suggested_response"),
        "citations": data.get("citations", []),
        "confidence": data.get("confidence", 0.0),
    }


def tool_get_ticket(args):
    if not MCP_URL or "placeholder" in MCP_URL:
        return {"error": "MCP_SERVER_URL não configurado — pendente Capítulo 05"}
    response = requests.post(
        f"{MCP_URL}/mcp",
        headers={"Authorization": f"Bearer {MCP_TOKEN}", "Content-Type": "application/json"},
        json={
            "jsonrpc": "2.0",
            "method": "tools/call",
            "params": {"name": "get_ticket", "arguments": args},
            "id": 1,
        },
        timeout=30,
    )
    return response.json().get("result", {})


def tool_list_similar(args):
    if not MCP_URL or "placeholder" in MCP_URL:
        return {"error": "MCP_SERVER_URL não configurado — pendente Capítulo 05"}
    response = requests.post(
        f"{MCP_URL}/mcp",
        headers={"Authorization": f"Bearer {MCP_TOKEN}", "Content-Type": "application/json"},
        json={
            "jsonrpc": "2.0",
            "method": "tools/call",
            "params": {"name": "list_tickets", "arguments": {"status": "Resolved", **args}},
            "id": 2,
        },
        timeout=30,
    )
    return response.json().get("result", {})


def tool_escalate(args):
    """Dispara mensagem em Service Bus → workflow n8n executa."""
    sb_conn = os.environ.get("SB_CONNECTION_STRING", "placeholder")
    if sb_conn == "placeholder":
        return {"escalated": False, "reason": "SB_CONNECTION_STRING não configurado — pendente Capítulo 08"}
    from azure.servicebus import ServiceBusClient, ServiceBusMessage
    with ServiceBusClient.from_connection_string(sb_conn) as sb:
        sender = sb.get_queue_sender(queue_name="ticket-escalations")
        with sender:
            sender.send_messages(ServiceBusMessage(json.dumps(args)))
    return {"escalated": True, "queue": "ticket-escalations"}


TOOL_HANDLERS = {
    "search_kb": tool_search_kb,
    "get_ticket": tool_get_ticket,
    "list_similar_tickets": tool_list_similar,
    "escalate_ticket": tool_escalate,
}


def run_agent(thread_id: str, user_message: str) -> str:
    # Add message
    client.agents.create_message(thread_id=thread_id, role="user", content=user_message)

    # Create run
    run = client.agents.create_and_process_run(thread_id=thread_id, agent_id=AGENT_ID)

    # Process tool calls if any
    while run.status == "requires_action":
        tool_outputs = []
        for tool_call in run.required_action.submit_tool_outputs.tool_calls:
            fn_name = tool_call.function.name
            fn_args = json.loads(tool_call.function.arguments)
            print(f"  [tool] {fn_name}({fn_args})")
            result = TOOL_HANDLERS[fn_name](fn_args)
            tool_outputs.append({
                "tool_call_id": tool_call.id,
                "output": json.dumps(result, ensure_ascii=False),
            })
        run = client.agents.submit_tool_outputs_to_run(
            thread_id=thread_id, run_id=run.id, tool_outputs=tool_outputs
        )

    # Get final message
    messages = client.agents.list_messages(thread_id=thread_id)
    return messages.data[0].content[0].text.value


if __name__ == "__main__":
    thread = client.agents.create_thread()
    print(f"Thread: {thread.id}\n")

    # Smoke run — só exercita search_kb, que chama RAG real
    response = run_agent(
        thread.id,
        "Lojista relata que pedido 84512 não foi entregue há 7 dias. Como reembolsar?",
    )
    print(f"\n=== Response ===\n{response}")
```

**Rodar smoke (Windows PowerShell 7):**

```powershell
python agent_runner.py
```

Saída esperada (placeholder MCP/SB são OK no smoke — só `search_kb` tem que funcionar):

```text
Thread: thread_xxxxxxx

  [tool] search_kb({'query': 'Lojista relata que pedido 84512 não foi entregue há 7 dias. Como reembolsar?'})

=== Response ===
Para iniciar o reembolso de pedido não entregue após 7 dias:
1. Confirme o status no rastreio Correios/transportadora...
[Manual de Reembolsos, seção 3.2] [Runbook Logística, item 7]
```

> **Custo:** ~R$ 0,02-0,05 por smoke run completo (4-6 chamadas de modelo + 1 chamada RAG).

> **Nota pedagógica — loop `while run.status == "requires_action"`:** o agente pode chamar **múltiplas tools em sequência** (ex.: `search_kb` → confidence baixo → `list_similar_tickets` → ainda baixo → `escalate_ticket`). O loop processa cada batch de tool calls e devolve `tool_outputs`. Quando o agente decide que tem resposta final, status vira `completed` e o loop sai.

---

## Passo 4.7 — Validar agente no Foundry portal (playground)

**No Azure AI Foundry portal (ai.azure.com):**

1. Project `aifproj-helpsphere-agente` → menu lateral → **Agents**
2. Você verá `helpsphere-tier1-agent` listado (criado pelo SDK no Passo 4.5)
3. Clique no agente → tab **Playground** (canto superior direito)
4. No painel direito, mande mensagem de teste:
   - `"Como faço para resetar a senha de um cliente que perdeu acesso ao app?"`
5. Observe:
   - O agente decide chamar `search_kb` (você vê o tool call no chat)
   - Tool call **falha no Playground** (porque Playground não roda seu `agent_runner.py` — Playground é apenas inspeção do schema). Isso é esperado.
6. O valor pedagógico é confirmar visualmente: agente existe, tools registradas, system prompt aplicado.

<!-- screenshot: cap04-passo4.7-playground-agent.png -->

> **Nota pedagógica — Playground vs runner:** Playground roda no servidor Foundry e só exercita o **modelo** + **schema das tools** (vê se o agente decide chamar tool X com args Y). Não executa as tools (não tem acesso à sua RAG Function nem MCP nem SB). Para teste end-to-end, use `python agent_runner.py` localmente.

---

## Validação end-to-end

```powershell
# 1. Confirmar Project no Azure
az ml workspace show `
  --name aifproj-helpsphere-agente `
  --resource-group rg-lab-intermediario `
  --query "{name:name, kind:kind, location:location}" -o table
# Esperado: kind=project, location=eastus2

# 2. Confirmar deployment do modelo
az cognitiveservices account deployment show `
  --name aifhub-apex-prod `
  --resource-group rg-lab-intermediario `
  --deployment-name gpt-4.1-mini `
  --query "{name:name, status:properties.provisioningState, model:properties.model.name}" -o table
# Esperado: status=Succeeded, model=gpt-4.1-mini

# 3. Smoke run do agente
Set-Location agent-code
python agent_runner.py
# Esperado: print da Thread + tool call search_kb + Response em pt-BR com citações
```

> **Linux/Mac/WSL:** troque `` ` `` (backtick) por `\` e `Set-Location` por `cd`.

---

## Checklist final

```text
[ ] Project aifproj-helpsphere-agente criado no Hub aifhub-apex-prod
[ ] Deployment gpt-4.1-mini ativo (Succeeded, 30K TPM)
[ ] Project Connection String capturada e salva no .env
[ ] agent-code/ setup com venv + requirements.txt + .env preenchido
[ ] create_agent.py rodou e retornou agent.id (formato asst_xxx)
[ ] AGENT_ID adicionado ao .env
[ ] agent_runner.py smoke run completo (search_kb chama RAG real e retorna sugestão + citações)
[ ] Agente visível no Foundry Playground com 4 tools registradas
```

---

## Surpresas pedagógicas (capturadas em smoke runs)

- ⚠️ **`azure-ai-projects==1.0.0b9` em preview** — pinned hard. GA Q3-2026 vai ter breaking changes (`create_message` → `threads.messages.create`). Não atualize sem ler migration guide.
- ⚠️ **`gpt-4.1-mini` vs `gpt-4.1` pricing differential** — mini é ~5x mais barato. Para tier 1 (resoluções diretas), mini entrega 90% da qualidade. Para tier 2 (raciocínio complexo), suba pra `gpt-4.1` ou `gpt-5-thinking`.
- ⚠️ **Foundry Agent Service vs Assistants API legacy** — Assistants API (OpenAI direto) está deprecada em favor do Foundry Agent Service (Azure-native, integra Hub/Project/Threads). Use SEMPRE Foundry Agent Service neste lab.
- ⚠️ **`DefaultAzureCredential` cai em `InteractiveBrowserCredential` se `az login` expirou** — abre browser do nada no meio do script. Workaround: rode `az account get-access-token` antes pra confirmar sessão válida.
- ⚠️ **Tool call falha em Playground** — esperado. Playground só executa o modelo, não suas tools (RAG, MCP, SB). Para teste end-to-end, sempre `python agent_runner.py`.
- ⚠️ **`requires_action` infinito** — se o agente entra em loop chamando a mesma tool repetidamente, **o problema é tool retornando JSON inválido** ou **payload quebrado**. Adicione `print(json.dumps(result))` antes de `tool_outputs.append` pra debugar.

---

## Próximo capítulo

[05 — MCP Server Deploy](./05-mcp-server-deploy.md)
