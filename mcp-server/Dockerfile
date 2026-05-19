# MCP Server HelpSphere
# Build: az acr build --registry <ACR_NAME> --image mcp-helpsphere:v1 --file Dockerfile .
#
# Bug fixes 2026-05-19:
#  1) Adicionado bloco ODBC Driver 18 + unixodbc-dev (pyodbc precisa de
#     libodbc.so.2 e msodbcsql18 instalados no SO; python:3.11-slim é minimal)
#  2) COPY *.py em vez de COPY server.py (server.py importa auth +
#     helpsphere_db — antes quebrava com ModuleNotFoundError)

FROM python:3.11-slim

# ODBC driver para pyodbc (SQL Server)
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl gnupg2 unixodbc-dev \
 && curl https://packages.microsoft.com/keys/microsoft.asc | apt-key add - \
 && curl https://packages.microsoft.com/config/debian/12/prod.list > /etc/apt/sources.list.d/mssql-release.list \
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
