# PARA-O-ALUNO — apex-helpsphere-agente-lab

> Bem-vindo. Este é o **entrypoint** do Lab Final (agente HelpSphere production-grade) da Disciplina 06. Vai te guiar pelo Portal Azure + AI Foundry portal + Copilot Studio + n8n UI passo-a-passo construindo um agente conversacional que classifica tickets, busca conhecimento (RAG) e escala via Service Bus + n8n + Google Sheets.
>
> `version-anchor: Q2-2026` · `status: v0.1.0-init`

---

## Status atual

Conteúdo Portal step-by-step real (10 capítulos detalhados + screenshots) **ainda em construção**. Veja [CHANGELOG.md](./CHANGELOG.md) para roadmap.

Quando v1.0.0 sair, este arquivo terá:
- Pré-requisitos checklist (1 minuto)
- Quick Start em 7 passos
- 10+ surpresas pedagógicas catalogadas (gotchas Portal + Foundry portal + Copilot Studio + n8n)
- Custo estimado real (R$ medido no smoke test)
- Tempo realista por capítulo

---

## 7 Pré-requisitos (CRÍTICOS antes de começar)

### 1. Azure subscription Pay-As-You-Go

> Free Trial **NÃO funciona** — Azure OpenAI / Foundry Agent Service exigem PAYG. Converta antes de iniciar.

- Subscription com role **Owner** OU **Contributor + User Access Administrator** no escopo do RG
- Quota Azure OpenAI aprovada (pode levar 24-48h se primeira vez na sub)

### 2. Foundry Hub `aifhub-apex-prod` provisionado

- Provisionado na **Pré-aula 1 D06** em `rg-helpsphere-ia` East US 2
- Sem ele, capítulo 04 (`docs/04-foundry-agent-sdk.md`) não roda

### 3. Conta Microsoft Power Platform com Copilot Studio Trial

- Acesse https://copilotstudio.microsoft.com/ → ativar **30-day Trial** com sua conta Microsoft Work or School
- Conta `live.com` pessoal **NÃO funciona** — precisa tenant com licenças Power Platform

### 4. Conta GitHub

- Pra forkar este repo + opcional uso GitHub Codespaces

### 5. Docker Desktop instalado e rodando

- Build do MCP Server image acontece local (capítulo 05)
- Versão recomendada: **4.30+**
- Habilitar WSL 2 backend (Windows)

### 6. Azure CLI 2.60+ instalado

- `az --version` deve retornar 2.60.0 ou superior
- `az login` autenticado na sub Pay-As-You-Go correta
- Extensions: `containerapp` + `ml` (instaladas via `az extension add`)

### 7. Stack dev local

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

## Cenário em 3 linhas (preview)

A **Apex Group** (holding varejo brasileira fictícia) já tem:
1. **HelpSphere** (SaaS de tickets em produção — `apex-helpsphere`)
2. **Pipeline RAG** sobre 8 PDFs corporativos (`apex-rag-lab`, Lab Intermediário)

Sua missão neste Lab Final: **construir um agente conversacional Foundry** que classifica tickets em pt-BR, consulta o índice RAG via MCP Server, responde com voz (Speech STT/TTS), e escala tickets críticos via Service Bus → n8n → Google Sheets audit + Slack/Email notifications. Personas seed: Diego (ops), Marina (financeiro), Lia (atendimento).

---

## Suporte

- **Issues:** https://github.com/tftec-guilherme/apex-helpsphere-agente-lab/issues
- **Discussions:** abrir issue com label `discussion` se quiser tirar dúvida geral
- **Prof Guilherme Campos** (Coordenador da Disciplina) — disponível via TFTEC
