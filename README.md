<div align="center">

# 🎯 apex-helpsphere-agente-lab

**Lab Final D06 — Agente conversacional production-grade com Foundry SDK + MCP + Speech + n8n**

[![Status](https://img.shields.io/badge/status-v0.3.1--guia--portal--consolidado-success)](./CHANGELOG.md)
[![Anchor](https://img.shields.io/badge/version--anchor-Q2--2026-blue)](./docs/00-Lab_Final_Agente_Workflow_Guia_Portal.md)
[![Region](https://img.shields.io/badge/region-East%20US%202-orange)](#)
[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![Disciplina D06](https://img.shields.io/badge/Pós--Graduação-TFTEC%20+%20Anhanguera-purple)](https://github.com/tftec-guilherme/azure-retail)

📘 [**Guia Portal completo (70KB · 1961L · entry-point único)**](./docs/00-Lab_Final_Agente_Workflow_Guia_Portal.md)

</div>

---

> Companion público do **Lab Final D06** da Pós-Graduação Arquitetura Cloud Azure (TFTEC + Anhanguera). Portal-first end-to-end — agente HelpSphere que classifica tickets, busca conhecimento via MCP Server, responde com voz e escala via Service Bus + n8n.

## Contexto

Este repo é o **espelho Portal-first** do Lab Final da Disciplina 06 (IA e Automação no Azure — Pós-Graduação Arquitetura Cloud Azure TFTEC + Anhanguera).

- **Pedagogia:** clique-clique no Portal Azure + AI Foundry portal (`ai.azure.com`) + Copilot Studio Maker portal + n8n UI
- **Stack:** Azure Container Apps + Azure Container Registry + Foundry Agent Service + MCP Server (Docker) + AI Speech + Service Bus + n8n + Google Sheets audit
- **Region:** East US 2 (alinhado Foundry Hub `aifhub-apex-prod`)
- **Tier:** Standard SKUs (production-grade entry)

Companion didático do [`apex-helpsphere`](https://github.com/tftec-guilherme/apex-helpsphere) (SaaS host) e do [`apex-rag-lab`](https://github.com/tftec-guilherme/apex-rag-lab) (Lab Intermediário RAG).

## Estrutura

```
apex-helpsphere-agente-lab/
├── README.md                          # ← você está aqui
├── PARA-O-ALUNO.md                    # entrypoint pedagógico + gotchas + custo real
├── CHANGELOG.md                       # histórico de versões
├── CONTRIBUTING.md                    # convenções de commit + PR workflow
├── SECURITY.md                        # política de segurança educacional
├── LICENSE                            # MIT
├── docs/                              # guia consolidado (entry-point) + 10 capítulos + disclaimers
│   ├── 00-Lab_Final_Agente_Workflow_Guia_Portal.md  # ⭐ GUIA COMPLETO entry-point (70KB · 1961L)
│   ├── 01-pre-requisitos.md
│   ├── 02-resource-group-acr-aca.md
│   ├── 03-copilot-studio-setup.md
│   ├── 04-foundry-agent-sdk.md
│   ├── 05-mcp-server-deploy.md
│   ├── 06-speech-stt-tts.md
│   ├── 07-n8n-escalation.md
│   ├── 08-service-bus-google-sheets.md
│   ├── 09-cleanup-obrigatorio.md
│   ├── 10-troubleshooting.md
│   └── _disclaimers.md                # disclaimers e armadilhas consolidados (AMB-2 fix)
├── agent-code/                        # Foundry Agent SDK Python
│   ├── agent.py
│   └── requirements.txt
├── mcp-server/                        # MCP Server Docker
│   ├── Dockerfile
│   ├── server.py
│   └── requirements.txt
├── n8n-workflows/                     # JSON templates pra escalação
│   ├── escalation-servicebus-sheets.json
│   └── README.md
├── snippets/                          # .http exemplos REST
│   └── test-agent.http
└── images/                            # screenshots Portal Q2-2026 (capturados na execução real)
```

## 🚀 Quick start

```powershell
# 1. Fork em https://github.com/tftec-guilherme/apex-helpsphere-agente-lab → seu fork

# 2. Clone local
git clone https://github.com/SEU_USUARIO/apex-helpsphere-agente-lab.git
Set-Location apex-helpsphere-agente-lab

# 3. Abra o guia consolidado (entry-point único)
code docs/00-Lab_Final_Agente_Workflow_Guia_Portal.md

# 4. OU navegue pelos 10 capítulos detalhados
code docs/01-pre-requisitos.md
```

**Lifecycle estimado:** ~9h ponta-a-ponta (provisioning + setup + smoke + cleanup).

**Linux/Mac/WSL:** troque `Set-Location` por `cd`.

## Pré-requisitos

> [!IMPORTANT]
> **2 stacks cross-repo precisam estar deployados/concluídos ANTES deste lab.** Sem eles, os capítulos 04 e 05 quebram.

### 🔴 Críticos cross-repo (deploy antes)

| Stack | Bloco D06 | RG | Por que? |
|---|---|---|---|
| **[`apex-helpsphere`](https://github.com/tftec-guilherme/apex-helpsphere)** | Bloco 2 SaaS | `rg-helpsphere-saas` | SQL Database `helpsphere` consumido pelo MCP Server (cap 05) via tools `get_ticket` / `list_similar_tickets` |
| **[`apex-rag-lab`](https://github.com/tftec-guilherme/apex-rag-lab)** | Bloco 3 Lab Inter | `rg-lab-intermediario` | RAG Function App `func-helpsphere-rag-{rand}` consultada pela tool `search_kb` do agente Foundry (cap 04) |

### 🟡 Comuns

| Item | Detalhe |
|---|---|
| Azure subscription | **Pay-As-You-Go** obrigatório (Free Trial **não funciona** — Azure OpenAI exige PAYG) |
| Foundry Hub | `aifhub-apex-prod` em `rg-lab-intermediario` East US 2 (Pré-aula 1 D06) |
| Power Platform | Copilot Studio Trial 30d (conta Work or School, **não** `live.com` pessoal) |
| Stack dev local | Docker Desktop 4.30+, Python 3.11+, Node 18+, Azure CLI 2.60+, Functions Core Tools 4.x |

> Detalhes completos em [`docs/01-pre-requisitos.md`](./docs/01-pre-requisitos.md).

## 💰 Custos esperados (lab completo)

| Recurso | Tier | Custo estimado |
|---|---|---|
| Azure Container Registry | Basic | ~R$ 35/mês |
| Azure Container Apps Environment | Pay-per-use | ~R$ 50-80/lab |
| AI Speech | S0 pay-per-use | ~R$ 5/lab |
| AI Foundry Project + gpt-4.1-mini | Pay-per-use | ~R$ 30-50/lab |
| PostgreSQL Flexible Server | Burstable B1ms | ~R$ 60/mês ou ~R$ 20/lab parcial |
| Service Bus | Basic | Free tier suficiente |
| **Total estimado lab único** | — | **R$ 100-180** |

## 🔗 Família D06

| Repo | Bloco | Estilo | Status |
|---|---|---|---|
| [`apex-helpsphere`](https://github.com/tftec-guilherme/apex-helpsphere) | Bloco 2 — SaaS base | Production-grade `azd up` | v2.x |
| [`apex-rag-lab`](https://github.com/tftec-guilherme/apex-rag-lab) | Bloco 3 — Lab Inter RAG | Portal-first + fork funcional | v1.x |
| **`apex-helpsphere-agente-lab`** (você está aqui) | Bloco 4-5 — Lab Final agente | Portal-first companion | v0.3.1 |
| [`apex-helpsphere-prod-lab`](https://github.com/tftec-guilherme/apex-helpsphere-prod-lab) | Bloco 6 — Lab Avançado production | Bicep + CLI manual | v0.3.1 |

## 🧹 Cleanup obrigatório

[`docs/09-cleanup-obrigatorio.md`](./docs/09-cleanup-obrigatorio.md) crava obrigatoriedade `az group delete --name rg-lab-final --yes --no-wait` ao final.

## Arquitetura (high-level)

```
┌──────────────────────────────────────────────────────────────────┐
│  Azure Subscription (aluno) — East US 2                           │
│                                                                    │
│  Resource Group: rg-lab-final-{aluno}                             │
│                                                                    │
│  ┌──────────────────┐         ┌──────────────────────────┐        │
│  │  Copilot Studio  │────────▶│  Foundry Agent Service   │        │
│  │  (Trial · Maker) │         │  (gpt-4.1-mini)          │        │
│  └──────────────────┘         └─────────┬────────────────┘        │
│         │                                │                         │
│         │  Speech (STT/TTS)              │ tools                   │
│         ▼                                ▼                         │
│  ┌──────────────────┐         ┌──────────────────────────┐        │
│  │  AI Speech S0    │         │  MCP Server (ACA)        │        │
│  └──────────────────┘         │  - search_kb             │        │
│                                │  - classify_intent       │        │
│                                │  - estimate_confidence   │        │
│                                │  - escalate_servicebus   │        │
│                                └─────────┬────────────────┘        │
│                                           │                         │
│                                           ▼                         │
│                                ┌──────────────────────────┐        │
│                                │  Service Bus (Basic)     │        │
│                                │  topic: escalations       │       │
│                                └─────────┬────────────────┘        │
│                                           │                         │
│                                           ▼                         │
│                                ┌──────────────────────────┐        │
│                                │  n8n (ACA + PostgreSQL)  │        │
│                                │  workflow: escalation    │        │
│                                └─────────┬────────────────┘        │
│                                           │                         │
│                       ┌───────────────────┼───────────────────┐    │
│                       ▼                   ▼                   ▼    │
│                  Google Sheets         Slack              Email     │
│                  (audit trail)         (notify)          (notify)   │
└──────────────────────────────────────────────────────────────────┘
```

> Diagrama detalhado virá em `docs/01-pre-requisitos.md`.

## Referências

- [`apex-helpsphere`](https://github.com/tftec-guilherme/apex-helpsphere) — SaaS HelpSphere base (tickets seed que o agente resolve)
- [`apex-rag-lab`](https://github.com/tftec-guilherme/apex-rag-lab) — Lab Intermediário (pipeline RAG que alimenta o `search_kb` do MCP Server)
- [`azure-retail`](https://github.com/tftec-guilherme/azure-retail) — monorepo da Pós-Graduação · guia oficial em `Disciplina_06_*/01_Aulas/Lab_Final_*_Guia_Portal.md`
- Microsoft Learn — [Azure AI Foundry Agent Service](https://learn.microsoft.com/azure/ai-foundry/agents/overview)
- Microsoft Learn — [Model Context Protocol (MCP)](https://learn.microsoft.com/azure/developer/ai/intro-agents-mcp)
- Microsoft Learn — [Azure Container Apps](https://learn.microsoft.com/azure/container-apps/overview)
- Microsoft Learn — [AI Speech](https://learn.microsoft.com/azure/ai-services/speech-service/overview)
- [n8n docs](https://docs.n8n.io/)

## Versão

`v0.3.0-portal-azure-aligned` · `version-anchor: Q2-2026`

**Política de revisão anual:**
- Comparar Portal screenshots vs UI atual (capturar novos se >30% mudou)
- Verificar se Foundry Agent Service SDK continua o caminho recomendado (vs Semantic Kernel / outras alternativas)
- Validar pricing AI Foundry + ACA + AI Speech (mudam a cada ~6-12 meses)
- Re-rodar smoke completo em conta limpa

## Licença

MIT — fork e adapte livremente. Veja [LICENSE](./LICENSE).
