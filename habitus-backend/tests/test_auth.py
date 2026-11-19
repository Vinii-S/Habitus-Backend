from tests.conftest import cadastrar


def test_cadastro_devolve_camelcase_e_nao_vaza_senha(client):
    r = client.post("/auth/cadastro", json={"nomeCompleto": "Maria S", "nomeExibicao": "maria", "email": "Maria@Teste.dev", "dataNascimento": "2000-05-10", "senha": "Segura#123"})
    assert r.status_code == 201
    u = r.json()["usuario"]
    assert u["nomeCompleto"] == "Maria S" and u["email"] == "maria@teste.dev"  # e-mail normalizado
    assert "senha" not in str(u).lower() and "hash" not in str(u).lower()


def test_cadastro_duplicado_e_validacao(client):
    cadastrar(client, "ana")
    assert client.post("/auth/cadastro", json={"nomeCompleto": "x", "nomeExibicao": "outra", "email": "ana@teste.dev", "dataNascimento": "2000-01-01", "senha": "Segura#123"}).status_code == 409
    assert client.post("/auth/cadastro", json={"nomeCompleto": "x", "nomeExibicao": "ANA", "email": "n@teste.dev", "dataNascimento": "2000-01-01", "senha": "Segura#123"}).status_code == 409
    assert client.post("/auth/cadastro", json={"nomeCompleto": "x", "nomeExibicao": "z", "email": "invalido", "dataNascimento": "2000-01-01", "senha": "Segura#123"}).status_code == 422
    assert client.post("/auth/cadastro", json={"nomeCompleto": "x", "nomeExibicao": "z", "email": "z@teste.dev", "dataNascimento": "2000-01-01", "senha": "curta"}).status_code == 422


def test_login(client):
    cadastrar(client, "ana")
    ok = client.post("/auth/login", json={"email": "ANA@teste.dev", "senha": "Segura#123"})
    assert ok.status_code == 200 and ok.json()["token"]
    # mesma resposta para senha errada e e-mail inexistente
    a = client.post("/auth/login", json={"email": "ana@teste.dev", "senha": "errada"})
    b = client.post("/auth/login", json={"email": "nao@existe.dev", "senha": "Segura#123"})
    assert a.status_code == b.status_code == 401 and a.json() == b.json()


def test_rotas_exigem_token(client):
    for caminho in ("/perfil/resumo", "/atividades", "/ranking", "/loja", "/grupos/minha"):
        assert client.get(caminho).status_code == 401
    assert client.get("/perfil", headers={"Authorization": "Bearer lixo"}).status_code == 401


def test_perfil_resumo_cria_personagem_composicao(client):
    h, _ = cadastrar(client)
    r = client.get("/perfil/resumo", headers=h).json()
    p = r["personagem"]
    assert p["nivel"] == 1 and p["xpAtual"] == 0 and p["xpProximoNivel"] == 750 and p["moedasOuro"] == 0


def test_atualizar_perfil_ignora_campos_protegidos(client):
    h, u = cadastrar(client)
    # o frontend envia o objeto inteiro de volta (inclui id e e-mail): só campos editáveis valem
    r = client.patch("/perfil", json={**u, "email": "hacker@x.dev", "id": 999, "bio": "olá", "genero": "Feminino"}, headers=h)
    assert r.status_code == 200
    assert r.json()["bio"] == "olá" and r.json()["email"] == u["email"] and r.json()["id"] == u["id"]
    assert client.patch("/perfil", json={"bio": "x" * 201}, headers=h).status_code == 422  # limite 200 do Figma


def test_amigos(client):
    h1, _ = cadastrar(client, "ana")
    h2, _ = cadastrar(client, "beto")
    assert client.post("/amigos", json={"nomeExibicao": "beto"}, headers=h1).status_code == 201
    assert [a["nomeExibicao"] for a in client.get("/amigos", headers=h2).json()] == ["ana"]  # vínculo nos dois sentidos
    assert client.post("/amigos", json={"nomeExibicao": "ninguem"}, headers=h1).status_code == 404  # UC002 4a
    assert client.post("/amigos", json={"nomeExibicao": "ana"}, headers=h1).status_code == 422
