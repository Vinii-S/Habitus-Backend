"""Rotas do componente [Autenticacao e Gestao de Usuarios]. Caminhos = src/api/endpoints.ts do frontend."""
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import criar_token
from app.modules.auth import service
from app.modules.auth.deps import usuario_atual
from app.modules.auth.models import Usuario
from app.modules.auth.schemas import (
    AmigoIn,
    CadastroIn,
    LoginIn,
    PerfilResumoOut,
    PerfilUpdateIn,
    SessaoOut,
    UsuarioOut,
)

router = APIRouter(tags=["auth e usuários"])


@router.post("/auth/cadastro", response_model=SessaoOut, status_code=201)  # RF01 / "Criar Conta"
def cadastro(dados: CadastroIn, db: Session = Depends(get_db)):
    u = service.criar_conta(db, dados)
    return SessaoOut(token=criar_token(u.id), usuario=UsuarioOut.model_validate(u))


@router.post("/auth/login", response_model=SessaoOut)  # RF01 / "Fazer Login"
def login(dados: LoginIn, db: Session = Depends(get_db)):
    u = service.autenticar(db, dados.email, dados.senha)
    return SessaoOut(token=criar_token(u.id), usuario=UsuarioOut.model_validate(u))


@router.get("/perfil/resumo", response_model=PerfilResumoOut)  # Sidebar do Figma
def perfil_resumo(u: Usuario = Depends(usuario_atual)):
    return PerfilResumoOut(usuario=UsuarioOut.model_validate(u), personagem=u.personagem)


@router.get("/perfil", response_model=UsuarioOut)  # RF04
def obter_perfil(u: Usuario = Depends(usuario_atual)):
    return u


@router.patch("/perfil", response_model=UsuarioOut)  # RF04
def atualizar_perfil(dados: PerfilUpdateIn, u: Usuario = Depends(usuario_atual), db: Session = Depends(get_db)):
    return service.atualizar_perfil(db, u, dados)


@router.post("/amigos", response_model=UsuarioOut, status_code=201)  # [DCU] "Adicionar Amigos" (sem tela no Figma)
def adicionar_amigo(dados: AmigoIn, u: Usuario = Depends(usuario_atual), db: Session = Depends(get_db)):
    return service.adicionar_amigo(db, u, dados.nome_exibicao)


@router.get("/amigos", response_model=list[UsuarioOut])
def listar_amigos(u: Usuario = Depends(usuario_atual), db: Session = Depends(get_db)):
    return service.listar_amigos(db, u)
