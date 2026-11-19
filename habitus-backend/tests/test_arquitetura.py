"""Garante que o código respeita as dependências do Diagrama de Componentes (Diagrama de Componentes.drawio.html).

Setas do diagrama (A → B = A usa B):
  ATIV→AUTH · VALID→AUTH · GAME→AUTH · GRUPOS→AUTH
  VALID→ATIV ("valida tarefa") · VALID→GAME ("concede XP") · VALID→GRUPOS ("envia foto ao feed")
  GAME→GRUPOS ("fornece dados de ranking") · CRON→GAME ("aplica punições") · CRON→GRUPOS ("reset semanal")
"""
import ast
from pathlib import Path

from app.core import config
from app.modules.gamificacao import regras
from app.modules.auth.models import Personagem

RAIZ = Path(__file__).resolve().parents[1] / "app"
PERMITIDO = {
    "auth": set(),
    "atividades": {"auth"},
    "grupos": {"auth"},
    "gamificacao": {"auth", "grupos"},
    "validacao": {"auth", "atividades", "gamificacao", "grupos"},
    "automacoes": {"gamificacao", "grupos"},
}


def _importados(arquivo: Path) -> set[str]:
    achados = set()
    for no in ast.walk(ast.parse(arquivo.read_text(encoding="utf-8"))):
        nomes = [no.module or ""] if isinstance(no, ast.ImportFrom) else [a.name for a in no.names] if isinstance(no, ast.Import) else []
        for nome in nomes:
            partes = nome.split(".")
            if partes[:2] == ["app", "modules"] and len(partes) > 2:
                achados.add(partes[2])
    return achados


def test_modulos_respeitam_as_setas_do_diagrama_de_componentes():
    violacoes = []
    for modulo, permitidos in PERMITIDO.items():
        for arq in (RAIZ / "modules" / modulo).glob("*.py"):
            for destino in _importados(arq) - {modulo}:
                if destino not in permitidos:
                    violacoes.append(f"{modulo} → {destino} ({arq.name})")
    assert not violacoes, "dependência fora do diagrama de componentes: " + "; ".join(violacoes)


def test_nao_ha_ciclos_entre_modulos():
    visitando, ok = set(), set()

    def dfs(n):
        assert n not in visitando, f"ciclo envolvendo {n}"
        if n in ok:
            return
        visitando.add(n)
        for d in PERMITIDO[n]:
            dfs(d)
        visitando.discard(n)
        ok.add(n)

    for m in PERMITIDO:
        dfs(m)


def test_apenas_o_gateway_combina_modulos():
    """app/core nunca depende de app/modules (só database.init_db importa os modelos, dentro de função)."""
    for arq in (RAIZ / "core").glob("*.py"):
        if arq.name == "database.py":
            continue
        assert not _importados(arq), f"core/{arq.name} importa módulos de negócio"


def test_valor_inicial_do_personagem_igual_a_regra():
    assert Personagem.xp_proximo_nivel.default.arg == regras.xp_proximo_nivel(1)


def test_limites_vindos_da_documentacao():
    assert config.settings.prova_tamanho_max_bytes == 10 * 1024 * 1024  # RNF06
