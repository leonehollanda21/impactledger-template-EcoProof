"""
app/controllers/users_router.py
────────────────────────────────
Rotas de perfil do usuário autenticado:
  GET /users/me       → perfil completo (dados variam por role)
  GET /users/me/nfts  → lista de NFTs do cidadão logado
"""
from typing import Union
from fastapi import APIRouter
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import (
    get_db,
    CurrentUser,
    DBSession,
)
from app.models.user import User, UserRole
from app.models.cidadao import Cidadao
from app.models.instituto import Instituto
from app.models.nft import NFT
from app.schemas.user import (
    CidadaoMeOut,
    InstitutoMeOut,
    AdminMeOut,
)
from app.schemas.validacao_nft import NFTOut
from fastapi import HTTPException, status

router = APIRouter(prefix="/users", tags=["Users"])


# ── GET /users/me ─────────────────────────────────────────────────────────────

@router.get(
    "/me",
    response_model=Union[CidadaoMeOut, InstitutoMeOut, AdminMeOut],
    summary="Meu perfil",
    description=(
        "Retorna o perfil completo do usuário autenticado. "
        "A resposta inclui campos extras dependendo do role: "
        "``total_points`` para cidadãos; ``cnpj`` e ``verified`` para institutos."
    ),
)
async def get_me(
    current_user: CurrentUser,
    db: DBSession,
) -> Union[CidadaoMeOut, InstitutoMeOut, AdminMeOut]:
    """Retorna perfil adaptado ao role do usuário logado."""

    if current_user.role == UserRole.cidadao:
        result = await db.execute(select(Cidadao).where(Cidadao.id == current_user.id))
        cidadao = result.scalar_one_or_none()

        return CidadaoMeOut(
            id=current_user.id,
            name=current_user.name,
            email=current_user.email,
            role=current_user.role,
            wallet_address=current_user.wallet_address,
            is_active=current_user.is_active,
            created_at=current_user.created_at,
            total_points=cidadao.total_points if cidadao else 0,
        )

    if current_user.role == UserRole.instituto:
        result = await db.execute(select(Instituto).where(Instituto.id == current_user.id))
        instituto = result.scalar_one_or_none()

        if instituto is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Perfil de instituto não encontrado.",
            )

        return InstitutoMeOut(
            id=current_user.id,
            name=current_user.name,
            email=current_user.email,
            role=current_user.role,
            wallet_address=current_user.wallet_address,
            is_active=current_user.is_active,
            created_at=current_user.created_at,
            cnpj=instituto.cnpj,
            verified=instituto.verified,
            verified_at=instituto.verified_at,
        )

    # admin
    return AdminMeOut(
        id=current_user.id,
        name=current_user.name,
        email=current_user.email,
        role=current_user.role,
        is_active=current_user.is_active,
        created_at=current_user.created_at,
    )


# ── GET /users/me/nfts ────────────────────────────────────────────────────────

@router.get(
    "/me/nfts",
    response_model=list[NFTOut],
    summary="Meus NFTs",
    description=(
        "Retorna todos os NFTs do cidadão autenticado, ordenados do mais recente ao mais antigo. "
        "Retorna 403 se o usuário não for um cidadão."
    ),
)
async def get_my_nfts(
    current_user: CurrentUser,
    db: DBSession,
) -> list[NFTOut]:
    """Lista NFTs do cidadão logado."""
    if current_user.role != UserRole.cidadao:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Este endpoint é exclusivo para cidadãos.",
        )

    result = await db.execute(
        select(NFT)
        .where(NFT.cidadao_id == current_user.id)
        .order_by(NFT.created_at.desc())
    )
    nfts = result.scalars().all()
    return [NFTOut.model_validate(nft) for nft in nfts]


# ── PATCH /users/me ────────────────────────────────────────────────────────────

@router.patch(
    "/me",
    response_model=Union[CidadaoMeOut, InstitutoMeOut, AdminMeOut],
    summary="Atualizar meu perfil",
    description="Permite atualizar ``name`` e ``wallet_address`` do usuário autenticado.",
)
async def update_me(
    current_user: CurrentUser,
    db: DBSession,
    name: str | None = None,
    wallet_address: str | None = None,
) -> Union[CidadaoMeOut, InstitutoMeOut, AdminMeOut]:
    """Atualiza campos do perfil do usuário logado."""
    if name is not None:
        current_user.name = name
    if wallet_address is not None:
        current_user.wallet_address = wallet_address

    db.add(current_user)

    # Reusa o endpoint /me para construir a resposta
    return await get_me(current_user, db)
