"""Entrar e criar conta - Passo 1 do algoritmo (rotas /login e /cadastro)."""
from textual.binding import Binding
from textual.containers import Horizontal, Vertical
from textual.screen import Screen
from textual.widgets import Button, Footer, Input, Label, Static

from src import configuracao
from src.servicos.validacoes import ErroDeRegra


class TelaLogin(Screen):
    BINDINGS = [Binding("escape", "voltar", "Voltar")]

    def __init__(self, login_digitado=""):
        super().__init__(classes="centrada")
        self.login_digitado = login_digitado
        self._contador = None
        self._restantes = 0

    def compose(self):
        with Vertical(classes="cartao"):
            yield Static("Bootcamp II · CEUB", classes="sobrenome")
            yield Static("Task Tracker", classes="titulo-cartao")
            yield Static("Suas tarefas organizadas por prazo e prioridade.", classes="apoio")
            yield Static("", id="mensagem", classes="mensagem")
            yield Label("E-mail")
            yield Input(value=self.login_digitado, placeholder="voce@exemplo.com", id="login")
            yield Label("Senha")
            yield Input(password=True, id="senha")
            with Horizontal(classes="acoes"):
                yield Button("Entrar", id="entrar", variant="primary")
                yield Button("Criar conta", id="cadastro")
                yield Button("Voltar", id="voltar")
        if self.app.avisos:
            yield Static("\n".join("· %s" % aviso for aviso in self.app.avisos),
                         id="avisos", markup=False)
        yield Footer()

    def on_mount(self):
        self.query_one("#senha" if self.login_digitado else "#login", Input).focus()

    # eventos
    def on_input_submitted(self, _evento):
        """Enter em qualquer campo envia o formulario, como na web."""
        self.entrar()

    def on_button_pressed(self, evento):
        if evento.button.id == "entrar":
            self.entrar()
        elif evento.button.id == "cadastro":
            self.app.push_screen(TelaCadastro(), self._depois_do_cadastro)
        elif evento.button.id == "voltar":
            self.action_voltar()

    def action_voltar(self):
        self.app.voltar_ao_inicio()

    # login
    def entrar(self):
        if self.query_one("#entrar", Button).disabled:
            return # bloqueado: o contador ainda corre
        email = self.query_one("#login", Input).value
        senha = self.query_one("#senha", Input).value
        try:
            usuario = self.app.usuarios.autenticar(email, senha)
        except ErroDeRegra as erro:
            self.query_one("#mensagem", Static).update(str(erro))
            self.query_one("#senha", Input).value = ""
            # Passo 1.6, o bloqueio fica visivel, com a contagem regressiva.
            self._iniciar_bloqueio(self.app.usuarios.segundos_de_bloqueio(email))
            return
        self.app.entrar(usuario)

    def _depois_do_cadastro(self, email):
        """Volta do cadastro com o e-mail ja preenchido."""
        if email:
            self.query_one("#login", Input).value = email
            self.query_one("#mensagem", Static).update("Conta criada. Faça login para continuar.")
            self.query_one("#senha", Input).focus()

    # bloqueio
    def _iniciar_bloqueio(self, segundos):
        """Desliga o botao e conta para tras, como o script de login.html."""
        if not segundos:
            return
        self._restantes = segundos
        botao = self.query_one("#entrar", Button)
        botao.disabled = True
        botao.label = "Bloqueado por %ds" % segundos
        self.query_one("#senha", Input).focus()
        if self._contador is None:
            self._contador = self.set_interval(1, self._contar)
        else:
            self._contador.resume()

    def _contar(self):
        self._restantes -= 1
        botao = self.query_one("#entrar", Button)
        if self._restantes > 0:
            botao.label = "Bloqueado por %ds" % self._restantes
            return
        self._contador.pause()
        botao.disabled = False
        botao.label = "Entrar"
        self.query_one("#senha", Input).focus()


class TelaCadastro(Screen[str]):
    """Passo 1.2 - devolve o e-mail cadastrado para a tela de login."""
    BINDINGS = [Binding("escape", "cancelar", "Voltar ao login")]

    def __init__(self):
        super().__init__(classes="centrada")

    def compose(self):
        with Vertical(classes="cartao"):
            yield Static("Bootcamp II · CEUB", classes="sobrenome")
            yield Static("Criar conta", classes="titulo-cartao")
            yield Static("Sua conta é pessoal: só você enxerga as suas tarefas.", classes="apoio")
            yield Static("", id="mensagem", classes="mensagem")
            yield Label("Nome")
            yield Input(placeholder="Seu nome", id="nome", max_length=80)
            yield Label("E-mail")
            yield Input(placeholder="voce@exemplo.com", id="login")
            yield Label("Senha")
            yield Input(password=True, id="senha")
            yield Static("Mínimo de %d caracteres." % configuracao.TAMANHO_MINIMO_SENHA,
                         classes="ajuda")
            with Horizontal(classes="acoes"):
                yield Button("Criar conta", id="criar", variant="primary")
                yield Button("Voltar ao login", id="cancelar")
        yield Footer()

    def on_mount(self):
        self.query_one("#nome", Input).focus()

    def on_input_submitted(self, _evento):
        self.criar()

    def on_button_pressed(self, evento):
        if evento.button.id == "criar":
            self.criar()
        elif evento.button.id == "cancelar":
            self.action_cancelar()

    def action_cancelar(self):
        self.dismiss("")

    def criar(self):
        nome = self.query_one("#nome", Input).value
        email = self.query_one("#login", Input).value
        senha = self.query_one("#senha", Input).value
        _, erros = self.app.usuarios.cadastrar(nome, email, senha)
        if erros:
            self.query_one("#mensagem", Static).update("\n".join(erros))
            return
        self.app.avisar_sucesso("Conta criada. Faça login para continuar.")
        self.dismiss(email.strip().lower())
