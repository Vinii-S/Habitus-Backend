"""SQLite (RNF04) com SQLAlchemy. O componente "SQLite Banco de Dados" do diagrama de componentes."""
from collections.abc import Iterator

from sqlalchemy import create_engine, event
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from app.core.config import settings


class Base(DeclarativeBase):
    pass


def make_engine(url: str):
    kwargs = {}
    if url.startswith("sqlite"):
        # A API atende requisições simultâneas (RNF05): cada requisição roda em uma thread.
        kwargs["connect_args"] = {"check_same_thread": False}
    engine = create_engine(url, **kwargs)
    if url.startswith("sqlite"):

        @event.listens_for(engine, "connect")
        def _pragmas(conn, _):  # noqa: ANN001
            cur = conn.cursor()
            cur.execute("PRAGMA foreign_keys=ON")  # SQLite não aplica FKs por padrão
            cur.execute("PRAGMA journal_mode=WAL")  # leituras não bloqueiam escritas
            cur.close()

    return engine


engine = make_engine(settings.database_url)
SessionLocal = sessionmaker(engine, autoflush=False, expire_on_commit=False)


def get_db() -> Iterator[Session]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db(eng=None) -> None:
    """Cria as tabelas. Importar os modelos aqui garante o registro de todos no metadata."""
    from app.modules.atividades import models as _a  # noqa: F401
    from app.modules.auth import models as _b  # noqa: F401
    from app.modules.gamificacao import models as _c  # noqa: F401
    from app.modules.grupos import models as _d  # noqa: F401
    from app.modules.validacao import models as _e  # noqa: F401

    Base.metadata.create_all(eng or engine)
