from datetime import datetime

from app.core.schemas import CamelModel
from app.modules.atividades.schemas import AtividadeOut
from app.modules.grupos.schemas import PostagemOut


class ProvaOut(CamelModel):
    id: int
    url_imagem: str
    tamanho_arquivo: float
    tipo_arquivo: str


class CheckInOut(CamelModel):
    id: int
    atividade_id: int
    data_hora: datetime
    status_validacao: str
    xp_ganho: float
    sequencia_streak: int
    minutos: int | None = None
    realizada: bool = True
    prova: ProvaOut | None = None


class ResultadoCheckInOut(CamelModel):
    check_in: CheckInOut
    xp_ganho: float
    subiu_de_nivel: bool
    novo_nivel: int | None = None
    postagem: PostagemOut | None = None


class DiaSemanaOut(CamelModel):
    rotulo: str
    data: str
    feito: bool


class EstatisticasAtividadeOut(CamelModel):
    conclusoes_totais: int
    taxa_conclusao: int
    sequencia_atual: int
    melhor_sequencia: int


class DetalheAtividadeOut(CamelModel):
    atividade: AtividadeOut
    semana: list[DiaSemanaOut]
    dias_feitos: int
    estatisticas: EstatisticasAtividadeOut
    historico: list[CheckInOut]
    motivacao: str | None = None  # texto/citação do Figma: sem origem no DC
    citacao: str | None = None
