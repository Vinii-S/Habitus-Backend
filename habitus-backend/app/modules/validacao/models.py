from datetime import datetime

from sqlalchemy import DateTime, Float, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.core.tempo import agora


class CheckIn(Base):
    """DC: CheckIn. Atividade 1 —registra (composição)— 0..* CheckIn."""

    __tablename__ = "checkin"

    id: Mapped[int] = mapped_column(primary_key=True)
    atividade_id: Mapped[int] = mapped_column(ForeignKey("atividade.id", ondelete="CASCADE"), index=True)
    data_hora: Mapped[datetime] = mapped_column(DateTime, default=agora, index=True)  # DC
    status_validacao: Mapped[str] = mapped_column(String(30), default="registrado")  # DC — valores NÃO documentados
    xp_ganho: Mapped[float] = mapped_column(Float, default=0.0)  # DC
    sequencia_streak: Mapped[int] = mapped_column(Integer, default=1)  # DC
    minutos: Mapped[int | None] = mapped_column(Integer)  # só no Figma (histórico: "30 minutos")

    prova: Mapped["ProvaDeConclusao | None"] = relationship(back_populates="checkin", uselist=False, cascade="all, delete-orphan")


class ProvaDeConclusao(Base):
    """DC: ProvaDeConclusao. CheckIn 1 —anexa (composição)— 0..1 ProvaDeConclusao."""

    __tablename__ = "prova_conclusao"

    id: Mapped[int] = mapped_column(primary_key=True)
    checkin_id: Mapped[int] = mapped_column(ForeignKey("checkin.id", ondelete="CASCADE"), unique=True)
    url_imagem: Mapped[str] = mapped_column(String(255))  # DC
    tamanho_arquivo: Mapped[float] = mapped_column(Float)  # DC (guardado em bytes)
    tipo_arquivo: Mapped[str] = mapped_column(String(30))  # DC

    checkin: Mapped[CheckIn] = relationship(back_populates="prova")
