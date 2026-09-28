"""Formatacao de texto para o terminal - o papel que o Jinja2 e o CSS fazem na web.

Só apresentacao. Datas no formato brasileiro, cores por prioridade e status,
barras de percentual. Nada aqui decide regra.
"""
from rich.text import Text

from src import configuracao

# Mesmas cores da folha de estilo da web, na paleta do terminal.
COR_PRIORIDADE = {"Alta": "bold red", "Média": "yellow", "Baixa": "green"}
COR_STATUS = {configuracao.STATUS_CONCLUIDA: "green", configuracao.STATUS_PENDENTE: "cyan"}


def data(valor):
    """date -> '21/09/2026'."""
    return valor.strftime("%d/%m/%Y")


def momento(valor):
    """datetime -> '28/09/2026 às 14:05'."""
    return valor.strftime("%d/%m/%Y às %H:%M")


def prioridade(valor):
    return Text(valor, style=COR_PRIORIDADE.get(valor, ""))


def status(tarefa):
    texto = Text(tarefa.status, style=COR_STATUS.get(tarefa.status, ""))
    if tarefa.data_conclusao:
        texto.append("  em %s" % momento(tarefa.data_conclusao), style="dim")
    return texto


def data_prevista(tarefa, hoje):
    texto = Text(data(tarefa.data_prevista))
    if tarefa.esta_atrasada(hoje):
        texto.append("  atrasada", style="bold red")
    return texto


def titulo(tarefa):
    estilo = "dim strike" if tarefa.concluida else ""
    return Text(tarefa.titulo, style=estilo)


def barra(percentual, largura=24):
    """42.9 -> '██████████░░░░░░░░░░░░░░'."""
    cheios = int(round(largura * percentual / 100.0))
    return "█" * cheios + "░" * (largura - cheios)


def plural(quantidade, singular, plural_):
    return singular if quantidade == 1 else plural_
