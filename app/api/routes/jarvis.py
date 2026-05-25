from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.connection import get_async_db
from app.llm.agent import JarvisAgent
from app.repositories.agenda_repository import AgendaRepository
from app.repositories.material_repository import MaterialRepository
from app.repositories.task_repository import TaskRepository
from app.schemas.jarvis_schema import JarvisAskRequest, JarvisAskResponse
from app.services.agenda_service import AgendaService
from app.services.material_service import MaterialService
from app.services.task_service import TaskService


router = APIRouter(prefix="/jarvis", tags=["JARVIS"])


def get_jarvis_agent(db: AsyncSession = Depends(get_async_db)) -> JarvisAgent:
    task_service = TaskService(TaskRepository(db))
    agenda_service = AgendaService(AgendaRepository(db))
    material_service = MaterialService(MaterialRepository(db))
    return JarvisAgent(
        task_service=task_service,
        agenda_service=agenda_service,
        material_service=material_service,
    )


@router.post(
    "/ask",
    response_model=JarvisAskResponse,
    status_code=status.HTTP_200_OK,
    summary="Conversar com o JARVIS usando Tool Calling",
    description=(
        "Recebe uma mensagem em linguagem natural, envia as tools disponíveis para a LLM "
        "e executa apenas as ferramentas solicitadas em tool_calls. "
        "O agente não acessa o banco diretamente; ele chama os services da aplicação."
    ),
    response_description="Resposta final da IA e resumo das ferramentas executadas.",
)
async def ask_jarvis(
    payload: JarvisAskRequest,
    agent: JarvisAgent = Depends(get_jarvis_agent),
) -> JarvisAskResponse:
    return await agent.ask(payload.message)
