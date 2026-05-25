from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


TaskPriority = Literal["low", "medium", "high"]
TaskStatus = Literal["pending", "completed"]


class TaskCreate(BaseModel):
    title: str = Field(
        ...,
        min_length=1,
        max_length=255,
        description="Título curto da tarefa acadêmica.",
        examples=["Estudar embeddings"],
    )
    description: str | None = Field(
        default=None,
        description="Descrição opcional com detalhes da atividade.",
        examples=["Revisar FAISS, BM25 e recuperação híbrida."],
    )
    subject: str | None = Field(
        default=None,
        max_length=255,
        description="Disciplina ou área relacionada à tarefa.",
        examples=["Inteligência Artificial"],
    )
    priority: TaskPriority = Field(
        default="medium",
        description="Prioridade da tarefa.",
        examples=["high"],
    )
    due_date: datetime | None = Field(
        default=None,
        description="Prazo da tarefa. Quando informado com timezone, é convertido para UTC internamente.",
        examples=["2026-05-30T20:00:00"],
    )

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "title": "Estudar embeddings",
                "description": "Revisar FAISS e BM25",
                "subject": "Inteligência Artificial",
                "priority": "high",
                "due_date": "2026-05-30T20:00:00",
            }
        }
    )


class TaskSummary(BaseModel):
    id: int = Field(description="Identificador único da tarefa.", examples=[1])
    title: str = Field(description="Título da tarefa.", examples=["Estudar embeddings"])
    status: TaskStatus = Field(description="Status atual da tarefa.", examples=["pending"])

    model_config = ConfigDict(
        from_attributes=True,
        json_schema_extra={
            "example": {
                "id": 1,
                "title": "Estudar embeddings",
                "status": "pending",
            }
        },
    )


class TaskResponse(BaseModel):
    id: int = Field(description="Identificador único da tarefa.", examples=[1])
    title: str = Field(description="Título da tarefa.", examples=["Estudar embeddings"])
    description: str | None = Field(
        default=None,
        description="Descrição detalhada da tarefa.",
        examples=["Revisar FAISS e BM25"],
    )
    subject: str | None = Field(
        default=None,
        description="Disciplina ou área relacionada à tarefa.",
        examples=["Inteligência Artificial"],
    )
    priority: TaskPriority = Field(description="Prioridade da tarefa.", examples=["high"])
    status: TaskStatus = Field(description="Status atual da tarefa.", examples=["pending"])
    due_date: datetime | None = Field(
        default=None,
        description="Prazo da tarefa armazenado internamente em UTC.",
        examples=["2026-05-30T20:00:00"],
    )
    completed_at: datetime | None = Field(
        default=None,
        description="Data de conclusão preenchida quando a tarefa é concluída.",
        examples=["2026-05-25T10:30:00"],
    )
    created_at: datetime = Field(description="Data de criação do registro.", examples=["2026-05-24T12:00:00"])
    updated_at: datetime = Field(description="Data da última atualização.", examples=["2026-05-24T12:00:00"])

    model_config = ConfigDict(
        from_attributes=True,
        json_schema_extra={
            "example": {
                "id": 1,
                "title": "Estudar embeddings",
                "description": "Revisar FAISS e BM25",
                "subject": "Inteligência Artificial",
                "priority": "high",
                "status": "pending",
                "due_date": "2026-05-30T20:00:00",
                "completed_at": None,
                "created_at": "2026-05-24T12:00:00",
                "updated_at": "2026-05-24T12:00:00",
            }
        },
    )


class TaskCompleteResponse(BaseModel):
    id: int = Field(description="Identificador único da tarefa.", examples=[1])
    status: TaskStatus = Field(description="Novo status após conclusão.", examples=["completed"])
    completed_at: datetime = Field(
        description="Timestamp UTC preenchido no momento da conclusão.",
        examples=["2026-05-25T10:30:00"],
    )

    model_config = ConfigDict(
        from_attributes=True,
        json_schema_extra={
            "example": {
                "id": 1,
                "status": "completed",
                "completed_at": "2026-05-25T10:30:00",
            }
        },
    )
