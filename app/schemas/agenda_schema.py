from datetime import date, datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator


AgendaEventType = Literal[
    "class",
    "exam",
    "meeting",
    "assignment",
    "activity",
    "other",
]
AgendaRecurrenceType = Literal["none", "weekly"]


class AgendaEventBase(BaseModel):
    title: str = Field(
        ...,
        min_length=1,
        max_length=255,
        description="Título do compromisso acadêmico.",
        examples=["Aula de Inteligência Artificial"],
    )
    description: str | None = Field(
        default=None,
        description="Descrição opcional do compromisso.",
        examples=["Revisão de RAG híbrido e embeddings."],
    )
    event_type: AgendaEventType = Field(
        description="Tipo do evento acadêmico.",
        examples=["class"],
    )
    subject: str | None = Field(
        default=None,
        max_length=255,
        description="Disciplina relacionada ao evento.",
        examples=["Inteligência Artificial"],
    )
    location: str | None = Field(
        default=None,
        max_length=255,
        description="Local físico ou virtual do evento.",
        examples=["Sala 12"],
    )
    start_at: datetime = Field(
        description="Data e hora inicial. Entradas sem timezone são interpretadas no timezone configurado.",
        examples=["2026-05-25T19:00:00"],
    )
    end_at: datetime | None = Field(
        default=None,
        description="Data e hora final. Deve ser maior que start_at quando informada.",
        examples=["2026-05-25T20:30:00"],
    )
    all_day: bool = Field(
        default=False,
        description="Indica se o evento ocupa o dia inteiro.",
        examples=[False],
    )
    recurrence_type: AgendaRecurrenceType = Field(
        default="none",
        description="Tipo de recorrência. Nesta etapa, apenas none e weekly são suportados.",
        examples=["weekly"],
    )
    recurrence_weekdays: list[int] | None = Field(
        default=None,
        description="Dias da semana para recorrência semanal, usando 0=segunda até 6=domingo.",
        examples=[[0, 2, 4]],
    )
    recurrence_until: date | None = Field(
        default=None,
        description="Data limite opcional para recorrência semanal.",
        examples=["2026-07-31"],
    )

    @model_validator(mode="after")
    def validate_dates_and_recurrence(self):
        if self.end_at and self.end_at <= self.start_at:
            raise ValueError("end_at deve ser maior que start_at")

        if self.recurrence_weekdays:
            invalid_days = [
                weekday
                for weekday in self.recurrence_weekdays
                if weekday < 0 or weekday > 6
            ]
            if invalid_days:
                raise ValueError("recurrence_weekdays deve usar valores de 0 a 6")

        if self.recurrence_type == "none" and self.recurrence_weekdays:
            raise ValueError("recurrence_weekdays só deve ser usado com weekly")

        return self


class AgendaEventCreate(AgendaEventBase):
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "title": "Aula de Inteligência Artificial",
                "description": "Revisão de RAG híbrido e embeddings.",
                "event_type": "class",
                "subject": "Inteligência Artificial",
                "location": "Sala 12",
                "start_at": "2026-05-25T19:00:00",
                "end_at": "2026-05-25T20:30:00",
                "all_day": False,
                "recurrence_type": "weekly",
                "recurrence_weekdays": [0, 2],
                "recurrence_until": "2026-07-31",
            }
        }
    )


class AgendaEventUpdate(BaseModel):
    title: str | None = Field(
        default=None,
        min_length=1,
        max_length=255,
        description="Novo título do evento.",
        examples=["Prova de Inteligência Artificial"],
    )
    description: str | None = Field(
        default=None,
        description="Nova descrição do evento.",
        examples=["Avaliação sobre RAG, embeddings e busca híbrida."],
    )
    event_type: AgendaEventType | None = Field(
        default=None,
        description="Novo tipo do evento.",
        examples=["exam"],
    )
    subject: str | None = Field(
        default=None,
        max_length=255,
        description="Nova disciplina relacionada.",
        examples=["Inteligência Artificial"],
    )
    location: str | None = Field(
        default=None,
        max_length=255,
        description="Novo local do evento.",
        examples=["Laboratório 2"],
    )
    start_at: datetime | None = Field(
        default=None,
        description="Nova data e hora inicial.",
        examples=["2026-05-26T08:00:00"],
    )
    end_at: datetime | None = Field(
        default=None,
        description="Nova data e hora final.",
        examples=["2026-05-26T10:00:00"],
    )
    all_day: bool | None = Field(
        default=None,
        description="Atualiza se o evento é de dia inteiro.",
        examples=[False],
    )
    recurrence_type: AgendaRecurrenceType | None = Field(
        default=None,
        description="Novo tipo de recorrência.",
        examples=["none"],
    )
    recurrence_weekdays: list[int] | None = Field(
        default=None,
        description="Novos dias da semana para recorrência semanal.",
        examples=[[1, 3]],
    )
    recurrence_until: date | None = Field(
        default=None,
        description="Nova data limite da recorrência.",
        examples=["2026-07-31"],
    )

    @model_validator(mode="after")
    def validate_weekdays(self):
        if self.recurrence_weekdays:
            invalid_days = [
                weekday
                for weekday in self.recurrence_weekdays
                if weekday < 0 or weekday > 6
            ]
            if invalid_days:
                raise ValueError("recurrence_weekdays deve usar valores de 0 a 6")
        return self

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "title": "Prova de Inteligência Artificial",
                "event_type": "exam",
                "location": "Laboratório 2",
                "start_at": "2026-05-26T08:00:00",
                "end_at": "2026-05-26T10:00:00",
                "recurrence_type": "none",
            }
        }
    )


class AgendaEventResponse(BaseModel):
    id: int = Field(description="Identificador único do evento.", examples=[1])
    title: str = Field(description="Título do evento.", examples=["Aula de Inteligência Artificial"])
    description: str | None = Field(
        default=None,
        description="Descrição do evento.",
        examples=["Revisão de RAG híbrido e embeddings."],
    )
    event_type: str = Field(description="Tipo do evento.", examples=["class"])
    subject: str | None = Field(default=None, description="Disciplina relacionada.", examples=["Inteligência Artificial"])
    location: str | None = Field(default=None, description="Local do evento.", examples=["Sala 12"])
    start_at: datetime = Field(description="Data e hora inicial apresentada no timezone configurado.", examples=["2026-05-25T19:00:00"])
    end_at: datetime | None = Field(default=None, description="Data e hora final apresentada no timezone configurado.", examples=["2026-05-25T20:30:00"])
    all_day: bool = Field(description="Indica se o evento ocupa o dia inteiro.", examples=[False])
    recurrence_type: str = Field(description="Tipo de recorrência.", examples=["weekly"])
    recurrence_weekdays: list[int] | None = Field(default=None, description="Dias de recorrência semanal.", examples=[[0, 2]])
    recurrence_until: date | None = Field(default=None, description="Data limite da recorrência.", examples=["2026-07-31"])
    created_at: datetime = Field(description="Data de criação do registro.", examples=["2026-05-24T12:00:00"])
    updated_at: datetime = Field(description="Data da última atualização.", examples=["2026-05-24T12:00:00"])

    model_config = ConfigDict(
        from_attributes=True,
        json_schema_extra={
            "example": {
                "id": 1,
                "title": "Aula de Inteligência Artificial",
                "description": "Revisão de RAG híbrido e embeddings.",
                "event_type": "class",
                "subject": "Inteligência Artificial",
                "location": "Sala 12",
                "start_at": "2026-05-25T19:00:00",
                "end_at": "2026-05-25T20:30:00",
                "all_day": False,
                "recurrence_type": "weekly",
                "recurrence_weekdays": [0, 2],
                "recurrence_until": "2026-07-31",
                "created_at": "2026-05-24T12:00:00",
                "updated_at": "2026-05-24T12:00:00",
            }
        },
    )


class AgendaOccurrence(BaseModel):
    event_id: int = Field(description="Identificador do evento original.", examples=[1])
    title: str = Field(description="Título da ocorrência.", examples=["Aula de Inteligência Artificial"])
    description: str | None = Field(default=None, description="Descrição da ocorrência.", examples=["Revisão de RAG híbrido."])
    event_type: str = Field(description="Tipo do evento.", examples=["class"])
    subject: str | None = Field(default=None, description="Disciplina relacionada.", examples=["Inteligência Artificial"])
    location: str | None = Field(default=None, description="Local do compromisso.", examples=["Sala 12"])
    start_at: datetime = Field(description="Data e hora da ocorrência.", examples=["2026-05-25T19:00:00"])
    end_at: datetime | None = Field(default=None, description="Data e hora final da ocorrência.", examples=["2026-05-25T20:30:00"])
    all_day: bool = Field(description="Indica se a ocorrência ocupa o dia inteiro.", examples=[False])
    recurrence_type: str = Field(description="Tipo de recorrência do evento original.", examples=["weekly"])
    is_recurring: bool = Field(description="Indica se a ocorrência foi expandida de um evento recorrente.", examples=[True])

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "event_id": 1,
                "title": "Aula de Inteligência Artificial",
                "description": "Revisão de RAG híbrido.",
                "event_type": "class",
                "subject": "Inteligência Artificial",
                "location": "Sala 12",
                "start_at": "2026-05-25T19:00:00",
                "end_at": "2026-05-25T20:30:00",
                "all_day": False,
                "recurrence_type": "weekly",
                "is_recurring": True,
            }
        }
    )


class AgendaAskRequest(BaseModel):
    question: str = Field(
        ...,
        min_length=1,
        description="Pergunta em linguagem natural sobre os compromissos cadastrados.",
        examples=["Tenho prova amanhã?"],
    )

    model_config = ConfigDict(
        json_schema_extra={"example": {"question": "Tenho prova amanhã?"}}
    )


class AgendaAskResponse(BaseModel):
    question: str = Field(description="Pergunta enviada pelo usuário.", examples=["Tenho prova amanhã?"])
    answer: str = Field(
        description="Resposta gerada pela IA usando apenas os eventos enviados no contexto.",
        examples=["Você tem prova de Inteligência Artificial amanhã às 08:00."],
    )
    events: list[AgendaOccurrence] = Field(description="Ocorrências enviadas como contexto para a IA.")

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "question": "Tenho prova amanhã?",
                "answer": "Você tem prova de Inteligência Artificial amanhã às 08:00.",
                "events": [
                    {
                        "event_id": 2,
                        "title": "Prova de Inteligência Artificial",
                        "description": "Avaliação sobre RAG e embeddings.",
                        "event_type": "exam",
                        "subject": "Inteligência Artificial",
                        "location": "Laboratório 2",
                        "start_at": "2026-05-25T08:00:00",
                        "end_at": "2026-05-25T10:00:00",
                        "all_day": False,
                        "recurrence_type": "none",
                        "is_recurring": False,
                    }
                ],
            }
        }
    )
