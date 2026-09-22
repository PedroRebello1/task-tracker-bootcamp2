"""Relatorio resumido - Passo 8 do algoritmo.

Trabalha sobre o conjunto de tarefas que o painel esta exibindo, ou seja, ja
filtrado por dono, periodo, situacao e busca.
"""
from src import configuracao
from src.servicos import relogio


def gerar(tarefas, hoje=None):
    """Devolve os numeros do resumo. `vazio` indica que nao há o que reportar.

    'hoje' decide o que conta como atrasado. Recebe-lo em vez de perguntar as
    horas e o que permite testar o relatorio numa data fixa.
    """
    hoje = hoje or relogio.hoje()
    total = len(tarefas)

    if total == 0:
        return {
            "vazio": True,
            "total": 0,
            "concluidas": 0,
            "pendentes": 0,
            "atrasadas": 0,
            "percentual": 0.0,
            "por_prioridade": [],
            "por_categoria": [],
        }

    concluidas = sum(1 for tarefa in tarefas if tarefa.concluida)
    atrasadas = sum(1 for tarefa in tarefas if tarefa.esta_atrasada(hoje))

    return {
        "vazio": False,
        "total": total,
        "concluidas": concluidas,
        "pendentes": total - concluidas,
        "atrasadas": atrasadas,
        "percentual": round(concluidas * 100.0 / total, 1),
        "por_prioridade": _distribuir(tarefas, "prioridade", configuracao.PRIORIDADES),
        "por_categoria": _distribuir(tarefas, "categoria", configuracao.CATEGORIAS),
    }


def _distribuir(tarefas, atributo, valores_possiveis):
    """Conta quantas tarefas caem em cada valor, omitindo os que ficaram em zero."""
    total = len(tarefas)
    distribuicao = []
    for valor in valores_possiveis:
        quantidade = sum(1 for tarefa in tarefas if getattr(tarefa, atributo) == valor)
        if quantidade:
            distribuicao.append({
                "valor": valor,
                "quantidade": quantidade,
                "percentual": round(quantidade * 100.0 / total, 1),
            })
    return distribuicao
