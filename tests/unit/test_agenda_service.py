from datetime import datetime
from unittest.mock import AsyncMock

import pytest

from app.models.agenda import AgendaEvent
from app.schemas.agenda_schema import AgendaEventCreate
from app.services.agenda_service import AgendaService


pytestmark = pytest.mark.asyncio


async def test_cadastrar_evento_converte_horario_local_para_utc():
    repository = AsyncMock()
    repository.create_event.return_value = AgendaEvent(
        id=1,
        title="Aula de IA",
        event_type="class",
        subject="IA",
        start_at=datetime(2026, 5, 25, 23, 0, 0),
        end_at=datetime(2026, 5, 26, 0, 0, 0),
        all_day=False,
        recurrence_type="none",
        recurrence_weekdays=None,
        recurrence_until=None,
        created_at=datetime(2026, 5, 24, 12, 0, 0),
        updated_at=datetime(2026, 5, 24, 12, 0, 0),
    )
    service = AgendaService(repository)

    await service.cadastrar_evento(
        AgendaEventCreate(
            title="Aula de IA",
            event_type="class",
            subject="IA",
            start_at=datetime(2026, 5, 25, 19, 0, 0),
            end_at=datetime(2026, 5, 25, 20, 0, 0),
        )
    )

    kwargs = repository.create_event.await_args.kwargs
    assert kwargs["start_at"] == datetime(2026, 5, 25, 23, 0, 0)
    assert kwargs["end_at"] == datetime(2026, 5, 26, 0, 0, 0)
    assert kwargs["recurrence_type"] == "none"
