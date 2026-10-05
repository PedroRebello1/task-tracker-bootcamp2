"""Testa o menu numerado (src/main.py), dirigido por respostas digitadas simuladas.

Cada teste roda o menu inteiro, do login a saida, sobre a pasta de dados
temporaria do conftest. As respostas acabam -> EOFError -> o menu encerra,
exatamente como um Ctrl+D no terminal.
"""
from datetime import date, timedelta

import pytest

from src import app as modulo
from src import configuracao
from src import main
from src.servicos import relogio

ADMIN = configuracao.ADMIN_PADRAO_LOGIN
SENHA_ADMIN = configuracao.ADMIN_PADRAO_SENHA


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


def gravadas():
    return modulo.tarefas.listar_todas()


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
        _, texto = rodar(ADMIN, "9", "abc", "2", "3")
        assert texto.count("Opção inválida. Escolha 1, 2 ou 3.") == 2
        assert "Nenhuma tarefa cadastrada no momento." in texto

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
        _, texto = rodar(ADMIN, *cadastro(data="15/01/2030"), "2", "3")
        for trecho in ("#1  Estudar Python", "Descrição:    Revisar listas",
                       "Prioridade:   Alta", "Categoria:    Geral",
                       "Data limite:  15/01/2030", "Status:       Pendente",
                       "Criada em:", "Concluída em: —", "1 tarefa."):
            assert trecho in texto

    def test_tarefa_fora_de_hoje_aparece_logo_depois_do_cadastro(self, preparado):
        """O painel abre em "Hoje"; o menu mostra todas, senao a tarefa sumiria."""
        _, texto = rodar(ADMIN, *cadastro(data=daqui_a(30)), "2", "3")
        assert "Nenhuma tarefa cadastrada" not in texto
        assert "#1  Estudar Python" in texto

    def test_tarefa_concluida_mostra_a_data_de_conclusao(self, preparado):
        rodar(ADMIN, *cadastro(), "3")
        admin = modulo.usuarios.buscar_por_login(ADMIN)
        modulo.tarefas.concluir(admin, 1)
        _, texto = rodar(ADMIN, "2", "3")
        assert "Status:       %s" % configuracao.STATUS_CONCLUIDA in texto
        assert "Concluída em: —" not in texto

    def test_rn05_so_aparecem_as_proprias_tarefas(self, preparado):
        rodar(ADMIN, *cadastro(titulo="Do administrador"), "3")
        modulo.usuarios.cadastrar("Ana", "ana@x.com", "senha123")
        _, texto = rodar("ana@x.com", "2", "3", senhas=("senha123",))
        assert "Do administrador" not in texto
        assert "Nenhuma tarefa cadastrada no momento." in texto


# conferencias isoladas
class TestConferencias:
    def test_titulo_volta_sem_os_espacos_das_pontas(self):
        assert main.conferir_titulo("  Estudar  ") == ("Estudar", None)

    def test_data_valida_vira_date(self):
        hoje = date(2026, 9, 22)
        assert main.conferir_data("22/09/2026", hoje=hoje) == (date(2026, 9, 22), None)

    def test_data_de_ontem_e_recusada(self):
        _, erro = main.conferir_data("21/09/2026", hoje=date(2026, 9, 22))
        assert erro == "A data prevista não pode ser anterior a hoje (22/09/2026)."

    @pytest.mark.parametrize("texto", ["", "2026-09-22", "22/9/2026", "31/02/2026", "amanhã"])
    def test_data_fora_do_formato_e_recusada(self, texto):
        data, erro = main.conferir_data(texto, hoje=date(2026, 9, 22))
        assert data is None and erro.startswith("Data inválida.")
