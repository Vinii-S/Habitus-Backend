"""Carga inicial do catálogo da Loja.  Rodar:  python -m app.seed

Os 8 itens vêm EXATAMENTE da tela "Loja de Prêmios" do Figma (título, descrição, preço). A categoria de cada
item (Personalização/Cupons/…) NÃO aparece nas telas — só os filtros —, então o mapeamento abaixo é suposição.
Não cria usuários: eles se cadastram pela API.
"""
from sqlalchemy import select

from app.core.database import SessionLocal, init_db
from app.modules.gamificacao.models import Recompensa

CATALOGO = [
    ("Avatar exclusivo", "Desbloqueie um avatar especial para o seu perfil Habitus.", 500, "Personalização", "avatar"),
    ("Tema roxo premium", "Deixe sua experiência ainda mais incrível com o tema roxo.", 3000, "Personalização", "tema"),
    ("Moldura de perfil", "Destaque seu perfil com uma moldura espacial.", 800, "Personalização", "moldura"),
    ("Cupom de 10%", "Ganhe 10% de desconto em parceiros.", 1000, "Cupons", "cupom"),
    ("Dia bônus", "Ganhe 1 dia extra de streak de tarefas.", 1200, "Benefícios", "calendario"),
    ("Badge especial da guilda", "Mostre seu apoio à sua guilda com um badge exclusivo.", 2500, "Exclusivos", "badge"),
    ("Plano de fundo raro", "Desbloqueie um plano de fundo exclusivo para seu perfil.", 4000, "Exclusivos", "fundo"),
    ("Caixa surpresa", "Uma recompensa misteriosa com itens exclusivos.", 5000, "Exclusivos", "caixa"),
]


def semear() -> int:
    init_db()
    novos = 0
    with SessionLocal() as db:
        existentes = set(db.scalars(select(Recompensa.titulo)))
        for titulo, desc, preco, cat, icone in CATALOGO:
            if titulo not in existentes:
                db.add(Recompensa(titulo=titulo, descricao=desc, preco_moedas=preco, categoria=cat, tipo=cat, icone=icone))
                novos += 1
        db.commit()
    return novos


if __name__ == "__main__":
    print(f"{semear()} recompensa(s) criada(s).")
