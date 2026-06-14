from datetime import datetime
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from app.models.learning_attempt import LearningAttempt
from app.services.review_service import ReviewService


pytestmark = pytest.mark.asyncio


def _attempt(*, topic: str, classification: str, score: float):
    return LearningAttempt(
        id=1,
        topic=topic,
        question="Pergunta",
        expected_answer="Resposta esperada",
        user_answer="Resposta do aluno",
        classification=classification,
        score=score,
        feedback="Feedback",
        created_at=datetime(2026, 6, 14, 12, 0, 0),
    )


async def test_review_service_prioridade_alta_para_erros_recorrentes():
    repository = SimpleNamespace(
        list_review_attempts=AsyncMock(
            return_value=[
                _attempt(topic="RAG", classification="incorreta", score=0.2),
                _attempt(topic="RAG", classification="incorreta", score=0.3),
            ]
        )
    )
    service = ReviewService(repository)

    response = await service.get_review_recommendations()

    assert len(response.recommendations) == 1
    assert response.recommendations[0].topic == "RAG"
    assert response.recommendations[0].priority == "alta"
    assert response.recommendations[0].attempts_count == 2


async def test_review_service_prioridade_media_para_parcialmente_corretas():
    repository = SimpleNamespace(
        list_review_attempts=AsyncMock(
            return_value=[
                _attempt(
                    topic="Embeddings",
                    classification="parcialmente_correta",
                    score=0.75,
                )
            ]
        )
    )
    service = ReviewService(repository)

    response = await service.get_review_recommendations()

    assert response.recommendations[0].topic == "Embeddings"
    assert response.recommendations[0].priority == "media"


async def test_review_service_retorna_lista_vazia_sem_dificuldades():
    repository = SimpleNamespace(list_review_attempts=AsyncMock(return_value=[]))
    service = ReviewService(repository)

    response = await service.get_review_recommendations()

    assert response.recommendations == []
