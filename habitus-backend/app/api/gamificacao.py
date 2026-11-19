"""Rotas de [Gamificacao e Evolucao]: Loja (funcionalidade 7) e Ranking (RF08)."""
from datetime import datetime

from fastapi import APIRouter, Depends, Query, Response
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.tempo import agora, data_extenso_curto, inicio_da_semana
from app.modules.auth.deps import usuario_atual
from app.modules.auth.models import Usuario
from app.modules.gamificacao import service
from app.modules.gamificacao.schemas import (
    GuildaMiniOut,
    LinhaRankingOut,
    MinhaPosicaoOut,
    PainelLojaOut,
    PeriodoRanking,
    RankingGuildaOut,
    ResumoRankingOut,
)
from app.modules.grupos import service as grupos
from app.modules.grupos.schemas import UsuarioResumoOut
from app.modules.validacao import service as validacao

router = APIRouter(tags=["gamificação"])


@router.get("/loja", response_model=PainelLojaOut)
def loja(u: Usuario = Depends(usuario_atual), db: Session = Depends(get_db)):
    p = service.painel_loja(db, u)
    p["recentes"] = [{"titulo": t, "data": data_extenso_curto(d)} for t, d in p["recentes"]]
    return p


@router.post("/loja/{recompensa_id}/resgatar", status_code=204)  # DC: Recompensa.comprarNaLoja()
def resgatar(recompensa_id: int, u: Usuario = Depends(usuario_atual), db: Session = Depends(get_db)):
    service.resgatar(db, u, recompensa_id)
    return Response(status_code=204)


@router.get("/ranking", response_model=ResumoRankingOut)  # RF08 — tela "Ranking"
def ranking(periodo: PeriodoRanking = Query(default="semanal"), u: Usuario = Depends(usuario_atual), db: Session = Depends(get_db)):
    base = service.classificar(db, periodo)  # 'mensal' → 501 (não definido)
    ids = [b.usuario.id for b in base]
    ref = agora()
    inicio_semana = datetime.combine(inicio_da_semana(ref.date()), datetime.min.time())
    desde = datetime.min if periodo == "geral" else inicio_semana
    tarefas = validacao.contar_checkins(db, ids, desde)
    tarefas_semana = validacao.contar_checkins(db, ids, inicio_semana)
    sequencias = validacao.sequencias_atuais(db, ids, ref)

    linhas = [
        LinhaRankingOut(
            posicao=i + 1,
            usuario=UsuarioResumoOut(id=b.usuario.id, nome_exibicao=b.usuario.nome_exibicao, foto_perfil=b.usuario.foto_perfil),
            guilda=GuildaMiniOut(nome=b.grupo.nome if b.grupo else "—", icone=(b.grupo.icone if b.grupo else None) or "escudo"),
            xp=b.xp, tarefas=tarefas.get(b.usuario.id, 0), sequencia_dias=sequencias.get(b.usuario.id, 0),
        )
        for i, b in enumerate(base)
    ]
    eu = next(l for l in linhas if l.usuario.id == u.id)
    por_guilda = service.ranking_por_guilda(db)
    maior = max((r.xp_total for r in por_guilda), default=0.0)
    vinculo = grupos.vinculo_principal(db, u)
    return ResumoRankingOut(
        periodo=periodo,
        reinicia_em_dias=grupos.reiniciar_em_dias(db, vinculo.grupo_id, ref) if vinculo else 0,
        linhas=linhas,
        minha_posicao=MinhaPosicaoOut(
            posicao=eu.posicao, xp=eu.xp,
            delta_xp=0.0,  # comparação com a semana anterior exigiria histórico que o DC não guarda
            tarefas=eu.tarefas,
            meta_semanal_pct=min(100, round(tarefas_semana.get(u.id, 0) / validacao.META_SEMANAL_TAREFAS * 100)),
            sequencia_dias=eu.sequencia_dias,
        ),
        por_guilda=[RankingGuildaOut(posicao=i + 1, guilda=GuildaMiniOut(nome=r.grupo.nome, icone=r.grupo.icone or "escudo"), xp=r.xp_total, max_xp=maior) for i, r in enumerate(por_guilda)],
        conquistas_do_ranking=[],  # entidade Conquista não existe no DC
    )
