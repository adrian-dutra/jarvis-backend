import asyncio
from datetime import date, datetime, time, timedelta, timezone
from zoneinfo import ZoneInfo

from fastapi import HTTPException, status
from loguru import logger

from app.core.config import get_settings
from app.llm.gemma_client import GemmaClient
from app.models.agenda import AgendaEvent
from app.repositories.agenda_repository import AgendaRepository
from app.schemas.agenda_schema import (
    AgendaAskResponse,
    AgendaEventCreate,
    AgendaEventResponse,
    AgendaEventUpdate,
    AgendaOccurrence,
)


class AgendaService:
    def __init__(self, repository: AgendaRepository):
        self.repository = repository
        self.settings = get_settings()
        self.timezone = ZoneInfo(self.settings.timezone)

    async def create_event(self, payload: AgendaEventCreate) -> AgendaEventResponse:
        return await self.cadastrar_evento(payload)

    async def cadastrar_evento(self, payload: AgendaEventCreate) -> AgendaEventResponse:
        data = payload.model_dump()
        start_at_local = self._input_to_local_naive(data["start_at"])
        data["start_at"] = self._to_utc_naive(data["start_at"])
        if data["end_at"]:
            data["end_at"] = self._to_utc_naive(data["end_at"])

        self._validate_event_dates(data["start_at"], data["end_at"])
        data = self._prepare_recurrence_data(data, weekday_source=start_at_local)
        now = self._utc_now()
        data["created_at"] = now
        data["updated_at"] = now

        event = await self.repository.create_event(**data)
        logger.info(
            "evento de agenda criado event_id={} event_type={} recurrence={}",
            event.id,
            event.event_type,
            event.recurrence_type,
        )
        return self._event_response(event)

    async def get_event(self, event_id: int) -> AgendaEventResponse:
        event = await self._get_event_or_404(event_id)
        return self._event_response(event)

    async def update_event(
        self,
        event_id: int,
        payload: AgendaEventUpdate,
    ) -> AgendaEventResponse:
        event = await self._get_event_or_404(event_id)
        data = payload.model_dump(exclude_unset=True)

        start_at_local = self._to_local_naive(event.start_at)
        if "start_at" in data and data["start_at"]:
            start_at_local = self._input_to_local_naive(data["start_at"])
            data["start_at"] = self._to_utc_naive(data["start_at"])
        if "end_at" in data and data["end_at"]:
            data["end_at"] = self._to_utc_naive(data["end_at"])

        start_at = data.get("start_at", event.start_at)
        end_at = data.get("end_at", event.end_at)
        self._validate_event_dates(start_at, end_at)

        merged_data = {
            "start_at": start_at,
            "recurrence_type": data.get("recurrence_type", event.recurrence_type),
            "recurrence_weekdays": data.get(
                "recurrence_weekdays",
                self._parse_weekdays(event.recurrence_weekdays),
            ),
            "recurrence_until": data.get("recurrence_until", event.recurrence_until),
        }
        prepared_recurrence = self._prepare_recurrence_data(
            merged_data,
            weekday_source=start_at_local,
        )

        if "recurrence_type" in data or "recurrence_weekdays" in data or "start_at" in data:
            data["recurrence_type"] = prepared_recurrence["recurrence_type"]
            data["recurrence_weekdays"] = prepared_recurrence["recurrence_weekdays"]
        if data.get("recurrence_type") == "none":
            data["recurrence_until"] = None
        data["updated_at"] = self._utc_now()

        event = await self.repository.update_event(event, data)
        logger.info("evento de agenda atualizado event_id={}", event.id)
        return self._event_response(event)

    async def delete_event(self, event_id: int) -> None:
        event = await self._get_event_or_404(event_id)
        await self.repository.delete_event(event)
        logger.info("evento de agenda removido event_id={}", event_id)

    async def consultar_agenda(
        self,
        *,
        start_date: date | None = None,
        end_date: date | None = None,
        event_type: str | None = None,
        subject: str | None = None,
    ) -> list[AgendaOccurrence]:
        today = self._today()
        start_date = start_date or today
        end_date = end_date or (start_date + timedelta(days=30))

        start_at = datetime.combine(start_date, time.min)
        end_at = datetime.combine(end_date, time.max)
        utc_start_at = self._local_boundary_to_utc_naive(start_at)
        utc_end_at = self._local_boundary_to_utc_naive(end_at)

        events = await self.repository.list_candidate_events(
            start_at=utc_start_at,
            end_at=utc_end_at,
            event_type=event_type,
            subject=subject,
        )
        occurrences = self._expand_events(events, start_at=start_at, end_at=end_at)

        logger.info(
            "consulta agenda start_date={} end_date={} total={}",
            start_date,
            end_date,
            len(occurrences),
        )
        return occurrences

    async def consultar_agenda_hoje(self) -> list[AgendaOccurrence]:
        today = self._today()
        occurrences = await self.consultar_agenda(start_date=today, end_date=today)
        logger.info("consulta agenda hoje total={}", len(occurrences))
        return occurrences

    async def consultar_agenda_semana(self) -> list[AgendaOccurrence]:
        today = self._today()
        start_date = today - timedelta(days=today.weekday())
        end_date = start_date + timedelta(days=6)
        occurrences = await self.consultar_agenda(start_date=start_date, end_date=end_date)
        logger.info("consulta agenda semana total={}", len(occurrences))
        return occurrences

    async def consultar_provas_proximas(self, days: int = 30) -> list[AgendaOccurrence]:
        today = self._today()
        return await self.consultar_agenda(
            start_date=today,
            end_date=today + timedelta(days=days),
            event_type="exam",
        )

    async def ask(self, question: str) -> AgendaAskResponse:
        occurrences = await self.consultar_agenda()
        logger.info(
            "pergunta agenda recebida occurrences_context={} question={}",
            len(occurrences),
            question,
        )

        if not occurrences:
            return AgendaAskResponse(
                question=question,
                answer="Não encontrei compromissos na agenda.",
                events=[],
            )

        prompt = self._build_agenda_prompt(question=question, occurrences=occurrences)

        try:
            answer = (
                await asyncio.to_thread(GemmaClient().generate, prompt)
            ).strip()
        except Exception as exc:
            logger.exception("erro ao chamar Gemma na agenda")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Erro ao gerar resposta da agenda com Gemma.",
            ) from exc

        return AgendaAskResponse(
            question=question,
            answer=answer or "Não encontrei compromissos na agenda.",
            events=occurrences,
        )

    def _expand_events(
        self,
        events: list[AgendaEvent],
        *,
        start_at: datetime,
        end_at: datetime,
    ) -> list[AgendaOccurrence]:
        occurrences: list[AgendaOccurrence] = []

        for event in events:
            if event.recurrence_type == "weekly":
                occurrences.extend(self._expand_weekly_event(event, start_at, end_at))
            else:
                event_start = self._to_local_naive(event.start_at)
                if start_at <= event_start <= end_at:
                    occurrences.append(self._occurrence_from_event(event, event_start))

        occurrences.sort(key=lambda item: item.start_at)
        return occurrences

    def _expand_weekly_event(
        self,
        event: AgendaEvent,
        start_at: datetime,
        end_at: datetime,
    ) -> list[AgendaOccurrence]:
        event_start = self._to_local_naive(event.start_at)
        weekdays = self._parse_weekdays(event.recurrence_weekdays)
        if not weekdays:
            weekdays = [event_start.weekday()]

        first_day = max(start_at.date(), event_start.date())
        last_day = min(end_at.date(), event.recurrence_until or end_at.date())

        occurrences: list[AgendaOccurrence] = []
        current_day = first_day
        while current_day <= last_day:
            if current_day.weekday() in weekdays:
                occurrence_start = datetime.combine(current_day, event_start.time())
                if event_start <= occurrence_start <= end_at:
                    occurrences.append(
                        self._occurrence_from_event(event, occurrence_start)
                    )
            current_day += timedelta(days=1)

        return occurrences

    def _occurrence_from_event(
        self,
        event: AgendaEvent,
        occurrence_start: datetime,
    ) -> AgendaOccurrence:
        occurrence_end = None
        if event.end_at:
            duration = event.end_at - event.start_at
            occurrence_end = occurrence_start + duration

        return AgendaOccurrence(
            event_id=event.id,
            title=event.title,
            description=event.description,
            event_type=event.event_type,
            subject=event.subject,
            location=event.location,
            start_at=occurrence_start,
            end_at=occurrence_end,
            all_day=event.all_day,
            recurrence_type=event.recurrence_type,
            is_recurring=event.recurrence_type != "none",
        )

    def _build_agenda_prompt(
        self,
        *,
        question: str,
        occurrences: list[AgendaOccurrence],
    ) -> str:
        today = self._today()
        tomorrow = today + timedelta(days=1)
        week_start = today - timedelta(days=today.weekday())
        week_end = week_start + timedelta(days=6)

        event_lines = []
        for item in occurrences:
            end_text = f" até {item.end_at.isoformat()}" if item.end_at else ""
            event_lines.append(
                "- "
                f"{item.start_at.isoformat()}{end_text} | "
                f"tipo={item.event_type} | "
                f"titulo={item.title} | "
                f"disciplina={item.subject or '-'} | "
                f"local={item.location or '-'} | "
                f"descricao={item.description or '-'}"
            )

        return (
            "Você é o assistente de agenda acadêmica do JARVIS Acadêmico.\n"
            "Responda em português usando apenas os eventos do contexto.\n"
            "Se não houver compromisso relevante no contexto, diga que não encontrou "
            "compromisso na agenda.\n\n"
            f"Timezone: {self.settings.timezone}\n"
            f"Hoje: {today.isoformat()}\n"
            f"Amanhã: {tomorrow.isoformat()}\n"
            f"Esta semana: {week_start.isoformat()} até {week_end.isoformat()}\n\n"
            "Eventos disponíveis:\n"
            f"{chr(10).join(event_lines)}\n\n"
            f"Pergunta do usuário: {question}\n"
            "Resposta:"
        )

    def _event_response(self, event: AgendaEvent) -> AgendaEventResponse:
        return AgendaEventResponse(
            id=event.id,
            title=event.title,
            description=event.description,
            event_type=event.event_type,
            subject=event.subject,
            location=event.location,
            start_at=self._to_local_naive(event.start_at),
            end_at=self._to_local_naive(event.end_at) if event.end_at else None,
            all_day=event.all_day,
            recurrence_type=event.recurrence_type,
            recurrence_weekdays=self._parse_weekdays(event.recurrence_weekdays),
            recurrence_until=event.recurrence_until,
            created_at=self._to_local_naive(event.created_at),
            updated_at=self._to_local_naive(event.updated_at),
        )

    def _prepare_recurrence_data(
        self,
        data: dict,
        *,
        weekday_source: datetime,
    ) -> dict:
        recurrence_type = data.get("recurrence_type") or "none"
        data["recurrence_type"] = recurrence_type

        if recurrence_type == "weekly":
            weekdays = data.get("recurrence_weekdays") or [weekday_source.weekday()]
            data["recurrence_weekdays"] = self._serialize_weekdays(weekdays)
        else:
            data["recurrence_weekdays"] = None
            data["recurrence_until"] = None

        return data

    def _validate_event_dates(
        self,
        start_at: datetime,
        end_at: datetime | None,
    ) -> None:
        if end_at and end_at <= start_at:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="end_at deve ser maior que start_at.",
            )

    async def _get_event_or_404(self, event_id: int) -> AgendaEvent:
        event = await self.repository.get_event(event_id)
        if event is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Evento de agenda não encontrado.",
            )
        return event

    def _today(self) -> date:
        return datetime.now(self.timezone).date()

    def _to_local_naive(self, value: datetime) -> datetime:
        if value.tzinfo:
            return value.astimezone(self.timezone).replace(tzinfo=None)
        return value.replace(tzinfo=timezone.utc).astimezone(self.timezone).replace(tzinfo=None)

    def _input_to_local_naive(self, value: datetime) -> datetime:
        if value.tzinfo:
            return value.astimezone(self.timezone).replace(tzinfo=None)
        return value

    def _to_utc_naive(self, value: datetime) -> datetime:
        if value.tzinfo:
            return value.astimezone(timezone.utc).replace(tzinfo=None)
        local_value = value.replace(tzinfo=self.timezone)
        return local_value.astimezone(timezone.utc).replace(tzinfo=None)

    def _local_boundary_to_utc_naive(self, value: datetime) -> datetime:
        return value.replace(tzinfo=self.timezone).astimezone(timezone.utc).replace(tzinfo=None)

    def _utc_now(self) -> datetime:
        return datetime.now(timezone.utc).replace(tzinfo=None)

    def _serialize_weekdays(self, weekdays: list[int]) -> str:
        unique_weekdays = sorted(set(weekdays))
        return ",".join(str(weekday) for weekday in unique_weekdays)

    def _parse_weekdays(self, value: str | None) -> list[int] | None:
        if not value:
            return None
        return [int(item) for item in value.split(",") if item != ""]
