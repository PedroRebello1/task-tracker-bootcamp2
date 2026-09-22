"""Testa as sete regras de negocio, uma a uma e de forma isolada.

Nenhum teste aqui precisa de servidor, navegador ou arquivo em disco, as regras
vivem em src/servicos/validacoes.py justamente para poderem ser testadas assim.
"""
from datetime import date, datetime, timedelta

import pytest

from src import configuracao
from src.modelos.tarefa import Tarefa
from src.modelos.usuario import Usuario
from src.servicos import validacoes

HOJE = date(2026, 9, 22)


def nova_tarefa(**ajustes):
    padrao = dict(id=1, titulo="Estudar", data_prevista=HOJE, prioridade="Alta",
                  usuario_id=1, data_criacao=datetime(2026, 9, 22, 9, 0))
    padrao.update(ajustes)
    return Tarefa(**padrao)


# RN01
class TestRN01TituloObrigatorio:
    def test_titulo_vazio_e_recusado(self):
        assert validacoes.validar_titulo("") == "Informe um título para a tarefa."

    def test_titulo_so_com_espacos_e_recusado(self):
        assert validacoes.validar_titulo("   ") == "Informe um título para a tarefa."

    def test_titulo_nulo_e_recusado(self):
        assert validacoes.validar_titulo(None) is not None

    def test_titulo_valido_passa(self):
        assert validacoes.validar_titulo("Entregar relatório") is None

    def test_titulo_acima_de_60_caracteres_e_recusado(self):
        erro = validacoes.validar_titulo("a" * 61)
        assert "60 caracteres" in erro

    def test_titulo_com_exatamente_60_caracteres_passa(self):
        assert validacoes.validar_titulo("a" * 60) is None


# RN02
class TestRN02DataNaoRetroativa:
    def test_data_de_ontem_e_recusada(self):
        erro = validacoes.validar_data_prevista(HOJE - timedelta(days=1), hoje=HOJE)
        assert erro == "A data prevista não pode ser anterior a hoje (22/09/2026)."

    def test_data_de_hoje_passa(self):
        assert validacoes.validar_data_prevista(HOJE, hoje=HOJE) is None

    def test_data_futura_passa(self):
        assert validacoes.validar_data_prevista(HOJE + timedelta(days=5), hoje=HOJE) is None

    def test_na_edicao_manter_data_passada_e_permitido(self):
        """Tarefa que ficou para tras continua editavel mantendo a propria data."""
        antiga = HOJE - timedelta(days=10)
        assert validacoes.validar_data_prevista(antiga, data_anterior=antiga, hoje=HOJE) is None

    def test_na_edicao_trocar_por_outra_data_passada_e_recusado(self):
        antiga = HOJE - timedelta(days=10)
        outra = HOJE - timedelta(days=3)
        assert validacoes.validar_data_prevista(outra, data_anterior=antiga, hoje=HOJE) is not None

    def test_data_mal_formatada_e_recusada(self):
        _, erro = validacoes.converter_data("31/02/2026")
        assert erro == "Selecione uma data válida no calendário."

    def test_data_inexistente_no_calendario_e_recusada(self):
        _, erro = validacoes.converter_data("2026-02-31")
        assert erro is not None

    def test_data_vazia_e_recusada(self):
        _, erro = validacoes.converter_data("")
        assert erro is not None

    def test_data_iso_valida_e_convertida(self):
        data, erro = validacoes.converter_data("2026-09-28")
        assert erro is None and data == date(2026, 9, 28)


# RN03
class TestRN03ListasFechadas:
    @pytest.mark.parametrize("valor", configuracao.PRIORIDADES)
    def test_prioridades_validas_passam(self, valor):
        assert validacoes.validar_prioridade(valor) is None

    def test_prioridade_fora_da_lista_e_recusada(self):
        erro = validacoes.validar_prioridade("urgentíssima")
        assert erro == "Prioridade inválida. Os valores aceitos são Alta, Média ou Baixa."

    def test_prioridade_com_caixa_diferente_e_recusada(self):
        assert validacoes.validar_prioridade("alta") is not None

    @pytest.mark.parametrize("valor", configuracao.CATEGORIAS)
    def test_categorias_validas_passam(self, valor):
        assert validacoes.validar_categoria(valor) is None

    def test_categoria_fora_da_lista_e_recusada(self):
        assert validacoes.validar_categoria("Academia") is not None


# RN04
class TestRN04ConcluidaNaoEdita:
    def test_tarefa_concluida_nao_pode_ser_editada(self):
        tarefa = nova_tarefa(status=configuracao.STATUS_CONCLUIDA)
        erro = validacoes.validar_edicao_permitida(tarefa)
        assert erro == "Esta tarefa está concluída. Reabra-a para poder editar."

    def test_tarefa_pendente_pode_ser_editada(self):
        assert validacoes.validar_edicao_permitida(nova_tarefa()) is None


# RN05
class TestRN05Isolamento:
    def test_dono_acessa_a_propria_tarefa(self):
        dono = Usuario(id=1, nome="Pedro", login="p@x.com", senha_hash="x")
        assert validacoes.validar_permissao(nova_tarefa(usuario_id=1), dono) is None

    def test_outro_usuario_nao_acessa(self):
        ana = Usuario(id=2, nome="Ana", login="a@x.com", senha_hash="x")
        erro = validacoes.validar_permissao(nova_tarefa(usuario_id=1), ana)
        assert erro == "Você não tem permissão para acessar esta tarefa."

    def test_admin_acessa_tarefa_de_qualquer_um(self):
        admin = Usuario(id=9, nome="Admin", login="admin@x.com", senha_hash="x",
                        perfil=configuracao.PERFIL_ADMIN)
        assert validacoes.validar_permissao(nova_tarefa(usuario_id=1), admin) is None

    def test_visao_administrativa_e_restrita(self):
        comum = Usuario(id=2, nome="Ana", login="a@x.com", senha_hash="x")
        assert validacoes.validar_acesso_administrativo(comum) == "Acesso restrito ao administrador."

    def test_admin_acessa_a_visao_administrativa(self):
        admin = Usuario(id=9, nome="Admin", login="admin@x.com", senha_hash="x",
                        perfil=configuracao.PERFIL_ADMIN)
        assert validacoes.validar_acesso_administrativo(admin) is None


# RN07
class TestRN07ConclusaoDepoisDaCriacao:
    def test_conclusao_anterior_a_criacao_e_recusada(self):
        tarefa = nova_tarefa(data_criacao=datetime(2026, 9, 22, 10, 0))
        erro = validacoes.validar_conclusao(tarefa, momento=datetime(2026, 9, 21, 23, 0))
        assert "anterior" in erro

    def test_conclusao_posterior_a_criacao_passa(self):
        tarefa = nova_tarefa(data_criacao=datetime(2026, 9, 22, 10, 0))
        assert validacoes.validar_conclusao(tarefa, momento=datetime(2026, 9, 22, 11, 0)) is None

    def test_conclusao_no_mesmo_instante_passa(self):
        momento = datetime(2026, 9, 22, 10, 0)
        assert validacoes.validar_conclusao(nova_tarefa(data_criacao=momento), momento) is None


# dados de conta
class TestValidacaoDeConta:
    @pytest.mark.parametrize("email", ["", "semarroba.com", "a@b", "com espaco@x.com",
                                       "dois@@x.com", "a@x."])
    def test_emails_invalidos(self, email):
        assert validacoes.validar_email(email) is not None

    def test_email_valido(self):
        assert validacoes.validar_email("pedro.rebello@sempreceub.com") is None

    def test_senha_curta_e_recusada(self):
        assert validacoes.validar_senha("12345") == "A senha deve ter pelo menos 6 caracteres."

    def test_senha_com_seis_caracteres_passa(self):
        assert validacoes.validar_senha("123456") is None


# agregador
class TestAgregador:
    def test_acumula_varios_erros_de_uma_vez(self):
        erros = validacoes.validar_dados_da_tarefa(
            titulo="", descricao="", data_prevista=HOJE - timedelta(days=1),
            prioridade="urgente", categoria="Academia", hoje=HOJE)
        assert len(erros) == 4

    def test_dados_corretos_nao_geram_erro(self):
        erros = validacoes.validar_dados_da_tarefa(
            titulo="Estudar", descricao="", data_prevista=HOJE,
            prioridade="Alta", categoria="Estudo", hoje=HOJE)
        assert erros == []


# categoria opcional
class TestCategoriaOpcional:
    """A Etapa 1 marca categoria como nao obrigatoria, com 'Geral' de padrao."""

    @pytest.mark.parametrize("vazio", [None, "", "   "])
    def test_categoria_vazia_vira_o_padrao(self, vazio):
        assert validacoes.normalizar_categoria(vazio) == configuracao.CATEGORIA_PADRAO

    def test_categoria_informada_e_preservada(self):
        assert validacoes.normalizar_categoria(" Saúde ") == "Saúde"

    def test_agregador_aceita_tarefa_sem_categoria(self):
        erros = validacoes.validar_dados_da_tarefa(
            titulo="Estudar", descricao="", data_prevista=HOJE,
            prioridade="Alta", categoria="", hoje=HOJE)
        assert erros == []

    def test_prioridade_continua_obrigatoria(self):
        """Categoria e opcional; prioridade nao e - a especificacao separa as duas."""
        assert validacoes.validar_prioridade("") is not None


# RN07 aplicada ao que ja esta no arquivo
class TestCoerenciaTemporalGravada:
    def test_tarefa_coerente_nao_gera_aviso(self):
        tarefa = nova_tarefa(data_criacao=datetime(2026, 9, 22, 9, 0),
                             data_conclusao=datetime(2026, 9, 22, 18, 0))
        assert validacoes.validar_coerencia_temporal(tarefa) is None

    def test_tarefa_pendente_nao_gera_aviso(self):
        assert validacoes.validar_coerencia_temporal(nova_tarefa()) is None

    def test_conclusao_anterior_a_criacao_e_sinalizada(self):
        tarefa = nova_tarefa(id=7, data_criacao=datetime(2026, 9, 22, 9, 0),
                             data_conclusao=datetime(2026, 9, 21, 9, 0))
        aviso = validacoes.validar_coerencia_temporal(tarefa)
        assert aviso is not None and "#7" in aviso