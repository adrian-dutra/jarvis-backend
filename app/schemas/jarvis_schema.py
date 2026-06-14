from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field


class JarvisConversationMessage(BaseModel):
    role: Literal["user", "assistant"] = Field(
        description="Papel da mensagem no histórico da conversa.",
        examples=["user"],
    )
    content: str = Field(
        ...,
        min_length=1,
        description="Conteúdo textual da mensagem.",
        examples=["Você pode criar uma pergunta sobre RAG?"],
    )


class JarvisAskRequest(BaseModel):
    message: str = Field(
        ...,
        min_length=1,
        description="Mensagem do usuário para o assistente JARVIS.",
        examples=["Quais tarefas pendentes eu tenho?"],
    )
    conversation_id: str = Field(
        default="default",
        min_length=1,
        max_length=100,
        description=(
            "Identificador simples da conversa. Mensagens com o mesmo ID reutilizam "
            "o histórico em memória durante a execução da API."
        ),
        examples=["apresentacao-ia"],
    )
    history: list[JarvisConversationMessage] = Field(
        default_factory=list,
        description=(
            "Histórico opcional enviado pelo cliente. Quando informado, ele é somado "
            "ao histórico em memória antes da mensagem atual."
        ),
    )

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "conversation_id": "apresentacao-ia",
                "message": "Quais tarefas pendentes eu tenho?",
                "history": [
                    {
                        "role": "user",
                        "content": "Crie uma pergunta sobre RAG.",
                    },
                    {
                        "role": "assistant",
                        "content": "Qual é a função da recuperação em um pipeline RAG?",
                    },
                ],
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
    conversation_id: str | None = Field(
        default=None,
        description="Identificador da conversa usada para recuperar o histórico em memória.",
    )
    answer: str = Field(description="Resposta final formulada pela IA.")
    tools_used: list[JarvisToolTrace] = Field(
        default_factory=list,
        description="Resumo das tools executadas durante a resposta.",
    )

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "conversation_id": "apresentacao-ia",
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
