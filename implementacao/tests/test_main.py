"""Testa o menu numerado (src/main.py), dirigido por respostas digitadas simuladas.

Cada teste roda o menu inteiro, do login a saida, sobre a pasta de dados
temporaria do conftest. As respostas acabam -> EOFError -> o menu encerra,
exatamente como um Ctrl+D no terminal.

Depois de uma lista com tarefas, o menu pergunta o numero de uma delas: por
isso as respostas trazem um ENTER (voltar) antes do "3" que encerra.
"""
from datetime import date, timedelta

import pytest

from src import app as modulo
from src import configuracao
from src import main
from src.servicos import relogio

ADMIN = configuracao.ADMIN_PADRAO_LOGIN
SENHA_ADMIN = configuracao.ADMIN_PADRAO_SENHA

# Enter vazio: na pergunta do numero da tarefa, volta ao menu; na edicao, mantem o campo.
ENTER = ""


@pytest.fixture
def preparado(pasta):
    main.preparar(modulo.usuarios, modulo.tarefas)
    return pasta


def daqui_a(dias):
    return (relogio.hoje() + timedelta(days=dias)).strftime("%d/%m/%Y")


def rodar(*respostas, senhas=(SENHA_ADMIN,)):
    """Roda o menu com as respostas dadas. Devolve (codigo, texto exibido)."""
    fila = list(respostas)
    fila_senhas = list(senhas)
    linhas = []

    def entrada(rotulo):
        if not fila:
            raise EOFError
        valor = fila.pop(0)
        if callable(valor):
            # Outra interface mexe nos arquivos entre duas perguntas.
            valor = valor()
        linhas.append(rotulo + valor)
        return valor

    def ler_senha(rotulo):
        linhas.append(rotulo)
        return fila_senhas.pop(0)

    menu = main.MenuNumerado(modulo.usuarios, modulo.tarefas, entrada=entrada,
                             saida=linhas.append, ler_senha=ler_senha)
    codigo = menu.executar()
    return codigo, "\n".join(linhas)


def cadastro(titulo="Estudar Python", descricao="Revisar listas", prioridade="Alta",
             categoria="", data=None):
    """As respostas de um cadastro valido, na ordem em que o menu pergunta."""
    return ["1", titulo, descricao, prioridade, categoria, data or daqui_a(10)]


def na_tarefa(numero, acao, lista="2"):
    """Abre a lista, escolhe a tarefa pelo numero e a acao no menu dela."""
    return [lista, str(numero), acao]


def edicao(titulo=ENTER, descricao=ENTER, prioridade=ENTER, categoria=ENTER, data=ENTER):
    """As respostas da edicao, na ordem das perguntas. Por padrao, Enter em tudo."""
    return [titulo, descricao, prioridade, categoria, data]


def gravadas():
    return modulo.tarefas.listar_todas()


def o_admin():
    return modulo.usuarios.buscar_por_login(ADMIN)


def tarefa_de(usuario, titulo="Estudar Python", descricao="Revisar listas", data=None,
              hoje=None, momento=None):
    """Cria direto pelo servico: o cadastro pelo menu tem testes proprios."""
    data = data or relogio.hoje() + timedelta(days=10)
    tarefa, erros = modulo.tarefas.criar(usuario, titulo, descricao, data.isoformat(),
                                         "Alta", "Estudo", hoje=hoje, momento=momento)
    assert erros == []
    return tarefa


def conta_comum(nome="Ana", login="ana@x.com"):
    usuario, erros = modulo.usuarios.cadastrar(nome, login, "senha123")
    assert erros == []
    return usuario


# menu e loop
class TestMenu:
    def test_mostra_as_tres_opcoes_do_enunciado(self, preparado):
        _, texto = rodar(ADMIN, "3")
        assert "1. Cadastrar nova tarefa" in texto
        assert "2. Visualizar tarefas cadastradas" in texto
        assert "3. Sair da aplicação" in texto

    def test_opcao_3_encerra(self, preparado):
        codigo, texto = rodar(ADMIN, "3")
        assert codigo == 0
        assert texto.endswith("Encerrando a aplicação. Até logo.")

    def test_opcao_invalida_avisa_e_o_loop_continua(self, preparado):
        conta_comum()
        _, texto = rodar("ana@x.com", "9", "abc", "2", "3", senhas=("senha123",))
        assert texto.count("Opção inválida. Escolha 1, 2 ou 3.") == 2
        assert "Nenhuma tarefa cadastrada no momento." in texto

    def test_para_o_admin_a_opcao_invalida_lista_tambem_a_4(self, preparado):
        _, texto = rodar(ADMIN, "9", "3")
        assert "Opção inválida. Escolha 1, 2, 3 ou 4." in texto

    def test_fim_da_entrada_no_meio_do_cadastro_encerra_sem_erro(self, preparado):
        codigo, texto = rodar(ADMIN, "1", "Estudar")
        assert codigo == 0
        assert "Até logo." in texto
        assert gravadas() == []

    def test_ctrl_c_encerra_sem_erro(self, preparado):
        def interromper(_rotulo):
            raise KeyboardInterrupt
        menu = main.MenuNumerado(modulo.usuarios, modulo.tarefas,
                                 entrada=interromper, saida=lambda _texto: None)
        assert menu.executar() == 0


# Passo 1
class TestEntrar:
    def test_senha_errada_avisa_e_pergunta_de_novo(self, preparado):
        _, texto = rodar(ADMIN, ADMIN, "3", senhas=("errada", SENHA_ADMIN))
        assert "E-mail ou senha inválidos." in texto
        assert "Olá, Administrador!" in texto

    def test_tres_falhas_seguidas_bloqueiam_o_login(self, preparado):
        _, texto = rodar(ADMIN, ADMIN, ADMIN, ADMIN, senhas=("x",) * 3 + (SENHA_ADMIN,))
        assert "Muitas tentativas seguidas" in texto
        assert "Olá" not in texto

    def test_criar_conta_e_entrar_com_ela(self, preparado):
        _, texto = rodar(main.CRIAR_CONTA, "Ana", "ana@x.com", "ana@x.com", "3",
                         senhas=("senha123", "senha123"))
        assert "Conta criada." in texto
        assert "Olá, Ana!" in texto
        ana = modulo.usuarios.buscar_por_login("ana@x.com")
        assert ana.perfil == configuracao.PERFIL_COMUM

    def test_conta_invalida_nao_e_criada(self, preparado):
        _, texto = rodar(main.CRIAR_CONTA, "Ana", "ana@x.com", senhas=("123",))
        assert "A senha deve ter pelo menos 6 caracteres." in texto
        assert modulo.usuarios.buscar_por_login("ana@x.com") is None


# Passo 3
class TestCadastro:
    def test_tarefa_nasce_pendente_e_e_gravada(self, preparado):
        _, texto = rodar(ADMIN, *cadastro(), "3")
        assert "Tarefa criada com sucesso. (#1, status Pendente)" in texto
        tarefa = gravadas()[0]
        assert tarefa.titulo == "Estudar Python"
        assert tarefa.status == configuracao.STATUS_PENDENTE
        assert tarefa.usuario_id == modulo.usuarios.buscar_por_login(ADMIN).id

    def test_rn01_titulo_vazio_ou_so_espacos_repete_a_pergunta(self, preparado):
        respostas = cadastro()
        respostas[1:2] = ["", "   ", "Estudar Python"]
        _, texto = rodar(ADMIN, *respostas, "3")
        assert texto.count("Informe um título para a tarefa.") == 2
        assert texto.count("Título: ") == 3
        assert gravadas()[0].titulo == "Estudar Python"

    def test_rn03_prioridade_invalida_repete_e_media_sem_acento_vale(self, preparado):
        respostas = cadastro()
        respostas[3:4] = ["Urgente", "1", "media"]
        _, texto = rodar(ADMIN, *respostas, "3")
        assert texto.count("Prioridade inválida. Os valores aceitos são Alta, Média ou Baixa.") == 2
        assert gravadas()[0].prioridade == "Média"

    def test_rn03_categoria_vazia_vira_geral_e_invalida_repete(self, preparado):
        respostas = cadastro()
        respostas[4:5] = ["Academia", "saude"]
        _, texto = rodar(ADMIN, *respostas, "3")
        assert "Categoria inválida." in texto
        assert gravadas()[0].categoria == "Saúde"
        rodar(ADMIN, *cadastro(categoria=""), "3")
        assert gravadas()[1].categoria == configuracao.CATEGORIA_PADRAO

    def test_rn02_data_passada_ou_fora_do_formato_repete(self, preparado):
        respostas = cadastro()
        respostas[5:6] = ["01/01/2020", "2030-01-15", "31/02/2030", "15/01/2030"]
        _, texto = rodar(ADMIN, *respostas, "3")
        assert "A data prevista não pode ser anterior a hoje" in texto
        assert texto.count("Data inválida. Use o formato DD/MM/AAAA (dia/mês/ano).") == 2
        assert gravadas()[0].data_prevista == date(2030, 1, 15)


# Passo 2 no recorte "Todas"
class TestVisualizar:
    def test_lista_vazia_tem_mensagem_clara(self, preparado):
        _, texto = rodar(ADMIN, "2", "3")
        assert "Nenhuma tarefa cadastrada no momento." in texto

    def test_lista_mostra_todos_os_campos(self, preparado):
        _, texto = rodar(ADMIN, *cadastro(data="15/01/2030"), "2", ENTER, "3")
        for trecho in ("#1  Estudar Python", "Descrição:    Revisar listas",
                       "Prioridade:   Alta", "Categoria:    Geral",
                       "Data limite:  15/01/2030", "Status:       Pendente",
                       "Criada em:", "Concluída em: —", "1 tarefa."):
            assert trecho in texto

    def test_tarefa_fora_de_hoje_aparece_logo_depois_do_cadastro(self, preparado):
        """O painel abre em "Hoje"; o menu mostra todas, senao a tarefa sumiria."""
        _, texto = rodar(ADMIN, *cadastro(data=daqui_a(30)), "2", ENTER, "3")
        assert "Nenhuma tarefa cadastrada" not in texto
        assert "#1  Estudar Python" in texto

    def test_tarefa_concluida_mostra_a_data_de_conclusao(self, preparado):
        rodar(ADMIN, *cadastro(), "3")
        admin = modulo.usuarios.buscar_por_login(ADMIN)
        modulo.tarefas.concluir(admin, 1)
        _, texto = rodar(ADMIN, "2", ENTER, "3")
        assert "Status:       %s" % configuracao.STATUS_CONCLUIDA in texto
        assert "Concluída em: —" not in texto

    def test_rn05_so_aparecem_as_proprias_tarefas(self, preparado):
        rodar(ADMIN, *cadastro(titulo="Do administrador"), "3")
        conta_comum()
        _, texto = rodar("ana@x.com", "2", "3", senhas=("senha123",))
        assert "Do administrador" not in texto
        assert "Nenhuma tarefa cadastrada no momento." in texto


# Passo 9
class TestVisaoAdministrativa:
    def test_admin_ve_a_opcao_4(self, preparado):
        _, texto = rodar(ADMIN, "3")
        assert "4. Visão administrativa (tarefas de todos os usuários)" in texto

    def test_usuario_comum_nao_ve_a_opcao_4(self, preparado):
        conta_comum()
        _, texto = rodar("ana@x.com", "3", senhas=("senha123",))
        assert "3. Sair da aplicação" in texto
        assert "Visão administrativa" not in texto

    def test_rn05_usuario_comum_que_digita_4_recebe_acesso_restrito(self, preparado):
        conta_comum()
        _, texto = rodar("ana@x.com", "4", "3", senhas=("senha123",))
        assert "Acesso restrito ao administrador." in texto
        assert "Opção inválida" not in texto

    def test_admin_ve_as_tarefas_de_todos_com_o_dono(self, preparado):
        conta_comum()
        rodar("ana@x.com", *cadastro(titulo="Da Ana"), "3", senhas=("senha123",))
        rodar(ADMIN, *cadastro(titulo="Do administrador"), "3")
        _, texto = rodar(ADMIN, "4", ENTER, "3")
        assert "#1  Da Ana" in texto and "Dono:         Ana" in texto
        assert "#2  Do administrador" in texto and "Dono:         Administrador" in texto
        assert "2 tarefas." in texto

    def test_na_opcao_2_o_admin_continua_vendo_so_as_proprias(self, preparado):
        """Passo 2.2 - fora da visao administrativa, o admin e um usuario como os outros."""
        conta_comum()
        rodar("ana@x.com", *cadastro(titulo="Da Ana"), "3", senhas=("senha123",))
        _, texto = rodar(ADMIN, "2", "3")
        assert "Da Ana" not in texto
        assert "Nenhuma tarefa cadastrada no momento." in texto
        assert "Como administrador, as tarefas de todos os usuários ficam na opção 4." in texto

    def test_usuario_comum_sem_tarefas_nao_recebe_a_dica_do_admin(self, preparado):
        conta_comum()
        _, texto = rodar("ana@x.com", "2", "3", senhas=("senha123",))
        assert "Como administrador" not in texto

    def test_visao_administrativa_vazia(self, preparado):
        _, texto = rodar(ADMIN, "4", "3")
        assert "Nenhuma tarefa cadastrada no momento." in texto


# Passos 4 a 6 - da lista ao menu da tarefa
class TestEscolherTarefa:
    def test_lista_vazia_nao_pergunta_o_numero(self, preparado):
        _, texto = rodar(ADMIN, "2", "3")
        assert "Número da tarefa" not in texto

    def test_lista_com_tarefas_explica_para_que_serve_o_numero(self, preparado):
        tarefa_de(o_admin())
        _, texto = rodar(ADMIN, "2", ENTER, "3")
        assert "Para editar, concluir, reabrir ou excluir, digite o número da tarefa." in texto
        assert "Número da tarefa (Enter volta ao menu): " in texto

    def test_enter_volta_ao_menu_sem_mudar_nada(self, preparado):
        tarefa_de(o_admin())
        antes = gravadas()[0].para_dict()
        codigo, texto = rodar(ADMIN, "2", ENTER, "3")
        assert codigo == 0
        assert texto.count("MENU PRINCIPAL") == 2
        assert gravadas()[0].para_dict() == antes

    @pytest.mark.parametrize("digitado", ["7", "abc", "1.0", "-1", "²"])
    def test_numero_fora_da_lista_avisa_e_pergunta_de_novo(self, preparado, digitado):
        tarefa_de(o_admin())
        _, texto = rodar(ADMIN, "2", digitado, "1", "0", "3")
        assert "Tarefa não encontrada na lista. Digite um dos números acima, como 1." in texto
        assert "Tarefa #1 · Estudar Python" in texto

    def test_aceita_o_numero_com_cerquilha(self, preparado):
        tarefa_de(o_admin())
        _, texto = rodar(ADMIN, "2", "#1", "0", "3")
        assert "Tarefa #1 · Estudar Python" in texto

    def test_rn05_usuario_comum_nao_alcanca_a_tarefa_de_outro(self, preparado):
        tarefa_de(o_admin(), titulo="Do administrador")
        tarefa_de(conta_comum(), titulo="Da Ana")
        _, texto = rodar("ana@x.com", "2", "1", ENTER, "3", senhas=("senha123",))
        assert "Tarefa não encontrada na lista. Digite um dos números acima, como 2." in texto
        assert "Tarefa #1" not in texto

    def test_pendente_oferece_concluir_e_concluida_oferece_reabrir(self, preparado):
        tarefa_de(o_admin())
        _, pendente = rodar(ADMIN, "2", "1", "0", "3")
        modulo.tarefas.concluir(o_admin(), 1)
        _, concluida = rodar(ADMIN, "2", "1", "0", "3")
        assert "Status: Pendente" in pendente
        assert "2. Concluir" in pendente and "2. Reabrir" not in pendente
        assert "Status: %s" % configuracao.STATUS_CONCLUIDA in concluida
        assert "2. Reabrir" in concluida and "2. Concluir" not in concluida

    def test_opcao_invalida_repete_e_enter_volta(self, preparado):
        tarefa_de(o_admin())
        _, texto = rodar(ADMIN, "2", "1", "9", "x", ENTER, "3")
        assert texto.count("Opção inválida. Escolha 1, 2, 3 ou 0.") == 2
        assert texto.count("MENU PRINCIPAL") == 2
        assert gravadas()[0].status == configuracao.STATUS_PENDENTE

    def test_lista_velha_vira_aviso_e_o_menu_continua(self, preparado):
        """A web e o terminal gravam nos mesmos arquivos: a tarefa pode sumir entre a lista e a acao."""
        tarefa_de(o_admin())

        def excluida_em_outra_interface():
            modulo.tarefas.excluir(o_admin(), 1)
            return "2"

        codigo, texto = rodar(ADMIN, "2", "1", excluida_em_outra_interface, "3")
        assert codigo == 0
        assert "Tarefa não encontrada." in texto
        assert texto.endswith("Encerrando a aplicação. Até logo.")


# Passo 4
class TestEditar:
    def test_mostra_o_valor_atual_de_cada_campo(self, preparado):
        tarefa_de(o_admin(), data=date(2030, 1, 15))
        _, texto = rodar(ADMIN, *na_tarefa(1, "1"), *edicao(), "3")
        for rotulo in ("Título [Estudar Python]: ", "Descrição [Revisar listas] (- apaga): ",
                       "Prioridade (Alta, Média ou Baixa) [Alta]: ",
                       "Categoria (Estudo, Trabalho, Pessoal, Saúde ou Geral) [Estudo]: ",
                       "Data limite (DD/MM/AAAA) [15/01/2030]: "):
            assert rotulo in texto

    def test_enter_mantem_todos_os_campos(self, preparado):
        tarefa_de(o_admin())
        antes = gravadas()[0].para_dict()
        _, texto = rodar(ADMIN, *na_tarefa(1, "1"), *edicao(), "3")
        assert "Tarefa atualizada com sucesso. (#1)" in texto
        assert gravadas()[0].para_dict() == antes

    def test_grava_o_que_foi_digitado(self, preparado):
        tarefa_de(o_admin())
        rodar(ADMIN, *na_tarefa(1, "1"),
              *edicao("  Estudar Docker  ", "Compose e volumes", "baixa", "trabalho", "20/02/2030"),
              "3")
        tarefa = gravadas()[0]
        assert (tarefa.titulo, tarefa.descricao, tarefa.prioridade, tarefa.categoria) == (
            "Estudar Docker", "Compose e volumes", "Baixa", "Trabalho")
        assert tarefa.data_prevista == date(2030, 2, 20)
        assert tarefa.status == configuracao.STATUS_PENDENTE

    def test_traco_apaga_a_descricao(self, preparado):
        tarefa_de(o_admin())
        rodar(ADMIN, *na_tarefa(1, "1"), *edicao(descricao="-"), "3")
        assert gravadas()[0].descricao == ""

    def test_sem_descricao_a_pergunta_nao_oferece_apagar(self, preparado):
        tarefa_de(o_admin(), descricao="")
        _, texto = rodar(ADMIN, *na_tarefa(1, "1"), *edicao(), "3")
        assert "Descrição (opcional): " in texto and "apaga" not in texto
        assert gravadas()[0].descricao == ""

    def test_rn01_rn02_rn03_resposta_invalida_repete_a_pergunta(self, preparado):
        tarefa_de(o_admin())
        respostas = ["x" * 61, ENTER, "y" * 301, ENTER, "Urgente", ENTER, "Academia", ENTER,
                     "01/01/2020", "2030-01-15", ENTER]
        _, texto = rodar(ADMIN, *na_tarefa(1, "1"), *respostas, "3")
        for erro in ("O título deve ter no máximo 60 caracteres.",
                     "A descrição deve ter no máximo 300 caracteres.",
                     "Prioridade inválida.", "Categoria inválida.",
                     "A data prevista não pode ser anterior a hoje",
                     "Data inválida. Use o formato DD/MM/AAAA (dia/mês/ano)."):
            assert erro in texto
        assert "Tarefa atualizada com sucesso. (#1)" in texto
        assert gravadas()[0].titulo == "Estudar Python"

    def test_rn02_tarefa_atrasada_pode_manter_a_propria_data(self, preparado):
        """Redigitar a data antiga vale; trocar por outra data passada, nao."""
        tarefa_de(o_admin(), data=date(2020, 1, 15), hoje=date(2020, 1, 1))
        _, texto = rodar(ADMIN, *na_tarefa(1, "1"), *edicao(data="15/01/2020"),
                         *na_tarefa(1, "1"), *edicao(data="16/01/2020"), ENTER, "3")
        assert texto.count("Tarefa atualizada com sucesso. (#1)") == 2
        assert texto.count("A data prevista não pode ser anterior a hoje") == 1
        assert gravadas()[0].data_prevista == date(2020, 1, 15)

    def test_rn04_concluida_oferece_reabrir_e_o_nao_mantem_tudo(self, preparado):
        tarefa_de(o_admin())
        modulo.tarefas.concluir(o_admin(), 1)
        antes = gravadas()[0].para_dict()
        _, texto = rodar(ADMIN, *na_tarefa(1, "1"), "n", "3")
        assert "Esta tarefa está concluída. Reabra-a para poder editar." in texto
        assert "A tarefa continua concluída." in texto
        assert "Editar tarefa #1" not in texto
        assert gravadas()[0].para_dict() == antes

    def test_rn04_aceitar_reabre_e_segue_para_a_edicao(self, preparado):
        tarefa_de(o_admin())
        modulo.tarefas.concluir(o_admin(), 1)
        _, texto = rodar(ADMIN, *na_tarefa(1, "1"), "s", *edicao(titulo="Revisado"), "3")
        assert "Tarefa reaberta." in texto
        assert "Tarefa atualizada com sucesso. (#1)" in texto
        tarefa = gravadas()[0]
        assert tarefa.titulo == "Revisado"
        assert tarefa.status == configuracao.STATUS_PENDENTE and tarefa.data_conclusao is None

    def test_fim_da_entrada_no_meio_da_edicao_nao_grava_nada(self, preparado):
        tarefa_de(o_admin())
        antes = gravadas()[0].para_dict()
        codigo, _ = rodar(ADMIN, *na_tarefa(1, "1"), "Pela metade")
        assert codigo == 0
        assert gravadas()[0].para_dict() == antes


# Passo 5
class TestConcluirReabrir:
    def test_concluir_grava_o_status_e_o_momento(self, preparado):
        tarefa_de(o_admin())
        _, texto = rodar(ADMIN, *na_tarefa(1, "2"), "3")
        tarefa = gravadas()[0]
        assert tarefa.status == configuracao.STATUS_CONCLUIDA
        assert tarefa.data_conclusao is not None
        assert ("Tarefa concluída. (#1, em %s)"
                % tarefa.data_conclusao.strftime("%d/%m/%Y às %H:%M")) in texto

    def test_reabrir_volta_para_pendente_e_apaga_a_conclusao(self, preparado):
        tarefa_de(o_admin())
        modulo.tarefas.concluir(o_admin(), 1)
        _, texto = rodar(ADMIN, *na_tarefa(1, "2"), "3")
        assert "Tarefa reaberta. (#1, status Pendente)" in texto
        tarefa = gravadas()[0]
        assert tarefa.status == configuracao.STATUS_PENDENTE and tarefa.data_conclusao is None

    def test_rn07_conclusao_anterior_a_criacao_e_recusada_e_o_menu_continua(self, preparado):
        """So acontece com o arquivo editado a mao, com a criacao gravada no futuro."""
        tarefa_de(o_admin(), momento=relogio.agora() + timedelta(days=1))
        _, texto = rodar(ADMIN, *na_tarefa(1, "2"), "3")
        assert ("Não foi possível concluir: a data de conclusão seria anterior "
                "à data de criação da tarefa.") in texto
        assert gravadas()[0].status == configuracao.STATUS_PENDENTE
        assert texto.endswith("Encerrando a aplicação. Até logo.")


# Passo 6
class TestExcluir:
    @pytest.mark.parametrize("resposta", ["s", "S", "sim", "SIM", " s "])
    def test_rn06_so_exclui_depois_do_sim(self, preparado, resposta):
        tarefa_de(o_admin())
        _, texto = rodar(ADMIN, *na_tarefa(1, "3"), resposta, "3")
        assert ('Excluir a tarefa #1 "Estudar Python"? Esta ação não pode ser desfeita. (s/n): '
                in texto)
        assert "Tarefa excluída. (#1)" in texto
        assert gravadas() == []

    @pytest.mark.parametrize("resposta", ["n", ENTER, "nao", "talvez", "excluir"])
    def test_rn06_qualquer_outra_resposta_cancela(self, preparado, resposta):
        tarefa_de(o_admin())
        _, texto = rodar(ADMIN, *na_tarefa(1, "3"), resposta, "3")
        assert "Exclusão cancelada. A tarefa continua cadastrada." in texto
        assert len(gravadas()) == 1

    def test_exclui_so_a_tarefa_escolhida(self, preparado):
        tarefa_de(o_admin(), titulo="Primeira")
        tarefa_de(o_admin(), titulo="Segunda")
        rodar(ADMIN, *na_tarefa(2, "3"), "s", "3")
        assert [tarefa.titulo for tarefa in gravadas()] == ["Primeira"]


# Passo 9 com os Passos 4 a 6 - RN05: o admin age sobre qualquer tarefa
class TestAdministradorGerencia:
    def test_admin_conclui_a_tarefa_de_outro_usuario_pela_opcao_4(self, preparado):
        ana = conta_comum()
        tarefa_de(ana)
        rodar(ADMIN, *na_tarefa(1, "2", lista="4"), "3")
        tarefa = gravadas()[0]
        assert tarefa.status == configuracao.STATUS_CONCLUIDA
        assert tarefa.usuario_id == ana.id

    def test_admin_edita_a_tarefa_de_outro_usuario_e_o_dono_continua_o_mesmo(self, preparado):
        ana = conta_comum()
        tarefa_de(ana)
        rodar(ADMIN, *na_tarefa(1, "1", lista="4"), *edicao(titulo="Revisado pelo admin"), "3")
        tarefa = gravadas()[0]
        assert tarefa.titulo == "Revisado pelo admin"
        assert tarefa.usuario_id == ana.id

    def test_admin_exclui_a_tarefa_de_outro_usuario(self, preparado):
        tarefa_de(conta_comum())
        rodar(ADMIN, *na_tarefa(1, "3", lista="4"), "s", "3")
        assert gravadas() == []

    def test_na_opcao_2_o_admin_so_alcanca_as_proprias(self, preparado):
        tarefa_de(conta_comum(), titulo="Da Ana")
        tarefa_de(o_admin(), titulo="Do administrador")
        _, texto = rodar(ADMIN, "2", "1", ENTER, "3")
        assert "Tarefa não encontrada na lista. Digite um dos números acima, como 2." in texto
        assert gravadas()[0].status == configuracao.STATUS_PENDENTE


# conferencias isoladas
class TestConferencias:
    def test_titulo_volta_sem_os_espacos_das_pontas(self):
        assert main.conferir_titulo("  Estudar  ") == ("Estudar", None)

    def test_data_valida_vira_date(self):
        hoje = date(2026, 10, 6)
        assert main.conferir_data("06/10/2026", hoje=hoje) == (date(2026, 10, 6), None)

    def test_data_de_ontem_e_recusada(self):
        _, erro = main.conferir_data("05/10/2026", hoje=date(2026, 10, 6))
        assert erro == "A data prevista não pode ser anterior a hoje (06/10/2026)."

    @pytest.mark.parametrize("texto", ["", "2026-10-06", "6/10/2026", "31/02/2026", "amanhã"])
    def test_data_fora_do_formato_e_recusada(self, texto):
        data, erro = main.conferir_data(texto, hoje=date(2026, 10, 6))
        assert data is None and erro.startswith("Data inválida.")

    def test_na_edicao_a_data_anterior_continua_valendo(self):
        hoje, anterior = date(2026, 10, 6), date(2026, 9, 30)
        assert main.conferir_data("30/09/2026", hoje=hoje, anterior=anterior) == (anterior, None)
        _, erro = main.conferir_data("29/09/2026", hoje=hoje, anterior=anterior)
        assert erro == "A data prevista não pode ser anterior a hoje (06/10/2026)."

    @pytest.mark.parametrize("texto", ["-", "  -  "])
    def test_traco_apaga_a_descricao_na_edicao(self, texto):
        assert main.conferir_descricao_editada(texto) == ("", None)

    def test_descricao_editada_segue_a_conferencia_do_cadastro(self):
        assert main.conferir_descricao_editada("  Nova  ") == ("Nova", None)
        _, erro = main.conferir_descricao_editada("x" * 301)
        assert erro == "A descrição deve ter no máximo 300 caracteres."
