# Capítulo 02 — Resource Group + ACR + ACA Environment

> **Objetivo:** provisionar fundação de infra (RG + Azure Container Registry + Azure Container Apps Environment + RBAC base).
>
> **Tempo:** 30-40 min
>
> **Status:** `v0.1.0-init` skeleton — conteúdo Portal step-by-step real virá em pass posterior

---

## Outline

1. **Criar Resource Group `rg-lab-final-{aluno}`**
   - Portal Azure → Resource Groups → Create
   - Region: East US 2 (alinhado com Foundry Hub)
   - Tags: `course=D06`, `lab=final`, `student={aluno}`

2. **Provisionar Azure Container Registry (ACR)**
   - Tier: Basic (~R$ 35/mês)
   - Admin user: disabled (usaremos Managed Identity)
   - Public network access: enabled (lab simplificado)

3. **Provisionar Azure Container Apps Environment**
   - Workload profile: Consumption
   - Log Analytics workspace: novo (`law-lab-final`)
   - Vnet: default (lab simplificado)

4. **Criar User-Assigned Managed Identity**
   - Nome: `mi-lab-final`
   - Será usada pelo MCP Server pra autenticar em Service Bus + AI Search + Storage

5. **Atribuir roles ao MI**
   - `AcrPull` no ACR (pull image)
   - `Azure Service Bus Data Sender` no Service Bus (capítulo 08)
   - `Search Index Data Reader` no AI Search do `apex-rag-lab` (capítulo 05)
   - `Cognitive Services User` no AI Speech (capítulo 06)

---

## Surpresas pedagógicas (TODO)

- [ ] ACR Basic vs Standard — quando justifica upgrade
- [ ] Workload profile Consumption vs Dedicated — pricing impact
- [ ] MI vs Service Principal — pq sempre MI no Azure

---

## Alternativa CLI

```bash
# Placeholder — comandos completos virão na v1.0.0
az group create --name rg-lab-final-{aluno} --location eastus2
az acr create --resource-group rg-lab-final-{aluno} --name acrlabfinal{aluno} --sku Basic
az containerapp env create --name aca-env-lab-final --resource-group rg-lab-final-{aluno} --location eastus2
```

---

## Próximo capítulo

[03 — Copilot Studio Setup](./03-copilot-studio-setup.md)
