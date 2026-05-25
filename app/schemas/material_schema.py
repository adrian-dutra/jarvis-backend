from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class MaterialSummary(BaseModel):
    id: int = Field(description="Identificador único do material.", examples=[1])
    original_filename: str = Field(description="Nome original do arquivo enviado.", examples=["regressao_logistica.pdf"])
    stored_filename: str = Field(description="Nome físico gerado com UUID para evitar conflitos.", examples=["550e8400-e29b-41d4-a716-446655440000.pdf"])
    subject: str | None = Field(default=None, description="Disciplina ou assunto associado ao material.", examples=["Inteligência Artificial"])
    file_type: str | None = Field(default=None, description="Extensão ou tipo do arquivo.", examples=["pdf"])
    content_type: str | None = Field(default=None, description="Content-Type recebido no upload.", examples=["application/pdf"])
    file_size: int | None = Field(default=None, description="Tamanho do arquivo em bytes.", examples=[204800])
    file_path: str = Field(description="Caminho físico onde o arquivo foi preservado.", examples=["uploads/550e8400-e29b-41d4-a716-446655440000.pdf"])
    indexed: bool = Field(description="Indica se o material já foi processado em chunks.", examples=[True])
    chunk_count: int = Field(description="Quantidade de chunks persistidos para recuperação RAG.", examples=[12])
    created_at: datetime = Field(description="Data de criação do registro.", examples=["2026-05-24T12:00:00"])
    updated_at: datetime = Field(description="Data da última atualização.", examples=["2026-05-24T12:05:00"])

    model_config = ConfigDict(
        from_attributes=True,
        json_schema_extra={
            "example": {
                "id": 1,
                "original_filename": "regressao_logistica.pdf",
                "stored_filename": "550e8400-e29b-41d4-a716-446655440000.pdf",
                "subject": "Inteligência Artificial",
                "file_type": "pdf",
                "content_type": "application/pdf",
                "file_size": 204800,
                "file_path": "uploads/550e8400-e29b-41d4-a716-446655440000.pdf",
                "indexed": True,
                "chunk_count": 12,
                "created_at": "2026-05-24T12:00:00",
                "updated_at": "2026-05-24T12:05:00",
            }
        },
    )


class MaterialDetail(MaterialSummary):
    extracted_text: str | None = Field(
        default=None,
        description="Texto extraído do arquivo, mantido para debug e apresentação. O RAG consulta os chunks.",
        examples=["Regressão logística é um modelo utilizado para classificação..."],
    )

    model_config = ConfigDict(
        from_attributes=True,
        json_schema_extra={
            "example": {
                "id": 1,
                "original_filename": "regressao_logistica.pdf",
                "stored_filename": "550e8400-e29b-41d4-a716-446655440000.pdf",
                "subject": "Inteligência Artificial",
                "file_type": "pdf",
                "content_type": "application/pdf",
                "file_size": 204800,
                "file_path": "uploads/550e8400-e29b-41d4-a716-446655440000.pdf",
                "indexed": True,
                "chunk_count": 12,
                "created_at": "2026-05-24T12:00:00",
                "updated_at": "2026-05-24T12:05:00",
                "extracted_text": "Regressão logística é um modelo utilizado para classificação...",
            }
        },
    )


class MaterialIndexResponse(BaseModel):
    material: MaterialSummary = Field(description="Material atualizado após indexação.")
    chunk_count: int = Field(description="Quantidade de chunks gerados.", examples=[12])

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "material": MaterialSummary.model_config["json_schema_extra"]["example"],
                "chunk_count": 12,
            }
        }
    )


class MaterialAskRequest(BaseModel):
    question: str = Field(
        ...,
        min_length=1,
        description="Pergunta do usuário sobre os materiais indexados.",
        examples=["Explique regressão logística"],
    )
    material_id: int | None = Field(
        default=None,
        description="Material específico para consulta. Quando omitido, busca apenas materiais indexados.",
        examples=[1],
    )
    method: Literal["bm25", "dense", "hybrid"] = Field(
        default="hybrid",
        description="Método de recuperação: BM25, dense com embeddings ou híbrido.",
        examples=["hybrid"],
    )
    k: int = Field(
        default=5,
        ge=1,
        le=10,
        description="Número máximo de chunks recuperados.",
        examples=[5],
    )
    alpha: float = Field(
        default=0.6,
        ge=0.0,
        le=1.0,
        description="Peso do score dense na recuperação híbrida.",
        examples=[0.6],
    )
    min_score: float = Field(
        default=0.15,
        ge=0.0,
        le=1.0,
        description="Score mínimo para considerar o contexto útil.",
        examples=[0.15],
    )

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "question": "Explique regressão logística",
                "material_id": 1,
                "method": "hybrid",
                "k": 5,
                "alpha": 0.6,
                "min_score": 0.15,
            }
        }
    )


class MaterialSource(BaseModel):
    material_id: int = Field(description="Identificador do material de origem.", examples=[1])
    material_name: str = Field(description="Nome original do material.", examples=["regressao_logistica.pdf"])
    chunk_id: int = Field(description="Identificador do chunk recuperado.", examples=[10])
    chunk_index: int = Field(description="Posição do chunk dentro do material.", examples=[3])
    text: str = Field(description="Trecho recuperado utilizado como contexto.", examples=["Regressão logística modela a probabilidade de uma classe..."])
    score: float = Field(description="Score final de recuperação.", examples=[0.87])

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "material_id": 1,
                "material_name": "regressao_logistica.pdf",
                "chunk_id": 10,
                "chunk_index": 3,
                "text": "Regressão logística modela a probabilidade de uma classe...",
                "score": 0.87,
            }
        }
    )


class MaterialAskResponse(BaseModel):
    question: str = Field(description="Pergunta enviada pelo usuário.", examples=["Explique regressão logística"])
    answer: str = Field(description="Resposta gerada com base apenas nos chunks recuperados.", examples=["Regressão logística é um modelo usado para classificação..."])
    method: Literal["bm25", "dense", "hybrid"] = Field(description="Método de recuperação utilizado.", examples=["hybrid"])
    sources: list[MaterialSource] = Field(description="Chunks utilizados como fontes da resposta.")

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "question": "Explique regressão logística",
                "answer": "Regressão logística é um modelo usado para classificação...",
                "method": "hybrid",
                "sources": [
                    {
                        "material_id": 1,
                        "material_name": "regressao_logistica.pdf",
                        "chunk_id": 10,
                        "chunk_index": 3,
                        "text": "Regressão logística modela a probabilidade de uma classe...",
                        "score": 0.87,
                    }
                ],
            }
        }
    )
