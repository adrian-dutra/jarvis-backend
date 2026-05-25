from fastapi import APIRouter, Depends, Path, Query, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.connection import get_async_db
from app.repositories.task_repository import TaskRepository
from app.schemas.task_schema import (
    TaskCompleteResponse,
    TaskCreate,
    TaskPriority,
    TaskResponse,
    TaskStatus,
    TaskSummary,
)
from app.services.task_service import TaskService


router = APIRouter(prefix="/tasks", tags=["Tarefas"])


def get_task_service(db: AsyncSession = Depends(get_async_db)) -> TaskService:
    repository = TaskRepository(db)
    return TaskService(repository)


@router.post(
    "",
    response_model=TaskSummary,
    status_code=status.HTTP_201_CREATED,
    summary="Criar tarefa acadêmica",
    description=(
        "Cria uma tarefa acadêmica com status inicial pending. "
        "Quando due_date contém timezone, o service converte a data para UTC antes da persistência."
    ),
    response_description="Resumo da tarefa criada.",
)
async def create_task(
    payload: TaskCreate,
    service: TaskService = Depends(get_task_service),
) -> TaskSummary:
    task = await service.adicionar_tarefa(payload)
    return task


@router.get(
    "",
    response_model=list[TaskResponse],
    status_code=status.HTTP_200_OK,
    summary="Listar tarefas",
    description=(
        "Lista tarefas cadastradas com filtros opcionais por status, prioridade e disciplina. "
        "A ordenação é feita no banco: tarefas pendentes primeiro e prazos mais próximos antes."
    ),
    response_description="Lista de tarefas ordenada e filtrada.",
)
async def list_tasks(
    status: TaskStatus | None = Query(default=None, description="Filtra tarefas por status."),
    priority: TaskPriority | None = Query(default=None, description="Filtra tarefas por prioridade."),
    subject: str | None = Query(default=None, description="Filtra tarefas por disciplina ou parte do nome."),
    service: TaskService = Depends(get_task_service),
) -> list[TaskResponse]:
    return await service.listar_tarefas(
        status_filter=status,
        priority=priority,
        subject=subject,
    )


@router.get(
    "/{task_id}",
    response_model=TaskResponse,
    status_code=status.HTTP_200_OK,
    summary="Detalhar tarefa",
    description="Retorna os dados completos de uma tarefa. Se o id não existir, retorna 404.",
    response_description="Dados completos da tarefa.",
)
async def get_task(
    task_id: int = Path(..., description="Identificador da tarefa."),
    service: TaskService = Depends(get_task_service),
) -> TaskResponse:
    return await service.obter_tarefa(task_id)


@router.patch(
    "/{task_id}/complete",
    response_model=TaskCompleteResponse,
    status_code=status.HTTP_200_OK,
    summary="Concluir tarefa",
    description=(
        "Marca uma tarefa pendente como completed, preenchendo completed_at e updated_at em UTC. "
        "Retorna erro quando a tarefa não existe ou já está concluída."
    ),
    response_description="Status e timestamp de conclusão da tarefa.",
)
async def complete_task(
    task_id: int = Path(..., description="Identificador da tarefa a concluir."),
    service: TaskService = Depends(get_task_service),
) -> TaskCompleteResponse:
    return await service.concluir_tarefa(task_id)


@router.delete(
    "/{task_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Remover tarefa",
    description="Remove uma tarefa do banco. Se o id não existir, retorna 404.",
    response_description="Tarefa removida com sucesso, sem corpo de resposta.",
)
async def delete_task(
    task_id: int = Path(..., description="Identificador da tarefa a remover."),
    service: TaskService = Depends(get_task_service),
) -> Response:
    await service.remover_tarefa(task_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
