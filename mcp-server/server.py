"""HelpSphere MCP Server — FastMCP + SQL backend.

Expõe 4 tools sobre o SQL Database `helpsphere` (stack apex-helpsphere SaaS):
    - get_ticket(ticket_id)
    - list_tickets(status, limit, category)
    - add_comment(ticket_id, comment, author)
    - update_status(ticket_id, new_status)

+ 1 resource `helpsphere://tickets/{ticket_id}`.

# ─────────────────────────────────────────────────────────────────────────────
# AUTH JWT DESABILITADO TEMPORARIAMENTE (bug #13 — FastMCP v2 Context API)
# ─────────────────────────────────────────────────────────────────────────────
# O decorator `@require_scope` (auth.py) lia o Bearer token via parâmetro
# `ctx: dict` injetado pelo FastMCP. A partir do FastMCP v2+ esse contrato
# mudou: agora o framework injeta um objeto `Context` (não mais dict), e o
# wrapper antigo retorna "missing bearer token" mesmo com token válido.
#
# Decisão pedagógica para o Lab Final (D06): desabilitar `@require_scope` nas
# 4 tools para destravar a gravação ao vivo. O lab demonstra integração
# MCP + Agent + RAG + Speech + Service Bus + n8n — auth JWT no app code não
# é o foco didático.
#
# Em produção real, JWT validation acontece em camada ANTES do MCP:
#   - APIM gateway (Lab Avançado / Bloco 5/6) com policy `validate-jwt`
#   - Azure Front Door com WAF + Easy Auth
#   - Container Apps Built-in Auth (`microsoft` provider)
# O app code recebe requests já autenticados — princípio "auth no edge".
#
# Tech debt formalizado: Story 06.30 (reativar @require_scope após refactor
# para FastMCP v2 Context API). `auth.py` mantido intacto para retomada.
# ─────────────────────────────────────────────────────────────────────────────

Uso:
    pip install -r requirements.txt
    $env:HELPSPHERE_SQL_CONNECTION = "Driver={ODBC Driver 18 for SQL Server};Server=tcp:...;Database=helpsphere;..."
    python server.py   # listen 0.0.0.0:8080
"""
from __future__ import annotations

import logging
import os

from fastmcp import FastMCP

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
def get_ticket(ticket_id: int) -> dict:
    """Recupera dados completos de um ticket pelo ID."""
    return db.get_ticket(ticket_id)


@mcp.tool()
def list_tickets(status: str = "Open", limit: int = 10, category: str | None = None) -> list[dict]:
    """Lista tickets filtrando por status e opcionalmente categoria."""
    return db.list_tickets(status=status, limit=limit, category=category)


@mcp.tool()
def add_comment(ticket_id: int, comment: str, author: str) -> dict:
    """Adiciona comentário a um ticket."""
    return db.add_comment(ticket_id, comment, author)


@mcp.tool()
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
