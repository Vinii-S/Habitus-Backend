"""Rotas que o frontend JÁ chama (há tela no Figma) mas cujo modelo de dados NÃO existe no Diagrama de Classes,
nos casos de uso nem no diagrama de componentes. Respondem 501 com explicação — melhor que um 404 mudo."""
from fastapi import APIRouter, Depends

from app.core.erros import NaoImplementado
from app.modules.auth.deps import usuario_atual

router = APIRouter(tags=["pendentes de definição"], dependencies=[Depends(usuario_atual)])


def _pendente(o_que: str):
    raise NaoImplementado(f"{o_que}: há tela no Figma, mas a entidade/regra não está definida na documentação (ver docs/ARQUITETURA_BACKEND.md).")


@router.get("/desafios")
def desafios():
    _pendente("Desafios da guilda")


@router.get("/conquistas")
def conquistas():
    _pendente("Conquistas")


@router.get("/progresso")
def progresso():
    _pendente("Progresso e Níveis (Dashboard de Estatísticas — nomes de nível e metas não definidos)")


@router.get("/notificacoes")
def notificacoes():
    _pendente("Notificações")


@router.post("/notificacoes/ler-todas")
def notificacoes_ler_todas():
    _pendente("Notificações")


@router.get("/configuracoes/notificacoes")
def prefs_get():
    _pendente("Preferências de notificação")


@router.put("/configuracoes/notificacoes")
def prefs_put():
    _pendente("Preferências de notificação")
