"""Erros de domínio. Os serviços lançam estes erros; main.py os converte em respostas HTTP."""


class ErroDominio(Exception):
    status = 400

    def __init__(self, mensagem: str):
        super().__init__(mensagem)
        self.mensagem = mensagem


class NaoAutenticado(ErroDominio):
    status = 401


class Proibido(ErroDominio):
    status = 403


class NaoEncontrado(ErroDominio):
    status = 404


class Conflito(ErroDominio):
    status = 409


class RegraDeNegocio(ErroDominio):
    status = 422


class NaoImplementado(ErroDominio):
    """Usado onde a documentação NÃO define a regra/entidade (ver docs/ARQUITETURA_BACKEND.md)."""

    status = 501
