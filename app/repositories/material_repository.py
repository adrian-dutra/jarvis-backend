from datetime import datetime

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload

from app.models.material import Material
from app.models.material_chunk import MaterialChunk


class MaterialRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def create_material(
        self,
        *,
        original_filename: str,
        stored_filename: str,
        subject: str | None,
        file_type: str | None,
        content_type: str | None,
        file_size: int | None,
        file_path: str,
        created_at: datetime,
        updated_at: datetime,
    ) -> Material:
        material = Material(
            original_filename=original_filename,
            stored_filename=stored_filename,
            subject=subject,
            file_type=file_type,
            content_type=content_type,
            file_size=file_size,
            file_path=file_path,
            created_at=created_at,
            updated_at=updated_at,
        )
        self.db.add(material)
        await self.db.commit()
        await self.db.refresh(material)
        return material

    async def list_materials(self) -> list[Material]:
        statement = select(Material).order_by(Material.created_at.desc())
        result = await self.db.execute(statement)
        return list(result.scalars().all())

    async def get_material(self, material_id: int) -> Material | None:
        return await self.db.get(Material, material_id)

    async def update_index_data(
        self,
        material: Material,
        *,
        extracted_text: str,
        chunks: list[str],
        updated_at: datetime,
    ) -> Material:
        await self.delete_chunks(material.id)

        material.extracted_text = extracted_text
        material.indexed = True
        material.chunk_count = len(chunks)
        material.updated_at = updated_at

        for index, text in enumerate(chunks):
            self.db.add(
                MaterialChunk(
                    material_id=material.id,
                    chunk_index=index,
                    chunk_text=text,
                    token_count=len(text.split()),
                    created_at=updated_at,
                )
            )

        await self.db.commit()
        await self.db.refresh(material)
        return material

    async def delete_chunks(self, material_id: int) -> None:
        await self.db.execute(
            delete(MaterialChunk).where(MaterialChunk.material_id == material_id)
        )
        await self.db.flush()

    async def list_chunks_for_material(self, material_id: int) -> list[MaterialChunk]:
        statement = (
            select(MaterialChunk)
            .options(joinedload(MaterialChunk.material))
            .join(Material)
            .where(MaterialChunk.material_id == material_id, Material.indexed.is_(True))
            .order_by(MaterialChunk.chunk_index.asc())
        )
        result = await self.db.execute(statement)
        return list(result.scalars().all())

    async def list_chunks_for_indexed_materials(self) -> list[MaterialChunk]:
        statement = (
            select(MaterialChunk)
            .options(joinedload(MaterialChunk.material))
            .join(Material)
            .where(Material.indexed.is_(True))
            .order_by(MaterialChunk.material_id.asc(), MaterialChunk.chunk_index.asc())
        )
        result = await self.db.execute(statement)
        return list(result.scalars().all())
