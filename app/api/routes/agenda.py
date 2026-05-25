from datetime import date

from fastapi import APIRouter, Depends, Path, Query, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.connection import get_async_db
from app.repositories.agenda_repository import AgendaRepository
from app.schemas.agenda_schema import (
    AgendaAskRequest,
    AgendaAskResponse,
    AgendaEventCreate,
    AgendaEventResponse,
    AgendaEventUpdate,
    AgendaOccurrence,
)
from app.services.agenda_service import AgendaService


router = APIRouter(prefix="/agenda", tags=["Agenda"])


def get_agenda_service(db: AsyncSession = Depends(get_async_db)) -> AgendaService:
    repository = AgendaRepository(db)
    return AgendaService(repository)


@router.post(
    "",
    response_model=AgendaEventResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Criar evento de agenda",
    description=(
        "Cria um evento acadêmico simples ou recorrente semanal. "
        "Datas sem timezone são interpretadas em America/Campo_Grande e convertidas para UTC internamente."
    ),
    response_description="Evento cadastrado e normalizado para apresentação.",
)
async def create_event(
    payload: AgendaEventCreate,
    service: AgendaService = Depends(get_agenda_service),
):
    return await service.create_event(payload)


@router.get(
    "",
    response_model=list[AgendaOccurrence],
    status_code=status.HTTP_200_OK,
    summary="Listar ocorrências da agenda",
    description=(
        "Lista ocorrências em um intervalo de datas, com filtros opcionais por tipo e disciplina. "
        "Eventos semanais recorrentes são expandidos pelo service antes de retornar ao frontend."
    ),
    response_description="Ocorrências da agenda ordenadas por data e hora.",
)
async def list_agenda(
    start_date: date | None = Query(default=None, description="Data inicial da consulta."),
    end_date: date | None = Query(default=None, description="Data final da consulta."),
    event_type: str | None = Query(default=None, description="Filtra por tipo de evento."),
    subject: str | None = Query(default=None, description="Filtra por disciplina ou parte do nome."),
    service: AgendaService = Depends(get_agenda_service),
):
    return await service.consultar_agenda(
        start_date=start_date,
        end_date=end_date,
        event_type=event_type,
        subject=subject,
    )


@router.get(
    "/today",
    response_model=list[AgendaOccurrence],
    status_code=status.HTTP_200_OK,
    summary="Consultar agenda de hoje",
    description=(
        "Retorna as ocorrências do dia atual considerando a data do servidor no timezone configurado. "
        "O service converte o intervalo local para UTC antes de consultar o banco."
    ),
    response_description="Ocorrências de hoje.",
)
async def get_today_agenda(service: AgendaService = Depends(get_agenda_service)):
    return await service.consultar_agenda_hoje()


@router.get(
    "/week",
    response_model=list[AgendaOccurrence],
    status_code=status.HTTP_200_OK,
    summary="Consultar agenda da semana",
    description=(
        "Retorna as ocorrências da semana atual, de segunda a domingo, considerando o timezone configurado. "
        "Eventos semanais recorrentes são expandidos para o período."
    ),
    response_description="Ocorrências da semana atual.",
)
async def get_week_agenda(service: AgendaService = Depends(get_agenda_service)):
    return await service.consultar_agenda_semana()


@router.post(
    "/ask",
    response_model=AgendaAskResponse,
    status_code=status.HTTP_200_OK,
    summary="Perguntar sobre a agenda",
    description=(
        "Envia uma pergunta em linguagem natural para a IA usando como contexto as ocorrências dos próximos 30 dias. "
        "A resposta deve se basear apenas nos eventos cadastrados."
    ),
    response_description="Resposta da IA e eventos usados como contexto.",
)
async def ask_agenda(
    payload: AgendaAskRequest,
    service: AgendaService = Depends(get_agenda_service),
):
    return await service.ask(payload.question)


@router.get(
    "/{event_id}",
    response_model=AgendaEventResponse,
    status_code=status.HTTP_200_OK,
    summary="Detalhar evento de agenda",
    description="Retorna o registro salvo de um evento da agenda. Se o id não existir, retorna 404.",
    response_description="Dados completos do evento.",
)
async def get_event(
    event_id: int = Path(..., description="Identificador do evento de agenda."),
    service: AgendaService = Depends(get_agenda_service),
):
    return await service.get_event(event_id)


@router.patch(
    "/{event_id}",
    response_model=AgendaEventResponse,
    status_code=status.HTTP_200_OK,
    summary="Atualizar evento de agenda",
    description=(
        "Atualiza parcialmente um evento. Quando datas são alteradas, o service valida end_at > start_at "
        "e converte os valores para UTC antes da persistência."
    ),
    response_description="Evento atualizado.",
)
async def update_event(
    payload: AgendaEventUpdate,
    event_id: int = Path(..., description="Identificador do evento a atualizar."),
    service: AgendaService = Depends(get_agenda_service),
):
    return await service.update_event(event_id, payload)


@router.delete(
    "/{event_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Remover evento de agenda",
    description="Remove um evento da agenda. Se o id não existir, retorna 404.",
    response_description="Evento removido com sucesso, sem corpo de resposta.",
)
async def delete_event(
    event_id: int = Path(..., description="Identificador do evento a remover."),
    service: AgendaService = Depends(get_agenda_service),
):
    await service.delete_event(event_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
