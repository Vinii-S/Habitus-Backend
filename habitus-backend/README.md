# Habitus — Backend (FastAPI + SQLite)

> Gerado com auxílio de IA. Revisão final por: ______________________

Esqueleto do backend do Habitus. Estrutura baseada no Diagrama de Componentes e no Diagrama de Classes.
**Leia [docs/ARQUITETURA_BACKEND.md](docs/ARQUITETURA_BACKEND.md)**: rastreabilidade, conflitos entre documentos e regras provisórias.

## Rodar (Windows PowerShell; em Linux/Mac troque `.venv\Scripts\` por `.venv/bin/`)

```bash
python -m venv .venv
.venv\Scripts\python -m pip install -r requirements.txt
.venv\Scripts\python -m app.seed
.venv\Scripts\python -m uvicorn app.main:app --reload
```

API em `http://localhost:8000` · documentação interativa em `http://localhost:8000/docs`.

## Testes

```bash
.venv\Scripts\python -m pytest
```

## Ligar ao frontend

No frontend (`habitus-frontend`), defina `VITE_USE_MOCKS=false` e `VITE_API_URL=http://localhost:8000` (ver `.env.example` de lá).
As telas de Desafios, Conquistas, Notificações, Progresso e Preferências recebem **501** porque essas entidades não existem na documentação.

## Automações (reset semanal das ligas, punições)

```bash
.venv\Scripts\python -m app.modules.automacoes     # execução avulsa (para cron do sistema)
```

Ou `HABITUS_SCHEDULER=1` para rodar dentro da API a cada hora. Variáveis em `.env.example`.
