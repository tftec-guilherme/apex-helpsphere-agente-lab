# Changelog — apex-helpsphere-agente-lab

All notable changes to this project are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

> **Note:** Architectural decisions emergem ao longo do build. Pedagogical surprises são catalogadas em [`PARA-O-ALUNO.md`](./PARA-O-ALUNO.md).

---

## [v0.1.0-init] — 2026-05-07

### Bootstrap

Skeleton inicial criado conforme **Story 06.11 Bloco B** do Epic Pendências v5 D06 (Wave 4 — Lab Final ganha repo público novo + Portal refactor + n8n templates, autorizado pelo prof 2026-05-07).

Espelho Portal-first do guia oficial em `azure-retail/Disciplina_06_*/01_Aulas/Lab_Final_*_Guia_Portal.md`. Conteúdo step-by-step detalhado virá em pass posterior quando @ux-design-expert refatorar o Lab Final guide (Story 06.11 Bloco A).

### Added

- **`README.md`** — production-grade mirror do padrão `apex-rag-lab`, descreve objetivo pedagógico, stack (Foundry Agent SDK + MCP Server + Speech + n8n), arquitetura high-level, custos esperados (R$ 100-180), pré-requisitos, política de revisão anual
- **`PARA-O-ALUNO.md`** — entrypoint pedagógico com tom enterprise, 7 pré-requisitos detalhados (Azure PAYG, Foundry Hub, Copilot Studio Trial, GitHub, Docker, Azure CLI, stack dev), filosofia Portal-first com alternativa CLI
- **`CHANGELOG.md`** — este arquivo
- **`CONTRIBUTING.md`** — convenções Conventional Commits + PR workflow + branch protection + anti-padrões editoriais
- **`SECURITY.md`** — política de segurança educacional adaptada pra contexto TFTEC
- **`LICENSE`** — MIT
- **`.gitignore`** + **`.gitattributes`**
- **Estrutura `docs/`** — 10 capítulos skeleton (01-pre-requisitos a 10-troubleshooting), apenas headings + outline (~30-50 linhas cada). Conteúdo Portal-step-by-step real virá em pass posterior
- **`agent-code/agent.py`** — Foundry Agent SDK Python minimal (~80 linhas) com 4 tools placeholder (search_kb, classify_intent, estimate_confidence, escalate_servicebus)
- **`agent-code/requirements.txt`** — azure-ai-projects + azure-identity
- **`mcp-server/Dockerfile`** — FROM python:3.11-slim
- **`mcp-server/server.py`** — MCP server skeleton com 1 tool stub `search_helpsphere_kb`
- **`mcp-server/requirements.txt`** — mcp + azure-identity + azure-search-documents
- **`n8n-workflows/escalation-servicebus-sheets.json`** — JSON template (~150 linhas) com 7 nodes (Service Bus Trigger → Function Filter → Switch Severity → Sheets Append + Slack Notify + Email)
- **`n8n-workflows/README.md`** — instruções import + setup credentials + ativar + troubleshooting
- **`snippets/test-agent.http`** — 5 requests REST exemplo

### Configured

- Repo público em `tftec-guilherme/apex-helpsphere-agente-lab`
- License: MIT
- Default branch: `main`
- Description: "Lab Final D06 — Foundry Agent SDK + MCP Server + Speech + n8n escalation (Portal-first companion)"

### Pedagogical impact

- **0% conteúdo step-by-step do lab pronto** — esperado nesta versão (bootstrap)
- Estrutura pronta pra @ux-design-expert popular cada capítulo com Portal screenshots + steps reais (Story 06.11 Bloco A futuro)
- Aluno tem caminho claro pra contribuir issues/PRs quando v1.0.0 sair
- Padrão dual-repo consistente com `apex-rag-lab` (mesmo arquétipo)

### Cross-references

- Story 06.11: `azure-retail/docs/stories/06.11.lab-final-portal-refactor-repo-novo.md`
- Repo template: `apex-rag-lab` (HEAD `e2e48f2`)
- Repo companion: `apex-helpsphere` (SaaS host)

---

`version-anchor: Q2-2026`
