from types import SimpleNamespace

import pytest

from app.rag.local_dataset import LocalDatasetChunk, LocalDatasetIndex
from app.rag.retriever import RetrievedDocument, RetrieverDocument
from app.schemas.material_schema import MaterialAskRequest
from app.services.material_service import MaterialService


pytestmark = pytest.mark.asyncio


async def _run_sync(func, /, *args, **kwargs):
    return func(*args, **kwargs)


async def test_buscar_material_rag_usa_dataset_local_quando_ativo(mocker):
    mocker.patch("app.services.material_service.asyncio.to_thread", side_effect=_run_sync)
    repository = SimpleNamespace(list_chunks_for_indexed_materials=mocker.AsyncMock())
    service = MaterialService(repository)
    service.settings = SimpleNamespace(
        use_local_dataset=True,
        local_dataset_path="data",
    )

    local_chunk = LocalDatasetChunk(
        material_id=123,
        material_name="docs/demo.md",
        chunk_id=456,
        chunk_index=0,
        text="Regressão logística é usada para classificação.",
        file_path="data/docs/demo.md",
    )
    mocker.patch(
        "app.services.material_service.rebuild_local_dataset_index",
        return_value=LocalDatasetIndex(
            base_path="data",
            file_count=1,
            chunk_count=1,
            chunks=[local_chunk],
        ),
    )
    mocker.patch(
        "app.services.material_service.retrieve",
        return_value=[
            RetrievedDocument(
                document=RetrieverDocument(
                    material_id=123,
                    material_name="docs/demo.md",
                    chunk_id=456,
                    chunk_index=0,
                    text=local_chunk.text,
                ),
                score=0.9,
            )
        ],
    )
    mock_rag_service = mocker.patch("app.services.material_service.RagService")
    mock_rag_service.return_value.answer.return_value = "Resposta local."

    response = await service.buscar_material_rag(
        MaterialAskRequest(
            question="Explique regressão logística",
            material_id=999,
            method="bm25",
            min_score=0.15,
        )
    )

    assert response.answer == "Resposta local."
    assert response.sources[0].material_id == 123
    assert response.sources[0].material_name == "docs/demo.md"
    repository.list_chunks_for_indexed_materials.assert_not_awaited()


async def test_buscar_material_rag_mantem_fluxo_banco_quando_dataset_desativado(mocker):
    mocker.patch("app.services.material_service.asyncio.to_thread", side_effect=_run_sync)
    material = SimpleNamespace(original_filename="banco.txt")
    db_chunk = SimpleNamespace(
        material_id=1,
        material=material,
        id=10,
        chunk_index=0,
        chunk_text="Conteúdo vindo do banco.",
    )
    repository = SimpleNamespace(
        list_chunks_for_indexed_materials=mocker.AsyncMock(return_value=[db_chunk])
    )
    service = MaterialService(repository)
    service.settings = SimpleNamespace(
        use_local_dataset=False,
        local_dataset_path="data",
    )

    mock_local_loader = mocker.patch(
        "app.services.material_service.rebuild_local_dataset_index"
    )
    mocker.patch(
        "app.services.material_service.retrieve",
        return_value=[
            RetrievedDocument(
                document=RetrieverDocument(
                    material_id=1,
                    material_name="banco.txt",
                    chunk_id=10,
                    chunk_index=0,
                    text="Conteúdo vindo do banco.",
                ),
                score=0.9,
            )
        ],
    )
    mock_rag_service = mocker.patch("app.services.material_service.RagService")
    mock_rag_service.return_value.answer.return_value = "Resposta do banco."

    response = await service.buscar_material_rag(
        MaterialAskRequest(question="Pergunta", method="bm25", min_score=0.15)
    )

    assert response.answer == "Resposta do banco."
    assert response.sources[0].material_name == "banco.txt"
    repository.list_chunks_for_indexed_materials.assert_awaited_once()
    mock_local_loader.assert_not_called()
