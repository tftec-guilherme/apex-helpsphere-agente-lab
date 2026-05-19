# MCP Server HelpSphere — v0.1.0-init skeleton
# Build: docker build -t mcp-helpsphere:v0.1 .
# Push: docker push acrlabfinal{aluno}.azurecr.io/mcp-helpsphere:v0.1

FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Bug fix 2026-05-19: COPY *.py em vez de COPY server.py — server.py faz
# `from auth import require_scope` e `from helpsphere_db import HelpSphereDB`.
# Versão anterior só copiava server.py e quebrava com ModuleNotFoundError no boot.
COPY *.py ./

EXPOSE 8080

CMD ["python", "server.py"]
