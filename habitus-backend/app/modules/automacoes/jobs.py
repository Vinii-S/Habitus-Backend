"""Componente [Automacoes e Cron Jobs] — ator "Sistema" do Diagrama de Casos de Uso.

  CRON → GAME    "aplica punições por negligência"  → aplicar_penalidades()
  CRON → GRUPOS  "reset semanal de ligas"           → processar_reset_semanal()
  CRON → DB      "consulta/atualiza status"
"""
import logging

from sqlalchemy.orm import Session

from app.modules.gamificacao import service as gamificacao
from app.modules.grupos import service as grupos

log = logging.getLogger("habitus.automacoes")


def aplicar_penalidades(db: Session) -> int:  # UC (Sistema): "Aplicar Penalidade de Negligência"
    return gamificacao.aplicar_penalidade_negligencia(db)


def processar_reset_semanal(db: Session) -> int:  # UC (Sistema): "Processar Reset do grupo"
    return grupos.processar_reset_semanal(db)


def executar_todos(db: Session) -> dict[str, int]:
    resultado = {"punicoes": aplicar_penalidades(db), "grupos_reiniciados": processar_reset_semanal(db)}
    log.info("automações executadas: %s", resultado)
    return resultado
