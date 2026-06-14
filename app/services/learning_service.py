import json
from datetime import datetime, timezone
from typing import Any

from fastapi import HTTPException, status
from loguru import logger
from pydantic import BaseModel, Field, ValidationError

from app.llm.gemma_client import GemmaClient
from app.models.learning_attempt import LearningAttempt
from app.repositories.learning_attempt_repository import LearningAttemptRepository
from app.schemas.learning_schema import (
    ActiveRecallAnswerRequest,
    ActiveRecallEvaluationResponse,
    ActiveRecallQuestionResponse,
    ActiveRecallStartRequest,
    ExerciseGenerationRequest,
    ExerciseGenerationResponse,
    ExerciseItem,
    LearningSource,
)
from app.schemas.material_schema import MaterialAskRequest, MaterialAskResponse
from app.services.material_service import MaterialService


class _ExerciseLLMResponse(BaseModel):
    exercises: list[ExerciseItem] = Field(default_factory=list)


class _ActiveRecallQuestionLLMResponse(BaseModel):
    question: str
    expected_answer: str


class LearningService:
    def __init__(
        self,
        *,
        material_service: MaterialService,
        attempt_repository: LearningAttemptRepository,
        gemma_client: GemmaClient | None = None,
    ):
        self.material_service = material_service
        self.attempt_repository = attempt_repository
        self.gemma_client = gemma_client or GemmaClient()

    async def generate_exercises(
        self,
        request: ExerciseGenerationRequest,
    ) -> ExerciseGenerationResponse:
        logger.info(
            "geração de exercícios recebida topic={} quantity={} level={}",
            request.topic,
            request.quantity,
            request.level,
        )
        material_response = await self._retrieve_context(request.topic)
        sources = self._sources_from_material_response(material_response)

        prompt = self._build_exercises_prompt(
            request=request,
            material_response=material_response,
            sources=sources,
        )
        content = await self._call_llm(prompt, "Erro ao gerar exercícios com Gemma.")

        try:
            llm_response = _ExerciseLLMResponse(**self._parse_json(content))
        except (ValidationError, ValueError, TypeError) as exc:
            logger.warning("resposta inválida da LLM nos exercícios erro={}", exc)
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="A Gemma retornou exercícios em formato inválido.",
            ) from exc

        exercises = llm_response.exercises[: request.quantity]
        logger.info(
            "exercícios gerados topic={} total={} sources={}",
            request.topic,
            len(exercises),
            len(sources),
        )
        return ExerciseGenerationResponse(
            topic=request.topic,
            level=request.level,
            exercises=exercises,
            sources=sources,
        )

    async def start_active_recall(
        self,
        request: ActiveRecallStartRequest,
    ) -> ActiveRecallQuestionResponse:
        logger.info(
            "active recall start recebido topic={} level={}",
            request.topic,
            request.level,
        )
        material_response = await self._retrieve_context(request.topic)
        sources = self._sources_from_material_response(material_response)
        prompt = self._build_active_recall_prompt(
            request=request,
            material_response=material_response,
            sources=sources,
        )
        content = await self._call_llm(
            prompt,
            "Erro ao gerar pergunta de active recall com Gemma.",
        )

        try:
            llm_response = _ActiveRecallQuestionLLMResponse(**self._parse_json(content))
        except (ValidationError, ValueError, TypeError) as exc:
            logger.warning("resposta inválida da LLM no active recall erro={}", exc)
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="A Gemma retornou pergunta de active recall em formato inválido.",
            ) from exc

        attempt = await self.attempt_repository.create_attempt(
            topic=request.topic,
            question=llm_response.question,
            expected_answer=llm_response.expected_answer,
            created_at=self._utc_now(),
        )
        logger.info(
            "active recall pergunta criada attempt_id={} topic={} sources={}",
            attempt.id,
            request.topic,
            len(sources),
        )
        return ActiveRecallQuestionResponse(
            question_id=attempt.id,
            topic=request.topic,
            level=request.level,
            question=llm_response.question,
            sources=sources,
        )

    async def evaluate_active_recall(
        self,
        request: ActiveRecallAnswerRequest,
    ) -> ActiveRecallEvaluationResponse:
        logger.info(
            "active recall answer recebido question_id={}",
            request.question_id,
        )
        attempt = await self.attempt_repository.get_attempt(request.question_id)
        if attempt is None:
            logger.warning(
                "tentativa de active recall não encontrada question_id={}",
                request.question_id,
            )
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Pergunta de active recall não encontrada.",
            )

        prompt = self._build_evaluation_prompt(
            attempt=attempt,
            user_answer=request.user_answer,
        )
        content = await self._call_llm(
            prompt,
            "Erro ao avaliar resposta de active recall com Gemma.",
        )

        try:
            evaluation = ActiveRecallEvaluationResponse(
                question_id=attempt.id,
                **self._parse_json(content),
            )
        except (ValidationError, ValueError, TypeError) as exc:
            logger.warning("resposta inválida da LLM na avaliação erro={}", exc)
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="A Gemma retornou avaliação em formato inválido.",
            ) from exc

        await self.attempt_repository.update_evaluation(
            attempt,
            user_answer=request.user_answer,
            classification=evaluation.classification,
            score=evaluation.score,
            feedback=evaluation.feedback,
        )
        logger.info(
            "active recall avaliado question_id={} classification={} score={}",
            attempt.id,
            evaluation.classification,
            evaluation.score,
        )
        return evaluation

    async def _retrieve_context(self, topic: str) -> MaterialAskResponse:
        try:
            response = await self.material_service.buscar_material_rag(
                MaterialAskRequest(
                    question=topic,
                    method="hybrid",
                    k=5,
                    min_score=0.15,
                )
            )
        except HTTPException:
            raise
        except Exception as exc:
            logger.exception("erro inesperado ao recuperar contexto de aprendizado")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Erro ao recuperar materiais para aprendizado.",
            ) from exc

        if not response.sources:
            logger.warning("nenhum material recuperado para aprendizado topic={}", topic)
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Nenhum material relevante foi encontrado para o tema informado.",
            )

        return response

    def _sources_from_material_response(
        self,
        response: MaterialAskResponse,
    ) -> list[LearningSource]:
        return [
            LearningSource(
                material_id=source.material_id,
                material_name=source.material_name,
                chunk_id=source.chunk_id,
                chunk_index=source.chunk_index,
                score=source.score,
                text=source.text,
            )
            for source in response.sources
        ]

    def _build_exercises_prompt(
        self,
        *,
        request: ExerciseGenerationRequest,
        material_response: MaterialAskResponse,
        sources: list[LearningSource],
    ) -> str:
        context = self._context_payload(
            topic=request.topic,
            material_response=material_response,
            sources=sources,
        )
        return (
            "Você é um tutor acadêmico. Gere exercícios em português usando apenas "
            "o contexto recuperado dos materiais.\n"
            "Retorne SOMENTE JSON válido neste formato:\n"
            '{"exercises": [{"question": "...", "exercise_type": "discursiva", '
            '"expected_answer": "..."}]}\n'
            f"Quantidade: {request.quantity}\n"
            f"Nível: {request.level}\n"
            "As respostas esperadas devem ser curtas e objetivas.\n\n"
            f"Contexto:\n{json.dumps(context, ensure_ascii=False, default=str)}"
        )

    def _build_active_recall_prompt(
        self,
        *,
        request: ActiveRecallStartRequest,
        material_response: MaterialAskResponse,
        sources: list[LearningSource],
    ) -> str:
        context = self._context_payload(
            topic=request.topic,
            material_response=material_response,
            sources=sources,
        )
        return (
            "Você é um tutor de active recall. Crie uma única pergunta aberta, "
            "clara e adequada ao nível do estudante, usando apenas o contexto.\n"
            "Retorne SOMENTE JSON válido neste formato:\n"
            '{"question": "...", "expected_answer": "..."}\n'
            f"Nível: {request.level}\n\n"
            f"Contexto:\n{json.dumps(context, ensure_ascii=False, default=str)}"
        )

    def _build_evaluation_prompt(
        self,
        *,
        attempt: LearningAttempt,
        user_answer: str,
    ) -> str:
        payload = {
            "topic": attempt.topic,
            "question": attempt.question,
            "expected_answer": attempt.expected_answer,
            "user_answer": user_answer,
        }
        return (
            "Você é um avaliador acadêmico. Compare a resposta do estudante com a "
            "resposta esperada. Seja objetivo e justo.\n"
            "Classifique como exatamente uma destas opções: correta, parcialmente_correta, incorreta.\n"
            "Retorne SOMENTE JSON válido neste formato:\n"
            "{\n"
            '  "classification": "correta|parcialmente_correta|incorreta",\n'
            '  "score": 0.0,\n'
            '  "feedback": "...",\n'
            '  "expected_answer_summary": "...",\n'
            '  "strengths": ["..."],\n'
            '  "improvements": ["..."],\n'
            '  "review_recommendation": "..."\n'
            "}\n\n"
            f"Dados:\n{json.dumps(payload, ensure_ascii=False, default=str)}"
        )

    def _context_payload(
        self,
        *,
        topic: str,
        material_response: MaterialAskResponse,
        sources: list[LearningSource],
    ) -> dict[str, Any]:
        return {
            "topic": topic,
            "rag_answer": material_response.answer,
            "sources": [source.model_dump() for source in sources],
        }

    async def _call_llm(self, prompt: str, error_message: str) -> str:
        try:
            response = await self.gemma_client.async_chat(
                messages=[{"role": "user", "content": prompt}],
                temperature=0.2,
            )
            return response.choices[0].message.content or ""
        except Exception as exc:
            logger.exception("erro ao chamar Gemma no módulo de aprendizado")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=error_message,
            ) from exc

    def _parse_json(self, content: str) -> dict[str, Any]:
        clean_content = content.strip()
        if clean_content.startswith("```"):
            clean_content = clean_content.strip("`").strip()
            if clean_content.lower().startswith("json"):
                clean_content = clean_content[4:].strip()

        data = json.loads(clean_content)
        if not isinstance(data, dict):
            raise ValueError("Resposta da LLM deve ser um objeto JSON.")
        return data

    def _utc_now(self) -> datetime:
        return datetime.now(timezone.utc).replace(tzinfo=None)
