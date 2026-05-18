# agent-code — Foundry Agent + Function App runner

Código Python do agente **`helpsphere-tier1-agent`** (Foundry Agent Service)
referenciado pelos Passos 3.3, 3.5 e 3.6 do
[guia Portal canônico](../docs/00-Lab_Final_Agente_Workflow_Guia_Portal.md).

## Estrutura

```
agent-code/
├── create_agent.py          # Passo 3.3 — registra agent + 4 tools no Foundry
├── agent_runner.py          # Passo 3.5 — handlers das tools + event loop run_agent()
├── requirements.txt         # deps locais (rodar create_agent.py + smoke)
└── func-agent-runner/       # Passo 3.6 — Function App wrapper HTTP
    ├── function_app.py
    ├── host.json
    └── requirements.txt
```

## TODOs do aluno (10% pedagógico)

1. **`create_agent.py`** — `SYSTEM_PROMPT`: customize tom, regras, scope da HelpSphere fictícia.
2. **`agent_runner.py`** — `ESCALATION_THRESHOLD`: ajuste o valor (default `0.5`); discuta trade-offs com a turma.

## SDK utilizado

- **`azure-ai-agents`** ≥ 1.0.0 (GA) — operações de Agent (create, threads, messages, runs)
- **`azure-ai-projects`** ≥ 2.1.0 (GA) — cliente guarda-chuva (não usado diretamente aqui, mas no requirements para futuras integrações como `client.get_openai_client()`)

> **Nota:** o SDK preview antigo `azure-ai-projects==1.0.0b9` foi descontinuado. Aceitava connection string formato `<region>.api.azureml.ms;...` (Foundry Hub-based legacy). A v2 GA usa o **endpoint URI direto** do Foundry Direct Project (formato `https://<hub>.services.ai.azure.com/api/projects/<project>`).

## Como achar o `AI_PROJECT_ENDPOINT`

No Portal AI Foundry (https://ai.azure.com):

1. Abra o **Project** dentro do seu Hub (não o Hub em si)
2. Na sidebar lateral direita ou em **Settings → Properties**, procure por **"Project endpoint"** ou **"Endpoint URI"**
3. URL no formato: `https://<hub-name>.services.ai.azure.com/api/projects/<project-name>`

Alternativa via Azure CLI:

```powershell
az rest --method get `
  --uri "https://management.azure.com/subscriptions/<sub>/resourceGroups/<rg>/providers/Microsoft.CognitiveServices/accounts/<hub-name>/projects/<project-name>?api-version=2024-10-01" `
  --query "properties.endpoints"
```

## Rodar `create_agent.py` local (1× para registrar o agent)

```powershell
cd agent-code
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt

# Endpoint URI do Foundry Project (formato novo Direct Project)
$env:AI_PROJECT_ENDPOINT = "https://<hub-name>.services.ai.azure.com/api/projects/<project-name>"

python create_agent.py
```

Saída esperada: `[+] Agent criado: asst_xxxxxxx`. Anote o `asst_xxxxxxx` — será o `AGENT_ID` do Function App.

## Deploy `func-agent-runner` como Function App

Veja **Passo 3.6** do guia. Resumo:

1. Criar Function App `func-agent-runner` (Linux, Python 3.11, Consumption)
2. Configurar Application Settings com TODAS as env vars que `agent_runner.py` consome:
   `AI_PROJECT_ENDPOINT`, `AGENT_ID`, `RAG_FUNCTION_URL`, `RAG_FUNCTION_KEY`,
   `MCP_SERVER_URL`, `MCP_TOKEN` (após Parte 4), `SERVICE_BUS_CONNECTION` (após Parte 7)
3. Deploy via VS Code Azure Functions ou `func azure functionapp publish func-agent-runner`

## Troubleshooting

| Sintoma | Causa | Fix |
|---------|-------|-----|
| `ModuleNotFoundError: No module named 'agent_runner'` no deploy (logs do worker) | `agent_runner.py` está fora da pasta `func-agent-runner/` e o `func publish` só zipa a pasta atual | Mover o arquivo: `Move-Item agent_runner.py func-agent-runner\` (já refletido no repo) |
| `az functionapp function list` retorna vazio depois de deploy "successful" + logs do host mostram `0 functions found (Custom)` em 1ms | Flex Consumption não descobriu programming model v2 (sem `@app.route` indexados) | Setar App Setting `AzureWebJobsFeatureFlags=EnableWorkerIndexing` + restart do Function App |
| `ValueError: Invalid connection string format` | Você está rodando código velho (b9) com a URL nova | Rode `pip install -U azure-ai-agents azure-ai-projects` e use `AI_PROJECT_ENDPOINT` (não mais `AI_PROJECT_CONNECTION_STRING`) |
| `KeyError: 'AGENT_ID'` | env var não configurada | Atualize App Settings após rodar `create_agent.py` |
| `Token tenant XXX does not match resource tenant` | `DefaultAzureCredential` pegou token de tenant errado (sub default do `az account` é de outro tenant) | `az account set --subscription <sub-id-do-foundry>` antes de rodar, ou trocar para `DefaultAzureCredential(tenant_id="<tenant-do-foundry>")` no código |
| `HttpResponseError: ... 401` | MI/credential sem permissão no Foundry Project | Atribua role **Azure AI User** ao Managed Identity (Container App ou Function App) no nível do Project |
| `404` no `/api/tickets/.../suggest` | URL da RAG Function App errada ou function key inválida | Confirme via `az functionapp keys list -g <rg> -n func-helpsphere-rag --query functionKeys.default` |
| `404` no MCP | URL não atualizada após Parte 4 | Atualize `MCP_SERVER_URL` no App Settings |
| Escalation não dispara | Service Bus connection vazia | Configure `SERVICE_BUS_CONNECTION` após Parte 7 |
