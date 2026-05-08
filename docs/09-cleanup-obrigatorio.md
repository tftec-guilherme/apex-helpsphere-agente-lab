# Capítulo 09 — Cleanup Obrigatório

> **Objetivo:** deletar todos os recursos do lab pra evitar custos recorrentes (PostgreSQL ~R$ 60/mês + ACR ~R$ 35/mês).
>
> **Tempo:** 5-10 min
>
> **Status:** `v0.1.0-init` skeleton — conteúdo Portal step-by-step real virá em pass posterior

---

## Outline

1. **Confirmar que terminou o lab**
   - Smoke end-to-end passou
   - Screenshots capturados
   - Notes salvos

2. **Cleanup via CLI (recomendado)**
   ```bash
   az group delete --name rg-lab-final-{aluno} --yes --no-wait
   ```
   - `--no-wait` retorna imediato; deletion roda em background
   - Verificar 30 min depois: `az group show --name rg-lab-final-{aluno}` deve retornar 404

3. **Cleanup via Portal (alternativa)**
   - Resource Groups → `rg-lab-final-{aluno}` → Delete resource group
   - Digitar nome do RG pra confirmar
   - Aguardar conclusão

4. **Cleanup Foundry Project (separado)**
   - AI Foundry portal → Project `proj-lab-final-{aluno}` → Delete project
   - Hub `aifhub-apex-prod` permanece (compartilhado entre alunos)

5. **Cleanup Copilot Studio agent (opcional)**
   - https://copilotstudio.microsoft.com/
   - Agente HelpSphere → Settings → Delete copilot
   - (Trial expira em 30 dias se não deletar)

6. **Validar billing**
   - Cost Management → Cost analysis → filtrar `rg-lab-final-{aluno}`
   - Esperar 24h pra dados aparecerem
   - Confirmar custo total dentro do esperado (R$ 100-180)

---

## Surpresas pedagógicas (TODO)

- [ ] Soft-delete de RG vs hard-delete — quando recuperável
- [ ] Foundry Project deletion não deleta Hub (compartilhado)
- [ ] PostgreSQL Burstable continua faturando até deletion completa

---

## Próximo capítulo

[10 — Troubleshooting](./10-troubleshooting.md)
