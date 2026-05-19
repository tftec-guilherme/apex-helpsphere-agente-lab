# Capítulo 11 (OPCIONAL) — Azure Bot Service: alternativa low-code ao Foundry agent

> **Status:** **OPCIONAL** — este capítulo NÃO é exigido para concluir o Lab Final. Os capítulos 01-10 já entregam o agente HelpSphere end-to-end via Foundry + Copilot Studio + MCP + Speech + n8n + Service Bus. **Cap 11 existe para o aluno que quer comparar abordagens** ou tem caso de uso onde Bot Service se encaixa melhor que Foundry (ver §1).
>
> **Tempo:** ~45min se executado · ~10min se apenas leitura comparativa
>
> **Pré-requisitos:** mesmos do Lab Final (Entra ID + Speech + Application Insights) — Cap 01-02 concluídos. Não depende do Foundry agent do Cap 04.

---

## §1 Quando usar Bot Service vs Copilot Studio vs Foundry SDK

A escolha entre as 3 plataformas conversacionais do Azure depende de **3 dimensões**: nível de customização, time-to-value e tipo de canal.

| Dimensão | Copilot Studio (Cap 03) | Foundry Agent SDK (Cap 04) | **Azure Bot Service (Cap 11)** |
|---|---|---|---|
| **Modelo de programação** | Low-code visual (Power Platform) | Code-first Python/.NET | **SDK híbrido — Bot Framework SDK + canais nativos** |
| **Time-to-value** | Horas (drag-and-drop) | Dias (custom tools + RAG) | **Dias (Bot Framework boilerplate + canais)** |
| **Customização** | Limitada — tópicos pré-definidos | Total — qualquer integração custom | **Alta — qualquer canal (Teams/WebChat/Direct Line/SMS/Email)** |
| **Canais nativos** | Teams + Web + Power Platform | API direta (você integra canal) | **15+ canais oficiais (Teams/Slack/Telegram/WhatsApp via Twilio/Email/SMS)** |
| **Multi-tenant SaaS** | Por environment (1 bot por tenant) | Sim (qualquer arquitetura) | **Sim — `MultiTenant` auth nativo** |
| **Custo** | Por message capacity (US$ 200+/mês plan) | Token-based (OpenAI quota) | **Standard: ~US$ 0,50/1000 messages + Premium tier custom** |
| **Caso de uso típico** | FAQ corporativo + workflows simples | RAG + agente com tools custom + voz | **Bot multi-canal com handoff humano + analytics enterprise** |

**Regra prática deste lab:**

- Copilot Studio = **front-end conversacional** (cap 03) — fala com o usuário final via Teams
- Foundry Agent SDK = **engine de raciocínio** (cap 04) — RAG + tools custom + decisão
- Bot Service = **alternativa quando você precisa de canais que Copilot Studio NÃO suporta** (WhatsApp via Twilio, SMS, Email, Direct Line embedded, Webex, etc.) — substituto direto do Copilot Studio na ponta, **continua consumindo Foundry agent como backend** via MCP server (Cap 04).

> **Anti-pattern recorrente:** aluno pensa que Bot Service é "outra IA". Não é — é apenas a **camada de canal multi-platform**. A IA continua sendo Foundry agent, Bot Service só recebe/envia mensagens em mais formatos.

---

## §2 Por que Bot Service neste lab é opcional

O Lab Final foca em **Teams como canal único** (via Copilot Studio) porque:

1. Apex Retail é workplace Microsoft 365 — Teams é nativo
2. Copilot Studio cobre Teams + Web sem overhead de Bot Framework SDK
3. Voz (cap 06) entra via Speech Service direto — não precisa de canal Bot Service

**Bot Service entra quando:**

- Cliente precisa de WhatsApp Business (via Twilio adapter)
- Atendimento via SMS (operadoras BR via Twilio ou Vonage)
- Direct Line embedded em site público (sem login Microsoft)
- Webex/Slack channels para clientes em outros ecossistemas

Para esses casos, este Cap 11 mostra **como criar um Bot Service que substitui Copilot Studio mas mantém Foundry agent como backend**.

---

## §3 Provisionar Bot Service

> **Atenção custo:** Bot Service tier **Free F0** (até 10.000 mensagens/mês em canais Premium) é suficiente para o lab. Tier **Standard S1** (~US$ 0,50/1000 mensagens em canais Premium) cobra apenas em produção real.

**No Portal Azure:**

1. Barra superior → buscar **"Azure Bot"** → clicar
2. **+ Create** → escolher **Azure Bot** (não "Bot Channels Registration" — esse é legado)
3. Preencher tab **Basics:**
   - **Bot handle:** `bot-helpsphere-final` (globalmente único)
   - **Subscription:** sua
   - **Resource group:** `rg-lab-final`
   - **Pricing tier:** `Free F0`
   - **Microsoft App ID:** **Create new Microsoft App ID** → tipo `Multi-tenant`
   - **Creation type:** `Create new Microsoft App ID`
4. Tab **Tags** (opcional): `cost-center=apex-helpsphere-ia`, `environment=lab`
5. **Review + create** → **Create**
6. Aguardar provisioning ~1-2min até **Succeeded**

<!-- screenshot: passo-11.3-criar-bot-service-portal.png -->

> **Diferença Bot Service vs Bot Channels Registration:** "Azure Bot" (novo, GA desde 2021) é o resource type recomendado — engloba Bot Channels Registration legacy + suporta canais Premium nativos. Documentação Microsoft ainda usa termos misturados, mas se você está criando em 2024+, sempre use **Azure Bot**.

---

## §4 Adicionar canal Teams (paridade com Copilot Studio)

1. Resource `bot-helpsphere-final` → menu **Channels** (esquerda)
2. Tab **Available Channels** → clicar **Microsoft Teams**
3. **Microsoft Teams Channel** → aceitar Terms of Service → **Apply** → **Save**
4. Canal Teams agora aparece em **Connected** com status `Running`

<!-- screenshot: passo-11.4-channel-teams.png -->

Para canais adicionais (opcional pedagógico):

- **Web Chat:** já vem ativo por default. Resource → **Channels** → **Web Chat** → copiar **Embed code** e colar em qualquer site HTML.
- **Direct Line:** Resource → **Channels** → **Direct Line** → criar Secret key → usar para embeds custom (substituto white-label do Web Chat).
- **Slack:** Resource → **Channels** → **Slack** → exige criar Slack App em api.slack.com e colar 3 IDs.

---

## §5 Conectar Bot Service ao Foundry agent (via MCP)

A inteligência continua sendo o Foundry agent do Cap 04. Bot Service apenas roteia mensagens. Há 2 padrões:

### §5.1 Padrão A — Bot Framework SDK chama Foundry diretamente

Você implementa o **Bot Framework SDK** (Python ou .NET) em uma Function App ou Container App separada. O bot recebe activity Teams, chama `agent_runner.run(prompt, conversation_id)` do Cap 04, retorna activity.

**Pseudo-código Python (Bot Framework SDK 4.16+):**

```python
from botbuilder.core import TurnContext, ActivityHandler
from agent_runner import run_agent  # Cap 04 entrypoint

class HelpSphereBot(ActivityHandler):
    async def on_message_activity(self, turn_context: TurnContext):
        user_message = turn_context.activity.text
        conversation_id = turn_context.activity.conversation.id

        # Chamar Foundry agent (Cap 04) com conversation_id como thread
        response = await run_agent(prompt=user_message, thread_id=conversation_id)

        await turn_context.send_activity(response.assistant_message)
```

Deploy em Function App ou Container App + configurar Bot Service **Messaging endpoint** apontando para a URL `/api/messages` da Function/App.

### §5.2 Padrão B — Bot Service via MCP (server do Cap 04 é reusado)

Mais simples e demonstra reuso da arquitetura existente:

1. Bot Framework recebe activity Teams
2. Bot chama tool `get_ticket` ou `add_comment` do MCP server (Cap 04)
3. MCP responde com dados HelpSphere
4. Bot formata como Adaptive Card e responde no canal

Vantagem: **um único endpoint de tools** (MCP) serve Copilot Studio (cap 03) + Foundry agent (cap 04) + Bot Service (este cap 11) — DRY arquitetural.

---

## §6 Testar no Web Chat

1. Resource `bot-helpsphere-final` → menu **Test in Web Chat** (esquerda)
2. Digitar: `Qual o status do ticket 1?`
3. Bot deve responder com dados do ticket via MCP → HelpSphere API

> **Se retornar erro 503:** Bot Service não consegue alcançar Messaging endpoint. Verifique que o endpoint da Function App / Container App está ativo + retornando 200 em `/api/messages`.

<!-- screenshot: passo-11.6-test-web-chat.png -->

---

## §7 Cleanup (obrigatório se executado)

Se você provisionou Bot Service, **delete antes de fechar o lab** para evitar charges residuais:

**No Portal Azure:**

1. **Resource groups** → `rg-lab-final` → tab **Resources**
2. Selecionar `bot-helpsphere-final` (e Function App / Container App associados, se criou)
3. **Delete** → confirmar

**Via Azure CLI — PowerShell:**

```powershell
az bot delete --resource-group rg-lab-final --name bot-helpsphere-final --yes
```

> **Linux/Mac/WSL:** comando idêntico (Azure CLI é multi-plat).

App Registration do Bot ID **fica no Entra** mesmo após delete do resource — limpe manualmente em **Microsoft Entra ID → App registrations → All applications** se quiser zerar.

---

## §8 Comparação rápida com Copilot Studio (Cap 03)

| Aspecto | Copilot Studio (Cap 03) | Bot Service (Cap 11) |
|---|---|---|
| **Setup inicial** | ~5min (visual) | ~45min (resource + canais + code) |
| **Canais nativos** | Teams + Web + Power Platform | 15+ (incluindo WhatsApp/SMS/Slack) |
| **Customização lógica** | Tópicos drag-and-drop | Code-first total (Bot Framework SDK) |
| **Voz nativa** | Sim (Teams + Power Apps) | Não (precisa integrar Speech Service manualmente) |
| **Handoff humano** | Sim — Customer Service integrated | Sim — Direct Line + Connector custom |
| **Multi-tenant** | Sim (1 bot por environment) | Sim (`MultiTenant` no App ID) |
| **Custo lab** | Trial 30 dias gratuito | Free F0 (10k msg/mês) |
| **Custo produção** | US$ 200+/mês plan | ~US$ 0,50/1000 msg (canais Premium) |
| **Recomendação Apex** | **Default** para Teams-first | **Alternativa** para multi-canal extra-M365 |

---

## §9 Quando NÃO usar Bot Service

Bot Service **não compete** com Foundry agent — eles são complementares. Mas Bot Service **não substitui**:

- ❌ **Não é RAG engine** — você ainda precisa de Foundry/AI Search para grounding em documentos
- ❌ **Não é orquestrador de workflow** — n8n/Logic Apps continuam fazendo orquestração de Service Bus → Teams → Sheets
- ❌ **Não treina modelos** — usa modelos OpenAI/Foundry pré-treinados; fine-tuning fica no Foundry/Azure OpenAI
- ❌ **Não é alternativa ao MCP server** — o MCP server (Cap 04) continua sendo o contract de tools; Bot Service apenas adiciona canais

> **Resumo da §9:** Bot Service é **multiplicador de canal**, não substituto de inteligência. Se sua única dor é "preciso falar com cliente fora do Teams", entre. Se sua dor é "preciso de RAG melhor" ou "preciso de tools custom", continue no Cap 04.

---

## §10 Referências e leituras complementares

- [Azure Bot Service docs](https://learn.microsoft.com/azure/bot-service/) — overview oficial
- [Bot Framework SDK Python](https://github.com/microsoft/botbuilder-python) — repo oficial
- [Channels & connectors](https://learn.microsoft.com/azure/bot-service/bot-service-channels-reference) — lista completa de canais Premium e Standard
- [Pricing](https://azure.microsoft.com/pricing/details/bot-services/) — tier comparativo
- [Adaptive Cards designer](https://adaptivecards.io/designer/) — para construir respostas ricas no Bot

---

## ✅ Checkpoint Capítulo 11 (opcional)

Se você completou este capítulo:

- [ ] `bot-helpsphere-final` provisionado em `rg-lab-final` (Free F0)
- [ ] Canal Teams conectado e em estado `Running`
- [ ] Messaging endpoint apontando para Function App / Container App com Bot Framework SDK
- [ ] Test in Web Chat retorna resposta válida do Foundry agent (via MCP)
- [ ] **OU** você leu o capítulo e decidiu que Bot Service não se aplica ao seu caso de uso
- [ ] (Se provisionado) Cleanup executado para zerar charges

---

**Status final do Lab Final:** Caps 01-10 são o caminho canônico; Cap 11 é a porta para multi-canal além de Teams. Os 4 outros tópicos da disciplina D06 que valem investigação separada (Azure ML / Prompt Flow, Semantic Kernel, AutoGen multi-agent, Custom Document Intelligence) ficam fora do escopo deste lab — mencionados no PARA-O-ALUNO.md como extensões futuras.
