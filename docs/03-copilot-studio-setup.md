# Capítulo 03 — Copilot Studio Setup

> **Objetivo:** ativar Copilot Studio Trial 30 dias em environment Development, criar o agent `HelpSphere Tier 1 Agent` em pt-BR com instructions (system prompt) explícitas, habilitar Generative AI mode (free-flowing), criar 2 Topics base (`Saudacao_inicial` declarativo + `Resolver_ticket` description-based com placeholder de Action), e provisionar o canal Microsoft Teams via **Test in Teams** (sem dependência de Tenant Admin). Saída esperada: agent navegável no canvas com 2 topics + 1 channel + 6 checkboxes verdes.
>
> **Tempo:** 45-60 min (15-20 min se você já tem environment Development com licença Power Platform e fez o Passo 1.3 do Capítulo 01)
>
> **Status:** `v0.2.0-portal` ⚠️ EXPANDIDO (era `v0.1.0-init` outline) — derivado de `Lab_Final_Agente_Workflow_Guia_Portal.md` Parte 2 (Passos 2.0-2.5)

---

## Pré-requisitos

- ✅ Capítulo 01 concluído — Passo 1.3 confirma Copilot Studio Trial ativo (https://copilotstudio.microsoft.com/) e environment Power Platform visível em Admin center
- ✅ Capítulo 02 concluído — RG `rg-lab-final` + ACR `acrhelpsphere<rand>` + ACA Environment `cae-helpsphere-final` provisionados (não bloqueante, mas confirma que você está no fluxo certo)
- ✅ Conta Microsoft 365 corporativa OU tenant developer M365 grátis (https://developer.microsoft.com/microsoft-365/dev-program) — **NÃO** funciona com `live.com` / `outlook.com` / `hotmail.com`
- ✅ Browser desktop (Edge, Chrome ou Firefox) — Copilot Studio canvas **não é otimizado para mobile**

> **Atenção warning conta pessoal `live.com`:** Copilot Studio é Power Platform — exige tenant Microsoft 365 ou Power Platform standalone. Conta Microsoft Account pessoal (`@outlook.com` / `@hotmail.com` / `@live.com`) é **rejeitada na criação do agent** com erro `Your account doesn't have access to Copilot Studio` ou `Power Platform is not available for this account type`. Não é uma limitação que dá para contornar dentro do Studio — é falta de licença Power Platform sob a conta. **Workaround padrão da disciplina:** criar tenant developer M365 grátis em https://developer.microsoft.com/microsoft-365/dev-program (90 dias renováveis indefinidamente, vem com Power Platform + 25 licenças E5 de teste). Esta decisão (AMB-2) está cravada no Capítulo 01 Passo 1.3 — se você caiu aqui sem revisitar, volte e confirme.

---

## Resumo dos 5 elementos que vamos cravar no Copilot Studio

| Elemento | Tipo | Configuração-chave | Quando configurar |
|---|---|---|---|
| Trial + Environment | Licenciamento | `Development` (não `Default`) | Passo 3.1 |
| `HelpSphere Tier 1 Agent` | Agent (copilot) | Language `Portuguese (Brazil)` + system prompt 5 regras | Passo 3.2 |
| Generative AI mode | Setting | `Generative (free-flowing)` | Passo 3.3 |
| Topic `Saudacao_inicial` | Declarativo (5 trigger phrases) | Send a message inicial | Passo 3.4 |
| Topic `Resolver_ticket` | Description-based (Generative AI decide) | Ask question → **placeholder** Call an action | Passo 3.5 |
| Canal Microsoft Teams | Channel | **Test in Teams** (sem Tenant Admin) | Passo 3.6 (após Parte 3 do guia canônico) |

> **Nota pedagógica — por que `Development` e não `Default` environment?** Copilot Studio é Power Platform por baixo. Default environment compartilha permissões com TODOS os usuários do tenant — qualquer pessoa pode editar/quebrar seu agent acidentalmente. Development environment isola seu trabalho com permissões específicas do criador. **Em produção corporate sempre use environments segregados (`Dev`, `Test`, `Prod`)** — Default fica reservado para apps de "uso geral" que ninguém quer manter.

> **Nota pedagógica — Topics declarativos vs Generative AI orchestration:** Topics declarativos (com `Trigger phrases` fixas como `oi`, `bom dia`) são **determinísticos** — se a frase bate, o flow roda. Topics description-based deixam a Generative AI decidir quando entrar baseado em descrição em linguagem natural. **Pattern Microsoft:** declarativo para fluxos críticos compliance (saudação padronizada, disclaimer LGPD, encerramento), description-based para tudo que precisa flexibilidade conversacional (resolver ticket, classificar problema, escalar). Misture os dois — não escolha um lado só.

### Tabela de referência — licenciamento Copilot Studio (decisão de comitê em produção)

| Modelo | Cobrança | Quando usar | Bloqueio |
|---|---|---|---|
| **Trial 30 dias** | R$ 0 | Lab, PoC, aprendizado | Vence em 30d, agent + topics são deletados se não migrar licença |
| **Tenant dev M365** | R$ 0 (90d renováveis) | Lab + estudo recorrente | Não pode publicar para usuários reais (terms of use) |
| **Per-User Premium** | R$ 1.000+/usuário/mês | Produção corporate com 50-500 atendentes | Custo fixo independente de uso |
| **Pay-As-You-Go** | ~R$ 0,07/mensagem | Produção com volume baixo/intermitente | Difícil prever budget mensal |
| **Power Platform Cap** | Embutido em E5 enterprise | Tenants já em E5 com Power Platform incluso | Negociação contrato Microsoft |

> **Decisão da disciplina:** Trial 30d para o recording deste lab. Em prova de conceito real corporate, partir para Pay-As-You-Go (controle de custo) e migrar para Per-User só quando volume justificar (~14k mensagens/mês = break-even). Discussão completa no Apêndice E do material autoral D06 (cheat sheet `cheat-licenciamento-power-platform.md`).

---

## Passo 3.0 — Pré-flight: confirmar tipo de conta + DLP policies do tenant

Antes de tocar Copilot Studio, valide 2 coisas que matam 80% dos labs com erro "silencioso":

**No browser:**

1. Abra `https://account.microsoft.com/profile` logado com a conta que você vai usar
2. Confirme o tipo de conta no canto superior direito:
   - ✅ Aceitável: `<seunome>@<empresa>.com`, `<seunome>@<dev>.onmicrosoft.com`
   - ❌ **Bloqueante:** `<seunome>@outlook.com`, `<seunome>@hotmail.com`, `<seunome>@live.com` — pare aqui e crie tenant dev (link Capítulo 01 Passo 1.3)
3. Abra Power Platform Admin Center (https://admin.powerplatform.microsoft.com/) → menu **Policies** → **Data policies**
4. Confirme se existe alguma DLP (Data Loss Prevention) policy ativa que bloqueia o conector **HTTP** ou **Custom Connectors**:
   - Se houver policy com `HTTP` na lista **Blocked connectors**, registre — vai bloquear o Capítulo 08 quando vincular `CallFoundryAgent` Action
   - Se você não tem permissão para ver Data policies, está OK em tenant dev (você é o admin); em corporate, peça ao Power Platform Admin para confirmar que `HTTP` está em `Business` ou `Non-Business` (não em `Blocked`)

<!-- screenshot: cap03-passo3.0-account-tenant-dlp-check.png -->

> **Custo:** R$ 0,00 (validação só de leitura).

> **Nota pedagógica — DLP policies do Power Platform são gatekeepers invisíveis:** muitas equipes só descobrem DLP no momento em que o agent dispara em produção e bate `Connector blocked by data policy`. Front-loadar essa verificação aqui salva 1-2h de debug no Capítulo 08. **Em produção corporate sempre catalogue conectores aprovados antes de iniciar projeto** — patterns vêm do Power Platform CoE Starter Kit da Microsoft.

---

## Passo 3.1 — Confirmar Trial + selecionar environment Development

**No browser:**

1. Abra `https://copilotstudio.microsoft.com/` → faça login com a mesma conta Microsoft 365 corporativa (ou tenant dev) usada no Passo 1.3
2. Se primeiro acesso e o trial ainda não foi ativado, aceite o botão **Start free trial** (sem cartão de crédito — vence em 30 dias automaticamente)
3. No header superior direito, clique no **seletor de environment** (texto pequeno ao lado do avatar — geralmente mostra `Default` se você nunca trocou)
4. Selecione o environment chamado `Development` na lista
   - Se o único environment listado for `Default`, vá ao **Power Platform Admin Center** (https://admin.powerplatform.microsoft.com/) → **Environments** → **+ New** → criar com type `Developer` (gratuito, sem custo de licença) e voltar ao Copilot Studio
5. Confirme no header: agora deve aparecer `Development` selecionado

<!-- screenshot: cap03-passo3.1-environment-development-selecionado.png -->

> **Alternativa via CLI / PAC CLI:**
> Power Platform CLI permite listar environments — útil para confirmar que você criou o Development corretamente:
> ```bash
> # Instalar PAC CLI (Windows)
> winget install Microsoft.PowerAppsCLI
>
> # Login + listar environments
> pac auth create --name dev-helpsphere
> pac admin list
> # Esperado: linha com type=Developer, state=Ready
> ```

> **Custo:** Trial Copilot Studio é **R$ 0,00** durante 30 dias. Após trial: **R$ 1.000+/mês** licença Per-User Premium corporate (não é por mensagem — é por usuário/mês fixo); ou pay-as-you-go ~R$ 0,07/mensagem (PAYG). **No lab realista: R$ 0,00** (cleanup obrigatório no Capítulo 09 antes do trial expirar). Tenant dev M365 grátis também não cobra.

> **Nota pedagógica — por que Trial expira em 30 dias e o Power Platform corporate paga ~R$ 1.000/usuário/mês?** Copilot Studio entrega 3 capacidades caras: (1) GPT-4o consumido por trás do Generative AI mode (Microsoft paga OpenAI), (2) integração nativa com Dataverse/SharePoint/Teams sem cobrar extra, (3) governance enterprise (DLP policies, Power Platform CoE). É um SaaS verticalizado em chatbots de negócio. Para PoC/aprendizado, trial resolve. Para produção, é decisão de comitê — o Apêndice E do material autoral do D06 detalha o ROI breakdown.

---

## Passo 3.2 — Criar agent `HelpSphere Tier 1 Agent`

**No Copilot Studio Maker (canvas principal, environment Development):**

1. Tela inicial → botão **+ Create** (canto superior esquerdo) → **New agent**
2. Você verá a tela "Describe your agent". **Pule** o assistente de criação por descrição (ele tenta gerar via natural language) — clique no link discreto **Skip to configure** (canto inferior direito)
3. Preencher:
   - **Name:** `HelpSphere Tier 1 Agent` (mantenha exatamente este nome — Capítulo 08 referencia este string em Service Bus message metadata)
   - **Description:** `Assistente de tier 1 da Apex HelpSphere — sugere respostas, escala para tier 2 quando necessário.`
   - **Language:** clique no dropdown e selecione `Portuguese (Brazil)` (não `Portuguese (Portugal)` — variantes mudam responses do GPT-4o por trás)
   - **Solution:** mantenha `Default Solution` (não crie solution custom no lab — isso adiciona complexidade de ALM Power Platform que está fora do escopo)
   - **Instructions** (system prompt — cole verbatim, é arquitetura, não enfeite):
     ```text
     Você é o assistente do tier 1 do HelpSphere da Apex Group, central de atendimento.
     Sua função é ajudar atendentes (ex.: Diego) a responder tickets de lojistas e colaboradores internos.

     Regras críticas:
     - Sempre responda em pt-BR a menos que o usuário escreva em outro idioma.
     - Sempre cite a fonte da informação.
     - Se a confidence da sua resposta for menor que 0.5, escale para tier 2.
     - Nunca prometa prazos abaixo de 24h.
     - Se ticket envolver dados pessoais sensíveis, peça redação humana.
     ```
4. Clique **Confirm** (botão azul canto inferior direito)
5. Aguarde provisioning ~10-20s até o agent abrir automaticamente no canvas (tela split com lista de Topics na esquerda + designer na direita). Banner verde **Agent created** no topo confirma sucesso

<!-- screenshot: cap03-passo3.2-agent-criado-canvas.png -->

> **Alternativa via Copilot Studio API (REST):** Existe API pública `https://api.powerplatform.com/copilots` mas é **avant-garde** — em janeiro 2026 ainda não tem stable contract para criação de agents (só read/list). Para o lab, sempre use o Maker UI. Para produção em scale, aguarde GA da API ou use Power Platform CLI (`pac copilot create` em preview).

> **Custo:** criar o agent em si é **R$ 0,00** (metadata só). Cobrança de tokens GPT-4o só dispara quando você abre o **Test pane** (Passo 3.4) ou quando usuários reais conversam via canal Teams (Passo 3.6).

> **Nota pedagógica — `instructions` (system prompt) é arquitetura, não copy:** as 5 regras numeradas são **políticas de produto codificadas em texto natural**. Trocar regra 5 (PII handling) muda comportamento legal/LGPD do agent. Trocar regra 3 (threshold confidence < 0.5) muda quanto agent escala (ROI tier 1 vs tier 2). Trocar regra 4 (prazos < 24h) muda compromisso comercial. **Trate o system prompt como código versionado em Git** (esta repo já versiona ele aqui). Em produção, tenha um doc de governance "quando mudar instructions, quem aprova".

> **Nota pedagógica — Language `Portuguese (Brazil)` muda mais do que tradução:** o setting altera o modelo prompt template interno, formatos de data (`dd/MM/yyyy` vs `MM/dd/yyyy`), formatos de moeda (R$), defaults de conversational fillers (`Aguarde um momento` vs `Hold on`), e até detecção de stop words. Trocar para `English (US)` depois de criar quebra Topics declarativos com `Trigger phrases` em pt-BR. **Decida no momento da criação — replanejar é doloroso.**

---

## Passo 3.3 — Habilitar Generative AI mode (free-flowing)

**No Copilot Studio Maker — agente aberto no canvas:**

1. Menu lateral esquerdo → **Generative AI** (ou clique em **Settings** no header → tab **Generative AI** dependendo da versão)
2. Localize a seção **Orchestration** ou **Mode**:
   - **Mode:** mude de `Classic` (default em alguns tenants) para `Generative (free-flowing)`
   - Banner amarelo aparece confirmando "Topics will be triggered by AI based on description"
3. **Knowledge sources:** **deixe vazio** neste capítulo. Vamos popular via MCP no Capítulo 05 (a tool `search_kb` no Capítulo 04 chama RAG diretamente — Knowledge sources nativas do Copilot Studio não são usadas neste lab, é decisão arquitetural)
4. **Content moderation:** mantenha default (`Medium` — content filter padrão)
5. Clique **Save** (header)

<!-- screenshot: cap03-passo3.3-generative-ai-mode.png -->

> **Custo:** habilitar o mode é **R$ 0,00**. Cobrança de tokens GPT-4o por trás cobra ~R$ 0,01-0,03 por interação completa de usuário (orchestration + topic + response). No lab inteiro: ~R$ 1-3 em smoke runs.

> **Nota pedagógica — `Generative` vs `Classic` orchestration:** Classic é determinístico — só topics com trigger phrases match disparam. Funciona em chatbots simples (FAQ rígido). **Generative** roda um LLM (GPT-4o por trás) que lê (a) histórico de conversa, (b) descrição de cada topic em natural language, (c) intenção implícita do usuário, e decide qual topic faz sentido. **Trade-off:** ganha flexibilidade conversacional, perde previsibilidade (mesma frase pode disparar topic diferente em contextos diferentes). Para tier 1 helpdesk com variedade alta de input, Generative é o caminho. Para fluxos compliance-heavy (assinatura de termo, KYC), volte para Classic naquele topic específico.

> **Nota pedagógica — Knowledge sources deixadas vazias é proposital:** Copilot Studio oferece Knowledge sources nativas (SharePoint, websites, arquivos) que rodam um RAG **dentro** do Power Platform. Funcional, mas: (1) você não controla pipeline de chunking/embedding, (2) cobrança fica embarcada na licença Power Platform, (3) latência e refresh são opacos. **Decisão arquitetural deste lab:** RAG vive no Lab Intermediário (`func-helpsphere-rag` — Azure Functions + AI Search + Azure OpenAI), com pipeline transparente. O agent Foundry (Capítulo 04) chama essa Function via tool `search_kb`. Copilot Studio orquestra o agent Foundry, não faz RAG próprio. **Pattern Microsoft enterprise:** sempre prefira RAG explícito em Azure quando possível.

---

## Passo 3.4 — Criar Topic declarativo `Saudacao_inicial`

Topics são fluxos guiados. Criamos um topic determinístico para padronizar a saudação inicial — **garante** que toda conversa começa com identificação da persona em vez do GPT-4o improvisar.

**No Copilot Studio Maker — agente aberto no canvas:**

1. Menu lateral esquerdo → **Topics** → botão **+ New topic** → escolha **Create from blank** (não use template "From description" para este — queremos controle determinístico)
2. Preencher cabeçalho do topic:
   - **Topic name:** `Saudacao_inicial` (sem espaços, sem hífen — convenção Power Platform)
   - **Trigger:** mude para `Phrases` (não `Description-based`)
   - **Trigger phrases** (clique **+ Add** para cada uma — adicione as 5):
     - `oi`
     - `olá`
     - `bom dia`
     - `boa tarde`
     - `boa noite`
   - **Trigger by message:** deixe `Yes` (default)
3. No canvas do topic (área central), clique no **+** abaixo do node **Trigger** → **Send a message**
4. No node **Send a message**, cole o texto:
   ```text
   Olá! Sou o assistente do HelpSphere — central de atendimento Apex Group.
   Posso ajudar com sugestões de resposta, busca em base de conhecimento e escalação para tier 2.
   Em que posso ajudar com seu ticket?
   ```
5. Clique **Save** (header) → aguarde banner verde **Saved**
6. **Teste rápido:** abra o painel **Test** (ícone de balão de fala canto direito) → digite `bom dia` → o agent deve responder com a saudação literal acima (sem improviso GPT-4o)

<!-- screenshot: cap03-passo3.4-topic-saudacao-trigger-phrases.png -->

> **Custo:** topic em si é **R$ 0,00**. Cada teste no painel Test consome ~R$ 0,001-0,005 em tokens (mensagem curta).

> **Nota pedagógica — 5 trigger phrases é pouco, e tá certo:** algumas equipes empilham 30-40 trigger phrases por topic ("oi", "oi tudo bem", "oi bot", "oie", "ola", ...). **Anti-pattern.** O orchestrator do Copilot Studio com Generative AI mode **já lida com variações** (`oi tudo bem` ainda dispara o topic `oi`). 5 trigger phrases canônicas é o ponto ótimo: cobre variantes formais/informais, mantém manutenção baixa. Adicione mais só quando você confirmar miss em telemetria real, não preventivamente.

> **Nota pedagógica — `Send a message` literal vs Generative response:** notou que a saudação é **string fixa**? Esse topic é **determinístico**. Quando o GPT-4o decidiria parafrasear ("Bom dia! Sou o assistente do HelpSphere..."), aqui a string é cravada. **Por quê:** saudação é touchpoint compliance/branding — você precisa garantir identificação da persona em 100% dos casos, não 95%. Para topics conversacionais (`Resolver_ticket` no próximo Passo), aí sim deixa GPT-4o improvisar.

---

## Passo 3.5 — Criar Topic description-based `Resolver_ticket` (com placeholder de Action)

Esse é o topic principal — ele é disparado pela Generative AI quando detecta que o usuário descreveu um problema/ticket, e em algum momento vai chamar uma **Action** (custom connector que invoca o Foundry Agent do Capítulo 04). Como o Foundry Agent ainda não existe, deixamos o node **Call an action** como placeholder e voltamos no Capítulo 08.

**No Copilot Studio Maker — agente aberto no canvas:**

1. Menu lateral esquerdo → **Topics** → **+ New topic** → **Create from blank**
2. Preencher cabeçalho:
   - **Topic name:** `Resolver_ticket`
   - **Trigger:** mude para `Description-based` (Generative AI decide quando entrar)
   - **Description for AI** (texto crítico — é o que o orchestrator lê para decidir):
     ```text
     Use este topic quando o usuário descreve um problema operacional, faz pergunta sobre um ticket específico do HelpSphere, pede sugestão de resposta para um lojista/colaborador, ou menciona ID numérico de ticket. Não use para saudação ou para perguntas sobre o próprio agent.
     ```
3. No canvas do topic, adicionar nodes em sequência:
   - **+ Add node** após Trigger → **Ask a question**
     - **Message:** `Pode me descrever o problema do ticket que você precisa de ajuda? Inclua ID se souber.`
     - **Identify:** `User's entire response` (captura tudo que o usuário falar)
     - **Save response as:** variável de saída `userQuery` (tipo `Text`)
   - **+ Add node** abaixo do **Ask a question** → **Call an action** → **Create new action** → escolha **Skill** ou **Custom connector** → **placeholder por enquanto**:
     - **Action name:** `CallFoundryAgent` (placeholder — vamos vincular ao Foundry Agent no Capítulo 08, Passo de integração final)
     - **Status:** anote no comentário do node `TODO: vincular após Capítulo 04 + 08`
   - **+ Add node** abaixo → **Send a message** → texto: `Aguarde um momento enquanto consulto a base de conhecimento...` (placeholder de UX — fica até a Action retornar)
4. **Save** (header) — banner amarelo "Action not yet configured" é **esperado** (vamos resolver no Capítulo 08)

<!-- screenshot: cap03-passo3.5-topic-resolver-ticket-placeholder.png -->

> **Custo:** topic em si **R$ 0,00**. Quando rodar no Test panel sem Action vinculada, vai responder o `Send a message` placeholder (sem cobrança Foundry).

> **Nota pedagógica — Description-based topic depende **muito** do texto da Description:** o orchestrator GPT-4o lê literalmente o campo **Description for AI** e decide se a intenção do usuário bate. Frases vagas ("Use para tickets") → orchestrator dispara topic em casos errados. Frases hipertrofiadas ("Use sempre que...") → orchestrator nunca dispara. **Pattern:** descrição em 1-3 frases, com **inclui** (cenários positivos) + **não use para** (cenários negativos). Itere medindo telemetria real (Analytics → Topic insights) — quase sempre você vai ajustar a description após primeiras 50 conversas reais.

> **Nota pedagógica — placeholder Call an action é um reconhecimento honesto da arquitetura:** este lab tem dependência circular pedagógica — o agent Foundry (Cap 04) usa ferramentas que ainda não existem (MCP do Cap 05, Service Bus do Cap 08), e o Copilot Studio agent (este Cap 03) usa o Foundry Agent que ainda não existe. **Solução:** cada componente cria placeholders/stubs e o último capítulo (Cap 08) faz wiring final. Isso espelha desenvolvimento real de sistemas integrados — você nunca tem todas as peças simultaneamente. **Anti-pattern:** tentar criar Cap 03 + Cap 04 + Cap 05 + Cap 08 todos juntos "para evitar placeholder" — perde a ordem didática e o aluno se afoga em side-quests.

---

## Passo 3.6 — Provisionar canal Microsoft Teams via "Test in Teams"

> ⚠️ **Este passo depende dos Capítulos 04 (Foundry Agent) + 08 (Service Bus + integração final) em produção real.** Para o lab você pode rodar agora **apenas o Test in Teams** (sem distribuição org-wide) — assim consegue testar a saudação `Saudacao_inicial` de imediato. A vinculação real do Action `CallFoundryAgent` no topic `Resolver_ticket` acontece no Capítulo 08.

**No Copilot Studio Maker — agente aberto no canvas:**

1. Menu lateral esquerdo → **Channels**
2. Card **Microsoft Teams** → clique → painel direito mostra **+ Add channel**
3. Clique **+ Add channel** → o Studio gera um App package interno (~10-20s)
4. Após sucesso, aparece botão **Open in Teams** (que abre o Teams web/desktop com o agent já adicionado como bot pessoal) — clique
5. No Teams, o bot aparece em chat 1:1 com nome `HelpSphere Tier 1 Agent`. Mande a primeira mensagem:
   - `bom dia` → deve responder com a saudação determinística do Passo 3.4
   - `tenho um problema com integração SAP no ticket 8451` → orchestrator deve disparar `Resolver_ticket` (Passo 3.5) e responder com o placeholder `Aguarde um momento enquanto consulto a base de conhecimento...` (a Action ainda não está vinculada — esperado)

<!-- screenshot: cap03-passo3.6-test-in-teams-bot-chat.png -->

> **Atenção licença Teams:** o caminho **Test in Teams** instala o bot **apenas para sua conta** (não exige Tenant Admin). A opção `Open in Teams admin` (instala para a organização inteira) **exige** role `Microsoft 365 Tenant Admin` — em tenant corporate isso bloqueia, em tenant developer M365 (do Capítulo 01) você é o admin e funciona. **No lab, sempre use Test in Teams** — nunca faça install org-wide com agent não-finalizado (vai sujar Teams para todos os usuários).

> **Custo:** distribuição via Test in Teams é **R$ 0,00**. Cada interação real do bot consome tokens (Generative AI mode) ~R$ 0,01-0,03 por conversa. Fica embarcado no Trial.

> **Nota pedagógica — por que provisionar Teams agora se a Action ainda não funciona?** Permite **smoke test imediato** dos topics determinísticos (Saudação) e confirma que canal Teams está plumbed corretamente. Anti-pattern: deixar canal Teams para o último capítulo e descobrir no fim do lab que o tenant tem policy bloqueando bot install. Front-load problemas — falha cedo, falha barato.

---

## Validação end-to-end

Não há `az` CLI para Copilot Studio (Power Platform tem `pac` CLI mas com cobertura parcial). Validação é **visual + funcional via Test panel**:

```text
# 1. Confirmar agent existe + language correto
Copilot Studio Maker → home → lista de agents → HelpSphere Tier 1 Agent visível
- Language: Portuguese (Brazil)
- Owner: você
- Status: Published

# 2. Confirmar 2 topics criados
Agent → menu Topics → lista deve mostrar:
- Saudacao_inicial (System: No, Trigger: Phrases (5))
- Resolver_ticket (System: No, Trigger: Description-based)
- + outros topics System (Conversation Start, End, Fallback) — auto-criados

# 3. Confirmar Generative AI mode
Agent → menu Generative AI → Mode = "Generative (free-flowing)"

# 4. Confirmar canal Teams
Agent → menu Channels → Microsoft Teams → status "Available"

# 5. Smoke test no Test panel (canto direito)
Input: "bom dia"
Expected: saudação literal do Passo 3.4 (sem improviso GPT-4o)

Input: "tenho problema no ticket 8451"
Expected: dispara Resolver_ticket → Ask question → placeholder message (Action ainda não vinculada)

# 6. (Opcional) Inspecionar telemetria — Analytics tab
Agent → menu Analytics → Sessions/Topics
- Sessions: ≥ 1 sessão registrada após smoke tests
- Topics performance: Saudacao_inicial com 1+ trigger, Resolver_ticket com 1+ trigger
```

### KQL útil em Application Insights (se Power Platform CoE habilitado no tenant)

```kusto
// Mensagens recentes do agent HelpSphere Tier 1
customEvents
| where timestamp > ago(1h)
| where name == "BotMessageReceived"
| where customDimensions.botId contains "HelpSphere"
| project timestamp, userMessage = customDimensions.text, topicMatched = customDimensions.matchedTopic
| order by timestamp desc
```

> **Nota:** Application Insights integration de Copilot Studio é **opt-in** via Power Platform CoE. Em tenant dev grátis pode não estar configurado — não falhe o lab por isso. O importante é o smoke test funcional no Test panel + Teams.

---

## Checklist final

```text
[ ] Trial Copilot Studio ativo (30 dias) e environment Development selecionado
[ ] Agent HelpSphere Tier 1 Agent criado com Language Portuguese (Brazil)
[ ] Instructions (system prompt) com 5 regras coladas verbatim
[ ] Generative AI mode = Generative (free-flowing) habilitado
[ ] Topic Saudacao_inicial criado (5 trigger phrases) e testado no Test panel
[ ] Topic Resolver_ticket criado (description-based) com placeholder Action CallFoundryAgent
[ ] Canal Microsoft Teams provisionado via Test in Teams
[ ] Smoke test "bom dia" no Teams retorna saudação determinística
[ ] Smoke test "problema no ticket X" dispara Resolver_ticket e cai no placeholder
```

---

## Surpresas pedagógicas (capturadas em smoke runs)

- ⚠️ **Conta `live.com` rejeitada — só workaround real é tenant developer M365** — erro `Your account doesn't have access to Copilot Studio` ao criar agent. Causa: tenant pessoal Microsoft Account (MSA) não tem licença Power Platform. Workaround único: criar tenant dev em https://developer.microsoft.com/microsoft-365/dev-program (90 dias renováveis, gratuito). **Não tente "ativar Power Platform" na MSA** — não existe esse fluxo. Decisão AMB-2 cravada na disciplina.
- ⚠️ **Default environment compartilha permissões com TODO o tenant** — em tenant corporate, qualquer colega com licença Power Platform pode editar/deletar seu agent acidentalmente se você criar em Default. Sintoma: agent some de um dia pro outro, ninguém assume autoria. Workaround: sempre criar em environment Development isolado (Power Platform Admin Center → New → type Developer). **Anti-pattern:** ignorar warning de environment achando que "depois eu mudo" — não dá pra mover agent entre environments sem export/import manual.
- ⚠️ **Language mudada após criação quebra Topics declarativos** — se você cria agent com Language `English (US)` e depois muda para `Portuguese (Brazil)` em Settings, Topics existentes com `Trigger phrases` em pt-BR (`oi`, `olá`) param de matchar. Causa: orchestrator usa Language para tokenização/stemming de trigger phrases. Workaround: **decida Language no momento da criação** — replanejar é doloroso (deletar/recriar topics). Documentar em runbook do time.
- ⚠️ **Generative AI mode `Classic` em alguns tenants é o default — surpresa silenciosa** — em tenants antigos ou com policy CoE, o agent vem com Mode = `Classic`. Sintoma: topic `Resolver_ticket` description-based **nunca dispara** (Classic não usa Description). Workaround: sempre confirmar Mode = `Generative (free-flowing)` no Passo 3.3 antes de criar topics description-based. Verificar via Settings → Generative AI no header.
- ⚠️ **`Test in Teams` instala bot pessoal, mas notificações ficam mudas até reload** — após Add channel + Open in Teams, o bot aparece no chat mas a primeira mensagem pode não receber resposta. Causa: caching do Teams web/desktop não pegou novo bot ainda. Workaround: feche Teams (Ctrl+Q no desktop) e reabra, ou hard-refresh `Ctrl+Shift+R` no Teams web. Aguarde 60-120s após Add channel.
- ⚠️ **Description-based topic com descrição vaga dispara em casos errados** — ex.: descrição "Use para tickets" faz orchestrator disparar `Resolver_ticket` em qualquer mensagem com a palavra "ticket" (incluindo "tickets de show"). Causa: GPT-4o orchestrator interpreta literalmente. Workaround: descrição em 1-3 frases com **inclui** + **não use para**. Iterar com base em telemetria real (Analytics → Topic insights). **Nunca hardcode topic em produção sem ver primeiras 50 conversas reais.**
- ⚠️ **Trial 30 dias começa no primeiro acesso, não no signup** — se você fez signup há 60 dias mas só agora abriu Copilot Studio, o Trial está rodando há 30 dias e expira **imediatamente**. Causa: política Microsoft de ativação por uso. Workaround: confirmar dias restantes em Power Platform Admin Center → Licenses → Copilot Studio Trial → coluna "Expires". Se < 7 dias, planejar migração de licença ou cleanup antes de continuar lab.
- ⚠️ **Action placeholder gera banner amarelo persistente em Topics** — após criar `CallFoundryAgent` como placeholder no Passo 3.5, o canvas fica com warning "Action not yet configured" amarelo. Isso é **esperado** até Capítulo 08 (wiring final). **Anti-pattern:** alguns alunos deletam o node "para limpar warning" e quebram o flow do topic — depois precisam recriar. Mantenha o placeholder até o Cap 08 fechar.
- ⚠️ **Topic name com hífen ou espaço quebra exportação para Solution** — Power Platform tolera espaço no Maker UI mas falha em export/import (`Resolver Ticket` vira erro `Invalid logical name`). Convenção da disciplina: snake_case ou PascalCase sem hífen (`Saudacao_inicial`, `ResolverTicket`). Workaround: renomear antes de exportar — Maker UI permite rename mas precisa atualizar referências cross-topic manualmente. **Em produção sempre snake_case desde o início.**
- ⚠️ **Trial Copilot Studio + Tenant Dev M365 podem colidir em conta única** — se você usa a mesma conta Microsoft para múltiplos tenants (ex.: corporate `@empresa.com` e dev `@meunome.onmicrosoft.com`), Copilot Studio pode abrir no tenant errado e mostrar "no environments". Causa: cookie de sessão M365 multi-tenant. Workaround: abrir Copilot Studio em **janela anônima/incognito** + login explícito com a conta dev, OU usar perfil de browser separado. Verificar tenant ativo no header (canto superior direito mostra `<conta>@<tenant>`).

---

## Troubleshooting rápido

| Sintoma | Causa provável | Fix |
|---|---|---|
| `Your account doesn't have access to Copilot Studio` | Conta MSA pessoal (`live.com`) | Criar tenant dev M365 em developer.microsoft.com |
| Agent não aparece em Topics → Resolver_ticket nunca dispara | Mode = `Classic` (não Generative) | Settings → Generative AI → mudar para `Generative (free-flowing)` |
| Test panel responde em inglês mesmo com Language pt-BR | Cache do Maker UI pós-mudança de Language | Recarregar página com Ctrl+Shift+R |
| `+ Add channel` em Teams retorna erro `Tenant policy denies bot installation` | Tenant corporate com Bot Framework policy | Trocar para tenant dev M365 OU pedir Tenant Admin ajuste |
| Saudação aparece com texto improvisado em vez do literal | Topic Saudacao_inicial não foi salvo OU Trigger phrases vazias | Topics → Saudacao_inicial → confirmar 5 phrases + Save |
| Topic `Resolver_ticket` dispara em "preciso comprar tickets" | Description vaga | Refinar Description for AI com `não use para` clauses |

---

## Próximo capítulo

[04 — Foundry Agent SDK](./04-foundry-agent-sdk.md)
