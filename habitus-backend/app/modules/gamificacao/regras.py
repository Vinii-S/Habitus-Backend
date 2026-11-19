"""Regras de gamificação.

⚠️ NENHUMA destas fórmulas está definida na documentação ([REL], [UC], [DC]): o DC só dá os nomes dos métodos
(ganharXP, subirNivel, calcularPontuacaoXP). Cada valor abaixo é PROVISÓRIO, com a evidência usada.
Centralizadas aqui para que a equipe troque num único lugar quando as regras forem decididas.
"""

# Evidência: tela "Progresso e Níveis" mostra Nível 4 com 2.430 / 3.000 XP (XP acumulado, "Total acumulado").
# A fórmula 750 × nível é consistente com esse único ponto (nível 4 → 3.000) e com 2.430 estar entre 2.250 e 3.000.
XP_POR_NIVEL = 750.0


def xp_proximo_nivel(nivel: int) -> float:
    """XP ACUMULADO necessário para sair do `nivel` atual."""
    return XP_POR_NIVEL * nivel


# Evidência: tela "Loja de Prêmios" mostra "2.430 pontos disponíveis", igual ao XP total da tela de Progresso.
# [DC] Recompensa.precoMoedas e Personagem.moedasOuro indicam que a compra gasta moedas, mas não como são ganhas.
MOEDAS_POR_XP = 1.0

# UC001/DC: Atividade.xpRecompensa; o formulário do Figma não tem campo de XP (a prévia mostra "+ 100 XP").
XP_PADRAO_ATIVIDADE = 100.0
