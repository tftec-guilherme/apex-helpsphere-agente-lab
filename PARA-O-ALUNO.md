# PARA-O-ALUNO — apex-helpsphere-agente-lab

> Bem-vindo. Este é o **entrypoint** do Lab Final (agente HelpSphere production-grade) da Disciplina 06. Vai te guiar pelo Portal Azure + AI Foundry portal + Copilot Studio + n8n UI passo-a-passo construindo um agente conversacional que classifica tickets, busca conhecimento (RAG) e escala via Service Bus + n8n + Google Sheets.
>
> `version-anchor: Q2-2026` · `status: v0.3.0-portal-azure-aligned`

---

## Status atual

Lab production-grade pós Wave 4 (2026-05-12). Os **10 capítulos `docs/`** estão completos, PowerShell-first e alinhados ao Azure real (Foundry Hub `aifhub-apex-prod` em `rg-lab-intermediario`):

- ✅ Pré-requisitos checklist (este arquivo, abaixo)
- ✅ Quick Start em 7 passos ([README.md](./README.md#quick-start))
- ✅ Surpresas pedagógicas distribuídas inline nos capítulos `docs/` + consolidadas em `docs/_disclaimers.md`
- ✅ Custo estimado: R$ 100-180/lab único ([README.md](./README.md#custos-esperados-lab-completo))
- ✅ Tempo realista: ~9h ponta-a-ponta (lifecycle estimado provision + setup + smoke)

Roadmap futuro: screenshots Q2-2026 capturados em execução real (Story 06.6 dedicada), smoke test fim-a-fim documentado (Story 06.13 AC10 pattern).

---

## 9 Pré-requisitos (CRÍTICOS antes de começar)

### 1. Stack `apex-helpsphere` SaaS deployado

> **CRÍTICO** — sem isso, `docs/05-mcp-server-deploy.md` Passo 5.4 falha. O MCP Server precisa de `HELPSPHERE_SQL_CONNECTION` apontando para o SQL Database `helpsphere` do stack SaaS.

- Repo: https://github.com/tftec-guilherme/apex-helpsphere
- Deploy: `azd up` em conta PAYG (~9-14min) — segue [README do apex-helpsphere](https://github.com/tftec-guilherme/apex-helpsphere#quick-start-aluno--local-via-vscode)
- RG resultante: `rg-helpsphere-saas` (westus3 default)
- Artefato consumido aqui: connection string do `sql-helpsphere-{rand}` → DB `helpsphere`
- Fallback: SQL Database vazio com schema mínimo (`tickets(id, title, status, category, priority, created_at)`) — ver `docs/05-mcp-server-deploy.md` callout "Fallback se o stack SaaS HelpSphere não está provisionado"

### 2. Stack `apex-rag-lab` (Lab Intermediário) concluído

> **CRÍTICO** — sem isso, `docs/04-foundry-agent-sdk.md` Passo 4.5 (tool `search_kb`) falha. O agente Foundry precisa de `RAG_FUNCTION_URL` apontando para a Function App do Lab Intermediário.

- Repo: https://github.com/tftec-guilherme/apex-rag-lab
- Conclusão: completar Lab Intermediário (~8h) seguindo [`docs/00-guia-completo.md`](https://github.com/tftec-guilherme/apex-rag-lab/blob/main/docs/00-guia-completo.md)
- RG resultante: `rg-lab-intermediario` (eastus2)
- Artefato consumido aqui: endpoint da Function App `func-helpsphere-rag-{rand}` em `rg-lab-intermediario`
- Pré-requisito interno: este Lab Intermediário também depende do `apex-helpsphere` (RAG é "plugado" ao SaaS via Container Apps no Passo 8 do guia)

### 3. Azure subscription Pay-As-You-Go

> Free Trial **NÃO funciona** — Azure OpenAI / Foundry Agent Service exigem PAYG. Converta antes de iniciar.

- Subscription com role **Owner** OU **Contributor + User Access Administrator** no escopo do RG
- Quota Azure OpenAI aprovada (pode levar 24-48h se primeira vez na sub)

### 4. Foundry Hub `aifhub-apex-prod` provisionado

- Provisionado na **Pré-aula 1 D06** em `rg-lab-intermediario` East US 2
- Sem ele, capítulo 04 (`docs/04-foundry-agent-sdk.md`) não roda

### 5. Conta Microsoft Power Platform com Copilot Studio Trial

- Acesse https://copilotstudio.microsoft.com/ → ativar **30-day Trial** com sua conta Microsoft Work or School
- Conta `live.com` pessoal **NÃO funciona** — precisa tenant com licenças Power Platform

### 6. Conta GitHub

- Pra forkar este repo + opcional uso GitHub Codespaces

### 7. Docker Desktop instalado e rodando

- Build do MCP Server image acontece local (capítulo 05)
- Versão recomendada: **4.30+**
- Habilitar WSL 2 backend (Windows)

### 8. Azure CLI 2.60+ instalado

- `az --version` deve retornar 2.60.0 ou superior
- `az login` autenticado na sub Pay-As-You-Go correta
- Extensions: `containerapp` + `ml` (instaladas via `az extension add`)

### 9. Stack dev local

- Python **3.11+** (NÃO 3.14 — wheels podem faltar)
- Node **18+** (n8n compatibility)
- Functions Core Tools **4.x** (opcional — só se for hospedar agent local antes de ACA)
- Git
- Editor (VSCode recomendado com extensions: Bicep, Python, Docker, REST Client)

---

## Filosofia "Portal-first com Alternativa CLI"

Este lab segue a mesma filosofia do `apex-rag-lab`:

- **Caminho principal:** clique-clique no Portal Azure / AI Foundry portal / Copilot Studio Maker
- **Alternativa CLI/script:** apresentada em callouts ao final de cada capítulo, pra alunos avançados ou re-execuções
- **Ground truth técnico:** Bicep harness em `azure-retail/Disciplina_06_*/03_Aplicações/lab-final-bicep/` (quando existir — ainda em backlog)

> **Anti-drift:** se UI Portal/Foundry mudar, atualizamos screenshots. CLI commands têm shelf-life mais longo.

---

## Custos esperados

Veja tabela completa no [README.md](./README.md#custos-esperados-lab-completo).

**Resumo:** R$ 100-180 pra um lab único completo (provisão + smoke + cleanup no mesmo dia).

> **Maior custo recorrente se você esquecer cleanup:** PostgreSQL Burstable B1ms (~R$ 60/mês) + ACR Basic (~R$ 35/mês). Sempre rode `docs/09-cleanup-obrigatorio.md` ao terminar.

---

## Cenário em 3 linhas

A **Apex Group** (holding varejo brasileira fictícia) já tem **2 stacks deployados** que este Lab Final consome (não apenas referencia narrativamente):

1. **[`apex-helpsphere`](https://github.com/tftec-guilherme/apex-helpsphere)** — SaaS HelpSphere em produção (Container Apps + .NET 10 Tickets API + Azure SQL com 50 tickets seed pt-BR). Provisionado no **Bloco 2** desta disciplina. **REQUER deploy completo** antes deste lab — o MCP Server (cap 05) consulta o SQL Database via tools `get_ticket` / `list_similar_tickets`.
2. **[`apex-rag-lab`](https://github.com/tftec-guilherme/apex-rag-lab)** — Pipeline RAG production-grade sobre 8 PDFs corporativos da Apex (Document Intelligence + AI Search Standard S1 vector hybrid + Function App orquestrador). Construído no **Lab Intermediário (Bloco 3)**. **REQUER conclusão** antes deste lab — o agente Foundry (cap 04) consulta a Function App via tool `search_kb`.

Sua missão neste Lab Final (Bloco 4-5): **construir um agente conversacional Foundry** que classifica tickets em pt-BR, consulta o índice RAG via MCP Server, responde com voz (Speech STT/TTS), e escala tickets críticos via Service Bus → n8n → Google Sheets audit + Slack/Email notifications. Personas seed: Diego (ops), Marina (financeiro), Lia (atendimento).

> **Sem os 2 stacks acima rodando, este lab quebra nos capítulos 04 e 05.** Não pule a fundação — ela existe por design.

---

## Suporte

- **Issues:** https://github.com/tftec-guilherme/apex-helpsphere-agente-lab/issues
- **Discussions:** abrir issue com label `discussion` se quiser tirar dúvida geral
- **Prof Guilherme Campos** (Coordenador da Disciplina) — disponível via TFTEC
