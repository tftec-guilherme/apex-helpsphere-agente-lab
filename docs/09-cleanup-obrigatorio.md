# Capítulo 09 — Cleanup Obrigatório

> **Objetivo:** zerar o **custo recorrente** deste lab em < 15 min: deletar o RG `rg-lab-final` (apaga ACR, ACA Env, MCP Server, n8n, **PostgreSQL Burstable B1ms — maior dreno**, Speech, Service Bus Standard), deletar o **Foundry Project `aifproj-helpsphere-agente`** (separado do Hub `aifhub-apex-prod` que continua vivo para outros usos), desativar/deletar o agent Copilot Studio `HelpSphere Tier 1 Agent` (trial 30d expira sozinho, mas consome licença até lá), remover as **3 App Registrations** (`app-mcp-helpsphere-server` + `app-mcp-helpsphere-client` + `app-n8n-graph` se você executou a configuração de envio de e-mail via Graph) que ficam órfãs no tenant Entra, e validar zero billing residual no **Cost Management** após 24-48h de delay de telemetria.
>
> **Tempo:** 10-15 min execução + 24-48h espera para Cost Management refletir

---

## Pré-requisitos

- ✅ Capítulos anteriores executados — todo o estado provisionado existe (RG `rg-lab-final` populado, Foundry Project ativo, Copilot Studio agent criado)
- ✅ Demo final dos tickets **gravada/screenshot** + logs/threads/dead-letter relevantes exportados — depois deste cap, **nada volta**
- ✅ `az` CLI logado na sub correta (`az account show -o table` confirma)
- ✅ Permissão `Owner`/`Contributor` no `rg-lab-final` + `Application Developer`/`Cloud Application Administrator` no tenant Entra (Passo 9.4)

> [!IMPORTANT] **Tier / Licenciamento — custo recorrente**
> Este lab introduz 3 recursos que cobram parados em `rg-lab-final`: PostgreSQL Burstable B1ms (~R$ 60/mês), ACR Basic (~R$ 35/mês), Service Bus Standard (~R$ 50/mês). Soma: ~R$ 145/mês esquecidos. Sem cleanup: 30 dias = R$ 145 debitados sem tráfego; em Free Trial USD 200, queima crédito sem o aluno entender por quê.

> **Atenção breaking — pause/resume vs delete definitivo:** o capítulo do workflow n8n oferece **Stop temporário** (PG + ACA n8n) para sessões recorrentes. Este cap é **delete definitivo** — caminho oposto. Não misture: Stop do PG + delete do RG falha porque o RG só deleta com PG em estado `Ready` (não `Stopped`).

---

## Resumo dos 5 alvos de cleanup

| Alvo | Onde vive | Custo se esquecer (R$/mês) |
|---|---|---|
| **RG `rg-lab-final`** (ACR + ACA Env + MCP + n8n + PG + Speech + Service Bus) — **crítico** | Sub Azure → `rg-lab-final` | ~R$ 145 fixo + variável |
| **Foundry Project `aifproj-helpsphere-agente`** — não está no `rg-lab-final` | Hub `aifhub-apex-prod` em `rg-lab-intermediario` | R$ 1-2/mês storage idle de threads |
| **Copilot Studio agent `HelpSphere Tier 1 Agent`** — trial expira 30d sozinho | Power Platform tenant | R$ 0 trial · R$ 1.000+/mês Per-User Premium |
| **3 App Registrations Entra** (`app-mcp-helpsphere-server`/`-client` + `app-n8n-graph` se Graph email configurado) | Tenant Entra | R$ 0 mas client secret 90d = vetor de ataque |
| **`rg-lab-intermediario`** (Hub + MI + LA pré-existentes de labs anteriores) — **NÃO delete se vai reaproveitar em outro lab** | RG `rg-lab-intermediario` | ~R$ 30/mês (Passo 9.6) |

> **Nota pedagógica — por que `az group delete` resolve 80% mas não 100% + matriz de soft-delete:** delete do RG é cascade local mas este lab tem 3 dependências **cross-RG/cross-tenant** órfãs: (1) Foundry **Project** vive sob o Hub em `rg-lab-intermediario`, (2) **App Registrations** vivem em tenant Entra, (3) **Copilot Studio agent** vive em Power Platform. Por isso o cleanup é em **5 passos separados**, não 1. Soft-delete varia por recurso: RG não tem (delete = definitivo), Key Vault tem 90d default, App Reg 30d, Foundry workspace 14d. Key Vault em soft-delete impede recriar com mesmo nome — `az keyvault purge` ou esperar 90d.

---

## Passo 9.1 — Confirmar que terminou (gate de segurança)

Antes de qualquer comando destrutivo, confirme o checklist:

```text
[ ] Demo final dos tickets executada e validada
[ ] Screenshots / vídeo de evidência salvos fora do Azure (laptop local, OneDrive pessoal)
[ ] Threads do agent Foundry exportadas via SDK (`client.agents.list_threads()` → JSON local) se você quer analisar offline
[ ] Logs do App Insights exportados via Kusto (export to CSV) se relevantes
[ ] Confirmou que NÃO vai reaproveitar `rg-lab-intermediario` em outro lab em sequência (se vai, NÃO delete — ver Passo 9.6)
```

> **Nota pedagógica — gate de confirmação humana é Defense in Depth:** todo comando destrutivo do Azure CLI exige `--yes` explícito proposital. Não automatize este capítulo em CI — é manual obrigatório. Casos clássicos de cleanup automatizado destrutivo (GitLab 2017, AWS S3 órfãos) reforçam: 5 segundos extras digitando `rg-lab-final` no Portal vale a pausa.

---

## Passo 9.2 — Deletar RG `rg-lab-final` (cleanup principal)

**No Portal Azure:**

1. Abra `https://portal.azure.com` → barra superior → buscar **"Resource groups"** → clicar
2. Clique no RG `rg-lab-final`
3. Tab **Overview** → botão **Delete resource group** (topo)
4. Painel direito: digite o nome `rg-lab-final` no campo de confirmação (case-sensitive)
5. ⚠️ **Pause antes de clicar Delete:** o Portal lista **todos os recursos** que serão deletados — confira que aparece **PostgreSQL `pg-n8n-<rand>`** (PG Burstable do n8n), **Container Apps `ca-mcp-helpsphere`+`ca-n8n-helpsphere`**, **ACR `acrhelpsphere<rand>`**, **ACA Env `cae-helpsphere-final`**, **Speech `spch-helpsphere`**, **Service Bus `sb-helpsphere-final`**. Se faltar algum desses, **pare** — pode ter ido para outro RG por engano.
6. Clique **Delete**
7. Notificação no sino superior: "Deleting resource group rg-lab-final" → aguarde **3-5 min** (PG Flexible Server demora mais que ACA Consumption)
8. Sucesso: notificação "Resource group rg-lab-final has been deleted"

<!-- screenshot: cap09-passo9.2-delete-rg-portal.png -->

> **Alternativa via Azure CLI (PowerShell 7 — Windows-first, recomendada — mais rápida e síncrona):**
>
> ```powershell
> # Pré-flight: listar o que vai morrer (NÃO destrutivo)
> az resource list --resource-group rg-lab-final `
>   --query "[].{name:name, type:type, location:location}" -o table
>
> # Delete síncrono (você acompanha o progresso)
> az group delete --name rg-lab-final --yes
> # ~3-5 min até voltar prompt
>
> # OU delete assíncrono (retorna imediato, deletion roda em background)
> az group delete --name rg-lab-final --yes --no-wait
>
> # Validar que sumiu (~5 min depois para o Azure CRP propagar)
> az group show --name rg-lab-final 2>&1 | Select-String -Pattern "could not be found|ResourceGroupNotFound"
> # Esperado: "Resource group 'rg-lab-final' could not be found."
> ```
>
> **Linux/Mac/WSL:** troque `` ` `` (backtick) por `\` e `Select-String -Pattern` por `grep -E`.

> **Custo:** R$ 0 — operação delete em si é gratuita. **Economia:** ~R$ 145/mês recorrente que para imediatamente (compute) e em ~24h no billing report.

> **Nota pedagógica — síncrono vs `--no-wait` + Resource Locks:** delete síncrono (`az group delete --yes`) bloqueia até concluir e mostra erro na hora se algum recurso falhar (lock, policy, dependência cross-RG); `--no-wait` retorna em 2s mas **mascara erros silenciosos**. Para lab manual: síncrono. **Resource Locks** tipo `CanNotDelete` cravados em recursos críticos pelo admin do tenant fazem delete falhar sem mensagem clara ("Operation completed with errors") — antes de tentar de novo: Portal → RG → **Settings → Locks** → remover.

---

## Passo 9.3 — Deletar Foundry Project `aifproj-helpsphere-agente`

⚠️ **Importante:** o Foundry Project NÃO está no `rg-lab-final`. Ele vive no `rg-lab-intermediario` sob o Hub `aifhub-apex-prod`. O delete do `rg-lab-final` no Passo 9.2 **NÃO removeu o Project**.

**No Azure AI Foundry portal:**

1. Abra `https://ai.azure.com` → faça login com a mesma conta Azure
2. Tela inicial → seção **Projects** (não Hubs) → localize `aifproj-helpsphere-agente`
3. Clique nos três pontos `⋮` ao lado do nome → **Delete project**
4. Confirme digitando o nome → **Delete**
5. Aguarde ~30s-1min até sumir da lista
6. Confirme que o **Hub `aifhub-apex-prod` continua existindo** (compartilhado entre múltiplos labs/turmas — NUNCA delete)

<!-- screenshot: cap09-passo9.3-delete-foundry-project.png -->

> **Alternativa via Azure CLI (PowerShell 7 — Windows-first):**
>
> ```powershell
> az ml workspace delete `
>   --name aifproj-helpsphere-agente `
>   --resource-group rg-lab-intermediario `
>   --yes `
>   --no-wait
>
> # Validar que sumiu
> az ml workspace list `
>   --resource-group rg-lab-intermediario `
>   --query "[?kind=='Project'].{name:name, kind:kind}" -o table
> # Esperado: linha aifproj-helpsphere-agente NÃO aparece
> ```
>
> **Linux/Mac/WSL:** troque `` ` `` (backtick) por `\` no fim das linhas.

> **Custo:** R$ 0 — Project é metadata gratuita. Se o Project tinha **threads ativas** (conversas), elas usam storage do Hub (~R$ 1-2/mês até delete). Após Project delete, threads são purgadas em ~24h.

> **Atenção storage residual:** mesmo após Project delete o storage account do Hub mantém threads em soft-delete por ~24-48h antes de purgar fisicamente. Cobrança zera no momento do delete (compute), mas o blob persiste — não estranhe ver bytes ainda alocados em **Hub → Settings → Storage** no dia seguinte.

> **Nota pedagógica — Project vs Hub + soft-delete 14d:** o **Project** carrega agent + threads + conexões; o **Hub** carrega storage + App Insights + Key Vault + **deployment do `gpt-4.1-mini` compartilhado**. Deletar Project NÃO deleta o deployment do modelo (continua no Hub cobrando por token). Para zerar 100% o billing do modelo: **AI Foundry → Hub → Models + endpoints → `gpt-4.1-mini` → Delete deployment** — mas **só se ninguém mais usa o Hub**. Foundry workspaces têm **soft-delete 14d** (Hub → **Settings → Deleted projects → Restore** se deletou por engano).

---

## Passo 9.4 — Deletar App Registrations órfãs do tenant Entra

O Passo 9.2 deletou recursos Azure RM mas **App Registrations vivem no tenant Entra**, fora do escopo do RG. Sobram 2-3 App Registrations órfãs com **client secrets válidos por 90 dias** — vetor de ataque até expirarem.

**Lista de App Regs criadas durante este lab (verifique cada uma):**

| App Reg | Origem | Client Secret? |
|---|---|---|
| `app-mcp-helpsphere-server` | MCP Server (resource app) | Não (só Application ID URI + scopes) |
| `app-mcp-helpsphere-client` | MCP Server (client app) | **Sim — 90 dias** ⚠️ |
| `app-n8n-graph` (se configurou envio de e-mail via Microsoft Graph) | n8n Graph workflow | **Sim — 90 dias** ⚠️ |

**No Portal Azure:**

1. Barra superior → buscar **"App registrations"** → clicar
2. Tab **All applications** → search bar → filtre por `helpsphere` ou `n8n-graph`
3. Para cada App Reg listada acima:
   - Clique no nome da app → tab **Overview**
   - Botão **Delete** (topo)
   - Confirme **Delete** no painel
   - Notificação verde: "Application has been deleted"
4. Repita para as 2-3 App Regs

<!-- screenshot: cap09-passo9.4-delete-app-registrations.png -->

> **Alternativa via Azure CLI (PowerShell 7 — Windows-first):**
>
> ```powershell
> # Listar candidatas órfãs (nomes contendo "helpsphere" ou "n8n-graph")
> az ad app list `
>   --filter "startswith(displayName, 'app-mcp-helpsphere') or startswith(displayName, 'app-n8n')" `
>   --query "[].{name:displayName, appId:appId}" -o table
>
> # Delete por appId (repita para cada uma)
> az ad app delete --id <appId-de-app-mcp-helpsphere-server>
> az ad app delete --id <appId-de-app-mcp-helpsphere-client>
> az ad app delete --id <appId-de-app-n8n-graph>  # se Graph email configurado
>
> # Validar que sumiram
> az ad app list `
>   --filter "startswith(displayName, 'app-mcp-helpsphere')" `
>   --query "length(@)"
> # Esperado: 0
> ```
>
> **Linux/Mac/WSL:** troque `` ` `` (backtick) por `\` no fim das linhas.

> **Custo:** R$ 0 — App Registrations são gratuitas (sem cobrança independente do número).

> **Nota pedagógica — soft-delete 30d + por que secret órfão é vetor de ataque:** App Regs ficam em **soft-deleted 30d** (Portal Entra → **App registrations** → tab **Deleted applications** → Restore ou Permanently delete). O `app-mcp-helpsphere-client` tem **client secret válido por 90d** — se vazou em log/screenshot/`.env` pushado por engano em repo público, atacante usa o OAuth flow do tenant até expiração mesmo com o app vivo. Deletar App Reg **invalida o secret na hora** — proteção #1 pós-lab.

> **Atenção Service Principal órfão:** alguns enterprise applications (Service Principals) podem persistir mesmo após delete da App Registration. Verifique em **Entra ID → Enterprise applications → All applications → filter "helpsphere"** — se aparecer Service Principal correspondente, delete também (`az ad sp delete --id <objectId>`).

---

## Passo 9.5 — Desativar/deletar Copilot Studio agent `HelpSphere Tier 1 Agent`

Power Platform vive em tenant separado, fora do Azure RM — único caminho é manual via portal Copilot Studio. Trial 30d expira sozinho, mas até lá ocupa licença e suja auditoria.

**No Power Platform / Copilot Studio:**

1. `https://copilotstudio.microsoft.com/` → login com a conta M365 usada na criação → confirme **environment Development** no header (não `Default`)
2. Sidebar esquerdo → **Agents** → localize `HelpSphere Tier 1 Agent`
3. Três pontos `⋮` → **Delete copilot** (recomendado se terminou) **OU** **Disable** (se vai refazer demo depois) → confirme

<!-- screenshot: cap09-passo9.5-delete-copilot-studio-agent.png -->

> **Custo:** R$ 0 em trial. **Per-User Premium**: delete libera R$ 1.000+/mês imediato. **Pay-As-You-Go**: para contagem de mensagens (R$ 0,07/msg).

> ⚠️ **Topics customizadas NÃO são deletadas pelo Delete copilot via portal** — se você criou Topics adicionais (além das default Greeting/Goodbye/Escalate), o **Delete copilot** marca o agent como deletado mas as Topics customizadas ficam órfãs no environment. Antes de clicar Delete: **Agent → tab Topics → selecione cada Topic custom → ⋮ → Delete topic** uma a uma. Só depois delete o copilot.

> **Nota pedagógica — agent vs environment Development:** deletar o agent não deleta o environment Power Platform Development (continua vazio e listado em **Power Platform Admin Center → Environments**). Em tenant dev grátis não cobra parado — pode ficar; em corporate, delete via role `Power Platform Administrator`.

---

## Passo 9.6 — Decidir destino de `rg-lab-intermediario`

⚠️ **Decisão crítica — não automatize.** O `rg-lab-intermediario` carrega **Foundry Hub `aifhub-apex-prod`** + **MI `mi-helpsphere-ia`** + **Log Analytics `log-helpsphere-ia`** + Key Vault + AI Search + a aplicação SaaS HelpSphere que serve de baseline para o agente.

| Cenário | Ação | Custo recorrente |
|---|---|---|
| Vou reaproveitar o Hub em outro lab amanhã/semana | **NÃO delete** | ~R$ 30-40/mês (Hub idle + LA 5 GiB free) |
| Terminei tudo, não vou usar mais | `az group delete --name rg-lab-intermediario --yes` | R$ 0 |
| Vou repetir este lab | Preserve (Hub + MI custosos de recriar) | ~R$ 30-40/mês |

> **Custo:** delete zera compute. Storage idle do Log Analytics (R$ 12/GiB/mês além dos 5 GiB free) e Key Vault em soft-delete 90d (R$ 0 mas ocupa nome) persistem até purga. Deletar o RG também **derruba a aplicação SaaS HelpSphere** — exporte dados antes se quer continuar testando a aplicação fora deste lab.

---

## Passo 9.7 — Validação visual no Cost Management (24-48h delay obrigatório)

Cost Management tem **delay de 24-48h** entre delete e dado refletido. Validações imediatas (RG/Project/AppReg sumiram) já estão na **Validação end-to-end** abaixo. Esta é a **validação visual final** — sem ela, você não tem certeza de que o cleanup zerou efetivamente o billing.

**24-48h depois — No Portal Azure:**

1. Barra superior → buscar **"Cost Management + Billing"** → clicar
2. Menu lateral → **Cost analysis**
3. No topo da tela → **Scope** → confirme que está na subscription correta (mesma onde estava `rg-lab-final`)
4. Painel **Add filter** → **Resource group name** → selecionar `rg-lab-final` → Apply
5. Date range (canto superior direito) → **Last 7 days**
6. **Validação visual esperada:**
   - Gráfico de barras mostra custo decrescente nos dias após o delete
   - Últimos 1-2 dias (após delay de telemetria) mostram **R$ 0,00** ou linha plana no eixo zero
   - **Total accumulated cost** no topo bate com o que você gastou durante o lab (~R$ 20-30 para lab de 4-8h)
7. Se custo > R$ 0 nos últimos 2 dias após o delete: **Group by → Service name** para identificar o recurso órfão (raro — Cosmos DB free tier residual, Public IP standalone, Reserved capacity pré-comprada)
8. ⚙️ **Crave proteção permanente** (faça agora, leva 2 min): **Cost Management → Cost alerts → + Add → Anomaly alert → threshold R$ 50 → scope subscription → email** → Save. R$ 0 fixo, dispara alerta automático se algum lab futuro esquecer um RG ligado.

<!-- screenshot: cap09-passo9.7-cost-analysis-pos-cleanup.png -->

> **Custo:** R$ 0 (Cost Management é gratuito — nem entra no quota de telemetria).

> **Nota pedagógica — 3 fontes de billing "fantasma":** (1) **Storage idle** de Key Vault soft-deleted ou Log Analytics retido (R$ 1-5/mês até purga), (2) **Reserved capacity** comprada antes (cobra mesmo sem uso — só cancela contrato), (3) **Marketplace items** (Apify/SendGrid cobram independente do RG). O Anomaly Alert (passo 8 acima) cobre as três com R$ 0 fixo, permanente. Crave antes do próximo lab.

---

## Validação end-to-end

```powershell
# 1. RG rg-lab-final sumiu
az group exists --name rg-lab-final
# Esperado: false

# 2. Foundry Project sumiu (mas Hub continua)
az ml workspace list `
  --resource-group rg-lab-intermediario `
  --query "[?name=='aifproj-helpsphere-agente']" -o tsv
# Esperado: linha vazia (Project deletado)

az ml workspace show `
  --name aifhub-apex-prod `
  --resource-group rg-lab-intermediario `
  --query "kind" -o tsv
# Esperado: Hub (continua vivo)

# 3. App Regs sumiram
az ad app list `
  --filter "startswith(displayName, 'app-mcp-helpsphere')" `
  --query "length(@)"
# Esperado: 0

# 4. Cost Management 24-48h depois (telemetria atrasa) — Portal → Cost analysis → filter rg-lab-final → últimos 2 dias = R$ 0
```

> **Linux/Mac/WSL:** troque `` ` `` (backtick) por `\` no fim das linhas.

---

## Checklist final

```text
[ ] Demo final dos tickets executada e evidência salva fora do Azure
[ ] Threads do agent Foundry exportadas se necessário (snippet Passo 9.1)
[ ] RG rg-lab-final deletado (cascade: ACR + ACA Env + MCP + n8n + PG + Speech + Service Bus)
[ ] Foundry Project aifproj-helpsphere-agente deletado (separado do Hub)
[ ] Hub aifhub-apex-prod PRESERVADO (compartilhado entre labs)
[ ] App Registrations órfãs deletadas (app-mcp-helpsphere-server + app-mcp-helpsphere-client + app-n8n-graph se Graph email configurado)
[ ] Service Principals correspondentes verificados em Enterprise applications
[ ] Topics customizadas do Copilot Studio deletadas ANTES do Delete copilot
[ ] Copilot Studio agent HelpSphere Tier 1 Agent deletado ou desabilitado
[ ] Decisão tomada sobre rg-lab-intermediario: preservar para próximo lab OU deletar
[ ] (24-48h depois) Cost Management confirma R$ 0 no escopo rg-lab-final
[ ] Azure Cost Anomaly Alert R$ 50 cravado na sub (proteção permanente)
[ ] Custo total do lab realizado: ≤ R$ 30 (alvo do lab cleanup-em-4-8h)
```

---

## Surpresas pedagógicas (capturadas em smoke runs)

- ⚠️ **Delete do `rg-lab-final` NÃO deleta o Foundry Project** — Project vive no `rg-lab-intermediario` sob o Hub. O aluno pensa "deletei o RG, acabou", mas o Project fica órfão consumindo storage idle (~R$ 1-2/mês) + threads cifradas. Workaround: cleanup em **5 passos separados** (este capítulo) — não confie em delete cascade do RG sozinho.
- ⚠️ **`az group delete` falha silently se houver Resource Lock** — admin do tenant pode ter cravado lock `CanNotDelete` em recursos críticos (ACR Premium, Log Analytics em compliance). Comando termina com "Operation completed with errors" sem detalhar qual recurso. Workaround: Portal → RG → **Settings → Locks** → remover antes de tentar delete novamente.
- ⚠️ **Client secrets em App Reg sobrevivem 90 dias após você esquecer da existência** — `app-mcp-helpsphere-client` e `app-n8n-graph` têm secrets válidos. Se vazaram em log/screenshot/`.env` pushado por engano, atacante usa OAuth flow do tenant até expiração. Workaround: deletar App Reg **invalida o secret na hora** (Passo 9.4 obrigatório).
- ⚠️ **PostgreSQL Burstable `Stopped` ainda cobra storage idle E reinicia sozinho em 7d** — Stop temporário no PG Burstable mantém storage provisionado (~R$ 8/mês) e Azure reinicia automaticamente após 7d. Para R$ 0 permanente: delete do RG (este Cap). Sempre crave Cost Anomaly Alert R$ 50 (Passo 9.7).
- ⚠️ **Service Bus Standard cobra baseline R$ 50/mês mesmo sem mensagens** — tier Standard é obrigatório por causa de Topics (Basic só tem Queues). Workaround: delete do RG no Passo 9.2 zera; confira Cost Analysis para namespace órfã em RG diferente (típico de typo na criação manual).
- ⚠️ **Cost Management tem 24-48h de delay — `R$ 0` na hora NÃO significa cleanup completo** — alunos rodam `az group delete` + abrem Cost Analysis 5 min depois, vêem R$ 5/dia lançado e entram em pânico. É telemetria atrasada. Workaround: confirme **48h depois** (Passo 9.7).
- ⚠️ **Key Vault soft-deleted impede recriar com mesmo nome por 90 dias** — se algum cap usou Key Vault que entrou em soft-delete junto com o RG, recriar `kv-helpsphere-<rand>` em fork novo falha com `VaultAlreadyExists` mesmo o vault não aparecendo na listagem. Workaround: `az keyvault purge --name <kv-name> --location eastus2` ou esperar 90d ou usar `<rand>` novo.
- ⚠️ **RG delete é "async billing" — Portal mostra "deleted" mas billing pode continuar 24h** — `az group exists` retorna `false` na hora, mas Cost Analysis ainda lança custos parciais nas próximas 24h até telemetria propagar. Aluno acha que "esqueceu de algo" e tenta deletar de novo (no-op, RG já não existe). Workaround: confie na Validação end-to-end imediata + aguarde 24-48h para Cost Management.
- ⚠️ **Foundry Project tem soft-delete 30d — recurso "deleted" recuperável, mas cobrança zera imediato** — após Delete project, ele some da lista principal mas aparece em **Hub → Settings → Deleted projects** por 30d. Cobrança de compute zera instantaneamente; storage de threads persiste linkado ao Hub. Se você quer purgar definitivo agora (sem esperar 30d): Hub → Deleted projects → ⋮ → **Permanently delete**.
- ⚠️ **Service Bus namespace órfã em RG diferente sobrevive ao cleanup** — se você criou Service Bus por engano em outro RG (typo, ou criou via Portal sem prestar atenção ao "Resource group" dropdown), ele NÃO é deletado pelo `az group delete --name rg-lab-final`. Standard tier cobra R$ 50/mês baseline sem mensagens. Workaround: `az servicebus namespace list --query "[].{name:name, rg:resourceGroup}" -o table` para varrer toda a sub e identificar namespaces órfãs.
- ⚠️ **Container Apps Environment delete NÃO deleta o Log Analytics workspace linkado** — `cae-helpsphere-final` referencia um Log Analytics workspace para logs. Quando o RG é deletado, o ACA Env morre junto, MAS se o Log Analytics estava em outro RG (caso comum: workspace compartilhado em `rg-lab-intermediario`), ele continua acumulando bytes de logs já ingeridos (cobra storage até retenção expirar — default 30d). Workaround: após delete do RG, vá em `rg-lab-intermediario` → Log Analytics → **Settings → Data Retention** → reduzir para 7d para minimizar custo residual.
- ⚠️ **Connection strings órfãs em apps externos** — Service Bus namespace delete leva ~1-2min. Apps consumidores que tinham a connection string hardcoded em `.env` local ou em GitHub Secrets continuam tentando conectar e recebem `MessagingEntityNotFoundException`. Não cobra Azure, mas polui logs e gera ruído de alertas. Limpe os secrets antes do delete: GitHub repo → Settings → Secrets → remover `SB_CONNECTION_STRING`.

---

## Próximo capítulo

[10 — Troubleshooting](./10-troubleshooting.md)
