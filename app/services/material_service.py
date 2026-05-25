import asyncio
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

import aiofiles
from fastapi import HTTPException, UploadFile, status
from loguru import logger

from app.core.config import get_settings
from app.rag.chunker import split_text
from app.rag.loader import extract_text
from app.rag.local_dataset import LocalDatasetChunk, rebuild_local_dataset_index
from app.rag.rag_service import NOT_FOUND_ANSWER, RagService
from app.rag.retriever import RetrieverDocument, retrieve
from app.repositories.material_repository import MaterialRepository
from app.schemas.material_schema import (
    MaterialAskRequest,
    MaterialAskResponse,
    MaterialIndexResponse,
    MaterialSource,
)


SUPPORTED_EXTENSIONS = {".pdf", ".txt"}


class MaterialService:
    def __init__(self, repository: MaterialRepository):
        self.repository = repository
        self.settings = get_settings()

    async def upload_material(self, *, file: UploadFile, subject: str | None):
        original_filename = Path(file.filename or "").name
        suffix = Path(original_filename).suffix.lower()

        if not original_filename or suffix not in SUPPORTED_EXTENSIONS:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Envie um arquivo PDF ou TXT.",
            )

        upload_dir = Path(self.settings.upload_dir)
        await asyncio.to_thread(upload_dir.mkdir, parents=True, exist_ok=True)

        stored_filename = f"{uuid4()}{suffix}"
        file_path = upload_dir / stored_filename

        content = await file.read()
        async with aiofiles.open(file_path, "wb") as output:
            await output.write(content)

        now = self._utc_now()
        material = await self.repository.create_material(
            original_filename=original_filename,
            stored_filename=stored_filename,
            subject=subject,
            file_type=suffix.replace(".", ""),
            content_type=file.content_type,
            file_size=len(content),
            file_path=str(file_path),
            created_at=now,
            updated_at=now,
        )

        logger.info(
            "upload de material realizado material_id={} filename={} size={}",
            material.id,
            original_filename,
            len(content),
        )
        return material

    async def list_materials(self):
        return await self.repository.list_materials()

    async def get_material(self, material_id: int):
        material = await self.repository.get_material(material_id)
        if material is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Material não encontrado.",
            )
        return material

    async def index_material(self, material_id: int) -> MaterialIndexResponse:
        material = await self.get_material(material_id)

        logger.info("iniciando indexação material_id={}", material.id)

        try:
            text, chunks = await asyncio.to_thread(
                self._extract_and_chunk,
                material.file_path,
            )
        except ValueError as exc:
            logger.error("erro de indexação material_id={} erro={}", material.id, exc)
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=str(exc),
            ) from exc
        except Exception as exc:
            logger.exception("erro inesperado na indexação material_id={}", material.id)
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Erro ao indexar material.",
            ) from exc

        if not text.strip() or not chunks:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Não foi possível extrair texto útil do material.",
            )

        material = await self.repository.update_index_data(
            material,
            extracted_text=text,
            chunks=chunks,
            updated_at=self._utc_now(),
        )

        logger.info(
            "indexação concluída material_id={} chunks={}",
            material.id,
            material.chunk_count,
        )
        return MaterialIndexResponse(material=material, chunk_count=material.chunk_count)

    async def ask(self, request: MaterialAskRequest) -> MaterialAskResponse:
        return await self.buscar_material_rag(request)

    async def buscar_material_rag(
        self,
        request: MaterialAskRequest,
    ) -> MaterialAskResponse:
        documents = await self._load_documents_for_question(request.material_id)

        logger.info(
            "pergunta RAG recebida origem={} method={} material_id={} k={} alpha={}",
            "local_dataset" if self.settings.use_local_dataset else "database",
            request.method,
            request.material_id,
            request.k,
            request.alpha,
        )

        try:
            retrieved = await asyncio.to_thread(
                retrieve,
                question=request.question,
                documents=documents,
                method=request.method,
                k=request.k,
                alpha=request.alpha,
            )
        except Exception as exc:
            logger.exception("erro no retrieval RAG")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Erro ao recuperar chunks.",
            ) from exc

        useful_retrieved = [
            item
            for item in retrieved
            if item.document.text.strip() and item.score >= request.min_score
        ]

        logger.info(
            "chunks recuperados method={} total={} úteis={}",
            request.method,
            len(retrieved),
            len(useful_retrieved),
        )

        if not useful_retrieved:
            return MaterialAskResponse(
                question=request.question,
                answer=NOT_FOUND_ANSWER,
                method=request.method,
                sources=[],
            )

        try:
            answer = await asyncio.to_thread(
                RagService().answer,
                question=request.question,
                retrieved_documents=useful_retrieved,
                min_score=request.min_score,
            )
        except Exception as exc:
            logger.exception("erro ao chamar Gemma")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Erro ao gerar resposta com Gemma.",
            ) from exc

        sources = [
            MaterialSource(
                material_id=item.document.material_id,
                material_name=item.document.material_name,
                chunk_id=item.document.chunk_id,
                chunk_index=item.document.chunk_index,
                text=item.document.text,
                score=item.score,
            )
            for item in useful_retrieved
        ]

        return MaterialAskResponse(
            question=request.question,
            answer=answer,
            method=request.method,
            sources=sources if answer != NOT_FOUND_ANSWER else [],
        )

    async def _load_documents_for_question(
        self,
        material_id: int | None,
    ) -> list[RetrieverDocument]:
        if self.settings.use_local_dataset:
            if material_id is not None:
                logger.info(
                    "material_id ignorado porque USE_LOCAL_DATASET=true material_id={}",
                    material_id,
                )

            local_index = await asyncio.to_thread(
                rebuild_local_dataset_index,
                self.settings.local_dataset_path,
                force=False,
            )
            if not local_index.chunks:
                logger.warning(
                    "dataset local ativo sem chunks úteis path={}",
                    self.settings.local_dataset_path,
                )
            return self._local_chunks_to_documents(local_index.chunks)

        chunks = await self._load_chunks_for_question(material_id)
        return [
            RetrieverDocument(
                material_id=chunk.material_id,
                material_name=chunk.material.original_filename,
                chunk_id=chunk.id,
                chunk_index=chunk.chunk_index,
                text=chunk.chunk_text,
            )
            for chunk in chunks
        ]

    async def _load_chunks_for_question(self, material_id: int | None):
        if material_id is not None:
            material = await self.get_material(material_id)
            if not material.indexed:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Material ainda não foi indexado.",
                )
            return await self.repository.list_chunks_for_material(material_id)

        return await self.repository.list_chunks_for_indexed_materials()

    def _local_chunks_to_documents(
        self,
        chunks: list[LocalDatasetChunk],
    ) -> list[RetrieverDocument]:
        return [
            RetrieverDocument(
                material_id=chunk.material_id,
                material_name=chunk.material_name,
                chunk_id=chunk.chunk_id,
                chunk_index=chunk.chunk_index,
                text=chunk.text,
            )
            for chunk in chunks
        ]

    def _extract_and_chunk(self, file_path: str) -> tuple[str, list[str]]:
        text = extract_text(file_path)
        chunks = split_text(text, chunk_size=800, overlap=150)
        return text, chunks

    def _utc_now(self) -> datetime:
        return datetime.now(timezone.utc).replace(tzinfo=None)
