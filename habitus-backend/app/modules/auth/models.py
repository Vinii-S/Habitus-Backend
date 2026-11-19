"""Entidades do Diagrama de Classes: Usuario, Personagem e a associação reflexiva amigoDe.

Personagem fica neste módulo porque o DC o liga a Usuario por COMPOSIÇÃO (1—1, "possui"): nasce e morre com
o usuário. (Isso também respeita o diagrama de componentes: gamificacao depende de auth, não o contrário.)
"""
from datetime import date

from sqlalchemy import Date, Float, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class Usuario(Base):
    __tablename__ = "usuario"

    id: Mapped[int] = mapped_column(primary_key=True)
    nome_completo: Mapped[str] = mapped_column(String(120))  # DC
    nome_exibicao: Mapped[str] = mapped_column(String(40), unique=True, index=True)  # DC (UC002 chama de "codinome")
    email: Mapped[str] = mapped_column(String(254), unique=True, index=True)  # DC
    senha_hash: Mapped[str] = mapped_column(String(255))  # DC (senhaHash) — nunca sai pela API
    data_nascimento: Mapped[date | None] = mapped_column(Date)  # DC
    genero: Mapped[str | None] = mapped_column(String(40))  # DC
    bio: Mapped[str | None] = mapped_column(String(200))  # DC (limite 200: contador "68/200" no Figma)
    foto_perfil: Mapped[str | None] = mapped_column(String(255))  # DC
    foto_capa: Mapped[str | None] = mapped_column(String(255))  # DC

    personagem: Mapped["Personagem"] = relationship(back_populates="usuario", uselist=False, cascade="all, delete-orphan")


class Personagem(Base):
    __tablename__ = "personagem"

    id: Mapped[int] = mapped_column(primary_key=True)
    usuario_id: Mapped[int] = mapped_column(ForeignKey("usuario.id", ondelete="CASCADE"), unique=True)
    nivel: Mapped[int] = mapped_column(Integer, default=1)  # DC
    xp_atual: Mapped[float] = mapped_column(Float, default=0.0)  # DC (acumulado: Figma mostra "Total acumulado")
    # Valor inicial = gamificacao.regras.xp_proximo_nivel(1). Duplicado aqui de propósito (auth não importa
    # gamificacao); tests/test_gamificacao.py garante que os dois continuam iguais.
    xp_proximo_nivel: Mapped[float] = mapped_column(Float, default=750.0)  # DC
    moedas_ouro: Mapped[int] = mapped_column(Integer, default=0)  # DC
    forca: Mapped[int] = mapped_column(Integer, default=0)  # DC
    intelecto: Mapped[int] = mapped_column(Integer, default=0)  # DC
    constituicao: Mapped[int] = mapped_column(Integer, default=0)  # DC

    usuario: Mapped[Usuario] = relationship(back_populates="personagem")


class Amizade(Base):
    """DC: Usuario 0..* —amigoDe— 0..* Usuario. O DC não diz se há convite/aceite; aqui é vínculo direto
    nos dois sentidos (duas linhas) — decisão provisória."""

    __tablename__ = "amizade"

    usuario_id: Mapped[int] = mapped_column(ForeignKey("usuario.id", ondelete="CASCADE"), primary_key=True)
    amigo_id: Mapped[int] = mapped_column(ForeignKey("usuario.id", ondelete="CASCADE"), primary_key=True)
