from pathlib import Path

from app.rag.local_dataset import (
    clear_local_dataset_cache,
    rebuild_local_dataset_index,
)


def test_local_dataset_le_txt_e_md(tmp_path: Path):
    clear_local_dataset_cache()
    docs_dir = tmp_path / "docs"
    docs_dir.mkdir()
    (docs_dir / "aula.txt").write_text("Texto sobre BM25 e busca lexical.", encoding="utf-8")
    (docs_dir / "resumo.md").write_text("# RAG\nEmbeddings e FAISS.", encoding="utf-8")

    index = rebuild_local_dataset_index(str(tmp_path), force=True, chunk_size=80, overlap=10)

    assert index.file_count == 2
    assert index.chunk_count == 2
    assert {chunk.material_name for chunk in index.chunks} == {
        "docs/aula.txt",
        "docs/resumo.md",
    }


def test_local_dataset_ignora_extensao_nao_suportada(tmp_path: Path):
    clear_local_dataset_cache()
    (tmp_path / "imagem.png").write_text("não deve entrar", encoding="utf-8")
    (tmp_path / "material.md").write_text("conteúdo útil", encoding="utf-8")

    index = rebuild_local_dataset_index(str(tmp_path), force=True)

    assert index.file_count == 1
    assert index.chunk_count == 1
    assert index.chunks[0].material_name == "material.md"


def test_local_dataset_gera_ids_deterministicos(tmp_path: Path):
    clear_local_dataset_cache()
    (tmp_path / "material.md").write_text("conteúdo útil para teste", encoding="utf-8")

    first = rebuild_local_dataset_index(str(tmp_path), force=True)
    second = rebuild_local_dataset_index(str(tmp_path), force=True)

    assert first.chunks[0].material_id == second.chunks[0].material_id
    assert first.chunks[0].chunk_id == second.chunks[0].chunk_id


def test_local_dataset_cache_evita_reprocessamento_sem_force(tmp_path: Path):
    clear_local_dataset_cache()
    file_path = tmp_path / "material.md"
    file_path.write_text("primeiro conteúdo", encoding="utf-8")

    first = rebuild_local_dataset_index(str(tmp_path), force=True)
    file_path.write_text("segundo conteúdo maior e diferente", encoding="utf-8")
    second = rebuild_local_dataset_index(str(tmp_path), force=False)

    assert second is first
    assert second.chunks[0].text == first.chunks[0].text
