"""HTTP wrapper do `agent_runner` para Copilot Studio (e clientes externos) chamarem.

Lazy import de `agent_runner`: necessário porque o módulo faz init pesado no
top-level (`DefaultAzureCredential()` + `AgentsClient(...)` + leitura de 6 env vars),
e em **Flex Consumption** o indexing inicial roda em modo "placeholder" onde as
App Settings ainda não estão expostas. Se o import top-level falhar nesse
contexto, o host registra `0 functions found` silenciosamente (sem stack trace
no Application Insights). Mover `from agent_runner import ...` para dentro de
`chat()` garante que o indexing só lê os decorators `@app.route(...)`, e os
clientes Azure são instanciados apenas na primeira invocação real (cold start
normal, com env vars já especializadas).
"""
import json

import azure.functions as func

app = func.FunctionApp(http_auth_level=func.AuthLevel.FUNCTION)


@app.route(route="agent/chat", methods=["POST"])
def chat(req: func.HttpRequest) -> func.HttpResponse:
    from agent_runner import client, run_agent

    body = req.get_json()
    user_message = body.get("message", "")
    thread_id = body.get("thread_id")

    if not thread_id:
        thread = client.threads.create()
        thread_id = thread.id

    response = run_agent(thread_id, user_message)
    return func.HttpResponse(
        json.dumps({"thread_id": thread_id, "response": response}),
        status_code=200,
        mimetype="application/json",
    )
