"""HelpSphere MCP Server — v0.1.0-init skeleton.

Cravado pela Story 06.11 Bloco B. Tool stub `search_helpsphere_kb` apenas;
implementação real chamando AI Search (apex-rag-lab) virá em capítulo 05.

Spec MCP: https://modelcontextprotocol.io/

Uso:
    python server.py     # listen 0.0.0.0:8080
"""

from __future__ import annotations

import logging
import os
from typing import Any

# MCP SDK imports — placeholder. Real wiring com mcp.server.lowlevel.Server
# vai ser cravado no capítulo 05.
try:
    from mcp.server.lowlevel import Server
    from mcp.server.stdio import stdio_server
except ImportError:
    Server = None
    stdio_server = None

logging.basicConfig(level=logging.INFO)
log = logging.getLogger("mcp-helpsphere")


def search_helpsphere_kb(query: str, top_k: int = 3) -> dict[str, Any]:
    """Busca conhecimento no índice AI Search do apex-rag-lab.

    Implementação real (cap 05):
        - Autenticar via DefaultAzureCredential (MI no ACA)
        - Chamar SearchClient.search() com query + select=['content', 'source', 'page']
        - Retornar top_k chunks com citação

    Por enquanto, retorna placeholder.
    """
    log.info("search_helpsphere_kb chamado: query=%r top_k=%d", query, top_k)
    return {
        "tool": "search_helpsphere_kb",
        "query": query,
        "top_k": top_k,
        "status": "placeholder",
        "results": [
            {
                "content": "Implementação real virá em docs/05-mcp-server-deploy.md",
                "source": "TBD",
                "page": 0,
                "score": 0.0,
            }
        ],
    }


def main() -> None:
    """Entrypoint MCP Server.

    Skeleton: apenas log + smoke da tool. Capítulo 05 vai cravar wiring real
    com mcp.server.lowlevel.Server + transport stdio ou SSE.
    """
    log.info("MCP Server HelpSphere v0.1.0-init iniciando...")
    log.info("AI_SEARCH_ENDPOINT=%s", os.getenv("AI_SEARCH_ENDPOINT", "MISSING"))
    log.info("AI_SEARCH_INDEX=%s", os.getenv("AI_SEARCH_INDEX", "apex-rag-lab-index"))

    # Smoke da tool
    result = search_helpsphere_kb("devolução de pedido", top_k=2)
    log.info("Smoke search_helpsphere_kb: %s", result)

    log.info("Server skeleton pronto. Implementação real: docs/05-mcp-server-deploy.md")
    log.info("Para rodar como MCP server real, descomente o stdio_server() abaixo após cap 05.")
    # asyncio.run(stdio_server(...))  # cravado no capítulo 05


if __name__ == "__main__":
    main()
