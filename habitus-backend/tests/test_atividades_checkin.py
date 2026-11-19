from datetime import timedelta

from sqlalchemy import select

from app.core.tempo import agora
from app.modules.validacao.models import CheckIn
from tests.conftest import JPG, PNG, cadastrar, criar_atividade


def test_criar_e_listar_painel(client):
    h, _ = cadastrar(client)
    aid = criar_atividade(client, h, "Ler livro", descricao="30 min", meta="50 páginas", duracaoEstimadaMin=30, lembrete={"ativo": True, "horario": "19:00"})
    painel = client.get("/atividades", headers=h).json()
    a = painel["atividades"][0]
    assert a["id"] == aid and a["status"] == "Não iniciada" and a["progresso"] == 0 and a["hoje"] is True
    assert a["lembrete"] == {"ativo": True, "horario": "19:00"} and a["xpRecompensa"] == 100
    assert set(painel) == {"atividades", "resumoSemana", "metaSemanal"}
    assert painel["metaSemanal"]["total"] == 7


def test_nome_obrigatorio_uc001_4a(client):
    h, _ = cadastrar(client)
    assert client.post("/atividades", json={"nome": "", "categoria": "Leitura"}, headers=h).status_code == 422
    assert client.post("/atividades", json={"nome": "x", "categoria": "Inventada"}, headers=h).status_code == 422


def test_limite_de_atividades_ativas_uc001_6a(client):
    h, _ = cadastrar(client)
    ids = [criar_atividade(client, h, f"t{i}") for i in range(10)]
    r = client.post("/atividades", json={"nome": "11ª", "categoria": "Outros"}, headers=h)
    assert r.status_code == 409 and "Limite de atividades ativas" in r.json()["detail"]
    # excluir (inativar) libera uma vaga
    assert client.delete(f"/atividades/{ids[0]}", headers=h).status_code == 204
    assert client.post("/atividades", json={"nome": "11ª", "categoria": "Outros"}, headers=h).status_code == 201


def test_atividade_de_outro_usuario_da_404(client):
    h1, _ = cadastrar(client, "ana")
    h2, _ = cadastrar(client, "beto")
    aid = criar_atividade(client, h1)
    assert client.get(f"/atividades/{aid}", headers=h2).status_code == 404
    assert client.post(f"/atividades/{aid}/checkins", headers=h2).status_code == 404
    assert client.delete(f"/atividades/{aid}", headers=h2).status_code == 404


def test_checkin_sem_prova_concede_xp_e_marca_concluida(client):
    h, _ = cadastrar(client)
    aid = criar_atividade(client, h)
    r = client.post(f"/atividades/{aid}/checkins", headers=h)
    assert r.status_code == 201, r.text
    body = r.json()
    assert body["xpGanho"] == 100 and body["checkIn"]["sequenciaStreak"] == 1 and body["checkIn"]["prova"] is None
    assert body["subiuDeNivel"] is False
    p = client.get("/perfil/resumo", headers=h).json()["personagem"]
    assert p["xpAtual"] == 100 and p["moedasOuro"] == 100
    a = client.get("/atividades", headers=h).json()["atividades"][0]
    assert a["status"] == "Concluída" and a["progresso"] == 100


def test_checkin_duplicado_no_mesmo_dia_409(client):
    h, _ = cadastrar(client)
    aid = criar_atividade(client, h)
    assert client.post(f"/atividades/{aid}/checkins", headers=h).status_code == 201
    r = client.post(f"/atividades/{aid}/checkins", headers=h)
    assert r.status_code == 409
    assert client.get("/perfil/resumo", headers=h).json()["personagem"]["xpAtual"] == 100  # não pagou XP duas vezes


def test_checkin_com_prova_png_guarda_arquivo(client):
    h, _ = cadastrar(client)
    aid = criar_atividade(client, h)
    r = client.post(f"/atividades/{aid}/checkins", headers=h, files={"prova": ("foto.png", PNG, "image/png")})
    assert r.status_code == 201, r.text
    prova = r.json()["checkIn"]["prova"]
    assert prova["tipoArquivo"] == "image/png" and prova["tamanhoArquivo"] == len(PNG)
    salvo = client.storage_dir / prova["urlImagem"].split("/")[-1]  # type: ignore[attr-defined]
    assert salvo.read_bytes() == PNG and salvo.suffix == ".png"  # nome gerado pelo servidor, não pelo cliente


def test_prova_aceita_jpeg(client):
    h, _ = cadastrar(client)
    aid = criar_atividade(client, h)
    assert client.post(f"/atividades/{aid}/checkins", headers=h, files={"prova": ("a.jpg", JPG, "image/jpeg")}).status_code == 201


def test_prova_invalida_422_e_nao_registra_nada(client, db):
    h, _ = cadastrar(client)
    aid = criar_atividade(client, h)
    casos = [
        ("doc.pdf", b"%PDF-1.4 ...", "application/pdf"),
        ("falso.png", b"isto nao e uma imagem", "image/png"),  # Content-Type mentiroso
        ("grande.png", PNG + b"0" * (10 * 1024 * 1024), "image/png"),  # > 10 MB (RNF06)
    ]
    for nome, conteudo, tipo in casos:
        r = client.post(f"/atividades/{aid}/checkins", headers=h, files={"prova": (nome, conteudo, tipo)})
        assert r.status_code == 422, (nome, r.text)
    assert db.scalars(select(CheckIn)).first() is None
    assert client.get("/perfil/resumo", headers=h).json()["personagem"]["xpAtual"] == 0
    assert list(client.storage_dir.iterdir()) == []  # type: ignore[attr-defined]
    # e continua possível fazer o check-in válido depois (UC003 4a: "volta ao passo 3")
    assert client.post(f"/atividades/{aid}/checkins", headers=h, files={"prova": ("a.png", PNG, "image/png")}).status_code == 201


def test_streak_continua_se_fez_ontem(client, db):
    h, u = cadastrar(client)
    aid = criar_atividade(client, h)
    db.add(CheckIn(atividade_id=aid, data_hora=agora() - timedelta(days=1), xp_ganho=100, sequencia_streak=4))
    db.commit()
    r = client.post(f"/atividades/{aid}/checkins", headers=h)
    assert r.json()["checkIn"]["sequenciaStreak"] == 5


def test_streak_reinicia_apos_pular_dia(client, db):
    h, _ = cadastrar(client)
    aid = criar_atividade(client, h)
    db.add(CheckIn(atividade_id=aid, data_hora=agora() - timedelta(days=3), xp_ganho=100, sequencia_streak=9))
    db.commit()
    assert client.post(f"/atividades/{aid}/checkins", headers=h).json()["checkIn"]["sequenciaStreak"] == 1


def test_subir_de_nivel_rnf09(client):
    h, _ = cadastrar(client)
    resultados = [client.post(f"/atividades/{criar_atividade(client, h, f't{i}')}/checkins", headers=h).json() for i in range(8)]
    assert [r["subiuDeNivel"] for r in resultados] == [False] * 7 + [True]
    assert resultados[-1]["novoNivel"] == 2
    p = client.get("/perfil/resumo", headers=h).json()["personagem"]
    assert p["nivel"] == 2 and p["xpAtual"] == 800 and p["xpProximoNivel"] == 1500


def test_detalhe_da_atividade(client):
    h, _ = cadastrar(client)
    aid = criar_atividade(client, h)
    client.post(f"/atividades/{aid}/checkins", headers=h)
    d = client.get(f"/atividades/{aid}", headers=h).json()
    assert len(d["semana"]) == 7 and d["diasFeitos"] == 1
    assert d["estatisticas"]["conclusoesTotais"] == 1 and d["estatisticas"]["sequenciaAtual"] == 1
    assert len(d["historico"]) == 1 and d["historico"][0]["realizada"] is True


def test_excluir_preserva_historico_mas_some_da_lista(client, db):
    h, _ = cadastrar(client)
    aid = criar_atividade(client, h)
    client.post(f"/atividades/{aid}/checkins", headers=h)
    assert client.delete(f"/atividades/{aid}", headers=h).status_code == 204
    assert client.get("/atividades", headers=h).json()["atividades"] == []
    assert client.get(f"/atividades/{aid}", headers=h).status_code == 404
    assert db.scalars(select(CheckIn)).first() is not None  # inativação, não remoção
