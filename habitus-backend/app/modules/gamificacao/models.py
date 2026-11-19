"""DC: Recompensa e ItemConsumivel (especialização). Resgate NÃO está no DC (ver docstring)."""
from datetime import datetime

from sqlalchemy import DateTime, Float, ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base
from app.core.tempo import agora


class Recompensa(Base):
    __tablename__ = "recompensa"

    id: Mapped[int] = mapped_column(primary_key=True)
    titulo: Mapped[str] = mapped_column(String(80))  # DC
    descricao: Mapped[str] = mapped_column(String(300), default="")  # DC
    preco_moedas: Mapped[int] = mapped_column(Integer)  # DC
    tipo: Mapped[str] = mapped_column(String(30), default="")  # DC (valores não documentados)
    categoria: Mapped[str] = mapped_column(String(30), default="")  # só no Figma: Personalização/Cupons/Benefícios/Exclusivos
    icone: Mapped[str | None] = mapped_column(String(40))
    classe: Mapped[str] = mapped_column(String(20), default="recompensa")  # discriminador da especialização

    __mapper_args__ = {"polymorphic_on": "classe", "polymorphic_identity": "recompensa"}


class ItemConsumivel(Recompensa):
    """DC: ItemConsumivel ◁— Recompensa ("especializacao"). Itens consumíveis são "Futura" em [REL §7] e
    estão FORA do escopo do semestre em [REL §10]; a tabela existe por fidelidade ao DC, sem endpoint de uso."""

    __tablename__ = "item_consumivel"

    id: Mapped[int] = mapped_column(ForeignKey("recompensa.id", ondelete="CASCADE"), primary_key=True)
    efeito_status: Mapped[str] = mapped_column(String(60), default="")  # DC
    multiplicador_xp: Mapped[float] = mapped_column(Float, default=1.0)  # DC

    __mapper_args__ = {"polymorphic_identity": "consumivel"}


class Resgate(Base):
    """⚠️ NÃO EXISTE NO DC. O DC liga só Personagem—ItemConsumivel ("inventario"), mas a Loja do Figma mostra
    "Resgatado" e "Resgates recentes" também para itens que não são consumíveis (avatar, cupom, tema). Para
    registrar quem resgatou o quê foi preciso esta tabela de associação. Precisa de aprovação da equipe."""

    __tablename__ = "resgate"
    __table_args__ = (UniqueConstraint("personagem_id", "recompensa_id"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    personagem_id: Mapped[int] = mapped_column(ForeignKey("personagem.id", ondelete="CASCADE"), index=True)
    recompensa_id: Mapped[int] = mapped_column(ForeignKey("recompensa.id", ondelete="CASCADE"))
    data: Mapped[datetime] = mapped_column(DateTime, default=agora)
