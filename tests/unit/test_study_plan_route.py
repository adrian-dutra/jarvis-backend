from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from app.api.routes.study_plan import generate_study_plan
from app.schemas.study_plan_schema import (
    StudyPlanItem,
    StudyPlanPriority,
    StudyPlanRequest,
    StudyPlanResponse,
    StudyPlanSource,
)


pytestmark = pytest.mark.asyncio


async def test_post_study_plan_retorna_plano_estruturado():
    expected = StudyPlanResponse(
        objective="Montar um plano de estudos para a prova de IA",
        priorities=[
            StudyPlanPriority(
                title="Revisar RAG",
                level="high",
                justification="Tema central dos materiais recuperados.",
                related_sources=["material:ia.pdf#chunk-1"],
            )
        ],
        agenda_considered=[
            StudyPlanSource(
                source_type="agenda",
                reference="agenda:1",
                title="Prova de IA",
                summary="exam em 2026-06-20 08:00:00.",
            )
        ],
        tasks_considered=[],
        materials_considered=[
            StudyPlanSource(
                source_type="material",
                reference="material:ia.pdf#chunk-1",
                title="ia.pdf",
                summary="RAG híbrido usa BM25 e embeddings.",
            )
        ],
        study_blocks=[
            StudyPlanItem(
                order=1,
                duration_minutes=60,
                focus="RAG",
                activity="Revisar conceitos principais.",
                related_sources=["material:ia.pdf#chunk-1"],
                justification="Atende ao objetivo informado.",
            )
        ],
        next_action="Comece pelo bloco de RAG.",
        warnings=["Nenhuma tarefa pendente encontrada."],
        llm_summary="Plano gerado com agenda e materiais.",
    )
    service = SimpleNamespace(generate_plan=AsyncMock(return_value=expected))

    response = await generate_study_plan(
        StudyPlanRequest(
            objective="Montar um plano de estudos para a prova de IA",
            target_date="2026-06-20",
            available_minutes=120,
            material_query="RAG, embeddings, FAISS, BM25",
        ),
        service=service,
    )

    data = response.model_dump(mode="json")
    assert data["priorities"]
    assert data["study_blocks"]
    assert data["agenda_considered"]
    assert data["materials_considered"]
    assert data["warnings"] == ["Nenhuma tarefa pendente encontrada."]
