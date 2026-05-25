import hashlib
import time
from dataclasses import dataclass
from pathlib import Path

from loguru import logger

from app.rag.chunker import split_text
from app.rag.loader import extract_text


SUPPORTED_LOCAL_DATASET_EXTENSIONS = {".pdf", ".txt", ".md"}


@dataclass(frozen=True)
class LocalDatasetChunk:
    material_id: int
    material_name: str
    chunk_id: int
    chunk_index: int
    text: str
    file_path: str


@dataclass(frozen=True)
class LocalDatasetIndex:
    base_path: str
    file_count: int
    chunk_count: int
    chunks: list[LocalDatasetChunk]


_CACHE: dict[str, LocalDatasetIndex] = {}


def rebuild_local_dataset_index(
    base_path: str,
    *,
    force: bool = False,
    chunk_size: int = 800,
    overlap: int = 150,
) -> LocalDatasetIndex:
    normalized_base_path = str(Path(base_path).resolve())

    if not force and normalized_base_path in _CACHE:
        cached_index = _CACHE[normalized_base_path]
        logger.info(
            "dataset local cache hit path={} files={} chunks={}",
            normalized_base_path,
            cached_index.file_count,
            cached_index.chunk_count,
        )
        return cached_index

    start = time.perf_counter()
    base = Path(normalized_base_path)
    if not base.exists():
        logger.warning("dataset local não encontrado path={}", normalized_base_path)
        index = LocalDatasetIndex(
            base_path=normalized_base_path,
            file_count=0,
            chunk_count=0,
            chunks=[],
        )
        _CACHE[normalized_base_path] = index
        return index

    loaded_files = 0
    chunks: list[LocalDatasetChunk] = []

    logger.info("reconstruindo dataset local path={}", normalized_base_path)
    for file_path in sorted(path for path in base.rglob("*") if path.is_file()):
        suffix = file_path.suffix.lower()
        relative_path = file_path.relative_to(base).as_posix()

        if suffix not in SUPPORTED_LOCAL_DATASET_EXTENSIONS:
            logger.info("arquivo ignorado no dataset local path={}", relative_path)
            continue

        try:
            text = extract_text(str(file_path))
        except Exception as exc:
            logger.warning(
                "erro ao carregar arquivo do dataset local path={} erro={}",
                relative_path,
                exc,
            )
            continue

        document_chunks = split_text(text, chunk_size=chunk_size, overlap=overlap)
        if not document_chunks:
            logger.warning("arquivo vazio ignorado no dataset local path={}", relative_path)
            continue

        material_id = _stable_positive_id(relative_path)
        loaded_files += 1
        logger.info(
            "arquivo carregado no dataset local path={} chunks={}",
            relative_path,
            len(document_chunks),
        )

        for chunk_index, chunk_text in enumerate(document_chunks):
            chunks.append(
                LocalDatasetChunk(
                    material_id=material_id,
                    material_name=relative_path,
                    chunk_id=_stable_positive_id(f"{relative_path}:{chunk_index}"),
                    chunk_index=chunk_index,
                    text=chunk_text,
                    file_path=str(file_path),
                )
            )

    elapsed = time.perf_counter() - start
    index = LocalDatasetIndex(
        base_path=normalized_base_path,
        file_count=loaded_files,
        chunk_count=len(chunks),
        chunks=chunks,
    )
    _CACHE[normalized_base_path] = index

    logger.info(
        "dataset local reconstruído path={} files={} chunks={} elapsed={:.3f}s",
        normalized_base_path,
        loaded_files,
        len(chunks),
        elapsed,
    )
    return index


def clear_local_dataset_cache() -> None:
    _CACHE.clear()


def _stable_positive_id(value: str) -> int:
    digest = hashlib.sha1(value.encode("utf-8")).hexdigest()
    return int(digest[:12], 16)
