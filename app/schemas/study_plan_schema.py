from datetime import date
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


StudyPlanSourceType = Literal["agenda", "task", "material"]
StudyPlanPriorityLevel = Literal["low", "medium", "high"]


class StudyPlanRequest(BaseModel):
    objective: str = Field(
        ...,
        min_length=1,
        description="Objetivo do plano de estudos.",
        examples=["Montar um plano de estudos para a prova de IA"],
    )
    target_date: date | None = Field(
        default=None,
        description="Data alvo para o estudo ou avaliação.",
        examples=["2026-06-20"],
    )
    available_minutes: int = Field(
        default=120,
        ge=15,
        le=720,
        description="Tempo total disponível para estudar, em minutos.",
        examples=[120],
    )
    material_query: str | None = Field(
        default=None,
        min_length=1,
        description="Consulta opcional para buscar materiais no RAG.",
        examples=["RAG, embeddings, FAISS, BM25"],
    )

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "objective": "Montar um plano de estudos para a prova de IA",
                "target_date": "2026-06-20",
                "available_minutes": 120,
                "material_query": "RAG, embeddings, FAISS, BM25",
            }
        }
    )


class StudyPlanSource(BaseModel):
    source_type: StudyPlanSourceType = Field(
        description="Tipo da fonte considerada no planejamento.",
        examples=["material"],
    )
    reference: str = Field(
        description="Identificador ou nome curto da fonte.",
        examples=["material:regressao_logistica.pdf#chunk-3"],
    )
    title: str = Field(
        description="Título ou nome da fonte.",
        examples=["Aula de Inteligência Artificial"],
    )
    summary: str = Field(
        description="Resumo do dado usado como contexto.",
        examples=["Trecho sobre embeddings e recuperação híbrida."],
    )


class StudyPlanPriority(BaseModel):
    title: str = Field(description="Item que deve ser priorizado.", examples=["Revisar RAG híbrido"])
    level: StudyPlanPriorityLevel = Field(description="Nível da prioridade.", examples=["high"])
    justification: str = Field(
        description="Motivo da prioridade.",
        examples=["Tema aparece nos materiais recuperados e está próximo da prova."],
    )
    related_sources: list[str] = Field(
        default_factory=list,
        description="Referências das fontes que sustentam a prioridade.",
        examples=[["agenda:1", "material:ia.pdf#chunk-2"]],
    )


class StudyPlanItem(BaseModel):
    order: int = Field(description="Ordem do bloco no plano.", examples=[1])
    duration_minutes: int = Field(description="Duração sugerida do bloco.", examples=[40])
    focus: str = Field(description="Foco principal do bloco.", examples=["Embeddings"])
    activity: str = Field(
        description="Atividade objetiva para o estudante executar.",
        examples=["Revisar o conceito e anotar diferenças entre BM25 e busca vetorial."],
    )
    related_sources: list[str] = Field(
        default_factory=list,
        description="Fontes usadas para montar o bloco.",
        examples=[["task:2", "material:ia.pdf#chunk-4"]],
    )
    justification: str = Field(
        description="Por que este bloco aparece no plano.",
        examples=["Resolve uma tarefa pendente e usa o material mais relevante do RAG."],
    )


class StudyPlanResponse(BaseModel):
    objective: str = Field(description="Objetivo original do plano.")
    priorities: list[StudyPlanPriority] = Field(description="Prioridades do plano.")
    agenda_considered: list[StudyPlanSource] = Field(description="Eventos de agenda considerados.")
    tasks_considered: list[StudyPlanSource] = Field(description="Tarefas pendentes consideradas.")
    materials_considered: list[StudyPlanSource] = Field(description="Materiais recuperados pelo RAG.")
    study_blocks: list[StudyPlanItem] = Field(description="Plano dividido em blocos de estudo.")
    next_action: str = Field(description="Próxima ação recomendada para o estudante.")
    warnings: list[str] = Field(
        default_factory=list,
        description="Avisos sobre fontes ausentes ou limitações do contexto.",
    )
    llm_summary: str = Field(
        description="Resumo textual curto gerado pela LLM sobre o plano.",
        examples=["Priorize RAG híbrido, embeddings e tarefas com prazo próximo."],
    )

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "objective": "Montar um plano de estudos para a prova de IA",
                "priorities": [
                    {
                        "title": "Revisar RAG híbrido",
                        "level": "high",
                        "justification": "Tema recorrente nos materiais recuperados.",
                        "related_sources": ["material:ia.pdf#chunk-1"],
                    }
                ],
                "agenda_considered": [
                    {
                        "source_type": "agenda",
                        "reference": "agenda:1",
                        "title": "Prova de IA",
                        "summary": "exam em 2026-06-20 08:00:00.",
                    }
                ],
                "tasks_considered": [],
                "materials_considered": [
                    {
                        "source_type": "material",
                        "reference": "material:ia.pdf#chunk-1",
                        "title": "ia.pdf",
                        "summary": "Trecho recuperado sobre RAG e embeddings.",
                    }
                ],
                "study_blocks": [
                    {
                        "order": 1,
                        "duration_minutes": 40,
                        "focus": "RAG",
                        "activity": "Revisar recuperação híbrida e fazer resumo.",
                        "related_sources": ["material:ia.pdf#chunk-1"],
                        "justification": "É o tema mais relevante para o objetivo.",
                    }
                ],
                "next_action": "Comece pelo bloco 1 e anote dúvidas.",
                "warnings": ["Nenhuma tarefa pendente encontrada."],
                "llm_summary": "Plano focado nos materiais recuperados e na data da prova.",
            }
        }
    )
