"""HelpSphere Foundry Agent — minimal skeleton (v0.1.0-init).

Cravado pela Story 06.11 Bloco B. Implementação real das 4 tools virá em pass
posterior (capítulos 04-08 Portal step-by-step).

Pré-requisitos:
    - AI Foundry Project provisionado (cap 04)
    - gpt-4.1-mini deployment ativo (cap 04)
    - .env com PROJECT_CONNECTION_STRING + MODEL_DEPLOYMENT_NAME

Uso:
    python agent.py
"""

from __future__ import annotations

import argparse
import os
from typing import Any

from azure.ai.projects import AIProjectClient
from azure.identity import DefaultAzureCredential

# === DEMO PROMPT (recording determinístico) ===
# Âncora pedagógica usada na gravação ao vivo do Capítulo 04 (Foundry Agent SDK).
# NÃO é teste automatizado — é um prompt cravado para garantir reprodutibilidade
# do output durante o recording: mesmo cenário, mesmas tools acionadas, mesmas
# keywords esperadas na resposta. Permite que o aluno (e o professor) consigam
# reproduzir a demo sem improviso e validem visualmente que o agente acionou
# search_kb + (eventualmente) escalate_ticket no caminho esperado.
#
# Cenário HelpSphere (service desk B2B): cliente XPTO (lojista) reporta latência
# alta no portal nas últimas 2 horas. O agente tier 1 deve consultar runbooks de
# observabilidade, propor roteiro de diagnóstico e abrir ticket de incidente
# via Service Bus se a sintomatologia exigir escalação para tier 2.
DEMO_PROMPT_INPUT: str = (
    "Cliente XPTO (lojista B2B Apex HelpSphere) está reportando latência alta "
    "no portal nas últimas 2 horas — checkout demorando >8s e timeouts "
    "intermitentes ao consultar pedidos. Liste, em ordem, a sequência de "
    "ações que você deve tomar para: (1) diagnosticar a causa-raiz consultando "
    "Application Insights e a base de runbooks corporativa, (2) recuperar o "
    "histórico de tickets similares já resolvidos, e (3) abrir um ticket de "
    "incidente no Service Bus topic 'ticket-escalations' caso a confiança da "
    "resposta automática seja inferior a 0.5 ou o caso envolva degradação "
    "ativa de produção. Cite as fontes consultadas."
)

# Keywords/tópicos que o output do agente DEVE conter para o smoke pós-execução
# considerar a demo "PASS pedagógico". Não é assertion estrita — é um checklist
# visual que o professor confere durante o recording.
DEMO_PROMPT_EXPECTED_KEYS: list[str] = [
    "service desk",
    "Application Insights",
    "runbook",
    "search_kb",
    "list_similar_tickets",
    "Service Bus",
    "ticket-escalations",
    "escalate_ticket",
    "confidence",
    "tier 2",
]


def get_project_client() -> AIProjectClient:
    """Conecta no AI Foundry Project via DefaultAzureCredential."""
    conn_str = os.getenv("PROJECT_CONNECTION_STRING")
    if not conn_str:
        raise RuntimeError(
            "PROJECT_CONNECTION_STRING não definido. "
            "Veja docs/04-foundry-agent-sdk.md step 4."
        )
    return AIProjectClient.from_connection_string(
        credential=DefaultAzureCredential(),
        conn_str=conn_str,
    )


# ----- Tool placeholders (implementação real virá em capítulos 05-08) -----


def search_kb(query: str) -> dict[str, Any]:
    """Busca conhecimento via MCP Server → AI Search (apex-rag-lab).

    Implementação real: capítulo 05 (MCP Server deploy).
    """
    return {
        "tool": "search_kb",
        "query": query,
        "status": "placeholder",
        "result": "Implementação real virá em docs/05-mcp-server-deploy.md",
    }


def classify_intent(text: str) -> dict[str, Any]:
    """Classifica intent do ticket (severity + category).

    Implementação real: usa gpt-4.1-mini com few-shot prompts em pt-BR.
    """
    return {
        "tool": "classify_intent",
        "text": text,
        "status": "placeholder",
        "severity": "TBD",
        "category": "TBD",
    }


def estimate_confidence(answer: str, sources: list[str]) -> dict[str, Any]:
    """Estima confiança da resposta com base em sources retornados.

    Implementação real: heuristic + grounding score.
    """
    return {
        "tool": "estimate_confidence",
        "answer_preview": answer[:80],
        "sources_count": len(sources),
        "status": "placeholder",
        "confidence": 0.0,
    }


def escalate_servicebus(ticket: dict[str, Any]) -> dict[str, Any]:
    """Escala ticket crítico via Service Bus topic 'escalations'.

    Implementação real: capítulo 08 (Service Bus + n8n).
    """
    return {
        "tool": "escalate_servicebus",
        "ticket_id": ticket.get("id", "unknown"),
        "status": "placeholder",
        "message": "Implementação real virá em docs/08-service-bus-google-sheets.md",
    }


# ----- Agent factory -----


def create_agent_with_tools() -> dict[str, Any]:
    """Cria agente HelpSphere no Foundry Project com 4 tools.

    Implementação real: registrar tools via Foundry Agent Service API,
    plugar MCP Server endpoint (cap 05), e cravar instructions em pt-BR.
    """
    deployment = os.getenv("MODEL_DEPLOYMENT_NAME", "gpt-4.1-mini")
    return {
        "agent_name": "helpsphere-agent-v0.1",
        "model_deployment": deployment,
        "tools": ["search_kb", "classify_intent", "estimate_confidence", "escalate_servicebus"],
        "status": "placeholder",
        "next_step": "Implementação real virá em docs/04-foundry-agent-sdk.md step 6",
    }


def smoke_run() -> None:
    """Smoke run mínimo — valida imports + env + tool placeholders."""
    print("[smoke] Validando imports...")
    print(f"[smoke] AIProjectClient: {AIProjectClient.__name__}")
    print(f"[smoke] DefaultAzureCredential: {DefaultAzureCredential.__name__}")

    print("\n[smoke] Validando env vars...")
    print(f"  PROJECT_CONNECTION_STRING: {'SET' if os.getenv('PROJECT_CONNECTION_STRING') else 'MISSING'}")
    print(f"  MODEL_DEPLOYMENT_NAME: {os.getenv('MODEL_DEPLOYMENT_NAME', 'gpt-4.1-mini (default)')}")

    print("\n[smoke] Tool placeholders:")
    print(f"  search_kb('devolução'): {search_kb('devolução')}")
    print(f"  classify_intent('SAP integração falhou'): {classify_intent('SAP integração falhou')}")
    print(f"  estimate_confidence(...): {estimate_confidence('resposta', ['s1', 's2'])}")
    print(f"  escalate_servicebus({{id: 'T-123'}}): {escalate_servicebus({'id': 'T-123'})}")

    print("\n[smoke] Agent factory:")
    print(f"  create_agent_with_tools(): {create_agent_with_tools()}")

    print("\n[smoke] OK — skeleton funcional. Implementação real: docs/04-foundry-agent-sdk.md")


def run_demo() -> None:
    """Executa o prompt determinístico do recording (Capítulo 04).

    No skeleton v0.1.0-init este método apenas imprime o prompt + keywords
    esperadas e dispara o smoke_run() para validar imports/env. Quando o
    handler real do agente (cap 04 Passo 4.6) estiver cravado em
    agent_runner.py, esta função será expandida para invocar
    `client.agents.create_and_process_run` com DEMO_PROMPT_INPUT como
    user message e validar se as DEMO_PROMPT_EXPECTED_KEYS aparecem na
    resposta final do agente.
    """
    print("=" * 72)
    print("[demo] Capítulo 04 — Foundry Agent SDK (recording determinístico)")
    print("=" * 72)
    print("\n[demo] DEMO_PROMPT_INPUT:")
    print(f"  {DEMO_PROMPT_INPUT}\n")
    print("[demo] DEMO_PROMPT_EXPECTED_KEYS (checklist pós-resposta):")
    for key in DEMO_PROMPT_EXPECTED_KEYS:
        print(f"  - {key}")
    print("\n[demo] Disparando smoke_run() para validar ambiente...\n")
    smoke_run()
    print("\n[demo] Próximo passo: implementar agent_runner.py (cap 04 Passo 4.6)")
    print("[demo] e plugar DEMO_PROMPT_INPUT como user message no run_agent().")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="HelpSphere Foundry Agent skeleton (cap 04 PILOTO)."
    )
    parser.add_argument(
        "--demo",
        action="store_true",
        help="Executa o prompt determinístico cravado para o recording do Capítulo 04.",
    )
    args = parser.parse_args()

    if args.demo:
        run_demo()
    else:
        smoke_run()
