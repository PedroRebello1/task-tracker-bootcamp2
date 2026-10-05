# TaskTracker

Sistema de gerenciamento de tarefas pessoais.

|                        |                                      |
| ---------------------- | ------------------------------------ |
| **Autor**        | Pedro Rebello Borges de Barros       |
| **Curso**        | Ciência de Dados e Machine Learning |
| **Polo / Turma** | EAD — Campus Asa Norte / Turma A    |
| **E-mail**       | pedro.rebello@sempreceub.com         |
| **Disciplina**   | Bootcamp II                          |

---

## O problema

Organizar tarefas em caderno, post-it e mensagens para si mesmo funciona até o volume crescer. O problema não é esquecer de anotar — é que uma anotação solta não tem noção de prazo (papel não sabe que dia é hoje), não tem prioridade (tudo ocupa a mesma linha com o mesmo peso) e não deixa histórico (o item riscado desaparece). Além disso, não existe filtro nem busca, e informação espalhada em quatro lugares significa que não há uma fonte de verdade.

## A solução

Uma aplicação local em Python com **duas interfaces sobre as mesmas regras e os mesmos dados**:

- **Web app** (Flask): o programa sobe um servidor na própria máquina e o uso é pelo navegador, em `http://127.0.0.1:5000`.
- **Modo terminal** (Textual): uma aplicação de tela cheia dentro do próprio terminal, com tabelas, formulários, diálogos e mouse.

Ao iniciar, o sistema pergunta qual das duas usar. Cada pessoa faz login e tem uma área própria, onde só enxerga e altera as suas tarefas.

- **Filtros de período** — Hoje, Semana, Mês e Todas, para responder "o que eu tenho para hoje?" sem reler nada
- **Filtro de situação** — Todas, Pendentes, Concluídas e Atrasadas, mais busca por palavra no título
- **Prioridade em lista fechada** — Alta, Média ou Baixa, com a listagem ordenada por data e, no empate, por prioridade
- **Histórico preservado** — concluir não apaga: muda o status e carimba a data e a hora da conclusão
- **Categorias** — Estudo, Trabalho, Pessoal, Saúde e Geral
- **Relatório resumido** — total, concluídas, pendentes, atrasadas, percentual de conclusão e distribuições por prioridade e categoria
- **Visão administrativa** — perfil `admin`, que enxerga as tarefas de todos os usuários

### Por que duas interfaces

A Etapa 1 planejou uma aplicação **100% web**: servidor Flask local e acesso pelo navegador. Na webaula 3, o enunciado da Etapa 2 apresentou a construção da aplicação como uma **CLI** — interface de linha de comando, executada no terminal. Em vez de abandonar o plano original ou reescrever o sistema, o plano foi ampliado: a aplicação ganhou uma segunda interface, de terminal, ao lado da web.

Isso foi possível sem tocar em nenhuma regra de negócio porque a estrutura desenhada na Etapa 1 já separava o sistema em camadas: as regras (RN01 a RN07), as operações sobre tarefas, a autenticação, o relatório e a persistência não conhecem HTTP nem templates. O web app é uma camada fina de apresentação sobre esses módulos — e o modo terminal é outra, igualmente fina, sobre os **mesmos** módulos e os **mesmos** arquivos de dados. O que a web recusa, o terminal recusa com a mesma mensagem, e os dois podem até rodar ao mesmo tempo.

### Próximo passo: menu numerado e execução no Google Colab (a implementar)

Com as duas interfaces já construídas, ficaram claros dois requisitos da entrega da Etapa 2 que elas ainda não atendem:

- **Menu numerado em loop contínuo.** O enunciado pede uma CLI clássica, com as opções `1. Cadastrar nova tarefa`, `2. Visualizar tarefas cadastradas` e `3. Sair da aplicação`. Nela, uma entrada inválida (título vazio ou prioridade fora da lista) gera mensagem de erro e repete a pergunta. O modo terminal atual é uma aplicação de tela cheia, com formulários e atalhos de teclado, e a prioridade é escolhida numa lista, então não há como digitá-la errado.
- **Link do Google Colab.** O formulário de entrega pede, além do GitHub e do vídeo, um link do Colab, a plataforma oficial da disciplina. Nem a interface Textual, que precisa de um terminal real, nem o servidor Flask rodam dentro de uma célula do Colab.

Os dois serão atendidos por uma **terceira interface**: um menu numerado simples em `implementacao/src/main.py`, feito apenas com `input()` e `print()`, que valida campo a campo e repete a pergunta até a entrada ser válida. Um notebook do Colab vai clonar este repositório e executar esse menu. Junto com ele, a prioridade passará a aceitar "Media" sem acento, como pede o enunciado.

Como as outras duas, essa camada não terá regra de negócio própria. Ela chamará os mesmos serviços (`validacoes`, `GerenciadorTarefas`, `GerenciadorUsuarios`) e gravará nos mesmos arquivos de dados. A especificação da Etapa 1 continua sem alterações.

> **Situação:** a implementar. O link do Colab e as instruções de execução do menu serão adicionados a este README quando estiverem prontos.

---

## Como executar

**Pré-requisito:** Python 3.12 ou mais recente.

### 1. Instalar

A partir da raiz do repositório:

```
cd implementacao
python -m venv venv
venv\Scripts\activate
python -m pip install -r requirements.txt
```

No Linux ou macOS, ative o ambiente com `source venv/bin/activate`. Todos os comandos a seguir são executados dentro de `implementacao/`, com o ambiente ativado.

### 2. Carregar os dados de exemplo (opcional, recomendado)

Para ver o sistema já povoado, sem cadastrar nada à mão:

```
python -m src.exemplo
```

São 12 tarefas de 2 usuários, cobrindo os três níveis de prioridade, as cinco categorias, tarefas concluídas e uma deliberadamente atrasada. As datas são ajustadas para cair sobre a semana atual, para que o painel não abra vazio.

| Conta                       | Senha        | Perfil        |
| --------------------------- | ------------ | ------------- |
| `admin@tasktracker.local` | `admin123` | administrador |
| `pedro@exemplo.local`     | `senha123` | comum         |
| `ana@exemplo.local`       | `senha123` | comum         |

O comando se recusa a sobrescrever dados que já existem. Para substituí-los pelos de exemplo, use `python -m src.exemplo --forcar` — uma cópia `.bak` dos arquivos anteriores é guardada antes.

### 3. Iniciar

```
python -m src.app
```

A primeira tela pergunta como você quer usar o sistema: **Continuar no terminal** ou **Abrir o web app**. Escolha com as setas, com `1`/`2`, Enter ou um clique.

Para pular a pergunta:

```
python -m src.app --web     # sobe o servidor direto (acesse http://127.0.0.1:5000)
python -m src.app --cli     # entra no modo terminal direto
```

Sem os dados de exemplo, a primeira execução cria sozinha a pasta `dados/` e um administrador padrão, **`admin@tasktracker.local` / `admin123`**. Qualquer pessoa pode criar a própria conta pela tela de cadastro.

### Usando o web app

Ao escolher o web app pela tela inicial, o navegador abre sozinho em **http://127.0.0.1:5000**. Para encerrar o servidor, volte ao terminal e pressione `Ctrl+C`.

O botão de tema na barra de navegação alterna entre claro e escuro, e a escolha fica gravada na conta. No celular, a tabela de tarefas vira cartões.

### Usando o modo terminal

Funciona em qualquer terminal moderno — Windows Terminal, PowerShell, o terminal do VS Code, Linux e macOS — com teclado e mouse. O rodapé de cada tela lista os atalhos válidos nela; no painel de tarefas:

| Tecla          | Ação      | Tecla      | Ação                             |
| -------------- | ----------- | ---------- | ---------------------------------- |
| `n`          | nova tarefa | `l`      | relatório                         |
| `e` ou Enter | editar      | `a`      | administração (só perfil admin) |
| `c`          | concluir    | `/`      | buscar no título                  |
| `r`          | reabrir     | `q`      | sair da conta                      |
| `x`          | excluir     | `Esc`    | voltar / cancelar                  |
|                |             | `Ctrl+Q` | fechar o programa                  |

No terminal, as datas são digitadas no formato `DD/MM/AAAA`.

### 4. Rodar os testes

```
python -m pytest
```

São **239 testes**, todos passando: as regras de negócio isoladas, as operações sobre tarefas, a autenticação, o relatório, as rotas do web app e o modo terminal (dirigido por teclas e cliques simulados, sem abrir terminal).

---

## Regras de negócio

As sete regras especificadas na Etapa 1, todas implementadas e cobertas por testes:

| Regra          | Descrição                                                                                                                                   |
| -------------- | --------------------------------------------------------------------------------------------------------------------------------------------- |
| **RN01** | O título é obrigatório e não pode ser vazio (nem só espaços)                                                                            |
| **RN02** | A data prevista não pode ser anterior à data atual no cadastro — barreira dupla: o calendário nasce limitado e o servidor confere de novo |
| **RN03** | Prioridade e categoria só aceitam valores de uma lista fechada                                                                               |
| **RN04** | Uma tarefa concluída não pode ser editada — é preciso reabri-la antes                                                                     |
| **RN05** | Cada usuário só enxerga e altera as próprias tarefas; o administrador é a exceção                                                       |
| **RN06** | Toda exclusão exige confirmação explícita                                                                                                 |
| **RN07** | A data de conclusão nunca pode ser anterior à data de criação                                                                             |

Detalhamento completo, com exemplos e mensagens de erro, no documento de planejamento em [`especificacao/`](especificacao/).

## Diferenças em relação ao planejamento da Etapa 1

A especificação da Etapa 1 foi entregue e não foi alterada. O que a implementação acrescentou além dela:

- **Modo terminal** como segunda interface, escolhida ao iniciar — sem tocar nas regras, nas telas web nem no formato dos dados.
- **Menu numerado e notebook do Google Colab** *(a implementar)* — terceira interface, exigida pela entrega da Etapa 2; ver [Próximo passo](#próximo-passo-menu-numerado-e-execução-no-google-colab-a-implementar).
- **Filtro por situação** (Pendentes, Concluídas, Atrasadas), ao lado do filtro de período: a pergunta que motivou o sistema é sobre o que está *pendente*.
- **Data de conclusão visível** na listagem e nas confirmações, para que o histórico protegido pela RN04 sirva para alguma coisa.
- **Fuso horário explícito** (`America/Sao_Paulo`): o sistema gira em torno de "hoje", e num servidor em UTC uma tarefa criada às 21h30 nasceria com a data do dia seguinte.
- **Proteções de segurança** — senhas com hash, proteção contra CSRF, bloqueio de 60 s após 3 tentativas de login erradas.
- **Números do resumo clicáveis**, como atalho para o filtro de situação correspondente.
- **Lista de tarefas no relatório**, ao lado das distribuições.
- **Tema claro/escuro**, com a escolha gravada na conta.

---

## Etapas do projeto

| Etapa                                    | Pasta              | Situação       |
| ---------------------------------------- | ------------------ | ---------------- |
| **1 — Planejamento lógico**      | `especificacao/` | ✅ Entregue      |
| **2 — Implementação em Python** | `implementacao/` | 🟡 Em andamento  |
| **3 — Empacotamento em Docker**   | `docker/`        | ⬜ Não iniciada |

### Estrutura do repositório

```
task-tracker/
├── README.md
├── LICENSE
├── .gitignore
│
├── especificacao/                       ← ETAPA 1
│   ├── Planejamento Lógico TaskTracker.pdf
│   ├── Mapeamento Arquitetural TaskTracker.pdf
│   └── Entrega Etapa Inicial.pdf
│
├── implementacao/                       ← ETAPA 2
│   ├── requirements.txt
│   ├── pytest.ini
│   ├── src/
│   │   ├── app.py                       ponto de entrada: pergunta terminal ou web, define as rotas
│   │   ├── configuracao.py              constantes, listas fechadas, limites, caminhos
│   │   ├── exemplo.py                   instalador dos dados de exemplo
│   │   ├── modelos/                     classes Tarefa e Usuario
│   │   ├── servicos/                    regras de negócio (RN01 a RN07), gerenciadores, relatório, relógio
│   │   ├── repositorio/                 único ponto que lê e grava o disco (JSON)
│   │   ├── templates/                   telas do web app (Jinja2)
│   │   ├── estaticos/                   estilo.css
│   │   └── cli/                         telas do modo terminal (Textual)
│   ├── dados/                           persistência em JSON (só os *.exemplo.json vão para o Git)
│   └── tests/                           testes automatizados com pytest
│
└── docker/                              ← ETAPA 3 (a construir)
```

O `src/` é dividido por **responsabilidade**, não por tipo de arquivo. As regras de negócio ficam em `servicos/` e nunca dentro das telas — é isso que permite testá-las sem abrir o navegador, e é o que permitiu acrescentar o modo terminal sem reescrever nenhuma regra.

## Stack

- **Python 3.12+** (desenvolvido e testado em 3.14)
- **Flask 3.x** — servidor web; traz Jinja2 (templates) e Werkzeug (hash das senhas)
- **Textual 8.x** — interface de terminal; traz o Rich
- **tzdata** — base de fusos horários, que o Python não embute no Windows
- **pytest 8.x** — testes automatizados
- **Persistência em JSON** — legível a olho nu, nativo do Python e adequado como volume do Docker na Etapa 3

---

## Detalhes técnicos

Referência para quem for ler o código. Nada disto é necessário para usar o sistema.

<details>
<summary><b>Onde cada regra de negócio está implementada e testada</b></summary>

<br>

As funções ficam em `implementacao/src/servicos/validacoes.py`; os testes, em `implementacao/tests/`.

| Regra                                  | Implementação                                                           | Teste                                                                                  |
| -------------------------------------- | ------------------------------------------------------------------------- | -------------------------------------------------------------------------------------- |
| **RN01** título obrigatório    | `validacoes.validar_titulo`                                             | `TestRN01TituloObrigatorio`                                                          |
| **RN02** data não retroativa    | `validacoes.validar_data_prevista` + `min` no `<input type="date">` | `TestRN02DataNaoRetroativa`, `test_rn02_data_retroativa_e_recusada_pelo_servidor`  |
| **RN03** listas fechadas         | `validacoes.validar_prioridade` / `validar_categoria` + `<select>`  | `TestRN03ListasFechadas`, `test_rn03_prioridade_forjada_e_recusada`                |
| **RN04** concluída não edita   | `validacoes.validar_edicao_permitida` + tela `tarefa_concluida.html`  | `TestRN04ConcluidaNaoEdita`, `test_rn04_editar_concluida_mostra_a_tela_de_reabrir` |
| **RN05** isolamento por usuário | `validacoes.validar_permissao` / `validar_acesso_administrativo`      | `TestRN05Isolamento`, `TestRN05PorHttp`                                            |
| **RN06** exclusão confirmada    | rota`excluir_tarefa` — GET confirma, POST remove                       | `TestRN06Confirmacao`                                                                |
| **RN07** conclusão ≥ criação | `validacoes.validar_conclusao` e `validar_coerencia_temporal`         | `TestRN07ConclusaoDepoisDaCriacao`, `TestCoerenciaTemporalGravada`                 |

A RN02 e a RN03 têm **barreira dupla**: o navegador impede o erro pelo próprio controle (calendário limitado, lista de opções) e o servidor confere de novo ao receber o formulário. A tela previne o erro honesto; o servidor garante a integridade dos dados.

**Sobre a RN07.** No fluxo normal ela nunca dispara: a data de conclusão vem do relógio, e o relógio não anda para trás. Por isso ela ganhou um segundo uso — `validar_coerencia_temporal` aplica a mesma regra ao que **já está gravado**. O arquivo é texto e pode ter sido editado à mão; tarefas incoerentes são listadas no terminal ao subir o servidor.

</details>

<details>
<summary><b>O que cada arquivo de teste cobre</b></summary>

<br>

| Arquivo                               | O que cobre                                                                                                                             |
| ------------------------------------- | --------------------------------------------------------------------------------------------------------------------------------------- |
| `tests/test_validacoes.py`          | As sete regras de negócio, isoladas, sem disco nem servidor                                                                            |
| `tests/test_gerenciador_tarefas.py` | Operações sobre tarefas, filtros de período e situação, ordenação, atraso                                                        |
| `tests/test_autenticacao.py`        | Cadastro, login, bloqueio por tentativas, administrador padrão, repositório                                                           |
| `tests/test_relatorio.py`           | Os números do resumo, com a data injetada                                                                                              |
| `tests/test_relogio_e_exemplo.py`   | Fuso horário e o instalador dos dados de exemplo                                                                                       |
| `tests/test_rotas.py`               | O que só existe no HTTP: RN06 em duas etapas, RN05 por URL, CSRF, páginas de erro, herança de filtros                                |
| `tests/test_cli.py`                 | O modo terminal: tela de escolha, login e bloqueio, formulário, RN04, RN06, filtros, relatório, RN05 e as opções`--web`/`--cli` |

</details>

<details>
<summary><b>Organização do código</b></summary>

<br>

Caminhos relativos a `implementacao/`.

| Caminho                                  | Responsabilidade                                                                                                  |
| ---------------------------------------- | ----------------------------------------------------------------------------------------------------------------- |
| `src/app.py`                           | Ponto de entrada. Pergunta terminal ou web, cria o servidor e define os endereços. Coordena, não contém regra. |
| `src/cli/`                             | O modo terminal em Textual: uma tela por rota do web app, sobre os mesmos serviços. Sem regra de negócio.       |
| `src/configuracao.py`                  | Caminhos, listas fechadas, limites, fuso e dados do administrador padrão.                                        |
| `src/exemplo.py`                       | Instalador dos dados de exemplo.                                                                                  |
| `src/modelos/`                         | Classes`Tarefa` e `Usuario`, com conversão de e para JSON.                                                   |
| `src/servicos/validacoes.py`           | **As sete regras de negócio (RN01 a RN07).**                                                               |
| `src/servicos/gerenciador_tarefas.py`  | Criar, editar, concluir, reabrir, excluir, filtrar, buscar e ordenar.                                             |
| `src/servicos/gerenciador_usuarios.py` | Cadastro, autenticação, bloqueio por tentativas e perfil.                                                       |
| `src/servicos/relatorio.py`            | Os números do resumo.                                                                                            |
| `src/servicos/relogio.py`              | Único ponto que pergunta as horas, no fuso configurado.                                                          |
| `src/repositorio/repositorio_json.py`  | Único ponto do sistema que lê e grava o disco.                                                                  |
| `src/templates/`                       | As telas do web app em Jinja2. Sem regra de negócio.                                                             |
| `src/estaticos/estilo.css`             | Folha de estilo única, sem dependências externas.                                                               |
| `dados/`                               | Persistência em JSON. Criada automaticamente; só os exemplos vão para o Git.                                   |
| `tests/`                               | Testes automatizados com pytest.                                                                                  |

</details>

<details>
<summary><b>Correspondência entre o web app e o modo terminal</b></summary>

<br>

Cada tela do terminal chama os mesmos serviços que a rota correspondente do Flask (`GerenciadorTarefas`, `GerenciadorUsuarios`, `validacoes`, `relatorio`, `relogio`) e grava nos mesmos `dados/tarefas.json` e `dados/usuarios.json`.

| Rota do web app                             | Tela no terminal                                                                                                       |
| ------------------------------------------- | ---------------------------------------------------------------------------------------------------------------------- |
| `/login`, `/cadastro`                   | Entrar e Criar conta, com o mesmo bloqueio de 60 s após 3 falhas (contagem regressiva no botão)                      |
| `/` (painel)                              | Faixa de resumo, filtros de período e situação, busca no título enquanto digita, tabela e detalhe da tarefa        |
| `/tarefas/nova`, `/tarefas/<id>/editar` | Formulário com data mascarada`DD/MM/AAAA` e caixas de seleção para prioridade e categoria (RN03)                  |
| `/tarefas/<id>/concluir`, `/reabrir`    | Teclas`c` e `r`, ou os botões; concluída não se edita — a tela da RN04 oferece **Reabrir e editar**      |
| `/tarefas/<id>/excluir`                   | Diálogo de confirmação (RN06); o foco nasce em**Cancelar**, e só **Sim, excluir** remove               |
| `/relatorio`                              | Percentual de conclusão, distribuições por prioridade e categoria e a lista de títulos, no mesmo recorte do painel |
| `/admin`                                  | Tecla`a`, só para o perfil admin (RN05): coluna do dono e tarefas de todos                                          |
| `/sair`                                   | Tecla`q` ou botão **Sair**: encerra a sessão e volta ao login                                                |
| `/tema`                                   | Não há botão; o tema gravado na conta (claro/escuro) é aplicado ao entrar                                          |

Uma diferença de forma, não de regra: no navegador a data vem de um calendário, que entrega `AAAA-MM-DD` ao servidor; no terminal ela é digitada como `DD/MM/AAAA`, e a camada CLI apenas reordena o texto para o mesmo `AAAA-MM-DD` antes de entregá-lo a `converter_data`. A validação (RN02) continua toda no serviço.

Sem um terminal interativo — dentro do Docker, com a saída redirecionada, em CI — não há a quem perguntar, e `python -m src.app` sobe o web app direto. É isso que mantém a Etapa 3 funcionando sem mudança.

</details>

<details>
<summary><b>Segurança</b></summary>

<br>

Nada aqui é exigido pela Etapa 1; são o mínimo para a aplicação não ser ingênua.

- **Senhas** guardadas com `generate_password_hash` (Werkzeug). Nunca em texto puro, nem no arquivo nem no log.
- **CSRF**: todo POST carrega um token da sessão, conferido com `secrets.compare_digest`. Sem token válido, a requisição é recusada com 400. `Sair` é um POST, não um link.
- **Sessão**: cookie `HttpOnly` e `SameSite=Lax`, com validade de 12 horas. O identificador da sessão é trocado a cada login, para que um valor capturado antes deixe de valer.
- **Redirecionamento**: o parâmetro `voltar_para` só aceita caminhos deste servidor — `//outro-site.com` começa com barra, mas o navegador o trataria como endereço absoluto.
- **Mensagem de login genérica**: "E-mail ou senha inválidos" não revela qual dos dois está errado. Após 3 tentativas, o formulário é bloqueado por 60 segundos, com contagem visível.
- **Depuração desligada por padrão.** O modo de depuração do Flask expõe um console que executa Python no servidor.

O terminal avisa, ao iniciar, quando a senha do administrador, a chave de sessão ou o modo de depuração estão nos valores de desenvolvimento.

</details>

<details>
<summary><b>Variáveis de ambiente</b></summary>

<br>

Nenhuma é necessária para rodar localmente; os padrões servem.

| Variável                     | Padrão                     | Para quê                                   |
| ----------------------------- | --------------------------- | ------------------------------------------- |
| `TASKTRACKER_HOST`          | `127.0.0.1`               | Endereço de escuta (no Docker,`0.0.0.0`) |
| `TASKTRACKER_PORTA`         | `5000`                    | Porta do servidor                           |
| `TASKTRACKER_DEBUG`         | `0`                       | `1` liga o modo de depuração            |
| `TASKTRACKER_CHAVE_SECRETA` | sorteada a cada início     | Assina o cookie de sessão                  |
| `TASKTRACKER_COOKIE_SEGURO` | `0`                       | `1` quando servir por HTTPS               |
| `TASKTRACKER_HORAS_SESSAO`  | `12`                      | Validade da sessão                         |
| `TASKTRACKER_FUSO`          | `America/Sao_Paulo`       | Fuso usado por "hoje"                       |
| `TASKTRACKER_PASTA_DADOS`   | `implementacao/dados`     | Onde ficam os arquivos JSON                 |
| `TASKTRACKER_ADMIN_LOGIN`   | `admin@tasktracker.local` | Login do administrador inicial              |
| `TASKTRACKER_ADMIN_SENHA`   | `admin123`                | Senha do administrador inicial              |

`TASKTRACKER_ADMIN_LOGIN` e `TASKTRACKER_ADMIN_SENHA` só têm efeito **antes** da primeira execução: depois que existe um administrador em `usuarios.json`, ele não é recriado.

A preparação dos dados roda na **primeira requisição**, e não apenas no `python -m src.app`. Isso mantém o comportamento correto quando a aplicação sobe por `flask run` ou por um servidor WSGI, que é o cenário da Etapa 3.

</details>

<details>
<summary><b>Interface web</b></summary>

<br>

- O tema claro/escuro fica no **cadastro do usuário**, e não no navegador, então acompanha a conta de uma máquina para outra; o visitante que ainda não entrou guarda o dele na sessão. O tema é resolvido no servidor e sai no próprio `<html>`, então a página não pisca clara antes de escurecer.
- No celular, a tabela de tarefas vira cartões — rolar uma tabela de oito colunas em tela pequena é hostil. A troca é feita só com CSS.
- Navegação por teclado com foco visível, link "pular para o conteúdo", rótulos associados aos campos e mensagens de erro anunciadas por leitores de tela.
- Nenhuma fonte, ícone ou script vindo de CDN: a aplicação funciona offline. O único JavaScript são as 12 linhas que fazem a contagem regressiva do bloqueio de login, e a tela funciona sem elas — inclusive a troca de tema, que é um POST comum.

</details>

<details>
<summary><b>Dados de exemplo</b></summary>

<br>

Os arquivos-fonte (`implementacao/dados/*.exemplo.json`) são versionados e podem ser copiados manualmente para `tarefas.json` e `usuarios.json`. O instalador (`python -m src.exemplo`) faz uma coisa a mais: **desloca todas as datas** para que a semana do exemplo caia sobre a semana atual. Sem isso, o painel abriria vazio, porque o filtro padrão é "Hoje" e as datas gravadas no arquivo são de setembro de 2026.

</details>

---

## Licença

GNU GPL v3.0 — ver [`LICENSE`](LICENSE).
