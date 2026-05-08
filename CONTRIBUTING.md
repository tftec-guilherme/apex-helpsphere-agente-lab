# Contributing — apex-helpsphere-agente-lab

> Convenções de contribuição pro Lab Final D06.
>
> `version-anchor: Q2-2026`

---

## Convenção de commits (Conventional Commits)

Conventional Commits + referência a Stories quando aplicável:

| Prefixo | Quando usar |
|---|---|
| `feat:` | Nova funcionalidade (capítulo novo, snippet novo, screenshot novo, n8n node novo) |
| `fix:` | Correção de bug (typo, link quebrado, snippet inválido, JSON malformado) |
| `docs:` | Apenas docs (README, PARA-O-ALUNO, CHANGELOG, capítulos `docs/`) |
| `chore:` | Manutenção (deps, configs, CI) |
| `refactor:` | Reorganizar sem alterar conteúdo (mover arquivo, renomear) |
| `test:` | Adicionar/ajustar smoke tests |

### Exemplos

```
feat(docs): adicionar capítulo 04 (Foundry Agent SDK)
fix(snippets): corrigir test-agent.http — header Authorization Bearer
docs(readme): atualizar custos esperados Q3-2026
chore(ci): adicionar workflow lint-docs.yml
test(agent): smoke validate agent.py imports
```

### Body do commit (opcional mas recomendado pra mudanças não-triviais)

```
feat(docs): adicionar capítulo 05 (MCP Server deploy)

- Build local Docker image
- Push pra ACR
- Deploy ACA com 2 App Regs (server + client)
- Smoke test via Portal

Refs: Story 06.11 Bloco A.5
```

Naming convention adicional:
- Convenção `apex-rag-lab` cravada em [CONTRIBUTING.md upstream](https://github.com/tftec-guilherme/apex-rag-lab/blob/main/CONTRIBUTING.md) — mesmo padrão aplicado aqui
- Branch: `feature/{escopo-curto}` (ex: `feature/cap-05-mcp-server`, `fix/n8n-template`)

---

## PR workflow

1. **Forka** o repo: `tftec-guilherme/apex-helpsphere-agente-lab` → `SEU_USUARIO/apex-helpsphere-agente-lab`
2. **Branch**: `feature/{escopo}` (ex: `feature/cap-05-mcp-server`, `fix/agent-imports`)
3. **Commit** + push pra seu fork
4. **Abrir PR** pra `main` deste repo com:
   - Título seguindo Conventional Commits
   - Descrição com:
     - O que mudou (resumo 2-3 linhas)
     - Referência a Stories/CHANGELOG quando aplicável
     - Screenshots se mudou conteúdo visual
     - Custo estimado se mudou steps de provisão
5. **Aguardar review** (mínimo 1 reviewer + status checks verdes)
6. **Squash and merge** preferido pra histórico linear

---

## Branch protection

`main` é protegida:
- Required PR review (mínimo 1)
- Required status checks: `lint-docs`, `agent-smoke`, `mcp-build` (quando workflows existirem em v1.1.0)
- No direct push to main
- No force push to main

---

## Anti-padrões editoriais (pra contribuições de conteúdo)

Evite:
- "É importante destacar que…"
- "No mundo dinâmico do varejo de hoje…"
- "Em última análise…"
- Listas com 3+ bullets dizendo a mesma coisa
- Marcas reais (Magalu, Americanas, Casas Bahia) — use sempre marcas Apex fictícias
- Datas absolutas que envelhecem ("em janeiro de 2026...") — use `Q2-2026` ou "trimestre vigente"
- Nomes de pessoas reais — use sempre personas v5 (Diego, Marina, Lia, Bruno, Carla)
- Screenshots com dados pessoais ou IDs sensíveis (mask antes de commitar)

---

## Suporte

- **Issues:** https://github.com/tftec-guilherme/apex-helpsphere-agente-lab/issues
- **Discussions:** abrir issue com label `discussion` se quiser tirar dúvida geral
- **Prof Guilherme Campos** — disponível via TFTEC
