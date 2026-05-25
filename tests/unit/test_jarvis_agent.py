from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from app.llm.agent import JarvisAgent


pytestmark = pytest.mark.asyncio


def _response(*, content: str | None = None):
    message = SimpleNamespace(content=content)
    return SimpleNamespace(choices=[SimpleNamespace(message=message)])


def _agent(*, gemma_client, task_service=None, agenda_service=None, material_service=None):
    return JarvisAgent(
        task_service=task_service or SimpleNamespace(),
        agenda_service=agenda_service or SimpleNamespace(),
        material_service=material_service or SimpleNamespace(),
        gemma_client=gemma_client,
    )


async def test_agent_retorna_texto_direto_quando_modelo_nao_chama_tool(mocker):
    gemma_client = SimpleNamespace(
        async_chat=AsyncMock(return_value=_response(content="Olá, como posso ajudar?"))
    )
    agent = _agent(gemma_client=gemma_client)

    response = await agent.ask("Olá")

    assert response.answer == "Olá, como posso ajudar?"
    assert response.tools_used == []
    assert gemma_client.async_chat.await_count == 1


async def test_agent_executa_listar_tarefas_quando_modelo_solicita_tool(mocker):
    task_service = SimpleNamespace(listar_tarefas=AsyncMock(return_value=[]))
    gemma_client = SimpleNamespace(
        async_chat=AsyncMock(
            side_effect=[
                _response(
                    content='{"tool": "listar_tarefas", "arguments": {"status": "pending"}}'
                ),
                _response(content="Você não tem tarefas pendentes."),
            ]
        )
    )
    agent = _agent(gemma_client=gemma_client, task_service=task_service)

    response = await agent.ask("Quais tarefas pendentes eu tenho?")

    task_service.listar_tarefas.assert_awaited_once_with(
        status_filter="pending",
        priority=None,
        subject=None,
    )
    assert response.answer == "Você não tem tarefas pendentes."
    assert len(response.tools_used) == 1
    assert response.tools_used[0].name == "listar_tarefas"
    assert response.tools_used[0].arguments == {"status": "pending"}
    assert response.tools_used[0].result == {"ok": True, "data": []}


async def test_agent_retorna_texto_quando_resposta_nao_for_json_de_tool(mocker):
    gemma_client = SimpleNamespace(
        async_chat=AsyncMock(return_value=_response(content="{status: pending}"))
    )
    agent = _agent(gemma_client=gemma_client)

    response = await agent.ask("Liste minhas tarefas")

    assert response.answer == "{status: pending}"
    assert response.tools_used == []


async def test_agent_registra_tool_desconhecida_no_trace(mocker):
    gemma_client = SimpleNamespace(
        async_chat=AsyncMock(
            side_effect=[
                _response(
                    content='{"tool": "ferramenta_inexistente", "arguments": {}}'
                ),
                _response(content="A ferramenta solicitada não está disponível."),
            ]
        )
    )
    agent = _agent(gemma_client=gemma_client)

    response = await agent.ask("Faça algo")

    assert response.answer == "A ferramenta solicitada não está disponível."
    assert response.tools_used[0].name == "ferramenta_inexistente"
    assert response.tools_used[0].result["ok"] is False
    assert "Tool desconhecida" in response.tools_used[0].result["error"]
