from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest
from fastapi import HTTPException

from app.schemas.agenda_schema import AgendaOccurrence
from app.schemas.material_schema import MaterialAskResponse, MaterialSource
from app.schemas.study_plan_schema import StudyPlanRequest
from app.services.study_plan_service import StudyPlanService


pytestmark = pytest.mark.asyncio


def _llm_response(content: str | None):
    message = SimpleNamespace(content=content)
    return SimpleNamespace(choices=[SimpleNamespace(message=message)])


def _llm_plan_json() -> str:
    return """
    {
      "priorities": [
        {
          "title": "Revisar RAG híbrido",
          "level": "high",
          "justification": "A prova está próxima e o material recuperado trata do tema.",
          "related_sources": ["agenda:1", "material:ia.pdf#chunk-1"]
        }
      ],
      "study_blocks": [
        {
          "order": 1,
          "duration_minutes": 60,
          "focus": "RAG e embeddings",
          "activity": "Revisar conceitos e fazer um resumo curto.",
          "related_sources": ["task:2", "material:ia.pdf#chunk-1"],
          "justification": "Combina tarefa pendente com o material mais relevante."
        }
      ],
      "next_action": "Comece revisando o bloco de RAG.",
      "llm_summary": "Plano prioriza a prova, a tarefa pendente e os materiais recuperados."
    }
    """


def _service(*, agenda=None, tasks=None, material=None, gemma_client=None):
    agenda_service = SimpleNamespace(
        consultar_agenda=AsyncMock(return_value=agenda if agenda is not None else [])
    )
    task_service = SimpleNamespace(
        listar_tarefas_pendentes=AsyncMock(return_value=tasks if tasks is not None else [])
    )
    material_service = SimpleNamespace(
        buscar_material_rag=AsyncMock(return_value=material)
    )
    return StudyPlanService(
        agenda_service=agenda_service,
        task_service=task_service,
        material_service=material_service,
        gemma_client=gemma_client
        or SimpleNamespace(async_chat=AsyncMock(return_value=_llm_response(_llm_plan_json()))),
    )


async def test_study_plan_service_combina_agenda_tarefas_e_materiais():
    agenda = [
        AgendaOccurrence(
            event_id=1,
            title="Prova de IA",
            description="RAG e embeddings",
            event_type="exam",
            subject="IA",
            location="Sala 1",
            start_at="2026-06-20T08:00:00",
            end_at="2026-06-20T10:00:00",
            all_day=False,
            recurrence_type="none",
            is_recurring=False,
        )
    ]
    tasks = [
        SimpleNamespace(
            id=2,
            title="Estudar FAISS",
            description="Revisar busca vetorial",
            subject="IA",
            priority="high",
            due_date=None,
        )
    ]
    material = MaterialAskResponse(
        question="RAG",
        answer="RAG combina recuperação e geração.",
        method="hybrid",
        sources=[
            MaterialSource(
                material_id=1,
                material_name="ia.pdf",
                chunk_id=10,
                chunk_index=1,
                text="RAG híbrido usa BM25, embeddings e FAISS.",
                score=0.91,
            )
        ],
    )

    service = _service(agenda=agenda, tasks=tasks, material=material)

    response = await service.generate_plan(
        StudyPlanRequest(
            objective="Montar plano para prova de IA",
            target_date="2026-06-20",
            available_minutes=120,
            material_query="RAG",
        )
    )

    assert response.objective == "Montar plano para prova de IA"
    assert response.priorities
    assert response.study_blocks
    assert response.agenda_considered[0].reference == "agenda:1"
    assert response.tasks_considered[0].reference == "task:2"
    assert response.materials_considered[0].reference == "material:ia.pdf#chunk-1"


async def test_study_plan_service_retorna_warnings_quando_fontes_vazias():
    material = MaterialAskResponse(
        question="RAG",
        answer="não encontrado no contexto",
        method="hybrid",
        sources=[],
    )
    service = _service(material=material)

    response = await service.generate_plan(
        StudyPlanRequest(objective="O que devo priorizar hoje?")
    )

    assert response.agenda_considered == []
    assert response.tasks_considered == []
    assert response.materials_considered == []
    assert "Nenhum evento de agenda encontrado no período." in response.warnings
    assert "Nenhuma tarefa pendente encontrada." in response.warnings
    assert "Nenhum material relevante foi recuperado pelo RAG." in response.warnings


async def test_study_plan_service_erro_llm_retorna_http_500():
    gemma_client = SimpleNamespace(async_chat=AsyncMock(side_effect=RuntimeError("falhou")))
    service = _service(material=None, gemma_client=gemma_client)

    with pytest.raises(HTTPException) as exc_info:
        await service.generate_plan(StudyPlanRequest(objective="Plano de estudos"))

    assert exc_info.value.status_code == 500
    assert exc_info.value.detail == "Erro ao gerar plano de estudos com Gemma."
