# Capítulo 04 — Foundry Agent SDK

> **Objetivo:** criar AI Foundry Project, deployar `gpt-4.1-mini`, criar agente Python via SDK e cravar 4 tools placeholder (search_kb, classify_intent, estimate_confidence, escalate_servicebus).
>
> **Tempo:** 60-90 min
>
> **Status:** `v0.1.0-init` skeleton — conteúdo Portal step-by-step real virá em pass posterior

---

## Outline

1. **Acessar AI Foundry portal `ai.azure.com`**
   - Sign in com mesma conta Azure
   - Navegar pra Hub `aifhub-apex-prod`

2. **Criar Project filho `proj-lab-final-{aluno}`**
   - New project
   - Hub: `aifhub-apex-prod`
   - Region: East US 2

3. **Deploy `gpt-4.1-mini`**
   - Project → Deployments → New deployment → gpt-4.1-mini
   - Capacity: 10K TPM (suficiente pro lab)
   - Capturar `endpoint` + `deployment name`

4. **Capturar Project Connection String**
   - Project → Settings → Properties
   - Copiar `connection string` (formato: `eastus2.api.azureml.ms;...`)

5. **Setup local `agent-code/`**
   - `cd agent-code`
   - `python -m venv .venv && source .venv/bin/activate` (ou `.venv\Scripts\activate` Windows)
   - `pip install -r requirements.txt`
   - Criar `.env` com `PROJECT_CONNECTION_STRING` + `MODEL_DEPLOYMENT_NAME`

6. **Criar agente via SDK**
   - Editar `agent.py` (skeleton já cravado neste repo)
   - Substituir tools placeholder por implementações reais (capítulo 05+)
   - `python agent.py` — smoke run mínimo

7. **Validar agente no Foundry portal**
   - Project → Agents → ver agente criado
   - Test playground → conversa simples

---

## Surpresas pedagógicas (TODO)

- [ ] gpt-4.1-mini vs gpt-4.1 — pricing differential
- [ ] Foundry Agent Service vs Assistants API legacy
- [ ] DefaultAzureCredential precedence (CLI → MI → ENV)

---

## Próximo capítulo

[05 — MCP Server Deploy](./05-mcp-server-deploy.md)
