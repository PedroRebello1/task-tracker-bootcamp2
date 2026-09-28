"""Tela inicial: o banner do sistema e a escolha entre terminal e web app.

E a unica tela sem equivalente na web - ela existe justamente para decidir
qual das duas interfaces vai ser usada.
"""
from textual.binding import Binding
from textual.containers import Horizontal, Vertical
from textual.screen import Screen
from textual.widgets import Button, Footer, Static

from src.cli.conta import TelaLogin

BANNER = r"""

████████╗ █████╗ ███████╗██╗  ██╗    ████████╗██████╗  █████╗  ██████╗██╗  ██╗███████╗██████╗ 
╚══██╔══╝██╔══██╗██╔════╝██║ ██╔╝    ╚══██╔══╝██╔══██╗██╔══██╗██╔════╝██║ ██╔╝██╔════╝██╔══██╗
   ██║   ███████║███████╗█████╔╝        ██║   ██████╔╝███████║██║     █████╔╝ █████╗  ██████╔╝
   ██║   ██╔══██║╚════██║██╔═██╗        ██║   ██╔══██╗██╔══██║██║     ██╔═██╗ ██╔══╝  ██╔══██╗
   ██║   ██║  ██║███████║██║  ██╗       ██║   ██║  ██║██║  ██║╚██████╗██║  ██╗███████╗██║  ██║
   ╚═╝   ╚═╝  ╚═╝╚══════╝╚═╝  ╚═╝       ╚═╝   ╚═╝  ╚═╝╚═╝  ╚═╝ ╚═════╝╚═╝  ╚═╝╚══════╝╚═╝  ╚═╝
                                                                                              
                                                                                                                      
""".strip("\n")


class TelaBoasVindas(Screen):
    BINDINGS = [
        Binding("1", "terminal", "Terminal"),
        Binding("2", "web", "Web app"),
        Binding("escape", "app.quit", "Fechar"),
        Binding("left", "app.focus_previous", show=False),
        Binding("right", "app.focus_next", show=False),
    ]

    def compose(self):
        with Vertical(id="boas-vindas"):
            yield Static(BANNER, id="banner", markup=False)
            yield Static("Bootcamp II · CEUB", id="sobrenome")
            yield Static("Suas tarefas organizadas por prazo e prioridade.", id="apoio")
            yield Static("Como você quer usar o sistema?", id="pergunta")
            with Horizontal(id="opcoes"):
                yield Button("1  Continuar no terminal", id="terminal", variant="primary")
                yield Button("2  Abrir o web app", id="web")
            yield Static("← → ou Tab para escolher · Enter para confirmar · "
                         "o clique do mouse também funciona", id="dica")
        yield Footer()

    def on_mount(self):
        self.query_one("#terminal", Button).focus()

    def on_button_pressed(self, evento):
        if evento.button.id == "terminal":
            self.action_terminal()
        elif evento.button.id == "web":
            self.action_web()

    def action_terminal(self):
        self.app.push_screen(TelaLogin())

    def action_web(self):
        self.app.abrir_web()
