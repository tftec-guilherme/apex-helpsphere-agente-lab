"""Validação de tokens Entra ID + decorator `@require_scope` para tools MCP.

# ─────────────────────────────────────────────────────────────────────────────
# MÓDULO DESATIVADO — ver server.py + Story 06.30
# ─────────────────────────────────────────────────────────────────────────────
# Este módulo NÃO está em uso no Lab Final (D06). O `server.py` removeu o
# `from auth import require_scope` e o decorator `@require_scope("...")` das 4
# tools porque o contrato do FastMCP v2+ mudou (Context object em vez de dict
# `ctx`), provocando bug #13 ("missing bearer token" mesmo com token válido).
#
# Mantido no repositório para:
#   1. Story 06.30 (reativar após refactor para FastMCP v2 Context API)
#   2. Referência didática do pattern JWT validation (JWKS + audience + scope)
#   3. Lab Avançado (Bloco 5/6) pode reusar `validate_token` em handlers próprios
#
# NÃO importar este módulo em código ativo enquanto Story 06.30 não for
# concluída — o decorator vai falhar silenciosamente com a nova API.
# ─────────────────────────────────────────────────────────────────────────────
"""
from __future__ import annotations

import functools
import logging
import os
from typing import Callable

import jwt
import requests

log = logging.getLogger("mcp-auth")

TENANT_ID = os.environ.get("AZURE_TENANT_ID", os.environ.get("ENTRA_TENANT_ID", ""))
EXPECTED_AUDIENCE = os.environ.get("EXPECTED_AUDIENCE", "")
JWKS_URL = f"https://login.microsoftonline.com/{TENANT_ID}/discovery/v2.0/keys"

_jwks_cache: list[dict] | None = None


def _get_jwks() -> list[dict]:
    global _jwks_cache
    if _jwks_cache is None:
        resp = requests.get(JWKS_URL, timeout=10)
        resp.raise_for_status()
        _jwks_cache = resp.json()["keys"]
    return _jwks_cache


def validate_token(token: str) -> dict:
    """Valida JWT do Entra ID. Retorna claims se válido, raise se inválido."""
    headers = jwt.get_unverified_header(token)
    kid = headers["kid"]
    key = next((k for k in _get_jwks() if k["kid"] == kid), None)
    if key is None:
        raise ValueError(f"kid {kid!r} não encontrado no JWKS")
    public_key = jwt.algorithms.RSAAlgorithm.from_jwk(key)
    claims = jwt.decode(
        token,
        public_key,
        algorithms=["RS256"],
        audience=EXPECTED_AUDIENCE,
        issuer=f"https://login.microsoftonline.com/{TENANT_ID}/v2.0",
    )
    return claims


def require_scope(scope: str) -> Callable:
    """Decorator para tools MCP: valida que o token Bearer tem o scope informado."""
    def decorator(fn):
        @functools.wraps(fn)
        def wrapper(*args, ctx: dict | None = None, **kwargs):
            token = (ctx or {}).get("bearer_token", "")
            if not token:
                raise PermissionError("missing bearer token")
            claims = validate_token(token)
            scopes = claims.get("scp", "").split()
            if scope not in scopes:
                raise PermissionError(f"required scope {scope!r} not in token")
            log.info("auth OK scope=%s sub=%s", scope, claims.get("sub"))
            return fn(*args, **kwargs)
        return wrapper
    return decorator
