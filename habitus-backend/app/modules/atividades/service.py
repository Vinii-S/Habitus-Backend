"""UC001 — Cadastrar Atividade; DC: Atividade.cadastrarAtividade() / inativarAtividade()."""
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.erros import Conflito, NaoEncontrado
from app.modules.atividades.models import Atividade
from app.modules.atividades.schemas import NovaAtividadeIn
from app.modules.auth.models import Usuario


def listar(db: Session, usuario: Usuario) -> list[Atividade]:
    return list(db.scalars(select(Atividade).where(Atividade.usuario_id == usuario.id, Atividade.status_ativa.is_(True)).order_by(Atividade.id)))


def contar_ativas(db: Session, usuario: Usuario) -> int:
    return db.scalar(select(func.count()).select_from(Atividade).where(Atividade.usuario_id == usuario.id, Atividade.status_ativa.is_(True))) or 0


def criar(db: Session, usuario: Usuario, dados: NovaAtividadeIn) -> Atividade:
    # UC001 fluxo alternativo 6a: limite de atividades ativas atingido → operação cancelada.
    if contar_ativas(db, usuario) >= settings.limite_atividades_ativas:
        raise Conflito("Limite de atividades ativas atingido. Para criar uma nova meta, conclua, arquive ou exclua um hábito antigo.")
    atividade = Atividade(
        usuario_id=usuario.id,
        nome=dados.nome.strip(),
        descricao=(dados.descricao or "").strip(),
        categoria=dados.categoria,
        frequencia=dados.frequencia,
        meta=dados.meta,
        duracao_estimada_min=dados.duracao_estimada_min,
        lembrete_ativo=bool(dados.lembrete and dados.lembrete.ativo),
        lembrete_horario=dados.lembrete.horario if dados.lembrete else None,
        data_fim=dados.data_fim,
    )
    db.add(atividade)
    db.commit()
    return atividade


def obter(db: Session, usuario: Usuario, atividade_id: int) -> Atividade:
    a = db.get(Atividade, atividade_id)
    # 404 também quando a atividade é de outra pessoa (não revela que existe).
    if a is None or a.usuario_id != usuario.id or not a.status_ativa:
        raise NaoEncontrado("Atividade não encontrada.")
    return a


def inativar(db: Session, usuario: Usuario, atividade_id: int) -> None:
    """O botão "Excluir tarefa" do Figma vira inativação (DC: inativarAtividade), preservando o histórico de check-ins."""
    obter(db, usuario, atividade_id).status_ativa = False
    db.commit()
