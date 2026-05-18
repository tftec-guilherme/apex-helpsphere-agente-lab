"""Wrapper SQL HelpSphere — operações usadas pelas 4 tools MCP.

Lê `HELPSPHERE_SQL_CONNECTION` do env (ODBC connection string apontando para
o SQL Database `helpsphere` do stack apex-helpsphere SaaS).
"""
from __future__ import annotations

import logging

import pyodbc

log = logging.getLogger("helpsphere-db")


class HelpSphereDB:
    """Wrapper minimal para tickets/comments do HelpSphere."""

    def __init__(self, connection_string: str):
        self.connection_string = connection_string

    def _conn(self):
        return pyodbc.connect(self.connection_string)

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
