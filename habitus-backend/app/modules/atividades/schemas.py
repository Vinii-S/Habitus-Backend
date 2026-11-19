from datetime import date, datetime
from typing import Literal

from pydantic import Field

from app.core.catalogos import Categoria
from app.core.schemas import CamelModel

Frequencia = Literal["Diária", "Semanal", "Mensal", "Personalizada"]
StatusTarefa = Literal["Concluída", "Em andamento", "Não iniciada", "Atrasada"]


class LembreteIO(CamelModel):
    ativo: bool
    horario: str = Field(pattern=r"^\d{2}:\d{2}$")


class NovaAtividadeIn(CamelModel):
    nome: str = Field(min_length=1, max_length=120)
    descricao: str | None = Field(default="", max_length=500)
    categoria: Categoria = "Outros"
    frequencia: Frequencia = "Diária"
    meta: str | None = Field(default=None, max_length=200)
    duracao_estimada_min: int | None = Field(default=None, ge=1, le=1440)
    lembrete: LembreteIO | None = None
    data_fim: date | None = None  # DC/UC001; o frontend atual não envia


class AtividadeOut(CamelModel):
    id: int
    nome: str
    descricao: str
    frequencia: Frequencia
    atributo_rpg: str | None = None
    dificuldade: str | None = None
    xp_recompensa: float
    status_ativa: bool
    data_fim: date | None = None
    categoria: Categoria
    meta: str | None = None
    duracao_estimada_min: int | None = None
    lembrete: LembreteIO | None = None
    # Derivados dos check-ins (ver validacao.service.status_atividades — regra PROVISÓRIA)
    status: StatusTarefa
    progresso: int
    hoje: bool


class ResumoSemanaOut(CamelModel):
    intervalo: str
    xp: float
    concluidas: int
    em_andamento: int
    nao_iniciadas: int


class MetaSemanalOut(CamelModel):
    descricao: str
    feitas: int
    total: int


class PainelTarefasOut(CamelModel):
    atividades: list[AtividadeOut]
    resumo_semana: ResumoSemanaOut
    meta_semanal: MetaSemanalOut


class CriadaOut(CamelModel):
    id: int
    criada_em: datetime
