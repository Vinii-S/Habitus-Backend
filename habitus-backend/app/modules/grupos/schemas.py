from datetime import datetime

from pydantic import Field

from app.core.catalogos import Categoria
from app.core.schemas import CamelModel


class UsuarioResumoOut(CamelModel):
    id: int
    nome_exibicao: str
    foto_perfil: str | None = None


class GrupoOut(CamelModel):
    id: int
    nome: str
    descricao: str
    codigo_convite: str | None = None  # só aparece para quem é membro
    nivel_grupo: int
    categorias: list[str]
    total_membros: int
    xp_total: float
    xp_proximo_nivel: float | None = None
    icone: str


class MembroOut(CamelModel):
    id: int
    papel: str
    data_entrada: datetime | None = None
    pontuacao_semanal: float
    usuario: UsuarioResumoOut


class PostagemOut(CamelModel):
    id: int
    conteudo_texto: str
    data_postagem: datetime
    tipo_evento: str
    autor: UsuarioResumoOut
    curtidas: int | None = None  # existe no Figma (♥/💬), mas não no DC → não implementado
    comentarios: int | None = None


class NivelGuildaOut(CamelModel):
    nivel: int
    xp_necessario: int


class ContribuicaoOut(CamelModel):
    xp: float
    meta: float


class EstatisticasGuildaOut(CamelModel):
    tarefas_concluidas_semana: int
    dias_sequencia: int
    membros_ativos_semana: int
    xp_total: float


class DetalheGuildaOut(CamelModel):
    grupo: GrupoOut
    membros: list[MembroOut]
    minha_contribuicao: ContribuicaoOut
    niveis: list[NivelGuildaOut]
    estatisticas: EstatisticasGuildaOut
    desafios_ativos: list[dict] = []  # entidade Desafio não existe no DC


class CriarGrupoIn(CamelModel):
    nome: str = Field(min_length=1, max_length=60)
    descricao: str = Field(default="", max_length=300)
    categorias: list[Categoria] = []
    icone: str | None = Field(default=None, max_length=40)


class EntrarGrupoIn(CamelModel):
    codigo_convite: str = Field(min_length=1, max_length=12)


class PublicarIn(CamelModel):
    conteudo_texto: str = Field(min_length=1, max_length=500)
