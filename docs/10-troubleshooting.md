# Capítulo 10 — Troubleshooting

> **Objetivo:** consolidar gotchas comuns + soluções rápidas pros 9 capítulos anteriores.
>
> **Status:** `v0.1.0-init` skeleton — conteúdo step-by-step real virá em pass posterior, populado a partir de smoke runs reais

---

## Outline

### Cap 01 — Pré-requisitos

- [ ] Quota Azure OpenAI rejected → como abrir support ticket
- [ ] Foundry Hub `aifhub-apex-prod` não aparece → verificar Pré-aula 1 D06 cravada
- [ ] Copilot Studio Trial não ativa em conta `live.com` → migrar pra Work or School

### Cap 02 — RG + ACR + ACA

- [ ] ACR name conflict (globally unique) → adicionar shortToken
- [ ] ACA Environment provisioning fica em "Updating" >10min → recreate em outra region

### Cap 03 — Copilot Studio

- [ ] Agente não responde em pt-BR → verificar Language setting
- [ ] Topics não match → habilitar Generative AI orchestration

### Cap 04 — Foundry Agent SDK

- [ ] `azure.ai.projects` import error → reinstalar com `pip install -U azure-ai-projects`
- [ ] `DefaultAzureCredential` falha local → `az login` antes de rodar
- [ ] Connection string formato inválido → copiar limpo do Foundry portal

### Cap 05 — MCP Server

- [ ] `docker build` falha em Windows → habilitar WSL 2 backend
- [ ] ACR push 401 → `az acr login` re-autenticar
- [ ] ACA pull image `ImagePullBackOff` → MI sem `AcrPull` role
- [ ] 2 App Regs admin consent não propaga → aguardar 5min ou re-grant
- [ ] MCP server returns 401 → audience mismatch v1 vs v2 (referência feedback `apex-helpsphere` Surpresa #46)

### Cap 06 — Speech

- [ ] `Speech_AuthenticationFailure` → MI sem role `Cognitive Services Speech User`
- [ ] pt-BR voice "FranciscaNeural" não encontrada → region não suporta (apenas East US 2 + algumas)

### Cap 07 — n8n

- [ ] PostgreSQL connection timeout → firewall não permite ACA outbound
- [ ] n8n Owner password perdido → recreate ACA + drop database (perdas workflows)
- [ ] Workflow import "Invalid JSON" → validar `n8n-workflows/escalation-servicebus-sheets.json` com `jq`

### Cap 08 — Service Bus + Google Sheets

- [ ] Service Bus Basic NÃO suporta Topics → upgrade pra Standard
- [ ] Google Sheets OAuth refresh token expira → re-authorize no n8n
- [ ] Service account sem acesso ao sheet → compartilhar email service account explícito

### Cap 09 — Cleanup

- [ ] `az group delete` falha com lock → remover lock manual
- [ ] PostgreSQL deletion stuck → force delete via Portal

---

## Cleanup obrigatório (recap final)

```bash
az group delete --name rg-lab-final-{aluno} --yes --no-wait
```

Confirme deletion completa em 30 min via:

```bash
az group show --name rg-lab-final-{aluno}
# Esperado: GroupNotFound (404)
```

---

## Suporte

- **Issues:** https://github.com/tftec-guilherme/apex-helpsphere-agente-lab/issues
- **Prof Guilherme Campos** — disponível via TFTEC
