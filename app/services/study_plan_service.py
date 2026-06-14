import json
from datetime import date, datetime, timedelta
from typing import Any
from zoneinfo import ZoneInfo

from fastapi import HTTPException, status
from loguru import logger
from pydantic import ValidationError

from app.core.config import get_settings
from app.llm.gemma_client import GemmaClient
from app.schemas.agenda_schema import AgendaOccurrence
from app.schemas.material_schema import MaterialAskRequest, MaterialAskResponse
from app.schemas.study_plan_schema import (
    StudyPlanRequest,
    StudyPlanResponse,
    StudyPlanSource,
)
from app.services.agenda_service import AgendaService
from app.services.material_service import MaterialService
from app.services.task_service import TaskService


MAX_CONTEXT_ITEMS = 5
SUMMARY_LIMIT = 280


class StudyPlanService:
    def __init__(
        self,
        *,
        agenda_service: AgendaService,
        task_service: TaskService,
        material_service: MaterialService,
        gemma_client: GemmaClient | None = None,
    ):
        self.agenda_service = agenda_service
        self.task_service = task_service
        self.material_service = material_service
        self.gemma_client = gemma_client or GemmaClient()
        self.settings = get_settings()
        self.timezone = ZoneInfo(self.settings.timezone)

    async def generate_plan(self, request: StudyPlanRequest) -> StudyPlanResponse:
        today = self._today()
        end_date = request.target_date or (today + timedelta(days=7))
        if end_date < today:
            end_date = today

        logger.info(
            "planejamento de estudos recebido objective={} target_date={} available_minutes={}",
            request.objective,
            request.target_date,
            request.available_minutes,
        )

        warnings: list[str] = []
        agenda_sources = await self._get_agenda_sources(
            start_date=today,
            end_date=end_date,
            warnings=warnings,
        )
        task_sources = await self._get_task_sources(warnings=warnings)
        material_response = await self._get_material_response(request, warnings=warnings)
        material_sources = self._material_sources(material_response)
        if not material_sources:
            warnings.append("Nenhum material relevante foi recuperado pelo RAG.")

        prompt = self._build_prompt(
            request=request,
            agenda_sources=agenda_sources,
            task_sources=task_sources,
            material_sources=material_sources,
            material_answer=material_response.answer if material_response else None,
            warnings=warnings,
        )

        try:
            response = await self.gemma_client.async_chat(
                messages=[{"role": "user", "content": prompt}],
                temperature=0.2,
            )
            content = response.choices[0].message.content or ""
        except Exception as exc:
            logger.exception("erro ao chamar Gemma no planejamento de estudos")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Erro ao gerar plano de estudos com Gemma.",
            ) from exc

        try:
            llm_data = self._parse_llm_json(content)
            llm_data = {
                key: llm_data[key]
                for key in ("priorities", "study_blocks", "next_action", "llm_summary")
                if key in llm_data
            }
            plan = StudyPlanResponse(
                objective=request.objective,
                agenda_considered=agenda_sources,
                tasks_considered=task_sources,
                materials_considered=material_sources,
                warnings=warnings,
                **llm_data,
            )
        except (ValidationError, ValueError, TypeError) as exc:
            logger.warning(
                "resposta inválida da LLM no planejamento erro={} content={}",
                exc,
                content[:500],
            )
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="A Gemma retornou um plano de estudos em formato inválido.",
            ) from exc

        logger.info(
            "planejamento de estudos gerado priorities={} blocks={} agenda={} tasks={} materials={} warnings={}",
            len(plan.priorities),
            len(plan.study_blocks),
            len(plan.agenda_considered),
            len(plan.tasks_considered),
            len(plan.materials_considered),
            len(plan.warnings),
        )
        return plan

    async def _get_agenda_sources(
        self,
        *,
        start_date: date,
        end_date: date,
        warnings: list[str],
    ) -> list[StudyPlanSource]:
        try:
            occurrences = await self.agenda_service.consultar_agenda(
                start_date=start_date,
                end_date=end_date,
            )
        except Exception as exc:
            logger.exception("erro ao consultar agenda para planejamento")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Erro ao consultar agenda para o plano de estudos.",
            ) from exc

        if not occurrences:
            warnings.append("Nenhum evento de agenda encontrado no período.")

        return [
            self._agenda_source(occurrence)
            for occurrence in occurrences[:MAX_CONTEXT_ITEMS]
        ]

    async def _get_task_sources(self, *, warnings: list[str]) -> list[StudyPlanSource]:
        try:
            tasks = await self.task_service.listar_tarefas_pendentes()
        except Exception as exc:
            logger.exception("erro ao consultar tarefas para planejamento")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Erro ao consultar tarefas para o plano de estudos.",
            ) from exc

        if not tasks:
            warnings.append("Nenhuma tarefa pendente encontrada.")

        return [self._task_source(task) for task in tasks[:MAX_CONTEXT_ITEMS]]

    async def _get_material_response(
        self,
        request: StudyPlanRequest,
        *,
        warnings: list[str],
    ) -> MaterialAskResponse | None:
        query = request.material_query or request.objective
        try:
            return await self.material_service.buscar_material_rag(
                MaterialAskRequest(question=query, method="hybrid", k=5, min_score=0.15)
            )
        except HTTPException as exc:
            logger.warning(
                "RAG indisponível para planejamento status={} detail={}",
                exc.status_code,
                exc.detail,
            )
            warnings.append("Não foi possível recuperar materiais pelo RAG.")
            return None
        except Exception:
            logger.exception("erro inesperado no RAG para planejamento")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Erro ao recuperar materiais para o plano de estudos.",
            )

    def _agenda_source(self, occurrence: AgendaOccurrence) -> StudyPlanSource:
        subject = f" disciplina={occurrence.subject}" if occurrence.subject else ""
        end_at = f" até {occurrence.end_at}" if occurrence.end_at else ""
        summary = (
            f"{occurrence.event_type}{subject} em {occurrence.start_at}{end_at}."
        )
        if occurrence.description:
            summary = f"{summary} {occurrence.description}"

        return StudyPlanSource(
            source_type="agenda",
            reference=f"agenda:{occurrence.event_id}",
            title=occurrence.title,
            summary=self._truncate(summary),
        )

    def _task_source(self, task: Any) -> StudyPlanSource:
        due_date = f" prazo={task.due_date}" if getattr(task, "due_date", None) else ""
        subject = f" disciplina={task.subject}" if getattr(task, "subject", None) else ""
        description = getattr(task, "description", None) or "Sem descrição."
        summary = (
            f"prioridade={task.priority}{subject}{due_date}. {description}"
        )
        return StudyPlanSource(
            source_type="task",
            reference=f"task:{task.id}",
            title=task.title,
            summary=self._truncate(summary),
        )

    def _material_sources(
        self,
        response: MaterialAskResponse | None,
    ) -> list[StudyPlanSource]:
        if response is None:
            return []

        return [
            StudyPlanSource(
                source_type="material",
                reference=(
                    f"material:{source.material_name}#chunk-{source.chunk_index}"
                ),
                title=source.material_name,
                summary=self._truncate(source.text),
            )
            for source in response.sources[:MAX_CONTEXT_ITEMS]
        ]

    def _build_prompt(
        self,
        *,
        request: StudyPlanRequest,
        agenda_sources: list[StudyPlanSource],
        task_sources: list[StudyPlanSource],
        material_sources: list[StudyPlanSource],
        material_answer: str | None,
        warnings: list[str],
    ) -> str:
        context = {
            "objective": request.objective,
            "target_date": request.target_date.isoformat()
            if request.target_date
            else None,
            "available_minutes": request.available_minutes,
            "agenda": [source.model_dump() for source in agenda_sources],
            "tasks": [source.model_dump() for source in task_sources],
            "materials": [source.model_dump() for source in material_sources],
            "material_answer": material_answer,
            "warnings": warnings,
        }

        return (
            "Você é o JARVIS Acadêmico. Gere um plano de estudos em português, "
            "objetivo e fácil de explicar em apresentação acadêmica.\n"
            "Use somente o contexto fornecido. Se alguma fonte estiver vazia, adapte o plano "
            "e considere os avisos.\n\n"
            "Retorne SOMENTE JSON válido com estes campos:\n"
            "{\n"
            '  "priorities": [{"title": "...", "level": "low|medium|high", '
            '"justification": "...", "related_sources": ["..."]}],\n'
            '  "study_blocks": [{"order": 1, "duration_minutes": 30, '
            '"focus": "...", "activity": "...", "related_sources": ["..."], '
            '"justification": "..."}],\n'
            '  "next_action": "...",\n'
            '  "llm_summary": "..."\n'
            "}\n\n"
            "Regras:\n"
            "- A soma aproximada dos blocos deve respeitar available_minutes.\n"
            "- Cada prioridade deve ter justificativa.\n"
            "- Use related_sources com as references do contexto quando possível.\n"
            "- Não inclua agenda_considered, tasks_considered, materials_considered, "
            "objective ou warnings no JSON; esses campos serão preenchidos pelo sistema.\n\n"
            f"Contexto:\n{json.dumps(context, ensure_ascii=False, default=str)}"
        )

    def _parse_llm_json(self, content: str) -> dict[str, Any]:
        clean_content = content.strip()
        if clean_content.startswith("```"):
            clean_content = clean_content.strip("`").strip()
            if clean_content.lower().startswith("json"):
                clean_content = clean_content[4:].strip()

        data = json.loads(clean_content)
        if not isinstance(data, dict):
            raise ValueError("Resposta da LLM deve ser um objeto JSON.")

        return data

    def _truncate(self, value: str) -> str:
        normalized = " ".join(value.split())
        if len(normalized) <= SUMMARY_LIMIT:
            return normalized
        return f"{normalized[: SUMMARY_LIMIT - 3]}..."

    def _today(self) -> date:
        return datetime.now(self.timezone).date()
