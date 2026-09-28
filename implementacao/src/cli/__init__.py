"""Modo terminal do Task Tracker - a segunda camada de apresentacao.

Tudo aqui e tela: formularios, tabelas, botoes e dialogos desenhados no
terminal com a biblioteca Textual, navegaveis por teclado e por mouse. As
regras continuam em src/servicos/, exatamente as mesmas que o Flask usa -
este pacote apenas as chama e mostra o resultado, como app.py faz com HTML.

Cada tela corresponde a uma rota da aplicacao web:

    boas_vindas.py   a escolha entre terminal e web app (so existe aqui)
    conta.py         /login e /cadastro
    painel.py        / e /admin
    formulario.py    /tarefas/nova e /tarefas/<id>/editar
    dialogos.py      /tarefas/<id>/excluir (RN06) e a tela da RN04
    relatorio.py     /relatorio

Ponto de entrada: `iniciar()`, chamado pelo bloco __main__ de src/app.py.
"""
from src.cli.aplicacao import AplicacaoTerminal


def iniciar(usuarios, tarefas, avisos=(), direto_no_cli=False):
    """Roda a interface de terminal e devolve o que o usuario pediu ao sair.

    Devolve "web" quando ele escolheu abrir o web app, e None quando fechou
    o programa. `direto_no_cli` pula a tela de escolha (e o caso de `--cli`).

    Os gerenciadores chegam de fora, e nao sao criados aqui, para que o modo
    terminal use as mesmas instancias (e os mesmos arquivos) que o Flask.
    """
    aplicacao = AplicacaoTerminal(usuarios, tarefas, avisos, direto_no_cli=direto_no_cli)
    return aplicacao.run()
