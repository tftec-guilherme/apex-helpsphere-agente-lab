# Capítulo 09 — Cleanup Obrigatório

> **Objetivo:** zerar o **custo recorrente** do Lab Final em < 15 min: deletar o RG `rg-lab-final` (apaga ACR, ACA Env, MCP Server, n8n, **PostgreSQL Burstable B1ms — maior dreno**, Speech, Service Bus Standard), deletar o **Foundry Project `aifproj-helpsphere-agente`** (separado do Hub `aifhub-apex-prod` que continua vivo para outros labs), desativar/deletar o agent Copilot Studio `HelpSphere Tier 1 Agent` (trial 30d expira sozinho, mas consome licença até lá), remover as **3 App Registrations** do Cap 05/08 (`app-mcp-helpsphere-server` + `app-mcp-helpsphere-client` + `app-n8n-graph` se Cap 08 Passo 8.4 executado) que ficam órfãs no tenant Entra, e validar zero billing residual no **Cost Management** após 24-48h de delay de telemetria.
>
> **Tempo:** 10-15 min execução + 24-48h espera para Cost Management refletir
>
> **Status:** `v0.2.0-portal` ⚠️ EXPANDIDO (era `v0.1.0-init` outline) — derivado de `Lab_Final_Agente_Workflow_Guia_Portal.md` Parte 8 + Passo 8.3 (linhas 1845-1940)

---

## Pré-requisitos

- ✅ Capítulos 02-08 executados — todo o estado provisionado existe
- ✅ Demo dos 5 tickets (Passo 8.2 do guia) **gravada/screenshot** + logs/threads/dead-letter relevantes exportados — depois deste cap, **nada volta**
- ✅ `az` CLI logado na sub correta (`az account show -o table` confirma)
- ✅ Permissão `Owner`/`Contributor` no `rg-lab-final` + `Application Developer`/`Cloud Application Administrator` no tenant Entra (Passo 9.4)

> [!IMPORTANT] **Tier / Licenciamento — custo recorrente**
> Lab Final introduz 3 recursos que cobram parados em `rg-lab-final`: PostgreSQL Burstable B1ms (~R$ 60/mês — ver **AMB-3**), ACR Basic (~R$ 35/mês — ver **AMB-1**), Service Bus Standard (~R$ 50/mês — ver **AMB-4**). Soma: ~R$ 145/mês esquecidos. Decisões consolidadas em [`_disclaimers.md`](./_disclaimers.md). Sem cleanup: 30 dias = R$ 145 debitados sem tráfego; em Free Trial USD 200, queima crédito sem o aluno entender por quê.

> **Atenção breaking — Cap 07 pause/resume vs Cap 09 delete:** Cap 07 Passo 7.7 oferece **Stop temporário** (PG + ACA n8n) para sessões recorrentes. Este Cap 09 é **delete definitivo** — caminho oposto. Não misture: Stop do PG + delete do RG falha porque o RG só deleta com PG em estado `Ready` (não `Stopped`).

---

## Resumo dos 5 alvos de cleanup

| Alvo | Onde vive | Custo se esquecer (R$/mês) |
|---|---|---|
| **RG `rg-lab-final`** (ACR + ACA Env + MCP + n8n + PG + Speech + Service Bus) — **crítico** | Sub Azure → `rg-lab-final` | ~R$ 145 fixo + variável |
| **Foundry Project `aifproj-helpsphere-agente`** — não está no `rg-lab-final` | Hub `aifhub-apex-prod` em `rg-helpsphere-ia` | R$ 1-2/mês storage idle de threads |
| **Copilot Studio agent `HelpSphere Tier 1 Agent`** — trial expira 30d sozinho | Power Platform tenant | R$ 0 trial · R$ 1.000+/mês Per-User Premium |
| **3 App Registrations Entra** (`app-mcp-helpsphere-server`/`-client` + `app-n8n-graph` se Cap 08) | Tenant Entra | R$ 0 mas client secret 90d = vetor de ataque |
| **`rg-helpsphere-ia`** (Hub + MI + LA do Bloco 2) — **NÃO delete se vai fazer Lab Avançado** | RG `rg-helpsphere-ia` | ~R$ 30/mês (Passo 9.6) |

> **Nota pedagógica — por que `az group delete` resolve 80% mas não 100% + matriz de soft-delete:** delete do RG é cascade local mas o Lab Final tem 3 dependências **cross-RG/cross-tenant** órfãs: (1) Foundry **Project** vive sob o Hub em `rg-helpsphere-ia`, (2) **App Registrations** vivem em tenant Entra, (3) **Copilot Studio agent** vive em Power Platform. Por isso o cleanup é em **5 passos separados**, não 1. Soft-delete varia por recurso: RG não tem (delete = definitivo), Key Vault tem 90d default, App Reg 30d, Foundry workspace 14d. Key Vault em soft-delete impede recriar com mesmo nome — `az keyvault purge` ou esperar 90d.

---

## Passo 9.1 — Confirmar que terminou (gate de segurança)

Antes de qualquer comando destrutivo, confirme o checklist:

```text
[ ] Demo dos 5 tickets (Passo 8.2 do guia) executada e validada
[ ] Screenshots / vídeo de evidência salvos fora do Azure (laptop local, OneDrive pessoal)
[ ] Threads do agent Foundry exportadas via SDK (`client.agents.list_threads()` → JSON local) se você quer analisar offline
[ ] Logs do App Insights exportados via Kusto (export to CSV) se relevantes
[ ] Confirmou que NÃO vai fazer Lab Avançado em sequência amanhã (se vai, NÃO delete `rg-helpsphere-ia` — ver Passo 9.6)
```

> **Nota pedagógica — gate de confirmação humana é Defense in Depth:** todo comando destrutivo do Azure CLI exige `--yes` explícito proposital. Não automatize este capítulo em CI — é manual obrigatório. Casos clássicos de cleanup automatizado destrutivo (GitLab 2017, AWS S3 órfãos) reforçam: 5 segundos extras digitando `rg-lab-final` no Portal vale a pausa.

---

## Passo 9.2 — Deletar RG `rg-lab-final` (cleanup principal)

**No Portal Azure:**

1. Abra `https://portal.azure.com` → barra superior → buscar **"Resource groups"** → clicar
2. Clique no RG `rg-lab-final`
3. Tab **Overview** → botão **Delete resource group** (topo)
4. Painel direito: digite o nome `rg-lab-final` no campo de confirmação (case-sensitive)
5. ⚠️ **Pause antes de clicar Delete:** o Portal lista **todos os recursos** que serão deletados — confira que aparece **PostgreSQL `pg-n8n-<rand>`** (PG Burstable Cap 07), **Container Apps `ca-mcp-helpsphere`+`ca-n8n-helpsphere`**, **ACR `acrhelpsphere<rand>`**, **ACA Env `cae-helpsphere-final`**, **Speech `spch-helpsphere`** (Cap 06), **Service Bus `sb-helpsphere-final`** (Cap 08). Se faltar algum desses, **pare** — pode ter ido para outro RG por engano.
6. Clique **Delete**
7. Notificação no sino superior: "Deleting resource group rg-lab-final" → aguarde **3-5 min** (PG Flexible Server demora mais que ACA Consumption)
8. Sucesso: notificação "Resource group rg-lab-final has been deleted"

<!-- screenshot: cap09-passo9.2-delete-rg-portal.png -->

> **Alternativa via Azure CLI (recomendada — mais rápida e síncrona):**
>
> ```bash
> # Pré-flight: listar o que vai morrer (NÃO destrutivo)
> az resource list --resource-group rg-lab-final \
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
> az group show --name rg-lab-final 2>&1 | grep -E "(could not be found|ResourceGroupNotFound)"
> # Esperado: "Resource group 'rg-lab-final' could not be found."
> ```

> **Custo:** R$ 0 — operação delete em si é gratuita. **Economia:** ~R$ 145/mês recorrente que para imediatamente (compute) e em ~24h no billing report.

> **Nota pedagógica — síncrono vs `--no-wait` + Resource Locks:** delete síncrono (`az group delete --yes`) bloqueia até concluir e mostra erro na hora se algum recurso falhar (lock, policy, dependência cross-RG); `--no-wait` retorna em 2s mas **mascara erros silenciosos**. Para lab manual: síncrono. **Resource Locks** tipo `CanNotDelete` cravados em recursos críticos pelo admin do tenant fazem delete falhar sem mensagem clara ("Operation completed with errors") — antes de tentar de novo: Portal → RG → **Settings → Locks** → remover.

---

## Passo 9.3 — Deletar Foundry Project `aifproj-helpsphere-agente`

⚠️ **Importante:** o Foundry Project NÃO está no `rg-lab-final`. Ele vive no `rg-helpsphere-ia` (Bloco 2) sob o Hub `aifhub-apex-prod`. O delete do `rg-lab-final` no Passo 9.2 **NÃO removeu o Project**.

**No Azure AI Foundry portal:**

1. Abra `https://ai.azure.com` → faça login com a mesma conta Azure
2. Tela inicial → seção **Projects** (não Hubs) → localize `aifproj-helpsphere-agente`
3. Clique nos três pontos `⋮` ao lado do nome → **Delete project**
4. Confirme digitando o nome → **Delete**
5. Aguarde ~30s-1min até sumir da lista
6. Confirme que o **Hub `aifhub-apex-prod` continua existindo** (ele é compartilhado para outros labs/turmas — NUNCA delete)

<!-- screenshot: cap09-passo9.3-delete-foundry-project.png -->

> **Alternativa via Azure CLI:**
>
> ```bash
> az ml workspace delete \
>   --name aifproj-helpsphere-agente \
>   --resource-group rg-helpsphere-ia \
>   --yes \
>   --no-wait
>
> # Validar que sumiu
> az ml workspace list \
>   --resource-group rg-helpsphere-ia \
>   --query "[?kind=='Project'].{name:name, kind:kind}" -o table
> # Esperado: linha aifproj-helpsphere-agente NÃO aparece
> ```

> **Custo:** R$ 0 — Project é metadata gratuita. Se o Project tinha **threads ativas** (conversas), elas usam storage do Hub (~R$ 1-2/mês até delete). Após Project delete, threads são purgadas em ~24h.

> **Nota pedagógica — Project vs Hub + soft-delete 14d:** o **Project** carrega agent + threads + conexões; o **Hub** carrega storage + App Insights + Key Vault + **deployment do `gpt-4.1-mini` compartilhado**. Deletar Project NÃO deleta o deployment do modelo (continua no Hub cobrando por token). Para zerar 100% o billing do modelo: **AI Foundry → Hub → Models + endpoints → `gpt-4.1-mini` → Delete deployment** — mas **só se ninguém mais usa o Hub**. Foundry workspaces têm **soft-delete 14d** (Hub → **Settings → Deleted projects → Restore** se deletou por engano).

---

## Passo 9.4 — Deletar App Registrations órfãs do tenant Entra

O Passo 9.2 deletou recursos Azure RM mas **App Registrations vivem no tenant Entra**, fora do escopo do RG. Sobram 2-3 App Registrations órfãs com **client secrets válidos por 90 dias** — vetor de ataque até expirarem.

**Lista de App Regs criadas durante o Lab Final (verifique cada uma):**

| App Reg | Criado em | Client Secret? |
|---|---|---|
| `app-mcp-helpsphere-server` | Cap 05 Passo 5.2 | Não (só Application ID URI + scopes) |
| `app-mcp-helpsphere-client` | Cap 05 Passo 5.3 | **Sim — 90 dias** ⚠️ |
| `app-n8n-graph` (se Cap 08 Passo 8.4 executado) | Cap 08 | **Sim — 90 dias** ⚠️ |

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

> **Alternativa via Azure CLI:**
>
> ```bash
> # Listar candidatas órfãs (nomes contendo "helpsphere" ou "n8n-graph")
> az ad app list \
>   --filter "startswith(displayName, 'app-mcp-helpsphere') or startswith(displayName, 'app-n8n')" \
>   --query "[].{name:displayName, appId:appId}" -o table
>
> # Delete por appId (repita para cada uma)
> az ad app delete --id <appId-de-app-mcp-helpsphere-server>
> az ad app delete --id <appId-de-app-mcp-helpsphere-client>
> az ad app delete --id <appId-de-app-n8n-graph>  # se Cap 08 executado
>
> # Validar que sumiram
> az ad app list \
>   --filter "startswith(displayName, 'app-mcp-helpsphere')" \
>   --query "length(@)"
> # Esperado: 0
> ```

> **Custo:** R$ 0 — App Registrations são gratuitas (sem cobrança independente do número).

> **Nota pedagógica — soft-delete 30d + por que secret órfão é vetor de ataque:** App Regs ficam em **soft-deleted 30d** (Portal Entra → **App registrations** → tab **Deleted applications** → Restore ou Permanently delete). O `app-mcp-helpsphere-client` tem **client secret válido por 90d** — se vazou em log/screenshot/`.env` pushado por engano em repo público, atacante usa o OAuth flow do tenant até expiração mesmo com o app vivo. Deletar App Reg **invalida o secret na hora** — proteção #1 pós-lab.

---

## Passo 9.5 — Desativar/deletar Copilot Studio agent `HelpSphere Tier 1 Agent`

Power Platform vive em tenant separado, fora do Azure RM — único caminho é manual via portal Copilot Studio. Trial 30d expira sozinho, mas até lá ocupa licença e suja auditoria.

**No Power Platform / Copilot Studio:**

1. `https://copilotstudio.microsoft.com/` → login com a conta M365 do Cap 03 → confirme **environment Development** no header (não `Default`)
2. Sidebar esquerdo → **Agents** → localize `HelpSphere Tier 1 Agent`
3. Três pontos `⋮` → **Delete copilot** (recomendado se terminou) **OU** **Disable** (se vai refazer demo depois) → confirme

<!-- screenshot: cap09-passo9.5-delete-copilot-studio-agent.png -->

> **Custo:** R$ 0 em trial. **Per-User Premium**: delete libera R$ 1.000+/mês imediato. **Pay-As-You-Go**: para contagem de mensagens (R$ 0,07/msg).

> **Nota pedagógica — agent vs environment Development:** deletar o agent não deleta o environment Power Platform Development (continua vazio e listado em **Power Platform Admin Center → Environments**). Em tenant dev grátis não cobra parado — pode ficar; em corporate, delete via role `Power Platform Administrator`.

---

## Passo 9.6 — Decidir destino de `rg-helpsphere-ia` (Bloco 2)

⚠️ **Decisão crítica — não automatize.** O `rg-helpsphere-ia` (Bloco 2) carrega **Foundry Hub `aifhub-apex-prod`** + **MI `mi-helpsphere-ia`** + **Log Analytics `log-helpsphere-ia`** + Key Vault + AI Search + **apex-helpsphere SaaS** (pivot 2026-05-06).

| Cenário | Ação | Custo recorrente |
|---|---|---|
| Vou fazer Lab Avançado D06 amanhã/semana | **NÃO delete** | ~R$ 30-40/mês (Hub idle + LA 5 GiB free) |
| Terminei a disciplina | `az group delete --name rg-helpsphere-ia --yes` | R$ 0 |
| Vou repetir o Lab Final | Preserve (Hub + MI custosos de recriar) | ~R$ 30-40/mês |

> **Custo:** delete zera compute. Storage idle do Log Analytics (R$ 12/GiB/mês além dos 5 GiB free) e Key Vault em soft-delete 90d (R$ 0 mas ocupa nome) persistem até purga. Deletar o RG também **derruba o apex-helpsphere SaaS** — exporte dados antes se quer continuar testando a aplicação fora do Lab Final.

---

## Passo 9.7 — Verificar billing pós-cleanup (24-48h delay obrigatório)

Cost Management tem **delay de 24-48h** entre delete e dado refletido. Validações imediatas (RG/Project/AppReg sumiram) já estão na **Validação end-to-end** abaixo. **24-48h depois — No Portal Azure:**

1. Barra superior → **"Cost Management + Billing"** → **Cost analysis**
2. Filter: **Resource group name = `rg-lab-final`** · Date range: **Last 7 days**
3. Esperado: gráfico decresce dia após delete e mostra **R$ 0** nos últimos 1-2 dias
4. Se custo > R$ 0 após 48h: recurso órfão (raro — Cosmos DB free tier residual, Public IP standalone). Investigue **Group by: Service name**

<!-- screenshot: cap09-passo9.7-cost-analysis-pos-cleanup.png -->

> **Custo:** R$ 0 (Cost Management é gratuito — nem entra no quota de telemetria).

> **Nota pedagógica — 3 fontes de billing "fantasma" + Cost Anomaly Alert grátis:** (1) **Storage idle** de Key Vault soft-deleted ou Log Analytics retido (R$ 1-5/mês até purga), (2) **Reserved capacity** comprada antes (cobra mesmo sem uso — só cancela contrato), (3) **Marketplace items** (Apify/SendGrid cobram independente do RG). Mitigação universal: **Cost Management → Cost alerts → + Add → Anomaly alert → threshold R$ 50 + scope sub → email**. R$ 0 fixo, permanente. Crave antes do próximo lab.

---

## Validação end-to-end

```bash
# 1. RG rg-lab-final sumiu
az group exists --name rg-lab-final                                          # false
# 2. Foundry Project sumiu (mas Hub continua)
az ml workspace list -g rg-helpsphere-ia --query "[?name=='aifproj-helpsphere-agente']" -o tsv  # vazio
az ml workspace show --name aifhub-apex-prod -g rg-helpsphere-ia --query "kind" -o tsv          # Hub
# 3. App Regs sumiram
az ad app list --filter "startswith(displayName, 'app-mcp-helpsphere')" --query "length(@)"     # 0
# 4. Cost Management 24-48h depois (telemetria atrasa) — Portal → Cost analysis → filter rg-lab-final → últimos 2 dias = R$ 0
```

---

## Checklist final

```text
[ ] Demo dos 5 tickets executada e evidência salva fora do Azure
[ ] Threads do agent Foundry exportadas se necessário (snippet Passo 9.1)
[ ] RG rg-lab-final deletado (cascade: ACR + ACA Env + MCP + n8n + PG + Speech + Service Bus)
[ ] Foundry Project aifproj-helpsphere-agente deletado (separado do Hub)
[ ] Hub aifhub-apex-prod PRESERVADO (compartilhado para outros labs)
[ ] App Registrations órfãs deletadas (app-mcp-helpsphere-server + app-mcp-helpsphere-client + app-n8n-graph se Cap 08)
[ ] Copilot Studio agent HelpSphere Tier 1 Agent deletado ou desabilitado
[ ] Decisão tomada sobre rg-helpsphere-ia (Bloco 2): preservar para Lab Avançado OU deletar
[ ] (24-48h depois) Cost Management confirma R$ 0 no escopo rg-lab-final
[ ] Azure Cost Anomaly Alert R$ 50 cravado na sub (proteção permanente)
[ ] Custo total do lab realizado: ≤ R$ 30 (alvo Apex)
```

---

## Surpresas pedagógicas (capturadas em smoke runs)

- ⚠️ **Delete do `rg-lab-final` NÃO deleta o Foundry Project** — Project vive no `rg-helpsphere-ia` (Bloco 2) sob o Hub. O aluno pensa "deletei o RG, acabou", mas o Project fica órfão consumindo storage idle (~R$ 1-2/mês) + threads cifradas. Workaround: cleanup em **5 passos separados** (este capítulo) — não confie em delete cascade do RG sozinho.
- ⚠️ **`az group delete` falha silently se houver Resource Lock** — admin do tenant pode ter cravado lock `CanNotDelete` em recursos críticos (ACR Premium, Log Analytics em compliance). Comando termina com "Operation completed with errors" sem detalhar qual recurso. Workaround: Portal → RG → **Settings → Locks** → remover antes de tentar delete novamente.
- ⚠️ **Client secrets em App Reg sobrevivem 90 dias após você esquecer da existência** — `app-mcp-helpsphere-client` (Cap 05) e `app-n8n-graph` (Cap 08) têm secrets válidos. Se vazaram em log/screenshot/`.env` pushado por engano, atacante usa OAuth flow do tenant até expiração. Workaround: deletar App Reg **invalida o secret na hora** (Passo 9.4 obrigatório).
- ⚠️ **PostgreSQL Burstable `Stopped` ainda cobra storage idle E reinicia sozinho em 7d** — ver [`_disclaimers.md`](./_disclaimers.md) **AMB-3** para causa-raiz e estratégia. Para R$ 0 permanente, delete do RG (este Cap) — Cap 07 Passo 7.7 Stop é só para sessão recorrente curta. Sempre crave Cost Anomaly Alert R$ 50 (Passo 9.7).
- ⚠️ **Service Bus Standard cobra baseline R$ 50/mês mesmo sem mensagens** — ver [`_disclaimers.md`](./_disclaimers.md) **AMB-4** para a decisão tier (Standard obrigatório por causa de Topics). Workaround: delete do RG no Passo 9.2 zera; confira Cost Analysis para namespace órfã em RG diferente (typo no Cap 08).
- ⚠️ **Cost Management tem 24-48h de delay — `R$ 0` na hora NÃO significa cleanup completo** — alunos rodam `az group delete` + abrem Cost Analysis 5 min depois, vêem R$ 5/dia lançado e entram em pânico. É telemetria atrasada. Workaround: confirme **48h depois** (Passo 9.7).
- ⚠️ **Key Vault soft-deleted impede recriar com mesmo nome por 90 dias** — se algum cap usou Key Vault que entrou em soft-delete junto com o RG, recriar `kv-helpsphere-<rand>` em fork novo falha com `VaultAlreadyExists` mesmo o vault não aparecendo na listagem. Workaround: `az keyvault purge --name <kv-name> --location eastus2` ou esperar 90d ou usar `<rand>` novo.

---

## Próximo capítulo

[10 — Troubleshooting](./10-troubleshooting.md)
