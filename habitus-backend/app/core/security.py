"""Hash de senha (DC: Usuario.senhaHash) e token.

Escolhas NÃO documentadas (recomendação técnica a validar): scrypt da biblioteca padrão (sem dependência
compilada → RNF10) e JWT HS256 enviado como "Authorization: Bearer".
"""
import base64
import hashlib
import hmac
import os
from datetime import timedelta

import jwt

from app.core.config import settings
from app.core.erros import NaoAutenticado
from app.core.tempo import agora

_N, _R, _P = 2**14, 8, 1


def hash_senha(senha: str) -> str:
    sal = os.urandom(16)
    h = hashlib.scrypt(senha.encode(), salt=sal, n=_N, r=_R, p=_P, dklen=32)
    return "scrypt${}${}${}${}${}".format(_N, _R, _P, base64.b64encode(sal).decode(), base64.b64encode(h).decode())


def verificar_senha(senha: str, armazenado: str) -> bool:
    try:
        _, n, r, p, sal, h = armazenado.split("$")
        esperado = base64.b64decode(h)
        calculado = hashlib.scrypt(senha.encode(), salt=base64.b64decode(sal), n=int(n), r=int(r), p=int(p), dklen=len(esperado))
        return hmac.compare_digest(esperado, calculado)
    except (ValueError, TypeError):
        return False


def criar_token(usuario_id: int) -> str:
    exp = agora() + timedelta(minutes=settings.token_minutos)
    return jwt.encode({"sub": str(usuario_id), "exp": exp}, settings.secret_key, algorithm="HS256")


def ler_token(token: str) -> int:
    try:
        dados = jwt.decode(token, settings.secret_key, algorithms=["HS256"])
        return int(dados["sub"])
    except (jwt.PyJWTError, KeyError, ValueError) as exc:
        raise NaoAutenticado("Sessão inválida ou expirada.") from exc
