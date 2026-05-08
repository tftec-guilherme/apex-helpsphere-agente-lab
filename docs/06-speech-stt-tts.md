# Capítulo 06 — Speech (STT/TTS)

> **Objetivo:** provisionar AI Speech S0, configurar RBAC ao MI, testar STT/TTS via SDK e plugar voice channel no Copilot Studio.
>
> **Tempo:** 30-45 min
>
> **Status:** `v0.1.0-init` skeleton — conteúdo Portal step-by-step real virá em pass posterior

---

## Outline

1. **Provisionar AI Speech S0**
   - Portal Azure → AI Services → Speech → Create
   - Tier: S0 Standard
   - Region: East US 2
   - RG: `rg-lab-final-{aluno}`

2. **RBAC Managed Identity**
   - Speech resource → Access control (IAM) → Add role assignment
   - Role: `Cognitive Services Speech User`
   - Assignee: `mi-lab-final`

3. **Smoke test SDK Python**
   - `pip install azure-cognitiveservices-speech`
   - Snippet TTS: gerar áudio "Olá Diego, como posso ajudar?"
   - Snippet STT: transcrever áudio gravado

4. **Validar pt-BR voices**
   - `pt-BR-FranciscaNeural` (feminina, default Apex)
   - `pt-BR-AntonioNeural` (masculina, alternativa)

5. **Plugar voice channel no Copilot Studio**
   - Copilot Studio → Settings → Voice
   - Connect Speech resource (key + region)
   - Test no Voice playground

---

## Surpresas pedagógicas (TODO)

- [ ] S0 vs F0 (free tier) — limites
- [ ] pt-BR voices catalog (cravar lista atualizada Q2-2026)
- [ ] Latência TTS streaming vs batch

---

## Próximo capítulo

[07 — n8n Escalation](./07-n8n-escalation.md)
