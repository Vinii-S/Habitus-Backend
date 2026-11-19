"""Configuração lida de variáveis de ambiente (ver .env.example)."""
import os
from dataclasses import dataclass, field
from pathlib import Path  # pathlib: RNF10 (rodar igual em Windows/Mac/Linux)


def _lista(valor: str) -> list[str]:
    return [v.strip() for v in valor.split(",") if v.strip()]


@dataclass(frozen=True)
class Settings:
    database_url: str = field(default_factory=lambda: os.getenv("HABITUS_DATABASE_URL", "sqlite:///./habitus.db"))
    secret_key: str = field(default_factory=lambda: os.getenv("HABITUS_SECRET_KEY", "dev-only-trocar-em-producao-0123456789"))  # ≥ 32 bytes (HS256)
    token_minutos: int = field(default_factory=lambda: int(os.getenv("HABITUS_TOKEN_MINUTOS", "480")))  # duração: NÃO documentada
    uploads_dir: Path = field(default_factory=lambda: Path(os.getenv("HABITUS_UPLOADS_DIR", "./uploads")))
    cors_origins: list[str] = field(default_factory=lambda: _lista(os.getenv("HABITUS_CORS_ORIGINS", "http://localhost:5173")))
    scheduler_ativo: bool = field(default_factory=lambda: os.getenv("HABITUS_SCHEDULER", "0") == "1")

    # RNF06: tamanho máximo 10 MB e tipos .jpg/.png nas Provas de Conclusão.
    prova_tamanho_max_bytes: int = 10 * 1024 * 1024
    # UC001 fluxo 6a: "limite máximo (ex: 10 tarefas)" — o valor real NÃO está definido na documentação.
    limite_atividades_ativas: int = 10


def get_settings() -> Settings:
    return Settings()


settings = get_settings()
