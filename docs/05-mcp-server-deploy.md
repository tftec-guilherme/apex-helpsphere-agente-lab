# Capítulo 05 — MCP Server Deploy

> **Objetivo:** build Docker image MCP Server, push pra ACR, deploy ACA, criar 2 App Registrations (server + client) e plugar no Foundry agent como tool.
>
> **Tempo:** 60-90 min
>
> **Status:** `v0.1.0-init` skeleton — conteúdo Portal step-by-step real virá em pass posterior

---

## Outline

1. **Build local Docker image**
   - `cd mcp-server`
   - `docker build -t mcp-helpsphere:v0.1 .`
   - Validar: `docker run --rm -it mcp-helpsphere:v0.1 python -c "import server"`

2. **Push pra Azure Container Registry**
   - `az acr login --name acrlabfinal{aluno}`
   - `docker tag mcp-helpsphere:v0.1 acrlabfinal{aluno}.azurecr.io/mcp-helpsphere:v0.1`
   - `docker push acrlabfinal{aluno}.azurecr.io/mcp-helpsphere:v0.1`

3. **Deploy ACA via Portal**
   - Container Apps Environment → Create container app
   - Image source: ACR `acrlabfinal{aluno}.azurecr.io/mcp-helpsphere:v0.1`
   - Identity: Managed Identity `mi-lab-final` (criada no cap 02)
   - Ingress: Internal (HTTP)
   - Target port: 8080
   - Capturar FQDN interno

4. **Criar 2 App Registrations**
   - **Server App Reg** (`mcp-server-helpsphere`):
     - Expose API → Application ID URI: `api://mcp-server-helpsphere`
     - Add scope `mcp.access`
   - **Client App Reg** (`mcp-client-foundry`):
     - API permissions → Add → My APIs → `mcp-server-helpsphere` → `mcp.access` → Grant admin consent
     - Client secret → criar (capturar 1x)

5. **Configurar Foundry agent pra usar MCP**
   - Em `agent.py`, plugar MCP client com endpoint ACA + credentials Client App Reg
   - Implementar tool `search_kb` chamando MCP Server `search_helpsphere_kb`

6. **Smoke test end-to-end**
   - Rodar `agent.py` com prompt: "Como funciona devolução de pedido?"
   - Validar: agent → MCP Server → AI Search (do `apex-rag-lab`) → resposta com citação

---

## Surpresas pedagógicas (TODO)

- [ ] MCP spec atual vs evolução (cravar `version-anchor: Q2-2026`)
- [ ] 2 App Regs obrigatório (single-app falha — referência feedback `apex-helpsphere`)
- [ ] ACA Internal vs External ingress — security implication

---

## Próximo capítulo

[06 — Speech (STT/TTS)](./06-speech-stt-tts.md)
