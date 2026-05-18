"""HTTP wrapper do `agent_runner` para Copilot Studio (e clientes externos) chamarem.

Deploy: Function App Linux Python 3.11 Consumption. Application Settings
precisam de TODAS as env vars que `agent_runner.py` consome.
"""
import json

import azure.functions as func

from agent_runner import client, run_agent

app = func.FunctionApp(http_auth_level=func.AuthLevel.FUNCTION)


@app.route(route="agent/chat", methods=["POST"])
def chat(req: func.HttpRequest) -> func.HttpResponse:
    body = req.get_json()
    user_message = body.get("message", "")
    thread_id = body.get("thread_id")

    if not thread_id:
        thread = client.agents.create_thread()
        thread_id = thread.id

    response = run_agent(thread_id, user_message)
    return func.HttpResponse(
        json.dumps({"thread_id": thread_id, "response": response}),
        status_code=200,
        mimetype="application/json",
    )
