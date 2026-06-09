"""
app/services/storage_service.py
────────────────────────────────
Serviço de upload de arquivos para Cloudinary.

Substitui o AWS S3 anterior mantendo a mesma interface pública:
  - upload_file(file, folder) → URL pública segura (https)
  - upload_json(content, key) → URL pública do JSON armazenado como raw

Pastas suportadas:
  - limpezas/antes/
  - limpezas/depois/
  - eventos/
  - nfts/metadata/

Credenciais no .env:
  CLOUDINARY_CLOUD_NAME=...
  CLOUDINARY_API_KEY=...
  CLOUDINARY_API_SECRET=...
"""
import uuid
import logging
from io import BytesIO
from typing import Literal

import cloudinary
import cloudinary.uploader
from fastapi import UploadFile, HTTPException, status

from app.core.config import settings

logger = logging.getLogger(__name__)

# Tipos de pasta permitidos (idêntico ao contrato anterior com o S3)
FolderType = Literal[
    "limpezas/antes",
    "limpezas/depois",
    "eventos",
    "pontos-verdes/iniciais",
    "pontos-verdes/checkins",
    "nfts/metadata",
    "denuncias/problemas",
    "denuncias/resolucoes",
    "educacoes",
]

# Extensões de imagem aceitas para uploads de foto
_ALLOWED_IMAGE_TYPES = {
    "image/jpeg",
    "image/jpg",
    "image/png",
    "image/webp",
    "image/heic",
    "image/heif",
}


def _configure_cloudinary() -> None:
    """Configura o SDK do Cloudinary com as credenciais do .env."""
    cloudinary.config(
        cloud_name=settings.CLOUDINARY_CLOUD_NAME,
        api_key=settings.CLOUDINARY_API_KEY,
        api_secret=settings.CLOUDINARY_API_SECRET,
        secure=True,  # sempre usa HTTPS nas URLs geradas
    )


# Configura na importação do módulo
_configure_cloudinary()


def _public_id(folder: str) -> str:
    """Gera um public_id único dentro da pasta especificada."""
    return f"{folder}/{uuid.uuid4()}"


async def upload_file(
    file: UploadFile,
    folder: FolderType,
    *,
    validate_image: bool = True,
) -> str:
    """
    Faz upload de um UploadFile para o Cloudinary.

    Args:
        file: Arquivo recebido via FastAPI multipart.
        folder: Pasta de destino dentro do Cloudinary.
        validate_image: Se True, rejeita tipos que não sejam imagens.

    Returns:
        URL pública segura (https) do arquivo no Cloudinary.

    Raises:
        400: Tipo de arquivo não permitido ou arquivo vazio.
        502: Falha na comunicação com o Cloudinary.
    """
    content_type = file.content_type or "application/octet-stream"

    if validate_image and content_type not in _ALLOWED_IMAGE_TYPES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                f"Tipo de arquivo não permitido: {content_type}. "
                "Envie uma imagem JPEG, PNG ou WebP."
            ),
        )

    content = await file.read()
    if not content:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Arquivo vazio. Envie uma imagem válida.",
        )

    public_id = _public_id(folder)

    try:
        result = cloudinary.uploader.upload(
            BytesIO(content),
            public_id=public_id,
            resource_type="image",
            # Cloudinary otimiza a imagem automaticamente
            quality="auto",
            fetch_format="auto",
        )
        url: str = result["secure_url"]
        logger.info("Upload concluído: %s", url)
    except Exception as exc:
        logger.exception("Falha no upload Cloudinary: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Falha ao enviar arquivo para o armazenamento. Tente novamente.",
        )

    # Volta o cursor para o início para uso posterior (se necessário)
    await file.seek(0)
    return url


async def upload_json(content: bytes, key: str) -> str:
    """
    Faz upload de bytes JSON diretamente para o Cloudinary como raw file.

    Args:
        content: Conteúdo JSON serializado como bytes.
        key: Caminho lógico do objeto (ex: 'nfts/metadata/<id>.json').
              Usado como public_id no Cloudinary (sem extensão obrigatória).

    Returns:
        URL pública do arquivo JSON no Cloudinary.
    """
    # Remove extensão do key para usar como public_id
    public_id = key.rsplit(".", 1)[0] if "." in key else key

    try:
        result = cloudinary.uploader.upload(
            BytesIO(content),
            public_id=public_id,
            resource_type="raw",  # raw = arquivos não-imagem (JSON, PDF, etc.)
        )
        url: str = result["secure_url"]
        logger.info("Metadata JSON enviado: %s", url)
    except Exception as exc:
        logger.exception("Falha no upload JSON Cloudinary: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Falha ao salvar metadata do NFT. Tente novamente.",
        )

    return url
