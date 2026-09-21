# TaskTracker

Sistema de gerenciamento de tarefas pessoais, projeto da disciplina **Bootcamp II** (CEUB).
A **Etapa 1 — planejamento lógico** está entregue; este repositório agora recebe a **Etapa 2 — implementação em Python**.

| | |
|---|---|
| **Nome** | Pedro Rebello Borges de Barros |
| **Curso** | Ciência de Dados e Machine Learning |
| **Polo e Turma** | Asa Norte / Turma A |
| **E-mail** | pedro.rebello@sempreceub.com |
| **Disciplina** | Bootcamp II |

---

## O problema

Organizar tarefas em caderno, post-it e mensagens funciona até o volume crescer. O problema não é esquecer de anotar, é que uma anotação solta não tem prazo, não tem prioridade e não deixa histórico. Além disso, não existe filtro ou busca, e a informação espalhada em quatro lugares significa que não há uma fonte única da verdade.

## A solução proposta

Uma aplicação local escrita em Python. Na forma planejada na Etapa 1, o programa sobe um servidor na própria máquina e o usuário acessa pelo navegador em `http://localhost:5000`. Cada pessoa fará login e terá uma área própria, onde só enxerga e altera as suas tarefas.

- **Filtros de período** — Hoje, Semana, Mês e Todas
- **Prioridade em lista fechada** — Alta, Média ou Baixa, sendo ordenada por data e prioridade
- **Histórico preservado** — concluir não apaga, apenas muda o status e salva a data da conclusão
- **Categorias e busca** — Estudo, Trabalho, Pessoal, Saúde e Geral, junto à busca por palavras-chave
- **Relatório resumido** — total, concluídas, pendentes, atrasadas e percentual de conclusão
- **Visão administrativa** — perfil `admin` enxerga as tarefas de todos os usuários

### A mudança — duas interfaces

Na Etapa 1 planejei uma aplicação **100% web**: servidor Flask local e acesso pelo navegador, com Python no backend. Na webaula 3, a construção da aplicação foi apresentada como uma **CLI** — uma interface de linha de comando, executada no terminal. Em vez de abandonar o plano original ou reescrever o sistema, o plano foi ampliado: a aplicação terá uma segunda interface, de terminal, ao lado da web. Ao executar o programa, a primeira tela perguntará qual das duas usar.

Isso é possível sem tocar em nenhuma regra de negócio porque a estrutura desenhada na Etapa 1 já separa o sistema em camadas: as regras (RN01 a RN07), as operações sobre tarefas, a autenticação, o relatório e a persistência ficam em `servicos/`, `modelos/` e `repositorio/`, sem conhecer HTTP nem templates.

O Flask será apenas uma camada de apresentação sobre esses módulos, e o modo terminal será outra camada sobre os **mesmos** módulos e os **mesmos** arquivos de dados. Cada tela do terminal corresponderá a uma rota do web app e chamará exatamente a mesma função de serviço: o que a web recusar, o terminal recusa com a mesma mensagem. Os dois modos poderão até rodar ao mesmo tempo sobre a mesma pasta `dados/`.

Na prática, o trabalho da Etapa 2 é: implementar o que a Etapa 1 especificou e, por cima, adicionar o pacote `src/cli/` (telas em Textual) e a pergunta "terminal ou web?" no ponto de entrada. As regras de negócio e os formatos gravados em disco são os mesmos para as duas interfaces — e os testes das regras não dependem de nenhuma delas, porque testam os serviços diretamente.

---

## Etapas do projeto

| Etapa | Pasta | Situação |
|---|---|---|
| **1 — Planejamento lógico** | `especificacao/` | 🟢 Pronta |
| **2 — Implementação em Python** | `implementacao/` | 🟡 Em andamento |
| **3 — Empacotamento em Docker** | `docker/` | ⬜ Não iniciada |

A entrega da Etapa 1 foi um arquivo PDF contendo os três links — Google Docs, Google Apresentações e YouTube.

### Estrutura planejada do repositório

Este é o desenho que está sendo construído na Etapa 2.

```
task-tracker-bootcamp2/
│
├── especificacao/    ← ETAPA 1 (entregue)
│
├── implementacao/    ← ETAPA 2 (em construção)
│   ├── src/             - arquivos da aplicação
│   │   ├── app.py          - ponto de entrada: pergunta terminal ou web
│   │   ├── modelos/        - classes Tarefa e Usuario
│   │   ├── servicos/       - regras de negócio
│   │   ├── repositorio/    - único ponto que toca o disco
│   │   ├── templates/      - telas do web app em Jinja2
│   │   ├── estaticos/      - estilos em css
│   │   └── cli/            - telas do modo terminal em Textual
│   ├── dados/           - persistência em JSON
│   └── tests/           - testes automatizados com pytest
│
└── docker/           ← ETAPA 3 (a construir)
```

O `src/` é dividido por **responsabilidade**, não por tipo de arquivo. A decisão central é que as regras de negócio ficam em `servicos/`, nunca dentro das telas, e é isso que permite testá-las sem abrir o navegador nem o terminal, e é o que torna viável ter duas interfaces sobre a mesma lógica.

## Stack da Etapa 2

- **Python 3.12+**
- **Flask 3.x** — servidor web, com Jinja2 para os templates e Werkzeug para o hash das senhas
- **Textual** — interface de terminal, com telas, tabelas, formulários e suporte a mouse
- **pytest 8.x** — testes automatizados
- **Persistência em JSON** — legível a olho nu, nativo do Python e adequado como volume do Docker

---

## Licença

Este repositório está licenciado sob a [GNU General Public License v3.0 (GPLv3)](LICENSE).
