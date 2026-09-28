"""Relatorio resumido. Passo 8 (rota /relatorio).

Enxerga exatamente o conjunto que o painel exibe: mesmo dono, 
mesmo periodo, mesma busca.
"""
from textual.binding import Binding
from textual.containers import Horizontal, Vertical, VerticalScroll
from textual.screen import Screen
from textual.widgets import Button, DataTable, Footer, Input, Label, ProgressBar, Static, Tab, Tabs

from src.cli import formato
from src.servicos import relatorio as servico_relatorio
from src.servicos import relogio

PERIODOS = [("hoje", "Hoje"), ("semana", "Semana"), ("mes", "Mês"), ("todas", "Todas")]
NUMEROS = [("total", "no período"), ("pendentes", "pendentes"),
           ("concluidas", "concluídas"), ("atrasadas", "atrasadas")]


class TelaRelatorio(Screen[None]):
    BINDINGS = [
        Binding("escape", "voltar", "Voltar"),
        Binding("q", "voltar", "Voltar", show=False),
        Binding("slash", "buscar", "Buscar", key_display="/"),
    ]

    def __init__(self):
        super().__init__()
        self._sincronizando = False

    def compose(self):
        yield Static("", id="cabecalho")
        with Horizontal(id="filtros"):
            with Vertical(classes="grupo-filtro"):
                yield Label("Período")
                yield Tabs(*[Tab(rotulo, id="periodo-%s" % chave) for chave, rotulo in PERIODOS],
                           id="periodo")
            with Vertical(classes="grupo-filtro grupo-busca"):
                yield Label("Buscar no título")
                yield Input(placeholder="Buscar no título…", id="busca")
        with VerticalScroll(id="conteudo"):
            yield Static("", id="vazio")
            with Horizontal(id="resumo"):
                for chave, _ in NUMEROS:
                    yield Static("", id="numero-%s" % chave, classes="numero")
            with Vertical(id="progresso"):
                yield Static("", id="rotulo-progresso")
                yield ProgressBar(total=100, show_eta=False, id="barra-progresso")
                yield Static("", id="ajuda-progresso", classes="ajuda")
            with Horizontal(id="colunas"):
                with Vertical(classes="coluna"):
                    yield Static("Por prioridade", classes="titulo-secao")
                    yield Static("", id="por-prioridade")
                with Vertical(classes="coluna"):
                    yield Static("Por categoria", classes="titulo-secao")
                    yield Static("", id="por-categoria")
            yield Static("", id="titulo-lista", classes="titulo-secao")
            yield DataTable(id="lista", cursor_type="row", zebra_stripes=True)
        with Horizontal(id="acoes"):
            yield Button("Voltar", id="voltar", variant="primary")
        yield Footer()

    def on_mount(self):
        # A situacao não vale aqui, e não é carregada adiante ao voltar.
        self.app.filtros["situacao"] = "todas"
        tabela = self.query_one("#lista", DataTable)
        tabela.add_column("Título", key="titulo")
        if self.app.visao_admin:
            tabela.add_column("Dono", key="dono")
        tabela.add_column("Data", key="data")
        tabela.add_column("Status", key="status")
        self._sincronizando = True
        try:
            self.query_one("#periodo", Tabs).active = "periodo-%s" % self.app.filtros["periodo"]
            self.query_one("#busca", Input).value = self.app.filtros["busca"]
        finally:
            self._sincronizando = False
        self.recarregar()
        self.query_one("#voltar", Button).focus()

    # dados
    def recarregar(self):
        app = self.app
        hoje = relogio.hoje()
        do_periodo, _ = app.listar()
        resumo = servico_relatorio.gerar(do_periodo, hoje=hoje)
        donos = app.usuarios.nomes_por_id() if app.visao_admin else {}

        self.query_one("#cabecalho", Static).update(
            "[b]Relatório[/b] · %s, no mesmo recorte do painel · [dim]%s[/dim]"
            % ("todas as tarefas de todos os usuários" if app.visao_admin else "suas tarefas",
               formato.data(hoje)))

        vazio = self.query_one("#vazio", Static)
        conteudo = ["#resumo", "#progresso", "#colunas", "#titulo-lista", "#lista"]
        if resumo["vazio"]:
            vazio.update("Não há dados suficientes para gerar o relatório neste período.")
            vazio.display = True
            for seletor in conteudo:
                self.query_one(seletor).display = False
            return
        vazio.display = False
        for seletor in conteudo:
            self.query_one(seletor).display = True

        for chave, rotulo in NUMEROS:
            numero = self.query_one("#numero-%s" % chave, Static)
            numero.update("[b]%d[/b]\n%s" % (resumo[chave], rotulo))
            numero.set_class(chave == "atrasadas" and resumo["atrasadas"] > 0, "alerta")

        self.query_one("#rotulo-progresso", Static).update(
            "Percentual de conclusão  [b]%s%%[/b]" % resumo["percentual"])
        self.query_one("#barra-progresso", ProgressBar).update(progress=resumo["percentual"])
        self.query_one("#ajuda-progresso", Static).update(
            "%d de %d concluídas." % (resumo["concluidas"], resumo["total"]))

        self.query_one("#por-prioridade", Static).update(
            self._distribuicao(resumo["por_prioridade"], colorir=True))
        self.query_one("#por-categoria", Static).update(
            self._distribuicao(resumo["por_categoria"]))

        # Os titulos que entraram na conta: buscar por palavra e receber só o
        # total seria fazer uma pergunta sem resposta.
        titulo = ("Tarefas com “%s”" % app.filtros["busca"] if app.filtros["busca"]
                  else "Tarefas no recorte")
        self.query_one("#titulo-lista", Static).update("%s  [dim]%d[/dim]" % (titulo, resumo["total"]))
        tabela = self.query_one("#lista", DataTable)
        tabela.clear()
        for tarefa in do_periodo:
            celulas = [formato.titulo(tarefa)]
            if app.visao_admin:
                celulas.append(donos.get(tarefa.usuario_id, "—"))
            celulas += [formato.data_prevista(tarefa, hoje), formato.status(tarefa)]
            tabela.add_row(*celulas, key=str(tarefa.id))

    @staticmethod
    def _distribuicao(itens, colorir=False):
        linhas = []
        for item in itens:
            cor = formato.COR_PRIORIDADE.get(item["valor"], "") if colorir else ""
            rotulo = "[%s]%-8s[/%s]" % (cor, item["valor"], cor) if cor else "%-8s" % item["valor"]
            linhas.append("%s %s  %d · %s%%" % (rotulo, formato.barra(item["percentual"]),
                                               item["quantidade"], item["percentual"]))
        return "\n".join(linhas)

    # eventos
    def on_tabs_tab_activated(self, evento):
        if self._sincronizando or evento.tab is None:
            return
        chave = evento.tab.id[len("periodo-"):]
        if self.app.filtros["periodo"] != chave:
            self.app.filtros["periodo"] = chave
            self.recarregar()

    def on_input_changed(self, evento):
        if evento.input.id == "busca" and not self._sincronizando:
            self.app.filtros["busca"] = evento.value.strip()
            self.recarregar()

    def on_button_pressed(self, evento):
        if evento.button.id == "voltar":
            self.action_voltar()

    def action_buscar(self):
        self.query_one("#busca", Input).focus()

    def action_voltar(self):
        self.dismiss(None)
