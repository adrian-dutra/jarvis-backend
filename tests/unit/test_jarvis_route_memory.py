from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from app.api.routes.jarvis import _CONVERSATIONS, ask_jarvis
from app.schemas.jarvis_schema import JarvisAskRequest, JarvisAskResponse


pytestmark = pytest.mark.asyncio


async def test_jarvis_ask_guarda_historico_por_conversation_id():
    _CONVERSATIONS.clear()
    agent = SimpleNamespace(
        ask=AsyncMock(
            side_effect=[
                JarvisAskResponse(
                    message="Crie uma pergunta sobre RAG.",
                    conversation_id="demo",
                    answer="Qual etapa recupera documentos relevantes no RAG?",
                    tools_used=[],
                ),
                JarvisAskResponse(
                    message="A recuperação.",
                    conversation_id="demo",
                    answer="Correto, essa etapa busca os documentos relevantes.",
                    tools_used=[],
                ),
            ]
        )
    )

    await ask_jarvis(
        JarvisAskRequest(
            conversation_id="demo",
            message="Crie uma pergunta sobre RAG.",
        ),
        agent=agent,
    )
    await ask_jarvis(
        JarvisAskRequest(
            conversation_id="demo",
            message="A recuperação.",
        ),
        agent=agent,
    )

    second_call = agent.ask.await_args_list[1]
    assert second_call.kwargs["conversation_id"] == "demo"
    assert second_call.kwargs["history"] == [
        {"role": "user", "content": "Crie uma pergunta sobre RAG."},
        {
            "role": "assistant",
            "content": "Qual etapa recupera documentos relevantes no RAG?",
        },
    ]
    assert _CONVERSATIONS["demo"][-2:] == [
        {"role": "user", "content": "A recuperação."},
        {
            "role": "assistant",
            "content": "Correto, essa etapa busca os documentos relevantes.",
        },
    ]
