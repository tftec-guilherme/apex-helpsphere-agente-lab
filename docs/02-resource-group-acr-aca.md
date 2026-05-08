# Capítulo 02 — Resource Group + ACR + ACA Environment

> **Objetivo:** provisionar a fundação de infraestrutura do Lab Final no Portal Azure — Resource Group `rg-lab-final`, Azure Container Registry `acrhelpsphere{rand}` (Basic), Azure Container Apps Environment `cae-helpsphere-final` com Log Analytics compartilhado, e atribuir role `AcrPull` à Managed Identity já criada no Bloco 2.
>
> **Tempo:** 30-40 min (10-15 min se você já fez Bloco 2 e tem o MI `mi-helpsphere-ia` + Log Analytics `log-helpsphere-ia` prontos)
>
> **Status:** `v0.2.0-portal` ⚠️ EXPANDIDO (era `v0.1.0-init` outline) — derivado de `Lab_Final_Agente_Workflow_Guia_Portal.md` Parte 1 (Passos 1.1-1.4)

---

## Pré-requisitos

- ✅ Capítulo 01 concluído — sub Azure logada (`az account show` confirma), VS Code + extensões Bicep/Python instaladas, conta Microsoft 365 (não `live.com`) para Copilot Studio nos próximos caps
- ✅ Bloco 2 da disciplina concluído OU acesso à sub onde já existem: Foundry Hub `aifhub-apex-prod`, Log Analytics workspace `log-helpsphere-ia`, Managed Identity `mi-helpsphere-ia` — todos no RG `rg-helpsphere-ia`
- ✅ Permissão `Contributor` + `User Access Administrator` (ou `Owner`) na sub — necessárias para criar role assignments no Passo 2.4
- ✅ `az` CLI ≥ 2.60 instalada (`az --version`) — usaremos como alternativa ao Portal e obrigatoriamente no Passo 2.4

> **Atenção dependência cruzada:** este capítulo cria recursos no RG **novo** `rg-lab-final` mas **lê e atribui role** sobre a Managed Identity `mi-helpsphere-ia` que vive no RG **`rg-helpsphere-ia`** (criado no Bloco 2). Se o Bloco 2 não foi feito, **pare aqui** e volte — não dá para "improvisar" um MI local; vários capítulos seguintes (05 MCP Server, 06 Speech, 07 n8n) dependem desse mesmo MI já vinculado a Service Bus, AI Search e Speech.

---

## Resumo dos 4 recursos que vamos cravar

| Recurso | Nome | SKU/Tier | RG | Custo (R$/mês ligado) |
|---|---|---|---|---|
| Resource Group | `rg-lab-final` | — | (novo) | R$ 0 (container lógico) |
| Azure Container Registry | `acrhelpsphere<rand>` | **Basic** | `rg-lab-final` | R$ 35 fixo |
| ACA Environment | `cae-helpsphere-final` | Consumption (workload profile) | `rg-lab-final` | R$ 0 parado · ~R$ 0,000024/vCPU-s + R$ 0,0000028/GiB-s ativo |
| Role Assignment | `AcrPull` | — | escopo: ACR | R$ 0 (RBAC é gratuito) |

> [!IMPORTANT] **Tier / Licenciamento**
> Decisão ACR Basic (R$ 35/mês fixo · 10 GiB storage · 1 webhook) consolidada em [`_disclaimers.md`](./_disclaimers.md). Veja **AMB-1** (motivação Standard/Premium upgrade gates).

> **Nota pedagógica — por que workload profile Consumption e não Dedicated?** Consumption cobra por execução (scale-to-zero possível). Dedicated reserva vCPU/RAM 24×7 (R$ 250+/mês baseline). No lab, MCP Server e n8n ficam parados >90% do tempo → Consumption economiza ~80%. Em produção com SLA <100ms cold-start ou GPU/large-RAM, Dedicated faz sentido.

### Tabela de referência — custo total estimado do Lab Final (Caps 02-09)

| Recurso | SKU | Cobrança | Custo total lab (8h ligado/dia × 5 dias) |
|---|---|---|---|
| ACR | Basic | Fixo R$ 35/mês | ~R$ 6 prorrated (5 dias) |
| ACA Environment | Consumption only | Por execução | R$ 0 baseline |
| ACA replicas (MCP + n8n) | 0,5 vCPU + 1 GiB | ~R$ 0,12/h ativo | ~R$ 5 (40h) |
| Foundry Project + agent | — | Por token | ~R$ 5-8 (smoke runs) |
| Service Bus Standard (Cap 08) | Standard | R$ 50/mês | ~R$ 8 prorrated |
| Speech Service (Cap 06) | Standard S0 | R$ 5/hora STT | ~R$ 5 (1h smoke) |
| **Total estimado** | — | — | **~R$ 30-35 (5 dias)** |

> **Atenção custo:** os valores acima assumem **delete do RG após cada sessão de estudo**. Se deixar `rg-lab-final` ligado 30 dias, custo pula para ~R$ 100-150 (ACR + Service Bus baseline + ACA replicas se houver tráfego). **Cap 09 cobre cleanup obrigatório** — não pule.

---

## Passo 2.1 — Criar Resource Group `rg-lab-final`

**No Portal Azure:**

1. Abra `https://portal.azure.com` → faça login com a conta da sub onde você criou o Foundry Hub (Bloco 2)
2. Barra superior → buscar **"Resource groups"** → clicar no resultado
3. Clique **+ Create** (canto superior esquerdo)
4. Preencher tab **Basics:**
   - **Subscription:** sua sub (a mesma do Bloco 2)
   - **Resource group:** `rg-lab-final` (sem sufixo de aluno — convenção da disciplina)
   - **Region:** `East US 2` (alinhado com o Foundry Hub do Bloco 2 — não troque)
5. Tab **Tags** (opcional mas **fortemente recomendado** para cost tracking):
   - `cost-center` = `apex-helpsphere-ia`
   - `environment` = `lab`
   - `application` = `helpsphere-ia`
   - `course` = `D06`
6. Clique **Review + create** → **Create**
7. Aguarde ~15s até banner verde **"Resource group rg-lab-final has been created"**

<!-- screenshot: cap02-passo2.1-criar-resource-group.png -->

> **Alternativa via Azure CLI:**
>
> ```bash
> az login
> az account set --subscription "<sua-sub-id>"
>
> az group create \
>   --name rg-lab-final \
>   --location eastus2 \
>   --tags cost-center=apex-helpsphere-ia environment=lab application=helpsphere-ia course=D06
> ```

> **Custo:** RG é gratuito — é apenas um container lógico para agrupar recursos. Cobrança só vem dos recursos dentro dele.

> **Nota pedagógica — por que RG separado do `rg-helpsphere-ia` (Bloco 2)?** O Bloco 2 cria os recursos **compartilhados** (Foundry Hub, Log Analytics, MI, Key Vault). Este Lab Final cria os recursos **efêmeros** (ACR, ACA env, MCP, n8n). Separando em 2 RGs, no fim do lab você deleta `rg-lab-final` e os recursos compartilhados continuam vivos para o próximo lab/turma. **Anti-pattern:** misturar tudo em 1 RG e ter que escolher recursos individualmente para deletar.

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
     - **Sugestão de geração:** abra um terminal e rode `openssl rand -hex 3` (ou no PowerShell: `-join ((48..57)+(97..102) | Get-Random -Count 6 | ForEach-Object {[char]$_})`)
   - **Location:** `East US 2`
   - **Pricing plan:** `Basic` ⚠️ **(não troque para Standard/Premium — custo do lab pula 3x)**
4. Tab **Networking:**
   - **Connectivity method:** `Public access` (lab simplificado — em prod corporate use Private Link)
5. Tab **Encryption:** deixe defaults (Microsoft-managed keys)
6. Tab **Identity:** deixe defaults (sem System-Assigned MI no ACR — vamos usar o MI do Bloco 2 com role `AcrPull`)
7. Tab **Tags:** herde do RG (já preenchidos no Passo 2.1)
8. Clique **Review + create** → **Create**
9. Aguarde provisioning ~1-2min até **Status: Succeeded**. Quando concluir, clique **Go to resource** e anote no overview:
   - **Login server:** `acrhelpsphere<rand>.azurecr.io` (use no `.env` dos próximos caps)
   - **Resource ID:** botão **JSON View** → copie o campo `id` (formato `/subscriptions/.../providers/Microsoft.ContainerRegistry/registries/acrhelpsphere<rand>`)

<!-- screenshot: cap02-passo2.2-criar-acr-basic.png -->

> **Alternativa via Azure CLI:**
>
> ```bash
> # Gera sufixo aleatório de 6 hex chars
> RAND=$(openssl rand -hex 3)
> ACR_NAME="acrhelpsphere${RAND}"
>
> az acr create \
>   --name "$ACR_NAME" \
>   --resource-group rg-lab-final \
>   --location eastus2 \
>   --sku Basic \
>   --admin-enabled false
>
> echo "ACR criado: $ACR_NAME.azurecr.io"
> echo "Anote este valor — vai entrar nos .env dos próximos capítulos"
> ```

> **Custo:** ACR Basic = R$ 35/mês fixo (cobra parado, não tem scale-to-zero). No lab, fique no Basic — delete o RG no Cap 09 para não acumular cobrança. Detalhes do trade-off Standard/Premium em [`_disclaimers.md`](./_disclaimers.md) **AMB-1**.

> **Nota pedagógica — `Admin user: disabled` é proposital:** no Portal default vem `disabled` (e estamos mantendo). Se você habilitar, o ACR cria 2 senhas master que vivem para sempre — vetor de credenciais long-lived é anti-pattern. Em vez disso, vamos usar a Managed Identity `mi-helpsphere-ia` (Bloco 2) com role `AcrPull` no Passo 2.4. Isso elimina 100% de senhas no fluxo de pull → ACA. **Em produção: SEMPRE admin disabled + RBAC + MI.**

---

## Passo 2.3 — Criar ACA Environment com Log Analytics compartilhado

**No Portal Azure:**

1. Barra superior → buscar **"Container Apps Environments"** → clicar
2. Clique **+ Create**
3. Preencher tab **Basics:**
   - **Subscription:** sua sub
   - **Resource group:** `rg-lab-final`
   - **Environment name:** `cae-helpsphere-final`
   - **Region:** `East US 2`
   - **Zone redundancy:** `Disabled` (lab — em prod ative para multi-AZ)
4. Tab **Workload profiles:**
   - **Workload profiles:** `Consumption only` (deixe default)
   - ⚠️ Se aparecer `Consumption + Dedicated`, troque para `Consumption only` — Dedicated cobra ~R$ 250/mês reservados que não usaremos no lab
5. Tab **Monitoring:**
   - **Logs destination:** `Azure Log Analytics`
   - **Log Analytics workspace:** clique no dropdown e selecione `log-helpsphere-ia` do RG `rg-helpsphere-ia` (compartilhado, criado no Bloco 2)
     - Se você não vê esse workspace na lista: **pare aqui** — o Bloco 2 não foi feito ou a sub está errada
6. Tab **Networking:** deixe defaults (managed network, public ingress)
7. Tab **Tags:** herde do RG
8. Clique **Review + create** → **Create**
9. Aguarde provisioning ~3-5min (tempo maior — o ACA Env provisiona infra subjacente AKS-managed) até **Status: Succeeded**

<!-- screenshot: cap02-passo2.3-criar-aca-environment.png -->

> **Alternativa via Azure CLI:**
>
> ```bash
> # Capturar customerId + sharedKey do Log Analytics existente do Bloco 2
> WORKSPACE_ID=$(az monitor log-analytics workspace show \
>   --resource-group rg-helpsphere-ia \
>   --workspace-name log-helpsphere-ia \
>   --query customerId -o tsv)
>
> WORKSPACE_KEY=$(az monitor log-analytics workspace get-shared-keys \
>   --resource-group rg-helpsphere-ia \
>   --workspace-name log-helpsphere-ia \
>   --query primarySharedKey -o tsv)
>
> az containerapp env create \
>   --name cae-helpsphere-final \
>   --resource-group rg-lab-final \
>   --location eastus2 \
>   --logs-destination log-analytics \
>   --logs-workspace-id "$WORKSPACE_ID" \
>   --logs-workspace-key "$WORKSPACE_KEY"
> ```

> **Custo:** ACA Environment em si = **R$ 0 parado** (sem replicas rodando = sem cobrança). Quando você deployar o MCP Server (Cap 05) e n8n (Cap 07), o billing vira: **R$ 0,000024/vCPU-segundo + R$ 0,0000028/GiB-segundo** apenas durante execução (scale-to-zero quando ocioso). Estimativa para o lab: ~R$ 5-10/dia ligado, ~R$ 0,50/dia ocioso.

> **Nota pedagógica — por que reusar Log Analytics do Bloco 2 e não criar `law-lab-final` novo?** 1 Log Analytics workspace = 1 cobrança fixa de ingestão (R$ 13/GiB) + retention. Centralizando no `log-helpsphere-ia`, todos os logs (Hub, Function App, ACA, MCP) caem no mesmo lugar → você consulta 1 query KQL e vê o trace inteiro cross-recurso. **Anti-pattern:** criar 1 workspace por RG → trace fragmentado, 5x cobrança duplicada de retention.

> **Nota pedagógica — `Consumption only` workload profile:** ACA tem 2 modos. **Consumption:** cada replica vive ~5min após última request, depois desliga (scale-to-zero) — perfeito para lab/dev/cargas burst. **Dedicated:** vCPU/RAM reservada 24×7, latência <100ms cold-start, GPU disponível — só faz sentido em produção com SLA agressivo. **No lab, sempre Consumption.**

---

## Passo 2.4 — Atribuir role `AcrPull` ao Managed Identity do Bloco 2

A Managed Identity `mi-helpsphere-ia` (criada no Bloco 2 no RG `rg-helpsphere-ia`) precisa de permissão para **pullar imagens** do ACR `acrhelpsphere<rand>` recém-criado. Sem isso, o deploy do MCP Server (Cap 05) falha com `UNAUTHORIZED: authentication required`.

**No Portal Azure (caminho visual):**

1. Barra superior → buscar `acrhelpsphere<rand>` → clicar no recurso
2. Menu lateral esquerdo → **Access control (IAM)**
3. Clique **+ Add** → **Add role assignment**
4. Tab **Role:** busque `AcrPull` → selecione → **Next**
5. Tab **Members:**
   - **Assign access to:** `Managed identity`
   - Clique **+ Select members** → no painel direito:
     - **Subscription:** sua sub
     - **Managed identity:** `User-assigned managed identity`
     - Selecione `mi-helpsphere-ia` (vai aparecer com badge `rg-helpsphere-ia`)
   - **Select** → **Next**
6. Tab **Conditions:** deixe `Constrain roles` desmarcado
7. Tab **Review + assign** → **Review + assign** → confirme
8. Aguarde ~30s — banner verde **"Added role assignment"**

<!-- screenshot: cap02-passo2.4-acrpull-role-assignment.png -->

> **Alternativa via Azure CLI** (mais robusta — recomendada porque captura IDs dinamicamente):
>
> ```bash
> # Capturar Principal ID do MI do Bloco 2
> PRINCIPAL_ID=$(az identity show \
>   --name mi-helpsphere-ia \
>   --resource-group rg-helpsphere-ia \
>   --query principalId -o tsv)
>
> # Capturar Resource ID do ACR recém-criado (substitua ACR_NAME)
> ACR_ID=$(az acr show \
>   --name "$ACR_NAME" \
>   --resource-group rg-lab-final \
>   --query id -o tsv)
>
> # Atribuir role AcrPull
> az role assignment create \
>   --assignee-object-id "$PRINCIPAL_ID" \
>   --assignee-principal-type ServicePrincipal \
>   --role AcrPull \
>   --scope "$ACR_ID"
>
> # Validar
> az role assignment list \
>   --assignee "$PRINCIPAL_ID" \
>   --scope "$ACR_ID" \
>   --query "[].{role:roleDefinitionName, scope:scope}" -o table
> # Esperado: 1 linha com role=AcrPull
> ```

> **Custo:** RBAC role assignments são **gratuitos** — não há cobrança por número de roles ou scopes.

> **Nota pedagógica — `--assignee-object-id` vs `--assignee`:** o flag `--assignee` aceita UPN/email/objectId mas faz **lookup no Microsoft Graph** que falha com `Insufficient privileges` se o usuário não tem permissão `Directory.Read.All`. Usar `--assignee-object-id` + `--assignee-principal-type ServicePrincipal` pula o lookup → funciona mesmo com permissões mínimas. **Cravar este pattern como default em scripts CI/CD.**

> **Nota pedagógica — por que `AcrPull` e não `Contributor` no ACR?** Princípio do least-privilege. `Contributor` permite delete do registry inteiro, criar webhooks, push de imagens — o MI só precisa **ler/pull**. `AcrPull` é o role minimal exato. Em produção com auditor pelas costas, `Contributor` no ACR seria flag vermelho de compliance.

---

## Passo 2.5 — Validar fundação no Portal

**No Portal Azure:**

1. Vá ao RG `rg-lab-final` → **Overview**
2. Confirme visualmente que existem **2 recursos:**
   - `acrhelpsphere<rand>` (Container registry)
   - `cae-helpsphere-final` (Container Apps Environment)
   - ⚠️ Se aparecer um terceiro recurso `workspace-cae-helpsphere-final<rand>` (Log Analytics), você esqueceu de selecionar o workspace existente no Passo 2.3 — veja Surpresas pedagógicas abaixo
3. Em `cae-helpsphere-final` → **Overview** → confirme:
   - **Provisioning state:** `Succeeded`
   - **Log Analytics customer ID:** mesmo `customerId` do `log-helpsphere-ia` (compare com RG `rg-helpsphere-ia`)
4. Em `acrhelpsphere<rand>` → **Access control (IAM)** → **Role assignments** tab → confirme:
   - 1 linha com `mi-helpsphere-ia` + role `AcrPull`

<!-- screenshot: cap02-passo2.5-rg-overview-validacao.png -->

---

## Validação end-to-end

```bash
# 1. RG existe
az group show --name rg-lab-final \
  --query "{name:name, location:location, state:properties.provisioningState}" -o table
# Esperado: rg-lab-final, eastus2, Succeeded

# 2. ACR existe e SKU correto
az acr show --name "$ACR_NAME" --resource-group rg-lab-final \
  --query "{name:name, sku:sku.name, loginServer:loginServer, adminEnabled:adminUserEnabled}" -o table
# Esperado: name=acrhelpsphere<rand>, sku=Basic, adminEnabled=false

# 3. ACA Environment existe e linka ao Log Analytics correto
az containerapp env show --name cae-helpsphere-final --resource-group rg-lab-final \
  --query "{name:name, state:properties.provisioningState, logsCustomerId:properties.appLogsConfiguration.logAnalyticsConfiguration.customerId}" -o table
# Esperado: state=Succeeded, customerId = mesmo do log-helpsphere-ia

# 4. AcrPull role assignment cravado
PRINCIPAL_ID=$(az identity show --name mi-helpsphere-ia --resource-group rg-helpsphere-ia --query principalId -o tsv)
ACR_ID=$(az acr show --name "$ACR_NAME" --resource-group rg-lab-final --query id -o tsv)
az role assignment list --assignee "$PRINCIPAL_ID" --scope "$ACR_ID" \
  --query "[].roleDefinitionName" -o tsv
# Esperado: AcrPull

# 5. Smoke pull anônimo (deve falhar — confirma que admin disabled está respeitado)
az acr login --name "$ACR_NAME" 2>&1 | head -5
# Esperado: erro "admin user is disabled" OU sucesso via az credential (ambos OK — confirma que não há fallback público)
```

---

## Checklist final

```text
[ ] Resource Group rg-lab-final criado em East US 2
[ ] Tags cost-center, environment, application, course aplicadas no RG
[ ] ACR acrhelpsphere<rand> criado com SKU Basic + adminUserEnabled=false
[ ] ACR loginServer anotado para uso nos .env (formato acrhelpsphere<rand>.azurecr.io)
[ ] ACA Environment cae-helpsphere-final criado em Consumption only
[ ] ACA Environment linkado ao Log Analytics log-helpsphere-ia (RG rg-helpsphere-ia)
[ ] Provisioning state de cae-helpsphere-final = Succeeded
[ ] Role AcrPull atribuído à mi-helpsphere-ia no scope do ACR
[ ] az role assignment list confirma 1 entry de AcrPull
[ ] RG rg-lab-final aparece com 2 recursos no Portal (ACR + ACA Env)
```

---

## Surpresas pedagógicas (capturadas em smoke runs)

- ⚠️ **ACR name globalmente único + sem hífen + lowercase** — Azure rejeita `acr-helpsphere` (hífen), `ACRhelpsphere` (uppercase) e qualquer nome já usado no mundo (formato DNS). Workaround: sempre concatenar 6 hex chars aleatórios (`acrhelpsphere8a3f2d`). **Anti-pattern comum:** copy-paste do nome de outro aluno → falha "Registry name not available".
- ⚠️ **ACA Environment provisiona Log Analytics novo se você esquecer de selecionar o existente** — no tab **Monitoring**, se deixar **Logs destination = Azure Log Analytics** mas NÃO selecionar workspace, o Portal **silenciosamente cria** `workspace-cae-helpsphere-final<rand>` no `rg-lab-final`. Isso **fragmenta** os logs (Bloco 2 vai pra um, Lab Final pra outro) e duplica cobrança de ingestão. Workaround: sempre selecionar `log-helpsphere-ia` explicitamente; se errou, delete o ACA Env e refaça (não dá pra trocar workspace depois de criado).
- ⚠️ **`AcrPull` role assignment leva 30-60s para propagar** — atribui via Portal/CLI, mas se você imediatamente rodar `az containerapp create --image acrhelpsphere<rand>.azurecr.io/...` no Cap 05, pode dar `UNAUTHORIZED`. Workaround: aguarde 60s após criar o role antes de fazer pull/deploy. **Anti-pattern:** debugar erro de imagem por 20min sem perceber que é só propagação RBAC.
- ⚠️ **`az role assignment create --assignee <upn>` falha com permissões mínimas** — o flag `--assignee` faz lookup no Microsoft Graph e exige `Directory.Read.All`. Em subs corporativas restritas, isso falha mesmo se o usuário tem `User Access Administrator`. Workaround: usar `--assignee-object-id <objectId> --assignee-principal-type ServicePrincipal` (pula o lookup). **Cravar pattern em todos os scripts CI/CD.**
- ⚠️ **MI do Bloco 2 vive em RG separado (`rg-helpsphere-ia`) — não tente recriar local** — alguns alunos criam `mi-lab-final` novo no `rg-lab-final` para "simplificar". Resultado: o MI novo NÃO tem roles em Service Bus (Cap 08), AI Search (do `apex-rag-lab` Cap 05), ou Speech (Cap 06) — todas pré-cravadas no MI do Bloco 2. Você teria que repetir 5+ role assignments. Workaround: **sempre reusar `mi-helpsphere-ia` cross-RG**. RBAC funciona perfeitamente em escopos cruzados.
- ⚠️ **ACR Basic tem limit de 10 GiB de storage** — ver [`_disclaimers.md`](./_disclaimers.md) **AMB-1** para o cap absoluto. Sintoma: `denied: requested access to the resource is denied` no `docker push`. Workaround: `az acr repository delete --name <acr> --image <repo>:<tag>` para liberar espaço, ou subir para Standard. **Em produção, sempre cravar política de retention de tags (`az acr config retention`).**
- ⚠️ **Workload profile `Consumption + Dedicated` aparece como default em algumas subs** — se você tem subs corporate com policy padrão, o Portal pode pré-selecionar Consumption + Dedicated → cobra ~R$ 250/mês reservados mesmo com 0 apps deployados. Workaround: **explicitamente selecionar `Consumption only`** no Tab **Workload profiles**. Verificar via CLI: `az containerapp env show --query 'properties.workloadProfiles'` (deve listar apenas `Consumption`).
- ⚠️ **`--admin-enabled true` no ACR vira credencial órfã** — se em algum debug você habilitou admin user (ex.: para um `docker login` rápido), as 2 senhas master nunca expiram automaticamente. Vetor de comprometimento de longo prazo. Workaround: depois de debugar, `az acr update --name <acr> --admin-enabled false` + rotacionar passwords (`az acr credential renew`). **Em produção: nunca habilite — Bicep policy `Microsoft.Authorization/policyDefinitions` deve denyar.**

---

## Troubleshooting rápido

| Sintoma | Causa provável | Fix |
|---|---|---|
| `Registry name 'acrhelpsphere' is not available` | Nome já registrado globalmente | Adicione 6 hex chars aleatórios ao final |
| `The subscription is not registered to use namespace 'Microsoft.App'` | Resource Provider não habilitado | `az provider register --namespace Microsoft.App && az provider register --namespace Microsoft.OperationalInsights` |
| ACA Env stuck em `Provisioning` >10min | Quota regional esgotada (raro mas acontece em East US 2) | Trocar para `East US` ou `South Central US` no `--location` |
| `UNAUTHORIZED: authentication required` ao pull do ACR | Role `AcrPull` não propagado ainda OU MI errado | Aguardar 60s; `az role assignment list --assignee <principalId>` para confirmar |
| Log Analytics workspace não aparece no dropdown | Workspace está em outra sub OU sem permissão `Microsoft.OperationalInsights/workspaces/sharedKeys/action` | Validar com `az monitor log-analytics workspace show -g rg-helpsphere-ia -n log-helpsphere-ia` |
| `Insufficient privileges to complete the operation` no role assignment | Falta `User Access Administrator` ou `Owner` na sub | Solicitar elevação ou usar conta com Owner |

---

## Próximo capítulo

[03 — Copilot Studio Setup](./03-copilot-studio-setup.md)
