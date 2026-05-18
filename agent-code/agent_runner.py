"""Handlers das 4 tools do helpsphere-tier1-agent + event loop `run_agent`.

Função `run_agent(thread_id, user_message)` é chamada pelo wrapper HTTP em
`func-agent-runner/function_app.py` (Passo 3.6).

Cada tool handler implementa a lógica REAL chamando:
    - search_kb     → HTTP POST RAG Function App (Lab Intermediário)
    - get_ticket    → HTTP POST MCP Server (Parte 4)
    - list_similar  → HTTP POST MCP Server
    - escalate      → Service Bus topic (Parte 7)
"""
from __future__ import annotations

import json
import logging
import os

import requests
from azure.ai.projects import AIProjectClient
from azure.identity import DefaultAzureCredential
from azure.servicebus import ServiceBusClient, ServiceBusMessage

logging.basicConfig(level=logging.INFO)
log = logging.getLogger("agent_runner")

RAG_FUNCTION_URL = os.environ["RAG_FUNCTION_URL"]
RAG_FUNCTION_KEY = os.environ["RAG_FUNCTION_KEY"]
MCP_SERVER_URL = os.environ["MCP_SERVER_URL"]
MCP_TOKEN = os.environ.get("MCP_TOKEN", "")
SERVICE_BUS_CONN = os.environ.get("SERVICE_BUS_CONNECTION", "")
AGENT_ID = os.environ["AGENT_ID"]

client = AIProjectClient.from_connection_string(
    credential=DefaultAzureCredential(),
    conn_str=os.environ["AI_PROJECT_CONNECTION_STRING"],
)

# TODO(student): ajuste este threshold conforme a criatividade pedagógica.
# 0.5 é a baseline; abaixo deste valor o agente escala automaticamente.
# Considere:
#   - 0.3 = agente confia mais em si (escala menos, risco de resposta ruim)
#   - 0.7 = agente cético (escala mais, custo maior em tier 2)
# Discuta com a turma qual valor faz sentido para a HelpSphere fictícia.
ESCALATION_THRESHOLD = 0.5


def tool_search_kb(query: str, ticket_id: str | None = None) -> dict:
    """Chama Function App RAG do Lab Intermediário."""
    log.info("tool_search_kb: query=%r ticket_id=%r", query, ticket_id)
    resp = requests.post(
        f"{RAG_FUNCTION_URL}/api/search",
        params={"code": RAG_FUNCTION_KEY},
        json={"query": query, "ticket_id": ticket_id},
        timeout=30,
    )
    resp.raise_for_status()
    return resp.json()


def tool_get_ticket(ticket_id: int) -> dict:
    """Chama MCP Server (Parte 4) para buscar ticket por ID."""
    log.info("tool_get_ticket: ticket_id=%d", ticket_id)
    resp = requests.post(
        f"{MCP_SERVER_URL}/tools/get_ticket",
        headers={"Authorization": f"Bearer {MCP_TOKEN}"},
        json={"ticket_id": ticket_id},
        timeout=15,
    )
    resp.raise_for_status()
    return resp.json()


def tool_list_similar(category: str, limit: int = 5) -> list[dict]:
    """Lista tickets resolvidos da mesma categoria via MCP."""
    log.info("tool_list_similar: category=%r limit=%d", category, limit)
    resp = requests.post(
        f"{MCP_SERVER_URL}/tools/list_tickets",
        headers={"Authorization": f"Bearer {MCP_TOKEN}"},
        json={"category": category, "limit": limit, "status": "Resolved"},
        timeout=15,
    )
    resp.raise_for_status()
    return resp.json()


def tool_escalate(ticket_id: int, reason: str, confidence: float) -> dict:
    """Dispara workflow n8n via Service Bus topic `escalations` (Parte 7)."""
    log.info(
        "tool_escalate: ticket_id=%d reason=%r confidence=%.2f",
        ticket_id, reason, confidence,
    )
    if not SERVICE_BUS_CONN:
        log.warning("SERVICE_BUS_CONNECTION ausente — escalation sem dispatch")
        return {"escalated": False, "reason": "service_bus_not_configured"}
    with ServiceBusClient.from_connection_string(SERVICE_BUS_CONN) as sb:
        sender = sb.get_topic_sender(topic_name="escalations")
        with sender:
            payload = {
                "ticket_id": ticket_id,
                "reason": reason,
                "confidence": confidence,
                "severity": "HIGH" if confidence < ESCALATION_THRESHOLD else "MEDIUM",
            }
            sender.send_messages(ServiceBusMessage(json.dumps(payload)))
    return {"escalated": True, "ticket_id": ticket_id}


TOOL_DISPATCH = {
    "search_kb": tool_search_kb,
    "get_ticket": tool_get_ticket,
    "list_similar_tickets": tool_list_similar,
    "escalate_ticket": tool_escalate,
}


def run_agent(thread_id: str, user_message: str) -> str:
    """Roda 1 turno completo do agente Foundry.

    1. Adiciona `user_message` no thread
    2. Cria run, polleia até completion
    3. Despacha `tool_calls` para handlers locais
    4. Submete `tool_outputs` de volta ao Foundry
    5. Retorna última resposta do assistant
    """
    log.info("run_agent: thread_id=%s message=%r", thread_id, user_message[:80])

    client.agents.create_message(
        thread_id=thread_id,
        role="user",
        content=user_message,
    )
    run = client.agents.create_run(thread_id=thread_id, assistant_id=AGENT_ID)

    while run.status in ("queued", "in_progress", "requires_action"):
        if run.status == "requires_action":
            tool_outputs = []
            for tool_call in run.required_action.submit_tool_outputs.tool_calls:
                fn_name = tool_call.function.name
                args = json.loads(tool_call.function.arguments)
                handler = TOOL_DISPATCH.get(fn_name)
                if handler is None:
                    output = {"error": f"unknown_tool: {fn_name}"}
                else:
                    try:
                        output = handler(**args)
                    except Exception as exc:
                        log.exception("Tool %s falhou", fn_name)
                        output = {"error": str(exc)}
                tool_outputs.append({
                    "tool_call_id": tool_call.id,
                    "output": json.dumps(output),
                })
            run = client.agents.submit_tool_outputs(
                thread_id=thread_id, run_id=run.id, tool_outputs=tool_outputs,
            )
        else:
            run = client.agents.get_run(thread_id=thread_id, run_id=run.id)

    messages = client.agents.list_messages(thread_id=thread_id, order="desc", limit=1)
    if messages.data:
        return messages.data[0].content[0].text.value
    return "(sem resposta)"


if __name__ == "__main__":
    # Smoke local — exige AGENT_ID em env + thread criada previamente
    thread = client.agents.create_thread()
    print(f"Thread criada: {thread.id}")
    resposta = run_agent(thread.id, "Como configuro MFA para um usuário novo?")
    print(f"Agent: {resposta}")
