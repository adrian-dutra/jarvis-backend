from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from app.llm.agent import JarvisAgent


pytestmark = pytest.mark.asyncio


def _response(*, content: str | None = None):
    message = SimpleNamespace(content=content)
    return SimpleNamespace(choices=[SimpleNamespace(message=message)])


def _agent(
    *,
    gemma_client,
    task_service=None,
    agenda_service=None,
    material_service=None,
    study_plan_service=None,
    learning_service=None,
    review_service=None,
):
    return JarvisAgent(
        task_service=task_service or SimpleNamespace(),
        agenda_service=agenda_service or SimpleNamespace(),
        material_service=material_service or SimpleNamespace(),
        study_plan_service=study_plan_service,
        learning_service=learning_service,
        review_service=review_service,
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


async def test_agent_envia_historico_para_gemma(mocker):
    gemma_client = SimpleNamespace(
        async_chat=AsyncMock(return_value=_response(content="Sua resposta foi correta."))
    )
    agent = _agent(gemma_client=gemma_client)

    response = await agent.ask(
        "Recuperação de documentos.",
        conversation_id="teste-historico",
        history=[
            {"role": "user", "content": "Crie uma pergunta sobre RAG."},
            {
                "role": "assistant",
                "content": "Qual etapa busca documentos relevantes no RAG?",
            },
        ],
    )

    messages = gemma_client.async_chat.await_args.kwargs["messages"]
    assert messages[0]["role"] == "system"
    assert messages[1] == {"role": "user", "content": "Crie uma pergunta sobre RAG."}
    assert messages[2]["role"] == "assistant"
    assert messages[3] == {"role": "user", "content": "Recuperação de documentos."}
    assert response.conversation_id == "teste-historico"
    assert response.answer == "Sua resposta foi correta."


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


async def test_agent_executa_gerar_plano_estudos_quando_modelo_solicita_tool(mocker):
    study_plan = {
        "objective": "Montar plano para a prova de IA",
        "priorities": [],
        "agenda_considered": [],
        "tasks_considered": [],
        "materials_considered": [],
        "study_blocks": [],
        "next_action": "Comece revisando RAG.",
        "warnings": [],
        "llm_summary": "Plano de estudos gerado.",
    }
    study_plan_service = SimpleNamespace(
        generate_plan=AsyncMock(return_value=study_plan)
    )
    gemma_client = SimpleNamespace(
        async_chat=AsyncMock(
            side_effect=[
                _response(
                    content=(
                        '{"tool": "gerar_plano_estudos", "arguments": '
                        '{"objective": "Montar plano para a prova de IA", '
                        '"target_date": "2026-06-20", "available_minutes": 120, '
                        '"material_query": "RAG"}}'
                    )
                ),
                _response(content="Aqui está seu plano de estudos."),
            ]
        )
    )
    agent = _agent(
        gemma_client=gemma_client,
        study_plan_service=study_plan_service,
    )

    response = await agent.ask("Monte um plano de estudos para a prova de IA")

    study_plan_service.generate_plan.assert_awaited_once()
    assert response.answer == "Aqui está seu plano de estudos."
    assert response.tools_used[0].name == "gerar_plano_estudos"
    assert response.tools_used[0].result["ok"] is True
    assert response.tools_used[0].result["data"]["next_action"] == "Comece revisando RAG."


@pytest.mark.parametrize(
    ("tool_name", "arguments", "service_attr", "method_name"),
    [
        (
            "gerar_exercicios",
            {"topic": "RAG", "quantity": 2, "level": "medio"},
            "learning_service",
            "generate_exercises",
        ),
        (
            "iniciar_active_recall",
            {"topic": "RAG", "level": "medio"},
            "learning_service",
            "start_active_recall",
        ),
        (
            "avaliar_resposta_active_recall",
            {"question_id": 1, "user_answer": "RAG usa contexto externo."},
            "learning_service",
            "evaluate_active_recall",
        ),
        (
            "recomendar_revisao",
            {},
            "review_service",
            "get_review_recommendations",
        ),
    ],
)
async def test_agent_executa_tools_de_aprendizado(
    tool_name,
    arguments,
    service_attr,
    method_name,
):
    service = SimpleNamespace(**{method_name: AsyncMock(return_value={"ok": "data"})})
    gemma_client = SimpleNamespace(
        async_chat=AsyncMock(
            side_effect=[
                _response(
                    content=(
                        '{"tool": "'
                        + tool_name
                        + '", "arguments": '
                        + __import__("json").dumps(arguments)
                        + "}"
                    )
                ),
                _response(content="Resultado de aprendizado."),
            ]
        )
    )
    kwargs = {
        "gemma_client": gemma_client,
        service_attr: service,
    }
    agent = _agent(**kwargs)

    response = await agent.ask("Quero estudar melhor")

    getattr(service, method_name).assert_awaited_once()
    assert response.answer == "Resultado de aprendizado."
    assert response.tools_used[0].name == tool_name
    assert response.tools_used[0].result["ok"] is True
