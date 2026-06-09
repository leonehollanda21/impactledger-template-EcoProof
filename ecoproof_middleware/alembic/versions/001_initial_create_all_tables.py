"""initial: create all tables

Revision ID: 001_initial
Revises:
Create Date: 2026-05-25 00:00:00.000000

"""
from typing import Sequence, Union

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql
from alembic import op

revision: str = "001_initial"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # --- LIMPEZA DE ENUMS PARA EVITAR ERROS DUPLICATEOBJECT ---
    for enum_name in [
        "assinadopor",
        "statuslimpeza",
        "statusparticipacao",
        "statusevento",
        "tipoacao",
        "userrole",
    ]:
        op.execute(f"DROP TYPE IF EXISTS {enum_name} CASCADE")

    # ── Tabela: users ────────────────────────────────────────────────────────
    op.create_table(
        "users",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("name", sa.String(100), nullable=False),
        sa.Column("email", sa.String(200), nullable=False),
        sa.Column("password_hash", sa.String(255), nullable=False),
        sa.Column(
            "role",
            sa.Enum("cidadao", "instituto", "admin", name="userrole"),
            nullable=False,
        ),
        sa.Column("wallet_address", sa.String(255), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("email"),
    )
    op.create_index("ix_users_id", "users", ["id"])
    op.create_index("ix_users_email", "users", ["email"])

    # ── Tabela: cidadaos ─────────────────────────────────────────────────────
    op.create_table(
        "cidadaos",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("total_points", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(["id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )

    # ── Tabela: institutos ───────────────────────────────────────────────────
    op.create_table(
        "institutos",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("cnpj", sa.String(20), nullable=False),
        sa.Column("verified", sa.Boolean(), nullable=False),
        sa.Column("verified_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("cnpj"),
    )
    op.create_index("ix_institutos_cnpj", "institutos", ["cnpj"])

    # ── Tabela: eventos ──────────────────────────────────────────────────────
    op.create_table(
        "eventos",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("instituto_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("titulo", sa.String(200), nullable=False),
        sa.Column("descricao", sa.Text(), nullable=True),
        sa.Column(
            "tipo_acao",
            sa.Enum("lixo_rua", "praia", "corrego", "queimada", "outro", name="tipoacao"),
            nullable=False,
        ),
        sa.Column("local", sa.String(300), nullable=False),
        sa.Column("data_evento", sa.DateTime(timezone=True), nullable=False),
        sa.Column("foto_capa_url", sa.String(500), nullable=True),
        sa.Column(
            "status",
            sa.Enum("ativo", "encerrado", "cancelado", name="statusevento"),
            nullable=False,
        ),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["instituto_id"], ["institutos.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_eventos_id", "eventos", ["id"])
    op.create_index("ix_eventos_instituto_id", "eventos", ["instituto_id"])

    # ── Tabela: limpezas_individuais ─────────────────────────────────────────
    op.create_table(
        "limpezas_individuais",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("cidadao_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("foto_antes_url", sa.String(500), nullable=False),
        sa.Column("foto_depois_url", sa.String(500), nullable=False),
        sa.Column(
            "tipo_acao",
            sa.Enum("lixo_rua", "praia", "corrego", "queimada", "outro", name="tipoacao"),
            nullable=False,
        ),
        sa.Column(
            "status",
            sa.Enum("pendente", "aprovado", "reprovado", name="statuslimpeza"),
            nullable=False,
        ),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["cidadao_id"], ["cidadaos.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_limpezas_individuais_id", "limpezas_individuais", ["id"])
    op.create_index("ix_limpezas_individuais_cidadao_id", "limpezas_individuais", ["cidadao_id"])

    # ── Tabela: participacoes ────────────────────────────────────────────────
    op.create_table(
        "participacoes",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("evento_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("cidadao_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("foto_url", sa.String(500), nullable=True),
        sa.Column(
            "status",
            sa.Enum(
                "confirmado", "foto_enviada", "aprovado", "rejeitado",
                name="statusparticipacao",
            ),
            nullable=False,
        ),
        sa.Column("checkin_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("motivo_rejeicao", sa.Text(), nullable=True),
        sa.ForeignKeyConstraint(["cidadao_id"], ["cidadaos.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["evento_id"], ["eventos.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("evento_id", "cidadao_id", name="uq_participacao_evento_cidadao"),
    )
    op.create_index("ix_participacoes_id", "participacoes", ["id"])
    op.create_index("ix_participacoes_evento_id", "participacoes", ["evento_id"])
    op.create_index("ix_participacoes_cidadao_id", "participacoes", ["cidadao_id"])

    # ── Tabela: validacoes ───────────────────────────────────────────────────
    op.create_table(
        "validacoes",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("limpeza_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("participacao_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("resultado", sa.Boolean(), nullable=False),
        sa.Column("score", sa.Float(), nullable=True),
        sa.Column("motivo", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["limpeza_id"], ["limpezas_individuais.id"], ondelete="SET NULL"
        ),
        sa.ForeignKeyConstraint(
            ["participacao_id"], ["participacoes.id"], ondelete="SET NULL"
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_validacoes_id", "validacoes", ["id"])
    op.create_index("ix_validacoes_limpeza_id", "validacoes", ["limpeza_id"])
    op.create_index("ix_validacoes_participacao_id", "validacoes", ["participacao_id"])

    # ── Tabela: nfts ─────────────────────────────────────────────────────────
    op.create_table(
        "nfts",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("token_id", sa.String(100), nullable=False),
        sa.Column("cidadao_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("limpeza_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("participacao_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column(
            "assinado_por",
            sa.Enum("ecoproof", "instituto", name="assinadopor"),
            nullable=False,
        ),
        sa.Column("instituto_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("metadata_url", sa.String(500), nullable=False),
        sa.Column("tx_hash", sa.String(255), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["cidadao_id"], ["cidadaos.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(
            ["limpeza_id"], ["limpezas_individuais.id"], ondelete="SET NULL"
        ),
        sa.ForeignKeyConstraint(
            ["participacao_id"], ["participacoes.id"], ondelete="SET NULL"
        ),
        sa.ForeignKeyConstraint(
            ["instituto_id"], ["institutos.id"], ondelete="SET NULL"
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("token_id"),
        sa.UniqueConstraint("tx_hash"),
    )
    op.create_index("ix_nfts_id", "nfts", ["id"])
    op.create_index("ix_nfts_token_id", "nfts", ["token_id"])
    op.create_index("ix_nfts_tx_hash", "nfts", ["tx_hash"])
    op.create_index("ix_nfts_cidadao_id", "nfts", ["cidadao_id"])

def downgrade() -> None:
    # Tabelas em ordem reversa de dependência
    op.drop_table("nfts")
    op.drop_table("validacoes")
    op.drop_table("participacoes")
    op.drop_table("limpezas_individuais")
    op.drop_table("eventos")
    op.drop_table("institutos")
    op.drop_table("cidadaos")
    op.drop_table("users")

    # Drop enums
    for enum_name in [
        "assinadopor",
        "statuslimpeza",
        "statusparticipacao",
        "statusevento",
        "tipoacao",
        "userrole",
    ]:
        op.execute(f"DROP TYPE IF EXISTS {enum_name}")
