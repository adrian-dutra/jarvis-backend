from fastapi import APIRouter, Depends, status
from loguru import logger
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.connection import get_async_db
from app.llm.agent import JarvisAgent
from app.repositories.agenda_repository import AgendaRepository
from app.repositories.learning_attempt_repository import LearningAttemptRepository
from app.repositories.material_repository import MaterialRepository
from app.repositories.task_repository import TaskRepository
from app.schemas.jarvis_schema import JarvisAskRequest, JarvisAskResponse
from app.services.agenda_service import AgendaService
from app.services.learning_service import LearningService
from app.services.material_service import MaterialService
from app.services.review_service import ReviewService
from app.services.study_plan_service import StudyPlanService
from app.services.task_service import TaskService


router = APIRouter(prefix="/jarvis", tags=["JARVIS"])
MAX_CONVERSATION_MESSAGES = 20
_CONVERSATIONS: dict[str, list[dict[str, str]]] = {}


def get_jarvis_agent(db: AsyncSession = Depends(get_async_db)) -> JarvisAgent:
    task_service = TaskService(TaskRepository(db))
    agenda_service = AgendaService(AgendaRepository(db))
    material_service = MaterialService(MaterialRepository(db))
    learning_attempt_repository = LearningAttemptRepository(db)
    study_plan_service = StudyPlanService(
        agenda_service=agenda_service,
        task_service=task_service,
        material_service=material_service,
    )
    learning_service = LearningService(
        material_service=material_service,
        attempt_repository=learning_attempt_repository,
    )
    review_service = ReviewService(learning_attempt_repository)
    return JarvisAgent(
        task_service=task_service,
        agenda_service=agenda_service,
        material_service=material_service,
        study_plan_service=study_plan_service,
        learning_service=learning_service,
        review_service=review_service,
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
    stored_history = _CONVERSATIONS.get(payload.conversation_id, [])
    request_history = [item.model_dump() for item in payload.history]
    history = [*stored_history, *request_history]

    _log_conversation(
        conversation_id=payload.conversation_id,
        history=history,
        current_message=payload.message,
    )

    response = await agent.ask(
        payload.message,
        history=history,
        conversation_id=payload.conversation_id,
    )

    _append_to_memory(
        conversation_id=payload.conversation_id,
        user_message=payload.message,
        assistant_answer=response.answer,
    )

    logger.info(
        "jarvis conversa resposta conversation_id={} answer={}",
        payload.conversation_id,
        _short(response.answer),
    )

    return response


def _append_to_memory(
    *,
    conversation_id: str,
    user_message: str,
    assistant_answer: str,
) -> None:
    messages = _CONVERSATIONS.setdefault(conversation_id, [])
    messages.extend(
        [
            {"role": "user", "content": user_message},
            {"role": "assistant", "content": assistant_answer},
        ]
    )
    _CONVERSATIONS[conversation_id] = messages[-MAX_CONVERSATION_MESSAGES:]


def _log_conversation(
    *,
    conversation_id: str,
    history: list[dict[str, str]],
    current_message: str,
) -> None:
    logger.info(
        "jarvis conversa pergunta conversation_id={} history_messages={} message={}",
        conversation_id,
        len(history),
        _short(current_message),
    )
    for index, item in enumerate(history, start=1):
        logger.info(
            "jarvis conversa historico conversation_id={} index={} role={} content={}",
            conversation_id,
            index,
            item.get("role"),
            _short(item.get("content", "")),
        )


def _short(value: str, limit: int = 1200) -> str:
    normalized = " ".join(value.split())
    if len(normalized) <= limit:
        return normalized
    return f"{normalized[: limit - 3]}..."
