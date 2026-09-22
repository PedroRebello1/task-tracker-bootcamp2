"""Testa os números do relatório (Passo 8).

O ponto central destes testes é a data: `gerar` recebe `hoje` em vez de
perguntar as horas, e é isso que permite afirmar quantas tarefas estão
atrasadas sem depender do dia em que a suíte roda.
"""
from datetime import date, datetime, timedelta

from src import configuracao
from src.modelos.tarefa import Tarefa
from src.servicos import relatorio

HOJE = date(2026, 9, 22)


def tarefa(id=1, data=None, prioridade="Alta", categoria="Estudo", concluida=False):
    return Tarefa(
        id=id, titulo="Tarefa %s" % id, data_prevista=data or HOJE,
        prioridade=prioridade, categoria=categoria, usuario_id=1,
        status=configuracao.STATUS_CONCLUIDA if concluida else configuracao.STATUS_PENDENTE,
        data_criacao=datetime(2026, 9, 16, 9, 0),
        data_conclusao=datetime(2026, 9, 21, 9, 0) if concluida else None,
    )


class TestConjuntoVazio:
    def test_relatorio_vazio_se_anuncia(self):
        resumo = relatorio.gerar([], hoje=HOJE)
        assert resumo["vazio"] is True
        assert resumo["total"] == 0 and resumo["percentual"] == 0.0


class TestContagens:
    def test_totais_e_percentual(self):
        tarefas = [tarefa(1, concluida=True), tarefa(2, concluida=True),
                   tarefa(3), tarefa(4)]
        resumo = relatorio.gerar(tarefas, hoje=HOJE)
        assert resumo["total"] == 4
        assert resumo["concluidas"] == 2 and resumo["pendentes"] == 2
        assert resumo["percentual"] == 50.0

    def test_atrasadas_usam_a_data_recebida(self):
        """Se `hoje` fosse ignorado, este teste mudaria de resultado com o calendário."""
        vencida = tarefa(1, data=HOJE - timedelta(days=3))
        futura = tarefa(2, data=HOJE + timedelta(days=3))
        assert relatorio.gerar([vencida, futura], hoje=HOJE)["atrasadas"] == 1

    def test_o_mesmo_conjunto_muda_de_atraso_conforme_a_data(self):
        alvo = [tarefa(1, data=HOJE)]
        assert relatorio.gerar(alvo, hoje=HOJE)["atrasadas"] == 0
        assert relatorio.gerar(alvo, hoje=HOJE + timedelta(days=1))["atrasadas"] == 1

    def test_concluida_vencida_nao_conta_como_atrasada(self):
        feita = tarefa(1, data=HOJE - timedelta(days=5), concluida=True)
        assert relatorio.gerar([feita], hoje=HOJE)["atrasadas"] == 0

    def test_percentual_de_cem_por_cento(self):
        assert relatorio.gerar([tarefa(1, concluida=True)], hoje=HOJE)["percentual"] == 100.0


class TestDistribuicoes:
    def test_distribuicao_por_prioridade(self):
        tarefas = [tarefa(1, prioridade="Alta"), tarefa(2, prioridade="Alta"),
                   tarefa(3, prioridade="Baixa")]
        por_prioridade = relatorio.gerar(tarefas, hoje=HOJE)["por_prioridade"]
        assert [(i["valor"], i["quantidade"]) for i in por_prioridade] == [("Alta", 2), ("Baixa", 1)]

    def test_valores_zerados_ficam_de_fora(self):
        resumo = relatorio.gerar([tarefa(1, categoria="Saúde")], hoje=HOJE)
        assert [i["valor"] for i in resumo["por_categoria"]] == ["Saúde"]

    def test_distribuicao_segue_a_ordem_da_lista_fechada(self):
        tarefas = [tarefa(1, prioridade="Baixa"), tarefa(2, prioridade="Alta"),
                   tarefa(3, prioridade="Média")]
        valores = [i["valor"] for i in relatorio.gerar(tarefas, hoje=HOJE)["por_prioridade"]]
        assert valores == list(configuracao.PRIORIDADES)

    def test_percentual_da_distribuicao(self):
        tarefas = [tarefa(1, prioridade="Alta"), tarefa(2, prioridade="Baixa")]
        resumo = relatorio.gerar(tarefas, hoje=HOJE)
        assert all(item["percentual"] == 50.0 for item in resumo["por_prioridade"])