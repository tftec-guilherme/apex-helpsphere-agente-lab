# apex-helpsphere-agente-lab

> **Lab Final — Disciplina 06: IA e Automação no Azure (Pós-Graduação Arquitetura Cloud Azure · TFTEC + Anhanguera)**
>
> Companion público do Lab Final D06 — agente HelpSphere com **Foundry Agent SDK + MCP Server + Speech + n8n escalation**. Espelho **Portal-first** do guia oficial em `azure-retail/Disciplina_06_*/01_Aulas/Lab_Final_*_Guia_Portal.md`. `version-anchor: Q2-2026`

> **Status:** `v0.3.0-portal-azure-aligned` — production-grade pós Wave 4 (2026-05-12). 10 capítulos Portal step-by-step completos (PowerShell-first, alinhados ao Azure real), `_disclaimers.md` consolidado, MCP Server + Foundry Agent + n8n escalation cobertos end-to-end. Histórico em [CHANGELOG.md](./CHANGELOG.md).

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
├── docs/                              # 10 capítulos Portal step-by-step + disclaimers consolidados
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

## Quick start

1. Faça **fork** deste repo pra sua conta GitHub
2. Clone localmente: `git clone https://github.com/SEU_USUARIO/apex-helpsphere-agente-lab.git`
3. Siga `docs/01-pre-requisitos.md` → `docs/10-troubleshooting.md`
4. **Lifecycle estimado:** ~9h (mínimo) considerando provisioning + setup + smoke

## Pré-requisitos críticos

- **Stack `apex-helpsphere` deployado** em `rg-helpsphere-saas` (Bloco 2 D06) — fornece SQL Database `helpsphere` com tickets seed que o MCP Server (cap 05) consulta via tools `get_ticket` e `list_similar_tickets`. Veja [`apex-helpsphere`](https://github.com/tftec-guilherme/apex-helpsphere) e provisione com `azd up` antes deste lab.
- **Stack `apex-rag-lab` deployado** em `rg-lab-intermediario` (Lab Intermediário D06) — fornece a RAG Function App `func-helpsphere-rag-{rand}` que o agente Foundry consulta via tool `search_kb` (cap 04). Veja [`apex-rag-lab`](https://github.com/tftec-guilherme/apex-rag-lab) e complete o Lab Intermediário antes.
- Azure subscription **Pay-As-You-Go** (Free Trial **não funciona** — Azure OpenAI exige PAYG)
- Foundry Hub `aifhub-apex-prod` provisionado em `rg-lab-intermediario` East US 2 (Pré-aula 1 D06)
- Conta Microsoft Power Platform com **Copilot Studio Trial** ativado
- Conta GitHub
- Docker Desktop (build MCP Server)
- Azure CLI 2.60+ + Functions Core Tools 4.x + Node 18+ + Python 3.11+

> Detalhes completos em [`docs/01-pre-requisitos.md`](./docs/01-pre-requisitos.md).

## Custos esperados (lab completo)

| Recurso | Tier | Custo estimado |
|---|---|---|
| Azure Container Registry | Basic | ~R$ 35/mês |
| Azure Container Apps Environment | Pay-per-use | ~R$ 50-80/lab |
| AI Speech | S0 pay-per-use | ~R$ 5/lab |
| AI Foundry Project + gpt-4.1-mini | Pay-per-use | ~R$ 30-50/lab |
| PostgreSQL Flexible Server | Burstable B1ms | ~R$ 60/mês ou ~R$ 20/lab parcial |
| Service Bus | Basic | Free tier suficiente |
| **Total estimado lab único** | — | **R$ 100-180** |

## Cleanup

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

`v0.1.0-init` · `version-anchor: Q2-2026`

**Política de revisão anual:**
- Comparar Portal screenshots vs UI atual (capturar novos se >30% mudou)
- Verificar se Foundry Agent Service SDK continua o caminho recomendado (vs Semantic Kernel / outras alternativas)
- Validar pricing AI Foundry + ACA + AI Speech (mudam a cada ~6-12 meses)
- Re-rodar smoke completo em conta limpa

## Licença

MIT — fork e adapte livremente. Veja [LICENSE](./LICENSE).
