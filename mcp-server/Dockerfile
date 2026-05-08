# MCP Server HelpSphere — v0.1.0-init skeleton
# Build: docker build -t mcp-helpsphere:v0.1 .
# Push: docker push acrlabfinal{aluno}.azurecr.io/mcp-helpsphere:v0.1

FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY server.py .

EXPOSE 8080

CMD ["python", "server.py"]
