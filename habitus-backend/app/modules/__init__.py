"""Um pacote por componente do Diagrama de Componentes (componente "Backend (FastAPI)").

  auth         → [Autenticacao e Gestao de Usuarios]
  atividades   → [Gestao de Atividades]
  validacao    → [Validacao e Prova de Conclusao]
  gamificacao  → [Gamificacao e Evolucao]
  grupos       → [Grupos / Guildas]
  automacoes   → [Automacoes e Cron Jobs]

Dependências PERMITIDAS entre módulos (setas do diagrama; verificadas em tests/test_arquitetura.py):
  atividades→auth · validacao→auth,atividades,gamificacao,grupos · gamificacao→auth,grupos ·
  grupos→auth · automacoes→gamificacao,grupos
O [API Router e Gateway] é app/api + app/main.py e pode usar todos.
"""
