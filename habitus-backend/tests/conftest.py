import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import sessionmaker

from app.core.database import get_db, init_db, make_engine
from app.core.storage import ArmazenamentoLocal, get_storage
from app.main import create_app

PNG = b"\x89PNG\r\n\x1a\n" + b"0" * 64
JPG = b"\xff\xd8\xff\xe0" + b"0" * 64


@pytest.fixture()
def sessao_factory(tmp_path):
    eng = make_engine(f"sqlite:///{tmp_path / 'teste.db'}")
    init_db(eng)
    return sessionmaker(eng, autoflush=False, expire_on_commit=False)


@pytest.fixture()
def db(sessao_factory):
    with sessao_factory() as s:
        yield s


@pytest.fixture()
def client(sessao_factory, tmp_path):
    app = create_app()
    storage = ArmazenamentoLocal(tmp_path / "midia")

    def _db():
        with sessao_factory() as s:
            yield s

    app.dependency_overrides[get_db] = _db
    app.dependency_overrides[get_storage] = lambda: storage
    c = TestClient(app)
    c.storage_dir = tmp_path / "midia"  # type: ignore[attr-defined]
    return c


def cadastrar(client, nome="ana", email=None, senha="Segura#123"):
    r = client.post(
        "/auth/cadastro",
        json={"nomeCompleto": f"{nome.title()} Teste", "nomeExibicao": nome, "email": email or f"{nome}@teste.dev", "dataNascimento": "2000-01-31", "senha": senha},
    )
    assert r.status_code == 201, r.text
    return {"Authorization": f"Bearer {r.json()['token']}"}, r.json()["usuario"]


def criar_atividade(client, headers, nome="Ler livro", **extra):
    r = client.post("/atividades", json={"nome": nome, "categoria": "Leitura", "frequencia": "Diária", **extra}, headers=headers)
    assert r.status_code == 201, r.text
    return r.json()["id"]
