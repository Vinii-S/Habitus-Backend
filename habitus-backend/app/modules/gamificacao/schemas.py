from typing import Literal

from app.core.schemas import CamelModel
from app.modules.grupos.schemas import UsuarioResumoOut

PeriodoRanking = Literal["geral", "semanal", "mensal"]


class RecompensaOut(CamelModel):
    id: int
    titulo: str
    descricao: str
    preco_moedas: int
    tipo: str
    categoria: str
    resgatada: bool
    icone: str | None = None


class ProximoPremioOut(CamelModel):
    titulo: str
    atual: int
    total: int


class RecenteOut(CamelModel):
    titulo: str
    data: str


class PainelLojaOut(CamelModel):
    pontos_disponiveis: int
    resgates_realizados: int
    proximo_premio: ProximoPremioOut | None = None
    itens: list[RecompensaOut]
    recentes: list[RecenteOut]


class GuildaMiniOut(CamelModel):
    nome: str
    icone: str


class LinhaRankingOut(CamelModel):
    posicao: int
    usuario: UsuarioResumoOut
    guilda: GuildaMiniOut
    xp: float
    tarefas: int
    sequencia_dias: int


class MinhaPosicaoOut(CamelModel):
    posicao: int
    xp: float
    delta_xp: float
    tarefas: int
    meta_semanal_pct: int
    sequencia_dias: int


class RankingGuildaOut(CamelModel):
    posicao: int
    guilda: GuildaMiniOut
    xp: float
    max_xp: float


class ConquistaRankingOut(CamelModel):
    titulo: str
    descricao: str


class ResumoRankingOut(CamelModel):
    periodo: PeriodoRanking
    reinicia_em_dias: int
    linhas: list[LinhaRankingOut]
    minha_posicao: MinhaPosicaoOut
    por_guilda: list[RankingGuildaOut]
    conquistas_do_ranking: list[ConquistaRankingOut]
