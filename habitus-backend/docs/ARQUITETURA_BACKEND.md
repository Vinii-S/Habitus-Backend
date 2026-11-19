# Habitus — Backend (FastAPI + SQLite): arquitetura e rastreabilidade

> **Gerado com auxílio de IA. Revisão final por: ______________________**
> A IA pode errar. Este documento deve ser conferido contra os diagramas originais por um integrante da equipe
> antes de virar decisão de projeto. Itens marcados **PROVISÓRIO** são escolhas minhas, não da documentação.

## 1. Verificação contra a documentação

### Correção importante sobre a minha proposta anterior
Na proposta que apresentei no chat eu me baseei no Diagrama de Classes e **não tinha visto o Diagrama de Componentes**
(`Diagrama de Componentes.drawio.html`; ele não constava da pasta no meu primeiro inventário). Ao lê-lo, minha estrutura
estava **parcialmente errada**: eu tinha separado `ranking` e `loja` em módulos próprios e não previa os componentes
*Automações e Cron Jobs* nem *Armazenamento de Mídia*. Foi refeita para espelhar o diagrama.

### O que cada documento foi usado para verificar
| Fonte | Conteúdo lido | Usado para |
|---|---|---|
| **[DCP]** Diagrama de Componentes (PlantUML embutido no `.drawio.html`) | 7 componentes do backend, SQLite, armazenamento de mídia e 23 ligações | Divisão em módulos e direção das dependências |
| **[DC]** Diagrama de Classes | 11 classes, atributos, métodos, multiplicidades, composições, herança | Tabelas e colunas |
| **[DCU]** Diagrama de Casos de Uso | Atores Membro, Líder/Admin, Sistema; 14 casos de uso | Endpoints e autorização |
| **[UC]** Casos de Uso Detalhados | UC001, UC002, UC003 | Fluxos principais e alternativos |
| **[REL]** Relatório | RF01–08, RNF01–10, escopo (§10), tecnologias (§9) | Requisitos e limites |
| **[FIG]** Telas | Dados que o frontend exibe | Formato das respostas |

**Não encontrei** na pasta os diagramas de **sequência** e de **implantação**, embora o cronograma de [REL §12] os cite.

## 2. Diagrama de Componentes → código

```
Frontend React ──REST/JSON──► [API Router e Gateway] = app/main.py + app/api/
                                  ├─► [Autenticacao e Gestao de Usuarios]  app/modules/auth
                                  ├─► [Gestao de Atividades]               app/modules/atividades
                                  ├─► [Validacao e Prova de Conclusao]     app/modules/validacao
                                  ├─► [Gamificacao e Evolucao]             app/modules/gamificacao
                                  ├─► [Grupos / Guildas]                   app/modules/grupos
                                  └   [Automacoes e Cron Jobs]             app/modules/automacoes
SQLite ← todos os módulos (app/core/database.py)      Armazenamento de Mídia ← app/core/storage.py
```

| Seta do [DCP] | Onde está no código |
|---|---|
| `FE → API` "REST/JSON" | `app/api/*` (JSON em camelCase) |
| `ATIV/VALID/GAME/GRUPOS ⇢ AUTH` "depende de" | `Depends(usuario_atual)` em todas as rotas |
| `VALID ⇢ ATIV` "valida tarefa" | `atividades.service.obter` (dono e ativa) antes do check-in |
| `VALID → GAME` "concede XP" | `validacao.service.registrar_checkin` → `gamificacao.conceder_xp` |
| `VALID → GRUPOS` "envia foto ao feed" | `grupos.publicar_evento` (post no mural) |
| `VALID → STORAGE` "upload de fotos" | `core/storage.ArmazenamentoLocal` |
| `GAME ⇢ GRUPOS` "fornece dados de ranking" | `gamificacao.classificar` usa `grupos.*` |
| `CRON ⇢ GAME` "aplica punições" | `automacoes.jobs.aplicar_penalidades` |
| `CRON ⇢ GRUPOS` "reset semanal de ligas" | `automacoes.jobs.processar_reset_semanal` |
| `AUTH/ATIV/VALID/GAME/GRUPOS → DB` | modelos em cada `models.py` |

**As dependências são verificadas por teste** (`tests/test_arquitetura.py` lê os `import` com AST e falha se um módulo usar
outro fora destas setas; confirmei que ele realmente falha quando injeto uma violação). Só o gateway (`app/api`) combina vários módulos.

## 3. Diagrama de Classes → tabelas

| Classe [DC] | Tabela | Atributos do DC | Relações do DC | Métodos do DC |
|---|---|---|---|---|
| Usuario | `usuario` | todos (id…fotoCapa; `senhaHash` nunca sai pela API) | `possui` Personagem 1—1 (composição); `amigoDe` 0..*—0..* | criarConta ✔ fazerLogin ✔ atualizarPerfil ✔ adicionarAmigo ✔ |
| Personagem | `personagem` | todos (8) | composição com Usuario | ganharXP/subirNivel ✔ (`conceder_xp`) gastarMoedas ✔ (`resgatar`) |
| Atividade | `atividade` | os 8 do DC | `cadastra` Usuario 1—0..* | cadastrar ✔ inativar ✔ calcularPontuacaoXP ✔ · **editarAtividade ✘** |
| CheckIn | `checkin` | os 5 do DC | `registra` Atividade 1—0..* (composição) | registrarConclusao/processarXPEvolucao ✔ |
| ProvaDeConclusao | `prova_conclusao` | os 4 do DC | `anexa` CheckIn 1—0..1 (composição) | validarTamanhoETipo ✔ enviarFoto ✔ |
| Grupo | `grupo` | os 5 do DC | contém MembroGrupo, PostagemMural, RankingGrupo (composições) | criarGrupo ✔ gerarCodigoConvite ✔ gerenciarGrupo ✔ processarResetGrupo ✔ · aplicarPenalidadeNegligencia **stub** |
| MembroGrupo | `membro_grupo` | os 4 do DC | `participa` Usuario 1—0..* | promoverAdmin ✔ removerMembro ✔ |
| PostagemMural | `postagem_mural` | os 4 do DC | `autor` Usuario 1—0..* | publicarNoMural ✔ · **interagirNoChat ✘** |
| RankingGrupo | `ranking_grupo` | os 3 do DC | `possui` Grupo 1—1 | calcularClassificacao ✔ atualizarLigasSemanais **parcial** |
| Recompensa | `recompensa` | os 5 do DC | — | comprarNaLoja ✔ |
| ItemConsumivel | `item_consumivel` (herança) | efeitoStatus, multiplicadorXP | `inventario` Personagem 1—0..* | usarItem **✘** (fora do escopo, ver B4) |

Exclusões em cascata seguem as composições (apagar usuário apaga personagem; apagar atividade apaga check-ins e prova…).

### Colunas/tabelas que NÃO estão no DC (vêm do Figma ou foram necessárias)
- `atividade`: `categoria`, `meta`, `duracao_estimada_min`, `lembrete_*` (tela Criar tarefa).
- `grupo`: `categorias`, `icone` (tela Explorar Guildas). `checkin.minutos` (Detalhes da tarefa).
- `recompensa`: `categoria`, `icone`, `classe` (discriminador da herança).
- **`resgate`** (tabela nova, **precisa de aprovação**): o DC só liga Personagem—ItemConsumivel; a Loja mostra "Resgatado" também para avatar, cupom, tema…
- `amizade`: tabela de associação para `amigoDe` (o DC não define convite/aceite — vínculo direto nos dois sentidos).

## 4. Casos de uso e requisitos → endpoints

Caminhos iguais aos esperados pelo frontend (`habitus-frontend/src/api/endpoints.ts`).

| Caso de uso / requisito | Endpoint | Observação |
|---|---|---|
| Criar Conta (RF01) | `POST /auth/cadastro` | 409 se e-mail/usuário já existe |
| Fazer Login (RF01) | `POST /auth/login` | mesma mensagem para e-mail/senha errados |
| Gestão de perfil (RF04) | `GET/PATCH /perfil`, `GET /perfil/resumo` | só campos editáveis; e-mail e id protegidos |
| Adicionar Amigos ([DCU]) | `POST/GET /amigos` | sem tela no Figma |
| **UC001** Cadastrar Atividade | `POST /atividades` | 4a: validação de campos (422); 6a: limite → 409 |
| Minhas tarefas / detalhe (RF05) | `GET /atividades`, `GET /atividades/{id}` | |
| "Excluir tarefa" | `DELETE /atividades/{id}` | inativa (DC `inativarAtividade`), preserva histórico |
| **UC003** Anexar Comprovante (RF05, RF06) | `POST /atividades/{id}/checkins` (multipart `prova` opcional) | 4a: tipo/tamanho → 422; XP, nível, post no feed |
| Criar grupo / Gerenciar grupo ([DCU]) | `POST /grupos`, `POST …/membros/{id}/promover`, `DELETE …/membros/{id}` | só Líder/Admin |
| Entrar por código ([REL §10]) | `POST /grupos/entrar` | |
| Minha Guilda / Explorar (RF03) | `GET /grupos/minha`, `GET /grupos?categoria&busca&ordenarPor` | código de convite só para membros |
| Mural (RF07) | `GET/POST /grupos/{id}/mural` | só membros |
| Visualizar Ranking (RF08) | `GET /ranking?periodo=geral\|semanal` | `mensal` → 501 |
| Comprar na loja de Recompensa | `GET /loja`, `POST /loja/{id}/resgatar` | |
| Sistema: Processar Reset do grupo | `automacoes.jobs.processar_reset_semanal` | agendador opcional |
| Sistema: Aplicar Penalidade | `automacoes.jobs.aplicar_penalidades` | **stub (0)** |
| **UC002** Interagir no Chat | — | **não implementado** (B1) |
| Usar Itens consumível | — | **não implementado** (B4) |
| (Figma) Desafios, Conquistas, Notificações, Progresso, Preferências | `GET /desafios` etc. | **501 explicativo** (B3) |

### RNF
RNF04 SQLite ✔ · RNF05 rotas síncronas rodam em threads + SQLite em modo WAL (**carga não testada**) · RNF06 10 MB e jpg/png validados no servidor, **inclusive pelos primeiros bytes do arquivo** (o `Content-Type` do cliente é falsificável) ✔ ·
RNF10 só biblioteca padrão + `pathlib`, sem dependência compilada (**não testado em Linux/Mac**) · RNF02 e RNF07 (tempos) — **não medidos**.

## 5. Conflitos, ambiguidades e decisões

| # | Ponto | Tratamento |
|---|---|---|
| B1 | **Chat**: [REL §10] "O grupo não terá um chat privado", mas [UC] UC002, [DCU], [DC] (`PostagemMural.interagirNoChat`) e [DCP] ("GRUPOS → DB : posts e chat") o preveem. O [DCP] reforça que o chat está na arquitetura. | Não implementado; mural sim. **Decisão da equipe.** |
| B2 | Seta `GAME ⇢ GRUPOS` com rótulo "fornece dados de ranking": a direção da seta (GAME usa GRUPOS) e o rótulo (GAME fornece) divergem. | Implementado pela direção da seta (GAME lê dados de GRUPOS). |
| B3 | Desafios, Conquistas, Notificações, níveis nomeados, preferências: têm tela mas **não existem** em [DC]/[UC]/[DCU]/[DCP]. | 501 com mensagem. Frontend mostra estado de erro nesses cartões. |
| B4 | Itens consumíveis: [REL §10] exclui a compra; [DC]/[DCU] os incluem. | Tabela existe (fidelidade ao DC), sem endpoint de uso. |
| B5 | Um usuário pode estar em vários grupos ([DC] 1—0..*), mas o Figma tem uma única "Minha Guilda". | Usa o vínculo mais antigo. |
| B6 | `MembroGrupo.papel` é String sem valores definidos; [DCU] fala "Líder/Admin". | `Líder`, `Admin`, `Membro`. |
| B7 | Autenticação não definida. | **PROVISÓRIO**: JWT HS256 em `Authorization: Bearer`, senha com scrypt (stdlib), 8 h de validade, mínimo 8 caracteres. |
| B8 | Dia do check-in. | **PROVISÓRIO**: dia em UTC; 1 check-in por atividade por dia. O fuso do usuário não está definido. |
| B9 | Ligas: o DC tem `ligaAtual`, mas não há nomes/regra de promoção. | `liga_atual` fica em "Liga 1"; o reset semanal só zera a pontuação. |
| B10 | Migrações de banco. | `create_all` (sem Alembic). Antes de produção, adotar migrações. |

### Regras PROVISÓRIAS (todas concentradas e comentadas no código)
| Regra | Valor | Evidência usada | Arquivo |
|---|---|---|---|
| XP para sair do nível *n* | 750 × n (acumulado) | única tela: Nível 4 com 2.430/3.000 | `gamificacao/regras.py` |
| Moedas ganhas | 1 por XP | Loja mostra 2.430 pontos = 2.430 XP | `gamificacao/regras.py` |
| XP padrão da atividade | 100 | prévia "+ 100 XP" no Figma | `atividades/models.py` |
| Limite de atividades ativas | 10 | UC001 "(ex: 10 tarefas)" | `core/config.py` |
| Status/progresso/"hoje" da tarefa | concluída 100% se há check-in no período; senão 0% | nenhuma (o Figma mostra 50%, 25%, "Atrasada") | `validacao/service.py` |
| Meta semanal / meta de contribuição | 7 tarefas / 300 XP | texto do Figma | `validacao`, `grupos` |
| Níveis da guilda | 100/300/1.000/2.500/5.000/7.500/10.000 | tela Minha Guilda | `grupos/service.py` |
| XP da guilda | soma do XP acumulado dos membros | nenhuma | `grupos/service.py` |
| Ciclo de reset | 7 dias | "Ligas Semanais", "Reseta em 5 dias" | `grupos/service.py` |
| Punição por negligência | **não faz nada** | nenhuma regra existe | `gamificacao/service.py` |

## 6. O que foi verificado

- **38 testes automatizados passam** (`pytest`): cadastro/login/perfil, UC001 (4a e 6a), UC003 (prova válida, PDF, arquivo falso, > 10 MB, nada gravado em caso de erro), streak, subida de nível, duplicidade de check-in, guildas, mural, permissões, ranking, loja (inclui não cobrar duas vezes), reset semanal, 501 dos pendentes, e as 5 verificações de arquitetura.
- **Integração real**: com `VITE_USE_MOCKS=false`, o frontend cadastrou um usuário, criou tarefa, fez check-in com PNG e abriu guilda, ranking, loja, explorar e perfil sem erro. Conferi no SQLite: check-in, prova, XP/moedas e hash de senha; o arquivo foi gravado com nome gerado pelo servidor.
- **Não verificado**: carga/concorrência (RNF05), tempos (RNF02, RNF07), execução em Linux/Mac (RNF10), segurança além do básico (sem limite de tentativas de login, sem renovação de token), e o agendador em execução contínua.
