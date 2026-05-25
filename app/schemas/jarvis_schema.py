from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class JarvisAskRequest(BaseModel):
    message: str = Field(
        ...,
        min_length=1,
        description="Mensagem do usuário para o assistente JARVIS.",
        examples=["Quais tarefas pendentes eu tenho?"],
    )

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "message": "Quais tarefas pendentes eu tenho?",
            }
        }
    )


class JarvisToolTrace(BaseModel):
    name: str = Field(description="Nome da tool escolhida pela IA.", examples=["listar_tarefas"])
    arguments: dict[str, Any] = Field(description="Argumentos JSON fornecidos pela IA.")
    result: Any = Field(description="Resultado serializado retornado pelo service.")

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "name": "listar_tarefas",
                "arguments": {"status": "pending"},
                "result": [
                    {
                        "id": 1,
                        "title": "Estudar embeddings",
                        "status": "pending",
                    }
                ],
            }
        }
    )


class JarvisAskResponse(BaseModel):
    message: str = Field(description="Mensagem original enviada pelo usuário.")
    answer: str = Field(description="Resposta final formulada pela IA.")
    tools_used: list[JarvisToolTrace] = Field(
        default_factory=list,
        description="Resumo das tools executadas durante a resposta.",
    )

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "message": "Quais tarefas pendentes eu tenho?",
                "answer": "Você tem uma tarefa pendente: Estudar embeddings.",
                "tools_used": [
                    {
                        "name": "listar_tarefas",
                        "arguments": {"status": "pending"},
                        "result": [
                            {
                                "id": 1,
                                "title": "Estudar embeddings",
                                "status": "pending",
                            }
                        ],
                    }
                ],
            }
        }
    )
