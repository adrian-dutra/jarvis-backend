from datetime import datetime

import pytest
from fastapi import HTTPException

from app.models.task import Task
from app.schemas.task_schema import TaskCreate
from app.services.task_service import TaskService


pytestmark = pytest.mark.asyncio


async def test_adicionar_tarefa_cria_com_status_pending(mock_task_repository):
    created_task = Task(
        id=1,
        title="Estudar embeddings",
        description="Revisar FAISS e BM25",
        subject="IA",
        priority="high",
        status="pending",
        due_date=None,
        created_at=datetime(2026, 5, 24, 12, 0, 0),
        updated_at=datetime(2026, 5, 24, 12, 0, 0),
    )
    mock_task_repository.create_task.return_value = created_task
    service = TaskService(mock_task_repository)

    result = await service.adicionar_tarefa(
        TaskCreate(
            title="Estudar embeddings",
            description="Revisar FAISS e BM25",
            subject="IA",
            priority="high",
        )
    )

    assert result.status == "pending"
    mock_task_repository.create_task.assert_awaited_once()
    assert mock_task_repository.create_task.await_args.kwargs["status"] == "pending"
    assert mock_task_repository.create_task.await_args.kwargs["priority"] == "high"


async def test_concluir_tarefa_pendente_preenche_completed_at(mock_task_repository):
    task = Task(
        id=1,
        title="Resolver lista",
        priority="medium",
        status="pending",
        created_at=datetime(2026, 5, 24, 12, 0, 0),
        updated_at=datetime(2026, 5, 24, 12, 0, 0),
    )
    mock_task_repository.get_task.return_value = task
    mock_task_repository.update_task.return_value = task
    service = TaskService(mock_task_repository)

    result = await service.concluir_tarefa(1)

    assert result.status == "completed"
    assert result.completed_at is not None
    assert result.updated_at == result.completed_at
    mock_task_repository.update_task.assert_awaited_once_with(task)


async def test_concluir_tarefa_ja_concluida_retorna_400(mock_task_repository):
    task = Task(
        id=1,
        title="Trabalho entregue",
        priority="medium",
        status="completed",
        completed_at=datetime(2026, 5, 24, 12, 0, 0),
        created_at=datetime(2026, 5, 24, 11, 0, 0),
        updated_at=datetime(2026, 5, 24, 12, 0, 0),
    )
    mock_task_repository.get_task.return_value = task
    service = TaskService(mock_task_repository)

    with pytest.raises(HTTPException) as exc:
        await service.concluir_tarefa(1)

    assert exc.value.status_code == 400
    assert exc.value.detail == "Tarefa já está concluída."
    mock_task_repository.update_task.assert_not_awaited()


async def test_concluir_tarefa_inexistente_retorna_404(mock_task_repository):
    mock_task_repository.get_task.return_value = None
    service = TaskService(mock_task_repository)

    with pytest.raises(HTTPException) as exc:
        await service.concluir_tarefa(999)

    assert exc.value.status_code == 404
    assert exc.value.detail == "Tarefa não encontrada."
    mock_task_repository.update_task.assert_not_awaited()


async def test_listar_tarefas_delega_filtros_ao_repository(mock_task_repository):
    mock_task_repository.list_tasks.return_value = []
    service = TaskService(mock_task_repository)

    result = await service.listar_tarefas(
        status_filter="pending",
        priority="high",
        subject="IA",
    )

    assert result == []
    mock_task_repository.list_tasks.assert_awaited_once_with(
        status="pending",
        priority="high",
        subject="IA",
    )
