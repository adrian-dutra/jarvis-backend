from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


LearningLevel = Literal["facil", "medio", "dificil"]
ActiveRecallClassification = Literal["correta", "parcialmente_correta", "incorreta"]
ReviewPriority = Literal["alta", "media", "baixa"]


class LearningSource(BaseModel):
    material_id: int = Field(description="Identificador do material usado como fonte.", examples=[1])
    material_name: str = Field(description="Nome do material.", examples=["rag.pdf"])
    chunk_id: int = Field(description="Identificador do chunk recuperado.", examples=[10])
    chunk_index: int = Field(description="Posição do chunk dentro do material.", examples=[2])
    score: float = Field(description="Score de recuperação do chunk.", examples=[0.87])
    text: str = Field(description="Trecho recuperado usado como contexto.")


class ExerciseGenerationRequest(BaseModel):
    topic: str = Field(
        ...,
        min_length=1,
        description="Tema dos exercícios.",
        examples=["RAG e embeddings"],
    )
    quantity: int = Field(
        default=5,
        ge=1,
        le=10,
        description="Quantidade de exercícios a gerar.",
        examples=[5],
    )
    level: LearningLevel = Field(
        default="medio",
        description="Nível de dificuldade dos exercícios.",
        examples=["medio"],
    )

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "topic": "RAG e embeddings",
                "quantity": 5,
                "level": "medio",
            }
        }
    )


class ExerciseItem(BaseModel):
    question: str = Field(description="Enunciado do exercício.")
    exercise_type: str = Field(
        description="Tipo da questão, por exemplo discursiva, objetiva ou comparação.",
        examples=["discursiva"],
    )
    expected_answer: str = Field(description="Resposta esperada para o exercício.")


class ExerciseGenerationResponse(BaseModel):
    topic: str = Field(description="Tema usado na geração.")
    level: LearningLevel = Field(description="Nível solicitado.")
    exercises: list[ExerciseItem] = Field(description="Exercícios gerados.")
    sources: list[LearningSource] = Field(description="Documentos/chunks usados como base.")


class ActiveRecallStartRequest(BaseModel):
    topic: str = Field(
        ...,
        min_length=1,
        description="Tema da pergunta de active recall.",
        examples=["RAG e embeddings"],
    )
    level: LearningLevel = Field(
        default="medio",
        description="Nível de dificuldade da pergunta.",
        examples=["medio"],
    )

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "topic": "RAG e embeddings",
                "level": "medio",
            }
        }
    )


class ActiveRecallQuestionResponse(BaseModel):
    question_id: int = Field(description="Identificador da pergunta/tentativa.", examples=[1])
    topic: str = Field(description="Tema da pergunta.")
    level: LearningLevel = Field(description="Nível da pergunta.")
    question: str = Field(description="Pergunta gerada para o estudante.")
    sources: list[LearningSource] = Field(description="Documentos/chunks usados como base.")


class ActiveRecallAnswerRequest(BaseModel):
    question_id: int = Field(description="Identificador retornado no start.", examples=[1])
    user_answer: str = Field(
        ...,
        min_length=1,
        description="Resposta do estudante.",
        examples=["RAG recupera documentos externos antes de gerar a resposta."],
    )

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "question_id": 1,
                "user_answer": "RAG busca informações externas e usa esse contexto na geração.",
            }
        }
    )


class ActiveRecallEvaluationResponse(BaseModel):
    question_id: int = Field(description="Identificador da pergunta/tentativa.")
    classification: ActiveRecallClassification = Field(description="Classificação da resposta.")
    score: float = Field(ge=0.0, le=1.0, description="Nota entre 0 e 1.")
    feedback: str = Field(description="Feedback objetivo para o estudante.")
    expected_answer_summary: str = Field(description="Resumo da resposta esperada.")
    strengths: list[str] = Field(description="Pontos fortes da resposta.")
    improvements: list[str] = Field(description="Pontos a melhorar.")
    review_recommendation: str = Field(description="Recomendação de revisão.")


class ReviewRecommendation(BaseModel):
    topic: str = Field(description="Tema recomendado para revisão.")
    priority: ReviewPriority = Field(description="Prioridade da revisão.")
    reason: str = Field(description="Justificativa da recomendação.")
    attempts_count: int = Field(description="Quantidade de tentativas ruins consideradas.")
    average_score: float = Field(description="Média das notas das tentativas consideradas.")


class ReviewRecommendationResponse(BaseModel):
    recommendations: list[ReviewRecommendation] = Field(
        description="Recomendações de revisão agrupadas por tema."
    )
    generated_at: datetime = Field(description="Data de geração das recomendações.")
