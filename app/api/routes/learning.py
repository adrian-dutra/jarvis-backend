from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.connection import get_async_db
from app.repositories.learning_attempt_repository import LearningAttemptRepository
from app.repositories.material_repository import MaterialRepository
from app.schemas.learning_schema import (
    ActiveRecallAnswerRequest,
    ActiveRecallEvaluationResponse,
    ActiveRecallQuestionResponse,
    ActiveRecallStartRequest,
    ExerciseGenerationRequest,
    ExerciseGenerationResponse,
    ReviewRecommendationResponse,
)
from app.services.learning_service import LearningService
from app.services.material_service import MaterialService
from app.services.review_service import ReviewService


router = APIRouter(prefix="/learning", tags=["Aprendizado"])


def get_learning_service(db: AsyncSession = Depends(get_async_db)) -> LearningService:
    material_service = MaterialService(MaterialRepository(db))
    attempt_repository = LearningAttemptRepository(db)
    return LearningService(
        material_service=material_service,
        attempt_repository=attempt_repository,
    )


def get_review_service(db: AsyncSession = Depends(get_async_db)) -> ReviewService:
    return ReviewService(LearningAttemptRepository(db))


@router.post(
    "/exercises",
    response_model=ExerciseGenerationResponse,
    status_code=status.HTTP_200_OK,
    summary="Gerar exercícios a partir dos materiais",
    description="Gera exercícios usando contexto recuperado por RAG nos materiais indexados.",
    response_description="Lista de exercícios e fontes usadas como base.",
)
async def generate_exercises(
    payload: ExerciseGenerationRequest,
    service: LearningService = Depends(get_learning_service),
) -> ExerciseGenerationResponse:
    return await service.generate_exercises(payload)


@router.post(
    "/active-recall/start",
    response_model=ActiveRecallQuestionResponse,
    status_code=status.HTTP_200_OK,
    summary="Iniciar active recall",
    description="Gera uma pergunta interativa baseada nos materiais recuperados por RAG.",
    response_description="Pergunta criada e identificador para envio da resposta.",
)
async def start_active_recall(
    payload: ActiveRecallStartRequest,
    service: LearningService = Depends(get_learning_service),
) -> ActiveRecallQuestionResponse:
    return await service.start_active_recall(payload)


@router.post(
    "/active-recall/answer",
    response_model=ActiveRecallEvaluationResponse,
    status_code=status.HTTP_200_OK,
    summary="Avaliar resposta de active recall",
    description="Avalia a resposta do estudante e salva a tentativa para recomendações futuras.",
    response_description="Classificação, nota, feedback e recomendação de revisão.",
)
async def answer_active_recall(
    payload: ActiveRecallAnswerRequest,
    service: LearningService = Depends(get_learning_service),
) -> ActiveRecallEvaluationResponse:
    return await service.evaluate_active_recall(payload)


@router.get(
    "/review-recommendations",
    response_model=ReviewRecommendationResponse,
    status_code=status.HTTP_200_OK,
    summary="Recomendar revisões",
    description="Agrupa tentativas ruins de active recall e recomenda temas para revisão.",
    response_description="Recomendações de revisão por tema.",
)
async def get_review_recommendations(
    service: ReviewService = Depends(get_review_service),
) -> ReviewRecommendationResponse:
    return await service.get_review_recommendations()
