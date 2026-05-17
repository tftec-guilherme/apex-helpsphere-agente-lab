# Disclaimers consolidados — Lab Final D06 (apex-helpsphere-agente-lab)

> **Version-anchor:** `Q2-2026` · **Última revisão:** 2026-05-09 · **Status:** Cravado por @aiox-master a partir das decisões da Wave 4 + audits A-H + sessão noturna 2026-05-09 · **Owner editorial:** prof Guilherme Campos
>
> Este arquivo consolida as **4 decisões cravadas (AMB-1 a AMB-4)** sobre tier/licenciamento/custo/cleanup que afetam **múltiplos capítulos** do companion. Antes vivam inline (espalhados em `01-*.md`, `03-*.md`, `06-*.md`, `07-*.md`, `08-*.md`) — risco de drift quando a decisão muda. **Política:** capítulos referenciam **AMB-N** apontando aqui; nunca duplicar conteúdo.
>
> **Quando atualizar este arquivo:** sempre que (a) Microsoft mudar política de tier/feature, (b) catálogo de voices/SKUs mudar, (c) custo BRL flutuar >20%, (d) prof revisar pedagogicamente. Bumpe o `version-anchor` (ex.: `Q3-2026`) e cole aviso de atualização no PR.
>
> **Como capítulos referenciam:** uma callout curta apontando aqui:
>
> > [!IMPORTANT] **Tier / Licenciamento**
> > Decisões de tier e licenciamento consolidadas em [_disclaimers.md](./_disclaimers.md). Veja AMB-N.

---

## AMB-1 — ACR Basic (R$ 35/mês fixo)

> [!NOTE] **AMB-1 — Container Registry tier: Basic**
>
> **TL;DR:** Use Azure Container Registry **Basic** (~R$ 35/mês fixo) para todos os Container Apps deste Lab Final. Nunca Standard/Premium no escopo do lab.
>
> **Detalhe técnico:** Basic dá 10 GiB storage + 1 webhook + ACR Tasks (6.000 build-min/mês incluídos) — suficiente para `mcp-helpsphere:v1` (~50 MiB) + `n8n` opcional. Standard (R$ 100/mês) só justifica geo-replication, 3 ou mais webhooks ou content trust. Premium (R$ 500+/mês) é Private Link + Customer-Managed Keys + tasks paralelas — produção crítica. Cobra mesmo parado, sem scale-to-zero. Cap absoluto storage Basic = 10 GiB; pushar imagens >2 GiB rapidamente estoura.
>
> **Custo no lab realista:** R$ 1-2 prorrated 5 dias (delete RG no Cap 09 zera). Em produção corporate, default = Basic; subir para Standard só quando feature exigir.
>
> **Onde aparece:** `02-resource-group-acr-aca.md` (provisioning ACR), `05-mcp-server-deploy.md` (ACA Env Passo 5.4 + RBAC AcrPull Passo 5.5 + push imagem MCP Passo 5.2 — Story 06.27 moveu ACA Env + RBAC do Cap 02 para Cap 05), `09-cleanup-obrigatorio.md` (delete cascade).
>
> **Cleanup link:** ver `09-cleanup-obrigatorio.md` Passo 9.2 — `az group delete --name rg-lab-final` zera o ACR junto.

---

## AMB-2 — Conta `live.com` NÃO funciona em Copilot Studio (warning)

> [!WARNING] **AMB-2 — Copilot Studio bloqueia Microsoft Account pessoal (`live.com` / `outlook.com` / `hotmail.com`)**
>
> **TL;DR:** Conta MSA pessoal (`@live.com`, `@outlook.com`, `@hotmail.com`) é rejeitada ao criar agent no Copilot Studio. Workaround único: tenant developer M365 grátis (90 dias renováveis).
>
> **Detalhe técnico:** Copilot Studio é Power Platform por baixo — exige tenant Microsoft 365 ou Power Platform standalone. MSA pessoal não tem licença Power Platform. Sintoma: erro `Your account does not have access to Copilot Studio` ou `Power Platform is not available for this account type`. Não é warning bloqueante de hard-stop (você consegue logar), mas trava na criação do agent. Não tente ativar Power Platform na MSA — não existe esse fluxo no portal pessoal.
>
> **Workaround padrão da disciplina:** criar tenant developer M365 grátis em https://developer.microsoft.com/microsoft-365/dev-program (90 dias renováveis indefinidamente, vem com Power Platform + 25 licenças E5 de teste). Cravar a decisão no Cap 01 Passo 1.3 ANTES de chegar no Cap 03 — descobrir o bloqueio só no Cap 03 custa 30-60min de re-setup.
>
> **Onde aparece:** `01-pre-requisitos.md` (Passo 1.3 + Surpresa #2), `03-copilot-studio-setup.md` (Passos 3.0/3.1 + Surpresa #1 + Troubleshooting), `06-speech-stt-tts.md` (Passo 6.7 — canal voice no Copilot), `09-cleanup-obrigatorio.md` (Passo 9.5 — delete agent), `10-troubleshooting.md` (3.1 A2 + Top 10 #1).
>
> **Referência cravada (apêndice E):** `azure-retail/Disciplina_06_IA_Automacao_Azure_Ferramentas_Integradas/07_Material Autoral/Cheat_Sheets/Apendice_E_cheat_licenciamento_power_platform.md` linha 67.
>
> **Cleanup link:** trial 30d expira sozinho; `09-cleanup-obrigatorio.md` Passo 9.5 deleta agent imediato + libera Per-User Premium (~R$ 1.000/mês) se conta corporate.

---

## AMB-3 — PostgreSQL Burstable B1ms cleanup obrigatório

> [!WARNING] **AMB-3 — PostgreSQL Flexible Server Burstable B1ms (R$ 60/mês ligado 24x7)**
>
> **TL;DR:** O PostgreSQL `pg-n8n-rand` (backend metadata do n8n) é o maior dreno de custo do Lab Final. Cobra R$ 60/mês ligado 24x7 mesmo idle. Cleanup do Cap 09 é obrigatório, não opcional.
>
> **Detalhe técnico:** SKU `Standard_B1ms` Burstable (1 vCore + 2 GiB RAM + 32 GiB storage) — escolhido por ser a mais barata permanente (PG não tem free tier no Azure; Free Trial USD 200 só dá 30 dias e não regenera). Diferente de ACA Consumption (R$ 0 parado) e Container Apps com `min-replicas 0` (também R$ 0 parado), o PostgreSQL Flexible Server cobra mesmo idle. Feature `Stop` zera compute mas storage 32 GiB continua faturando ~R$ 5/mês, e dia 8 Azure liga o server automaticamente cobrando R$ 60/mês 24x7 sem aviso (anti server-órfão). Para R$ 0 permanente: delete (não Stop).
>
> **Estratégias pause/resume:** Cap 07 Passo 7.7 oferece Stop temporário (sessões recorrentes curtas — máx 7 dias). Cap 09 Passo 9.2 oferece delete definitivo (caminho oposto). Não misture: Stop do PG + delete do RG falha porque RG só deleta com PG em estado `Ready`.
>
> **Custo no lab realista:** R$ 2-3 por sessão de 8h se Stop ao fim, R$ 0 total se delete. Se esquecer ligado 30 dias = R$ 60 debitados sem tráfego.
>
> **Onde aparece:** `07-n8n-escalation.md` (Passo 7.1 provisioning + Passo 7.7 pause/resume + Surpresas #2/#7), `09-cleanup-obrigatorio.md` (Passo 9.2 delete cascade + Surpresa #4 + Top 10 #6), `10-troubleshooting.md` (3.2 P7 + 3.6 N6 + 3.9 K4).
>
> **Cleanup link:** ver `09-cleanup-obrigatorio.md` Passo 9.2 — `az group delete --name rg-lab-final --yes` zera junto. Cravar Cost Anomaly Alert R$ 50 (Cost Management → Cost alerts → Add → Anomaly) para proteção permanente.

---

## AMB-4 — Service Bus tier Standard obrigatório (não Basic)

> [!WARNING] **AMB-4 — Service Bus tier: Standard (~R$ 50/mês baseline) — Basic NÃO suporta Topics**
>
> **TL;DR:** Use Service Bus Standard (~R$ 50/mês fixo + R$ 0,80/M operações). Nunca Basic — Basic só suporta Queues simples, não suporta Topics + Subscriptions, que são feature core do pattern fan-out deste lab.
>
> **Detalhe técnico:** O Cap 08 cria Topic `tickets-escalated` com Subscription `n8n-escalation-sub` porque o pattern realista é fan-out: escalação → n8n hoje (subscription `n8n-escalation-sub`); amanhã Logic App (`bi-warehouse-sub`); depois Function (`audit-trail-sub`) sem trocar nada no agente. Tentar criar Topic em Basic dá erro 400 silently (Portal cinza o botão sem explicar; CLI retorna `BadRequest: Topic creation is not allowed on basic SKU`). Standard (R$ ~50/mês fixo + R$ 0,80/M operações) adiciona Topics + Subscriptions + 5 GB queue size + transactions. Premium (~R$ 3.500/mês) só faz sentido em produção real com VNet integration + zone redundancy + 1.000 ou mais msg/s.
>
> **Custo no lab realista:** R$ 2-3 por sessão (provisiona + smoke + delete em 1-2 dias). Operações são gratuitas até 1M/mês — lab gera <100 msg/dia, operações ~R$ 0. Mas Standard cobra baseline R$ ~50/mês mesmo sem mensagens — fee fixo da feature Topics/Subscriptions. Se esquecer ligado 30 dias = R$ 50 debitados sem tráfego.
>
> **Sem feature `Stop`:** diferente do PostgreSQL (AMB-3), Service Bus Standard não pode pausar parcialmente. Único jeito de zerar custo é deletar o namespace e recriar. `delete-pause-recreate` (Cap 08 Passo 8.7) é rápido (~3min provisioning), zera R$ 50/mês.
>
> **Onde aparece:** `01-pre-requisitos.md` (Resumo decisões cravadas + Surpresa #3), `07-n8n-escalation.md` (Passo 7.4 RBAC + Surpresa #6 — Topic vs Queue), `08-service-bus-google-sheets.md` (DISCLAIMER no topo + Passo 8.1 + Surpresa #1 + Gaps), `09-cleanup-obrigatorio.md` (Passo 9.2 delete cascade + Surpresa #5), `10-troubleshooting.md` (3.2 P9 + 3.7 S1/S6 + Top 10 #2).
>
> **Cleanup link:** ver `08-service-bus-google-sheets.md` Passo 8.7 (`az servicebus namespace delete` rápido) ou `09-cleanup-obrigatorio.md` Passo 9.2 (delete RG cascata zera junto).

---

## SUR-CS-Q2-2026-TOPICS — Copilot Studio UI Topics (Trigger Description + nodes agrupados)

**Categoria:** UI / Pedagogia
**Severidade:** MEDIUM (confunde aluno, não bloqueia execução)
**Capítulos afetados:** `00-Lab_Final_Agente_Workflow_Guia_Portal.md` Passo 2.4 + `03-copilot-studio-setup.md` (se houver passo equivalente de topic generative)

**Contexto:** UI de Topics do Copilot Studio Maker mudou em Q2-2026 vs versões anteriores que tinham dropdown explícito "Description-based" e nodes "Ask a question" / "Call an action" no menu raiz.

**Sintomas:**
- Aluno procura **dropdown "Trigger: Description-based"** ao criar topic → não existe mais
- Aluno procura **node "Ask a question"** no menu **+** → não aparece de cara (escondido sob "See more" ou busca)
- Aluno procura **node "Call an action"** → também escondido, às vezes renomeado para **"Add a tool"** ou **"Call a Power Automate flow"**

**Causa raiz:**
- O orquestrador Generative AI agora consulta o campo **Description** do node **Trigger** (automático no canvas) — não há mais opção explícita "Description-based" no UI. O dropdown "Trigger by" às vezes ainda aparece mas é vestigial (mantenha `Phrases` mesmo sem preencher).
- O menu **+ Add node** foi reorganizado em categorias colapsáveis. Nodes menos usados ficam atrás de **"See more"**. Busca textual (`ask`, `call`, `condition`) é o caminho mais rápido.
- Nomes de nodes legacy (`Call an action`) coexistem com novos (`Add a tool` para tools de plugin, `Call a Power Automate flow` para automation) — visualmente parecidos, semanticamente equivalentes para custom action de Foundry Agent.

**Fix adotado (sessão 2026-05-17):**
- Passo 2.4 (guia consolidado) reescrito em 5 sub-passos:
  - 2.4.1 criar topic
  - 2.4.2 configurar trigger via campo Description (sem dropdown)
  - 2.4.3 Ask a question com `Identify: User's entire response` + `Save response as: userQuery`
  - 2.4.4 Call an action placeholder (com nota sobre nomes alternativos)
  - 2.4.5 Save
- Nota explicativa "Por que isso funciona" reforçando semantic match Generative AI vs phrases.

**Lição:** UI de Topics evolui junto com features de Generative Orchestration. Re-validar a cada bump de versão Copilot Studio. Esta entrada cataloga estado da UI em **Q2-2026** (validado em 2026-05-17).

---

## SUR-CS-Q2-2026 — Copilot Studio UI Generative AI mode + Knowledge sources

**Categoria:** UI / Pedagogia
**Severidade:** MEDIUM (confunde aluno, não bloqueia execução)
**Capítulos afetados:** `00-Lab_Final_Agente_Workflow_Guia_Portal.md` Passo 2.2 + `03-copilot-studio-setup.md` Passo 3.3

**Contexto:** UI do Copilot Studio Maker mudou em Q2-2026 vs versões anteriores.

**Sintomas:**
- Aluno procura "Menu lateral → Generative AI" e não encontra (migrou pra Settings ⚙️ header ou card na home)
- Aluno procura botão "Save" e não encontra (mudanças auto-persistem)
- Aluno confunde Knowledge sources com onde adicionar o Foundry Agent (Foundry vai como Tool, NÃO como Knowledge source)

**Causa raiz:**
- Configurações de Generative AI migraram pra **Settings header (⚙️)** ou card "Generative AI" na home do agente
- **Não há mais botão Save** na tela de Generative AI — mudanças persistem automaticamente (diferente de Topics, que ainda têm Save explícito)
- **Novos agentes já nascem em modo Generative por default** — passo é mais confirmação que configuração. Tenants legacy com CoE policy podem ainda nascer em Classic

**Fix adotado (Story 06.28 — 2026-05-14):**
- Passo 2.2 (guia consolidado) reescrito em 3 sub-passos: 2.2.1 confirmar modo / 2.2.2 confirmar Knowledge vazio / 2.2.3 persistência implícita
- Passo 3.3 (cap 03) reescrito em 4 sub-passos espelhados + Content moderation explicitado
- Notas pedagógicas reforçando "Foundry como Tool (Parte 3+4) vs Knowledge source nativo"

**Lição:** UI do Copilot Studio muda rápido — re-validar a cada ~6 meses ou no próximo bump de versão. Esta entrada cataloga estado da UI em **Q2-2026** (validado em 2026-05-14).

---

## Histórico de mudanças

| Data | Versão | Mudança | Origem |
|---|---|---|---|
| 2026-05-17 | Q2-2026 | SUR-CS-Q2-2026-TOPICS catalogada: Trigger via campo Description (sem dropdown) + nodes agrupados sob "See more" / busca | @aiox-master sessão debug Lab Final |
| 2026-05-14 | Q2-2026 | SUR-CS-Q2-2026 catalogada: Copilot Studio UI Generative AI mode + Knowledge sources (Story 06.28) | @aiox-master sessão correção |
| 2026-05-09 | Q2-2026 | Arquivo cravado consolidando AMB-1 a AMB-4 (drift fix sessão noturna 2026-05-09) | @aiox-master sessão close-the-day |

---

## Próximos itens a consolidar (backlog)

- Foundry Agent Service exige sub Pay-As-You-Go (Free Trial USD 200 não cobre) — atualmente em `01-pre-requisitos.md` Surpresa #1 e `10-troubleshooting.md` 3.1 A1. Promover a AMB-5 se aparecer drift entre caps.
- Workload profile `Consumption only` (não `Consumption + Dedicated`) — atualmente em `05-mcp-server-deploy.md` Surpresa (Passo 5.4) e `10-troubleshooting.md` 3.2 P5 / Top 10 #4. Promover a AMB-6 se decisão tipa permanente.
- `n8nio/n8n:1.6` pinned (não `:latest`) — atualmente em `07-n8n-escalation.md` Surpresa #1 e `10-troubleshooting.md` 3.3 C7 / Top 10 #7. Promover a AMB-7 se versão bumpar.
