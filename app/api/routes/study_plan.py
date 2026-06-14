from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.connection import get_async_db
from app.repositories.agenda_repository import AgendaRepository
from app.repositories.material_repository import MaterialRepository
from app.repositories.task_repository import TaskRepository
from app.schemas.study_plan_schema import StudyPlanRequest, StudyPlanResponse
from app.services.agenda_service import AgendaService
from app.services.material_service import MaterialService
from app.services.study_plan_service import StudyPlanService
from app.services.task_service import TaskService


router = APIRouter(prefix="/study-plan", tags=["Planejamento de Estudos"])


def get_study_plan_service(
    db: AsyncSession = Depends(get_async_db),
) -> StudyPlanService:
    agenda_service = AgendaService(AgendaRepository(db))
    task_service = TaskService(TaskRepository(db))
    material_service = MaterialService(MaterialRepository(db))
    return StudyPlanService(
        agenda_service=agenda_service,
        task_service=task_service,
        material_service=material_service,
    )


@router.post(
    "",
    response_model=StudyPlanResponse,
    status_code=status.HTTP_200_OK,
    summary="Gerar plano de estudos",
    description=(
        "Combina agenda acadêmica, tarefas pendentes e materiais recuperados por RAG "
        "para montar um plano de estudos estruturado com prioridades e blocos de estudo."
    ),
    response_description="Plano de estudos estruturado com fontes consideradas.",
)
async def generate_study_plan(
    payload: StudyPlanRequest,
    service: StudyPlanService = Depends(get_study_plan_service),
) -> StudyPlanResponse:
    return await service.generate_plan(payload)
