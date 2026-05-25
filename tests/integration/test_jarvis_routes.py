from types import SimpleNamespace

import pytest


pytestmark = pytest.mark.asyncio


def _response(content: str):
    message = SimpleNamespace(content=content, tool_calls=None)
    return SimpleNamespace(choices=[SimpleNamespace(message=message)])


async def test_jarvis_ask_retorna_resposta_com_gemma_mockado(async_client, mocker):
    mocker.patch(
        "app.llm.gemma_client.GemmaClient.async_chat",
        return_value=_response("Resposta direta mockada."),
    )

    response = await async_client.post(
        "/jarvis/ask",
        json={"message": "Olá, JARVIS"},
    )

    assert response.status_code == 200
    data = response.json()
    assert data["message"] == "Olá, JARVIS"
    assert data["answer"] == "Resposta direta mockada."
    assert data["tools_used"] == []
