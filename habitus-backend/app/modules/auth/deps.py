"""Dependência "usuário autenticado" — todos os componentes dependem de AUTH (setas "depende de")."""
from fastapi import Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.erros import NaoAutenticado
from app.core.security import ler_token
from app.modules.auth.models import Usuario

_bearer = HTTPBearer(auto_error=False)


def usuario_atual(
    cred: HTTPAuthorizationCredentials | None = Depends(_bearer),
    db: Session = Depends(get_db),
) -> Usuario:
    if cred is None:
        raise NaoAutenticado("Autenticação necessária.")
    usuario = db.get(Usuario, ler_token(cred.credentials))
    if usuario is None:
        raise NaoAutenticado("Sessão inválida ou expirada.")
    return usuario
