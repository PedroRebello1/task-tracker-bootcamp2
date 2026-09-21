# TaskTracker

Sistema de gerenciamento de tarefas pessoais, projeto da disciplina **Bootcamp II** (CEUB).
Este repositório está na **Etapa 1 — planejamento lógico**.

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

Uma aplicação web local: o programa será escrito em Python, subirá um servidor na própria máquina e o usuário acessará pelo navegador em `http://localhost:5000`. Cada pessoa fará login e terá uma área própria, onde só enxerga e altera as suas tarefas.

- **Filtros de período** — Hoje, Semana, Mês e Todas
- **Prioridade em lista fechada** — Alta, Média ou Baixa, sendo ordenada por data e prioridade
- **Histórico preservado** — concluir não apaga, apenas muda o status e salva a data da conclusão
- **Categorias e busca** — Estudo, Trabalho, Pessoal, Saúde e Geral, junto à busca por palavras-chave
- **Relatório resumido** — total, concluídas, pendentes, atrasadas e percentual de conclusão
- **Visão administrativa** — perfil `admin` enxerga as tarefas de todos os usuários

---

## Etapas do projeto

| Etapa | Pasta | Situação |
|---|---|---|
| **1 — Planejamento lógico** | `especificacao/` | 🟢 Pronta |
| **2 — Implementação em Python** | `implementacao/` | ⬜ Não iniciada |
| **3 — Empacotamento em Docker** | `docker/` | ⬜ Não iniciada |

A entrega da Etapa 1 será um aquivo PDF/docx contendo os três links — Google Docs, Google Apresentações e YouTube.

### Estrutura planejada do repositório

Este é o desenho que será construído na Fase 2 — hoje só a `especificacao/` tem conteúdo.

```
task-tracker-bootcamp2/
│
├── especificacao/    ← ETAPA 1 (esta entrega)
│
├── implementacao/    ← ETAPA 2 (a construir)
│   ├── src/             - arquivos da aplicação
│   │   ├── modelos/        - classes Tarefa e Usuario
│   │   ├── servicos/       - regras de negócio
│   │   ├── repositorio/    - único ponto que toca o disco
│   │   ├── templates/      - telas em Jinja2
│   │   └── estaticos/      - estilos em css
│   ├── dados/           - persistência em JSON
│   └── tests/           - testes automatizados com pytest
│
└── docker/           ← ETAPA 3 (a construir)
```

O `src/` será dividido por **responsabilidade**, não por tipo de arquivo. A decisão central é que as regras de negócio ficarão em `servicos/`, nunca dentro das telas, e é isso que vai permitir testá-las sem abrir o navegador.

## Stack prevista para a Fase 2

- **Python 3.12**
- **Flask 3.x** — servidor web, com Jinja2 para os templates e Werkzeug para o hash das senhas
- **pytest 8.x** — testes automatizados
- **Persistência em JSON** — legível a olho nu, nativo do Python e adequado como volume do Docker

---

## Licença

Este repositório está licenciado sob a [GNU General Public License v3.0 (GPLv3)](LICENSE).
