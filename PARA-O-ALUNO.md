# PARA-O-ALUNO — apex-helpsphere-agente-lab

<div align="center">

**🎯 Entrypoint pedagógico do Lab Final D06**

[![Status](https://img.shields.io/badge/status-v0.4.2--n8n--first--cap11--opcional-success)](./CHANGELOG.md)
[![Lifecycle](https://img.shields.io/badge/lifecycle-~9h-orange)](#custos-esperados)
[![Cost](https://img.shields.io/badge/custo-R%24%20100--180-yellow)](./README.md#-custos-esperados-lab-completo)
[![Optional Cap](https://img.shields.io/badge/opcional-cap%2011%20Bot%20Services-blue)](./docs/11-bot-services-opcional.md)

📘 [**Guia Portal completo — entry-point único**](./docs/00-Lab_Final_Agente_Workflow_Guia_Portal.md)

</div>

---

> Bem-vindo. Este é o **entrypoint** do Lab Final (agente HelpSphere production-grade) da Disciplina 06. Vai te guiar pelo Portal Azure + AI Foundry portal + Copilot Studio + n8n UI passo-a-passo construindo um agente conversacional que classifica tickets, busca conhecimento (RAG) e escala via Service Bus + n8n + Google Sheets.
>
> `version-anchor: Q2-2026` · `status: v0.4.2-n8n-first-cap11-opcional`

---

## Status atual

Lab production-grade (revisão 2026-05-19). Os **10 capítulos `docs/`** canônicos estão completos, PowerShell-first e alinhados ao Azure real (Foundry Hub `aifhub-apex-prod` em `rg-lab-intermediario`):

- ✅ Pré-requisitos checklist (este arquivo, abaixo)
- ✅ Quick Start em 7 passos ([README.md](./README.md#quick-start))
- ✅ Surpresas pedagógicas distribuídas inline nos capítulos `docs/` + consolidadas em `docs/_disclaimers.md`
- ✅ Custo estimado: R$ 100-180/lab único ([README.md](./README.md#custos-esperados-lab-completo))
- ✅ Tempo realista: ~9h ponta-a-ponta (lifecycle estimado provision + setup + smoke)

**+1 capítulo opcional:** [`docs/11-bot-services-opcional.md`](./docs/11-bot-services-opcional.md) — Azure Bot Service como alternativa ao Copilot Studio (Cap 03) para canais multi-platform (WhatsApp / SMS / Slack / Direct Line). ~45min se executado. **Não exigido para concluir o Lab Final.**

### Extensões futuras (fora do escopo deste lab)

Tópicos típicos de "IA no Azure 2026" que **NÃO** entram neste Lab Final, deixados como leitura/exploração independente para o aluno curioso:

- **Azure ML / Prompt Flow** — ML lifecycle (registered models, pipelines, endpoints). Foundry cobre parte da experiência, mas Prompt Flow é a ferramenta canônica para eval estruturado offline.
- **Semantic Kernel** — concorrente Microsoft-first do LangChain. Natural para planning + memory em agentes complexos; este lab usa Foundry SDK direto.
- **AutoGen / Multi-agent orchestration** — Microsoft Research framework para múltiplos agentes colaborando.
- **Custom Document Intelligence** — modelos custom treinados em dataset próprio (este lab usa apenas `prebuilt-layout`).
- **Anomaly Detector** — caso de uso natural em ITSM: anomalia em volume de tickets por categoria ou tenant.

Esses tópicos podem ser cobertos em disciplinas separadas ou aprofundados por conta própria após concluir os caps 01-10 + (opcional) cap 11.

Roadmap futuro: screenshots Q2-2026 capturados em execução real e smoke test fim-a-fim documentado.

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

## Como começar — roteiro de execução

Depois de validar os 9 pré-requisitos acima, **siga os capítulos `docs/` em ordem numérica**. Cada cap encerra com um ✅ Checkpoint — só passe ao próximo quando todos os itens estiverem marcados.

| Cap | Tempo | Objetivo macro | Recursos Azure provisionados |
|---|---|---|---|
| [00 — Guia Portal completo](./docs/00-Lab_Final_Agente_Workflow_Guia_Portal.md) | (índice) | Visão única do lab + estimativas + diagrama Mermaid | — |
| [01 — Pré-requisitos](./docs/01-pre-requisitos.md) | ~30min | Validar tudo da lista acima (checklist executável) | nenhum (só validações) |
| [02 — RG + ACR + ACA Env](./docs/02-resource-group-acr-aca.md) | ~45min | Fundação: Resource Group + Container Registry + Container Apps Environment | RG `rg-lab-final` + ACR Basic + ACA Env |
| [03 — Copilot Studio setup](./docs/03-copilot-studio-setup.md) | ~1h | Criar agente conversacional low-code no Power Platform | Copilot Studio Development environment |
| [04 — Foundry Agent SDK](./docs/04-foundry-agent-sdk.md) | ~1.5h | Code-first agent Python com 4 tools (RAG + MCP + tickets + escalation) | Foundry agent + AGENT_ID |
| [05 — MCP Server deploy](./docs/05-mcp-server-deploy.md) | ~1.5h | Build Docker + deploy ACA + Entra two-app + tools `get_ticket`/`list_similar`/etc | ACA Container App `ca-mcp-helpsphere` + 2 App Registrations |
| [06 — Speech STT/TTS](./docs/06-speech-stt-tts.md) | ~45min | Voz pt-BR via Azure AI Speech (transcrição + síntese) | Cognitive Service `spch-helpsphere` |
| [07 — n8n escalation](./docs/07-n8n-escalation.md) | ~1.5h | n8n self-hosted em ACA + workflow 7 nodes (Service Bus trigger → Teams + Sheets) | PostgreSQL B1ms + ACA Container App `ca-n8n-helpsphere` |
| [08 — Service Bus + Sheets](./docs/08-service-bus-google-sheets.md) | ~1h | Service Bus Standard com Topic + 2 Subscriptions (fan-out n8n + Sheets) + Google Sheets connector | Service Bus Standard `sb-helpsphere-final` + Google Sheet |
| [09 — Cleanup obrigatório](./docs/09-cleanup-obrigatorio.md) | ~15min | **CRÍTICO** — deletar tudo do `rg-lab-final` antes de fechar o lab (PostgreSQL B1ms cobra R$ ~60/mês parado) | nenhum (deleção) |
| [10 — Troubleshooting](./docs/10-troubleshooting.md) | consulta | Cheat sheet com 75+ surpresas catalogadas + decision tree + comandos diagnósticos | — |
| [11 — Bot Services (OPCIONAL)](./docs/11-bot-services-opcional.md) | ~45min | Alternativa multi-canal ao Copilot Studio (WhatsApp/SMS/Slack/Direct Line) | Azure Bot `bot-helpsphere-final` Free F0 |

**Ordem de execução cravada** (não pule capítulos — dependências existem):

```
01 → 02 → 03 → 04 → 05 → 06 → 07 → 08 → smoke E2E → 09 (cleanup)
                                            └─ opcional → 11
```

> **Dica:** cap 10 é cheat sheet sob demanda — não precisa ler do início ao fim. Use Ctrl+F com a mensagem exata do erro quando algo travar.

> **Atalho de tempo:** se você concluiu Lab Intermediário (`apex-rag-lab`) no mesmo dia, capítulos 01-02 ficam mais rápidos (~30min em vez de 1h15min) porque parte da fundação Entra/CLI já está validada.

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

Sua missão neste Lab Final (Bloco 4-5): **construir um agente conversacional Foundry** que classifica tickets em pt-BR, consulta o índice RAG via MCP Server, responde com voz (Speech STT/TTS), e escala tickets críticos via Service Bus → n8n → Google Sheets audit + Microsoft Teams (Adaptive Card via Microsoft Graph node). Personas seed: Diego (ops), Marina (financeiro), Lia (atendimento).

> **Sem os 2 stacks acima rodando, este lab quebra nos capítulos 04 e 05.** Não pule a fundação — ela existe por design.

---

## Suporte

- **Issues:** https://github.com/tftec-guilherme/apex-helpsphere-agente-lab/issues
- **Discussions:** abrir issue com label `discussion` se quiser tirar dúvida geral
- **Prof Guilherme Campos** (Coordenador da Disciplina)
