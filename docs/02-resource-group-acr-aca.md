# Capítulo 02 — Resource Group + ACR

> **Objetivo:** provisionar a fundação de infraestrutura do Lab Final no Portal Azure — Resource Group `rg-lab-final` e Azure Container Registry `acrhelpsphere{rand}` (Basic).
>
> **Tempo:** 15 min
>
> **Status:** `v0.3.0-portal-sync` (Story 06.27) — alinhado com guia consolidado pós Story 06.26 (ACA Environment + AcrPull movidos para Cap 05)
>
> **Mudança Q2-2026:** o **ACA Environment `cae-helpsphere-final`** e o **RBAC AcrPull** da Managed Identity foram movidos para o **início do Capítulo 05** (Passos 5.4 e 5.5), porque o Portal Azure **não permite criar um Container Apps Environment standalone** sem associá-lo a um Container App. Criamos os dois juntos do primeiro Container App de fato (MCP Server).

---

## Pré-requisitos

- ✅ Capítulo 01 concluído — sub Azure logada (`az account show` confirma), VS Code + extensões Bicep/Python instaladas, conta Microsoft 365 (não `live.com`) para Copilot Studio nos próximos capítulos
- ✅ Acesso à sub onde já existem: Foundry Hub `aifhub-apex-prod`, Log Analytics workspace `log-helpsphere-ia`, Managed Identity `mi-helpsphere-ia` — todos no RG `rg-lab-intermediario` (serão usados a partir do Cap 05)
- ✅ `az` CLI ≥ 2.60 instalada (`az --version`) — usaremos como alternativa ao Portal

> **Atenção dependência cruzada:** os capítulos seguintes (MCP Server no Cap 05, Speech no Cap 06, n8n no Cap 07) dependem da Managed Identity `mi-helpsphere-ia` vivendo no RG `rg-lab-intermediario` (já vinculada a Service Bus, AI Search e Speech). Se esse MI não existir, **pare** antes do Cap 05 e provisione-o primeiro — não dá para "improvisar" um MI local. Aqui (Cap 02) só criamos RG + ACR, então a falta do MI não bloqueia.

---

## Resumo dos 2 recursos que vamos cravar

| Recurso | Nome | SKU/Tier | RG | Custo (R$/mês ligado) |
|---|---|---|---|---|
| Resource Group | `rg-lab-final` | — | (novo) | R$ 0 (container lógico) |
| Azure Container Registry | `acrhelpsphere<rand>` | **Basic** | `rg-lab-final` | R$ 35 fixo |

> **Próximos recursos (Cap 05+):** ACA Environment `cae-helpsphere-final` (Passo 5.4) + RBAC AcrPull para `mi-helpsphere-ia` (Passo 5.5) + Container App `ca-mcp-helpsphere` (Passo 5.6). Veja "Mudança Q2-2026" no topo deste capítulo.

> [!IMPORTANT] **Tier / Licenciamento**
> Decisão ACR Basic (R$ 35/mês fixo · 10 GiB storage · 1 webhook) consolidada em [`_disclaimers.md`](./_disclaimers.md). Veja **AMB-1** (motivação Standard/Premium upgrade gates).

### Tabela de referência — custo total estimado do Lab Final (todos os capítulos)

| Recurso | SKU | Cobrança | Custo total lab (8h ligado/dia × 5 dias) |
|---|---|---|---|
| ACR | Basic | Fixo R$ 35/mês | ~R$ 6 prorrated (5 dias) |
| ACA Environment (criado no Cap 05) | Consumption only | Por execução | R$ 0 baseline |
| ACA replicas (MCP + n8n) | 0,5 vCPU + 1 GiB | ~R$ 0,12/h ativo | ~R$ 5 (40h) |
| Foundry Project + agent | — | Por token | ~R$ 5-8 (smoke runs) |
| Service Bus | **Standard** | R$ 50/mês fixo (cobra parado) | ~R$ 8 prorrated |
| Speech Service | Standard S0 | R$ 5/hora STT | ~R$ 5 (1h smoke) |
| **Total estimado** | — | — | **~R$ 30-35 (5 dias)** |

> ⚠️ **Service Bus tier — Standard obrigatório (NÃO Basic):** Basic só permite Queues. Para o pattern pub/sub do capítulo de workflow n8n (1 Topic + 2 Subscriptions: `ticket-escalations` + `ticket-notifications`), Standard é mandatório. Custo: ~R$ 50/mês fixo enquanto ligado — Service Bus **não tem scale-to-zero**, cobra parado. Sempre delete o RG quando terminar a sessão.

> **Atenção custo:** os valores acima assumem **delete do RG após cada sessão de estudo**. Se deixar `rg-lab-final` ligado 30 dias, custo pula para ~R$ 100-150 (ACR + Service Bus baseline + ACA replicas se houver tráfego). O capítulo de cleanup final cobre o procedimento obrigatório — não pule.

---

## Passo 2.1 — Criar Resource Group `rg-lab-final`

**No Portal Azure:**

1. Abra `https://portal.azure.com` → faça login com a conta da sub onde está o Foundry Hub `aifhub-apex-prod`
2. Barra superior → buscar **"Resource groups"** → clicar no resultado
3. Clique **+ Create** (canto superior esquerdo)
4. Preencher tab **Basics:**
   - **Subscription:** sua sub (a mesma do Hub)
   - **Resource group:** `rg-lab-final` (convenção canônica do lab)
   - **Region:** `East US 2` (alinhado com o Foundry Hub — não troque)
5. Tab **Tags** (opcional mas **fortemente recomendado** para cost tracking):
   - `cost-center` = `apex-helpsphere-ia`
   - `environment` = `lab`
   - `application` = `helpsphere-ia`
6. Clique **Review + create** → **Create**
7. Aguarde ~15s até banner verde **"Resource group rg-lab-final has been created"**

<!-- screenshot: cap02-passo2.1-criar-resource-group.png -->

> **Alternativa via Azure CLI (PowerShell 7 — Windows-first):**
>
> ```powershell
> az login
> az account set --subscription "<sua-sub-id>"
>
> az group create `
>   --name rg-lab-final `
>   --location eastus2 `
>   --tags cost-center=apex-helpsphere-ia environment=lab application=helpsphere-ia
> ```
>
> **Linux/Mac/WSL:** troque `` ` `` (backtick) por `\` no fim das linhas.

> **Custo:** RG é gratuito — é apenas um container lógico para agrupar recursos. Cobrança só vem dos recursos dentro dele.

> **Nota pedagógica — por que RG separado do `rg-lab-intermediario`?** O `rg-lab-intermediario` hospeda os recursos **compartilhados** (Foundry Hub, Log Analytics, MI, Key Vault) que vivem além do Lab Final. Este Lab cria recursos **efêmeros** (ACR, ACA env, MCP, n8n). Separando em 2 RGs, no fim do lab você deleta `rg-lab-final` e os recursos compartilhados continuam vivos para reuso. **Anti-pattern:** misturar tudo em 1 RG e ter que escolher recursos individualmente para deletar.

---

## Passo 2.2 — Criar Azure Container Registry (Basic)

**No Portal Azure:**

1. Barra superior → buscar **"Container registries"** → clicar
2. Clique **+ Create**
3. Preencher tab **Basics:**
   - **Subscription:** sua sub
   - **Resource group:** `rg-lab-final`
   - **Registry name:** `acrhelpsphere<rand>` — substitua `<rand>` por 6 chars hex (ex.: `acrhelpsphere8a3f2d`)
     - **Regras:** globalmente único, lowercase, **sem hífen**, 5-50 caracteres, alfanumérico
     - **Sugestão de geração (PowerShell):** `-join ((48..57)+(97..102) | Get-Random -Count 6 | ForEach-Object {[char]$_})` (alternativa Linux/Mac/WSL: `openssl rand -hex 3`)
   - **Location:** `East US 2`
   - **Pricing plan:** `Basic` ⚠️ **(não troque para Standard/Premium — custo do lab pula 3x)**
4. Tab **Networking:**
   - **Connectivity method:** `Public access` (lab simplificado — em prod corporate use Private Link)
5. Tab **Encryption:** deixe defaults (Microsoft-managed keys)
6. Tab **Identity:** deixe defaults (sem System-Assigned MI no ACR — vamos reusar o MI `mi-helpsphere-ia` existente com role `AcrPull`)
7. Tab **Tags:** herde do RG (já preenchidos no Passo 2.1)
8. Clique **Review + create** → **Create**
9. Aguarde provisioning ~1-2min até **Status: Succeeded**. Quando concluir, clique **Go to resource** e anote no overview:
   - **Login server:** `acrhelpsphere<rand>.azurecr.io` (use no `.env` dos próximos caps)
   - **Resource ID:** botão **JSON View** → copie o campo `id` (formato `/subscriptions/.../providers/Microsoft.ContainerRegistry/registries/acrhelpsphere<rand>`)

<!-- screenshot: cap02-passo2.2-criar-acr-basic.png -->

> **Alternativa via Azure CLI (PowerShell 7 — Windows-first):**
>
> ```powershell
> # Gera sufixo aleatório de 6 hex chars (PowerShell-only, sem dependência de openssl)
> $Rand = -join ((48..57) + (97..102) | Get-Random -Count 6 | ForEach-Object { [char]$_ })
> $AcrName = "acrhelpsphere$Rand"
>
> az acr create `
>   --name $AcrName `
>   --resource-group rg-lab-final `
>   --location eastus2 `
>   --sku Basic `
>   --admin-enabled false
>
> Write-Host "ACR criado: $AcrName.azurecr.io"
> Write-Host "Anote este valor — vai entrar nos .env dos próximos capítulos"
> ```
>
> **Linux/Mac/WSL:** gere o sufixo com `RAND=$(openssl rand -hex 3) && ACR_NAME="acrhelpsphere$RAND"`, troque `` ` `` (backtick) por `\` no `az acr create`, e use `echo` no lugar de `Write-Host`.

> **Custo:** ACR Basic = R$ 35/mês fixo (cobra parado, não tem scale-to-zero). No lab, fique no Basic — delete o RG no capítulo de cleanup final para não acumular cobrança. Detalhes do trade-off Standard/Premium em [`_disclaimers.md`](./_disclaimers.md) **AMB-1**.

> **Nota pedagógica — `Admin user: disabled` é proposital:** no Portal default vem `disabled` (e estamos mantendo). Se você habilitar, o ACR cria 2 senhas master que vivem para sempre — vetor de credenciais long-lived é anti-pattern. Em vez disso, vamos usar a Managed Identity `mi-helpsphere-ia` com role `AcrPull` no Cap 05 Passo 5.5. Isso elimina 100% de senhas no fluxo de pull → ACA. **Em produção: SEMPRE admin disabled + RBAC + MI.**

---

## Passo 2.3 — Validar fundação no Portal

**No Portal Azure:**

1. Vá ao RG `rg-lab-final` → **Overview**
2. Confirme visualmente que existe **1 recurso:**
   - `acrhelpsphere<rand>` (Container registry)
3. Em `acrhelpsphere<rand>` → **Overview** → confirme:
   - **Provisioning state:** `Succeeded`
   - **Login server:** formato `acrhelpsphere<rand>.azurecr.io`
   - **SKU:** `Basic`
   - **Admin user:** `Disabled`

<!-- screenshot: cap02-passo2.3-rg-overview-validacao.png -->

> **Próximo passo (Cap 05):** o ACA Environment `cae-helpsphere-final` e o RBAC AcrPull para `mi-helpsphere-ia` serão criados no início do Capítulo 05 (Passos 5.4 e 5.5), juntos do primeiro Container App (MCP Server). Motivo Q2-2026: o Portal Azure não permite criar Container Apps Environment standalone — é mais limpo provisionar tudo no momento em que de fato precisamos do Container App.

---

## Validação end-to-end

```powershell
# 1. RG existe
az group show --name rg-lab-final `
  --query "{name:name, location:location, state:properties.provisioningState}" -o table
# Esperado: rg-lab-final, eastus2, Succeeded

# 2. ACR existe e SKU correto
az acr show --name $AcrName --resource-group rg-lab-final `
  --query "{name:name, sku:sku.name, loginServer:loginServer, adminEnabled:adminUserEnabled}" -o table
# Esperado: name=acrhelpsphere<rand>, sku=Basic, adminEnabled=false

# 3. Smoke pull anônimo (deve falhar — confirma que admin disabled está respeitado)
az acr login --name $AcrName 2>&1 | Select-Object -First 5
# Esperado: erro "admin user is disabled" OU sucesso via az credential (ambos OK — confirma que não há fallback público)
```

---

## Checklist final

```text
[ ] Resource Group rg-lab-final criado em East US 2
[ ] Tags cost-center, environment, application, course aplicadas no RG
[ ] ACR acrhelpsphere<rand> criado com SKU Basic + adminUserEnabled=false
[ ] ACR loginServer anotado para uso nos .env (formato acrhelpsphere<rand>.azurecr.io)
[ ] RG rg-lab-final aparece com 1 recurso no Portal (ACR)
[ ] Confirmado: ACA Environment + RBAC AcrPull serão criados no Cap 05 (Passos 5.4 e 5.5)
```

---

## Surpresas pedagógicas (capturadas em smoke runs)

- ⚠️ **ACR name globalmente único + sem hífen + lowercase** — Azure rejeita `acr-helpsphere` (hífen), `ACRhelpsphere` (uppercase) e qualquer nome já usado no mundo (formato DNS). Workaround: sempre concatenar 6 hex chars aleatórios (`acrhelpsphere8a3f2d`). **Anti-pattern comum:** copy-paste do nome de outro aluno → falha "Registry name not available".
- ⚠️ **ACR Basic tem limit de 10 GiB de storage** — ver [`_disclaimers.md`](./_disclaimers.md) **AMB-1** para o cap absoluto. Sintoma: `denied: requested access to the resource is denied` no `docker push`. Workaround: `az acr repository delete --name <acr> --image <repo>:<tag>` para liberar espaço, ou subir para Standard. **Em produção, sempre cravar política de retention de tags (`az acr config retention`).**
- ⚠️ **`--admin-enabled true` no ACR vira credencial órfã** — se em algum debug você habilitou admin user (ex.: para um `docker login` rápido), as 2 senhas master nunca expiram automaticamente. Vetor de comprometimento de longo prazo. Workaround: depois de debugar, `az acr update --name <acr> --admin-enabled false` + rotacionar passwords (`az acr credential renew`). **Em produção: nunca habilite — Bicep policy `Microsoft.Authorization/policyDefinitions` deve denyar.**

> **Surpresas relacionadas a ACA Environment + RBAC AcrPull** foram **movidas para o Cap 05** junto com os Passos 5.4 e 5.5 (criação real desses recursos). Veja `docs/05-mcp-server-deploy.md` Surpresas pedagógicas.

---

## Troubleshooting rápido

| Sintoma | Causa provável | Fix |
|---|---|---|
| `Registry name 'acrhelpsphere' is not available` | Nome já registrado globalmente | Adicione 6 hex chars aleatórios ao final |
| `The subscription is not registered to use namespace 'Microsoft.App'` | Resource Provider não habilitado | `az provider register --namespace Microsoft.App && az provider register --namespace Microsoft.OperationalInsights` |

---

## Próximo capítulo

[03 — Copilot Studio Setup](./03-copilot-studio-setup.md)
