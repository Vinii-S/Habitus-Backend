"""Execução avulsa (para cron do sistema):  python -m app.modules.automacoes"""
from app.core.database import SessionLocal, init_db

if __name__ == "__main__":
    from app.modules.automacoes.jobs import executar_todos

    init_db()
    with SessionLocal() as db:
        print(executar_todos(db))
