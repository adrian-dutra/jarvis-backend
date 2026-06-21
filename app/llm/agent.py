import json
from datetime import date
from typing import Any

from fastapi import HTTPException, status
from fastapi.encoders import jsonable_encoder
from loguru import logger
from pydantic import ValidationError

from app.llm.gemma_client import GemmaClient
from app.schemas.jarvis_schema import JarvisAskResponse, JarvisToolTrace
from app.schemas.agenda_schema import AgendaEventCreate
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
  "status": "pending/completed ou null",
  "priority": "low/medium/high ou null",
  "subject": "matéria ou null"
}

3. adicionar_tarefa
Argumentos:
{
  "title": "título da tarefa",
  "description": "descrição",
  "subject": "matéria",
  "priority": "low/medium/high",
  "due_date": "YYYY-MM-DD ou null"
}

4. adicionar_evento_agenda
Argumentos:
{
  "title": "título do evento",
  "description": "descrição",
  "event_type": "class/exam/meeting/assignment/activity/other",
  "subject": "matéria",
  "location": "local ou null",
  "start_at": "YYYY-MM-DDTHH:MM:SS",
  "end_at": "YYYY-MM-DDTHH:MM:SS ou null",
  "all_day": false,
  "recurrence_type": "none/weekly",
  "recurrence_weekdays": [0, 1, 2] ou null,
  "recurrence_until": "YYYY-MM-DD ou null"
}

Use adicionar_evento_agenda quando o usuário pedir para criar/cadastrar/marcar
um evento, estudo, aula, prova, reunião ou compromisso na agenda.
Use adicionar_tarefa apenas quando o usuário pedir uma tarefa pendente.

5. concluir_tarefa
Argumentos:
{
  "task_id": 1
}

6. buscar_material_rag
Argumentos:
{
  "question": "pergunta do usuário"
}

7. gerar_plano_estudos
Argumentos:
{
  "objective": "objetivo do plano",
  "target_date": "YYYY-MM-DD ou null",
  "available_minutes": 120,
  "material_query": "consulta opcional para buscar materiais"
}

8. gerar_exercicios
Argumentos:
{
  "topic": "tema dos exercícios",
  "quantity": 5,
  "level": "facil/medio/dificil"
}

9. iniciar_active_recall
Argumentos:
{
  "topic": "tema da pergunta",
  "level": "facil/medio/dificil"
}

10. avaliar_resposta_active_recall
Argumentos:
{
  "question_id": 1,
  "user_answer": "resposta do estudante"
}

11. recomendar_revisao
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

            manual_tool_calls = self._parse_manual_tool_calls(content)

            if not manual_tool_calls:
                return JarvisAskResponse(
                    message=message,
                    conversation_id=conversation_id,
                    answer=content or "Não consegui gerar uma resposta.",
                    tools_used=tools_used,
                )

            tool_results: list[dict[str, Any]] = []
            for manual_tool_call in manual_tool_calls:
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
                tool_results.append(
                    {
                        "tool": name,
                        "arguments": arguments,
                        "result": serialized_result,
                    }
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
                    "content": "Vou consultar as ferramentas internas necessárias.",
                }
            )

            messages.append(
                {
                    "role": "user",
                    "content": (
                        "Resultados das ferramentas:\n"
                        f"{json.dumps(tool_results, ensure_ascii=False)}\n\n"
                        "Agora responda ao usuário de forma natural e objetiva. "
                        "Não inclua JSON de ferramentas na resposta final."
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
            if role == "assistant" and self._parse_manual_tool_calls(str(content)):
                continue
            normalized.append({"role": role, "content": str(content)})
        return normalized

    def _parse_manual_tool_call(
        self,
        content: str,
    ) -> dict[str, Any] | None:
        calls = self._parse_manual_tool_calls(content)
        return calls[0] if calls else None

    def _parse_manual_tool_calls(
        self,
        content: str,
    ) -> list[dict[str, Any]]:
        candidates = self._extract_json_candidates(content)
        tool_calls: list[dict[str, Any]] = []
        for data in candidates:
            if isinstance(data, list):
                items = data
            else:
                items = [data]

            for item in items:
                tool_call = self._tool_call_from_data(item)
                if tool_call:
                    tool_calls.append(tool_call)

        return tool_calls

    def _extract_json_candidates(self, content: str) -> list[Any]:
        decoder = json.JSONDecoder()
        candidates: list[Any] = []
        index = 0

        while index < len(content):
            next_object = content.find("{", index)
            next_array = content.find("[", index)
            starts = [position for position in (next_object, next_array) if position >= 0]
            if not starts:
                break

            start = min(starts)
            try:
                data, end = decoder.raw_decode(content[start:])
            except json.JSONDecodeError:
                index = start + 1
                continue

            candidates.append(data)
            index = start + end

        return candidates

    def _tool_call_from_data(self, data: Any) -> dict[str, Any] | None:
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
            "adicionar_evento_agenda": self._tool_adicionar_evento_agenda,
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
            event_type=self._normalize_agenda_event_type(arguments.get("event_type")),
            subject=arguments.get("subject"),
        )

    async def _tool_listar_tarefas(
        self,
        arguments: dict[str, Any],
    ) -> Any:
        return await self.task_service.listar_tarefas(
            status_filter=self._normalize_task_status(arguments.get("status")),
            priority=self._normalize_task_priority(arguments.get("priority")),
            subject=arguments.get("subject"),
        )

    async def _tool_adicionar_tarefa(
        self,
        arguments: dict[str, Any],
    ) -> Any:
        payload = TaskCreate(**self._normalize_task_create_arguments(arguments))
        return await self.task_service.adicionar_tarefa(payload)

    async def _tool_adicionar_evento_agenda(
        self,
        arguments: dict[str, Any],
    ) -> Any:
        payload = AgendaEventCreate(
            **self._normalize_agenda_event_create_arguments(arguments)
        )
        return await self.agenda_service.create_event(payload)

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

    def _normalize_agenda_event_type(self, value: Any) -> str | None:
        mapping = {
            "aula": "class",
            "class": "class",
            "classe": "class",
            "prova": "exam",
            "exam": "exam",
            "exame": "exam",
            "reuniao": "meeting",
            "reunião": "meeting",
            "meeting": "meeting",
            "trabalho": "assignment",
            "assignment": "assignment",
            "atividade": "activity",
            "activity": "activity",
            "outro": "other",
            "other": "other",
        }
        return self._normalize_mapped_value(value, mapping)

    def _normalize_task_status(self, value: Any) -> str | None:
        mapping = {
            "pendente": "pending",
            "pending": "pending",
            "concluida": "completed",
            "concluída": "completed",
            "completed": "completed",
            "todas": None,
            "todos": None,
            "all": None,
        }
        return self._normalize_mapped_value(value, mapping)

    def _normalize_task_priority(self, value: Any) -> str | None:
        mapping = {
            "baixa": "low",
            "low": "low",
            "media": "medium",
            "média": "medium",
            "medium": "medium",
            "alta": "high",
            "high": "high",
        }
        return self._normalize_mapped_value(value, mapping)

    def _normalize_task_create_arguments(
        self,
        arguments: dict[str, Any],
    ) -> dict[str, Any]:
        normalized = dict(arguments)
        if "priority" in normalized:
            normalized["priority"] = self._normalize_task_priority(
                normalized.get("priority")
            )
        return normalized

    def _normalize_agenda_event_create_arguments(
        self,
        arguments: dict[str, Any],
    ) -> dict[str, Any]:
        normalized = dict(arguments)
        normalized["event_type"] = (
            self._normalize_agenda_event_type(normalized.get("event_type"))
            or "activity"
        )

        recurrence_type = normalized.get("recurrence_type")
        if recurrence_type is not None:
            normalized["recurrence_type"] = self._normalize_recurrence_type(
                recurrence_type
            )

        if normalized.get("all_day") is None:
            normalized["all_day"] = False

        return normalized

    def _normalize_recurrence_type(self, value: Any) -> str:
        mapping = {
            "nenhuma": "none",
            "nao": "none",
            "não": "none",
            "none": "none",
            "semanal": "weekly",
            "weekly": "weekly",
        }
        return self._normalize_mapped_value(value, mapping) or "none"

    def _normalize_mapped_value(
        self,
        value: Any,
        mapping: dict[str, str | None],
    ) -> str | None:
        if value is None:
            return None

        normalized = str(value).strip().lower()
        if not normalized or normalized == "null":
            return None

        return mapping.get(normalized, normalized)

    def _get_message_content(
        self,
        message: Any,
    ) -> str | None:
        if isinstance(message, dict):
            return message.get("content")

        return getattr(message, "content", None)
