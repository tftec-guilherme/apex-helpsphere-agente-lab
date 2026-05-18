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

## Rodar `create_agent.py` local (1× para registrar o agent)

```powershell
cd agent-code
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt

# Connection string do Foundry Project (em ai.azure.com → Project → Settings)
$env:AI_PROJECT_CONNECTION_STRING = "<sua-connection-string>"
$env:RAG_FUNCTION_URL  = "https://func-helpsphere-rag-{rand}.azurewebsites.net"
$env:RAG_FUNCTION_KEY  = "<key>"
$env:MCP_SERVER_URL    = "https://placeholder"  # ate Parte 4

python create_agent.py
```

Saída esperada: `[+] Agent criado: asst_xxxxxxx`. Anote o `asst_xxxxxxx` — será o `AGENT_ID` do Function App.

## Deploy `func-agent-runner` como Function App

Veja **Passo 3.6** do guia. Resumo:

1. Criar Function App `func-agent-runner` (Linux, Python 3.11, Consumption)
2. Configurar Application Settings com TODAS as env vars que `agent_runner.py` consome:
   `AI_PROJECT_CONNECTION_STRING`, `AGENT_ID`, `RAG_FUNCTION_URL`, `RAG_FUNCTION_KEY`,
   `MCP_SERVER_URL`, `MCP_TOKEN` (após Parte 4), `SERVICE_BUS_CONNECTION` (após Parte 7)
3. Deploy via VS Code Azure Functions ou `func azure functionapp publish func-agent-runner`

## Troubleshooting

| Sintoma | Causa | Fix |
|---------|-------|-----|
| `KeyError: 'AGENT_ID'` | env var não configurada | Atualize App Settings após rodar `create_agent.py` |
| `TimeoutError` na primeira call | Cold start do plano Consumption | Aguarde 5-10s, ou use Premium plan |
| `404` no MCP | URL não atualizada após Parte 4 | Atualize `MCP_SERVER_URL` no App Settings |
| Escalation não dispara | Service Bus connection vazia | Configure `SERVICE_BUS_CONNECTION` após Parte 7 |
