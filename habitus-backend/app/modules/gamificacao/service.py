"""Componente [Gamificacao e Evolucao]: RF02 (pontuação dinâmica), evolução do Personagem, Loja e dados de ranking.

DC: Personagem.ganharXP()/subirNivel()/gastarMoedas(), Atividade.calcularPontuacaoXP(), Recompensa.comprarNaLoja(),
RankingGrupo.calcularClassificacao(). Fórmulas: ver regras.py (todas provisórias).
"""
from dataclasses import dataclass

from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.erros import Conflito, NaoEncontrado, NaoImplementado, RegraDeNegocio
from app.modules.auth.models import Personagem, Usuario
from app.modules.gamificacao import regras
from app.modules.gamificacao.models import Recompensa, Resgate
from app.modules.grupos import service as grupos
from app.modules.grupos.models import Grupo, MembroGrupo


# ---------------- Evolução (RF02) ----------------
def calcular_pontuacao_xp(xp_base: float) -> float:
    """DC: Atividade.calcularPontuacaoXP(). Hoje = XP base da atividade. Multiplicadores de streak e de itens
    consumíveis aparecem em [EQP] (funcionalidades 2 e 9) mas NÃO têm fórmula documentada."""
    return float(xp_base)


def conceder_xp(db: Session, usuario: Usuario, xp: float) -> tuple[bool, int | None]:
    """Soma XP ao Personagem (ganharXP), sobe de nível quando passa do limite (subirNivel), credita moedas e
    atualiza a pontuação semanal nos grupos (alimenta o ranking). NÃO faz commit: quem chama controla a transação."""
    p: Personagem = usuario.personagem
    p.xp_atual += xp
    p.moedas_ouro += int(xp * regras.MOEDAS_POR_XP)
    niveis_antes = p.nivel
    while p.xp_atual >= p.xp_proximo_nivel:  # um check-in grande pode subir mais de um nível
        p.nivel += 1
        p.xp_proximo_nivel = regras.xp_proximo_nivel(p.nivel)
    grupos.registrar_pontuacao(db, usuario, xp)
    subiu = p.nivel > niveis_antes
    return subiu, (p.nivel if subiu else None)


def aplicar_penalidade_negligencia(db: Session) -> int:
    """Caso de uso do ator Sistema "Aplicar Penalidade de Negligência" ([DCU], DC: Grupo.aplicarPenalidadeNegligencia()).
    "Punição Compartilhada" é funcionalidade FUTURA ([REL §7]) e nenhum documento define o que é negligência, o
    prazo ou o tamanho da punição. Por isso não faz nada e devolve 0 — evita inventar uma regra que mexeria no XP."""
    return 0


# ---------------- Loja (funcionalidade 7) ----------------
def painel_loja(db: Session, usuario: Usuario) -> dict:
    p = usuario.personagem
    resgatadas = {r.recompensa_id: r for r in db.scalars(select(Resgate).where(Resgate.personagem_id == p.id))}
    itens = list(db.scalars(select(Recompensa).order_by(Recompensa.preco_moedas, Recompensa.id)))
    # "Próximo prêmio desejado" no Figma não tem origem documentada (lista de desejos?). Provisório: o item não
    # resgatado mais barato que ainda não dá para pagar.
    proximo = next((i for i in itens if i.id not in resgatadas and i.preco_moedas > p.moedas_ouro), None)
    recentes = sorted(resgatadas.values(), key=lambda r: r.data, reverse=True)[:3]
    nomes = {i.id: i.titulo for i in itens}
    return {
        "pontos_disponiveis": p.moedas_ouro,
        "resgates_realizados": len(resgatadas),
        "proximo_premio": {"titulo": proximo.titulo, "atual": p.moedas_ouro, "total": proximo.preco_moedas} if proximo else None,
        "itens": [dict(id=i.id, titulo=i.titulo, descricao=i.descricao, preco_moedas=i.preco_moedas, tipo=i.tipo, categoria=i.categoria, icone=i.icone, resgatada=i.id in resgatadas) for i in itens],
        "recentes": [(nomes.get(r.recompensa_id, "?"), r.data) for r in recentes],
    }


def resgatar(db: Session, usuario: Usuario, recompensa_id: int) -> None:  # DC: Recompensa.comprarNaLoja(personagem)
    recompensa = db.get(Recompensa, recompensa_id)
    if recompensa is None:
        raise NaoEncontrado("Recompensa não encontrada.")
    p = usuario.personagem
    if db.scalar(select(Resgate.id).where(Resgate.personagem_id == p.id, Resgate.recompensa_id == recompensa_id)):
        raise Conflito("Recompensa já resgatada.")
    if p.moedas_ouro < recompensa.preco_moedas:  # DC: gastarMoedas() → Boolean
        raise RegraDeNegocio("Pontos insuficientes.")
    p.moedas_ouro -= recompensa.preco_moedas
    db.add(Resgate(personagem_id=p.id, recompensa_id=recompensa_id))
    try:
        db.commit()
    except IntegrityError as exc:  # duas requisições simultâneas: a restrição UNIQUE impede cobrar duas vezes
        db.rollback()
        raise Conflito("Recompensa já resgatada.") from exc


# ---------------- Ranking (RF08) — dados; o gateway completa com tarefas/sequência ----------------
@dataclass
class LinhaBase:
    usuario: Usuario
    grupo: Grupo | None
    xp: float


def classificar(db: Session, periodo: str) -> list[LinhaBase]:  # DC: RankingGrupo.calcularClassificacao()
    if periodo == "mensal":
        # O DC/REL só descrevem reset SEMANAL (ligas semanais). Não há pontuação mensal armazenada.
        raise NaoImplementado("Ranking mensal não está definido na documentação (só há pontuação semanal e acumulada).")
    usuarios = list(db.scalars(select(Usuario)))
    principais = grupos.grupos_principais(db, [u.id for u in usuarios])
    if periodo == "semanal":
        somas = dict(db.execute(select(MembroGrupo.usuario_id, func.sum(MembroGrupo.pontuacao_semanal)).group_by(MembroGrupo.usuario_id)).all())
        xp_de = lambda u: float(somas.get(u.id, 0.0))  # noqa: E731
    else:  # geral
        xp_de = lambda u: float(u.personagem.xp_atual)  # noqa: E731
    linhas = [LinhaBase(u, principais.get(u.id), xp_de(u)) for u in usuarios]
    return sorted(linhas, key=lambda l: (-l.xp, l.usuario.id))


def ranking_por_guilda(db: Session) -> list[grupos.GrupoResumo]:
    return sorted(grupos.resumos(db, list(db.scalars(select(Grupo)))), key=lambda r: -r.xp_total)
