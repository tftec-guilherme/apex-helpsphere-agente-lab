# Capítulo 01 — Pré-requisitos

> **Objetivo:** validar todos os pré-requisitos antes de iniciar o lab.
>
> **Tempo:** 30-45 min (apenas verificação · provisão Foundry Hub se ainda não foi feita pode levar +1h)
>
> **Status:** `v0.1.0-init` skeleton — conteúdo Portal step-by-step real virá em pass posterior

---

## Outline

1. **Azure subscription Pay-As-You-Go**
   - Confirmar role Owner ou Contributor + UAA
   - Validar quota Azure OpenAI (criar request se primeira vez)
   - Comando: `az account show` + `az role assignment list --assignee {seu_email}`

2. **Foundry Hub `aifhub-apex-prod` provisionado**
   - Verificar existência em `rg-helpsphere-ia` East US 2
   - Confirmar deployment `gpt-4.1-mini` ativo
   - Caminho: AI Foundry portal → Hubs → `aifhub-apex-prod`

3. **Conta Microsoft Power Platform**
   - Acessar https://copilotstudio.microsoft.com/
   - Ativar 30-day Trial
   - Validar tenant tem licenças Power Platform

4. **GitHub fork**
   - Forkar `tftec-guilherme/apex-helpsphere-agente-lab`
   - Clone local

5. **Docker Desktop**
   - Versão 4.30+
   - WSL 2 backend habilitado
   - `docker version` retorna sem erro

6. **Azure CLI 2.60+**
   - `az --version`
   - Extensions: `az extension add --name containerapp` + `az extension add --name ml`
   - `az login` autenticado na sub correta

7. **Stack dev local**
   - Python 3.11+ (`python --version`)
   - Node 18+ (`node --version`)
   - Functions Core Tools 4.x (opcional)
   - Git
   - VSCode + extensions Bicep/Python/Docker/REST Client

---

## Surpresas pedagógicas (TODO)

- [ ] Catalogar gotchas reais do smoke run
- [ ] Validar quota Azure OpenAI flow (screenshot rejeição inicial + aprovação)
- [ ] Documentar Copilot Studio Trial na conta Microsoft pessoal vs Work or School

---

## Próximo capítulo

[02 — Resource Group + ACR + ACA Environment](./02-resource-group-acr-aca.md)
