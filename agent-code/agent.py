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

import os
from typing import Any

from azure.ai.projects import AIProjectClient
from azure.identity import DefaultAzureCredential


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


if __name__ == "__main__":
    smoke_run()
