import json
from datetime import date
from typing import Any

from fastapi import HTTPException, status
from fastapi.encoders import jsonable_encoder
from loguru import logger
from pydantic import ValidationError

from app.llm.gemma_client import GemmaClient
from app.schemas.jarvis_schema import JarvisAskResponse, JarvisToolTrace
from app.schemas.learning_schema import (
    ActiveRecallAnswerRequest,
    ActiveRecallStartRequest,
    ExerciseGenerationRequest,
)
from app.schemas.material_schema import MaterialAskRequest
from app.schemas.study_plan_schema import StudyPlanRequest
from app.schemas.task_schema import TaskCreate
from app.services.agenda_service import AgendaService
from app.services.learning_service import LearningService
from app.services.material_service import MaterialService
from app.services.review_service import ReviewService
from app.services.study_plan_service import StudyPlanService
from app.services.task_service import TaskService


SYSTEM_PROMPT = """
Você é o JARVIS Acadêmico, um assistente para organização e estudo.
Responda sempre em português, de forma clara e objetiva.

Você possui acesso a ferramentas internas do sistema.

Ferramentas disponíveis:

1. consultar_agenda
Argumentos:
{
  "start_date": "YYYY-MM-DD ou null",
  "end_date": "YYYY-MM-DD ou null",
  "event_type": "aula/prova/trabalho/reuniao/outro ou null",
  "subject": "matéria ou null"
}

2. listar_tarefas
Argumentos:
{
  "status": "pendente/concluida/todas ou null",
  "priority": "baixa/media/alta ou null",
  "subject": "matéria ou null"
}

3. adicionar_tarefa
Argumentos:
{
  "title": "título da tarefa",
  "description": "descrição",
  "subject": "matéria",
  "priority": "baixa/media/alta",
  "due_date": "YYYY-MM-DD ou null"
}

4. concluir_tarefa
Argumentos:
{
  "task_id": 1
}

5. buscar_material_rag
Argumentos:
{
  "question": "pergunta do usuário"
}

6. gerar_plano_estudos
Argumentos:
{
  "objective": "objetivo do plano",
  "target_date": "YYYY-MM-DD ou null",
  "available_minutes": 120,
  "material_query": "consulta opcional para buscar materiais"
}

7. gerar_exercicios
Argumentos:
{
  "topic": "tema dos exercícios",
  "quantity": 5,
  "level": "facil/medio/dificil"
}

8. iniciar_active_recall
Argumentos:
{
  "topic": "tema da pergunta",
  "level": "facil/medio/dificil"
}

9. avaliar_resposta_active_recall
Argumentos:
{
  "question_id": 1,
  "user_answer": "resposta do estudante"
}

10. recomendar_revisao
Argumentos:
{}

Quando precisar usar uma ferramenta, responda SOMENTE com JSON válido neste formato:

{
  "tool": "nome_da_ferramenta",
  "arguments": {
    "campo": "valor"
  }
}

Não use markdown.
Não explique o JSON.
Se não precisar de ferramenta, responda normalmente.
"""


class JarvisAgent:
    def __init__(
        self,
        *,
        task_service: TaskService,
        agenda_service: AgendaService,
        material_service: MaterialService,
        study_plan_service: StudyPlanService | None = None,
        learning_service: LearningService | None = None,
        review_service: ReviewService | None = None,
        gemma_client: GemmaClient | None = None,
        max_iterations: int = 3,
    ):
        self.task_service = task_service
        self.agenda_service = agenda_service
        self.material_service = material_service
        self.study_plan_service = study_plan_service
        self.learning_service = learning_service
        self.review_service = review_service
        self.gemma_client = gemma_client or GemmaClient()
        self.max_iterations = max_iterations

    async def ask(
        self,
        message: str,
        *,
        history: list[dict[str, Any]] | None = None,
        conversation_id: str | None = None,
    ) -> JarvisAskResponse:
        messages: list[dict[str, Any]] = [
            {"role": "system", "content": SYSTEM_PROMPT},
        ]
        messages.extend(self._normalize_history(history or []))
        messages.append({"role": "user", "content": message})

        tools_used: list[JarvisToolTrace] = []

        logger.info(
            "jarvis ask recebido conversation_id={} history_messages={} message={}",
            conversation_id,
            len(history or []),
            message,
        )

        for _ in range(self.max_iterations):
            response = await self.gemma_client.async_chat(
                messages=messages,
            )

            assistant_message = response.choices[0].message
            content = self._get_message_content(assistant_message) or ""

            manual_tool_call = self._parse_manual_tool_call(content)

            if not manual_tool_call:
                return JarvisAskResponse(
                    message=message,
                    conversation_id=conversation_id,
                    answer=content or "Não consegui gerar uma resposta.",
                    tools_used=tools_used,
                )

            name = manual_tool_call["tool"]
            arguments = manual_tool_call["arguments"]

            arguments, result = await self._parse_and_execute_tool(
                name=name,
                raw_arguments=json.dumps(arguments),
            )

            serialized_result = jsonable_encoder(result)

            tools_used.append(
                JarvisToolTrace(
                    name=name,
                    arguments=arguments,
                    result=serialized_result,
                )
            )

            logger.info(
                "tool calling manual name={} entrada={} saida={}",
                name,
                arguments,
                serialized_result,
            )

            messages.append(
                {
                    "role": "assistant",
                    "content": content,
                }
            )

            messages.append(
                {
                    "role": "user",
                    "content": (
                        "Resultado da ferramenta:\n"
                        f"{json.dumps(serialized_result, ensure_ascii=False)}\n\n"
                        "Agora responda ao usuário de forma natural e objetiva."
                    ),
                }
            )

        logger.warning("limite de iterações do agente atingido")

        return JarvisAskResponse(
            message=message,
            conversation_id=conversation_id,
            answer="Não consegui finalizar a resposta após executar as ferramentas necessárias.",
            tools_used=tools_used,
        )

    def _normalize_history(
        self,
        history: list[dict[str, Any]],
    ) -> list[dict[str, str]]:
        normalized: list[dict[str, str]] = []
        for item in history:
            role = item.get("role")
            content = item.get("content")
            if role not in {"user", "assistant"} or not content:
                continue
            normalized.append({"role": role, "content": str(content)})
        return normalized

    def _parse_manual_tool_call(
        self,
        content: str,
    ) -> dict[str, Any] | None:
        try:
            data = json.loads(content)
        except json.JSONDecodeError:
            return None

        if not isinstance(data, dict):
            return None

        tool = data.get("tool")
        arguments = data.get("arguments", {})

        if not tool:
            return None

        if not isinstance(arguments, dict):
            arguments = {}

        return {
            "tool": tool,
            "arguments": arguments,
        }

    async def _parse_and_execute_tool(
        self,
        *,
        name: str | None,
        raw_arguments: str | None,
    ) -> tuple[dict[str, Any], Any]:
        try:
            arguments = json.loads(raw_arguments or "{}")

            if not isinstance(arguments, dict):
                raise ValueError("argumentos devem ser um objeto JSON")

        except (json.JSONDecodeError, ValueError) as exc:
            logger.warning(
                "erro ao converter argumentos da tool name={} raw_arguments={} erro={}",
                name,
                raw_arguments,
                exc,
            )

            return {"raw_arguments": raw_arguments}, {
                "ok": False,
                "error": "Argumentos inválidos enviados pela IA.",
                "detail": str(exc),
            }

        try:
            result = await self._execute_tool(
                name=name,
                arguments=arguments,
            )

            return arguments, {
                "ok": True,
                "data": result,
            }

        except HTTPException as exc:
            logger.warning(
                "erro de negócio ao executar tool name={} arguments={} status={} detail={}",
                name,
                arguments,
                exc.status_code,
                exc.detail,
            )

            return arguments, {
                "ok": False,
                "status_code": exc.status_code,
                "error": exc.detail,
            }

        except (ValidationError, ValueError, TypeError) as exc:
            logger.warning(
                "erro de validação ao executar tool name={} arguments={} erro={}",
                name,
                arguments,
                exc,
            )

            return arguments, {
                "ok": False,
                "status_code": status.HTTP_400_BAD_REQUEST,
                "error": str(exc),
            }

        except Exception as exc:
            logger.exception(
                "erro inesperado ao executar tool name={} arguments={}",
                name,
                arguments,
            )

            return arguments, {
                "ok": False,
                "status_code": status.HTTP_500_INTERNAL_SERVER_ERROR,
                "error": "Erro interno ao executar ferramenta.",
                "detail": str(exc),
            }

    async def _execute_tool(
        self,
        *,
        name: str | None,
        arguments: dict[str, Any],
    ) -> Any:
        tool_map = {
            "consultar_agenda": self._tool_consultar_agenda,
            "listar_tarefas": self._tool_listar_tarefas,
            "adicionar_tarefa": self._tool_adicionar_tarefa,
            "concluir_tarefa": self._tool_concluir_tarefa,
            "buscar_material_rag": self._tool_buscar_material_rag,
            "gerar_plano_estudos": self._tool_gerar_plano_estudos,
            "gerar_exercicios": self._tool_gerar_exercicios,
            "iniciar_active_recall": self._tool_iniciar_active_recall,
            "avaliar_resposta_active_recall": self._tool_avaliar_resposta_active_recall,
            "recomendar_revisao": self._tool_recomendar_revisao,
        }

        if name not in tool_map:
            raise ValueError(f"Tool desconhecida: {name}")

        return await tool_map[name](arguments)

    async def _tool_consultar_agenda(
        self,
        arguments: dict[str, Any],
    ) -> Any:
        return await self.agenda_service.consultar_agenda(
            start_date=self._parse_date(arguments.get("start_date")),
            end_date=self._parse_date(arguments.get("end_date")),
            event_type=arguments.get("event_type"),
            subject=arguments.get("subject"),
        )

    async def _tool_listar_tarefas(
        self,
        arguments: dict[str, Any],
    ) -> Any:
        return await self.task_service.listar_tarefas(
            status_filter=arguments.get("status"),
            priority=arguments.get("priority"),
            subject=arguments.get("subject"),
        )

    async def _tool_adicionar_tarefa(
        self,
        arguments: dict[str, Any],
    ) -> Any:
        payload = TaskCreate(**arguments)
        return await self.task_service.adicionar_tarefa(payload)

    async def _tool_concluir_tarefa(
        self,
        arguments: dict[str, Any],
    ) -> Any:
        task_id = arguments.get("task_id")

        if task_id is None:
            raise ValueError("task_id é obrigatório")

        return await self.task_service.concluir_tarefa(int(task_id))

    async def _tool_buscar_material_rag(
        self,
        arguments: dict[str, Any],
    ) -> Any:
        payload = MaterialAskRequest(**arguments)
        return await self.material_service.buscar_material_rag(payload)

    async def _tool_gerar_plano_estudos(
        self,
        arguments: dict[str, Any],
    ) -> Any:
        if self.study_plan_service is None:
            raise ValueError("StudyPlanService não configurado para o agente")

        payload = StudyPlanRequest(**arguments)
        return await self.study_plan_service.generate_plan(payload)

    async def _tool_gerar_exercicios(
        self,
        arguments: dict[str, Any],
    ) -> Any:
        if self.learning_service is None:
            raise ValueError("LearningService não configurado para o agente")

        payload = ExerciseGenerationRequest(**arguments)
        return await self.learning_service.generate_exercises(payload)

    async def _tool_iniciar_active_recall(
        self,
        arguments: dict[str, Any],
    ) -> Any:
        if self.learning_service is None:
            raise ValueError("LearningService não configurado para o agente")

        payload = ActiveRecallStartRequest(**arguments)
        return await self.learning_service.start_active_recall(payload)

    async def _tool_avaliar_resposta_active_recall(
        self,
        arguments: dict[str, Any],
    ) -> Any:
        if self.learning_service is None:
            raise ValueError("LearningService não configurado para o agente")

        payload = ActiveRecallAnswerRequest(**arguments)
        return await self.learning_service.evaluate_active_recall(payload)

    async def _tool_recomendar_revisao(
        self,
        arguments: dict[str, Any],
    ) -> Any:
        if self.review_service is None:
            raise ValueError("ReviewService não configurado para o agente")

        return await self.review_service.get_review_recommendations()

    def _parse_date(self, value: Any) -> date | None:
        if value is None:
            return None

        if isinstance(value, date):
            return value

        return date.fromisoformat(str(value))

    def _get_message_content(
        self,
        message: Any,
    ) -> str | None:
        if isinstance(message, dict):
            return message.get("content")

        return getattr(message, "content", None)
