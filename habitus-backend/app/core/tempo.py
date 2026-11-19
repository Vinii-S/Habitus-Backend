from datetime import date, datetime, timedelta, timezone


def agora() -> datetime:
    """Horário atual em UTC, sem fuso (SQLite não guarda fuso)."""
    return datetime.now(timezone.utc).replace(tzinfo=None)


def inicio_da_semana(d: date) -> date:
    """Segunda-feira. (O Figma tem a preferência "Início da semana: Segunda-feira"; no backend não há onde guardá-la.)"""
    return d - timedelta(days=d.weekday())


MESES_ABREV = ["jan", "fev", "mar", "abr", "mai", "jun", "jul", "ago", "set", "out", "nov", "dez"]
DIAS_ABREV = ["Seg", "Ter", "Qua", "Qui", "Sex", "Sáb", "Dom"]


def data_extenso_curto(d: datetime | date) -> str:
    """'12 de abr de 2025' — formato visto em "Resgates recentes" (Figma, Loja)."""
    return f"{d.day:02d} de {MESES_ABREV[d.month - 1]} de {d.year}"
