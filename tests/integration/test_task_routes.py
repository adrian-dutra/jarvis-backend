import pytest


pytestmark = pytest.mark.asyncio


async def test_create_task_retorna_201_e_contrato_json(async_client):
    response = await async_client.post(
        "/tasks",
        json={
            "title": "Estudar embeddings",
            "description": "Revisar FAISS e BM25",
            "subject": "Inteligência Artificial",
            "priority": "high",
            "due_date": "2026-05-30T20:00:00",
        },
    )

    assert response.status_code == 201
    data = response.json()
    assert data["id"] == 1
    assert data["title"] == "Estudar embeddings"
    assert data["status"] == "pending"
    assert set(data.keys()) == {"id", "title", "status"}


async def test_list_tasks_retorna_200_e_lista_ordenada(async_client):
    await async_client.post(
        "/tasks",
        json={
            "title": "Sem prazo",
            "priority": "medium",
        },
    )
    await async_client.post(
        "/tasks",
        json={
            "title": "Prazo próximo",
            "priority": "high",
            "due_date": "2026-05-25T20:00:00",
        },
    )

    response = await async_client.get("/tasks")

    assert response.status_code == 200
    data = response.json()
    assert [item["title"] for item in data] == ["Prazo próximo", "Sem prazo"]
    assert all(item["status"] == "pending" for item in data)


async def test_list_tasks_filtra_por_status_priority_e_subject(async_client):
    await async_client.post(
        "/tasks",
        json={
            "title": "Estudar RAG",
            "subject": "IA",
            "priority": "high",
        },
    )
    await async_client.post(
        "/tasks",
        json={
            "title": "Ler capítulo",
            "subject": "Banco de Dados",
            "priority": "low",
        },
    )

    response = await async_client.get(
        "/tasks",
        params={
            "status": "pending",
            "priority": "high",
            "subject": "IA",
        },
    )

    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1
    assert data[0]["title"] == "Estudar RAG"
    assert data[0]["priority"] == "high"
    assert data[0]["subject"] == "IA"


async def test_create_task_com_payload_invalido_retorna_422(async_client):
    response = await async_client.post(
        "/tasks",
        json={
            "title": "",
            "priority": "urgent",
        },
    )

    assert response.status_code == 422


async def test_get_task_inexistente_retorna_404(async_client):
    response = await async_client.get("/tasks/999")

    assert response.status_code == 404
    assert response.json()["detail"] == "Tarefa não encontrada."
