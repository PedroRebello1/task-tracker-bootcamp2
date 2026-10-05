"""Testes do modo terminal — o que o usuário encontra na interface de texto.

As regras já têm testes próprios. Aqui o alvo é a camada de apresentação em
Textual.

A aplicação roda sem terminal (`run_test`) sobre a mesma pasta temporária que
os testes de rota usam, e é dirigida pelo `Pilot` — teclas e cliques.
"""
import asyncio
from datetime import timedelta

import pytest
from textual.widgets import Button, DataTable, Input, MaskedInput, Static, Tabs

from src import app as modulo
from src import configuracao
from src.cli.aplicacao import AplicacaoTerminal
from src.cli.boas_vindas import TelaBoasVindas
from src.cli.conta import TelaLogin
from src.cli.dialogos import ConfirmarExclusao, TarefaConcluida
from src.cli.formulario import TelaFormularioTarefa
from src.cli.painel import TelaPainel
from src.cli.relatorio import TelaRelatorio
from src.servicos import relogio
from src.servicos.validacoes import data_para_iso

TAMANHO = (120, 40)


# apoio
def rodar(corrotina):
    """Executa um fluxo assíncrono do Pilot dentro de um teste comum."""
    return asyncio.run(corrotina)


def nova_aplicacao(direto_no_cli=False, avisos=()):
    return AplicacaoTerminal(modulo.usuarios, modulo.tarefas, avisos, direto_no_cli=direto_no_cli)


def texto(widget):
    """O conteúdo visível de um Static, sem marcação."""
    return str(widget.visual.plain if hasattr(widget.visual, "plain") else widget.visual)


async def entrar(pilot, login="pedro@x.com", senha="senha123"):
    """Do login até o painel, como `entrar` faz nos testes de rota."""
    tela = pilot.app.screen
    assert isinstance(tela, TelaLogin)
    tela.query_one("#login", Input).value = login
    tela.query_one("#senha", Input).value = senha
    await pilot.click("#entrar")
    await pilot.pause()
    assert isinstance(pilot.app.screen, TelaPainel)


async def preencher_e_salvar(pilot, titulo, dias=0, prioridade="Média"):
    tela = pilot.app.screen
    assert isinstance(tela, TelaFormularioTarefa)
    tela.query_one("#titulo", Input).value = titulo
    tela.query_one("#data", MaskedInput).value = (relogio.hoje() + timedelta(days=dias)).strftime("%d/%m/%Y")
    tela.query_one("#prioridade").value = prioridade
    await pilot.click("#salvar")
    await pilot.pause()


def titulos_na_tabela(pilot):
    return [tarefa.titulo for tarefa in pilot.app.screen._linhas]


@pytest.fixture(autouse=True)
def sem_animacao_de_clique(monkeypatch):
    """Um botão recém-clicado ignora cliques por 0,2 s; o teste não espera isso."""
    original = Button.__init__

    def sem_efeito(botao, *args, **kwargs):
        original(botao, *args, **kwargs)
        botao.active_effect_duration = 0

    monkeypatch.setattr(Button, "__init__", sem_efeito)


@pytest.fixture
def preparado(pasta):
    """Disco temporário já com o administrador padrão e uma conta comum."""
    modulo.preparar()
    modulo.usuarios.cadastrar("Pedro Rebello", "pedro@x.com", "senha123")
    modulo.usuarios.cadastrar("Ana", "ana@x.com", "senha123")
    return pasta


# tela de escolha
class TestTelaInicial:
    def test_abre_com_as_duas_opcoes(self, preparado):
        async def fluxo():
            app = nova_aplicacao()
            async with app.run_test(size=TAMANHO) as pilot:
                await pilot.pause()
                assert isinstance(app.screen, TelaBoasVindas)
                rotulos = [str(botao.label) for botao in app.screen.query(Button)]
                assert any("terminal" in rotulo for rotulo in rotulos)
                assert any("web app" in rotulo for rotulo in rotulos)
        rodar(fluxo())

    def test_escolher_web_encerra_pedindo_o_flask(self, preparado):
        async def fluxo():
            app = nova_aplicacao()
            async with app.run_test(size=TAMANHO) as pilot:
                await pilot.pause()
                await pilot.click("#web")
                await pilot.pause()
            return app.return_value
        assert rodar(fluxo()) == "web"

    def test_atalho_de_teclado_tambem_escolhe_web(self, preparado):
        async def fluxo():
            app = nova_aplicacao()
            async with app.run_test(size=TAMANHO) as pilot:
                await pilot.pause()
                await pilot.press("2")
                await pilot.pause()
            return app.return_value
        assert rodar(fluxo()) == "web"

    def test_escolher_terminal_leva_ao_login(self, preparado):
        async def fluxo():
            app = nova_aplicacao(avisos=["Administrador padrão criado: x / y"])
            async with app.run_test(size=TAMANHO) as pilot:
                await pilot.pause()
                await pilot.click("#terminal")
                await pilot.pause()
                assert isinstance(app.screen, TelaLogin)
                # Os avisos que a web imprime no terminal aparecem na tela.
                assert "Administrador padrão criado" in texto(app.screen.query_one("#avisos", Static))
                # Voltar do login devolve à tela de escolha.
                await pilot.press("escape")
                await pilot.pause()
                assert isinstance(app.screen, TelaBoasVindas)
        rodar(fluxo())

    def test_modo_cli_direto_pula_a_escolha_e_voltar_fecha(self, preparado):
        async def fluxo():
            app = nova_aplicacao(direto_no_cli=True)
            async with app.run_test(size=TAMANHO) as pilot:
                await pilot.pause()
                assert isinstance(app.screen, TelaLogin)
                await pilot.click("#voltar")
                await pilot.pause()
            return app.return_value
        assert rodar(fluxo()) is None


# Passo 1
class TestLoginECadastro:
    def test_login_certo_abre_o_painel_com_o_nome(self, preparado):
        async def fluxo():
            app = nova_aplicacao(direto_no_cli=True)
            async with app.run_test(size=TAMANHO) as pilot:
                await pilot.pause()
                await entrar(pilot)
                assert app.usuario.login == "pedro@x.com"
                cabecalho = texto(app.screen.query_one("#cabecalho", Static))
                assert "Minhas tarefas" in cabecalho
                assert "Pedro Rebello" in cabecalho
        rodar(fluxo())

    def test_senha_errada_mostra_a_mensagem_generica(self, preparado):
        async def fluxo():
            app = nova_aplicacao(direto_no_cli=True)
            async with app.run_test(size=TAMANHO) as pilot:
                await pilot.pause()
                app.screen.query_one("#login", Input).value = "pedro@x.com"
                app.screen.query_one("#senha", Input).value = "errada"
                await pilot.press("enter")
                await pilot.pause()
                assert isinstance(app.screen, TelaLogin)
                assert texto(app.screen.query_one("#mensagem", Static)) == "E-mail ou senha inválidos."
                assert app.screen.query_one("#senha", Input).value == ""
        rodar(fluxo())

    def test_bloqueio_apos_tres_falhas_desliga_o_botao(self, preparado):
        async def fluxo():
            app = nova_aplicacao(direto_no_cli=True)
            async with app.run_test(size=TAMANHO) as pilot:
                await pilot.pause()
                for _ in range(configuracao.MAXIMO_TENTATIVAS_LOGIN):
                    app.screen.query_one("#login", Input).value = "pedro@x.com"
                    app.screen.query_one("#senha", Input).value = "errada"
                    await pilot.click("#entrar")
                    await pilot.pause()
                botao = app.screen.query_one("#entrar", Button)
                assert botao.disabled
                assert "Bloqueado por" in str(botao.label)
                # Com o botao desligado, nem a senha certa entra.
                app.screen.query_one("#senha", Input).value = "senha123"
                app.screen.query_one("#senha", Input).focus()
                await pilot.press("enter")
                await pilot.pause()
                assert isinstance(app.screen, TelaLogin)
        rodar(fluxo())

    def test_cadastro_cria_conta_comum_e_volta_com_o_email(self, preparado):
        async def fluxo():
            app = nova_aplicacao(direto_no_cli=True)
            async with app.run_test(size=TAMANHO) as pilot:
                await pilot.pause()
                await pilot.click("#cadastro")
                await pilot.pause()
                app.screen.query_one("#nome", Input).value = "Novo"
                app.screen.query_one("#login", Input).value = "novo@x.com"
                app.screen.query_one("#senha", Input).value = "123"
                await pilot.click("#criar")
                await pilot.pause()
                assert "pelo menos" in texto(app.screen.query_one("#mensagem", Static))
                app.screen.query_one("#senha", Input).value = "senha123"
                await pilot.click("#criar")
                await pilot.pause()
                assert isinstance(app.screen, TelaLogin)
                assert app.screen.query_one("#login", Input).value == "novo@x.com"
            assert not modulo.usuarios.buscar_por_login("novo@x.com").eh_admin
        rodar(fluxo())

    def test_sair_da_conta_volta_ao_login(self, preparado):
        async def fluxo():
            app = nova_aplicacao(direto_no_cli=True)
            async with app.run_test(size=TAMANHO) as pilot:
                await pilot.pause()
                await entrar(pilot)
                await pilot.click("#sair")
                await pilot.pause()
                assert isinstance(app.screen, TelaLogin)
                assert app.usuario is None
        rodar(fluxo())


# Passos 2 a 6
class TestTarefas:
    def test_painel_vazio_tem_mensagem_clara(self, preparado):
        async def fluxo():
            app = nova_aplicacao(direto_no_cli=True)
            async with app.run_test(size=TAMANHO) as pilot:
                await pilot.pause()
                await entrar(pilot)
                vazio = app.screen.query_one("#vazio", Static)
                assert vazio.display
                assert "Nenhuma tarefa encontrada" in texto(vazio)
                assert not app.screen.query_one("#tabela", DataTable).display
        rodar(fluxo())

    def test_formulario_reexibe_os_erros_das_regras(self, preparado):
        """RN01 e RN02 chegam ao formulário com as mesmas mensagens da web."""
        async def fluxo():
            app = nova_aplicacao(direto_no_cli=True)
            async with app.run_test(size=TAMANHO) as pilot:
                await pilot.pause()
                await entrar(pilot)
                await pilot.press("n")
                await pilot.pause()
                assert isinstance(app.screen, TelaFormularioTarefa)
                await preencher_e_salvar(pilot, "   ", dias=-1)
                erros = texto(app.screen.query_one("#erros", Static))
                assert "Informe um título" in erros
                assert "não pode ser anterior a hoje" in erros
                assert isinstance(app.screen, TelaFormularioTarefa)
            assert modulo.tarefas.listar_todas() == []
        rodar(fluxo())

    def test_criar_tarefa_grava_no_disco_e_aparece_na_tabela(self, preparado):
        async def fluxo():
            app = nova_aplicacao(direto_no_cli=True)
            async with app.run_test(size=TAMANHO) as pilot:
                await pilot.pause()
                await entrar(pilot)
                await pilot.click("#nova")
                await pilot.pause()
                await preencher_e_salvar(pilot, "Estudar", prioridade="Alta")
                assert isinstance(app.screen, TelaPainel)
                assert titulos_na_tabela(pilot) == ["Estudar"]
                assert "1 tarefa neste recorte" in texto(app.screen.query_one("#cabecalho", Static))
            gravada = modulo.tarefas.listar_todas()[0]
            assert gravada.prioridade == "Alta"
            assert gravada.usuario_id == modulo.usuarios.buscar_por_login("pedro@x.com").id
        rodar(fluxo())

    def test_data_com_mascara_vira_iso_para_o_servico(self):
        assert data_para_iso("05/10/2026") == "2026-10-05"
        assert data_para_iso(" 01/02/2026 ") == "2026-02-01"
        # Texto incompleto segue como está e é recusado por converter_data.
        assert data_para_iso("05/10/2") == "05/10/2"
        assert data_para_iso("") == ""

    def test_concluir_e_reabrir(self, preparado):
        async def fluxo():
            app = nova_aplicacao(direto_no_cli=True)
            async with app.run_test(size=TAMANHO) as pilot:
                await pilot.pause()
                await entrar(pilot)
                await pilot.press("n")
                await pilot.pause()
                await preencher_e_salvar(pilot, "Estudar")
                await pilot.press("c")
                await pilot.pause()
                assert modulo.tarefas.listar_todas()[0].concluida
                assert app.screen.query_one("#concluir", Button).disabled
                await pilot.press("r")
                await pilot.pause()
                assert not modulo.tarefas.listar_todas()[0].concluida
                assert app.screen.query_one("#reabrir", Button).disabled
        rodar(fluxo())

    def test_rn04_editar_concluida_mostra_a_tela_de_reabrir(self, preparado):
        async def fluxo():
            app = nova_aplicacao(direto_no_cli=True)
            async with app.run_test(size=TAMANHO) as pilot:
                await pilot.pause()
                await entrar(pilot)
                await pilot.press("n")
                await pilot.pause()
                await preencher_e_salvar(pilot, "Estudar")
                await pilot.press("c")
                await pilot.pause()
                await pilot.press("e")
                await pilot.pause()
                assert isinstance(app.screen, TarefaConcluida)
                await pilot.click("#voltar")
                await pilot.pause()
                assert isinstance(app.screen, TelaPainel)
                assert modulo.tarefas.listar_todas()[0].concluida
                # "Reabrir e editar" reabre e ja abre o formulario.
                await pilot.press("e")
                await pilot.pause()
                await pilot.click("#reabrir")
                await pilot.pause()
                assert isinstance(app.screen, TelaFormularioTarefa)
                assert app.screen.modo == "editar"
                assert not modulo.tarefas.listar_todas()[0].concluida
        rodar(fluxo())

    def test_editar_altera_a_tarefa(self, preparado):
        async def fluxo():
            app = nova_aplicacao(direto_no_cli=True)
            async with app.run_test(size=TAMANHO) as pilot:
                await pilot.pause()
                await entrar(pilot)
                await pilot.press("n")
                await pilot.pause()
                await preencher_e_salvar(pilot, "Estudar")
                await pilot.press("e")
                await pilot.pause()
                assert isinstance(app.screen, TelaFormularioTarefa)
                assert app.screen.query_one("#titulo", Input).value == "Estudar"
                await preencher_e_salvar(pilot, "Estudar mais", dias=1, prioridade="Baixa")
                assert isinstance(app.screen, TelaPainel)
            gravada = modulo.tarefas.listar_todas()[0]
            assert gravada.titulo == "Estudar mais"
            assert gravada.prioridade == "Baixa"
            assert gravada.data_prevista == relogio.hoje() + timedelta(days=1)
        rodar(fluxo())

    def test_rn06_excluir_pede_confirmacao_e_cancelar_preserva(self, preparado):
        async def fluxo():
            app = nova_aplicacao(direto_no_cli=True)
            async with app.run_test(size=TAMANHO) as pilot:
                await pilot.pause()
                await entrar(pilot)
                await pilot.press("n")
                await pilot.pause()
                await preencher_e_salvar(pilot, "Estudar")
                await pilot.press("x")
                await pilot.pause()
                assert isinstance(app.screen, ConfirmarExclusao)
                # Enter no foco padrao cancela: dois toques seguidos nao apagam.
                await pilot.press("enter")
                await pilot.pause()
                assert isinstance(app.screen, TelaPainel)
                assert len(modulo.tarefas.listar_todas()) == 1
                await pilot.press("x")
                await pilot.pause()
                await pilot.click("#confirmar")
                await pilot.pause()
                assert modulo.tarefas.listar_todas() == []
                assert app.screen.query_one("#vazio", Static).display
        rodar(fluxo())


# Passos 7 e 8
class TestFiltrosERelatorio:
    async def _tres_tarefas(self, pilot):
        await pilot.press("n")
        await pilot.pause()
        await preencher_e_salvar(pilot, "Hoje A")
        await pilot.press("n")
        await pilot.pause()
        await preencher_e_salvar(pilot, "Hoje B")
        await pilot.press("n")
        await pilot.pause()
        await preencher_e_salvar(pilot, "Daqui a um mês", dias=40)

    def test_periodo_situacao_e_busca(self, preparado):
        async def fluxo():
            app = nova_aplicacao(direto_no_cli=True)
            async with app.run_test(size=TAMANHO) as pilot:
                await pilot.pause()
                await entrar(pilot)
                await self._tres_tarefas(pilot)
                assert titulos_na_tabela(pilot) == ["Hoje A", "Hoje B"]

                app.screen.query_one("#periodo", Tabs).active = "periodo-todas"
                await pilot.pause()
                assert titulos_na_tabela(pilot) == ["Hoje A", "Hoje B", "Daqui a um mês"]

                await pilot.press("c")            # conclui a primeira
                await pilot.pause()
                app.screen.query_one("#situacao", Tabs).active = "situacao-pendentes"
                await pilot.pause()
                assert titulos_na_tabela(pilot) == ["Hoje B", "Daqui a um mês"]
                # O resumo conta o periodo inteiro, nao so a situacao filtrada.
                assert "3" in texto(app.screen.query_one("#numero-todas", Static))

                app.screen.query_one("#busca", Input).value = "MES"   # sem acento, maiusculas
                await pilot.pause()
                assert titulos_na_tabela(pilot) == ["Daqui a um mês"]

                app.screen.query_one("#busca", Input).value = "nada"
                await pilot.pause()
                assert "“nada”" in texto(app.screen.query_one("#vazio", Static))

                # Clicar num numero do resumo e atalho para a situacao correspondente.
                app.screen.query_one("#busca", Input).value = ""
                await pilot.click("#numero-concluidas")
                await pilot.pause()
                assert app.filtros["situacao"] == "concluidas"
                assert titulos_na_tabela(pilot) == ["Hoje A"]
        rodar(fluxo())

    def test_relatorio_no_mesmo_recorte(self, preparado):
        async def fluxo():
            app = nova_aplicacao(direto_no_cli=True)
            async with app.run_test(size=TAMANHO) as pilot:
                await pilot.pause()
                await entrar(pilot)
                await self._tres_tarefas(pilot)
                await pilot.press("c")
                await pilot.pause()
                await pilot.press("l")
                await pilot.pause()
                assert isinstance(app.screen, TelaRelatorio)
                assert "50.0%" in texto(app.screen.query_one("#rotulo-progresso", Static))
                assert "1 de 2 concluídas" in texto(app.screen.query_one("#ajuda-progresso", Static))
                assert "Média" in texto(app.screen.query_one("#por-prioridade", Static))
                # Trocar o periodo aqui vale ao voltar para o painel.
                app.screen.query_one("#periodo", Tabs).active = "periodo-todas"
                await pilot.pause()
                assert "33.3%" in texto(app.screen.query_one("#rotulo-progresso", Static))
                await pilot.press("escape")
                await pilot.pause()
                assert isinstance(app.screen, TelaPainel)
                assert app.filtros["periodo"] == "todas"
                assert len(titulos_na_tabela(pilot)) == 3
        rodar(fluxo())

    def test_relatorio_vazio(self, preparado):
        async def fluxo():
            app = nova_aplicacao(direto_no_cli=True)
            async with app.run_test(size=TAMANHO) as pilot:
                await pilot.pause()
                await entrar(pilot)
                await pilot.press("l")
                await pilot.pause()
                vazio = app.screen.query_one("#vazio", Static)
                assert vazio.display
                assert "Não há dados suficientes" in texto(vazio)
        rodar(fluxo())


# Passo 9
class TestRN05VisaoAdministrativa:
    def test_usuario_comum_nao_entra_na_administracao(self, preparado):
        async def fluxo():
            app = nova_aplicacao(direto_no_cli=True)
            async with app.run_test(size=TAMANHO) as pilot:
                await pilot.pause()
                await entrar(pilot)
                assert not app.screen.query_one("#admin", Button).display
                assert "a" not in app.screen.active_bindings
                # Mesmo chamando a acao por fora, o servico recusa (RN05).
                app.screen.action_admin()
                await pilot.pause()
                assert not app.visao_admin
        rodar(fluxo())

    def test_admin_ve_as_tarefas_de_todos_com_o_dono(self, preparado):
        pedro = modulo.usuarios.buscar_por_login("pedro@x.com")
        ana = modulo.usuarios.buscar_por_login("ana@x.com")
        hoje = relogio.hoje().isoformat()
        modulo.tarefas.criar(pedro, "De Pedro", "", hoje, "Alta", "Estudo")
        modulo.tarefas.criar(ana, "De Ana", "", hoje, "Baixa", "Geral")

        async def fluxo():
            app = nova_aplicacao(direto_no_cli=True)
            async with app.run_test(size=TAMANHO) as pilot:
                await pilot.pause()
                await entrar(pilot, configuracao.ADMIN_PADRAO_LOGIN, configuracao.ADMIN_PADRAO_SENHA)
                assert titulos_na_tabela(pilot) == []          # o admin nao tem tarefas proprias
                await pilot.press("a")
                await pilot.pause()
                assert app.visao_admin
                assert app.filtros["periodo"] == "todas"
                assert sorted(titulos_na_tabela(pilot)) == ["De Ana", "De Pedro"]
                colunas = [str(coluna.label) for coluna in app.screen.query_one("#tabela", DataTable).columns.values()]
                assert "Dono" in colunas
                assert "Administração" in texto(app.screen.query_one("#cabecalho", Static))
                # O relatorio da visao administrativa tambem enxerga todos.
                await pilot.press("l")
                await pilot.pause()
                assert "todos os usuários" in texto(app.screen.query_one("#cabecalho", Static))
                await pilot.press("escape")
                await pilot.pause()
                # Voltar ao "Meu painel" recomeça do recorte padrao.
                await pilot.press("a")
                await pilot.pause()
                assert not app.visao_admin
                assert app.filtros["periodo"] == configuracao.PERIODO_PADRAO
                assert titulos_na_tabela(pilot) == []
        rodar(fluxo())


# ponto de entrada
class TestModoDeExecucao:
    def test_sem_argumento_e_com_terminal_pergunta(self):
        assert modulo._modo_de_execucao([], interativo=True) == "escolher"

    def test_sem_terminal_sobe_o_web_app_como_sempre(self):
        assert modulo._modo_de_execucao([], interativo=False) == "web"

    def test_opcoes_pulam_a_pergunta(self):
        assert modulo._modo_de_execucao(["--web"], interativo=True) == "web"
        assert modulo._modo_de_execucao(["--cli"], interativo=False) == "cli"
        assert modulo._modo_de_execucao(["--menu"], interativo=True) == "menu"

    def test_opcoes_sao_excludentes(self):
        with pytest.raises(SystemExit):
            modulo._modo_de_execucao(["--web", "--cli"])
        with pytest.raises(SystemExit):
            modulo._modo_de_execucao(["--menu", "--web"])

    def test_processo_filho_do_recarregador_nao_pergunta(self, monkeypatch):
        monkeypatch.setenv("WERKZEUG_RUN_MAIN", "true")
        assert modulo._modo_de_execucao([], interativo=True) == "web"

    def test_endereco_para_o_navegador_nunca_e_0000(self, monkeypatch):
        monkeypatch.setattr(configuracao, "HOST", "0.0.0.0")
        assert modulo._endereco_do_servidor() == "http://127.0.0.1:%d" % configuracao.PORTA
