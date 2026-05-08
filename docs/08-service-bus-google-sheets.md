# Capítulo 08 — Service Bus + Google Sheets Audit

> **Objetivo:** provisionar Service Bus Basic, criar topic `escalations`, conectar n8n, configurar Google Sheets audit trail. Apresenta também alternativa Logic App.
>
> **Tempo:** 45-60 min
>
> **Status:** `v0.1.0-init` skeleton — conteúdo Portal step-by-step real virá em pass posterior

---

## Outline

1. **Provisionar Service Bus Basic**
   - Portal Azure → Service Bus → Create namespace
   - Tier: Basic (free tier suficiente pro lab)
   - Region: East US 2

2. **Criar topic `escalations` + subscription `n8n-consumer`**
   - Service Bus → Topics → New
   - Topic name: `escalations`
   - Subscription: `n8n-consumer`
   - Lock duration: 30s

3. **Capturar connection string**
   - Service Bus → Shared access policies → RootManageSharedAccessKey
   - Copiar Primary Connection String (uso temporário no lab — produção: usar MI)

4. **Configurar credentials no n8n**
   - n8n → Credentials → New → Service Bus
   - Connection string (do step anterior)
   - Test connection

5. **Setup Google Sheets**
   - Criar spreadsheet "HelpSphere Escalations Audit"
   - Headers: `timestamp | ticket_id | severity | category | persona | summary | escalated_by`
   - Compartilhar com service account (criar via Google Cloud Console)

6. **Configurar credentials Google Sheets no n8n**
   - n8n → Credentials → New → Google Sheets OAuth2
   - Authorize com conta Google
   - Test connection

7. **Alternativa Logic App (apresentada como callout)**
   - Trigger: Service Bus message received
   - Action: Append row to Google Sheet
   - Trade-off: Logic App é PaaS Azure native vs n8n self-hosted no ACA

8. **Smoke test end-to-end**
   - Agent classifica ticket crítico
   - Foundry tool `escalate_servicebus` envia mensagem
   - n8n consume → append no Google Sheet
   - Validar audit trail aparece na linha nova

---

## Surpresas pedagógicas (TODO)

- [ ] Service Bus Basic não tem topics — só queues. Validar tier (Standard mínimo pra topics)
- [ ] Connection string vs MI — quando cada
- [ ] Logic App vs n8n — pricing + flexibility comparison

> **Nota crítica detectada no skeleton:** Service Bus Basic NÃO suporta Topics (apenas Queues). Para topics + subscriptions, **Standard** é mínimo (~R$ 50/mês). Capítulo 02 deve refletir isso quando v1.0.0 sair.

---

## Próximo capítulo

[09 — Cleanup Obrigatório](./09-cleanup-obrigatorio.md)
