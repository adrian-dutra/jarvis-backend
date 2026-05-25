from fastapi import APIRouter, Depends, File, Form, Path, UploadFile, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.connection import get_async_db
from app.repositories.material_repository import MaterialRepository
from app.schemas.material_schema import (
    MaterialAskRequest,
    MaterialAskResponse,
    MaterialDetail,
    MaterialIndexResponse,
    MaterialSummary,
)
from app.services.material_service import MaterialService


router = APIRouter(prefix="/materials", tags=["Materiais (RAG)"])


def get_material_service(db: AsyncSession = Depends(get_async_db)) -> MaterialService:
    repository = MaterialRepository(db)
    return MaterialService(repository)


@router.post(
    "/upload",
    response_model=MaterialSummary,
    status_code=status.HTTP_201_CREATED,
    summary="Enviar material de estudo",
    description=(
        "Recebe um arquivo PDF ou TXT e um assunto opcional. "
        "O arquivo original é salvo fisicamente em uploads/ com nome UUID, enquanto metadados são persistidos no PostgreSQL."
    ),
    response_description="Metadados do material criado.",
)
async def upload_material(
    file: UploadFile = File(..., description="Arquivo PDF ou TXT a ser preservado e indexado posteriormente."),
    subject: str | None = Form(default=None, description="Disciplina ou assunto associado ao material."),
    service: MaterialService = Depends(get_material_service),
):
    return await service.upload_material(file=file, subject=subject)


@router.get(
    "",
    response_model=list[MaterialSummary],
    status_code=status.HTTP_200_OK,
    summary="Listar materiais",
    description=(
        "Lista materiais cadastrados sem retornar o texto extraído completo. "
        "Use o endpoint de detalhe para visualizar informações completas do material."
    ),
    response_description="Lista de materiais cadastrados.",
)
async def list_materials(service: MaterialService = Depends(get_material_service)):
    return await service.list_materials()


@router.post(
    "/ask",
    response_model=MaterialAskResponse,
    status_code=status.HTTP_200_OK,
    summary="Perguntar aos materiais com RAG",
    description=(
        "Executa recuperação sobre material_chunks usando BM25, dense ou hybrid. "
        "Quando material_id é omitido, consulta apenas materiais com indexed=true. "
        "Se não houver contexto útil acima do min_score, retorna exatamente 'não encontrado no contexto'."
    ),
    response_description="Resposta baseada nos chunks recuperados e fontes utilizadas.",
)
async def ask_materials(
    request: MaterialAskRequest,
    service: MaterialService = Depends(get_material_service),
):
    return await service.ask(request)


@router.get(
    "/{material_id}",
    response_model=MaterialDetail,
    status_code=status.HTTP_200_OK,
    summary="Detalhar material",
    description=(
        "Retorna detalhes do material, incluindo extracted_text para debug e apresentação. "
        "O arquivo físico não é retornado por este endpoint."
    ),
    response_description="Detalhes do material cadastrado.",
)
async def get_material(
    material_id: int = Path(..., description="Identificador do material."),
    service: MaterialService = Depends(get_material_service),
):
    return await service.get_material(material_id)


@router.post(
    "/{material_id}/index",
    response_model=MaterialIndexResponse,
    status_code=status.HTTP_200_OK,
    summary="Indexar material",
    description=(
        "Lê o arquivo salvo em file_path, extrai texto, divide em chunks e persiste os chunks no banco. "
        "Operações pesadas são executadas fora do event loop com asyncio.to_thread."
    ),
    response_description="Material indexado e quantidade de chunks gerados.",
)
async def index_material(
    material_id: int = Path(..., description="Identificador do material a indexar."),
    service: MaterialService = Depends(get_material_service),
):
    return await service.index_material(material_id)
