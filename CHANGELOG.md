# Changelog — apex-helpsphere-agente-lab

All notable changes to this project are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

> **Note:** Architectural decisions emergem ao longo do build. Pedagogical surprises são catalogadas em [`PARA-O-ALUNO.md`](./PARA-O-ALUNO.md).

---

## [v0.4.0-code-files-physical] — 2026-05-17

### Added

**Código de aplicação em pastas físicas espelhando pattern `apex-helpsphere/app/`.**

Antes desta release, ~315L de código Python das Partes 3 e 4 ficavam apenas inline no guia Portal canônico; o repo continha skeletons stub (`agent-code/agent.py` 216L + `mcp-server/server.py` 78L). Aluno copiava 315L do guia, com risco de typos/indentação, e a manutenção exigia editar 2 fontes.

Agora o aluno clona o repo e encontra as pastinhas com código 90% pronto + TODOs estratégicos para customizar.

- **`agent-code/create_agent.py`** (novo, ~125L) — registra `helpsphere-tier1-agent` no Foundry com 4 tools + system prompt. TODO marcado no `SYSTEM_PROMPT` (custom tom/regras)
- **`agent-code/agent_runner.py`** (novo, ~150L) — handlers das 4 tools + event loop `run_agent()`. TODO marcado no `ESCALATION_THRESHOLD` (default `0.5`)
- **`agent-code/func-agent-runner/`** (nova pasta) — wrapper Function App HTTP para Copilot Studio: `function_app.py` + `host.json` + `requirements.txt`
- **`agent-code/README.md`** (novo) — instruções run local + deploy Function App + troubleshooting
- **`mcp-server/auth.py`** (novo, ~55L) — validação JWT Entra + decorator `@require_scope`
- **`mcp-server/helpsphere_db.py`** (novo, ~90L) — wrapper SQL HelpSphere (4 ops: get/list/add_comment/update_status)
- **`mcp-server/README.md`** (novo) — build + deploy ACA + troubleshooting

### Changed

- **`agent-code/requirements.txt`** — sync com o que `create_agent.py`/`agent_runner.py` usam: `azure-ai-projects==1.0.0b9`, `azure-identity`, `azure-servicebus`, `openai>=1.40.0`, `requests`
- **`mcp-server/server.py`** — expandido de skeleton stub (78L) para FastMCP completo com 4 tools `@require_scope` + 1 resource `helpsphere://tickets/{ticket_id}`. TODO marcado em `ticket_resource()` (custom formatação)
- **`mcp-server/requirements.txt`** — substituído por deps reais: `fastmcp`, `pyodbc`, `pyjwt[crypto]`, `requests`, `azure-identity`

### Removed

- **`agent-code/agent.py`** (skeleton legacy v0.1.0-init 216L) — substituído por `agent_runner.py` (handlers reais) + `create_agent.py` (registro)

### Pedagogical impact

- **DRY restaurada:** 1 fonte da verdade (arquivos físicos), guia Portal pode referenciar com "abra `<path>`"
- **3 TODOs estratégicos** preservam ACTIVE learning (90% pronto + 10% customização pedagógica):
  1. `create_agent.py:SYSTEM_PROMPT` — tom/regras do agente
  2. `agent_runner.py:ESCALATION_THRESHOLD` — política de escalação
  3. `mcp-server/server.py:ticket_resource` — formatação do recurso
- **Pattern alinhado** com `apex-helpsphere/app/` (template SaaS base): código pronto em pastas semânticas
- **Deploy continua Portal manual** — Copilot Studio + n8n + ACA via Portal (não vira `azd up`)

### Out of scope nesta release

- Refactor do guia Portal canônico substituindo blocos longos por callouts "abra `<path>`" + trechos curtos — entrega futura
- Tests automatizados / observability / telemetry
- Replicação do pattern em `apex-helpsphere-prod-lab` (Lab Avançado)

---

## [v0.3.0] — 2026-05-14

### Changed

**Sync de README + PARA-O-ALUNO com estado pós Wave 4** (Story 06.22).

Após Wave 4 polish dirigido (commit `f46abec` em 2026-05-12) ter levado os 10 capítulos `docs/` ao estado production-grade, o `README.md` e o `PARA-O-ALUNO.md` continuavam congelados em `v0.1.0-init` (2026-05-07) — situação detectada por audit `@aiox-master` em 2026-05-14 via `gh api`. Esta release resolve essa falsa promessa de "skeleton em construção" e cataloga as 2 dependências cross-repo críticas que `docs/04-05` declaravam mas o entrypoint silenciava.

- **`README.md`** — bump status `v0.1.0-init` → `v0.3.0-portal-azure-aligned`; remoção da frase "Conteúdo Portal step-by-step real virá em pass posterior" (F-001, F-002)
- **`README.md` Pré-requisitos críticos** — adicionados 2 bullets CRÍTICOS no topo: stack `apex-helpsphere` SaaS em `rg-helpsphere-saas` (consumido por tools `get_ticket`/`list_similar_tickets` do MCP Server cap 05) + stack `apex-rag-lab` em `rg-lab-intermediario` (consumido por tool `search_kb` do agente Foundry cap 04) (F-005, F-006)
- **`README.md` árvore docs/** — adicionado `_disclaimers.md` na listagem (F-009)
- **`PARA-O-ALUNO.md`** — bump status no header (F-003); reescrita da seção "Status atual" refletindo realidade pós Wave 4 (F-004); pré-requisitos `7 → 9` itens com 2 novos itens CRÍTICOS no topo (Stack SaaS + Stack RAG) (F-007); reescrita do "Cenário em 3 linhas" clarificando que `apex-helpsphere` e `apex-rag-lab` são pré-requisitos operacionais, não narrativos (F-008)

### Verification

- Audit re-run via `gh api` esperado pós-push: 0 ocorrências de "v0.1.0-init" no README/PARA-O-ALUNO; 0 ocorrências de "skeleton em construção"; presença de "rg-helpsphere-saas" e "rg-lab-intermediario" como dependências; `_disclaimers.md` listado na árvore

### Pedagogical impact

- Aluno descobre dependências cross-repo ANTES de quebrar nos caps 04/05 (não mais "no meio do lab")
- Narrativa "Cenário em 3 linhas" deixa explícito que os 2 stacks precedentes precisam estar deployados/concluídos, não apenas referenciados
- README pós Wave 4 reflete realidade do repo: production-grade, não skeleton

### Cross-references

- Story 06.22: `azure-retail/docs/stories/06.22.companion-labs-readme-sync.md`
- Audit fonte: `@aiox-master` via `gh api repos/tftec-guilherme/apex-helpsphere-agente-lab/readme` em 2026-05-14
- Predecessoras técnicas: Story 06.15 (`9635ac1` PowerShell), 06.18 (`1ebb6e0` Azure alignment), 06.21+ Wave 4 (`f46abec` polish)
- Padrão a replicar: CHANGELOG entries v0.2.0 (mesmo formato)

---

## [v0.2.0] — 2026-05-10

### Changed

**Refactor PowerShell-First dos guias do Lab Final** (Story 06.15 — alinhado ao público Windows da Disciplina D06).

Após audit cross-lab `@aiox-master` em 2026-05-10 detectar 12 CRITICAL findings de bash residual que quebravam quando alunos copiavam-colavam em Windows PowerShell 7 (cenário do "show de horror" da aula 2026-05-09 com o Lab Inter), aplicamos o mesmo padrão de refactor consolidado pela Story 06.13 no `apex-rag-lab` (commits `02b22a7`, `a42d349`, `61c5845`, `b72a341`).

- **`docs/01-pre-requisitos.md`** — adicionada nota global "⚙️ Sintaxe de comandos shell" no topo (padrão `apex-rag-lab/docs/00-guia-completo.md:219-223`) + 7 blocos shell convertidos `bash` → `powershell` (line continuations `\` → backtick, fence trocado)
- **`docs/02-resource-group-acr-aca.md`** — F-001 (`RAND=$(openssl rand)` → `$Rand = -join (...) | Get-Random`) + F-012 (`head -5` → `Select-Object -First 5`) + 4 blocos extras convertidos
- **`docs/05-mcp-server-deploy.md`** — F-002/F-003/F-004/F-005 (`curl` → `curl.exe`, pipeline `cut | base64 -d | jq` → `[Convert]::FromBase64String()` + `ConvertFrom-Json`, `-o /dev/null` → `-o $null`) + Passos 5.2/5.3/5.4 ACR build & alternativas CLI convertidos
- **`docs/06-speech-stt-tts.md`** — F-006/F-007/F-008/F-009 (curl multiline com backtick, `--data-binary "@file"` com aspas para evitar splatting, SSML em here-string `@'...'@`, `--output`) + Passos 6.1/6.3 alternativas CLI convertidos
- **`docs/07-n8n-escalation.md`** — F-010 (`openssl rand -base64 32` → `[Convert]::ToBase64String((1..32 | ForEach-Object {...}))`) + Passos 7.1 PostgreSQL CLI, 7.4 RBAC SB, 7.7 stop/resume, validação end-to-end convertidos
- **`docs/10-troubleshooting.md`** — F-011 (mesmo padrão F-004) + diagnóstico §5.1-§5.7 convertidos + **nova seção "PowerShell vs Bash — armadilhas comuns"** com tabela de 12 antipadrões, nota sobre instalação `jq` no Windows (winget/choco) e alternativa `ConvertFrom-Json` nativa

### Verification

- `grep '^\`\`\`bash'` nos 6 arquivos retorna apenas referências documentais propositais (notas Linux/Mac/WSL na seção de armadilhas)
- `grep ' \\$'` (line continuation bash) retorna zero matches
- `grep 'export [A-Z_]+='` retorna apenas referências documentais
- Padrões aplicados consistentes com gold-standard `apex-rag-lab/snippets/test_translator.ps1` + `test_vision_ocr.ps1`

### Pedagogical impact

- **Bloqueante removido** para próxima gravação Bloco 4-5 D06 (Lab Final agente autônomo). Alunos Windows-first copiam-colam sem quebrar.
- Linha de tradução para Linux/Mac/WSL preservada via nota global em `01-pre-requisitos.md` e seção de armadilhas em `10-troubleshooting.md`.
- AC10 da Story 06.15 (smoke test manual PowerShell 7 dos 3 comandos críticos representativos) fica **GATED** para sessão QA separada com aprovação do prof.

### Cross-references

- Story 06.15: `azure-retail/docs/stories/06.15.lab-final-powershell-refactor.md`
- Audit fonte: subagente Explore `a5537f367845a4085` em 2026-05-10 (12 CRITICAL)
- Padrão de fix: Story 06.13 do `apex-rag-lab` (HEAD `61c5845` na época)
- Análoga pendente: Story 06.16 (refactor PowerShell `apex-helpsphere-prod-lab` — 21 findings)

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
- **`SECURITY.md`** — política de segurança educacional
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
