"""Componente [Validacao e Prova de Conclusao]: UC003 (Anexar Comprovante), RF05 (check-in), RF06 (prova), RNF06.

Setas do diagrama de componentes implementadas aqui:
  VALID → ATIV  "valida tarefa"        (a atividade precisa existir/ser do usuário — feito no gateway com atividades.service.obter)
  VALID → GAME  "concede XP"           gamificacao.conceder_xp
  VALID → GRUPOS "envia foto ao feed"  grupos.publicar_evento
  VALID → STORAGE "upload de fotos"    ArmazenamentoMidia
  VALID → DB    "registros de check-in"
"""
from dataclasses import dataclass
from datetime import date, datetime, timedelta

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.erros import Conflito, RegraDeNegocio
from app.core.storage import ArmazenamentoMidia
from app.core.tempo import DIAS_ABREV, agora, inicio_da_semana
from app.modules.atividades.models import Atividade
from app.modules.auth.models import Usuario
from app.modules.gamificacao import service as gamificacao
from app.modules.grupos import service as grupos
from app.modules.grupos.models import PostagemMural
from app.modules.validacao.models import CheckIn, ProvaDeConclusao

EXTENSOES = {"image/jpeg": "jpg", "image/png": "png"}
ASSINATURAS = {"jpg": b"\xff\xd8\xff", "png": b"\x89PNG\r\n\x1a\n"}
# Figma (Tarefas › "Meta semanal"): "Complete pelo menos 7 tarefas essa semana" — origem da meta (7) não documentada.
META_SEMANAL_TAREFAS = 7


def validar_arquivo(conteudo: bytes, content_type: str | None) -> str:  # DC: ProvaDeConclusao.validarTamanhoETipo()
    """RNF06 (≤ 10 MB, só .jpg/.png) e UC003 fluxo 4a. Além do Content-Type informado pelo cliente (que é
    falsificável), confere os primeiros bytes do arquivo. [REL §10]: NÃO há reconhecimento de imagem."""
    if len(conteudo) > settings.prova_tamanho_max_bytes:
        raise RegraDeNegocio(f"O arquivo ultrapassa o limite de {settings.prova_tamanho_max_bytes // (1024 * 1024)} MB.")
    ext = EXTENSOES.get((content_type or "").lower())
    if ext is None or not conteudo.startswith(ASSINATURAS[ext]):
        raise RegraDeNegocio("Arquivo não suportado. Envie uma imagem JPG ou PNG.")
    return ext


@dataclass
class ResultadoCheckIn:
    checkin: CheckIn
    xp_ganho: float
    subiu_de_nivel: bool
    novo_nivel: int | None
    postagem: PostagemMural | None


def registrar_checkin(
    db: Session,
    usuario: Usuario,
    atividade: Atividade,
    conteudo: bytes | None,
    content_type: str | None,
    storage: ArmazenamentoMidia,
) -> ResultadoCheckIn:  # DC: CheckIn.registrarConclusao() + processarXPEvolucao()
    agora_ = agora()
    ultimo = db.scalar(select(CheckIn).where(CheckIn.atividade_id == atividade.id).order_by(CheckIn.data_hora.desc()))
    if ultimo and ultimo.data_hora.date() == agora_.date():
        # PROVISÓRIO: um check-in por atividade por dia (UTC). A documentação não define a regra para
        # frequências semanal/mensal/personalizada nem o fuso horário do usuário.
        raise Conflito("Check-in já realizado hoje para esta atividade.")
    streak = ultimo.sequencia_streak + 1 if ultimo and ultimo.data_hora.date() == agora_.date() - timedelta(days=1) else 1

    ext = validar_arquivo(conteudo, content_type) if conteudo is not None else None  # falha → 422 antes de gravar qualquer coisa
    url = storage.salvar(conteudo, ext) if conteudo is not None and ext else None
    try:
        xp = gamificacao.calcular_pontuacao_xp(atividade.xp_recompensa)
        checkin = CheckIn(atividade_id=atividade.id, data_hora=agora_, xp_ganho=xp, sequencia_streak=streak, minutos=atividade.duracao_estimada_min)
        if url and conteudo is not None:
            checkin.prova = ProvaDeConclusao(url_imagem=url, tamanho_arquivo=float(len(conteudo)), tipo_arquivo=content_type or "")
        db.add(checkin)
        db.flush()
        subiu, novo_nivel = gamificacao.conceder_xp(db, usuario, xp)
        postagem = grupos.publicar_evento(db, usuario, f"Concluí “{atividade.nome}”! +{xp:g} XP", "checkin")  # UC003 pós-condição
        db.commit()
    except Exception:
        db.rollback()
        if url:
            storage.remover(url)  # não deixa foto órfã se o banco falhar
        raise
    return ResultadoCheckIn(checkin, xp, subiu, novo_nivel, postagem)


# ---------------- Leituras usadas nas telas de tarefas ----------------
def _inicio_periodo(a: Atividade, hoje: date) -> date:
    if a.frequencia == "Semanal":
        return inicio_da_semana(hoje)
    if a.frequencia == "Mensal":
        return hoje.replace(day=1)
    return hoje  # Diária e Personalizada (esta última: regra não documentada)


def status_atividades(db: Session, atividades: list[Atividade], ref: datetime | None = None) -> dict[int, tuple[str, int, bool]]:
    """id → (status, progresso%, hoje). ⚠️ REGRA PROVISÓRIA: o Figma mostra "Em andamento 50%/25%", "Atrasada" e
    uma divisão "hoje / outras", mas nenhum documento diz como são calculados. Aqui: concluída (100%) se há
    check-in no período da frequência; senão "Não iniciada" (0%). "Em andamento" e "Atrasada" não são produzidos."""
    ref = ref or agora()
    ids = [a.id for a in atividades]
    ultimos = dict(db.execute(select(CheckIn.atividade_id, func.max(CheckIn.data_hora)).where(CheckIn.atividade_id.in_(ids)).group_by(CheckIn.atividade_id)).all()) if ids else {}
    saida = {}
    for a in atividades:
        ultimo = ultimos.get(a.id)
        feita = ultimo is not None and ultimo.date() >= _inicio_periodo(a, ref.date())
        saida[a.id] = ("Concluída", 100, a.frequencia == "Diária") if feita else ("Não iniciada", 0, a.frequencia == "Diária")
    return saida


def historico(db: Session, atividade: Atividade, limite: int = 5) -> list[CheckIn]:
    return list(db.scalars(select(CheckIn).where(CheckIn.atividade_id == atividade.id).order_by(CheckIn.data_hora.desc()).limit(limite)))


def semana(db: Session, atividade: Atividade, ref: datetime | None = None) -> list[dict]:
    ref = ref or agora()
    segunda = inicio_da_semana(ref.date())
    dias_feitos = {c.date() for c in db.scalars(select(CheckIn.data_hora).where(CheckIn.atividade_id == atividade.id, CheckIn.data_hora >= datetime.combine(segunda, datetime.min.time())))}
    return [
        {"rotulo": DIAS_ABREV[i], "data": f"{(segunda + timedelta(days=i)).day:02d}/{(segunda + timedelta(days=i)).month:02d}", "feito": (segunda + timedelta(days=i)) in dias_feitos}
        for i in range(7)
    ]


def estatisticas(db: Session, atividade: Atividade, ref: datetime | None = None) -> dict:
    ref = ref or agora()
    datas = [c.date() for c in db.scalars(select(CheckIn.data_hora).where(CheckIn.atividade_id == atividade.id))]
    ultimo = db.scalar(select(CheckIn).where(CheckIn.atividade_id == atividade.id).order_by(CheckIn.data_hora.desc()))
    ultimos_7 = {d for d in datas if d > ref.date() - timedelta(days=7)}
    atual = ultimo.sequencia_streak if ultimo and ultimo.data_hora.date() >= ref.date() - timedelta(days=1) else 0
    melhor = db.scalar(select(func.max(CheckIn.sequencia_streak)).where(CheckIn.atividade_id == atividade.id)) or 0
    return {"conclusoes_totais": len(datas), "taxa_conclusao": round(len(ultimos_7) / 7 * 100), "sequencia_atual": atual, "melhor_sequencia": melhor}


def resumo_semana_usuario(db: Session, atividades: list[Atividade], ref: datetime | None = None) -> dict:
    """Bloco "Resumo da semana" e "Meta semanal" (Figma, Minhas Tarefas). Provisório: concluídas = check-ins da
    semana; "em andamento" não é calculável (regra não documentada)."""
    ref = ref or agora()
    segunda = inicio_da_semana(ref.date())
    inicio = datetime.combine(segunda, datetime.min.time())
    ids = [a.id for a in atividades]
    linhas = db.execute(select(CheckIn.atividade_id, CheckIn.xp_ganho).where(CheckIn.atividade_id.in_(ids), CheckIn.data_hora >= inicio)).all() if ids else []
    com_checkin = {aid for aid, _ in linhas}
    fim = segunda + timedelta(days=6)
    abrev = ["jan", "fev", "mar", "abr", "mai", "jun", "jul", "ago", "set", "out", "nov", "dez"]
    return {
        "intervalo": f"{segunda.day} - {fim.day} {abrev[fim.month - 1]}",
        "xp": sum(x for _, x in linhas),
        "concluidas": len(linhas),
        "em_andamento": 0,
        "nao_iniciadas": len([a for a in atividades if a.id not in com_checkin]),
        "meta": {"descricao": f"Complete pelo menos {META_SEMANAL_TAREFAS} tarefas essa semana.", "feitas": len(linhas), "total": META_SEMANAL_TAREFAS},
    }


# ---------------- Agregados para ranking e guildas (consumidos pelo gateway) ----------------
def contar_checkins(db: Session, usuario_ids: list[int], desde: datetime) -> dict[int, int]:
    if not usuario_ids:
        return {}
    q = (
        select(Atividade.usuario_id, func.count(CheckIn.id))
        .join(CheckIn, CheckIn.atividade_id == Atividade.id)
        .where(Atividade.usuario_id.in_(usuario_ids), CheckIn.data_hora >= desde)
        .group_by(Atividade.usuario_id)
    )
    return dict(db.execute(q).all())


def sequencias_atuais(db: Session, usuario_ids: list[int], ref: datetime | None = None) -> dict[int, int]:
    """Maior sequência em andamento do usuário (check-in ontem ou hoje). Provisório."""
    ref = ref or agora()
    if not usuario_ids:
        return {}
    desde = datetime.combine(ref.date() - timedelta(days=1), datetime.min.time())
    q = (
        select(Atividade.usuario_id, func.max(CheckIn.sequencia_streak))
        .join(CheckIn, CheckIn.atividade_id == Atividade.id)
        .where(Atividade.usuario_id.in_(usuario_ids), CheckIn.data_hora >= desde)
        .group_by(Atividade.usuario_id)
    )
    return dict(db.execute(q).all())
