from fastapi import FastAPI

from app.api.routes import agenda
from app.api.routes import jarvis
from app.api.routes import materials
from app.api.routes import tasks

description = """
JARVIS Acadêmico API é um backend FastAPI para apoio à organização acadêmica e
consulta inteligente a materiais de estudo.

A aplicação demonstra boas práticas de engenharia de software em um projeto de
Inteligência Artificial: arquitetura em camadas, acesso assíncrono ao PostgreSQL,
schemas Pydantic V2, logs estruturados e implementação explícita de RAG sem
delegar a lógica principal para agentes prontos.

Funcionalidades principais:

- Materiais de estudo com RAG, BM25, embeddings, FAISS e recuperação híbrida.
- Agenda acadêmica com eventos, provas, aulas e recorrência semanal simples.
- Tarefas acadêmicas com criação, listagem, conclusão e remoção.

O projeto está preparado para futura integração com Tool Calling da LLM.
"""

tags_metadata = [
    {
        "name": "Materiais (RAG)",
        "description": "Upload, indexação e consulta a materiais acadêmicos usando RAG.",
    },
    {
        "name": "Agenda",
        "description": "Cadastro e consulta de aulas, provas, reuniões e eventos acadêmicos.",
    },
    {
        "name": "Tarefas",
        "description": "Gerenciamento de tarefas acadêmicas, estudos, leituras e entregas.",
    },
    {
        "name": "Sistema",
        "description": "Endpoints básicos de saúde e disponibilidade da API.",
    },
    {
        "name": "JARVIS",
        "description": "Orquestrador de IA com Tool Calling sobre agenda, tarefas e RAG.",
    },
]

app = FastAPI(
    title="JARVIS Acadêmico API",
    description=description,
    version="0.1.0",
    contact={"name": "Equipe JARVIS Acadêmico"},
    openapi_tags=tags_metadata,
)

app.include_router(materials.router)
app.include_router(agenda.router)
app.include_router(tasks.router)
app.include_router(jarvis.router)


@app.get(
    "/",
    tags=["Sistema"],
    summary="Verificar status básico",
    description="Retorna uma mensagem simples indicando que a API está online.",
    response_description="Status básico da aplicação.",
    status_code=200,
)
def health_check():
    return {"status": "ok", "message": "JARVIS Acadêmico API online"}


@app.get(
    "/health",
    tags=["Sistema"],
    summary="Health check",
    description="Endpoint leve para verificar disponibilidade da API em ambientes locais ou Docker.",
    response_description="Status de saúde da API.",
    status_code=200,
)
def health():
    return {"status": "ok"}
