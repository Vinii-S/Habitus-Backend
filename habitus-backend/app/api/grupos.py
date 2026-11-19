"""Rotas de [Grupos / Guildas] (RF03, RF07)."""
from datetime import timedelta

from fastapi import APIRouter, Depends, Query, Response
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.tempo import agora, inicio_da_semana
from datetime import datetime

from app.modules.auth.deps import usuario_atual
from app.modules.auth.models import Usuario
from app.modules.grupos import service
from app.modules.grupos.models import MembroGrupo, PostagemMural
from app.modules.grupos.schemas import (
    ContribuicaoOut,
    CriarGrupoIn,
    DetalheGuildaOut,
    EntrarGrupoIn,
    EstatisticasGuildaOut,
    GrupoOut,
    MembroOut,
    NivelGuildaOut,
    PostagemOut,
    PublicarIn,
    UsuarioResumoOut,
)
from app.modules.validacao import service as validacao

router = APIRouter(tags=["grupos / guildas"])


def _resumo_usuario(u: Usuario) -> UsuarioResumoOut:
    return UsuarioResumoOut(id=u.id, nome_exibicao=u.nome_exibicao, foto_perfil=u.foto_perfil)


def grupo_out(r: service.GrupoResumo, com_codigo: bool) -> GrupoOut:
    g = r.grupo
    return GrupoOut(
        id=g.id, nome=g.nome, descricao=g.descricao, codigo_convite=g.codigo_convite if com_codigo else None,
        nivel_grupo=g.nivel_grupo, categorias=[c for c in g.categorias.split(",") if c], total_membros=r.total_membros,
        xp_total=r.xp_total, xp_proximo_nivel=r.xp_proximo_nivel, icone=g.icone or "escudo",
    )


def membro_out(m: MembroGrupo) -> MembroOut:
    return MembroOut(id=m.id, papel=m.papel, data_entrada=m.data_entrada, pontuacao_semanal=m.pontuacao_semanal, usuario=_resumo_usuario(m.usuario))


def postagem_out(p: PostagemMural) -> PostagemOut:
    return PostagemOut(id=p.id, conteudo_texto=p.conteudo_texto, data_postagem=p.data_postagem, tipo_evento=p.tipo_evento, autor=_resumo_usuario(p.autor))


@router.get("/grupos/minha", response_model=DetalheGuildaOut)  # tela "Minha Guilda"
def minha(u: Usuario = Depends(usuario_atual), db: Session = Depends(get_db)):
    resumo, membros, meu = service.minha_guilda(db, u)
    ids = [m.usuario_id for m in membros]
    # Estatística que depende de check-ins (módulo VALID) é combinada aqui, no gateway.
    semana = validacao.contar_checkins(db, ids, datetime.combine(inicio_da_semana(agora().date()), datetime.min.time()))
    return DetalheGuildaOut(
        grupo=grupo_out(resumo, com_codigo=True),
        membros=[membro_out(m) for m in membros],
        minha_contribuicao=ContribuicaoOut(xp=meu.pontuacao_semanal, meta=service.META_CONTRIBUICAO_SEMANAL),
        niveis=[NivelGuildaOut(nivel=n, xp_necessario=xp) for n, xp in service.NIVEIS_GUILDA],
        estatisticas=EstatisticasGuildaOut(
            tarefas_concluidas_semana=sum(semana.values()),
            dias_sequencia=0,  # origem do "dias de sequência da guilda" não documentada
            membros_ativos_semana=sum(1 for m in membros if m.pontuacao_semanal > 0),
            xp_total=resumo.xp_total,
        ),
    )


@router.get("/grupos", response_model=list[GrupoOut])  # tela "Explorar Guildas"
def explorar(
    categoria: str | None = Query(default=None),
    busca: str | None = Query(default=None),
    ordenar_por: str | None = Query(default=None, alias="ordenarPor"),
    _: Usuario = Depends(usuario_atual),
    db: Session = Depends(get_db),
):
    return [grupo_out(r, com_codigo=False) for r in service.explorar(db, categoria, busca, ordenar_por)]  # código de convite NÃO é público


@router.post("/grupos", response_model=GrupoOut, status_code=201)  # [DCU] "Criar grupo"
def criar(dados: CriarGrupoIn, u: Usuario = Depends(usuario_atual), db: Session = Depends(get_db)):
    g = service.criar_grupo(db, u, dados.nome, dados.descricao, list(dados.categorias), dados.icone)
    return grupo_out(service.resumos(db, [g])[0], com_codigo=True)


@router.post("/grupos/entrar", response_model=GrupoOut)  # [REL §10] entrar via código/convite
def entrar(dados: EntrarGrupoIn, u: Usuario = Depends(usuario_atual), db: Session = Depends(get_db)):
    g = service.entrar_por_codigo(db, u, dados.codigo_convite)
    return grupo_out(service.resumos(db, [g])[0], com_codigo=True)


@router.get("/grupos/{grupo_id}/mural", response_model=list[PostagemOut])  # RF07
def mural(grupo_id: int, u: Usuario = Depends(usuario_atual), db: Session = Depends(get_db)):
    return [postagem_out(p) for p in service.listar_mural(db, u, grupo_id)]


@router.post("/grupos/{grupo_id}/mural", response_model=PostagemOut, status_code=201)  # DC: publicarNoMural()
def publicar(grupo_id: int, dados: PublicarIn, u: Usuario = Depends(usuario_atual), db: Session = Depends(get_db)):
    p = service.publicar(db, u, grupo_id, dados.conteudo_texto)
    db.commit()
    return postagem_out(p)


@router.post("/grupos/{grupo_id}/membros/{usuario_id}/promover", response_model=MembroOut)  # DC: promoverAdmin()
def promover(grupo_id: int, usuario_id: int, u: Usuario = Depends(usuario_atual), db: Session = Depends(get_db)):
    return membro_out(service.promover_admin(db, u, grupo_id, usuario_id))


@router.delete("/grupos/{grupo_id}/membros/{usuario_id}", status_code=204)  # DC: removerMembro()
def remover(grupo_id: int, usuario_id: int, u: Usuario = Depends(usuario_atual), db: Session = Depends(get_db)):
    service.remover_membro(db, u, grupo_id, usuario_id)
    return Response(status_code=204)
