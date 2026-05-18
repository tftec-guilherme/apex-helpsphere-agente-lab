# Capítulo 06 — Speech (STT/TTS)

> **Objetivo:** provisionar **Azure AI Speech `spch-helpsphere`** (Standard S0) no `rg-lab-final`, atribuir role `Cognitive Services User` à Managed Identity cross-RG `mi-helpsphere-ia` (em `rg-lab-intermediario`), capturar `SPEECH_KEY` + `SPEECH_REGION`, gravar áudio próprio em pt-BR, validar **STT** (cURL `recognition/conversation`) + **TTS** (cURL SSML com voice `pt-BR-FranciscaNeural`), expor o endpoint `/api/agent/voice` que encadeia STT → `agent_runner.py` → TTS, e plugar tudo no canal de voz do agente Copilot Studio `HelpSphere Tier 1 Agent`. Validação visual final via **Speech Studio TTS playback** no Portal.
>
> **Tempo:** 30-45 min (15-20 min se você só vai exercitar STT/TTS via cURL e pular o endpoint Function `/api/agent/voice` para uma sessão posterior)

---

## Pré-requisitos

- ✅ RG `rg-lab-final` existe (capítulo anterior do Lab Final) e RG `rg-lab-intermediario` hospeda a MI cross-RG `mi-helpsphere-ia` (provisionada no Lab Intermediário)
- ✅ Agente Foundry `helpsphere-tier1-agent` criado em `agent-code/func-agent-runner/agent_runner.py` com tools de MCP funcionais (capítulos anteriores)
- ✅ Agente Copilot Studio `HelpSphere Tier 1 Agent` em tenant M365 dev (não `live.com` — ver [`_disclaimers.md`](./_disclaimers.md) **AMB-2**)
- ✅ `az` CLI logado, `curl` + `jq` instalados, microfone funcional no laptop, player de áudio local (`.mp3` reproduzível)

> **Atenção preview pt-BR voices:** catálogo neural Microsoft muda trimestralmente. Voices canônicas no momento da gravação: `pt-BR-FranciscaNeural` (feminina, default Apex) e `pt-BR-AntonioNeural` (masculina, fallback). Voices novas como `pt-BR-ThalitaNeural` aparecem antes em `eastus`/`westus3`. Confira `https://speech.microsoft.com/portal/voicegallery` antes de cravar voice nova em produção. **Não use `pt-PT-*` (Portugal)** — sotaque/prosódia divergem.

---

## Resumo dos 4 artefatos que vamos cravar

| Artefato | Implementação | Backend / Identidade | Custo (R$) |
|---|---|---|---|
| Recurso `spch-helpsphere` | Portal → AI Services → Speech (Standard S0) em `rg-lab-final` | Speech Service standalone (sem Foundry attach) | R$ 0 parado · ~R$ 5/hora STT · ~R$ 5/1M chars TTS standard · ~R$ 60/1M chars TTS neural |
| Role `Cognitive Services User` | Speech IAM → atribuir à MI `mi-helpsphere-ia` em `rg-lab-intermediario` (cross-RG) | Entra RBAC | R$ 0 |
| Áudio próprio `sample-question-pt.wav` | Windows Voice Recorder / QuickTime / Audacity (5-10s pt-BR) | Arquivo local na pasta do lab | R$ 0 |
| Endpoint `/api/agent/voice` (opcional) | Function App `func-agent-runner` → STT → agent → TTS → MP3 | Encadeia Speech + Foundry agent + Speech | ~R$ 0,01 por chamada smoke (10s áudio + ~150 tokens + ~80 chars TTS) |

> **Nota pedagógica — Speech standalone vs atachado a Foundry Hub:** o Foundry Hub permite atachar Speech para playground de voice agents. **Mantemos standalone** porque cleanup é mais limpo (delete `rg-lab-final` apaga junto), `agent_runner.py` chama Speech via REST direto, e preserva reuso pós-lab sem derrubar Hub. Em produção corporate, atachar ao Hub centraliza billing + monitoring.

> **Nota pedagógica — Free F0 vs Standard S0:** F0 dá **5h STT/mês + 0,5M chars TTS/mês gratuitos** (1 unidade por sub, sem SLA). Lab caberia em F0, mas usamos **S0** por 3 motivos: (a) pattern de produção (sem surpresas se sub for reusada), (b) S0 tem SLA 99,9%, (c) segundo F0 na sub falha com `OutOfFreeQuota` se outro projeto já consumiu. **Atenção:** 5h STT em F0 esgota rápido em smoke testing repetido (gravação + transcrição × várias iterações dev). **Custo absoluto lab S0: R$ 4-6** total (vs R$ 0 no F0 se quota mensal disponível).

> **Nota pedagógica — TTS standard vs neural pricing:** TTS standard custa ~R$ 5/1M chars (voices antigas, descontinuadas para novos deployments em 2024); TTS neural custa ~R$ 60/1M chars (`pt-BR-FranciscaNeural`, `pt-BR-AntonioNeural`, etc — 12x mais caro mas qualidade conversacional natural). Lab usa exclusivamente neural — custo de smoke (~80 chars) fica abaixo de R$ 0,01.

---

## Passo 6.1 — Criar Azure AI Speech `spch-helpsphere`

**No Portal Azure:**

1. Barra superior → buscar **"Speech Services"** (ou **"Speech"** em **AI + Machine Learning**) → **+ Create**
2. Tab **Basics:**
   - **Subscription:** sua sub · **Resource group:** `rg-lab-final` · **Region:** `East US 2`
   - **Name:** `spch-helpsphere` (sem sufixo aluno — convenção da disciplina)
   - **Pricing tier:** `Standard S0` ⚠️ **não troque para F0** (ver Nota Free F0 acima)
3. Tab **Network:** `All networks` (lab simplificado — produção use Private Endpoint)
4. Tab **Identity:** `System assigned: Off` (consumidor é a MI `mi-helpsphere-ia`, sentido inverso)
5. Tab **Tags:** herde do RG (`cost-center`, `environment=lab`, `application=helpsphere-ia`)
6. **Review + create** → **Create** → aguarde ~30s-1min até **Succeeded**

<!-- screenshot: cap06-passo6.1-criar-speech-portal.png -->

> **Alternativa via Azure CLI (Windows PowerShell 7):**
> ```powershell
> az cognitiveservices account create -n spch-helpsphere -g rg-lab-final `
>   --kind SpeechServices --sku S0 --location eastus2 --yes
> ```
> **Linux/Mac/WSL:** substitua backticks (`` ` ``) por backslashes (`\`).

> **Custo:** S0 cobra só por uso · R$ 0 parado · ~R$ 5/hora STT · ~R$ 60/1M chars TTS Neural · ~R$ 300/1M chars Custom Voice. **Lab realista: R$ 4-6** total.

> **Nota pedagógica — `eastus2` vs `brazilsouth`:** br-south tem latência ~30ms vs ~120ms para SP, MAS catálogo pt-BR reduzido (atualmente só Francisca + Antonio em br-south; eastus2 tem catálogo completo + Custom Voice training). Lab prioriza catálogo > latência. Produção SLA <200ms p99: br-south ou multi-region via Front Door.

> **Atenção region-locked:** `SPEECH_KEY` é vinculada à região do recurso. Cravando recurso em `eastus2` significa que TODAS as chamadas REST devem ir para `https://eastus2.stt.speech.microsoft.com` e `https://eastus2.tts.speech.microsoft.com`. Chamar `https://brazilsouth.*` com a mesma key retorna 401 silencioso. Anti-pattern: aluno provisiona Foundry/AOAI em `eastus2` e Speech em `brazilsouth` por reflexo de "latência BR" — STT/TTS quebram.

---

## Passo 6.2 — Capturar `SPEECH_KEY` e `SPEECH_REGION`

**No Portal Azure (recurso `spch-helpsphere` recém-criado):**

1. Após o **Create** concluir, clique **Go to resource** (ou abra o recurso `spch-helpsphere` em `rg-lab-final`)
2. Menu lateral → **Resource Management** → **Keys and Endpoint**
3. Anote os 2 valores que vamos usar:
   - **KEY 1** → vamos chamar de `SPEECH_KEY` (formato: 32 chars hex)
   - **Location/Region** → vamos chamar de `SPEECH_REGION` = `eastus2` (sem o "East US 2" amigável)
4. Clique no ícone **Copy** ao lado da KEY 1 — cole temporariamente em editor seguro

<!-- screenshot: cap06-passo6.2-keys-endpoint-anotar.png -->

**Adicionar ao `.env` do `agent-code/`:**

```dotenv
# Speech Service
SPEECH_KEY="<KEY-1-do-Portal>"
SPEECH_REGION="eastus2"
```

> [!IMPORTANT] **Placeholders no `.env`**
> `<KEY-1-do-Portal>` e `eastus2` são placeholders. Substitua `<KEY-1-do-Portal>` pelo valor real copiado em 6.2.1; `SPEECH_REGION` deve ser exatamente `eastus2` (lowercase, sem espaço/hífen) para que o REST endpoint resolva. Se a Function App `func-agent-runner` já foi provisionada, replicar essas variáveis em **Configuration → Application settings** dela também (referenciar Key Vault em produção).

> **Atenção secret rotation:** KEY 1 + KEY 2 permitem rotação sem downtime (alternar mensalmente em produção via automation). Lab: KEY 1 estática OK pelo prazo curto + cleanup obrigatório no capítulo final.

> **Nota pedagógica — `SPEECH_REGION` formato:** REST endpoint exige `eastus2` lowercase sem espaço/hífen. `eastus-2`, `east us 2`, `EASTUS2` resultam em 404 silencioso. Anti-pattern recorrente: aluno copia "East US 2" do Portal e cola direto.

---

## Passo 6.3 — Atribuir RBAC `Cognitive Services User` à MI cross-RG

**No Portal Azure:**

1. Recurso `spch-helpsphere` → **Access control (IAM)** → **+ Add** → **Add role assignment**
2. Tab **Role:** buscar **`Cognitive Services User`** → **Next**
   - ⚠️ **Não use** `Cognitive Services Speech User` — esse é só para Custom Speech training, **não cobre runtime STT/TTS** via Bearer.
3. Tab **Members:** `Managed identity` → **+ Select members** → User-assigned → `mi-helpsphere-ia` (RG `rg-lab-intermediario`) → **Next**
4. **Review + assign** → confirmar role + scope + member → aguarde **~30-60s** até propagação Entra global

<!-- screenshot: cap06-passo6.3-rbac-cognitive-services-user.png -->

> **Alternativa via Azure CLI (Windows PowerShell 7):**
> ```powershell
> $SpchId = az cognitiveservices account show -n spch-helpsphere -g rg-lab-final --query id -o tsv
> $MiPrincipal = az identity show -n mi-helpsphere-ia -g rg-lab-intermediario --query principalId -o tsv
> az role assignment create --assignee "$MiPrincipal" --role "Cognitive Services User" --scope "$SpchId"
> ```
> **Linux/Mac/WSL:** substitua `$Var = az ...` por `VAR=$(az ...)`.

> **Custo:** R$ 0 (RBAC é gratuito).

> **Nota pedagógica — Bearer Entra vs `Ocp-Apim-Subscription-Key`:** Speech aceita 2 formas: (a) header `Ocp-Apim-Subscription-Key` (key estática, legacy), (b) header `Authorization: Bearer <token-AAD>` da MI (curta duração, audit trail por identidade). **(b) é o padrão produção.** Cravamos `Cognitive Services User` agora mesmo que smokes 6.4-6.5 usem (a) por simplicidade — assim, quando o wiring do `func-agent-runner` migrar para Bearer, não é preciso revisitar IAM. Anti-pattern: lab que só ensina key → aluno joga key em `appsettings.json`.

> **Nota pedagógica — `Cognitive Services User` vs `Contributor`:** `User` (runtime) basta para STT/TTS via Bearer; `Contributor` é management plane (criar/deletar resource, rotacionar keys). Custom Voice training exige `Cognitive Services Contributor` adicional sobre datasets. Lab cobra apenas `User` — Contributor amplo demais para identidade de runtime (princípio do menor privilégio).

---

## Passo 6.4 — Smoke STT: gravar áudio próprio + transcrever

### 6.4.a — Gravar áudio em pt-BR

Grave a **sua própria voz** (5-10s) falando: *"Como faço para devolver um produto da Apex Mart?"*. STT é mais convincente quando aluno ouve a própria pergunta transcrita.

| Plataforma | Ferramenta | Comando/Caminho | Conversão necessária? |
|---|---|---|---|
| Windows | Voice Recorder (Iniciar) | salva em `.m4a` por default | **Sim** — `ffmpeg -i input.m4a -ac 1 -ar 16000 -sample_fmt s16 sample-question-pt.wav` |
| macOS | QuickTime → New Audio Recording → Export | salva em `.m4a` | **Sim** — idem ffmpeg |
| Linux/WSL | `arecord -d 8 -f cd -r 16000 -c 1 sample-question-pt.wav` | direto em WAV | Não |

Salve como `sample-question-pt.wav` na pasta `agent-code/` do clone local. `ffmpeg` instala via `winget install ffmpeg` (Windows), `brew install ffmpeg` (macOS), `apt install ffmpeg` (Linux).

> **Atenção formato:** STT REST exige **PCM 16 kHz mono 16-bit**. Áudios `.m4a`/`.mp3` retornam 400 Bad Request `Invalid audio format` — converta antes do smoke.

### 6.4.b — Transcrever via cURL

**No terminal local (Windows PowerShell 7):**

```powershell
# Variáveis (ajuste conforme seu .env)
$SpeechKey = "<KEY-1-do-Passo-6.2>"
$SpeechRegion = "eastus2"

# Smoke STT
# Nota: @ em PowerShell precisa estar entre aspas para evitar splatting operator
$SttResponse = curl.exe -sS -X POST `
  "https://$SpeechRegion.stt.speech.microsoft.com/speech/recognition/conversation/cognitiveservices/v1?language=pt-BR" `
  -H "Ocp-Apim-Subscription-Key: $SpeechKey" `
  -H "Content-Type: audio/wav" `
  --data-binary "@sample-question-pt.wav"

# Parse via PowerShell nativo (sem dependência de jq):
$SttResponse | ConvertFrom-Json

# Alternativa com jq (se instalado via `winget install jqlang.jq`):
# $SttResponse | jq '.'
```

> **Nota:** `jq` requer instalação no Windows. Instale via `winget install jqlang.jq` ou use o fallback PowerShell nativo `ConvertFrom-Json` (aplicado acima).

Saída esperada (campos relevantes):

```json
{
  "RecognitionStatus": "Success",
  "DisplayText": "Como faço para devolver um produto da Apex Mart?",
  "Offset": 1500000,
  "Duration": 38000000
}
```

<!-- screenshot: cap06-passo6.4-stt-curl-success.png -->

> **Alternativa via Portal — Speech Studio Real-time:**
>
> 1. `https://speech.microsoft.com/portal` → fazer login → selecionar resource `spch-helpsphere`
> 2. Menu **Real-time Speech to text** → upload `sample-question-pt.wav` → Language `Portuguese (Brazil)` → **Test**
> 3. Aparece transcrição em painel direito + JSON detalhado em **View output**
> 4. Útil pedagogicamente para **inspeção visual** + waveform — mas o smoke real é via cURL.

> **Custo:** ~R$ 0,02 para 10s de áudio (R$ 5/hora ÷ 360 segmentos de 10s).

> **Nota pedagógica — `RecognitionStatus: NoMatch` com áudio claro:** causa típica é (1) `language=pt-PT` em vez de `pt-BR` (você passou Portugal por engano — sotaque rejeita), (2) áudio com ruído de fundo > 60dB, (3) volume muito baixo (<20% do range). Workaround: confirmar `language=pt-BR` no query string + gravar em ambiente silencioso + falar a 30cm do mic. Anti-pattern: aluno fica trocando código quando o problema é o WAV.

---

## Passo 6.5 — Smoke TTS: gerar MP3 com voice `pt-BR-FranciscaNeural`

**No terminal local (Windows PowerShell 7):**

```powershell
# SSML em here-string literal (single-quoted) — evita interpolação de $ e backticks
$Ssml = @'
<speak version="1.0" xmlns="http://www.w3.org/2001/10/synthesis" xml:lang="pt-BR">
  <voice name="pt-BR-FranciscaNeural">Olá, sou a assistente do HelpSphere. Como posso ajudar você hoje?</voice>
</speak>
'@

curl.exe -sS -X POST "https://$SpeechRegion.tts.speech.microsoft.com/cognitiveservices/v1" `
  -H "Ocp-Apim-Subscription-Key: $SpeechKey" `
  -H "Content-Type: application/ssml+xml" `
  -H "X-Microsoft-OutputFormat: audio-24khz-48kbitrate-mono-mp3" `
  -d $Ssml --output greeting-francisca.mp3

# Reproduzir no Windows: Start-Process greeting-francisca.mp3
# (macOS: `open greeting-francisca.mp3` · Linux: `xdg-open greeting-francisca.mp3`)
```

Você deve ouvir a frase com voz feminina pt-BR neural.

<!-- screenshot: cap06-passo6.5-tts-mp3-generated.png -->

**Smoke opcional — voice masculina com estilo `customerservice`** (troque `pt-BR-FranciscaNeural` por `pt-BR-AntonioNeural` no SSML acima e adicione `xmlns:mstts="https://www.w3.org/2001/mstts"` + wrapper `<mstts:express-as style="customerservice">...</mstts:express-as>` dentro do `<voice>`).

> **Custo:** ~R$ 0,001 por chamada smoke (~80 chars × R$ 16/1M chars). Passo 6.5 inteiro < R$ 0,10.

> **Nota pedagógica — voices Neural vs Custom Neural:** só Neural é comercial (Standard descontinuado em 2024). Custom Neural Voice (30+ min áudio do locutor) custa ~5x mais e exige aprovação **Limited Access** Microsoft (anti-deepfake gate). `pt-BR-FranciscaNeural` é o sweet spot lab: prosódia natural + 7 estilos via `<mstts:express-as>` (`customerservice`, `chat`, `cheerful`, `empathetic`, `newscast`, `narration-relaxed`, `whispering`).

> **Nota pedagógica — output `audio-24khz-mp3` vs `riff-48khz-pcm`:** MP3 24kHz = 6 KB/s, ideal canal voz Copilot/Teams (banda limitada). PCM 48kHz = 96 KB/s, ideal studio quality. Anti-pattern: escolher PCM "porque qualidade" e estourar banda em chamada Teams real. **Default lab: MP3 24kHz mono.**

---

## Passo 6.6 — Endpoint `/api/agent/voice` (opcional · gated)

Em produção integraríamos com **Azure Communication Services** (PSTN streaming bidirecional). No lab demonstramos via HTTP direto — cliente sobe WAV, recebe MP3.

> **Gate:** depende da Function App `func-agent-runner` (provisionada em capítulo posterior do Lab Final). Salve o snippet e volte aqui após a Function App estar deployada.

Adicione o endpoint em `agent-code/function_app.py` (resumido — versão completa no scaffold do repo):

```python
# agent-code/function_app.py — endpoint /api/agent/voice (encadeia STT → agent → TTS)
import os, azure.functions as func, requests
from agent_runner import run_agent, client  # do agente Foundry

app = func.FunctionApp(http_auth_level=func.AuthLevel.FUNCTION)
SPEECH_KEY, SPEECH_REGION = os.environ["SPEECH_KEY"], os.environ["SPEECH_REGION"]

@app.route(route="agent/voice", methods=["POST"])
def voice(req: func.HttpRequest) -> func.HttpResponse:
    audio_bytes = req.get_body()
    if not audio_bytes:
        return func.HttpResponse("Empty body", status_code=400)
    # 1) STT
    stt = requests.post(
        f"https://{SPEECH_REGION}.stt.speech.microsoft.com/speech/recognition/conversation/cognitiveservices/v1?language=pt-BR",
        headers={"Ocp-Apim-Subscription-Key": SPEECH_KEY, "Content-Type": "audio/wav"},
        data=audio_bytes, timeout=30).json()
    transcription = stt.get("DisplayText", "").strip()
    if not transcription:
        return func.HttpResponse(f"STT NoMatch ({stt.get('RecognitionStatus')})", status_code=422)
    # 2) Agent
    thread = client.agents.create_thread()
    response_text = run_agent(thread.id, transcription)
    # 3) TTS (Francisca · customerservice)
    ssml = (f'<speak version="1.0" xmlns="http://www.w3.org/2001/10/synthesis" '
            f'xmlns:mstts="https://www.w3.org/2001/mstts" xml:lang="pt-BR">'
            f'<voice name="pt-BR-FranciscaNeural">'
            f'<mstts:express-as style="customerservice">{response_text}</mstts:express-as>'
            f'</voice></speak>')
    tts = requests.post(
        f"https://{SPEECH_REGION}.tts.speech.microsoft.com/cognitiveservices/v1",
        headers={"Ocp-Apim-Subscription-Key": SPEECH_KEY,
                 "Content-Type": "application/ssml+xml",
                 "X-Microsoft-OutputFormat": "audio-24khz-48kbitrate-mono-mp3"},
        data=ssml.encode("utf-8"), timeout=30)
    return func.HttpResponse(body=tts.content, mimetype="audio/mpeg",
        status_code=tts.status_code,
        headers={"X-Transcription": transcription[:200], "X-Agent-Thread": thread.id})
```

**Smoke end-to-end** após `func azure functionapp publish func-agent-runner --python`:

```powershell
$FuncUrl = az functionapp show -n func-agent-runner -g rg-lab-final --query defaultHostName -o tsv
$FuncKey = az functionapp keys list -n func-agent-runner -g rg-lab-final --query functionKeys.default -o tsv
curl.exe -sS -X POST "https://$FuncUrl/api/agent/voice?code=$FuncKey" `
  -H "Content-Type: audio/wav" --data-binary "@sample-question-pt.wav" `
  --output response-agent.mp3 -D headers.txt
Select-String -Path headers.txt -Pattern 'x-transcription' -CaseSensitive:$false
# Esperado: X-Transcription: <transcrição pt-BR>
```

<!-- screenshot: cap06-passo6.6-endpoint-voice-smoke.png -->

> **Custo:** ~R$ 0,02 por chamada (10s STT + ~150 tokens gpt-4.1-mini + ~100 chars TTS).

> **Nota pedagógica — `X-Transcription` em header, não body:** body é MP3 binário, JSON cabe só via multipart. Headers são canal natural para metadata observável (debug + telemetria). Produção: log `transcription` + `response_text` em App Insights. Anti-pattern: logar áudio inteiro (PII).

---

## Passo 6.7 — Plugar Speech no canal de voz do Copilot Studio

**No Copilot Studio (https://copilotstudio.microsoft.com):**

1. Abra o agente `HelpSphere Tier 1 Agent`
2. Menu lateral → **Settings** → **Voice** (sub-aba)
3. Em **Speech-to-text and text-to-speech provider:** selecione **Azure AI Speech**
4. Preencher:
   - **Resource ID:** `/subscriptions/<sub-id>/resourceGroups/rg-lab-final/providers/Microsoft.CognitiveServices/accounts/spch-helpsphere`
     - Captura via CLI: `az cognitiveservices account show -n spch-helpsphere -g rg-lab-final --query id -o tsv`
   - **Region:** `eastus2`
   - **Default voice:** `pt-BR-FranciscaNeural`
5. Clique **Save**
6. Menu lateral **Channels** → seção **Voice** → **+ Add channel** → **Telephony (preview)** ou **Direct Line Speech**
   - **Telephony:** integração com PSTN via Azure Communication Services (cobrança extra ACS) — fora do escopo lab
   - **Direct Line Speech:** integração SDK para apps mobile/web — usa o Speech resource direto

7. **Test no Voice playground** (canto superior direito do agent → ícone microfone):
   - Botão **Hold to talk** → fale "bom dia" → solte
   - Saudação determinística do agente Copilot Studio deve responder em voz Francisca pt-BR

<!-- screenshot: cap06-passo6.7-copilot-voice-channel.png -->

> [!IMPORTANT] **Tier / Licenciamento**
> Passo 6.7 (canal voice no Copilot Studio) não funciona em conta `live.com` MSA. Veja [`_disclaimers.md`](./_disclaimers.md) **AMB-2**. Speech resource em si funciona em qualquer sub.

> **Custo:** Direct Line Speech é gratuito no Trial; Speech já contado em 6.4-6.5. Telephony via ACS = ~R$ 0,03/min.

> **Nota pedagógica — Direct Line Speech vs Web Chat browser-TTS:** Direct Line encadeia STT + agent + TTS no servidor (1 round-trip, qualidade neural Francisca). Web Chat com `SpeechSynthesisUtterance` browser-side é qualidade ruim — anti-pattern customer-facing. Apex tier 1 sempre Direct Line.

---

## Passo 6.8 — Validação visual final no Speech Studio (TTS playback)

**No Portal Speech Studio (`https://speech.microsoft.com/portal`):**

1. Faça login com a mesma conta Azure → no canto superior direito, garanta que o resource selecionado é `spch-helpsphere` (region `East US 2`, RG `rg-lab-final`)
2. Menu lateral → **Voice Gallery** (ou **Text to speech → Voice gallery**)
3. Buscar **`Francisca`** → clique no card **`pt-BR-FranciscaNeural`** → abre painel **Try it out** (sintetizador interativo)
4. Cole o texto:
   ```
   Olá, sou a assistente do HelpSphere. Como posso ajudar você hoje?
   ```
5. Botão **Play** (ícone ▶ azul) → ouça a frase com voz feminina pt-BR neural — **mesma voz do MP3 gerado no Passo 6.5**
6. (Opcional) Clique no dropdown **Speaking style** → selecione `customerservice` → **Play** novamente — note a entonação mais empática
7. (Opcional) Aba **Audio Content Creation** (menu lateral) → **+ New File** → cole SSML do Passo 6.5 → **Play** → painel direito mostra waveform + duração + size estimado

<!-- screenshot: cap06-passo6.8-speech-studio-playback.png -->

**Por que validar no Speech Studio depois de já ter ouvido o MP3?**

| Validação | O que confirma |
|---|---|
| Smoke cURL TTS (Passo 6.5) | REST endpoint + KEY funcionando + arquivo MP3 baixado OK |
| Playback no MP3 local (Passo 6.5) | Player reproduz arquivo (não é regional/codec issue) |
| **Speech Studio Voice Gallery (este passo)** | **Voice existe no catálogo da SUA region** + qualidade neural percebida + estilos `<mstts:express-as>` disponíveis |

Se Francisca não aparecer no Voice Gallery do recurso (apesar de estar no catálogo global Microsoft), o recurso está em região errada — provisione novo Speech em `eastus2`/`eastus`/`westus3`.

> **Custo:** Speech Studio playback é gratuito até cap diário (~100 sínteses Voice Gallery). Smokes do lab cabem fácil.

> **Nota pedagógica — por que Speech Studio é a validação de fechamento:** smokes cURL provam o **plano técnico** (auth + REST + formato). Speech Studio prova o **plano de produto** (a voz que você ouve é a voz que o cliente final ouvirá no canal Copilot/Teams, com mesma prosódia + mesmos estilos disponíveis). Validação visual fecha a lacuna entre "arquivo gerado" e "experiência percebida".

---

## Validação end-to-end

```powershell
# 1. Speech resource OK + SKU S0
az cognitiveservices account show -n spch-helpsphere -g rg-lab-final `
  --query "{sku:sku.name, region:location, state:properties.provisioningState}" -o table
# Esperado: sku=S0, region=eastus2, state=Succeeded

# 2. Role cravado para MI cross-RG
$SpchId = az cognitiveservices account show -n spch-helpsphere -g rg-lab-final --query id -o tsv
$MiPrincipal = az identity show -n mi-helpsphere-ia -g rg-lab-intermediario --query principalId -o tsv
az role assignment list --assignee $MiPrincipal --scope $SpchId `
  --query "[].roleDefinitionName" -o tsv
# Esperado: Cognitive Services User

# 3. STT smoke (transcrição não-vazia)
$SttCheck = curl.exe -sS -X POST "https://eastus2.stt.speech.microsoft.com/speech/recognition/conversation/cognitiveservices/v1?language=pt-BR" `
  -H "Ocp-Apim-Subscription-Key: $SpeechKey" -H "Content-Type: audio/wav" `
  --data-binary "@sample-question-pt.wav"
($SttCheck | ConvertFrom-Json).DisplayText

# 4. TTS smoke + tamanho > 5 KB
$SsmlCheck = @'
<speak version="1.0" xml:lang="pt-BR"><voice name="pt-BR-FranciscaNeural">teste</voice></speak>
'@
curl.exe -sS -X POST "https://eastus2.tts.speech.microsoft.com/cognitiveservices/v1" `
  -H "Ocp-Apim-Subscription-Key: $SpeechKey" -H "Content-Type: application/ssml+xml" `
  -H "X-Microsoft-OutputFormat: audio-24khz-48kbitrate-mono-mp3" `
  -d $SsmlCheck --output _check.mp3
Get-Item _check.mp3 | Select-Object Name, Length
```

---

## Checklist final

```text
[ ] Recurso spch-helpsphere criado em rg-lab-final region eastus2 SKU S0
[ ] SPEECH_KEY (KEY 1) copiado e cravado em agent-code/.env
[ ] SPEECH_REGION="eastus2" (lowercase, sem espaço/hífen) cravado em .env
[ ] Role "Cognitive Services User" atribuído à MI mi-helpsphere-ia (cross-RG) no scope do Speech
[ ] sample-question-pt.wav gravado em pt-BR (5-10s, formato PCM 16kHz mono)
[ ] STT cURL retornou DisplayText em pt-BR (RecognitionStatus=Success)
[ ] TTS cURL gerou greeting-francisca.mp3 reproduzível com voz feminina pt-BR
[ ] (Opcional) Endpoint /api/agent/voice deployado e smoke end-to-end OK (gated Function App)
[ ] Copilot Studio agent ligado ao Speech resource via Settings → Voice
[ ] Test in Voice playground responde com voice Francisca pt-BR
[ ] Speech Studio Voice Gallery confirma Francisca disponível no resource spch-helpsphere (validação visual final)
```

---

## Surpresas pedagógicas (capturadas em smoke runs)

- ⚠️ **`Cognitive Services Speech User` vs `Cognitive Services User`** — `Speech User` é só para Custom Speech training (datasets/models), **não cobre runtime STT/TTS via Bearer**. Sintoma: 401 Unauthorized mesmo com role atribuído. Fix: usar `Cognitive Services User` (mais amplo).
- ⚠️ **Voice Recorder do Windows salva em `.m4a` — Speech STT REST rejeita** — endpoint `recognition/conversation` aceita só `audio/wav` PCM. Sintoma: 400 Bad Request `Invalid audio format`. Fix: `ffmpeg -i input.m4a -ac 1 -ar 16000 -sample_fmt s16 output.wav`.
- ⚠️ **`SPEECH_REGION` formato — "East US 2" amigável quebra requests** — URL exige `eastus2` lowercase sem espaço. Sintoma: 404 Not Found ou DNS resolve falha. Fix: copiar do header `Location` das Keys and Endpoint, não do display name.
- ⚠️ **`pt-PT` vs `pt-BR` — sotaque Portugal vs Brasil rejeita** — endpoint aceita ambos mas cross-locale falha. Sintoma: `RecognitionStatus: NoMatch` ou transcrição com prosódia errada. Fix: cravar `language=pt-BR` no query + `xml:lang="pt-BR"` no SSML.
- ⚠️ **Voice neural nova fora do catálogo eastus2** — voices novas (`pt-BR-ThalitaNeural`) chegam primeiro em `eastus`/`westus3`/`francecentral`. Sintoma: TTS 400 `Voice not supported in region`. Fix: validar `learn.microsoft.com/azure/ai-services/speech-service/regions` antes de cravar voice em SSML produção.
- ⚠️ **Output format `riff-*` quebra playback** — `riff-24khz-16bit-mono-pcm` é PCM cru, não MP3. Sintoma: `.mp3` não toca em WMP/VLC. Fix: usar `audio-24khz-48kbitrate-mono-mp3` para MP3 real ou trocar extensão para `.wav` se PCM.
- ⚠️ **Latência TTS streaming vs batch — 1.5s vs 0.4s** — cURL `--output file.mp3` faz batch (espera response completo); SDK streaming retorna chunks 50-100ms desde primeiro byte. Para SLA <300ms first-audio-byte, **obrigatório SDK streaming**. Lab aceita batch porque smokes não medem first-audio.
- ⚠️ **`<mstts:express-as>` sem namespace é ignorado silenciosamente** — esquecer `xmlns:mstts="https://www.w3.org/2001/mstts"` no `<speak>` faz Speech voltar para tom neutro sem warning. Sintoma: voice sai sem `customerservice`/`cheerful`. Fix: cravar template SSML com namespace no scaffold.
- ⚠️ **F0 tier cap de 5h STT/mês esgota em smoke testing repetido** — F0 dá 5h STT/mês + 0,5M chars TTS/mês gratuitos por sub (1 unidade só). Dev rodando 30 smokes de 10s/dia consome 5h em ~10 dias e o 6º smoke retorna 429 `QuotaExceeded` no meio da aula. Workaround lab: S0 desde o início (R$ 4-6 total) ou cravar `az cognitiveservices account list-usage` em monitoring para alertar 80% antes de estourar.
- ⚠️ **Latência neural vs standard ~3x mais lenta** — `pt-BR-FranciscaNeural` (neural) gera 80 chars em ~400ms; voices standard legacy faziam o mesmo em ~120ms. Para SLA <300ms first-audio-byte em agent conversacional, **obrigatório SDK streaming** (chunks 50-100ms) em vez de batch cURL `--output file.mp3`. Anti-pattern: prometer "tempo real" usando batch REST — UX percebe lag.
- ⚠️ **Speech key é region-locked silenciosamente** — KEY 1 emitida para resource em `eastus2` NÃO funciona se você chamar `https://brazilsouth.tts.speech.microsoft.com` por engano. Sintoma: 401 Unauthorized (não "wrong region"). Fix: confirmar `SPEECH_REGION` no `.env` bate exatamente com a region do resource criado. Provisionar Speech na mesma region do Foundry/AOAI evita cross-region troubleshooting.

---

## Troubleshooting rápido

| Sintoma | Causa provável | Fix |
|---|---|---|
| `401 Unauthorized` no STT/TTS | KEY 1 inválida ou typo (espaço final) | Re-copiar via botão Copy do Portal; se não resolver, regenerar KEY 1 |
| `404 Not Found` no endpoint REST | `SPEECH_REGION` malformado ("East US 2" em vez de `eastus2`) | Trocar para `eastus2` lowercase sem espaço |
| `RecognitionStatus: NoMatch` com áudio claro | `language=pt-PT` por engano OU áudio muito baixo | Forçar `language=pt-BR` + gravar mais perto do mic |
| `400 Bad Request: Invalid audio format` | Áudio em `.m4a`/`.mp3` enviado para STT | Converter para WAV PCM 16kHz mono via ffmpeg |
| `Voice 'X' is not supported in region 'eastus2'` no TTS | Voice nova ainda não disponível na região | Trocar voice ou trocar Speech resource para `eastus`/`westus3` |
| Copilot Studio Voice tab não aparece | Trial Power Platform expirado OR conta `live.com` (ver AMB-2 em [`_disclaimers.md`](./_disclaimers.md)) | Renovar trial OR migrar para tenant M365 dev |
| MP3 gerado mas player não reproduz | Output format `riff-*` em vez de `audio-*-mp3` | Trocar header `X-Microsoft-OutputFormat` para `audio-24khz-48kbitrate-mono-mp3` |
| `403 Forbidden` ao chamar via Bearer Entra MI | Role assignment ainda propagando (<60s) ou role errado | Aguardar 1min + confirmar role = `Cognitive Services User` (não Speech User) |

---

## Próximo capítulo

[07 — n8n Escalation](./07-n8n-escalation.md)
