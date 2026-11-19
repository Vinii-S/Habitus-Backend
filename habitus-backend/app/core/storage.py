"""Componente "Armazenamento de Mídia / Fotos" (diagrama de componentes).

Hoje: pasta local. Está atrás de uma interface para trocar por outro armazenamento sem mexer nos módulos.
O nome do arquivo é gerado aqui (uuid) — nunca vem do cliente, o que evita path traversal.
"""
import uuid
from pathlib import Path
from typing import Protocol

from app.core.config import settings

PREFIXO_URL = "/midia"


class ArmazenamentoMidia(Protocol):
    def salvar(self, conteudo: bytes, extensao: str) -> str: ...
    def remover(self, url: str) -> None: ...


class ArmazenamentoLocal:
    def __init__(self, pasta: Path):
        self.pasta = pasta
        self.pasta.mkdir(parents=True, exist_ok=True)

    def salvar(self, conteudo: bytes, extensao: str) -> str:
        nome = f"{uuid.uuid4().hex}.{extensao}"
        (self.pasta / nome).write_bytes(conteudo)
        return f"{PREFIXO_URL}/{nome}"

    def remover(self, url: str) -> None:
        alvo = self.pasta / Path(url).name
        alvo.unlink(missing_ok=True)


_padrao: ArmazenamentoLocal | None = None


def get_storage() -> ArmazenamentoMidia:
    global _padrao
    if _padrao is None:
        _padrao = ArmazenamentoLocal(settings.uploads_dir)
    return _padrao
