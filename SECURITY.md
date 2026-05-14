# Security Policy

> `version-anchor: Q2-2026`

## Reporting a Vulnerability

This repository is part of an educational project (Pós-Graduação Avançada de Cloud com Azure · Disciplina 06 · Lab Final).

If you find a security vulnerability:

1. **Não abra um issue público** com detalhes do exploit
2. Envie email pra **prof Guilherme Campos** (Coordenador da Disciplina)
3. Inclua: tipo do problema, paths afetados, repro steps, impacto potencial

Espere resposta em até 5 dias úteis.

---

## Scope

- Conteúdo educativo é fictício (Apex Group é uma empresa fictícia — holding varejista BR)
- Snippets/configs Azure + agent code + MCP Server são exemplos pedagógicos — alunos devem ajustar pra produção real
- Templates n8n contêm placeholders (`{{ $env.X }}`) — alunos devem configurar credentials próprios
- Nenhum credential, key ou secret deve ser commitado neste repo

---

## Responsible Use

Lab Azure pode gerar custos reais (~R$ 100-180 por lab completo se cleanup atrasado). Sempre rode o capítulo `docs/09-cleanup-obrigatorio.md` ao terminar a sessão.

Recursos provisionados pelos alunos:
- Resource Group (deletável via 1 click)
- Azure Container Registry Basic (~R$ 35/mês)
- Azure Container Apps Environment (pay-per-use)
- AI Foundry Project + gpt-4.1-mini deployment (pay-per-use)
- AI Speech S0 (pay-per-use)
- PostgreSQL Burstable B1ms (~R$ 60/mês)
- Service Bus Basic (free tier)

---

## Out of scope

- Vulnerabilidades em Foundry Agent SDK upstream — reportar diretamente ao [MSRC](https://msrc.microsoft.com/create-report)
- Vulnerabilidades em Azure Services (Container Apps, Foundry, Speech, Service Bus) — reportar ao Microsoft
- Vulnerabilidades em n8n upstream — reportar ao [n8n security](https://docs.n8n.io/privacy-security/security/)
- Vulnerabilidades em Copilot Studio — reportar ao Microsoft Power Platform team

---

## Versioning

Política de segurança versiona junto com `CHANGELOG.md`. Mudanças significativas (`MAJOR.MINOR`) são anunciadas em `CHANGELOG.md` e no commit message.
