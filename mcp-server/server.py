"""HelpSphere MCP Server — FastMCP + Entra OAuth + SQL backend.

Expõe 4 tools sobre o SQL Database `helpsphere` (stack apex-helpsphere SaaS):
    - get_ticket(ticket_id)
    - list_tickets(status, limit, category)
    - add_comment(ticket_id, comment, author)
    - update_status(ticket_id, new_status)

+ 1 resource `helpsphere://tickets/{ticket_id}`.

Auth via decorator `@require_scope` (auth.py) lendo Bearer token do contexto MCP.

Uso:
    pip install -r requirements.txt
    $env:HELPSPHERE_SQL_CONNECTION = "Driver={ODBC Driver 18 for SQL Server};Server=tcp:...;Database=helpsphere;..."
    $env:AZURE_TENANT_ID = "<tenant>"
    $env:EXPECTED_AUDIENCE = "api://<server-app-client-id>"
    python server.py   # listen 0.0.0.0:8080
"""
from __future__ import annotations

import logging
import os

from fastmcp import FastMCP

from auth import require_scope
from helpsphere_db import HelpSphereDB

logging.basicConfig(level=logging.INFO)
log = logging.getLogger("mcp-helpsphere")

# Stateless HTTP via env var FASTMCP_STATELESS_HTTP=true (setada no Container App).
# Necessário porque ACA usa min-replicas=0 (scale-to-zero) e session in-memory do
# FastMCP morre entre requests. FastMCP atual (v2+) removeu o kwarg stateless_http
# do construtor — agora vive em env var OU em run_http_async()/http_app().
mcp = FastMCP("helpsphere")
db = HelpSphereDB(os.environ["HELPSPHERE_SQL_CONNECTION"])


@mcp.tool()
@require_scope("helpsphere.tickets.read")
def get_ticket(ticket_id: int) -> dict:
    """Recupera dados completos de um ticket pelo ID."""
    return db.get_ticket(ticket_id)


@mcp.tool()
@require_scope("helpsphere.tickets.read")
def list_tickets(status: str = "Open", limit: int = 10, category: str | None = None) -> list[dict]:
    """Lista tickets filtrando por status e opcionalmente categoria."""
    return db.list_tickets(status=status, limit=limit, category=category)


@mcp.tool()
@require_scope("helpsphere.tickets.write")
def add_comment(ticket_id: int, comment: str, author: str) -> dict:
    """Adiciona comentário a um ticket."""
    return db.add_comment(ticket_id, comment, author)


@mcp.tool()
@require_scope("helpsphere.tickets.write")
def update_status(ticket_id: int, new_status: str) -> dict:
    """Atualiza status do ticket. Válidos: Open, InProgress, Resolved, Escalated."""
    return db.update_status(ticket_id, new_status)


@mcp.resource("helpsphere://tickets/{ticket_id}")
def ticket_resource(ticket_id: int) -> str:
    """Retorna ticket formatado como recurso MCP.

    TODO(student): customize a formatação para incluir mais contexto além
    do dict cru — sugestões:
      - Incluir últimos N comentários (helpsphere_db.list_comments(ticket_id))
      - Adicionar SLA metadata (deadline esperado por priority)
      - Formatar como Markdown ao invés de str(dict)
    """
    ticket = db.get_ticket(ticket_id)
    return str(ticket)


if __name__ == "__main__":
    log.info("MCP Server HelpSphere iniciando em 0.0.0.0:8080")
    mcp.run(transport="http", host="0.0.0.0", port=8080)
