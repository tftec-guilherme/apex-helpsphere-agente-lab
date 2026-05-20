"""Wrapper SQL HelpSphere — operações usadas pelas 4 tools MCP.

Lê `HELPSPHERE_SQL_CONNECTION` do env (ODBC connection string apontando para
o SQL Database `helpsphere` do stack apex-helpsphere SaaS).

Autenticação Azure SQL via Managed Identity
-------------------------------------------
Connection string **NÃO usa mais** `Authentication=ActiveDirectoryMsi` nem
`UID=`. Em vez disso, o token AAD é obtido via `azure-identity`
(`ManagedIdentityCredential`) e injetado no pyodbc via `attrs_before` usando
o atributo `SQL_COPT_SS_ACCESS_TOKEN` (1256).

**Por quê:** o ODBC Driver 18 com `Authentication=ActiveDirectoryMsi` chama
o endpoint IMDS de VM (`169.254.169.254`) hardcoded — esse endpoint **não
existe em Azure Container Apps**, que expõe MI via `IDENTITY_ENDPOINT` /
`IDENTITY_HEADER`. `ActiveDirectoryDefault` também não é aceito pelo driver
("Invalid value"). Este é o **pattern oficial Microsoft** para Container
Apps + Azure SQL + Managed Identity.

**Env var `AZURE_CLIENT_ID`** (opcional): só necessária quando o Container
App tem System-assigned + User-assigned MI simultaneamente, ou múltiplas
User-assigned MIs. Especifica qual MI usar para obter o token. Quando ausente,
o `ManagedIdentityCredential` usa a única identity disponível.

Connection string esperada (sem `Authentication=` nem `UID=`):
    Driver={ODBC Driver 18 for SQL Server};Server=tcp:<srv>.database.windows.net,1433;Database=helpsphere;Encrypt=yes;TrustServerCertificate=no;Connection Timeout=30;
"""
from __future__ import annotations

import logging
import os
import struct

import pyodbc
from azure.identity import ManagedIdentityCredential

log = logging.getLogger("helpsphere-db")

# Atributo pyodbc para injetar access token AAD (SQL_COPT_SS_ACCESS_TOKEN)
_SQL_COPT_SS_ACCESS_TOKEN = 1256
_AZURE_SQL_SCOPE = "https://database.windows.net/.default"


class HelpSphereDB:
    """Wrapper minimal para tickets/comments do HelpSphere."""

    def __init__(self, connection_string: str):
        self.connection_string = connection_string
        # Cache do credential — evita recriar a cada conexão. O próprio
        # ManagedIdentityCredential cacheia tokens internamente e renova
        # automaticamente quando próximos do vencimento.
        client_id = os.environ.get("AZURE_CLIENT_ID")
        if client_id:
            self._credential = ManagedIdentityCredential(client_id=client_id)
        else:
            self._credential = ManagedIdentityCredential()

    def _conn(self):
        """Abre conexão pyodbc autenticada via access token AAD (MI)."""
        token = self._credential.get_token(_AZURE_SQL_SCOPE).token
        # Token precisa ser UTF-16-LE com prefix de length (formato exigido
        # pelo driver ODBC para SQL_COPT_SS_ACCESS_TOKEN).
        token_bytes = token.encode("utf-16-le")
        token_struct = struct.pack(f"<I{len(token_bytes)}s", len(token_bytes), token_bytes)
        return pyodbc.connect(
            self.connection_string,
            attrs_before={_SQL_COPT_SS_ACCESS_TOKEN: token_struct},
        )

    def get_ticket(self, ticket_id: int) -> dict:
        """Retorna ticket por ID com colunas básicas."""
        with self._conn() as cnx:
            cur = cnx.cursor()
            cur.execute(
                "SELECT id, title, status, category, priority, description, created_at "
                "FROM tickets WHERE id = ?",
                ticket_id,
            )
            row = cur.fetchone()
            if not row:
                return {"error": "not_found", "ticket_id": ticket_id}
            return {
                "id": row[0],
                "title": row[1],
                "status": row[2],
                "category": row[3],
                "priority": row[4],
                "description": row[5],
                "created_at": str(row[6]),
            }

    def list_tickets(
        self,
        status: str = "Open",
        limit: int = 10,
        category: str | None = None,
    ) -> list[dict]:
        """Lista tickets filtrando por status (e opcionalmente categoria)."""
        query = (
            "SELECT TOP (?) id, title, status, category, priority, created_at "
            "FROM tickets WHERE status = ?"
        )
        params: list = [limit, status]
        if category:
            query += " AND category = ?"
            params.append(category)
        query += " ORDER BY created_at DESC"
        with self._conn() as cnx:
            cur = cnx.cursor()
            cur.execute(query, *params)
            return [
                {
                    "id": r[0],
                    "title": r[1],
                    "status": r[2],
                    "category": r[3],
                    "priority": r[4],
                    "created_at": str(r[5]),
                }
                for r in cur.fetchall()
            ]

    def add_comment(self, ticket_id: int, comment: str, author: str) -> dict:
        """Adiciona comentário ao ticket."""
        with self._conn() as cnx:
            cur = cnx.cursor()
            cur.execute(
                "INSERT INTO comments (ticket_id, author, content, created_at) "
                "VALUES (?, ?, ?, SYSUTCDATETIME())",
                ticket_id, author, comment,
            )
            cnx.commit()
            log.info("comment adicionado: ticket=%d author=%s", ticket_id, author)
            return {"ok": True, "ticket_id": ticket_id}

    def update_status(self, ticket_id: int, new_status: str) -> dict:
        """Atualiza status. Status válidos: Open, InProgress, Resolved, Escalated."""
        valid = {"Open", "InProgress", "Resolved", "Escalated"}
        if new_status not in valid:
            return {"error": f"invalid_status: {new_status}", "valid": list(valid)}
        with self._conn() as cnx:
            cur = cnx.cursor()
            cur.execute(
                "UPDATE tickets SET status = ?, updated_at = SYSUTCDATETIME() "
                "WHERE id = ?",
                new_status, ticket_id,
            )
            cnx.commit()
            return {"ok": True, "ticket_id": ticket_id, "new_status": new_status}
