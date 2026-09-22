"""Testa criacao, edicao, conclusao, exclusao, filtros de periodo e ordenacao.

Cada teste usa um arquivo JSON temporario, para nunca tocar os dados reais.
"""
from datetime import date, datetime, timedelta

import pytest

from src import configuracao
from src.modelos.usuario import Usuario
from src.repositorio.repositorio_json import RepositorioJson
from src.servicos.gerenciador_tarefas import GerenciadorTarefas
from src.servicos.validacoes import ErroDeRegra

HOJE = date(2026, 9, 22)
SEGUNDA = date(2026, 9, 21)
DOMINGO = date(2026, 9, 27)


@pytest.fixture
def gerenciador(tmp_path):
    return GerenciadorTarefas(RepositorioJson(str(tmp_path / "tarefas.json")))


@pytest.fixture
def pedro():
    return Usuario(id=1, nome="Pedro", login="pedro@x.com", senha_hash="x")


@pytest.fixture
def ana():
    return Usuario(id=2, nome="Ana", login="ana@x.com", senha_hash="x")


@pytest.fixture
def admin():
    return Usuario(id=9, nome="Admin", login="admin@x.com", senha_hash="x",
                   perfil=configuracao.PERFIL_ADMIN)


def criar(gerenciador, usuario, titulo="Estudar", data=None,
          prioridade="Média", categoria="Geral"):
    tarefa, erros = gerenciador.criar(
        usuario, titulo, "", (data or HOJE).isoformat(), prioridade, categoria, hoje=HOJE)
    assert erros == [], erros
    return tarefa


# criacao
class TestCriacao:
    def test_tarefa_nasce_pendente_e_sem_data_de_conclusao(self, gerenciador, pedro):
        tarefa = criar(gerenciador, pedro)
        assert tarefa.status == configuracao.STATUS_PENDENTE
        assert tarefa.data_conclusao is None

    def test_identificador_e_sequencial(self, gerenciador, pedro):
        assert [criar(gerenciador, pedro).id for _ in range(3)] == [1, 2, 3]

    def test_dono_e_o_usuario_da_sessao(self, gerenciador, ana):
        assert criar(gerenciador, ana).usuario_id == ana.id

    def test_titulo_vazio_impede_a_criacao(self, gerenciador, pedro):
        tarefa, erros = gerenciador.criar(pedro, "   ", "", HOJE.isoformat(),
                                          "Alta", "Geral", hoje=HOJE)
        assert tarefa is None
        assert erros == ["Informe um título para a tarefa."]
        assert gerenciador.listar_todas() == []

    def test_data_retroativa_impede_a_criacao(self, gerenciador, pedro):
        tarefa, erros = gerenciador.criar(
            pedro, "Estudar", "", (HOJE - timedelta(days=1)).isoformat(),
            "Alta", "Geral", hoje=HOJE)
        assert tarefa is None and len(erros) == 1

    def test_prioridade_invalida_impede_a_criacao(self, gerenciador, pedro):
        tarefa, erros = gerenciador.criar(pedro, "Estudar", "", HOJE.isoformat(),
                                          "urgentíssima", "Geral", hoje=HOJE)
        assert tarefa is None and "Prioridade inválida" in erros[0]

    def test_dados_sobrevivem_a_releitura_do_arquivo(self, gerenciador, pedro):
        criar(gerenciador, pedro, titulo="Persistir", data=HOJE)
        assert gerenciador.listar_todas()[0].titulo == "Persistir"


# edicao
class TestEdicao:
    def test_edicao_altera_os_campos(self, gerenciador, pedro):
        tarefa = criar(gerenciador, pedro)
        editada, erros = gerenciador.editar(
            pedro, tarefa.id, "Novo título", "detalhe",
            (HOJE + timedelta(days=2)).isoformat(), "Alta", "Estudo", hoje=HOJE)
        assert erros == []
        assert editada.titulo == "Novo título" and editada.prioridade == "Alta"

    def test_rn04_tarefa_concluida_nao_pode_ser_editada(self, gerenciador, pedro):
        tarefa = criar(gerenciador, pedro)
        gerenciador.concluir(pedro, tarefa.id)
        with pytest.raises(ErroDeRegra, match="Reabra-a"):
            gerenciador.editar(pedro, tarefa.id, "Outro", "", HOJE.isoformat(),
                               "Alta", "Geral", hoje=HOJE)

    def test_rn05_outro_usuario_nao_edita(self, gerenciador, pedro, ana):
        tarefa = criar(gerenciador, pedro)
        with pytest.raises(ErroDeRegra, match="permissão"):
            gerenciador.editar(ana, tarefa.id, "Invadida", "", HOJE.isoformat(),
                               "Alta", "Geral", hoje=HOJE)

    def test_admin_edita_tarefa_de_outro(self, gerenciador, pedro, admin):
        tarefa = criar(gerenciador, pedro)
        _, erros = gerenciador.editar(admin, tarefa.id, "Ajustada", "",
                                      HOJE.isoformat(), "Alta", "Geral", hoje=HOJE)
        assert erros == []

    def test_tarefa_antiga_mantem_a_propria_data(self, gerenciador, pedro):
        """RN02 nao engessa o historico: da para editar outros campos."""
        antiga = HOJE - timedelta(days=10)
        tarefa = criar(gerenciador, pedro, data=HOJE)
        # coloca a tarefa no passado direto no arquivo, simulando o tempo passando
        todas = gerenciador.listar_todas()
        todas[0].data_prevista = antiga
        gerenciador._gravar(todas)

        _, erros = gerenciador.editar(pedro, tarefa.id, "Título novo", "",
                                      antiga.isoformat(), "Alta", "Geral", hoje=HOJE)
        assert erros == []

    def test_id_inexistente_avisa(self, gerenciador, pedro):
        with pytest.raises(ErroDeRegra, match="não encontrada"):
            gerenciador.buscar_por_id(999, pedro)


# conclusao e reabertura
class TestConclusao:
    def test_concluir_muda_status_e_carimba_a_data(self, gerenciador, pedro):
        tarefa = gerenciador.concluir(pedro, criar(gerenciador, pedro).id)
        assert tarefa.status == configuracao.STATUS_CONCLUIDA
        assert tarefa.data_conclusao is not None

    def test_concluir_duas_vezes_avisa(self, gerenciador, pedro):
        tarefa = criar(gerenciador, pedro)
        gerenciador.concluir(pedro, tarefa.id)
        with pytest.raises(ErroDeRegra, match="já está concluída"):
            gerenciador.concluir(pedro, tarefa.id)

    def test_rn07_conclusao_antes_da_criacao_e_recusada(self, gerenciador, pedro):
        tarefa = criar(gerenciador, pedro)
        anterior = tarefa.data_criacao - timedelta(days=1)
        with pytest.raises(ErroDeRegra, match="anterior"):
            gerenciador.concluir(pedro, tarefa.id, momento=anterior)
        assert not gerenciador.listar_todas()[0].concluida

    def test_reabrir_devolve_para_pendente(self, gerenciador, pedro):
        tarefa = criar(gerenciador, pedro)
        gerenciador.concluir(pedro, tarefa.id)
        reaberta = gerenciador.reabrir(pedro, tarefa.id)
        assert reaberta.status == configuracao.STATUS_PENDENTE
        assert reaberta.data_conclusao is None

    def test_rn05_outro_usuario_nao_conclui(self, gerenciador, pedro, ana):
        tarefa = criar(gerenciador, pedro)
        with pytest.raises(ErroDeRegra, match="permissão"):
            gerenciador.concluir(ana, tarefa.id)


# exclusao
class TestExclusao:
    def test_exclusao_remove_a_tarefa(self, gerenciador, pedro):
        tarefa = criar(gerenciador, pedro)
        gerenciador.excluir(pedro, tarefa.id)
        assert gerenciador.listar_todas() == []

    def test_exclusao_nao_afeta_as_demais(self, gerenciador, pedro):
        a, b = criar(gerenciador, pedro, "A"), criar(gerenciador, pedro, "B")
        gerenciador.excluir(pedro, a.id)
        assert [t.id for t in gerenciador.listar_todas()] == [b.id]

    def test_rn05_outro_usuario_nao_exclui(self, gerenciador, pedro, ana):
        tarefa = criar(gerenciador, pedro)
        with pytest.raises(ErroDeRegra, match="permissão"):
            gerenciador.excluir(ana, tarefa.id)
        assert len(gerenciador.listar_todas()) == 1


# filtros e ordenacao
class TestFiltros:
    @pytest.fixture
    def povoado(self, gerenciador, pedro):
        criar(gerenciador, pedro, "Hoje", HOJE)
        criar(gerenciador, pedro, "Nesta semana", DOMINGO)
        criar(gerenciador, pedro, "Neste mês", date(2026, 9, 30))
        criar(gerenciador, pedro, "Mês que vem", date(2026, 10, 15))
        return gerenciador

    def test_filtro_hoje(self, povoado, pedro):
        assert [t.titulo for t in povoado.listar(pedro, "hoje", hoje=HOJE)] == ["Hoje"]

    def test_filtro_semana_vai_de_segunda_a_domingo(self, povoado, pedro):
        titulos = [t.titulo for t in povoado.listar(pedro, "semana", hoje=HOJE)]
        assert titulos == ["Hoje", "Nesta semana"]

    def test_filtro_mes(self, povoado, pedro):
        assert len(povoado.listar(pedro, "mes", hoje=HOJE)) == 3

    def test_filtro_todas(self, povoado, pedro):
        assert len(povoado.listar(pedro, "todas", hoje=HOJE)) == 4

    def test_limite_da_semana_e_inclusivo(self, gerenciador, pedro):
        # A segunda-feira da semana corrente ja passou, e criar tarefa em data
        # vencida seria barrado pela RN02. Como aqui o alvo do teste e o FILTRO
        # e nao a criacao, a data e ajustada direto no arquivo.
        criar(gerenciador, pedro, "Segunda", HOJE)
        criar(gerenciador, pedro, "Domingo", DOMINGO)
        criar(gerenciador, pedro, "Segunda seguinte", DOMINGO + timedelta(days=1))
        todas = gerenciador.listar_todas()
        todas[0].data_prevista = SEGUNDA
        gerenciador._gravar(todas)

        titulos = [t.titulo for t in gerenciador.listar(pedro, "semana", hoje=HOJE)]
        assert titulos == ["Segunda", "Domingo"]

    def test_ordena_por_data_e_depois_por_prioridade(self, gerenciador, pedro):
        amanha = HOJE + timedelta(days=1)
        criar(gerenciador, pedro, "Amanhã baixa", amanha, "Baixa")
        criar(gerenciador, pedro, "Hoje baixa", HOJE, "Baixa")
        criar(gerenciador, pedro, "Hoje alta", HOJE, "Alta")
        criar(gerenciador, pedro, "Hoje média", HOJE, "Média")
        titulos = [t.titulo for t in gerenciador.listar(pedro, "todas", hoje=HOJE)]
        assert titulos == ["Hoje alta", "Hoje média", "Hoje baixa", "Amanhã baixa"]

    def test_busca_ignora_acentos_e_maiusculas(self, gerenciador, pedro):
        criar(gerenciador, pedro, "Revisão de Cálculo", HOJE)
        criar(gerenciador, pedro, "Comprar pão", HOJE)
        assert len(gerenciador.listar(pedro, "todas", busca="CALCULO", hoje=HOJE)) == 1

    def test_busca_e_periodo_se_somam(self, povoado, pedro):
        assert povoado.listar(pedro, "hoje", busca="mês", hoje=HOJE) == []

    def test_rn05_cada_usuario_ve_so_as_suas(self, gerenciador, pedro, ana):
        criar(gerenciador, pedro, "Do Pedro", HOJE)
        criar(gerenciador, ana, "Da Ana", HOJE)
        assert [t.titulo for t in gerenciador.listar(pedro, "hoje", hoje=HOJE)] == ["Do Pedro"]
        assert [t.titulo for t in gerenciador.listar(ana, "hoje", hoje=HOJE)] == ["Da Ana"]

    def test_admin_com_visao_global_ve_todas(self, gerenciador, pedro, ana, admin):
        criar(gerenciador, pedro, "Do Pedro", HOJE)
        criar(gerenciador, ana, "Da Ana", HOJE)
        todas = gerenciador.listar(admin, "hoje", visao_admin=True, hoje=HOJE)
        assert len(todas) == 2

    def test_admin_sem_visao_global_ve_so_as_proprias(self, gerenciador, pedro, admin):
        criar(gerenciador, pedro, "Do Pedro", HOJE)
        assert gerenciador.listar(admin, "hoje", hoje=HOJE) == []

    def test_lista_vazia_quando_nada_bate(self, gerenciador, pedro):
        assert gerenciador.listar(pedro, "hoje", hoje=HOJE) == []


# atrasadas
class TestAtraso:
    def test_pendente_com_data_vencida_esta_atrasada(self, gerenciador, pedro):
        criar(gerenciador, pedro, "Antiga", HOJE)
        todas = gerenciador.listar_todas()
        todas[0].data_prevista = date.today() - timedelta(days=3)
        gerenciador._gravar(todas)
        assert gerenciador.listar_todas()[0].atrasada is True

    def test_concluida_nunca_conta_como_atrasada(self, gerenciador, pedro):
        tarefa = criar(gerenciador, pedro, "Antiga", HOJE)
        gerenciador.concluir(pedro, tarefa.id)
        todas = gerenciador.listar_todas()
        todas[0].data_prevista = date.today() - timedelta(days=3)
        gerenciador._gravar(todas)
        assert gerenciador.listar_todas()[0].atrasada is False


# filtro de situacao
class TestFiltroDeSituacao:
    """Acrescimo da Etapa 2: a especificacao nao previa filtrar por status."""

    @pytest.fixture
    def misturado(self, gerenciador, pedro):
        pendente = criar(gerenciador, pedro, "Pendente de hoje", HOJE)
        feita = criar(gerenciador, pedro, "Já concluída", HOJE)
        gerenciador.concluir(pedro, feita.id)
        # Coloca uma terceira no passado direto no arquivo: criar tarefa vencida
        # seria barrado pela RN02, e aqui o alvo do teste e o filtro.
        vencida = criar(gerenciador, pedro, "Venceu", HOJE)
        todas = gerenciador.listar_todas()
        for tarefa in todas:
            if tarefa.id == vencida.id:
                tarefa.data_prevista = HOJE - timedelta(days=4)
        gerenciador._gravar(todas)
        return {"pendente": pendente, "feita": feita, "vencida": vencida}

    def test_padrao_mostra_todas(self, gerenciador, misturado, pedro):
        assert len(gerenciador.listar(pedro, "todas", hoje=HOJE)) == 3

    def test_somente_pendentes(self, gerenciador, misturado, pedro):
        titulos = [t.titulo for t in gerenciador.listar(
            pedro, "todas", situacao="pendentes", hoje=HOJE)]
        assert "Já concluída" not in titulos and len(titulos) == 2

    def test_somente_concluidas(self, gerenciador, misturado, pedro):
        titulos = [t.titulo for t in gerenciador.listar(
            pedro, "todas", situacao="concluidas", hoje=HOJE)]
        assert titulos == ["Já concluída"]

    def test_somente_atrasadas(self, gerenciador, misturado, pedro):
        titulos = [t.titulo for t in gerenciador.listar(
            pedro, "todas", situacao="atrasadas", hoje=HOJE)]
        assert titulos == ["Venceu"]

    def test_atraso_acompanha_a_data_recebida(self, gerenciador, misturado, pedro):
        depois = HOJE + timedelta(days=1)
        titulos = [t.titulo for t in gerenciador.listar(
            pedro, "todas", situacao="atrasadas", hoje=depois)]
        assert set(titulos) == {"Venceu", "Pendente de hoje"}

    def test_situacao_e_periodo_se_somam(self, gerenciador, misturado, pedro):
        assert gerenciador.listar(pedro, "hoje", situacao="atrasadas", hoje=HOJE) == []

    def test_situacao_desconhecida_nao_filtra(self, gerenciador, misturado, pedro):
        assert len(gerenciador.listar(pedro, "todas", situacao="qualquer", hoje=HOJE)) == 3


# integridade
class TestIncoerencias:
    def test_arquivo_coerente_nao_acusa_nada(self, gerenciador, pedro):
        criar(gerenciador, pedro)
        assert gerenciador.incoerencias() == []

    def test_conclusao_antes_da_criacao_gravada_a_mao_e_acusada(self, gerenciador, pedro):
        tarefa = criar(gerenciador, pedro)
        todas = gerenciador.listar_todas()
        todas[0].status = configuracao.STATUS_CONCLUIDA
        todas[0].data_conclusao = todas[0].data_criacao - timedelta(days=2)
        gerenciador._gravar(todas)
        avisos = gerenciador.incoerencias()
        assert len(avisos) == 1 and ("#%d" % tarefa.id) in avisos[0]