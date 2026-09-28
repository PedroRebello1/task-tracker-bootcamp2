"""A aplicacao Textual: guarda a sessao e coordena a troca de telas.

Faz o papel que `session` e os `redirect` fazem no Flask: sabe quem esta
logado, qual recorte (periodo, situacao, busca) esta em uso e para onde ir
depois de cada ação.
"""
from textual.app import App
from textual.binding import Binding

from src import configuracao
from src.cli.boas_vindas import TelaBoasVindas
from src.cli.conta import TelaLogin
from src.cli.painel import TelaPainel

# O tema gravado na conta vale tambem no terminal
TEMAS_DO_TERMINAL = {"claro": "textual-light", "escuro": "textual-dark"}


class AplicacaoTerminal(App[str]):
    TITLE = "Task Tracker"
    SUB_TITLE = "Bootcamp II"
    CSS_PATH = "estilo.tcss"
    ENABLE_COMMAND_PALETTE = False
    BINDINGS = [Binding("ctrl+q", "quit", "Fechar", priority=True)]

    def __init__(self, usuarios, tarefas, avisos=(), direto_no_cli=False):
        super().__init__()
        self.usuarios = usuarios
        self.tarefas = tarefas
        self.avisos = list(avisos)
        self.direto_no_cli = direto_no_cli
        # Estado da sessao, equivalente ao cookie
        self.usuario = None
        self.visao_admin = False
        self.filtros = self.filtros_padrao()

    def on_mount(self):
        self.theme = TEMAS_DO_TERMINAL[configuracao.TEMA_PADRAO]
        self.push_screen(TelaLogin() if self.direto_no_cli else TelaBoasVindas())

    # sessao
    def entrar(self, usuario):
        """Passo 1.7 - abre a sessao e leva ao painel."""
        self.usuario = usuario
        self.visao_admin = False
        self.filtros = self.filtros_padrao()
        self.theme = TEMAS_DO_TERMINAL.get(usuario.tema, TEMAS_DO_TERMINAL[configuracao.TEMA_PADRAO])
        self.notify("Bem-vindo, %s." % usuario.nome.split()[0])
        self.switch_screen(TelaPainel())

    def sair_da_conta(self):
        """Passo 10 - encerra a sessao. Nenhum dado se perde: cada operacao ja gravou."""
        self.usuario = None
        self.visao_admin = False
        self.filtros = self.filtros_padrao()
        self.theme = TEMAS_DO_TERMINAL[configuracao.TEMA_PADRAO]
        self.notify("Sessão encerrada.")
        self.switch_screen(TelaLogin())

    def voltar_ao_inicio(self):
        """Da tela de login para a de boas-vindas; sem ela (`--cli`), fecha o programa."""
        if any(isinstance(tela, TelaBoasVindas) for tela in self.screen_stack):
            self.pop_screen()
        else:
            self.exit()

    def abrir_web(self):
        """Encerra o terminal avisando a quem chamou que e para subir o Flask."""
        self.exit("web")

    # filtros
    @staticmethod
    def filtros_padrao(periodo=configuracao.PERIODO_PADRAO):
        return {"periodo": periodo, "situacao": configuracao.SITUACAO_PADRAO, "busca": ""}

    def listar(self):
        """Devolve tudo do periodo com uma unica leitura.
        """
        do_periodo = self.tarefas.listar(
            self.usuario, periodo=self.filtros["periodo"], busca=self.filtros["busca"],
            situacao="todas", visao_admin=self.visao_admin)
        return do_periodo, self.tarefas.filtrar_por_situacao(do_periodo, self.filtros["situacao"])

    # mensagens
    def avisar_erro(self, mensagem):
        """O `flash(..., "erro")` do terminal."""
        self.notify(str(mensagem), title="Não foi possível", severity="error", timeout=6)

    def avisar_sucesso(self, mensagem):
        self.notify(str(mensagem), timeout=4)
