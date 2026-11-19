"""Entrada da API. Rodar:  uvicorn app.main:app --reload   (documentação interativa em /docs)"""
import asyncio
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles

from app.api import atividades, auth, gamificacao, grupos, pendentes
from app.core.config import settings
from app.core.database import init_db
from app.core.erros import ErroDominio
from app.core.storage import PREFIXO_URL


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    tarefa = None
    if settings.scheduler_ativo:
        from app.modules.automacoes.scheduler import loop

        tarefa = asyncio.create_task(loop())
    yield
    if tarefa:
        tarefa.cancel()


def create_app() -> FastAPI:
    app = FastAPI(title="Habitus API", version="0.1.0", lifespan=lifespan)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,  # o frontend Vite (http://localhost:5173)
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.exception_handler(ErroDominio)
    async def _erro_dominio(_: Request, exc: ErroDominio):
        return JSONResponse({"detail": exc.mensagem}, status_code=exc.status)

    for r in (auth.router, atividades.router, grupos.router, gamificacao.router, pendentes.router):
        app.include_router(r)

    settings.uploads_dir.mkdir(parents=True, exist_ok=True)
    app.mount(PREFIXO_URL, StaticFiles(directory=settings.uploads_dir), name="midia")

    @app.get("/saude", tags=["infra"])
    def saude():
        return {"status": "ok"}

    return app


app = create_app()
