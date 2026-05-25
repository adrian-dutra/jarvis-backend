from datetime import datetime

from sqlalchemy import case, nullslast, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.task import Task


class TaskRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def create_task(
        self,
        *,
        title: str,
        description: str | None,
        subject: str | None,
        priority: str,
        status: str,
        due_date: datetime | None,
        created_at: datetime,
        updated_at: datetime,
    ) -> Task:
        task = Task(
            title=title,
            description=description,
            subject=subject,
            priority=priority,
            status=status,
            due_date=due_date,
            created_at=created_at,
            updated_at=updated_at,
        )
        self.db.add(task)
        await self.db.commit()
        await self.db.refresh(task)
        return task

    async def list_tasks(
        self,
        *,
        status: str | None = None,
        priority: str | None = None,
        subject: str | None = None,
    ) -> list[Task]:
        pending_first = case((Task.status == "pending", 0), else_=1)

        statement = select(Task)
        if status:
            statement = statement.where(Task.status == status)
        if priority:
            statement = statement.where(Task.priority == priority)
        if subject:
            statement = statement.where(Task.subject.ilike(f"%{subject}%"))

        statement = statement.order_by(
            pending_first.asc(),
            nullslast(Task.due_date.asc()),
            Task.created_at.asc(),
        )

        result = await self.db.execute(statement)
        return list(result.scalars().all())

    async def get_task(self, task_id: int) -> Task | None:
        return await self.db.get(Task, task_id)

    async def update_task(self, task: Task) -> Task:
        await self.db.commit()
        await self.db.refresh(task)
        return task

    async def delete_task(self, task: Task) -> None:
        await self.db.delete(task)
        await self.db.commit()
