from datetime import timedelta

from app.core.tempo import agora
from app.modules.auth.models import Personagem
from app.modules.gamificacao.models import ItemConsumivel, Recompensa
from app.modules.grupos.models import MembroGrupo, RankingGrupo
from app.seed import CATALOGO
from tests.conftest import PNG, cadastrar, criar_atividade


def _grupo(client, h, nome="Invictus"):
    r = client.post("/grupos", json={"nome": nome, "descricao": "Juntos", "categorias": ["Estudos", "Saúde"], "icone": "escudo"}, headers=h)
    assert r.status_code == 201, r.text
    return r.json()


def test_criar_grupo_lider_e_codigo(client):
    h, _ = cadastrar(client)
    g = _grupo(client, h)
    assert g["codigoConvite"] and g["totalMembros"] == 1 and g["categorias"] == ["Estudos", "Saúde"]
    minha = client.get("/grupos/minha", headers=h).json()
    assert minha["membros"][0]["papel"] == "Líder"
    assert minha["grupo"]["xpProximoNivel"] == 300  # nível 1 → próximo nível 2 = 300 XP (tabela do Figma)
    assert len(minha["niveis"]) == 7 and minha["desafiosAtivos"] == []


def test_sem_guilda_minha_da_404(client):
    h, _ = cadastrar(client)
    assert client.get("/grupos/minha", headers=h).status_code == 404


def test_entrar_por_codigo(client):
    h1, _ = cadastrar(client, "ana")
    h2, _ = cadastrar(client, "beto")
    g = _grupo(client, h1)
    assert client.post("/grupos/entrar", json={"codigoConvite": "ZZZZZZ"}, headers=h2).status_code == 404
    assert client.post("/grupos/entrar", json={"codigoConvite": g["codigoConvite"].lower()}, headers=h2).status_code == 200
    assert client.post("/grupos/entrar", json={"codigoConvite": g["codigoConvite"]}, headers=h2).status_code == 409
    assert client.get("/grupos/minha", headers=h2).json()["grupo"]["totalMembros"] == 2


def test_explorar_nao_expoe_codigo_e_filtra(client):
    h, _ = cadastrar(client)
    _grupo(client, h, "Foco total")
    lista = client.get("/grupos", headers=h).json()
    assert lista[0]["codigoConvite"] is None  # código de convite não é público
    assert len(client.get("/grupos?categoria=Estudos", headers=h).json()) == 1
    assert client.get("/grupos?categoria=Leitura", headers=h).json() == []
    assert len(client.get("/grupos?busca=foco&ordenarPor=nivel", headers=h).json()) == 1
    assert client.get("/grupos?busca=zzz", headers=h).json() == []


def test_mural_so_para_membros_e_publicacao(client):
    h1, _ = cadastrar(client, "ana")
    h2, _ = cadastrar(client, "beto")
    gid = _grupo(client, h1)["id"]
    assert client.get(f"/grupos/{gid}/mural", headers=h2).status_code == 403
    assert client.post(f"/grupos/{gid}/mural", json={"conteudoTexto": "oi"}, headers=h2).status_code == 403
    p = client.post(f"/grupos/{gid}/mural", json={"conteudoTexto": "Bora!"}, headers=h1)
    assert p.status_code == 201 and p.json()["autor"]["nomeExibicao"] == "ana"
    assert [x["conteudoTexto"] for x in client.get(f"/grupos/{gid}/mural", headers=h1).json()] == ["Bora!"]
    assert client.post(f"/grupos/{gid}/mural", json={"conteudoTexto": ""}, headers=h1).status_code == 422


def test_checkin_publica_no_mural_e_pontua_na_guilda_uc003(client):
    h, _ = cadastrar(client)
    gid = _grupo(client, h)["id"]
    aid = criar_atividade(client, h, "Ir para academia")
    r = client.post(f"/atividades/{aid}/checkins", headers=h, files={"prova": ("a.png", PNG, "image/png")})
    assert r.status_code == 201 and r.json()["postagem"]["tipoEvento"] == "checkin"
    mural = client.get(f"/grupos/{gid}/mural", headers=h).json()
    assert "Ir para academia" in mural[0]["conteudoTexto"]
    minha = client.get("/grupos/minha", headers=h).json()
    assert minha["membros"][0]["pontuacaoSemanal"] == 100
    assert minha["minhaContribuicao"] == {"xp": 100, "meta": 300}
    assert minha["estatisticas"]["tarefasConcluidasSemana"] == 1 and minha["estatisticas"]["membrosAtivosSemana"] == 1


def test_gestao_de_membros_so_lider_ou_admin(client):
    h1, _ = cadastrar(client, "ana")
    h2, u2 = cadastrar(client, "beto")
    h3, u3 = cadastrar(client, "caio")
    g = _grupo(client, h1)
    for h in (h2, h3):
        client.post("/grupos/entrar", json={"codigoConvite": g["codigoConvite"]}, headers=h)
    gid = g["id"]
    assert client.post(f"/grupos/{gid}/membros/{u3['id']}/promover", headers=h2).status_code == 403  # membro comum
    assert client.post(f"/grupos/{gid}/membros/{u2['id']}/promover", headers=h1).json()["papel"] == "Admin"
    assert client.delete(f"/grupos/{gid}/membros/{u3['id']}", headers=h2).status_code == 204  # agora beto (Admin) pode
    assert client.get("/grupos/minha", headers=h1).json()["grupo"]["totalMembros"] == 2
    assert client.delete(f"/grupos/{gid}/membros/1", headers=h2).status_code == 422  # líder não é removível


def test_ranking_semanal_geral_e_mensal(client):
    h1, _ = cadastrar(client, "ana")
    h2, _ = cadastrar(client, "beto")
    _grupo(client, h1)
    client.post(f"/atividades/{criar_atividade(client, h1)}/checkins", headers=h1)
    client.post(f"/atividades/{criar_atividade(client, h2)}/checkins", headers=h2)
    client.post(f"/atividades/{criar_atividade(client, h2, 'outra')}/checkins", headers=h2)
    # beto não tem guilda → pontuação semanal só existe dentro de guildas (MembroGrupo.pontuacaoSemanal)
    sem = client.get("/ranking?periodo=semanal", headers=h1).json()
    assert [l["usuario"]["nomeExibicao"] for l in sem["linhas"]] == ["ana", "beto"] and sem["linhas"][0]["xp"] == 100
    assert sem["minhaPosicao"]["posicao"] == 1 and sem["minhaPosicao"]["tarefas"] == 1 and sem["linhas"][0]["guilda"]["nome"] == "Invictus"
    assert sem["linhas"][1]["guilda"]["nome"] == "—"
    assert 0 <= sem["reiniciaEmDias"] <= 7
    ger = client.get("/ranking?periodo=geral", headers=h1).json()
    assert [l["usuario"]["nomeExibicao"] for l in ger["linhas"]] == ["beto", "ana"] and ger["minhaPosicao"]["posicao"] == 2
    assert ger["porGuilda"][0]["guilda"]["nome"] == "Invictus"
    r = client.get("/ranking?periodo=mensal", headers=h1)
    assert r.status_code == 501 and "mensal" in r.json()["detail"]
    assert client.get("/ranking?periodo=anual", headers=h1).status_code == 422


def _semear(db):
    for t, d, preco, cat, ic in CATALOGO:
        db.add(Recompensa(titulo=t, descricao=d, preco_moedas=preco, categoria=cat, tipo=cat, icone=ic))
    db.commit()


def test_loja_resgate(client, db):
    _semear(db)
    h, u = cadastrar(client)
    loja = client.get("/loja", headers=h).json()
    assert loja["pontosDisponiveis"] == 0 and len(loja["itens"]) == 8 and loja["proximoPremio"]["titulo"] == "Avatar exclusivo"
    avatar = next(i for i in loja["itens"] if i["titulo"] == "Avatar exclusivo")
    r = client.post(f"/loja/{avatar['id']}/resgatar", headers=h)
    assert r.status_code == 422 and "insuficientes" in r.json()["detail"]
    db.query(Personagem).filter_by(usuario_id=u["id"]).update({"moedas_ouro": 600})
    db.commit()
    assert client.post(f"/loja/{avatar['id']}/resgatar", headers=h).status_code == 204
    assert client.post(f"/loja/{avatar['id']}/resgatar", headers=h).status_code == 409  # não cobra duas vezes
    loja = client.get("/loja", headers=h).json()
    assert loja["pontosDisponiveis"] == 100 and loja["resgatesRealizados"] == 1
    assert next(i for i in loja["itens"] if i["id"] == avatar["id"])["resgatada"] is True
    assert loja["recentes"][0]["titulo"] == "Avatar exclusivo" and " de " in loja["recentes"][0]["data"]
    assert client.post("/loja/9999/resgatar", headers=h).status_code == 404


def test_item_consumivel_e_especializacao_de_recompensa(db):
    """DC: ItemConsumivel ◁— Recompensa (herança)."""
    db.add(ItemConsumivel(titulo="Poção de XP", preco_moedas=300, efeito_status="xp em dobro", multiplicador_xp=2.0))
    db.commit()
    r = db.query(Recompensa).filter_by(titulo="Poção de XP").one()
    assert isinstance(r, ItemConsumivel) and r.multiplicador_xp == 2.0


def test_reset_semanal_automacao(client, db):
    from app.modules.automacoes.jobs import executar_todos

    h, u = cadastrar(client)
    gid = _grupo(client, h)["id"]
    client.post(f"/atividades/{criar_atividade(client, h)}/checkins", headers=h)
    assert db.query(MembroGrupo).filter_by(grupo_id=gid).one().pontuacao_semanal == 100
    assert executar_todos(db) == {"punicoes": 0, "grupos_reiniciados": 0}  # ciclo ainda não venceu
    db.query(RankingGrupo).filter_by(grupo_id=gid).update({"data_ultimo_reset": agora() - timedelta(days=8)})
    db.commit()
    assert executar_todos(db)["grupos_reiniciados"] == 1
    db.expire_all()
    assert db.query(MembroGrupo).filter_by(grupo_id=gid).one().pontuacao_semanal == 0
    assert client.get("/perfil/resumo", headers=h).json()["personagem"]["xpAtual"] == 100  # XP acumulado não é zerado


def test_pendentes_respondem_501_explicativo(client):
    h, _ = cadastrar(client)
    for caminho in ("/desafios", "/conquistas", "/progresso", "/notificacoes", "/configuracoes/notificacoes"):
        r = client.get(caminho, headers=h)
        assert r.status_code == 501 and "não está definida" in r.json()["detail"]
    assert client.get("/desafios").status_code == 401
