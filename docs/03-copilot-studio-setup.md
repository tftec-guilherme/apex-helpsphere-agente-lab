# Capítulo 03 — Copilot Studio Setup

> **Objetivo:** ativar Copilot Studio Trial, criar agente HelpSphere e topics base, integrar com Teams (opcional).
>
> **Tempo:** 45-60 min
>
> **Status:** `v0.1.0-init` skeleton — conteúdo Portal step-by-step real virá em pass posterior

---

## Outline

1. **Ativar Copilot Studio Trial**
   - https://copilotstudio.microsoft.com/
   - Sign in com conta Microsoft Work or School
   - Trial 30-day
   - Selecionar Environment

2. **Criar agente "HelpSphere"**
   - New copilot
   - Description: "Assistente HelpSphere · classifica tickets em pt-BR + busca conhecimento RAG + escala via Service Bus"
   - Language: Portuguese (Brazil)
   - Solution: Default Solution

3. **Configurar Topics base**
   - Topic 1: `Conversation Start` (saudação + identificação persona)
   - Topic 2: `Classify Ticket` (intent: severity, category)
   - Topic 3: `Knowledge Lookup` (chama Foundry Agent → MCP Server)
   - Topic 4: `Escalate Critical` (chama Foundry Agent → escalate_servicebus tool)
   - Topic 5: `Fallback` (não entendi · transferir pra humano)

4. **Habilitar Generative AI**
   - Settings → Generative AI → On
   - Model: GPT-4o (default Copilot Studio)
   - Knowledge sources: vazios neste capítulo (popularemos via MCP em capítulo 05)

5. **Test no Test panel**
   - Saudação
   - "Tenho um problema com integração SAP" → debug Topic match

6. **Integrar com Teams (opcional)**
   - Channels → Microsoft Teams → Add
   - Test bot via Teams desktop/web

---

## Surpresas pedagógicas (TODO)

- [ ] Copilot Studio Trial vs licença paga — limitations
- [ ] Topics declarativos vs Generative AI orchestration — quando cada
- [ ] Conta `live.com` pessoal NÃO funciona (gotcha catalogado)

---

## Próximo capítulo

[04 — Foundry Agent SDK](./04-foundry-agent-sdk.md)
