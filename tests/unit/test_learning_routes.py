from datetime import datetime
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from app.api.routes.learning import (
    answer_active_recall,
    generate_exercises,
    get_review_recommendations,
    start_active_recall,
)
from app.schemas.learning_schema import (
    ActiveRecallAnswerRequest,
    ActiveRecallEvaluationResponse,
    ActiveRecallQuestionResponse,
    ActiveRecallStartRequest,
    ExerciseGenerationRequest,
    ExerciseGenerationResponse,
    ExerciseItem,
    LearningSource,
    ReviewRecommendation,
    ReviewRecommendationResponse,
)


pytestmark = pytest.mark.asyncio


def _source():
    return LearningSource(
        material_id=1,
        material_name="rag.pdf",
        chunk_id=10,
        chunk_index=2,
        score=0.9,
        text="RAG recupera contexto externo.",
    )


async def test_generate_exercises_route_delega_para_service():
    expected = ExerciseGenerationResponse(
        topic="RAG",
        level="medio",
        exercises=[
            ExerciseItem(
                question="O que é RAG?",
                exercise_type="discursiva",
                expected_answer="Recuperação aumentada por geração.",
            )
        ],
        sources=[_source()],
    )
    service = SimpleNamespace(generate_exercises=AsyncMock(return_value=expected))

    response = await generate_exercises(
        ExerciseGenerationRequest(topic="RAG"),
        service=service,
    )

    assert response.exercises[0].question == "O que é RAG?"
    service.generate_exercises.assert_awaited_once()


async def test_start_active_recall_route_delega_para_service():
    expected = ActiveRecallQuestionResponse(
        question_id=1,
        topic="RAG",
        level="medio",
        question="Como o RAG usa contexto?",
        sources=[_source()],
    )
    service = SimpleNamespace(start_active_recall=AsyncMock(return_value=expected))

    response = await start_active_recall(
        ActiveRecallStartRequest(topic="RAG"),
        service=service,
    )

    assert response.question_id == 1
    assert response.sources


async def test_answer_active_recall_route_delega_para_service():
    expected = ActiveRecallEvaluationResponse(
        question_id=1,
        classification="correta",
        score=0.95,
        feedback="Boa resposta.",
        expected_answer_summary="RAG usa contexto externo.",
        strengths=["Mencionou contexto"],
        improvements=["Detalhar recuperação"],
        review_recommendation="Revise exemplos de RAG.",
    )
    service = SimpleNamespace(evaluate_active_recall=AsyncMock(return_value=expected))

    response = await answer_active_recall(
        ActiveRecallAnswerRequest(question_id=1, user_answer="Usa contexto externo."),
        service=service,
    )

    assert response.classification == "correta"
    assert response.score == 0.95


async def test_review_recommendations_route_delega_para_service():
    expected = ReviewRecommendationResponse(
        recommendations=[
            ReviewRecommendation(
                topic="RAG",
                priority="alta",
                reason="Erros recorrentes.",
                attempts_count=2,
                average_score=0.25,
            )
        ],
        generated_at=datetime(2026, 6, 14, 12, 0, 0),
    )
    service = SimpleNamespace(get_review_recommendations=AsyncMock(return_value=expected))

    response = await get_review_recommendations(service=service)

    assert response.recommendations[0].priority == "alta"
