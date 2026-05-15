# Capítulo 10 — Troubleshooting

> **Objetivo:** consolidar todas as **gotchas reais** capturadas em smoke runs dos Capítulos 01-09 num único guia de busca rápida — tabela mestre por categoria, decision tree para erros recorrentes, comandos diagnósticos universais e referência cruzada para o capítulo onde a causa-raiz é explicada. Este capítulo **não duplica conteúdo** dos caps 01-09: agrega + cross-ref + arruma por sintoma.
>
> **Tempo:** consulta sob demanda — ~5min para localizar fix · ~20min se quiser ler o capítulo inteiro como cheat sheet pré-recording
>
> **Status:** capítulo agrega ~75+ Surpresas pedagógicas dos 9 capítulos anteriores + Troubleshooting do guia canônico Portal. **Não duplica conteúdo** — cada linha referencia o cap-fonte para detalhe completo.

---

## Como usar este capítulo

1. **Erro com mensagem específica?** Use Ctrl+F com a string exata do erro — quase toda mensagem real está catalogada na **§3 Tabela mestre de Surpresas**.
2. **Sintoma vago ("não funciona")?** Vá para a **§2 Decision tree** e siga o galho conforme o capítulo onde travou.
3. **Quer prevenção em vez de cura?** Leia a **§4 Top 10 issues recorrentes** antes do recording.
4. **Quer comandos diagnósticos universais?** **§5 Toolkit de diagnóstico** — `az resource list`, `az role assignment list`, etc.
5. **Erro não está aqui?** Cap 09 Passo 9.7 cobre billing residual; gaps reportados na **§7 Gaps para follow-up do prof**.

> **Princípio geral:** este lab tem **dependências circulares pedagógicas** (Cap 03 placeholder → Cap 04 → Cap 05 → Cap 08 wiring final). Erros "não funciona" no meio do lab quase sempre são placeholders ainda não fechados, não bugs. Confirme primeiro qual capítulo é dono do recurso antes de mexer.

---

## §1 Pré-requisitos para diagnosticar

- ✅ `az` CLI logado na sub correta (`az account show` confirma)
- ✅ `jq` instalado (parse de outputs JSON é onipresente neste cap)
- ✅ Acesso de leitura aos RGs `rg-lab-final` + `rg-lab-intermediario` (cross-RG)
- ✅ Permissão `Reader` no tenant Entra (para listar App Registrations) — Owner se for fixar

> **Atenção:** se você bateu erro `Insufficient privileges` em algum cap, reler **§3.1 Auth/RBAC** abaixo antes de pedir elevação para o admin do tenant — boa parte das falhas "permissão" é placeholder de propagação RBAC (60s) ou flag `--assignee` errado.

---

## §2 Decision tree — sintomas e galhos

```text
Erro/sintoma reportado
│
├─ "Não consigo logar" / "tenant errado" / "Copilot Studio rejeita" / "AADSTS50020"
│   └─► §3.1 Auth/RBAC + Cap 01 (Pré-req) + Cap 03 (Copilot Studio)
│       Top causa: conta `live.com` rejeitada em copilotstudio.microsoft.com (AADSTS50020) — fallback Entra trial 30d via Cap 03 Passo 3.7
│
├─ "Recurso não cria" / "name not available" / "quota"
│   └─► §3.2 Provisioning + Caps 02/06/07/08
│       Top causa: ACR name globally unique (Cap 02 Surpresa #1)
│
├─ "Container não sobe" / "ImagePullBackOff" / "Provisioning infinito"
│   └─► §3.3 Containers + Caps 02/05/07
│       Top causa: AcrPull RBAC ainda propagando (Cap 05 Surpresa — Passo 5.5)
│
├─ "401/403 ao chamar API" / "audience mismatch" / "token sem roles"
│   └─► §3.4 Auth aplicacional + Caps 05/06/08
│       Top causa: EXPECTED_AUDIENCE != aud do token (Cap 05 Surpresa #3)
│
├─ "Agente não responde" / "tool não dispara" / "loop infinito" / "BadRequest 400 RAG search"
│   └─► §3.5 Foundry Agent + Cap 04
│       Top causa: tool retornou JSON inválido OU tiktoken truncation faltando (Capítulo 04 Surpresas F3/F7)
│
├─ "n8n não vê mensagem" / "PG connection refused" / "owner perdido"
│   └─► §3.6 n8n + PostgreSQL + Cap 07
│       Top causa: PG firewall sem "allow Azure services" (Cap 07 Surpresa #2)
│
├─ "Topic não cria" / "duplicação na escalação" / "Sheets vazio"
│   └─► §3.7 Service Bus + Google Sheets + Cap 08
│       Top causa: SB Basic tentando criar Topic (Cap 08 Surpresa #1)
│
├─ "Áudio não transcreve" / "voice not supported" / "MP3 não toca"
│   └─► §3.8 Speech + Cap 06
│       Top causa: WAV não é PCM 16kHz mono (Cap 06 Surpresa #2)
│
└─ "Custo apareceu pós-cleanup" / "RG não deleta" / "secret órfão" / "Foundry soft-deleted 30d"
    └─► §3.9 Cleanup + custo + Cap 09
        Top causa: Foundry Project não está no `rg-lab-final` (Cap 09 Surpresa #1) + soft-delete 30d Foundry/KV bloqueia recriar nome
```

---

## §3 Tabela mestre de Surpresas (organizada por categoria)

> Cada linha tem **Sintoma observável → Causa raiz → Fix → Cap onde explica em detalhe**. Conteúdo sintético; explicação completa fica no cap-fonte (sem duplicação).

### §3.1 Auth & RBAC (tenant + sub)

| # | Sintoma | Causa | Fix | Cap fonte |
|---|---|---|---|---|
| A1 | `SubscriptionNotRegistered` em Foundry agent create | Free Trial USD 200 não suporta Foundry Agent Service | Converter sub para Pay-As-You-Go no Portal (botão Upgrade) | Cap 01 |
| A2 | `AADSTS50020: User account from identity provider 'live.com' does not exist in tenant` em `copilotstudio.microsoft.com` | Conta MSA pessoal (`live.com`/`outlook.com`/`hotmail.com`) sem licença Power Platform — Copilot Studio exige conta corporativa (work/school) | Fallback: criar tenant dev M365 trial 30d via Cap 03 **Passo 3.7** + reusar `MSAL` patterns; ver [`_disclaimers.md`](./_disclaimers.md) **AMB-2** | Caps 01, 03 |
| A3 | `AuthorizationFailed` em `az role assignment create` | Contributor pelado sem User Access Administrator | Pedir admin tenant para `User Access Administrator` no scope da sub OU `Owner` direto | Caps 01, 02 |
| A4 | `Insufficient privileges` em `az role assignment create --assignee <upn>` | Flag `--assignee` faz lookup Microsoft Graph (exige `Directory.Read.All`) | Trocar por `--assignee-object-id <objectId> --assignee-principal-type ServicePrincipal` (pula lookup) | Cap 05 |
| A5 | Trial Copilot Studio expira **imediatamente** após signup remoto | Trial conta dias desde **primeiro acesso**, não signup | Confirmar dias restantes em Power Platform Admin Center → Licenses | Cap 03 |
| A6 | Default environment sumiu o agent / outro user editou | Default compartilha permissões com TODO o tenant | Sempre criar agent em environment **Development** isolado (não Default) | Cap 03 |
| A7 | Agent Test panel responde em inglês mesmo com Language pt-BR | Cache do Maker UI pós-mudança de Language OU Language mudada após criação | `Ctrl+Shift+R` no browser; se persiste, deletar/recriar topics em pt-BR (não dá pra reverter) | Cap 03 |
| A8 | Multi-tenant: Copilot Studio abre tenant errado / "no environments" | Cookie de sessão M365 multi-tenant escolhe tenant corporate | Janela anônima/incognito + login explícito com conta dev | Cap 03 |

### §3.2 Provisioning de recursos Azure

| # | Sintoma | Causa | Fix | Cap fonte |
|---|---|---|---|---|
| P1 | `Registry name 'acrhelpsphere' is not available` | ACR name é globalmente único (DNS) + sem hífen + lowercase | Adicionar 6 hex chars aleatórios (`openssl rand -hex 3`) ao final → `acrhelpsphere8a3f2d` | Cap 02 |
| P2 | `subscription is not registered to use namespace 'Microsoft.App'` | Resource Provider não habilitado | `az provider register --namespace Microsoft.App && az provider register --namespace Microsoft.OperationalInsights` | Cap 02 |
| P3 | ACA Environment provisiona Log Analytics novo silenciosamente | Tab Monitoring com workspace não selecionado explicitamente | Selecionar `log-helpsphere-ia` no dropdown; se já errou, deletar ACA Env e recriar (não dá trocar workspace) | Cap 05 |
| P4 | ACA Env stuck em `Provisioning` >10min | Quota regional esgotada (raro em East US 2) | Trocar para `eastus` ou `southcentralus` | Cap 05 |
| P5 | Workload profile `Consumption + Dedicated` cobra R$ 250/mês reservados | Default em algumas subs corporate | Selecionar **explicitamente** `Consumption only` no Tab Workload profiles | Cap 05 |
| P3b | Portal não permite criar ACA Environment standalone (Q2-2026) | Blade Container Apps obriga criar Container App junto | 3 opções no Cap 05 Passo 5.4: (A) Marketplace link `https://portal.azure.com/#create/Microsoft.ManagedEnvironment`, (B) `az containerapp env create`, (C) inline durante criação do Container App | Cap 05 |
| P6 | `gpt-4.1-mini` quota request leva 24-72h | Aprovação manual Microsoft em sub nova | Provisionar Hub + deployment `gpt-4.1-mini` em RG separado (`rg-lab-intermediario`) **antes** deste lab (este lab apenas reusa o deployment existente) | Cap 01 |
| P7 | `pg-n8n-<rand>` PostgreSQL Burstable B1ms cobra parado mesmo idle | PG não tem free tier permanente; `Stop` reinicia automaticamente após 7 dias | Para zerar custo: `delete` (não `Stop`) — ver Cap 07 Passo 7.7 / Cap 09 | Caps 07, 09 |
| P8 | Speech voice nova (`pt-BR-ThalitaNeural`) `400 Voice not supported` em eastus2 | Voices novas chegam primeiro em `eastus`/`westus3`/`francecentral` | Validar `learn.microsoft.com/azure/ai-services/speech-service/regions` antes de cravar voice | Cap 06 |
| P9 | Service Bus Topic não cria — botão cinza no Portal | Tier Basic não suporta Topics (só Queues) — ver [`_disclaimers.md`](./_disclaimers.md) **AMB-4** | Sempre Standard (~R$ 50/mês baseline) — não confunda nome "Basic" com "menor" | Cap 08 |

### §3.3 Containers (ACR + ACA + imagens)

| # | Sintoma | Causa | Fix | Cap fonte |
|---|---|---|---|---|
| C1 | `UNAUTHORIZED: authentication required` no pull do ACR | Role `AcrPull` ainda propagando (~30-60s) ou MI errado | Aguardar 60s; `az role assignment list --assignee <principalId>` confirma | Cap 05 |
| C2 | `denied: requested access to the resource is denied` no `docker push` | ACR Basic atingiu cap 10 GiB | `az acr repository delete --name <acr> --image <repo>:<tag>` para liberar OU upgrade Standard | Cap 02 |
| C3 | `--admin-enabled true` cria credencial órfã | Senha master nunca expira automaticamente | `az acr update --name <acr> --admin-enabled false` + `az acr credential renew` (rotacionar) | Cap 02 |
| C4 | `az acr build` falha `unauthorized: authentication required` em corporate | Tenant policy bloqueia Service Connection temporária do ACR Tasks | Pedir tenant-admin liberar `Microsoft.ContainerRegistry/registries/tasks/scheduledRuns/action` OU build local + `docker push` | Cap 05 |
| C5 | Container App `Provisioning` infinito >10min | MI sem `AcrPull` propagado (Cap 05 Passo 5.5) | Aguardar 60s pós-RBAC; se passou 5min, deletar Container App + esperar 60s + recriar | Cap 05 |
| C6 | Cold-start ACA scale-to-zero adiciona 3-5s na 1ª request após 5min ociosidade | Comportamento esperado do Consumption profile | Subir `min-replicas=1` (custo ~R$ 30/mês fixo) — só se latência crítica | Cap 05 |
| C7 | `n8nio/n8n:latest` quebrou breaking change em 15/04 — workflows invisíveis | Tag `latest` migrou schema PG sem aviso | **Sempre pinar major.minor** (`n8nio/n8n:1.6`); acompanhar releases antes de bumpar | Cap 07 |
| C8 | `WEBHOOK_URL` vazio gera URLs `0.0.0.0:5678` inacessíveis | n8n não usa FQDN ACA real automaticamente | Cravar `WEBHOOK_URL=https://<FQDN>/` (com barra final) **após** ACA criar | Cap 07 |

### §3.4 Auth aplicacional (OAuth + Bearer + tokens)

| # | Sintoma | Causa | Fix | Cap fonte |
|---|---|---|---|---|
| O1 | `api://mcp-helpsphere` rejeitado pelo Portal — `Identifier URI is not a valid URI` | Tenant policy exige `api://{guid}` (não custom name) | Aceitar GUID sugerido + cravar **esse GUID** como `EXPECTED_AUDIENCE` no Container App + atualizar `scope=api://{guid}/.default` | Cap 05 |
| O2 | `tools/list` retorna 200 mas `tools` vazio | `EXPECTED_AUDIENCE` no env do Container App não bate `aud` claim do token (typo trailing slash) | Comparar `jq '.aud'` do token vs `az containerapp show --query "properties.template.containers[0].env"` — devem ser **idênticos byte-a-byte** | Cap 05 |
| O3 | `AADSTS500011: resource principal api://mcp-helpsphere not found` | Server App Reg criada mas Application ID URI **não foi salvo** (Save em Expose an API esquecido) | Voltar Expose an API → confirmar `api://mcp-helpsphere` no topo (não vazio) | Cap 05 |
| O4 | Token sai mas `roles` vem vazio → 403 no MCP | Application permissions sem admin consent (Grant cinza para non-admin) | Tenant-admin abrir App Reg client → API permissions → Grant admin consent | Cap 05 |
| O5 | `MCP_TOKEN` expira durante demo de 1h+ | Token client-credentials TTL = 3600s | Re-rodar Passo 5.6 + atualizar `.env` + re-rodar smoke; em prod usar `ClientSecretCredential` SDK com refresh automático | Cap 05 |
| O6 | `PyJWT` aceita qualquer audience (vetor crítico de impersonation) | `jwt.decode` sem `audience=` parameter | `jwt.decode(token, key, algorithms=["RS256"], audience=os.environ["EXPECTED_AUDIENCE"])` no `auth.py` | Cap 05 |
| O7 | `403 Forbidden` no Speech via Bearer Entra MI | Role assignment ainda propagando (<60s) OR role errado (`Speech User` em vez de `Cognitive Services User`) | Aguardar 60s + confirmar role = `Cognitive Services User` (Speech User só cobre Custom Speech training, não runtime) | Cap 06 |
| O8 | `DefaultAzureCredential` cai em `InteractiveBrowserCredential` no meio do script | `az login` expirou (>1h) ou sessão revogada | `az account get-access-token --resource https://servicebus.azure.net` antes do smoke confirma sessão | Caps 04, 08 |

### §3.5 Foundry Agent SDK (Cap 04)

| # | Sintoma | Causa | Fix | Cap fonte |
|---|---|---|---|---|
| F1 | `azure.ai.projects` import error / `cannot import name 'AIProjectClient'` | Versão errada do SDK preview | Pinar `azure-ai-projects==1.0.0b9` no `requirements.txt`; GA Q3-2026 trará breaking changes (ex.: `create_message` → `threads.messages.create`) | Cap 04 |
| F2 | Tool call falha em **Playground** Foundry | Playground só executa modelo + schema (não suas tools reais) | Esperado — para teste end-to-end use `python agent_runner.py` localmente | Cap 04 |
| F3 | `requires_action` polling infinito (loop sem fim) | Tool retorna JSON inválido OU payload quebrado OU exceção silenciosa no handler | Adicionar `print(json.dumps(result))` antes de `tool_outputs.append`; cravar timeout `max_poll_seconds=60` no loop | Cap 04 |
| F4 | Connection string formato inválido | Cópia incompleta do Foundry portal | Recopiar limpo: Settings → Project properties → Project connection string | Cap 04 |
| F5 | Sugestão "use Assistants API" em StackOverflow não funciona | Assistants API (OpenAI direto) deprecada | Usar **sempre Foundry Agent Service** (Azure-native, integra Hub/Project/Threads) | Cap 04 |
| F6 | Confidence score sempre 1.0 (over-confident) | `temperature=0` produz scoring colado | Ajustar inference parameters: `temperature=0.3`, `top_p=0.9` no deployment + redeploy | Cap 04 |
| F7 | **`BadRequest: This model's maximum context length is 8192 tokens`** no `search_kb` tool ao indexar PDFs grandes | Embedding `text-embedding-ada-002` tem hard limit 8192 tokens; chunks de PDFs corporativos (>30 KB) estourar limite silently antes do tiktoken count | **Truncar chunks a 8000 tokens** (margem segurança vs 8192) usando `tiktoken.encoding_for_model("text-embedding-ada-002")`; fallback se `tiktoken` não disponível: corte hard em 10.000 chars. `pip install tiktoken` obrigatório. Bug original descoberto em aula ao vivo Wave 4 | Cap 04 + cap RAG (Lab Intermediário) |
| F8 | **`search_kb` retorna 400 ou resultados vazios** mesmo com índice populado — payload aceita `query` mas search engine ignora | Índice Azure AI Search criado **sem vectorizer integrado** (config sem `vectorizer` no `index.json`) — `VectorizableTextQuery` (que delega embedding ao Search) falha; precisa `VectorizedQuery` com vetor **pré-computado** localmente | Trocar `VectorizableTextQuery(text=query, ...)` por: `embedding = aoai_client.embeddings.create(input=query, model="text-embedding-ada-002").data[0].embedding` + `VectorizedQuery(vector=embedding, k_nearest_neighbors=5, fields="contentVector")`. Bug descoberto em aula Wave 4 (Function App RAG) | Cap 04 + cap RAG (Lab Intermediário) |

### §3.6 n8n + PostgreSQL (Cap 07)

| # | Sintoma | Causa | Fix | Cap fonte |
|---|---|---|---|---|
| N1 | n8n container loop de restart `connection refused` no PG | PG firewall **Allow public access from any Azure service** = No | Ativar flag em PG → Networking; em prod use VNet + Private Endpoint | Cap 07 |
| N2 | Service Bus messages enfileiram, n8n nunca dispara | `min-replicas 0` + n8n não usa KEDA-aware patterns (long-polling para quando container dorme) | `min-replicas 1` no lab; em prod implementar KEDA Service Bus scaler com Function App wake-up | Cap 07 |
| N3 | `N8N_ENCRYPTION_KEY` perdida = todas credentials viram lixo cifrado | Sem path de recuperação | Sempre gerar via PowerShell `[Convert]::ToBase64String((1..32 \| ForEach-Object {[byte](Get-Random -Maximum 256)}))` (ou `openssl rand -base64 32` em Git Bash/WSL) + anotar em Key Vault/password manager **antes** de colar | Cap 07 |
| N4 | Owner setup do n8n sem "esqueci minha senha" | n8n não tem fluxo password reset built-in | `psql -h <PG_HOST> -U n8nadmin n8n -c "DELETE FROM \"public\".\"user\" WHERE email='<email>';"` + refazer setup; em prod integrar SSO Entra | Cap 07 |
| N5 | n8n node Service Bus Trigger polling falha silently com Topic | Campo `Subscription Name` vazio (Topic exige; Queue não) | Preencher com `n8n-escalation-sub` (ver [`_disclaimers.md`](./_disclaimers.md) **AMB-4**) | Cap 07 |
| N6 | PostgreSQL `Stop` reinicia automaticamente após 7 dias cobrando | Feature Microsoft anti server-órfão | Configurar **Azure Cost Anomaly Alert** (R$ 0) threshold R$ 50 OR delete (não Stop) ao fim da disciplina | Caps 07, 09 |
| N7 | n8n Service Bus Trigger ainda não suporta MI (issue #7821 desde 2024-06) | Limitação upstream | Dual-stack: Connection String ativa + RBAC paralelo cravado (quando PR merge, troca sem mexer mais) | Cap 07 |
| N8 | n8n credentials confusas: alguns nodes aceitam MI Azure, outros só Service Principal, outros só Connection String | n8n é **ferramenta transversal multi-lab** (não-Azure-native) — cada node mantém seu próprio padrão auth conforme upstream community | Documentar matriz auth-por-node no início do lab; padronizar **Service Principal scope-bounded** quando MI não rolar (evita Connection String full-access) | Cap 07 |

### §3.7 Service Bus + Google Sheets (Cap 08)

| # | Sintoma | Causa | Fix | Cap fonte |
|---|---|---|---|---|
| S1 | **`BadRequest: Topic creation is not allowed on basic SKU`** | Service Bus **Basic não suporta Topics** (apenas Queues FIFO 1-para-1) — Topic exige fanout 1-para-N (Standard) | Sempre Standard (~R$ 50/mês fee fixo + msgs); pattern obrigatório se duas subscriptions independentes (`sub-n8n` Teams + `sub-sheets` Google Sheets). Ver [`_disclaimers.md`](./_disclaimers.md) **AMB-4** | Cap 08 |
| S2 | Workflow JSON `escalation-servicebus-sheets.json` usa `topic: escalations` mas Caps 07/08 cravam `tickets-escalated` | Scaffold inicial desalinhado dos passos finais | Editar node Service Bus Trigger no n8n UI direto (sobrescreve JSON); **gap follow-up prof:** atualizar JSON canônico do scaffold | Cap 08 + §7 |
| S7 | Google Sheets API setup external bloqueia smoke (~30min extra) — service account, share, OAuth scope | Setup acontece **fora do Azure** (Google Cloud Console) e não é coberto por preview templates Azure | Provisionar Google Cloud Project + Service Account + JSON key **antes** do recording; share planilha com SA email com **Notify=off**; cravar credential em n8n. Tempo: 20-30min na primeira vez | Cap 08 |
| S3 | Lock duration 15s causa duplicação silent (linha duplicada Sheet, Adaptive Card duplicado) | n8n leva 25s processando (HelpSphere + MCP + Teams), SB reenvia antes do `complete` | `lock-duration ≥ 30s` no lab; em prod medir P99 e setar 5x | Cap 08 |
| S4 | Google share manda email para `n8n-helpsphere-sheets@...iam.gserviceaccount.com` que dá bounce | Checkbox **Notify people** padrão marcado ao share | **Uncheck Notify** ao compartilhar planilha com Service Account | Cap 08 |
| S5 | n8n Google Sheets credential `Error: PEM_read_bio_PrivateKey` | Editor (VSCode com extensão JSON formatter) quebrou `\n` literal em quebra real ao colar | Copiar `private_key` direto do JSON cru no Notepad OU usar campo upload JSON do n8n | Cap 08 |
| S6 | Service Bus Standard cobra R$ 50/mês mesmo sem mensagens | Fee fixo da feature Topics/Subscriptions | Delete namespace ao fim (sem feature `Stop` parcial) — ver Passo 8.7 / Cap 09 | Caps 08, 09 |

### §3.8 Speech (Cap 06)

| # | Sintoma | Causa | Fix | Cap fonte |
|---|---|---|---|---|
| V1 | `400 Bad Request: Invalid audio format` no STT | WAV em `.m4a`/`.mp3` (Voice Recorder Windows grava `.m4a` por default) | `ffmpeg -i input.m4a -ac 1 -ar 16000 -sample_fmt s16 output.wav` (PCM 16kHz mono 16-bit) | Cap 06 + Lab guide |
| V2 | `404 Not Found` no endpoint REST Speech | `SPEECH_REGION` em formato display ("East US 2") em vez de code (`eastus2`) | Copiar do header **Location** das Keys and Endpoint, não do display name | Cap 06 |
| V3 | `RecognitionStatus: NoMatch` mesmo áudio claro | `language=pt-PT` (Portugal) em vez de `pt-BR` OU áudio muito baixo | Forçar `language=pt-BR` no query + `xml:lang="pt-BR"` no SSML; gravar perto do mic | Cap 06 |
| V4 | `Voice 'X' is not supported in region 'eastus2'` | Voice neural nova ainda não disponível na região | Trocar voice OR Speech resource para `eastus`/`westus3`/`francecentral` | Cap 06 |
| V5 | MP3 gerado mas player não reproduz | Output format `riff-*` (PCM cru) em vez de `audio-*-mp3` | `X-Microsoft-OutputFormat: audio-24khz-48kbitrate-mono-mp3` para MP3 real | Cap 06 |
| V6 | `<mstts:express-as>` ignorado silenciosamente (volta tom neutro) | Esquecer `xmlns:mstts="https://www.w3.org/2001/mstts"` no `<speak>` | Cravar template SSML com namespace no scaffold | Cap 06 |
| V7 | Latência TTS > 1s perceived first-byte | cURL `--output file.mp3` faz batch (espera response completo) | Usar SDK streaming (chunks 50-100ms) — obrigatório SLA <300ms | Cap 06 |
| V8 | Copilot Studio knowledge não atualiza após upload PDF/URL | Reindex assíncrono | Aguardar **5-15min** + verificar Knowledge → status `Ready` (não `Processing`); se >20min, remover + re-upload | Cap 03 |
| V9 | Speech F0 (free tier) bloqueia após 5h STT/mês — `403 Quota exceeded` no meio do recording | F0 tem cap 5 horas áudio/mês STT + 0.5M chars TTS; reset dia 1 | Para lab single-recording F0 OK; se previsão >5h, criar **Speech S0** (~R$ 5/1M chars TTS + R$ 5/h STT) — esquecer cleanup de S0 = cobrança contínua | Cap 06 |
| V10 | Voice neural pt-BR (`ThalitaNeural`/`FranciscaNeural`) latência ~3x maior que voice standard (`pt-BR-Antonio`) | Neural voices fazem inference real-time (custo ~R$ 5/1M chars vs R$ 0.50 standard) | Para latência crítica + custo, escolha standard. Neural só quando qualidade tonal expressiva é must-have | Cap 06 |
| V11 | `403 Forbidden` no Speech via Bearer Entra MI mesmo com role atribuído | Role errado: `Speech User` cobre apenas Custom Speech training, **não** runtime STT/TTS | Atribuir `Cognitive Services User` (não `Speech User`) no scope do Speech resource; aguardar 60s propagação | Cap 06 |

### §3.9 Cleanup + custo residual (Cap 09)

| # | Sintoma | Causa | Fix | Cap fonte |
|---|---|---|---|---|
| K1 | `az group delete` em `rg-lab-final` deixa Foundry Project vivo | Project vive em `rg-lab-intermediario` (RG cross-lab compartilhado) sob o Hub — não cascata via RG novo | Cleanup em **5 passos separados** (Cap 09): RG + Foundry Project + Copilot agent + 3 App Regs + decisão `rg-lab-intermediario` | Cap 09 |
| K2 | `az group delete` falha silently com Resource Lock | Lock `CanNotDelete` cravado por admin tenant | Portal → RG → Settings → Locks → remover antes de re-tentar | Cap 09 |
| K3 | App Reg client secrets sobrevivem 90d após esquecer da existência | Vetor de comprometimento longo se vazaram | **Deletar App Reg** invalida o secret na hora — Passo 9.4 obrigatório | Cap 09 |
| K4 | PostgreSQL `Stopped` cobra storage idle E reinicia em 7d | Stop zera compute mas storage 32 GiB cobra ~R$ 5/mês; auto-restart Microsoft | Para R$ 0 permanente: **delete** (não Stop) — Cap 09; Stop é só para sessão recorrente curta | Caps 07, 09 |
| K5 | Cost Management `R$ 0` na hora — alunos entram pânico | Telemetria atrasa **24-48h** entre delete e billing refletir | Confirmar **48h depois** (Passo 9.7) — não 5 min depois | Cap 09 |
| K6 | Key Vault soft-deleted impede recriar nome por 90 dias | Soft-delete obrigatório para KV (compliance) | `az keyvault purge --name <kv> --location eastus2` OR esperar 90d OR usar `<rand>` novo | Cap 09 |
| K7 | Conta sub gera billing "fantasma" em RG já deletado | Storage idle KV soft-deleted, Reserved capacity, Marketplace items | **Cost Anomaly Alert** R$ 50 (gratuito, permanente) — Cost Management → Cost alerts → Add → Anomaly | Cap 09 |
| K8 | RG `rg-lab-intermediario` carrega Hub + MI + LA — decisão crítica | RG cross-lab compartilha entre múltiplos labs do curso | Cenário: vai fazer o lab de produção depois? **NÃO delete** (~R$ 30-40/mês idle); terminou todos labs? `az group delete --name rg-lab-intermediario --yes` | Cap 09 |
| K9 | **Foundry Project deletado fica em soft-delete por 30 dias** — Hub não permite recriar Project com mesmo nome | Foundry tem soft-delete forçado (não desligável) similar ao KV | Usar `<rand>` novo no nome OR esperar 30d OR `az ml workspace delete --permanently-delete true` (purge imediato) | Cap 09 |
| K10 | **RG `rg-lab-final` deletado mas billing reflete só 24h depois** — alunos entram em pânico vendo cobrança "drenando" pós-cleanup | Azure Cost Management telemetria assíncrona (~24h batch, até 48h em casos extremos) | Comunicar timeline ao aluno: cleanup hoje → confirmar R$ 0 só **48h depois** (Cap 09 Passo 9.7). Não retentar delete | Cap 09 |
| K11 | Copilot Studio agent deletado deixa **Topics órfãs** no environment Power Platform | Delete agent UI não cascata Topics (legado Power Virtual Agents) | Antes de deletar agent: limpar Topics manualmente OU deletar **environment** inteiro (Power Platform Admin Center) | Cap 09 |
| K12 | ACA Environment deletado mas **Log Analytics workspace linked sobrevive** cobrando ~R$ 5/mês idle | Log Analytics tem ciclo de vida independente (foi provisionado junto mas não é child resource) | Cleanup explícito: `az monitor log-analytics workspace delete --workspace-name log-helpsphere-ia -g rg-lab-final --yes --force true` | Cap 09 |
| K13 | Service Bus namespace deletado deixa **connection strings órfãs** em apps consumidores (`ca-mcp-helpsphere` env vars, n8n credentials) | Apps consumidores não sabem que namespace sumiu — continuam tentando autenticar com 401/404 | Cleanup ordem: **primeiro** revogar/atualizar todas connection strings em apps clientes → **depois** delete SB namespace. Para lab descartável, OK delete direto | Caps 08, 09 |

---

## §4 Top 12 issues recorrentes (pré-recording checklist)

> Lista priorizada por **frequência de incidência** + **tempo perdido em debug** observado nos smoke runs. Crave essas doze antes do recording.

1. **Conta `live.com` rejeitada (AADSTS50020) em Copilot Studio** (A2) — bloqueia 80% do Cap 03. Fix: tenant dev M365 trial 30d via Cap 03 Passo 3.7 (ver [`_disclaimers.md`](./_disclaimers.md) **AMB-2**). **Tempo evitado: 1-2h**.
2. **Service Bus Basic tentando criar Topic** (S1) — Basic não suporta Topics, apenas Queues 1-para-1. Fix: sempre Standard (~R$ 50/mês). Topic é obrigatório para fanout 2 subscriptions (`sub-n8n` Teams + `sub-sheets` Sheets). Ver [`_disclaimers.md`](./_disclaimers.md) **AMB-4**. **Tempo evitado: 30-60min** (debugging silent failure).
3. **tiktoken truncation 8000 tokens no `search_kb`** (F7) — embeddings `text-embedding-ada-002` têm hard limit 8192 tokens; chunks PDFs estouram silently. Fix: `pip install tiktoken` + truncar a 8000 tokens (margem). **Tempo evitado: 1-2h** (BadRequest 400 sem stack trace claro).
4. **`VectorizedQuery` vs `VectorizableTextQuery` no Function App RAG** (F8) — índices sem vectorizer integrado precisam de vetor pré-computado. Fix: gerar embedding localmente + `VectorizedQuery(vector=..., fields="contentVector")`. **Tempo evitado: 2-3h** (search retorna vazio sem erro).
5. **AcrPull RBAC ainda propagando** (C1, C5) — 60s de espera economiza 20min de "por que não pulla?". Fix: aguardar antes de criar Container App.
6. **Workload profile `Consumption + Dedicated` cobra parado** (P5) — R$ 250/mês silently. Fix: explicitamente `Consumption only`.
7. **`EXPECTED_AUDIENCE` byte-a-byte com `aud` do token** (O2, O3) — trailing slash mata smokes inteiros. Fix: `jq '.aud'` (ou `ConvertFrom-Json` pwsh) vs Container App env var.
8. **PostgreSQL Burstable cobra parado + auto-restart 7d** (P7, N6, K4) — R$ 60/mês esquecido. Fix: delete (não Stop) ao fim + Cost Anomaly Alert R$ 50.
9. **`n8nio/n8n:latest` quebra breaking change** (C7) — tag `latest` migrou schema sem aviso. Fix: pinar `n8nio/n8n:1.6`. n8n é **ferramenta transversal multi-lab** — versionar manualmente.
10. **`min-replicas 0` no n8n perde Service Bus messages** (N2) — long-polling para quando dorme. Fix: `min-replicas 1` no lab.
11. **WAV não é PCM 16kHz mono no STT** (V1) — Voice Recorder Windows grava `.m4a` 48kHz estéreo. Fix: ffmpeg conversão. **Confidence "vai funcionar primeira vez" = 0**.
12. **Cleanup parcial deixa Foundry Project (soft-delete 30d) + 3 App Regs + Log Analytics órfãos** (K1, K3, K9, K12) — `az group delete` não cascata + Foundry/KV têm soft-delete forçado. Fix: 6 passos separados Cap 09.

---

## §5 Toolkit de diagnóstico — comandos universais

### §5.1 Inventário rápido do `rg-lab-final`

```powershell
# Listar todos recursos do RG do Lab Final (cobre 80% dos diagnósticos iniciais)
az resource list --resource-group rg-lab-final `
  --query "[].{name:name, type:type, state:provisioningState}" -o table

# Listar recursos do RG cross-lab compartilhado — onde Foundry Hub + MI + LA vivem
az resource list --resource-group rg-lab-intermediario `
  --query "[].{name:name, type:type}" -o table

# Confirmar sub correta + tipo
az account show --query "{name:name, state:state, type:subscriptionPolicies.quotaId}" -o table
# Esperado: state=Enabled, type=PayAsYouGo_2014-09-01 (NÃO FreeTrial_*)
```

> **Linux/Mac/WSL:** substitua backticks (`` ` ``) por backslashes (`\`).

### §5.2 RBAC — quem tem o quê em quem

```powershell
# Capturar Principal ID da MI cross-RG (vive no `rg-lab-intermediario`)
$MiPrincipal = az identity show -n mi-helpsphere-ia -g rg-lab-intermediario --query principalId -o tsv

# Listar TODAS roles atribuídas à MI (espera-se: AcrPull + Cognitive Services User + Service Bus Receiver + Service Bus Sender)
az role assignment list --assignee "$MiPrincipal" `
  --query "[].{role:roleDefinitionName, scope:scope}" -o table

# Listar suas próprias roles na sub (debugging permissão)
$MyUpn = az account show --query user.name -o tsv
az role assignment list --assignee "$MyUpn" `
  --query "[].{role:roleDefinitionName, scope:scope}" -o table
```

> **Linux/Mac/WSL:** substitua `$Var = az ...` por `VAR=$(az ...)` e backticks por backslashes.

### §5.3 Container Apps — estado + logs

```powershell
# Estado dos Container Apps (MCP + n8n)
az containerapp list --resource-group rg-lab-final `
  --query "[].{name:name, state:properties.runningStatus, fqdn:properties.configuration.ingress.fqdn, image:properties.template.containers[0].image}" -o table

# Logs ao vivo (substitua <NAME>: ca-mcp-helpsphere ou ca-n8n-helpsphere)
az containerapp logs show --name <NAME> --resource-group rg-lab-final --follow

# Inspecionar env vars do MCP (debug audience mismatch)
az containerapp show --name ca-mcp-helpsphere --resource-group rg-lab-final `
  --query "properties.template.containers[0].env" -o table
```

> **Linux/Mac/WSL:** substitua backticks (`` ` ``) por backslashes (`\`).

### §5.4 Foundry Hub + Project (cross-RG)

```powershell
# Hub aifhub-apex-prod existe?
az ml workspace show --name aifhub-apex-prod -g rg-lab-intermediario --query "{name:name, kind:kind, state:provisioningState}" -o table

# Project criado no Cap 04 existe?
az ml workspace show --name aifproj-helpsphere-agente -g rg-lab-intermediario --query "{name:name, kind:kind}" -o table
# Esperado: kind=project

# Deployment gpt-4.1-mini ativo
az cognitiveservices account deployment show `
  --name aifhub-apex-prod -g rg-lab-intermediario --deployment-name gpt-4.1-mini `
  --query "properties.provisioningState" -o tsv
# Esperado: Succeeded
```

> **Linux/Mac/WSL:** substitua backticks (`` ` ``) por backslashes (`\`).

### §5.5 App Registrations (tenant Entra)

```powershell
# Listar 2 App Regs do MCP (Cap 05)
az ad app list --filter "startswith(displayName,'app-mcp-helpsphere')" `
  --query "[].{name:displayName, appId:appId}" -o table
# Esperado: 2 linhas (server + client)

# Decode token (debug audience/roles) — substitua $Token (PowerShell nativo, sem jq/base64 -d)
$Segments = $Token.Split('.')
$PayloadB64 = $Segments[1].Replace('-', '+').Replace('_', '/')
switch ($PayloadB64.Length % 4) { 2 { $PayloadB64 += '==' } 3 { $PayloadB64 += '=' } }
$Payload = [Text.Encoding]::UTF8.GetString([Convert]::FromBase64String($PayloadB64))
$Payload | ConvertFrom-Json | Select-Object aud, iss, roles, exp
# Esperado: aud == EXPECTED_AUDIENCE do Container App; roles não-vazio
```

### §5.6 Service Bus + n8n + PostgreSQL

```powershell
# Service Bus namespace + Topic + Subscription
az servicebus namespace show --name sb-helpsphere-final -g rg-lab-final `
  --query "{name:name, sku:sku.name, status:status}" -o table
# Esperado: sku=Standard, status=Active

# PostgreSQL Flexible Server estado (Cap 07)
az postgres flexible-server show --name pg-n8n-<rand> -g rg-lab-final `
  --query "{state:state, sku:sku.name}" -o table
# Esperado: state=Ready, sku=Standard_B1ms

# Smoke n8n /healthz
curl.exe -i "https://<N8N_FQDN>/healthz"
# Esperado: HTTP/2 200 + body { "status": "ok" }
```

> **Linux/Mac/WSL:** substitua backticks por backslashes e `curl.exe` por `curl`.

### §5.7 Smoke da pipeline end-to-end (após Cap 08)

```powershell
# Publica msg sintética no SB Topic — pipeline SB → n8n → Sheet roda
az servicebus topic send `
  --namespace-name sb-helpsphere-final --resource-group rg-lab-final `
  --topic-name tickets-escalated `
  --body '{"ticket_id":9999,"severity":"HIGH","category":"smoke-diag","persona":"validador","summary":"Diagnóstico §5","escalated_by":"troubleshooting-cap10"}'
# Esperado: ~10s depois, linha nova na planilha Google Sheets + Adaptive Card no Teams
```

> **Linux/Mac/WSL:** substitua backticks (`` ` ``) por backslashes (`\`).

---

## §6 Cleanup obrigatório (recap rápido — detalhe completo no Cap 09)

```powershell
# Path completo (ordem importa para não deixar órfão)
az group delete --name rg-lab-final --yes --no-wait                              # Passo 1: RG do lab
az ml workspace delete --name aifproj-helpsphere-agente -g rg-lab-intermediario      # Passo 2: Foundry Project (Hub fica)
# Passo 3: Copilot Studio agent — manual em https://copilotstudio.microsoft.com (delete copilot)
az ad app delete --id <app-mcp-helpsphere-server-id>                             # Passo 4a: App Reg server
az ad app delete --id <app-mcp-helpsphere-client-id>                             # Passo 4b: App Reg client
az ad app delete --id <app-n8n-graph-id>                                         # Passo 4c: App Reg n8n (se Cap 08 fez)
# Passo 5: 24-48h depois — Cost Management → confirmar R$ 0
```

Confirme via:

```powershell
az group exists --name rg-lab-final                                              # false
az ml workspace list -g rg-lab-intermediario --query "[?name=='aifproj-helpsphere-agente']" -o tsv  # vazio
az ad app list --filter "startswith(displayName, 'app-mcp-helpsphere')" --query "length(@)"    # 0
```

> **Linux/Mac/WSL:** comandos `az` funcionam idênticos; remova os comentários inline em `#` se quebrar parser do shell.

> **Regra de ouro:** se você delete o RG mas não deletou o Foundry Project, App Regs, e Copilot agent, o lab continua **drenando ~R$ 1-3/mês idle** + secrets órfãos vivos 90d. Cap 09 é não-opcional.

---

## §7 Gaps para follow-up do prof

> Itens identificados em smoke runs recentes que precisam pass dedicado — não bloqueiam recording mas devem entrar em backlog.

- 🔄 **`n8n-workflows/escalation-servicebus-sheets.json` desalinhado com Caps 07/08** — JSON canônico no repo usa `topic: "escalations"` + `subscription: "n8n-consumer"`, mas Caps 07/08 cravam `tickets-escalated` + `n8n-escalation-sub`. Workaround atual: editar no n8n UI (Cap 08 Passo 8.3). **Fix dedicado:** atualizar JSON do scaffold em pass próprio. (Origem: Cap 08 Surpresa S2)
- 🔄 **Adaptive Card payload do node Microsoft Graph (Teams) é placeholder** — workflow JSON ainda não tem botões `Aceitar`/`Rejeitar`/`Reatribuir` que façam PATCH de volta no HelpSphere. (Origem: Cap 08 §Gaps)
- 🔄 **Dead-letter alerting não cravado neste lab** — Service Bus Subscription com `dead-letter ON` mas sem alerta de DLQ depth no Application Insights. **Production-grade:** mover para o lab de produção (`apex-helpsphere-prod-lab/07` — Content Safety + App Insights). (Origem: Cap 08 §Gaps)
- 🔄 **Smoke run real do `/api/agent/voice` (Cap 06) está gated** — endpoint que encadeia STT → agent → TTS depende de Function App `func-agent-runner` com Foundry Agent + MCP wired (Cap 08). Smoke voice playground via Copilot Studio funciona, mas pipeline programática completa precisa Cap 08 fechado. (Origem: Cap 06 checklist linha "(Opcional) Endpoint /api/agent/voice deployado")
- 🔄 **2 surpresas RAG não estavam neste cap até polish recente** (F7 tiktoken truncation + F8 VectorizedQuery) — descobertas em aula ao vivo. Considerar cross-ref formal com cap RAG do Lab Intermediário (capítulo `09 — Function App RAG` no fork `apex-rag-lab`). (Origem: smoke run pós-recording)
- ✅ **AMB-1, AMB-2, AMB-3, AMB-4 consolidados em `_disclaimers.md`** — capítulos referenciam IDs apontando para [`_disclaimers.md`](./_disclaimers.md), eliminando drift. Quando prof revisar tier/licenciamento, atualizar somente esse arquivo + bumpar `version-anchor`.

---

## PowerShell vs Bash — armadilhas comuns

Esta disciplina usa **Windows PowerShell 7** como shell padrão. Se você copiar comandos bash de outros guias (StackOverflow, docs Linux, READMEs upstream), vai esbarrar nestas diferenças:

| Antipadrão bash | Equivalente PowerShell |
|---|---|
| `curl -X POST ...` (com flags) | `curl.exe -X POST ...` — em pwsh, `curl` é alias de `Invoke-WebRequest` |
| `--data-binary @file.json` | `--data-binary "@file.json"` — `@` em pwsh é splatting operator, precisa estar entre aspas |
| `export VAR="value"` | `$env:VAR = "value"` |
| `cmd \` (line continuation) | `` cmd ` `` (backtick) |
| `2>/dev/null` ou `> /dev/null` | `2>$null` ou `\| Out-Null` |
| `head -5` | `\| Select-Object -First 5` |
| `<<EOF ... EOF` heredoc | `@'...'@` here-string (com `@` na coluna 0) |
| `cmd1 \| cut -d'.' -f2` | `($cmd1).Split('.')[1]` |
| `base64 -d` | `[Text.Encoding]::UTF8.GetString([Convert]::FromBase64String($var))` |
| `mkdir -p path` | `New-Item -ItemType Directory -Path path -Force` |
| `~/path` | `$HOME\path` ou `$env:USERPROFILE\path` |
| `openssl rand -base64 32` | `[Convert]::ToBase64String((1..32 \| ForEach-Object {[byte](Get-Random -Maximum 256)}))` |

**`jq` no Windows:** não vem instalado por default. Instale com `winget install jqlang.jq` ou `choco install jq`. Como alternativa PowerShell nativa, use `ConvertFrom-Json`:

```powershell
# Bash: response | jq '.tools[].name'
# PowerShell:
$response | ConvertFrom-Json | Select-Object -ExpandProperty tools | ForEach-Object { $_.name }
```

**Por que `curl.exe` e não `curl`?** Em PowerShell 7, `curl` é um alias para `Invoke-WebRequest` (cmdlet nativo do PowerShell) — ele não aceita as flags do curl Unix (`-X`, `-H`, `-d`, `--data-binary`). Para usar o curl real (que vem com Windows 10+ via `C:\Windows\System32\curl.exe`), invoque sempre como `curl.exe` explicitamente. **Anti-pattern silencioso:** rodar `curl -X POST ...` em pwsh "funciona" mas com semântica errada, retornando objetos `HtmlWebResponseObject` que confundem o parse.

---

## §8 Suporte adicional

- **Issues:** https://github.com/tftec-guilherme/apex-helpsphere-agente-lab/issues — abra issue marcando o número do Cap onde travou + colando output do `az resource list -g rg-lab-final` para diagnóstico rápido
- **Guia canônico Portal (mais detalhado em casos extremos):** `Lab_Final_Agente_Workflow_Guia_Portal.md` — seção Troubleshooting do guia mestre
- **Cheat sheets relacionadas (Material Autoral):** buscar `cheat-licenciamento-power-platform.md`, `cheat-rbac-managed-identity.md`, `cheat-service-bus-tier-decision.md` no repositório de material complementar do curso
- **Prof Guilherme Campos** (Coordenador da Disciplina) — para gaps que estão em §7 ou erros novos não catalogados

---

## §9 Cross-ref rápida — capítulo onde a gotcha original aparece

| Cap | Tema | Surpresas catalogadas (n) | Issues no Top 12 |
|---|---|---:|---|
| 01 | Pré-requisitos | 6 | A2, A3, P6 |
| 02 | RG + ACR + ACA | 8 | C1, C5, P1, P5 |
| 03 | Copilot Studio | 8 | A2 (AADSTS50020), A5, A6, A7, A8 |
| 04 | Foundry Agent SDK | 8 | F1-F8 (inclui tiktoken F7 + VectorizedQuery F8) |
| 05 | MCP Server Deploy | 8 | C1, C5, O1-O6 |
| 06 | Speech (STT/TTS) | 11 | V1-V11 (inclui F0 cap + Neural latência + Cog Services role) |
| 07 | n8n Escalation | 9 | C7, C8, N1-N8 (inclui n8n transversal multi-lab) |
| 08 | Service Bus + Sheets | 7 | S1-S2, S7 (Topic vs Queue + Google Sheets external) |
| 09 | Cleanup | 13 | K1-K13 (inclui Foundry soft-delete 30d, billing async 24h, Copilot topics órfãs, Log Analytics linked, SB connection strings órfãs) |
| **Total** | — | **~78+** | **12 críticos + 60+ catalogados** |

> Este capítulo **agrega ~78+ Surpresas** dos 9 capítulos anteriores em **1 ponto único de busca**, **sem duplicar conteúdo** — cada linha cita o cap-fonte para detalhe completo. Ordem de leitura recomendada: §2 decision tree → §3 categoria do erro → cap-fonte para context. Dois gotchas centrais (`tiktoken truncation` e `VectorizedQuery` vs `VectorizableTextQuery`) **só foram descobertos em smoke pós-recording Wave 4** — referência cruzada com cap RAG (`apex-rag-lab/docs/09-funcao-rag`) é recomendada para alunos cursando ambos os labs.
