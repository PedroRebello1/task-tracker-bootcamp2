"""Modo terminal do Task Tracker

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
    """
    aplicacao = AplicacaoTerminal(usuarios, tarefas, avisos, direto_no_cli=direto_no_cli)
    return aplicacao.run()
