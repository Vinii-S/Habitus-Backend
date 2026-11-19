from datetime import date

from pydantic import Field

from app.core.schemas import CamelModel

EMAIL_RE = r"^\S+@\S+\.\S+$"


class UsuarioOut(CamelModel):
    id: int
    nome_completo: str
    nome_exibicao: str
    email: str
    data_nascimento: date | None = None
    genero: str | None = None
    bio: str | None = None
    foto_perfil: str | None = None
    foto_capa: str | None = None


class PersonagemOut(CamelModel):
    id: int
    nivel: int
    xp_atual: float
    xp_proximo_nivel: float
    moedas_ouro: int
    forca: int
    intelecto: int
    constituicao: int


class CadastroIn(CamelModel):
    nome_completo: str = Field(min_length=1, max_length=120)
    nome_exibicao: str = Field(min_length=1, max_length=40)
    email: str = Field(pattern=EMAIL_RE, max_length=254)
    data_nascimento: date
    senha: str = Field(min_length=8, max_length=128)  # mínimo de 8: suposição (política de senha não documentada)


class LoginIn(CamelModel):
    email: str
    senha: str


class SessaoOut(CamelModel):
    token: str
    usuario: UsuarioOut


class PerfilResumoOut(CamelModel):
    usuario: UsuarioOut
    personagem: PersonagemOut


class PerfilUpdateIn(CamelModel):
    """Só estes campos são editáveis (RF04). Campos extras enviados pelo frontend (id, e-mail…) são ignorados."""

    nome_completo: str | None = Field(default=None, min_length=1, max_length=120)
    nome_exibicao: str | None = Field(default=None, min_length=1, max_length=40)
    data_nascimento: date | None = None
    genero: str | None = Field(default=None, max_length=40)
    bio: str | None = Field(default=None, max_length=200)


class AmigoIn(CamelModel):
    nome_exibicao: str
