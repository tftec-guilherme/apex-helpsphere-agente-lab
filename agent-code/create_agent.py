"""Cria o helpsphere-tier1-agent no Foundry Agent Service.

Define system prompt + 4 tools (function calling). Roda 1x para registrar o
agent no Foundry; depois, agent_runner.py usa o `agent.id` retornado.

Pré-requisitos:
    pip install -r requirements.txt
    $env:AI_PROJECT_CONNECTION_STRING = "<connection-string-do-foundry-project>"
    $env:RAG_FUNCTION_URL = "https://func-helpsphere-rag-{rand}.azurewebsites.net"
    $env:RAG_FUNCTION_KEY = "<key>"
    $env:MCP_SERVER_URL = "https://placeholder"  # placeholder ate Parte 4

Uso:
    python create_agent.py
"""
import os

from azure.ai.projects import AIProjectClient
from azure.identity import DefaultAzureCredential

PROJECT_CONNECTION_STRING = os.environ["AI_PROJECT_CONNECTION_STRING"]
RAG_FUNCTION_URL = os.environ["RAG_FUNCTION_URL"]
RAG_FUNCTION_KEY = os.environ["RAG_FUNCTION_KEY"]
MCP_SERVER_URL = os.environ["MCP_SERVER_URL"]

client = AIProjectClient.from_connection_string(
    credential=DefaultAzureCredential(),
    conn_str=PROJECT_CONNECTION_STRING,
)

# Tool 1: search_kb — chama RAG do Lab Intermediário
search_kb_tool = {
    "type": "function",
    "function": {
        "name": "search_kb",
        "description": "Busca na base de conhecimento corporativa (manuais, runbooks, FAQs, políticas) sugestões de resposta para um problema descrito. Retorna sugestão com citações e score de confiança.",
        "parameters": {
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "Descrição do problema/pergunta a buscar"},
                "ticket_id": {"type": "string", "description": "ID do ticket (opcional)"},
            },
            "required": ["query"],
        },
    },
}

# Tool 2: get_ticket — via MCP Server
get_ticket_tool = {
    "type": "function",
    "function": {
        "name": "get_ticket",
        "description": "Recupera dados completos de um ticket do HelpSphere pelo ID. Retorna descrição, status, categoria, prioridade, anexos, histórico.",
        "parameters": {
            "type": "object",
            "properties": {
                "ticket_id": {"type": "integer", "description": "ID numérico do ticket"},
            },
            "required": ["ticket_id"],
        },
    },
}

# Tool 3: list_similar_tickets — via MCP Server
list_similar_tool = {
    "type": "function",
    "function": {
        "name": "list_similar_tickets",
        "description": "Lista tickets passados resolvidos com mesma categoria — útil para basear sugestão em casos análogos.",
        "parameters": {
            "type": "object",
            "properties": {
                "category": {"type": "string"},
                "limit": {"type": "integer", "default": 5},
            },
            "required": ["category"],
        },
    },
}

# Tool 4: escalate_ticket — dispara workflow n8n via Service Bus
escalate_tool = {
    "type": "function",
    "function": {
        "name": "escalate_ticket",
        "description": "Escala ticket para tier 2 (supervisora Marina). Use quando confidence < 0.5 ou quando o caso envolver complexidade alta. Dispara workflow estruturado de notificação.",
        "parameters": {
            "type": "object",
            "properties": {
                "ticket_id": {"type": "integer"},
                "reason": {"type": "string", "description": "Motivo da escalação"},
                "confidence": {"type": "number", "description": "Confidence calculado (0-1)"},
            },
            "required": ["ticket_id", "reason", "confidence"],
        },
    },
}

# TODO(student): customize o system prompt do seu agente.
# O texto abaixo é a baseline pedagógica — ajuste o tom, regras de negócio,
# limites de scope ou estilo de resposta. Sugestões de exploração:
#   - Tom mais ou menos formal (você/senhor/etc.)
#   - Adicionar políticas internas da empresa fictícia HelpSphere
#   - Limitar respostas em máximo X palavras
#   - Citar SLA esperado de resposta
SYSTEM_PROMPT = """Você é o agente autônomo de tier 1 da Apex HelpSphere.

Quando recebe uma pergunta sobre ticket:
1. Use `search_kb` para buscar resposta na base de conhecimento corporativa
2. Se confidence retornado < 0.5, use `escalate_ticket` em vez de tentar responder
3. Para casos onde precisa contexto adicional, use `get_ticket` e `list_similar_tickets`
4. Sempre cite as fontes ([Manual X, seção Y]) na resposta final
5. Resposta em pt-BR, tom profissional, conciso (max 200 palavras)
6. Se a pergunta envolver dados pessoais sensíveis (CPF, salário, dados médicos), responda "Esse caso requer redação humana — escalando para tier 2." e use `escalate_ticket`.

NUNCA invente informação que não esteja no kb. Se não encontrar, escale."""

agent = client.agents.create_agent(
    model="gpt-4.1-mini",
    name="helpsphere-tier1-agent",
    instructions=SYSTEM_PROMPT,
    tools=[search_kb_tool, get_ticket_tool, list_similar_tool, escalate_tool],
)

print(f"[+] Agent criado: {agent.id}")
print(f"    Model: {agent.model}")
print(f"    Tools: {len(agent.tools)}")
print("    Anote esse ID — usado no Copilot Studio (Passo 2.5) e no Function App (Passo 3.6).")
