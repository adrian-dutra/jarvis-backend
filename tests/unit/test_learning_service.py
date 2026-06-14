from datetime import datetime
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest
from fastapi import HTTPException

from app.models.learning_attempt import LearningAttempt
from app.schemas.learning_schema import (
    ActiveRecallAnswerRequest,
    ActiveRecallStartRequest,
    ExerciseGenerationRequest,
)
from app.schemas.material_schema import MaterialAskResponse, MaterialSource
from app.services.learning_service import LearningService


pytestmark = pytest.mark.asyncio


def _llm_response(content: str | None):
    message = SimpleNamespace(content=content)
    return SimpleNamespace(choices=[SimpleNamespace(message=message)])


def _material_response(*, sources=True):
    return MaterialAskResponse(
        question="RAG",
        answer="RAG recupera contexto externo antes da geração.",
        method="hybrid",
        sources=[
            MaterialSource(
                material_id=1,
                material_name="rag.pdf",
                chunk_id=10,
                chunk_index=2,
                text="RAG combina recuperação de documentos com geração de respostas.",
                score=0.91,
            )
        ]
        if sources
        else [],
    )


def _service(*, material_response=None, llm_content=None, attempt=None):
    material_service = SimpleNamespace(
        buscar_material_rag=AsyncMock(
            return_value=material_response
            if material_response is not None
            else _material_response()
        )
    )
    repository = SimpleNamespace(
        create_attempt=AsyncMock(
            return_value=attempt
            or LearningAttempt(
                id=1,
                topic="RAG",
                question="O que é RAG?",
                expected_answer="RAG recupera contexto externo antes de gerar.",
                created_at=datetime(2026, 6, 14, 12, 0, 0),
            )
        ),
        get_attempt=AsyncMock(
            return_value=attempt
            or LearningAttempt(
                id=1,
                topic="RAG",
                question="O que é RAG?",
                expected_answer="RAG recupera contexto externo antes de gerar.",
                created_at=datetime(2026, 6, 14, 12, 0, 0),
            )
        ),
        update_evaluation=AsyncMock(),
    )
    gemma_client = SimpleNamespace(
        async_chat=AsyncMock(return_value=_llm_response(llm_content or "{}"))
    )
    return (
        LearningService(
            material_service=material_service,
            attempt_repository=repository,
            gemma_client=gemma_client,
        ),
        repository,
        gemma_client,
    )


async def test_generate_exercises_usa_rag_e_gemma():
    service, _, _ = _service(
        llm_content="""
        {
          "exercises": [
            {
              "question": "Explique o papel da recuperação no RAG.",
              "exercise_type": "discursiva",
              "expected_answer": "Buscar documentos relevantes para compor o contexto."
            }
          ]
        }
        """
    )

    response = await service.generate_exercises(
        ExerciseGenerationRequest(topic="RAG e embeddings", quantity=1, level="medio")
    )

    assert response.topic == "RAG e embeddings"
    assert response.level == "medio"
    assert response.exercises[0].question == "Explique o papel da recuperação no RAG."
    assert response.sources[0].material_name == "rag.pdf"


async def test_generate_exercises_sem_fontes_retorna_404():
    service, _, _ = _service(material_response=_material_response(sources=False))

    with pytest.raises(HTTPException) as exc:
        await service.generate_exercises(ExerciseGenerationRequest(topic="RAG"))

    assert exc.value.status_code == 404
    assert exc.value.detail == "Nenhum material relevante foi encontrado para o tema informado."


async def test_start_active_recall_cria_tentativa_pendente():
    service, repository, _ = _service(
        llm_content="""
        {
          "question": "Como o RAG melhora respostas de uma LLM?",
          "expected_answer": "Ele recupera contexto externo e usa esse contexto na geração."
        }
        """
    )

    response = await service.start_active_recall(
        ActiveRecallStartRequest(topic="RAG", level="medio")
    )

    assert response.question_id == 1
    assert response.question == "Como o RAG melhora respostas de uma LLM?"
    repository.create_attempt.assert_awaited_once()
    assert repository.create_attempt.await_args.kwargs["topic"] == "RAG"


@pytest.mark.parametrize(
    ("classification", "score"),
    [
        ("correta", 0.95),
        ("parcialmente_correta", 0.6),
        ("incorreta", 0.2),
    ],
)
async def test_evaluate_active_recall_salva_classificacao(classification, score):
    service, repository, _ = _service(
        llm_content=f"""
        {{
          "classification": "{classification}",
          "score": {score},
          "feedback": "Feedback objetivo.",
          "expected_answer_summary": "Resumo da resposta esperada.",
          "strengths": ["Mencionou contexto"],
          "improvements": ["Detalhar recuperação"],
          "review_recommendation": "Revise o fluxo de RAG."
        }}
        """
    )

    response = await service.evaluate_active_recall(
        ActiveRecallAnswerRequest(question_id=1, user_answer="RAG usa contexto externo.")
    )

    assert response.classification == classification
    assert response.score == score
    repository.update_evaluation.assert_awaited_once()
    assert repository.update_evaluation.await_args.kwargs["classification"] == classification
