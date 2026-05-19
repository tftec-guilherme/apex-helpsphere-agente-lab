# MCP Server HelpSphere
# Build: az acr build --registry <ACR_NAME> --image mcp-helpsphere:v1 --file Dockerfile .
#
# Bug fixes 2026-05-19:
#  1) Adicionado bloco ODBC Driver 18 + unixodbc-dev (pyodbc precisa de
#     libodbc.so.2 e msodbcsql18 instalados no SO; python:3.11-slim é minimal)
#  2) COPY *.py em vez de COPY server.py (server.py importa auth +
#     helpsphere_db — antes quebrava com ModuleNotFoundError)
#  3) Bug #8 — Adicionado `unixodbc` (runtime libs) e `libgssapi-krb5-2`.
#     `unixodbc-dev` sao apenas headers para compilar bindings; `libodbc.so.2`
#     (runtime que pyodbc faz dlopen em import-time) vem de `unixodbc`. Em
#     Debian 12 Bookworm com `--no-install-recommends`, esse runtime nao e
#     instalado por transitividade — gerando ImportError no boot do container.
#     `libgssapi-krb5-2` e dependencia de msodbcsql18 para AAD/Kerberos auth.

FROM python:3.11-slim

# ODBC driver para pyodbc (SQL Server) — Debian 12 Bookworm
# Bug fix 2026-05-19: apt-key foi deprecated em Debian 12. Microsoft agora usa
# signed-by com chave em /etc/apt/keyrings/ (approach moderno).
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl gnupg2 ca-certificates apt-transport-https \
    unixodbc unixodbc-dev libgssapi-krb5-2 \
 && mkdir -p /etc/apt/keyrings \
 && curl -fsSL https://packages.microsoft.com/keys/microsoft.asc \
    | gpg --dearmor -o /etc/apt/keyrings/microsoft-prod.gpg \
 && echo "deb [arch=amd64,arm64,armhf signed-by=/etc/apt/keyrings/microsoft-prod.gpg] https://packages.microsoft.com/debian/12/prod bookworm main" \
    > /etc/apt/sources.list.d/mssql-release.list \
 && apt-get update \
 && ACCEPT_EULA=Y apt-get install -y msodbcsql18 \
 && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# COPY *.py — server.py + auth.py + helpsphere_db.py
COPY *.py ./

EXPOSE 8080

CMD ["python", "server.py"]
