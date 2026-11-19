from datetime import date, datetime

from sqlalchemy import Boolean, Date, DateTime, Float, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base
from app.core.tempo import agora


class Atividade(Base):
    """DC: Atividade (UC001 "Cadastrar Atividade"). Usuario 1 —cadastra— 0..* Atividade."""

    __tablename__ = "atividade"

    id: Mapped[int] = mapped_column(primary_key=True)
    usuario_id: Mapped[int] = mapped_column(ForeignKey("usuario.id", ondelete="CASCADE"), index=True)
    nome: Mapped[str] = mapped_column(String(120))  # DC, UC001
    descricao: Mapped[str] = mapped_column(String(500), default="")  # DC, UC001
    frequencia: Mapped[str] = mapped_column(String(20), default="Diária")  # DC (String); valores vistos no Figma
    atributo_rpg: Mapped[str | None] = mapped_column(String(40))  # DC — nenhuma tela o preenche
    dificuldade: Mapped[str | None] = mapped_column(String(40))  # DC — nenhuma tela o preenche
    xp_recompensa: Mapped[float] = mapped_column(Float, default=100.0)  # DC; padrão 100 = valor da prévia do Figma
    status_ativa: Mapped[bool] = mapped_column(Boolean, default=True)  # DC (inativarAtividade)
    data_fim: Mapped[date | None] = mapped_column(Date)  # DC, UC001 ("data final") — o formulário do Figma não tem

    # --- Campos que só existem no Figma (tela "Criar tarefa"), ausentes do DC ---
    categoria: Mapped[str] = mapped_column(String(30), default="Outros")
    meta: Mapped[str | None] = mapped_column(String(200))
    duracao_estimada_min: Mapped[int | None] = mapped_column(Integer)
    lembrete_ativo: Mapped[bool] = mapped_column(Boolean, default=False)
    lembrete_horario: Mapped[str | None] = mapped_column(String(5))

    criada_em: Mapped[datetime] = mapped_column(DateTime, default=agora)
