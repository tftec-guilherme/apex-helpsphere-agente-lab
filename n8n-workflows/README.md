# n8n Workflows — HelpSphere Escalation

> Templates JSON pra n8n self-hosted (ACA — capítulo 07).
>
> `version-anchor: Q2-2026` · `status: v0.1.0-init`

---

## Workflows

### `escalation-servicebus-sheets.json`

**Pipeline:** Service Bus topic `escalations` → filter severity → switch → 3 branches paralelos:
1. **Google Sheets append** — audit trail completo
2. **Slack webhook** — notify ops channel
3. **Email** — notify on-call

7 nodes total.

---

## Como importar

1. Acessar n8n UI (FQDN ACA do capítulo 07)
2. Login com basic auth (configurado em capítulo 07)
3. Sidebar → **Workflows** → botão **Import from File**
4. Upload `escalation-servicebus-sheets.json` deste diretório
5. Workflow aparece com **active: false** (intencional — ativar depois de configurar credentials)

---

## Setup credentials (obrigatório antes de ativar)

O workflow usa **4 credentials externos**, parametrizados via env vars (`{{ $env.X }}`):

### 1. Service Bus connection string

- Variable: `SERVICE_BUS_CRED_ID`
- n8n → **Credentials** → **New** → **Azure Service Bus**
- Nome: `HelpSphere Service Bus`
- Connection String: capturada no capítulo 08 (Shared access policy `RootManageSharedAccessKey`)
- **Test connection** antes de salvar

### 2. Google Sheets OAuth2

- Variable: `SHEETS_OAUTH_CRED_ID` + `GOOGLE_SHEET_ID`
- n8n → **Credentials** → **New** → **Google Sheets OAuth2 API**
- Nome: `HelpSphere Sheets OAuth`
- Authorize com conta Google (browser flow)
- Capturar Sheet ID da URL: `https://docs.google.com/spreadsheets/d/{SHEET_ID}/edit`
- Adicionar `GOOGLE_SHEET_ID` em **Settings → Variables** do n8n

### 3. Slack Webhook (opcional)

- Variable: `SLACK_WEBHOOK_URL`
- Criar Incoming Webhook no Slack workspace: https://api.slack.com/messaging/webhooks
- Adicionar `SLACK_WEBHOOK_URL` em **Settings → Variables**
- Se não quiser Slack, **delete** o node "HTTP: Slack Notify" do workflow

### 4. SMTP Email

- Variable: `SMTP_CRED_ID` + `EMAIL_FROM` + `EMAIL_TO`
- n8n → **Credentials** → **New** → **SMTP**
- Nome: `HelpSphere SMTP`
- Host/Port/User/Password: SMTP do prof ou seu próprio
- Adicionar `EMAIL_FROM` e `EMAIL_TO` em **Settings → Variables**

---

## Como ativar

1. Após configurar os 4 credentials acima
2. Abrir o workflow
3. Toggle **Active** (canto superior direito) → **on**
4. Smoke test:
   ```bash
   az servicebus topic message send \
     --resource-group rg-lab-final-{aluno} \
     --namespace-name sb-lab-final-{aluno} \
     --topic-name escalations \
     --body '{"ticket_id":"T-TEST-001","severity":"CRITICAL","category":"sap-integration","persona":"diego","summary":"Test escalation"}'
   ```
5. Validar: linha nova no Google Sheet + mensagem no Slack + email recebido

---

## Troubleshooting

### Service Bus Trigger não recebe mensagens

- Verificar `azureServiceBusApi` credentials test connection
- Verificar topic `escalations` + subscription `n8n-consumer` existem (Portal Azure)
- Verificar Service Bus tier — **Basic NÃO suporta topics** (precisa Standard mínimo)

### Google Sheets append falha 403

- Service account não tem acesso ao sheet
- Compartilhar sheet com email do service account explícito (`...@iam.gserviceaccount.com`)

### Slack webhook 404

- Webhook URL revogada — recriar em https://api.slack.com/apps

### Email falha 535 auth

- Senha SMTP errada ou app password necessário (Gmail/Outlook)
- Habilitar app passwords se 2FA ativo

---

## Suporte

- **Issues:** https://github.com/tftec-guilherme/apex-helpsphere-agente-lab/issues
- **n8n docs:** https://docs.n8n.io/
