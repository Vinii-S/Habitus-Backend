"""Componente [Grupos / Guildas]: RF03 (gestão de grupos), RF07 (feed do Mural), DC: Grupo/MembroGrupo/PostagemMural/RankingGrupo."""
import secrets
from dataclasses import dataclass
from datetime import datetime, timedelta

from sqlalchemy import func, select
from sqlalchemy.orm import Session, joinedload

from app.core.erros import Conflito, NaoEncontrado, Proibido, RegraDeNegocio
from app.core.tempo import agora
from app.modules.auth.models import Personagem, Usuario
from app.modules.grupos.models import Grupo, MembroGrupo, PostagemMural, RankingGrupo

# Figma (Minha Guilda › "Progresso da guilda"): níveis 1…7 com XP 100/300/1.000/2.500/5.000/7.500/10.000.
# O DC só guarda Grupo.nivelGrupo; a TABELA de níveis vem apenas da tela.
NIVEIS_GUILDA = [(1, 100), (2, 300), (3, 1000), (4, 2500), (5, 5000), (6, 7500), (7, 10000)]
# Figma: "Sua contribuição 240 / 300 XP" — origem da meta (300) NÃO documentada.
META_CONTRIBUICAO_SEMANAL = 300.0
# Figma (Ranking): "Reseta em 5 dias" / "Ligas Semanais" ([REL] funcionalidade 9) → ciclo de 7 dias.
CICLO_RESET = timedelta(days=7)
PAPEIS_GESTORES = ("Líder", "Admin")  # DCU: ator "Líder/Admin do grupo"


@dataclass
class GrupoResumo:
    grupo: Grupo
    total_membros: int
    xp_total: float  # PROVISÓRIO: soma do XP acumulado dos membros (a fonte do "XP da guilda" não está documentada)
    xp_proximo_nivel: float | None


def _xp_para_nivel(nivel: int) -> float | None:
    return next((float(xp) for n, xp in NIVEIS_GUILDA if n == nivel), None)


def resumos(db: Session, grupos: list[Grupo]) -> list[GrupoResumo]:
    ids = [g.id for g in grupos]
    if not ids:
        return []
    linhas = db.execute(
        select(MembroGrupo.grupo_id, func.count(MembroGrupo.id), func.coalesce(func.sum(Personagem.xp_atual), 0.0))
        .join(Personagem, Personagem.usuario_id == MembroGrupo.usuario_id)
        .where(MembroGrupo.grupo_id.in_(ids))
        .group_by(MembroGrupo.grupo_id)
    ).all()
    por_grupo = {gid: (n, xp) for gid, n, xp in linhas}
    return [GrupoResumo(g, *por_grupo.get(g.id, (0, 0.0)), _xp_para_nivel(g.nivel_grupo + 1)) for g in grupos]


def vinculo_principal(db: Session, usuario: Usuario) -> MembroGrupo | None:
    """O DC permite vários vínculos (Usuario 1—0..* MembroGrupo), mas o Figma tem UMA "Minha Guilda":
    usa-se o vínculo mais antigo. Decisão provisória."""
    return db.scalar(select(MembroGrupo).where(MembroGrupo.usuario_id == usuario.id).order_by(MembroGrupo.id).options(joinedload(MembroGrupo.grupo)))


def grupos_principais(db: Session, usuario_ids: list[int]) -> dict[int, Grupo]:
    if not usuario_ids:
        return {}
    vinculos = db.scalars(select(MembroGrupo).where(MembroGrupo.usuario_id.in_(usuario_ids)).order_by(MembroGrupo.id).options(joinedload(MembroGrupo.grupo))).all()
    saida: dict[int, Grupo] = {}
    for v in vinculos:
        saida.setdefault(v.usuario_id, v.grupo)
    return saida


def _codigo_unico(db: Session) -> str:
    while True:
        codigo = secrets.token_hex(3).upper()
        if db.scalar(select(Grupo.id).where(Grupo.codigo_convite == codigo)) is None:
            return codigo


def gerar_codigo_convite(db: Session) -> str:  # DC: Grupo.gerarCodigoConvite()
    return _codigo_unico(db)


def criar_grupo(db: Session, usuario: Usuario, nome: str, descricao: str, categorias: list[str], icone: str | None) -> Grupo:  # DC: criarGrupo()
    grupo = Grupo(nome=nome.strip(), descricao=descricao.strip(), categorias=",".join(categorias), icone=icone, codigo_convite=_codigo_unico(db))
    grupo.membros.append(MembroGrupo(usuario_id=usuario.id, papel="Líder"))
    grupo.ranking = RankingGrupo()
    db.add(grupo)
    db.commit()
    return grupo


def entrar_por_codigo(db: Session, usuario: Usuario, codigo: str) -> Grupo:
    """[REL §10]: "sistema para entrar via código ou convite simples"."""
    grupo = db.scalar(select(Grupo).where(Grupo.codigo_convite == codigo.strip().upper()))
    if grupo is None:
        raise NaoEncontrado("Código de convite inválido.")
    if db.scalar(select(MembroGrupo.id).where(MembroGrupo.grupo_id == grupo.id, MembroGrupo.usuario_id == usuario.id)):
        raise Conflito("Você já participa desta guilda.")
    db.add(MembroGrupo(grupo_id=grupo.id, usuario_id=usuario.id, papel="Membro"))
    db.commit()
    return grupo


def exigir_membro(db: Session, usuario: Usuario, grupo_id: int) -> MembroGrupo:
    m = db.scalar(select(MembroGrupo).where(MembroGrupo.grupo_id == grupo_id, MembroGrupo.usuario_id == usuario.id))
    if m is None:
        raise Proibido("Você não participa desta guilda.")
    return m


def membros_do_grupo(db: Session, grupo_id: int) -> list[MembroGrupo]:
    return list(db.scalars(select(MembroGrupo).where(MembroGrupo.grupo_id == grupo_id).order_by(MembroGrupo.pontuacao_semanal.desc(), MembroGrupo.id).options(joinedload(MembroGrupo.usuario))))


def minha_guilda(db: Session, usuario: Usuario) -> tuple[GrupoResumo, list[MembroGrupo], MembroGrupo]:
    vinculo = vinculo_principal(db, usuario)
    if vinculo is None:
        raise NaoEncontrado("Você ainda não participa de uma guilda.")
    return resumos(db, [vinculo.grupo])[0], membros_do_grupo(db, vinculo.grupo_id), vinculo


def explorar(db: Session, categoria: str | None, busca: str | None, ordenar_por: str | None) -> list[GrupoResumo]:
    q = select(Grupo)
    if categoria:
        q = q.where(func.instr("," + Grupo.categorias + ",", f",{categoria},") > 0)
    if busca:
        like = f"%{busca.strip().lower()}%"
        q = q.where(func.lower(Grupo.nome).like(like) | func.lower(Grupo.descricao).like(like))
    itens = resumos(db, list(db.scalars(q)))
    chave = {"nivel": lambda r: r.grupo.nivel_grupo, "xp": lambda r: r.xp_total}.get(ordenar_por or "", lambda r: r.total_membros)
    return sorted(itens, key=chave, reverse=True)  # padrão: "Mais membros" (Figma)


# ---------------- Mural (RF07) ----------------
def listar_mural(db: Session, usuario: Usuario, grupo_id: int, limite: int = 50) -> list[PostagemMural]:
    exigir_membro(db, usuario, grupo_id)
    return list(db.scalars(select(PostagemMural).where(PostagemMural.grupo_id == grupo_id).order_by(PostagemMural.data_postagem.desc(), PostagemMural.id.desc()).limit(limite).options(joinedload(PostagemMural.autor))))


def publicar(db: Session, usuario: Usuario, grupo_id: int, texto: str, tipo_evento: str = "mensagem") -> PostagemMural:  # DC: publicarNoMural()
    exigir_membro(db, usuario, grupo_id)
    p = PostagemMural(grupo_id=grupo_id, autor_id=usuario.id, conteudo_texto=texto.strip(), tipo_evento=tipo_evento)
    db.add(p)
    db.flush()
    p.autor = usuario
    return p


def publicar_evento(db: Session, usuario: Usuario, texto: str, tipo_evento: str) -> PostagemMural | None:
    """Usado pela Validação (UC003: "publica o registro no feed da guilda"). Sem guilda → não publica."""
    v = vinculo_principal(db, usuario)
    return publicar(db, usuario, v.grupo_id, texto, tipo_evento) if v else None


# ---------------- Pontuação / ranking ----------------
def registrar_pontuacao(db: Session, usuario: Usuario, xp: float) -> None:
    for m in db.scalars(select(MembroGrupo).where(MembroGrupo.usuario_id == usuario.id)):
        m.pontuacao_semanal += xp


def reiniciar_em_dias(db: Session, grupo_id: int, ref: datetime | None = None) -> int:
    r = db.scalar(select(RankingGrupo).where(RankingGrupo.grupo_id == grupo_id))
    if r is None:
        return 0
    restante = (r.data_ultimo_reset + CICLO_RESET) - (ref or agora())
    return max(0, restante.days)


def processar_reset_semanal(db: Session, ref: datetime | None = None) -> int:  # DC: processarResetGrupo()/atualizarLigasSemanais()
    """Zera a pontuação semanal dos grupos cujo ciclo (7 dias) venceu. Retorna quantos grupos foram reiniciados.
    A regra de promoção/rebaixamento de ligas NÃO está documentada, então `liga_atual` não é alterada."""
    ref = ref or agora()
    reiniciados = 0
    for r in db.scalars(select(RankingGrupo)):
        if ref - r.data_ultimo_reset >= CICLO_RESET:
            for m in db.scalars(select(MembroGrupo).where(MembroGrupo.grupo_id == r.grupo_id)):
                m.pontuacao_semanal = 0.0
            r.data_ultimo_reset = ref
            reiniciados += 1
    db.commit()
    return reiniciados


# ---------------- Gestão (Líder/Admin) ----------------
def _exigir_gestor(db: Session, usuario: Usuario, grupo_id: int) -> None:
    if exigir_membro(db, usuario, grupo_id).papel not in PAPEIS_GESTORES:
        raise Proibido("Apenas o líder ou administradores da guilda podem fazer isso.")


def promover_admin(db: Session, usuario: Usuario, grupo_id: int, alvo_usuario_id: int) -> MembroGrupo:  # DC: promoverAdmin()
    _exigir_gestor(db, usuario, grupo_id)
    alvo = exigir_membro_por_id(db, grupo_id, alvo_usuario_id)
    if alvo.papel == "Líder":
        raise RegraDeNegocio("O líder já possui todas as permissões.")
    alvo.papel = "Admin"
    db.commit()
    return alvo


def remover_membro(db: Session, usuario: Usuario, grupo_id: int, alvo_usuario_id: int) -> None:  # DC: removerMembro()
    _exigir_gestor(db, usuario, grupo_id)
    alvo = exigir_membro_por_id(db, grupo_id, alvo_usuario_id)
    if alvo.papel == "Líder":
        raise RegraDeNegocio("O líder não pode ser removido.")
    db.delete(alvo)
    db.commit()


def exigir_membro_por_id(db: Session, grupo_id: int, usuario_id: int) -> MembroGrupo:
    m = db.scalar(select(MembroGrupo).where(MembroGrupo.grupo_id == grupo_id, MembroGrupo.usuario_id == usuario_id))
    if m is None:
        raise NaoEncontrado("Membro não encontrado nesta guilda.")
    return m
