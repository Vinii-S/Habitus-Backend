"""Rotas de [Gestao de Atividades] e [Validacao e Prova de Conclusao] (o check-in mora em VALID, mas a URL
fica sob /atividades/{id}/checkins, como o frontend espera)."""
from fastapi import APIRouter, Depends, File, Response, UploadFile
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.database import get_db
from app.core.erros import RegraDeNegocio
from app.core.storage import ArmazenamentoMidia, get_storage
from app.core.tempo import agora
from app.modules.atividades import service as atividades
from app.modules.atividades.models import Atividade
from app.modules.atividades.schemas import AtividadeOut, CriadaOut, LembreteIO, NovaAtividadeIn, PainelTarefasOut
from app.modules.auth.deps import usuario_atual
from app.modules.auth.models import Usuario
from app.modules.validacao import service as validacao
from app.modules.validacao.schemas import CheckInOut, DetalheAtividadeOut, ResultadoCheckInOut

router = APIRouter(tags=["atividades e check-in"])


def _out(a: Atividade, status: tuple[str, int, bool]) -> AtividadeOut:
    return AtividadeOut(
        id=a.id, nome=a.nome, descricao=a.descricao, frequencia=a.frequencia, atributo_rpg=a.atributo_rpg,
        dificuldade=a.dificuldade, xp_recompensa=a.xp_recompensa, status_ativa=a.status_ativa, data_fim=a.data_fim,
        categoria=a.categoria, meta=a.meta, duracao_estimada_min=a.duracao_estimada_min,
        lembrete=LembreteIO(ativo=a.lembrete_ativo, horario=a.lembrete_horario) if a.lembrete_horario else None,
        status=status[0], progresso=status[1], hoje=status[2],
    )


@router.get("/atividades", response_model=PainelTarefasOut)  # RF05 — tela "Minhas Tarefas"
def painel(u: Usuario = Depends(usuario_atual), db: Session = Depends(get_db)):
    lista = atividades.listar(db, u)
    estados = validacao.status_atividades(db, lista)
    resumo = validacao.resumo_semana_usuario(db, lista)
    return PainelTarefasOut(
        atividades=[_out(a, estados[a.id]) for a in lista],
        resumo_semana={k: resumo[k] for k in ("intervalo", "xp", "concluidas", "em_andamento", "nao_iniciadas")},
        meta_semanal=resumo["meta"],
    )


@router.post("/atividades", response_model=CriadaOut, status_code=201)  # UC001
def criar(dados: NovaAtividadeIn, u: Usuario = Depends(usuario_atual), db: Session = Depends(get_db)):
    a = atividades.criar(db, u, dados)
    return CriadaOut(id=a.id, criada_em=a.criada_em)


@router.get("/atividades/{atividade_id}", response_model=DetalheAtividadeOut)  # tela "Detalhes da tarefa"
def detalhe(atividade_id: int, u: Usuario = Depends(usuario_atual), db: Session = Depends(get_db)):
    a = atividades.obter(db, u, atividade_id)
    ref = agora()
    semana = validacao.semana(db, a, ref)
    return DetalheAtividadeOut(
        atividade=_out(a, validacao.status_atividades(db, [a], ref)[a.id]),
        semana=semana,
        dias_feitos=sum(d["feito"] for d in semana),
        estatisticas=validacao.estatisticas(db, a, ref),
        historico=[CheckInOut.model_validate(c) for c in validacao.historico(db, a)],
    )


@router.delete("/atividades/{atividade_id}", status_code=204)  # botão "Excluir tarefa" → DC: inativarAtividade()
def excluir(atividade_id: int, u: Usuario = Depends(usuario_atual), db: Session = Depends(get_db)):
    atividades.inativar(db, u, atividade_id)
    return Response(status_code=204)


@router.post("/atividades/{atividade_id}/checkins", response_model=ResultadoCheckInOut, status_code=201)  # UC003 / RF05 / RF06
def checkin(
    atividade_id: int,
    prova: UploadFile | None = File(default=None),
    u: Usuario = Depends(usuario_atual),
    db: Session = Depends(get_db),
    storage: ArmazenamentoMidia = Depends(get_storage),
):
    """multipart/form-data com o campo opcional `prova` (imagem). A prova é opcional porque o DC define
    CheckIn—ProvaDeConclusao como 0..1. Esta função é síncrona de propósito: o FastAPI a executa em
    thread separada, então vários check-ins simultâneos não travam a API (RNF05)."""
    a = atividades.obter(db, u, atividade_id)  # VALID → ATIV "valida tarefa"
    conteudo = None
    if prova is not None and prova.filename:
        conteudo = prova.file.read(settings.prova_tamanho_max_bytes + 1)  # lê no máximo limite+1 (não carrega arquivos gigantes)
        if not conteudo:
            raise RegraDeNegocio("Arquivo vazio.")
    r = validacao.registrar_checkin(db, u, a, conteudo, prova.content_type if prova else None, storage)
    return ResultadoCheckInOut(
        check_in=CheckInOut.model_validate(r.checkin),
        xp_ganho=r.xp_ganho,
        subiu_de_nivel=r.subiu_de_nivel,
        novo_nivel=r.novo_nivel,
        postagem=_postagem(r.postagem),
    )


def _postagem(p):
    from app.api.grupos import postagem_out  # evita import circular entre routers

    return postagem_out(p) if p else None
