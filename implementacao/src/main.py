"""Menu numerado do Task Tracker - a terceira interface, feita so de input() e print().

A entrega da Etapa 2 pede uma CLI classica: um menu em loop continuo com as
opcoes cadastrar, visualizar e sair. É tambem a interface que roda no Google
Colab, onde nem o Textual (que precisa de um terminal real) nem o Flask (que
precisa de um navegador apontado para ele) funcionam.

Como src/cli/ e o app.py, esta camada nao tem regra de negocio: os dados passam
pelos mesmos GerenciadorUsuarios e GerenciadorTarefas e sao gravados nos mesmos
arquivos JSON.

    python -m src.main       (a partir de implementacao/)
    python src/main.py
"""
import getpass
import os
import sys

# Garante que a pasta implementacao/ esteja no caminho de importação, para que
# `python src/main.py` funcione tanto quanto `python -m src.main`.
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src import configuracao
from src.repositorio.repositorio_json import ArquivoCorrompido
from src.servicos import relogio, validacoes
from src.servicos.gerenciador_tarefas import GerenciadorTarefas
from src.servicos.gerenciador_usuarios import GerenciadorUsuarios
from src.servicos.validacoes import ErroDeRegra

LINHA = "=" * 44

OPCOES = (
    ("1", "Cadastrar nova tarefa"),
    ("2", "Visualizar tarefas cadastradas"),
    ("3", "Sair da aplicação"),
)

# Palavra que, digitada no lugar do e-mail, abre o cadastro de conta.
CRIAR_CONTA = "nova"


class MenuNumerado:
    """O loop do menu. `entrada`, `saida` e `ler_senha` sao trocados nos testes."""

    def __init__(self, usuarios, tarefas, entrada=None, saida=None, ler_senha=None):
        self.usuarios = usuarios
        self.tarefas = tarefas
        # input, print e getpass sao procurados na hora da chamada, e nao na
        # definicao da classe: o Colab troca o input() e o getpass() a cada
        # celula executada, e uma referencia guardada antes ficaria velha.
        self.entrada = entrada or (lambda rotulo: input(rotulo))
        self.saida = saida or (lambda texto: print(texto))
        self.ler_senha = ler_senha or (lambda rotulo: getpass.getpass(rotulo))
        self.usuario = None

    # ponto de entrada
    def executar(self):
        """Passo 1 (entrar) e depois o menu, ate a opcao 3. Devolve o codigo de saida."""
        try:
            self.entrar()
            while True:
                opcao = self.escolher_opcao()
                if opcao == "1":
                    self.cadastrar()
                elif opcao == "2":
                    self.visualizar()
                elif opcao == "3":
                    break
                else:
                    self.mostrar("Opção inválida. Escolha 1, 2 ou 3.")
        except (KeyboardInterrupt, EOFError):
            # Ctrl+C, Ctrl+D ou "interromper execução" no Colab: sai sem traceback.
            # Nada se perde, cada cadastro ja regravou o arquivo (Passo 10.3).
            self.saida("")
        self.mostrar()
        self.mostrar("Encerrando a aplicação. Até logo.")
        return 0

    # entrada e saida
    def mostrar(self, texto=""):
        self.saida("  %s" % texto if texto else "")

    def perguntar(self, rotulo):
        return self.entrada("  %s" % rotulo)

    def cabecalho(self, titulo):
        self.mostrar()
        self.mostrar(LINHA)
        self.mostrar(titulo)
        self.mostrar(LINHA)

    # Passo 1
    def entrar(self):
        """Pede e-mail e senha ate conferirem, com o bloqueio do GerenciadorUsuarios."""
        self.cabecalho("TASK TRACKER · Bootcamp II")
        self.mostrar('Entre com a sua conta. Para criar uma, digite "%s" no e-mail.'
                     % CRIAR_CONTA)
        if configuracao.ADMIN_SENHA_PADRAO_EM_USO:
            self.mostrar("Administrador padrão: %s / %s"
                         % (configuracao.ADMIN_PADRAO_LOGIN, configuracao.ADMIN_PADRAO_SENHA))
        while self.usuario is None:
            self.mostrar()
            login = self.perguntar("E-mail: ").strip()
            if login.lower() == CRIAR_CONTA:
                self.criar_conta()
                continue
            senha = self.ler_senha("  Senha: ")
            try:
                self.usuario = self.usuarios.autenticar(login, senha)
            except ErroDeRegra as erro:
                self.mostrar(str(erro))
        self.mostrar("Olá, %s!" % self.usuario.nome)

    def criar_conta(self):
        """Passo 1.2 - nome, e-mail e senha. A conta nasce com perfil comum."""
        self.cabecalho("Criar conta")
        nome = self.perguntar("Nome: ")
        login = self.perguntar("E-mail: ")
        senha = self.ler_senha("  Senha (mínimo de %d caracteres): "
                               % configuracao.TAMANHO_MINIMO_SENHA)
        _, erros = self.usuarios.cadastrar(nome, login, senha)
        if erros:
            for erro in erros:
                self.mostrar(erro)
            self.mostrar("A conta não foi criada.")
            return
        # Passo 1.2.d - devolve o usuario a tela de login.
        self.mostrar("Conta criada. Agora entre com o e-mail e a senha.")

    # menu
    def escolher_opcao(self):
        self.cabecalho("MENU PRINCIPAL")
        for numero, descricao in OPCOES:
            self.mostrar("%s. %s" % (numero, descricao))
        self.mostrar()
        return self.perguntar("Escolha uma opção: ").strip()

    # Passo 3
    def cadastrar(self):
        """Pergunta campo a campo. Resposta invalida mostra o erro e repete a pergunta.

        O GerenciadorTarefas confere tudo de novo ao gravar. A pergunta previne
        o erro, o servico garante a integridade, como a barreira dupla da web.
        """
        self.cabecalho("Cadastrar nova tarefa")
        titulo = self.ler_campo("Título: ", conferir_titulo)
        descricao = self.ler_campo("Descrição (opcional): ", conferir_descricao)
        prioridade = self.ler_campo("Prioridade (%s): " % _ou(configuracao.PRIORIDADES),
                                    conferir_prioridade)
        categoria = self.ler_campo("Categoria (%s) [%s]: "
                                   % (_ou(configuracao.CATEGORIAS), configuracao.CATEGORIA_PADRAO),
                                   conferir_categoria)
        data = self.ler_campo("Data limite (DD/MM/AAAA): ", conferir_data)

        tarefa, erros = self.tarefas.criar(self.usuario, titulo, descricao,
                                           data.isoformat(), prioridade, categoria)
        if erros:
            # So acontece se algo mudar entre a pergunta e a gravacao, como a
            # virada do dia deixando a data no passado.
            for erro in erros:
                self.mostrar(erro)
            self.mostrar("A tarefa não foi cadastrada.")
            return
        self.mostrar("Tarefa criada com sucesso. (#%d, status %s)" % (tarefa.id, tarefa.status))

    def ler_campo(self, rotulo, conferir):
        """Repete a pergunta ate `conferir` aceitar o que foi digitado."""
        while True:
            valor, erro = conferir(self.perguntar(rotulo))
            if erro is None:
                return valor
            self.mostrar(erro)

    # Passo 2, no recorte "Todas"
    def visualizar(self):
        """Lista todas as tarefas do usuario, com todos os campos.

        O painel do terminal e da web abre em "Hoje". Aqui o recorte é "Todas",
        senao uma tarefa cadastrada para a semana que vem sumiria da lista logo
        depois do cadastro.
        """
        lista = self.tarefas.listar(self.usuario, periodo="todas")
        self.cabecalho("Tarefas cadastradas")
        if not lista:
            self.mostrar("Nenhuma tarefa cadastrada no momento.")
            return
        hoje = relogio.hoje()
        for tarefa in lista:
            self.mostrar_tarefa(tarefa, hoje)
        self.mostrar("%d %s." % (len(lista), "tarefa" if len(lista) == 1 else "tarefas"))

    def mostrar_tarefa(self, tarefa, hoje):
        prazo = _data(tarefa.data_prevista)
        if tarefa.esta_atrasada(hoje):
            prazo += "  (atrasada)"
        campos = (
            ("Descrição", tarefa.descricao or "—"),
            ("Prioridade", tarefa.prioridade),
            ("Categoria", tarefa.categoria),
            ("Data limite", prazo),
            ("Status", tarefa.status),
            ("Criada em", _momento(tarefa.data_criacao)),
            ("Concluída em", _momento(tarefa.data_conclusao) if tarefa.data_conclusao else "—"),
        )
        self.mostrar("#%d  %s" % (tarefa.id, tarefa.titulo))
        for rotulo, valor in campos:
            self.mostrar("    %-14s%s" % (rotulo + ":", valor))
        self.mostrar()


# conferencia campo a campo
# Cada uma recebe o texto digitado e devolve (valor, erro). As regras sao as de
# validacoes.py, as mesmas que o GerenciadorTarefas aplica ao gravar (Passo 3.4).
def conferir_titulo(texto):
    """RN01 - vazio ou so espacos e recusado; ate 60 caracteres."""
    return texto.strip(), validacoes.validar_titulo(texto)


def conferir_descricao(texto):
    """Opcional, ate 300 caracteres."""
    return texto.strip(), validacoes.validar_descricao(texto)


def conferir_prioridade(texto):
    """RN03 - so Alta, Média (ou Media) e Baixa, sem diferenciar maiusculas."""
    prioridade = validacoes.normalizar_prioridade(texto)
    return prioridade, validacoes.validar_prioridade(prioridade)


def conferir_categoria(texto):
    """RN03 - opcional. Enter vazio vira a categoria padrao."""
    categoria = validacoes.normalizar_categoria(texto)
    return categoria, validacoes.validar_categoria(categoria)


def conferir_data(texto, hoje=None):
    """RN02 - DD/MM/AAAA, de hoje em diante."""
    iso = validacoes.data_para_iso(texto)
    # data_para_iso devolve sem mudar o que nao esta em DD/MM/AAAA. Sem esta
    # checagem, '2026-10-15' passaria direto pela converter_data.
    data, erro = validacoes.converter_data(iso)
    if erro or iso == texto.strip():
        # A mensagem do servico fala em calendario, que aqui nao existe.
        return None, "Data inválida. Use o formato DD/MM/AAAA (dia/mês/ano)."
    return data, validacoes.validar_data_prevista(data, hoje=hoje)


# formatacao
# As mesmas de src/cli/formato.py, repetidas aqui porque importar qualquer
# coisa de src/cli/ carrega o Textual, que o menu numerado nao usa.
def _data(valor):
    """date -> '21/09/2026'."""
    return valor.strftime("%d/%m/%Y")


def _momento(valor):
    """datetime -> '28/09/2026 às 14:05'."""
    return valor.strftime("%d/%m/%Y às %H:%M")


def _ou(valores):
    """['a', 'b', 'c'] -> 'a, b ou c'"""
    valores = list(valores)
    return "%s ou %s" % (", ".join(valores[:-1]), valores[-1])


# Passo 0
def preparar(usuarios, tarefas):
    """O mesmo preparar() do app.py: pasta e arquivos de dados e o admin padrao."""
    os.makedirs(configuracao.PASTA_DADOS, exist_ok=True)
    tarefas.repositorio.garantir_arquivo()
    usuarios.repositorio.garantir_arquivo()
    return usuarios.garantir_admin_padrao()


def main():
    usuarios = GerenciadorUsuarios()
    tarefas = GerenciadorTarefas()
    try:
        preparar(usuarios, tarefas)
    except ArquivoCorrompido as erro:
        # Passo 0.4 - avisa e para, sem sobrescrever o que pode ser recuperado.
        print("\n  ERRO: %s\n" % erro)
        return 1
    return MenuNumerado(usuarios, tarefas).executar()


if __name__ == "__main__":
    sys.exit(main())
