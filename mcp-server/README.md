# mcp-server — HelpSphere MCP Server

FastMCP server expondo 4 tools sobre o SQL Database `helpsphere` (stack
apex-helpsphere SaaS). Auth via Entra ID com decorator `@require_scope`.
Deploy em Azure Container Apps.

## Estrutura

```
mcp-server/
├── server.py            # FastMCP + 4 tools com @require_scope
├── auth.py              # Validação JWT Entra (decorator require_scope)
├── helpsphere_db.py     # Wrapper SQL HelpSphere (4 ops)
├── Dockerfile           # imagem para build via az acr build
└── requirements.txt
```

## TODOs do aluno (10% pedagógico)

1. **`server.py`** — `ticket_resource()`: customize formatação da resposta do recurso `helpsphere://tickets/{ticket_id}` (sugestões: incluir histórico de comentários, anexos, metadados de SLA).

## Build da imagem (Passo 4.2 do guia)

```powershell
cd mcp-server
$env:ACR_NAME = "<acrhelpsphere{rand}>"
az acr build `
  --registry $env:ACR_NAME `
  --image mcp-helpsphere:v1 `
  --file Dockerfile `
  .
```

## Deploy em Azure Container Apps (Passo 4.6)

Veja **Parte 4** completa do guia. Resumo:

1. ACA Environment criado (Passo 4.4)
2. RBAC `AcrPull` no Managed Identity do Container App (Passo 4.5)
3. Container App `ca-mcp-helpsphere` com env vars:
   - `HELPSPHERE_SQL_CONNECTION` — ODBC string apontando pro SQL `helpsphere`
   - `AZURE_TENANT_ID` — tenant Entra da App Registration (`ENTRA_TENANT_ID` aceito como fallback p/ retrocompat)
   - `EXPECTED_AUDIENCE` — `api://<server-app-client-id>`
4. Ingress external + target-port 8080

## Troubleshooting

| Sintoma | Causa provável | Fix |
|---------|----------------|-----|
| `tools/list` retorna `tools: []` | `EXPECTED_AUDIENCE` divergente do `aud` claim do token | Comparar `jq '.aud'` com `az containerapp show ... env` byte-a-byte (sem trailing slash) |
| `pyodbc.OperationalError: 28000` | MI sem permissão no DB `helpsphere` | Grant `CREATE USER FROM EXTERNAL PROVIDER` + role `db_datareader`/`db_datawriter` |
| CrashLoopBackoff no startup | `JWKS_URL` inacessível (network rules) | Validar egress to `login.microsoftonline.com:443` |
| `401` em tool call | scope ausente no token | Confirmar que Entra App Registration expõe `helpsphere.tickets.read`/`.write` e client requisita |
