from datetime import datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.learning_attempt import LearningAttempt


class LearningAttemptRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def create_attempt(
        self,
        *,
        topic: str,
        question: str,
        expected_answer: str,
        created_at: datetime,
    ) -> LearningAttempt:
        attempt = LearningAttempt(
            topic=topic,
            question=question,
            expected_answer=expected_answer,
            created_at=created_at,
        )
        self.db.add(attempt)
        await self.db.commit()
        await self.db.refresh(attempt)
        return attempt

    async def get_attempt(self, attempt_id: int) -> LearningAttempt | None:
        return await self.db.get(LearningAttempt, attempt_id)

    async def update_evaluation(
        self,
        attempt: LearningAttempt,
        *,
        user_answer: str,
        classification: str,
        score: float,
        feedback: str,
    ) -> LearningAttempt:
        attempt.user_answer = user_answer
        attempt.classification = classification
        attempt.score = score
        attempt.feedback = feedback
        await self.db.commit()
        await self.db.refresh(attempt)
        return attempt

    async def list_review_attempts(self) -> list[LearningAttempt]:
        statement = (
            select(LearningAttempt)
            .where(
                LearningAttempt.classification.in_(
                    ["incorreta", "parcialmente_correta"]
                )
            )
            .order_by(LearningAttempt.created_at.desc())
        )
        result = await self.db.execute(statement)
        return list(result.scalars().all())
