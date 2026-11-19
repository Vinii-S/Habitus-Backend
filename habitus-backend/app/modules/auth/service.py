"""Caso de uso "Criar Conta", "Fazer Login", RF01/RF04 e Usuario.adicionarAmigo()."""
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.erros import Conflito, NaoAutenticado, NaoEncontrado, RegraDeNegocio
from app.core.security import hash_senha, verificar_senha
from app.modules.auth.models import Amizade, Personagem, Usuario
from app.modules.auth.schemas import CadastroIn, PerfilUpdateIn


def _por_email(db: Session, email: str) -> Usuario | None:
    return db.scalar(select(Usuario).where(Usuario.email == email.strip().lower()))


def criar_conta(db: Session, dados: CadastroIn) -> Usuario:  # DC: Usuario.criarConta()
    if _por_email(db, dados.email):
        raise Conflito("E-mail já cadastrado.")
    if db.scalar(select(Usuario).where(func.lower(Usuario.nome_exibicao) == dados.nome_exibicao.strip().lower())):
        raise Conflito("Nome de usuário já em uso.")
    usuario = Usuario(
        nome_completo=dados.nome_completo.strip(),
        nome_exibicao=dados.nome_exibicao.strip(),
        email=dados.email.strip().lower(),
        data_nascimento=dados.data_nascimento,
        senha_hash=hash_senha(dados.senha),
        personagem=Personagem(),
    )
    db.add(usuario)
    db.commit()
    return usuario


def autenticar(db: Session, email: str, senha: str) -> Usuario:  # DC: Usuario.fazerLogin()
    usuario = _por_email(db, email)
    # Mesma mensagem para e-mail inexistente e senha errada (não revela quais e-mails existem).
    if usuario is None or not verificar_senha(senha, usuario.senha_hash):
        raise NaoAutenticado("E-mail ou senha inválidos.")
    return usuario


def atualizar_perfil(db: Session, usuario: Usuario, dados: PerfilUpdateIn) -> Usuario:  # DC: atualizarPerfil()
    campos = dados.model_dump(exclude_unset=True)
    if "nome_exibicao" in campos and campos["nome_exibicao"]:
        existe = db.scalar(
            select(Usuario).where(func.lower(Usuario.nome_exibicao) == campos["nome_exibicao"].strip().lower(), Usuario.id != usuario.id)
        )
        if existe:
            raise Conflito("Nome de usuário já em uso.")
    for chave, valor in campos.items():
        setattr(usuario, chave, valor)
    db.commit()
    return usuario


def adicionar_amigo(db: Session, usuario: Usuario, nome_exibicao: str) -> Usuario:  # DC: adicionarAmigo()
    amigo = db.scalar(select(Usuario).where(func.lower(Usuario.nome_exibicao) == nome_exibicao.strip().lower()))
    if amigo is None:
        raise NaoEncontrado("Usuário não encontrado.")  # UC002 fluxo 4a
    if amigo.id == usuario.id:
        raise RegraDeNegocio("Você não pode adicionar a si mesmo.")
    if db.get(Amizade, (usuario.id, amigo.id)) is None:
        db.add_all([Amizade(usuario_id=usuario.id, amigo_id=amigo.id), Amizade(usuario_id=amigo.id, amigo_id=usuario.id)])
        db.commit()
    return amigo


def listar_amigos(db: Session, usuario: Usuario) -> list[Usuario]:
    return list(db.scalars(select(Usuario).join(Amizade, Amizade.amigo_id == Usuario.id).where(Amizade.usuario_id == usuario.id)))
