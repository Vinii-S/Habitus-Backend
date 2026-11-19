"""Entidades do DC: Grupo, MembroGrupo, PostagemMural, RankingGrupo (todas ligadas a Grupo por composição)."""
from datetime import datetime

from sqlalchemy import DateTime, Float, ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.core.tempo import agora
from app.modules.auth.models import Usuario


class Grupo(Base):
    __tablename__ = "grupo"

    id: Mapped[int] = mapped_column(primary_key=True)
    nome: Mapped[str] = mapped_column(String(60), index=True)  # DC
    descricao: Mapped[str] = mapped_column(String(300), default="")  # DC
    codigo_convite: Mapped[str] = mapped_column(String(12), unique=True, index=True)  # DC
    nivel_grupo: Mapped[int] = mapped_column(Integer, default=1)  # DC — nenhuma regra de subida documentada
    # --- só no Figma (Explorar Guildas); ausentes do DC ---
    categorias: Mapped[str] = mapped_column(String(200), default="")  # lista separada por vírgula
    icone: Mapped[str | None] = mapped_column(String(40))  # chave do ícone/emblema

    membros: Mapped[list["MembroGrupo"]] = relationship(back_populates="grupo", cascade="all, delete-orphan")
    postagens: Mapped[list["PostagemMural"]] = relationship(back_populates="grupo", cascade="all, delete-orphan")
    ranking: Mapped["RankingGrupo"] = relationship(back_populates="grupo", uselist=False, cascade="all, delete-orphan")


class MembroGrupo(Base):
    __tablename__ = "membro_grupo"
    __table_args__ = (UniqueConstraint("grupo_id", "usuario_id"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    grupo_id: Mapped[int] = mapped_column(ForeignKey("grupo.id", ondelete="CASCADE"), index=True)
    usuario_id: Mapped[int] = mapped_column(ForeignKey("usuario.id", ondelete="CASCADE"), index=True)
    papel: Mapped[str] = mapped_column(String(20), default="Membro")  # DC (String): 'Líder' | 'Admin' | 'Membro' — valores NÃO documentados
    data_entrada: Mapped[datetime] = mapped_column(DateTime, default=agora)  # DC
    pontuacao_semanal: Mapped[float] = mapped_column(Float, default=0.0)  # DC

    grupo: Mapped[Grupo] = relationship(back_populates="membros")
    usuario: Mapped[Usuario] = relationship()


class PostagemMural(Base):
    __tablename__ = "postagem_mural"

    id: Mapped[int] = mapped_column(primary_key=True)
    grupo_id: Mapped[int] = mapped_column(ForeignKey("grupo.id", ondelete="CASCADE"), index=True)
    autor_id: Mapped[int] = mapped_column(ForeignKey("usuario.id", ondelete="CASCADE"))  # DC: relação "autor"
    conteudo_texto: Mapped[str] = mapped_column(String(500))  # DC
    data_postagem: Mapped[datetime] = mapped_column(DateTime, default=agora, index=True)  # DC
    tipo_evento: Mapped[str] = mapped_column(String(30), default="mensagem")  # DC — valores NÃO documentados

    grupo: Mapped[Grupo] = relationship(back_populates="postagens")
    autor: Mapped[Usuario] = relationship()


class RankingGrupo(Base):
    __tablename__ = "ranking_grupo"

    id: Mapped[int] = mapped_column(primary_key=True)
    grupo_id: Mapped[int] = mapped_column(ForeignKey("grupo.id", ondelete="CASCADE"), unique=True)
    liga_atual: Mapped[str] = mapped_column(String(30), default="Liga 1")  # DC — nomes das ligas NÃO documentados
    data_ultimo_reset: Mapped[datetime] = mapped_column(DateTime, default=agora)  # DC

    grupo: Mapped[Grupo] = relationship(back_populates="ranking")
