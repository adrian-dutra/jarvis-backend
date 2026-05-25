from datetime import date, datetime

from sqlalchemy import and_, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.agenda import AgendaEvent


class AgendaRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def create_event(
        self,
        *,
        title: str,
        description: str | None,
        event_type: str,
        subject: str | None,
        location: str | None,
        start_at: datetime,
        end_at: datetime | None,
        all_day: bool,
        recurrence_type: str,
        recurrence_weekdays: str | None,
        recurrence_until: date | None,
        created_at: datetime,
        updated_at: datetime,
    ) -> AgendaEvent:
        event = AgendaEvent(
            title=title,
            description=description,
            event_type=event_type,
            subject=subject,
            location=location,
            start_at=start_at,
            end_at=end_at,
            all_day=all_day,
            recurrence_type=recurrence_type,
            recurrence_weekdays=recurrence_weekdays,
            recurrence_until=recurrence_until,
            created_at=created_at,
            updated_at=updated_at,
        )
        self.db.add(event)
        await self.db.commit()
        await self.db.refresh(event)
        return event

    async def get_event(self, event_id: int) -> AgendaEvent | None:
        return await self.db.get(AgendaEvent, event_id)

    async def list_candidate_events(
        self,
        *,
        start_at: datetime,
        end_at: datetime,
        event_type: str | None = None,
        subject: str | None = None,
    ) -> list[AgendaEvent]:
        non_recurring_filter = and_(
            AgendaEvent.recurrence_type == "none",
            AgendaEvent.start_at >= start_at,
            AgendaEvent.start_at <= end_at,
        )
        weekly_filter = and_(
            AgendaEvent.recurrence_type == "weekly",
            AgendaEvent.start_at <= end_at,
            or_(
                AgendaEvent.recurrence_until.is_(None),
                AgendaEvent.recurrence_until >= start_at.date(),
            ),
        )

        statement = select(AgendaEvent).where(or_(non_recurring_filter, weekly_filter))

        if event_type:
            statement = statement.where(AgendaEvent.event_type == event_type)
        if subject:
            statement = statement.where(AgendaEvent.subject.ilike(f"%{subject}%"))

        statement = statement.order_by(AgendaEvent.start_at.asc())
        result = await self.db.execute(statement)
        return list(result.scalars().all())

    async def update_event(self, event: AgendaEvent, data: dict) -> AgendaEvent:
        for field, value in data.items():
            setattr(event, field, value)
        await self.db.commit()
        await self.db.refresh(event)
        return event

    async def delete_event(self, event: AgendaEvent) -> None:
        await self.db.delete(event)
        await self.db.commit()
