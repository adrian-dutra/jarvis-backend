from collections import defaultdict
from datetime import datetime, timezone

from loguru import logger

from app.models.learning_attempt import LearningAttempt
from app.repositories.learning_attempt_repository import LearningAttemptRepository
from app.schemas.learning_schema import (
    ReviewRecommendation,
    ReviewRecommendationResponse,
    ReviewPriority,
)


class ReviewService:
    def __init__(self, repository: LearningAttemptRepository):
        self.repository = repository

    async def get_review_recommendations(self) -> ReviewRecommendationResponse:
        attempts = await self.repository.list_review_attempts()
        grouped: dict[str, list[LearningAttempt]] = defaultdict(list)
        for attempt in attempts:
            grouped[attempt.topic].append(attempt)

        recommendations = [
            self._recommendation_for_topic(topic, topic_attempts)
            for topic, topic_attempts in grouped.items()
        ]
        recommendations.sort(
            key=lambda item: (
                {"alta": 0, "media": 1, "baixa": 2}[item.priority],
                item.average_score,
                item.topic,
            )
        )

        logger.info(
            "recomendações de revisão geradas attempts={} recommendations={}",
            len(attempts),
            len(recommendations),
        )
        return ReviewRecommendationResponse(
            recommendations=recommendations,
            generated_at=self._utc_now(),
        )

    def _recommendation_for_topic(
        self,
        topic: str,
        attempts: list[LearningAttempt],
    ) -> ReviewRecommendation:
        scores = [attempt.score or 0.0 for attempt in attempts]
        average_score = round(sum(scores) / len(scores), 2) if scores else 0.0
        incorrect_count = sum(
            1 for attempt in attempts if attempt.classification == "incorreta"
        )
        partial_count = sum(
            1
            for attempt in attempts
            if attempt.classification == "parcialmente_correta"
        )
        priority = self._priority(
            average_score=average_score,
            incorrect_count=incorrect_count,
            partial_count=partial_count,
        )

        reason = (
            f"O tema teve {len(attempts)} tentativa(s) com dificuldade, "
            f"média {average_score}, {incorrect_count} incorreta(s) e "
            f"{partial_count} parcialmente correta(s)."
        )
        return ReviewRecommendation(
            topic=topic,
            priority=priority,
            reason=reason,
            attempts_count=len(attempts),
            average_score=average_score,
        )

    def _priority(
        self,
        *,
        average_score: float,
        incorrect_count: int,
        partial_count: int,
    ) -> ReviewPriority:
        if average_score < 0.4 or incorrect_count >= 2:
            return "alta"
        if average_score < 0.7 or partial_count > 0:
            return "media"
        return "baixa"

    def _utc_now(self) -> datetime:
        return datetime.now(timezone.utc).replace(tzinfo=None)
