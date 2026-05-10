# Capítulo 01 — Pré-requisitos

> **Objetivo:** validar **toda** a base operacional antes de provisionar qualquer recurso do Lab Final — sub Pay-As-You-Go, Foundry Hub do Bloco 2, conta Microsoft Power Platform com Copilot Studio, Docker Desktop, Azure CLI, e stack dev local. Saída esperada: 9 checklist boxes marcados verdes + nenhum bloqueio para o Capítulo 02.
>
> **Tempo:** 30-45 min (skip ~20 min se você fez o Bloco 2 / Lab Intermediário sem reset; +60-90 min se precisar provisionar Foundry Hub do zero).
>
> **Status:** `v0.2.0-portal` ⚠️ EXPANDIDO (era `v0.1.0-init` outline) — derivado de `Lab_Final_Agente_Workflow_Guia_Portal.md` Pré-requisitos (linhas 24-58) + Tabela de recursos (linhas 59-80).

---

## ⚙️ Sintaxe de comandos shell

> **Os blocos shell deste guia usam PowerShell** (Windows-first, alinhado ao público da disciplina). Continuação de linha é `` ` `` (backtick), variáveis de ambiente via `$env:VAR = "..."`, substituição de comando via `(cmd)` ou `$(cmd)`.
>
> **Linux / Mac / WSL:** troque `$env:VAR = "..."` por `export VAR="..."`, `$env:VAR = (cmd)` por `export VAR=$(cmd)`, e `` ` `` por `\` no fim das linhas.

---

## Pré-requisitos (este capítulo é o root — pré-condições externas ao repo)

- ✅ Você completou o **Bloco 2 da Disciplina 06** (apex-helpsphere SaaS provisionado em `rg-lab-intermediario`) — fornece Foundry Hub `aifhub-apex-prod` + Managed Identity `mi-helpsphere-ia` + Log Analytics `log-helpsphere-ia` que serão **reusados** neste lab.
- ✅ Você completou o **Lab Intermediário** (RAG HelpSphere) — fornece Function App `func-helpsphere-rag-{rand}` que será chamada pela tool `search_kb` no Capítulo 04.
- ✅ Você tem acesso de Owner ou Contributor + UAA na sub Azure que vai usar.
- ✅ Você tem ~R$ 22-30 disponíveis (custo realista do lab provisionado e deletado no mesmo dia — ver tabela abaixo).

> **Atenção custo + Free Trial:** este lab **NÃO funciona em Free Trial USD 200** — Foundry Agent Service exige sub Pay-As-You-Go ativa. ~R$ 380/mês se ligado, **R$ 22-30 no lab realista** (provisionar + deletar mesmo dia). Capítulo 09 (cleanup obrigatório) é parte do lab, não opcional.

---

## Resumo dos 7 pré-requisitos que você vai validar

| # | Pré-requisito | Como validar | Bloqueia? |
|---|---|---|---|
| 1 | Sub Azure Pay-As-You-Go + roles | `az account show` + `az role assignment list` | Cap 02 |
| 2 | Foundry Hub `aifhub-apex-prod` em `rg-lab-intermediario` | Portal AI Foundry → Hubs | Cap 04 |
| 3 | Conta Microsoft + Copilot Studio Trial 30d | https://copilotstudio.microsoft.com/ | Cap 03 |
| 4 | Fork `apex-helpsphere-agente-lab` + clone local | `git remote -v` | Todos |
| 5 | Docker Desktop 4.30+ com WSL 2 | `docker version` | Cap 05 (build imagem MCP) |
| 6 | Azure CLI 2.60+ + extensions `containerapp` + `ml` | `az --version` | Todos |
| 7 | Stack dev local (Python 3.11+ / Node 18+ / Git / VS Code) | `python --version` etc | Cap 04+ |

**Decisões cravadas neste lab:** ACR `Basic` + Service Bus `Standard` obrigatório (Cap 08 cria Topic `ticket-escalations`, e tier Basic NÃO suporta Topics).

> [!IMPORTANT] **Tier / Licenciamento**
> Decisões de tier e licenciamento consolidadas em [`_disclaimers.md`](./_disclaimers.md). Veja **AMB-1** (ACR Basic) e **AMB-4** (Service Bus Standard).

> **Nota pedagógica — por que validar TUDO antes em vez de tropeçar capítulo a capítulo?** Lab Final tem 9h de duração e 8 partes com dependências cross-recurso (Foundry → MCP → Speech → Service Bus → n8n → Logic App). Cada falha de pré-requisito descoberta no meio custa 30-60min de retrabalho. **Front-load a validação aqui** e o resto do lab flui.

---

## Passo 1.1 — Validar sub Azure Pay-As-You-Go + roles

**No terminal local (PowerShell com Azure CLI logado):**

```powershell
# 1. Sub correta + tipo PAYG
az account show --query "{name:name, state:state, type:subscriptionPolicies.quotaId}" -o table
# Esperado: state=Enabled, type=PayAsYouGo_2014-09-01 (se aparecer FreeTrial_*, PARE — converta no Portal)

# 2. Role Owner ou Contributor+UAA
az role assignment list --assignee $(az account show --query user.name -o tsv) `
  --query "[].{role:roleDefinitionName, scope:scope}" -o table
# Esperado: Owner OU (Contributor + User Access Administrator) no scope da sub
```

Se você só tem `Reader` ou `Contributor` sem UAA, **peça ao admin do tenant** antes de continuar — Capítulo 04 (RBAC do MI no Foundry Project) e Capítulo 05 (App Registration MCP) vão falhar.

<!-- screenshot: cap01-passo1.1-az-account-show-output.png -->

> **Alternativa via Portal Azure:**
> Portal → **Subscriptions** → sua sub → **Access control (IAM)** → tab **Role assignments** → filtrar por seu email. Confirme `Owner` ou `Contributor + User Access Administrator`.

> **Custo:** validação é gratuita (só leitura). R$ 0,00.

> **Nota pedagógica — por que UAA importa em vez de só Contributor?** O Capítulo 04 atribui role `Cognitive Services User` ao Managed Identity do MCP Server no Foundry Hub. **Atribuir role exige UAA**, não só Contributor. Owner já tem UAA implícito; Contributor pelado falha em `az role assignment create` com erro `AuthorizationFailed`.

---

## Passo 1.2 — Validar Foundry Hub `aifhub-apex-prod` (do Bloco 2)

**No Azure Portal (https://portal.azure.com):**

1. Resource Groups → abra `rg-lab-intermediario` (criado no Bloco 2).
2. Verifique que existem nesse RG:
   - **Hub** Azure AI Foundry: `aifhub-apex-prod`
   - **Managed Identity** (User-assigned): `mi-helpsphere-ia`
   - **Log Analytics workspace**: `log-helpsphere-ia`
   - **Application Insights**: `ai-helpsphere-rag` (compartilhado com Lab Inter)
3. Abra `aifhub-apex-prod` → menu lateral **Models + endpoints** → confirme deployment `gpt-4.1-mini` ativo (status `Succeeded`).

<!-- screenshot: cap01-passo1.2-foundry-hub-aifhub-apex-prod.png -->

> **Alternativa via Azure CLI:**
> ```powershell
> # Confirma os 4 recursos do Bloco 2 existindo
> az resource list --resource-group rg-lab-intermediario `
>   --query "[].{name:name, type:type}" -o table
>
> # Confirma deployment gpt-4.1-mini
> az cognitiveservices account deployment list `
>   --name aifhub-apex-prod `
>   --resource-group rg-lab-intermediario `
>   -o table
> ```

> **Custo:** Hub e MI são gratuitos (cobrança vem em deployments). R$ 0,00 só por validar.

> **Atenção breaking — se o Hub não existe:** volte ao Bloco 2 e provisione o ambiente base. Criar Hub do zero aqui dispara fluxo de quota Azure OpenAI (aprovação 24-72h). Não pule o Bloco 2.

> **Nota pedagógica — Hub vs Project, por quê:** Hub centraliza networking + storage + Application Insights + Key Vault. Projects (criados no Cap 04) herdam essa fundação e isolam **agentes + threads + deployments**. Pattern Microsoft para multi-equipe: 1 Hub corporate, N Projects por squad.

---

## Passo 1.3 — Conta Microsoft + Copilot Studio Trial 30 dias

**No browser:**

1. Acesse https://copilotstudio.microsoft.com/ logado com a conta Microsoft que você vai usar para o lab.
2. Se for primeira vez: aceite o **30-day Trial** quando solicitado (botão **Start free trial**). Sem cartão de crédito — vence em 30 dias automaticamente.
3. Confirme que a conta tem licenças Power Platform: header superior direito → ícone de gear → **Admin center** → **Environments**. Você deve ver pelo menos um environment Default.

<!-- screenshot: cap01-passo1.3-copilot-studio-trial-ativo.png -->

> **Atenção warning — conta `live.com` (Outlook pessoal) NÃO funciona:** Copilot Studio exige tenant Microsoft 365 ou Power Platform. Conta `@outlook.com` / `@hotmail.com` / `@live.com` é rejeitada com erro `Your account doesn't have access to Copilot Studio`. Workaround: conta corporativa (`@suaempresa.com`) ou tenant developer M365 grátis em https://developer.microsoft.com/microsoft-365/dev-program (90 dias renováveis).

> **Custo:** Trial gratuito 30 dias · após trial R$ 90/usuário/mês · no lab realista R$ 0 (cleanup antes do trial expirar).

> **Nota pedagógica — Copilot Studio Trial é por usuário, não por tenant:** trial não compartilha. Em sala de aula cada aluno precisa da própria trial — confirme antes do recording.

---

## Passo 1.4 — Forkar e clonar `apex-helpsphere-agente-lab`

**No GitHub:** acesse https://github.com/tftec-guilherme/apex-helpsphere-agente-lab → botão **Fork** (canto superior direito) → mantenha nome `apex-helpsphere-agente-lab`.

**No terminal local** (substitua `<SEU-USER>` pelo seu username GitHub):

```powershell
git clone https://github.com/<SEU-USER>/apex-helpsphere-agente-lab.git
cd apex-helpsphere-agente-lab
git remote add upstream https://github.com/tftec-guilherme/apex-helpsphere-agente-lab.git
git remote -v    # Esperado: origin=<SEU-USER>, upstream=tftec-guilherme
```

> **Custo:** R$ 0,00. GitHub fork é gratuito.

> **Nota pedagógica — fork vs clone direto:** o fork dá a você um `origin` mutável (commitar adaptações suas — secrets, customizações de prompt, screenshots). O `upstream` permite puxar atualizações da turma quando o prof publicar. Clone direto = read-only.

---

## Passo 1.5 — Docker Desktop 4.30+ com WSL 2

**No terminal local:**

```powershell
docker version    # Esperado: Client 4.30+ / Server Engine 25.x+
```

Se aparecer `Cannot connect to the Docker daemon`, abra Docker Desktop no menu Iniciar e aguarde a baleia ficar verde. **Confirmar WSL 2 backend (Windows):** Docker Desktop → gear → **General** → checkbox **Use the WSL 2 based engine** marcado.

<!-- screenshot: cap01-passo1.5-docker-version-output.png -->

> **Custo:** R$ 0,00 (Docker Desktop pessoal é gratuito; uso comercial >250 funcionários exige Pro/Team).

> **Nota pedagógica — por que precisamos Docker se o ACA roda na nuvem?** Capítulo 05 builda a imagem `mcp-helpsphere:v1.0` localmente via `docker build` (mais rápido que ACR Tasks remoto), depois `az acr login` + `docker push`. Pattern: build local quando dev rápido + push pro ACR; build remoto (ACR Tasks) quando CI/CD ou hardware fraco.

---

## Passo 1.6 — Azure CLI 2.60+ com extensions `containerapp` + `ml`

**No terminal local:**

```powershell
az --version                                          # Esperado: 2.60.0+
az extension add --name containerapp --upgrade
az extension add --name ml --upgrade
az extension list --query "[].{name:name, version:version}" -o table
az login
az account set --subscription "<nome ou id da sub do Passo 1.1>"
```

Se CLI < 2.60: `az upgrade` (Windows: novo MSI em https://aka.ms/installazurecliwindows).

> **Custo:** R$ 0,00.

> **Nota pedagógica — `az upgrade` NÃO atualiza extensions:** core (~80% dos serviços) e extensions são versionados separados (`containerapp` é GA mas extende; `ml` cobre AI Foundry/Azure ML). Sempre `az extension add --name <nome> --upgrade` em paralelo ao `az upgrade`.

---

## Passo 1.7 — Stack dev local (Python 3.11+ / Node 18+ / Git / VS Code)

**No terminal local, validar as 4 ferramentas:**

```powershell
python --version    # Esperado: Python 3.11.x+
node --version      # Esperado: v18.x+
git --version       # Esperado: git 2.40+ (qualquer 2.x recente serve)
code --version      # Esperado: 1.85+
```

Se Python < 3.11, baixe https://www.python.org/downloads/ e marque **Add Python to PATH** no instalador.

**VS Code extensions exigidas no lab:**

```powershell
code --install-extension ms-python.python
code --install-extension ms-azuretools.vscode-bicep
code --install-extension ms-azuretools.vscode-docker
code --install-extension humao.rest-client
code --install-extension ms-azuretools.vscode-azurecontainerapps
```

> **Custo:** R$ 0,00. Tudo gratuito.

> **Nota — Functions Core Tools 4.x é OPCIONAL no Lab Final:** o agente Foundry roda via SDK Python `azure-ai-projects`, não Functions. Só instale (`npm install -g azure-functions-core-tools@4`) se quiser debugar a `RAG_FUNCTION_URL` do Lab Intermediário localmente.

---

## Validação end-to-end

Rode este bloco depois de completar Passos 1.1 a 1.7. **Todos** os comandos devem retornar sucesso:

```powershell
# 1. Sub PAYG + role correta
az account show --query "{state:state, name:name}" -o table
# Esperado: state=Enabled

# 2. RG do Bloco 2 existindo com Foundry Hub
az resource show `
  --resource-group rg-lab-intermediario `
  --name aifhub-apex-prod `
  --resource-type "Microsoft.MachineLearningServices/workspaces" `
  --query "{name:name, location:location}" -o table
# Esperado: linha com aifhub-apex-prod / eastus2

# 3. Deployment gpt-4.1-mini ativo
az cognitiveservices account deployment show `
  --name aifhub-apex-prod `
  --resource-group rg-lab-intermediario `
  --deployment-name gpt-4.1-mini `
  --query "properties.provisioningState" -o tsv
# Esperado: Succeeded

# 4. Docker rodando
docker version --format '{{.Server.Version}}'
# Esperado: 25.x ou superior

# 5. Az CLI extensions
az extension list --query "[?contains(['containerapp','ml'], name)].name" -o tsv
# Esperado: containerapp`nml (2 linhas)
```

---

## Checklist final

```text
[ ] Sub Azure Pay-As-You-Go ativa, role Owner ou Contributor+UAA confirmada
[ ] Foundry Hub aifhub-apex-prod existindo em rg-lab-intermediario (Bloco 2)
[ ] Deployment gpt-4.1-mini ativo no Hub
[ ] mi-helpsphere-ia + log-helpsphere-ia + ai-helpsphere-rag presentes em rg-lab-intermediario
[ ] Conta Microsoft com Copilot Studio Trial 30d ativo (NÃO live.com)
[ ] Fork apex-helpsphere-agente-lab + clone local + remote upstream configurado
[ ] Docker Desktop 4.30+ rodando, WSL 2 backend habilitado
[ ] Azure CLI 2.60+ logado na sub correta com extensions containerapp+ml
[ ] Python 3.11+, Node 18+, Git, VS Code com 5 extensions instaladas
```

Se TODOS os 9 boxes estão marcados → siga para Capítulo 02. Se algum falhou → resolva antes (este capítulo é hard-gate).

---

## Surpresas pedagógicas (capturadas em smoke runs)

- ⚠️ **Free Trial USD 200 não funciona neste lab** — Foundry Agent Service exige sub Pay-As-You-Go ativa. Tentativa em Free Trial dispara erro `SubscriptionNotRegistered` ao chamar `client.agents.create_agent`. Workaround: converter sub em PAYG no Portal (botão **Upgrade** → cartão de crédito).
- ⚠️ **Conta `live.com` rejeitada em Copilot Studio** — ver [`_disclaimers.md`](./_disclaimers.md) **AMB-2** para causa-raiz, workaround (tenant dev M365 grátis) e referência cravada no Apêndice E.
- ⚠️ **Service Bus Basic não suporta Topics** — ver [`_disclaimers.md`](./_disclaimers.md) **AMB-4** para a decisão Standard obrigatório + custo + erro `BadRequest: Topics are not supported on Basic tier`.
- ⚠️ **Contributor sem User Access Administrator falha em `az role assignment create`** — erro `AuthorizationFailed: client does not have authorization to perform action 'Microsoft.Authorization/roleAssignments/write'`. Workaround: peça ao admin do tenant para conceder `User Access Administrator` no scope da sub OU `Owner` direto.
- ⚠️ **`gpt-4.1-mini` quota request leva 24-72h em sub nova** — se for primeira vez deployando Azure OpenAI nesta sub, Microsoft pode pedir aprovação manual. Workaround: faça o **Bloco 2 da disciplina antes** (já passa pela aprovação) — neste lab você só reusa o deployment existente.
- ⚠️ **`az upgrade` não atualiza extensions** — comum: aluno roda `az upgrade`, comemora `2.60.0`, mas `containerapp` extension fica em versão antiga e dá erro `unknown command`. Sempre `az extension add --name <nome> --upgrade` em paralelo.

---

## Próximo capítulo

[02 — Resource Group + ACR + ACA Environment](./02-resource-group-acr-aca.md)
