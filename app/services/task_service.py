from datetime import datetime, timezone

from fastapi import HTTPException, status
from loguru import logger

from app.models.task import Task
from app.repositories.task_repository import TaskRepository
from app.schemas.task_schema import TaskCreate


class TaskService:
    def __init__(self, repository: TaskRepository):
        self.repository = repository

    async def adicionar_tarefa(self, payload: TaskCreate) -> Task:
        now = self._utc_now()
        task = await self.repository.create_task(
            title=payload.title,
            description=payload.description,
            subject=payload.subject,
            priority=payload.priority,
            status="pending",
            due_date=self._to_utc_naive(payload.due_date),
            created_at=now,
            updated_at=now,
        )
        logger.info(
            "tarefa criada task_id={} priority={} subject={}",
            task.id,
            task.priority,
            task.subject,
        )
        return task

    async def listar_tarefas(
        self,
        *,
        status_filter: str | None = None,
        priority: str | None = None,
        subject: str | None = None,
    ) -> list[Task]:
        tasks = await self.repository.list_tasks(
            status=status_filter,
            priority=priority,
            subject=subject,
        )
        logger.info(
            "tarefas listadas total={} status={} priority={} subject={}",
            len(tasks),
            status_filter,
            priority,
            subject,
        )
        return tasks

    async def obter_tarefa(self, task_id: int) -> Task:
        return await self._get_task_or_404(task_id)

    async def concluir_tarefa(self, task_id: int) -> Task:
        task = await self._get_task_or_404(task_id)
        if task.status == "completed":
            logger.warning("tentativa de concluir tarefa já concluída task_id={}", task_id)
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Tarefa já está concluída.",
            )

        now = self._utc_now()
        task.status = "completed"
        task.completed_at = now
        task.updated_at = now

        task = await self.repository.update_task(task)
        logger.info("tarefa concluída task_id={}", task.id)
        return task

    async def remover_tarefa(self, task_id: int) -> None:
        task = await self._get_task_or_404(task_id)
        await self.repository.delete_task(task)
        logger.info("tarefa removida task_id={}", task_id)

    async def listar_tarefas_pendentes(self) -> list[Task]:
        return await self.listar_tarefas(status_filter="pending")

    async def listar_tarefas_atrasadas(self) -> list[Task]:
        now = self._utc_now()
        pending_tasks = await self.listar_tarefas(status_filter="pending")
        return [
            task
            for task in pending_tasks
            if task.due_date is not None and task.due_date < now
        ]

    async def _get_task_or_404(self, task_id: int) -> Task:
        task = await self.repository.get_task(task_id)
        if task is None:
            logger.warning("tarefa não encontrada task_id={}", task_id)
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Tarefa não encontrada.",
            )
        return task

    def _utc_now(self) -> datetime:
        return datetime.now(timezone.utc).replace(tzinfo=None)

    def _to_utc_naive(self, value: datetime | None) -> datetime | None:
        if value is None:
            return None
        if value.tzinfo is None:
            return value
        return value.astimezone(timezone.utc).replace(tzinfo=None)
