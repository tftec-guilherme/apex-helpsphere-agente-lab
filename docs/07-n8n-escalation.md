# Capítulo 07 — n8n Escalation

> **Objetivo:** provisionar PostgreSQL Burstable (backend n8n), deploy n8n no ACA, setup inicial, importar workflow de escalation e ativar.
>
> **Tempo:** 60-90 min
>
> **Status:** `v0.1.0-init` skeleton — conteúdo Portal step-by-step real virá em pass posterior

---

## Outline

1. **Provisionar PostgreSQL Flexible Server**
   - Portal Azure → Azure Database for PostgreSQL → Flexible server → Create
   - Tier: Burstable B1ms (~R$ 60/mês — maior custo recorrente do lab)
   - Storage: 32GB
   - Authentication: PostgreSQL only
   - Database: `n8n`

2. **Configurar firewall PostgreSQL**
   - Allow Azure services
   - Allow client IP (pra setup local)

3. **Deploy n8n no ACA**
   - Image: `docker.io/n8nio/n8n:latest`
   - Env vars:
     - `DB_TYPE=postgresdb`
     - `DB_POSTGRESDB_HOST={postgres-fqdn}`
     - `DB_POSTGRESDB_DATABASE=n8n`
     - `DB_POSTGRESDB_USER={user}`
     - `DB_POSTGRESDB_PASSWORD={secret}` (Container App Secrets)
     - `N8N_BASIC_AUTH_ACTIVE=true`
     - `N8N_BASIC_AUTH_USER=admin`
     - `N8N_BASIC_AUTH_PASSWORD={secret}`
   - Ingress: External (HTTPS)
   - Target port: 5678

4. **Setup inicial n8n**
   - Acessar FQDN ACA
   - Login com basic auth
   - Owner setup wizard

5. **Importar workflow `escalation-servicebus-sheets.json`**
   - Workflows → Import from File
   - Upload `n8n-workflows/escalation-servicebus-sheets.json` deste repo
   - Configurar credentials (próximo step)

6. **Configurar credentials**
   - Service Bus connection string (capítulo 08)
   - Google Sheets OAuth (capítulo 08)
   - Slack Webhook (opcional)
   - Email SMTP (opcional)

7. **Activate workflow**
   - Toggle Activate on
   - Smoke test: enviar mensagem de teste pro Service Bus topic

---

## Surpresas pedagógicas (TODO)

- [ ] PostgreSQL Burstable é maior custo do lab (~R$ 60/mês) — pause/resume strategy
- [ ] n8n Owner setup só funciona 1ª vez — perda de password = recreate
- [ ] Workflow import file vs URL — file mais confiável

---

## Próximo capítulo

[08 — Service Bus + Google Sheets Audit](./08-service-bus-google-sheets.md)
