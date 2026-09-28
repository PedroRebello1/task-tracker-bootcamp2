"""Painel e visão administrativa. Passos 2 e 9 (rotas / e /admin).

É a tela principal: faixa de resumo, filtros, tabela e acoes. 
A mesma tela serve ao painel pessoal e a administração.
"""
from textual.binding import Binding
from textual.containers import Horizontal, Vertical
from textual.screen import Screen
from textual.widgets import Button, DataTable, Footer, Input, Label, Static, Tab, Tabs

from src import configuracao
from src.cli import formato
from src.cli.dialogos import ConfirmarExclusao, TarefaConcluida
from src.cli.formulario import TelaFormularioTarefa
from src.cli.relatorio import TelaRelatorio
from src.servicos import relatorio as servico_relatorio
from src.servicos import relogio, validacoes
from src.servicos.validacoes import ErroDeRegra

PERIODOS = [("hoje", "Hoje"), ("semana", "Semana"), ("mes", "Mês"), ("todas", "Todas")]
SITUACOES = [("todas", "Todas"), ("pendentes", "Pendentes"),
             ("concluidas", "Concluídas"), ("atrasadas", "Atrasadas")]
ROTULO_DO_NUMERO = {"todas": "no período", "pendentes": "pendentes",
                    "concluidas": "concluídas", "atrasadas": "atrasadas"}


class TelaPainel(Screen):
    BINDINGS = [
        Binding("n", "nova", "Nova"),
        Binding("e", "editar", "Editar"),
        Binding("c", "concluir", "Concluir"),
        Binding("r", "reabrir", "Reabrir"),
        Binding("x", "excluir", "Excluir"),
        Binding("delete", "excluir", "Excluir", show=False),
        Binding("l", "relatorio", "Relatório"),
        Binding("a", "admin", "Administração"),
        Binding("slash", "buscar", "Buscar", key_display="/"),
        Binding("f5", "recarregar", "Atualizar", show=False),
        Binding("q", "sair", "Sair da conta"),
    ]

    def __init__(self):
        super().__init__()
        self._linhas = [] # tarefas na ordem em que estao na tabela
        self._sincronizando = False # evita recarregar ao ajustar as abas por codigo

    # montagem
    def compose(self):
        yield Static("", id="cabecalho")
        yield Static("", id="nota-admin")
        with Horizontal(id="resumo"):
            for chave, _ in SITUACOES:
                yield Static("", id="numero-%s" % chave, classes="numero")
        with Horizontal(id="filtros"):
            with Vertical(classes="grupo-filtro"):
                yield Label("Período")
                yield Tabs(*[Tab(rotulo, id="periodo-%s" % chave) for chave, rotulo in PERIODOS],
                           id="periodo")
            with Vertical(classes="grupo-filtro"):
                yield Label("Situação")
                yield Tabs(*[Tab(rotulo, id="situacao-%s" % chave) for chave, rotulo in SITUACOES],
                           id="situacao")
            with Vertical(classes="grupo-filtro grupo-busca"):
                yield Label("Buscar no título")
                yield Input(placeholder="Buscar no título…", id="busca")
        yield DataTable(id="tabela", cursor_type="row", zebra_stripes=True)
        yield Static("", id="vazio")
        yield Static("", id="detalhe")
        with Horizontal(id="acoes"):
            yield Button("Nova", id="nova", variant="primary")
            yield Button("Editar", id="editar")
            yield Button("Concluir", id="concluir", variant="success")
            yield Button("Reabrir", id="reabrir")
            yield Button("Excluir", id="excluir", variant="error")
            yield Button("Relatório", id="relatorio")
            yield Button("Administração", id="admin")
            yield Button("Sair", id="sair")
        yield Footer()

    def on_mount(self):
        self.query_one("#admin", Button).display = self.app.usuario.eh_admin
        self._montar_colunas()
        self._sincronizar_filtros()
        self.recarregar()
        self.query_one("#tabela", DataTable).focus()

    def check_action(self, acao, _parametros):
        """RN05 - a acao de administracao nem aparece para quem nao e admin.

        False esconde a tecla do rodape; a acao em si confere a regra de novo
        pelo servico, como a rota /admin faz na web.
        """
        if acao == "admin" and not self.app.usuario.eh_admin:
            return False
        return True

    # dados
    def _montar_colunas(self):
        tabela = self.query_one("#tabela", DataTable)
        tabela.clear(columns=True)
        tabela.add_column("ID", key="id")
        if self.app.visao_admin:
            tabela.add_column("Dono", key="dono")
        tabela.add_column("Título", key="titulo")
        tabela.add_column("Prioridade", key="prioridade")
        tabela.add_column("Categoria", key="categoria")
        tabela.add_column("Data prevista", key="data")
        tabela.add_column("Status", key="status")

    def recarregar(self):
        """Passo 2 - relê o disco e redesenha tudo o que depende do recorte."""
        app = self.app
        hoje = relogio.hoje()
        do_periodo, lista = app.listar()
        resumo = servico_relatorio.gerar(do_periodo, hoje=hoje)
        donos = app.usuarios.nomes_por_id() if app.visao_admin else {}

        if app.visao_admin:
            cabecalho = "[b]Administração[/b] · todas as tarefas de todos os usuários"
        else:
            cabecalho = "[b]Minhas tarefas[/b]"
        cabecalho += " · %s · %d %s neste recorte · [dim]%s (%s)[/dim]" % (
            formato.data(hoje), resumo["total"],
            formato.plural(resumo["total"], "tarefa", "tarefas"),
            app.usuario.nome, app.usuario.perfil)
        self.query_one("#cabecalho", Static).update(cabecalho)

        nota = self.query_one("#nota-admin", Static)
        nota.display = app.visao_admin
        nota.update("As regras [b]RN04[/b] (tarefa concluída não se edita) e "
                    "[b]RN06[/b] (exclusão exige confirmação) continuam valendo aqui.")

        # Passo 2.7 - os quatro numeros decompoem o periodo inteiro.
        for chave, _ in SITUACOES:
            numero = self.query_one("#numero-%s" % chave, Static)
            valor = resumo["total"] if chave == "todas" else resumo[chave]
            numero.update("[b]%d[/b]\n%s" % (valor, ROTULO_DO_NUMERO[chave]))
            numero.set_class(app.filtros["situacao"] == chave, "ativo")
            numero.set_class(chave == "atrasadas" and valor > 0, "alerta")

        # Guarda a tarefa sob o cursor para devolver o cursor a ela depois.
        selecionada = self.tarefa_selecionada()
        tabela = self.query_one("#tabela", DataTable)
        tabela.clear()
        self._linhas = lista
        for tarefa in lista:
            celulas = ["#%d" % tarefa.id]
            if app.visao_admin:
                celulas.append(donos.get(tarefa.usuario_id, "—"))
            celulas += [formato.titulo(tarefa), formato.prioridade(tarefa.prioridade),
                        tarefa.categoria, formato.data_prevista(tarefa, hoje),
                        formato.status(tarefa)]
            tabela.add_row(*celulas, key=str(tarefa.id))
        if selecionada is not None:
            for posicao, tarefa in enumerate(lista):
                if tarefa.id == selecionada.id:
                    tabela.move_cursor(row=posicao)
                    break

        # Passo 2.6 - lista vazia tem mensagem clara, nao uma tabela em branco.
        vazio = self.query_one("#vazio", Static)
        if lista:
            vazio.display = False
            tabela.display = True
        else:
            tabela.display = False
            vazio.display = True
            if app.filtros["busca"]:
                vazio.update("Nenhuma tarefa com “%s” no título dentro deste recorte."
                             % app.filtros["busca"])
            else:
                vazio.update("Nenhuma tarefa encontrada para este período.")
        self._mostrar_detalhe()

    def _sincronizar_filtros(self):
        """Leva os filtros da sessao para as abas sem disparar recarga em cascata."""
        self._sincronizando = True
        try:
            self.query_one("#periodo", Tabs).active = "periodo-%s" % self.app.filtros["periodo"]
            self.query_one("#situacao", Tabs).active = "situacao-%s" % self.app.filtros["situacao"]
            self.query_one("#busca", Input).value = self.app.filtros["busca"]
        finally:
            self._sincronizando = False

    def tarefa_selecionada(self):
        tabela = self.query_one("#tabela", DataTable)
        if not self._linhas or tabela.row_count == 0:
            return None
        posicao = tabela.cursor_row
        if 0 <= posicao < len(self._linhas):
            return self._linhas[posicao]
        return None

    def _mostrar_detalhe(self):
        """A descricao e as datas da tarefa sob o cursor - o que a tabela nao comporta."""
        detalhe = self.query_one("#detalhe", Static)
        tarefa = self.tarefa_selecionada()
        if tarefa is None:
            detalhe.update("")
            self.query_one("#concluir", Button).disabled = True
            self.query_one("#reabrir", Button).disabled = True
            return
        partes = ["[b]#%d %s[/b]" % (tarefa.id, tarefa.titulo)]
        if tarefa.descricao:
            partes.append(tarefa.descricao)
        partes.append("[dim]Criada em %s%s[/dim]" % (
            formato.momento(tarefa.data_criacao),
            " · concluída em %s" % formato.momento(tarefa.data_conclusao)
            if tarefa.data_conclusao else ""))
        detalhe.update("\n".join(partes))
        self.query_one("#concluir", Button).disabled = tarefa.concluida
        self.query_one("#reabrir", Button).disabled = not tarefa.concluida

    # eventos
    def on_tabs_tab_activated(self, evento):
        if self._sincronizando or evento.tab is None:
            return
        grupo, _, chave = evento.tab.id.partition("-")
        if grupo in ("periodo", "situacao") and self.app.filtros.get(grupo) != chave:
            self.app.filtros[grupo] = chave
            self.recarregar()

    def on_input_changed(self, evento):
        """Passo 2.4 - a busca filtra enquanto se digita; o disco e local e pequeno."""
        if evento.input.id == "busca" and not self._sincronizando:
            self.app.filtros["busca"] = evento.value.strip()
            self.recarregar()

    def on_input_submitted(self, evento):
        if evento.input.id == "busca":
            self.query_one("#tabela", DataTable).focus()

    def on_data_table_row_highlighted(self, _evento):
        self._mostrar_detalhe()

    def on_data_table_row_selected(self, _evento):
        """Enter ou duplo clique na linha abre a edicao."""
        self.action_editar()

    def on_click(self, evento):
        """Clicar num numero do resumo e um atalho para a situacao correspondente."""
        alvo = evento.widget
        while alvo is not None and not (isinstance(alvo, Static) and alvo.has_class("numero")):
            alvo = alvo.parent
        if alvo is not None and alvo.id:
            self.query_one("#situacao", Tabs).active = "situacao-%s" % alvo.id[len("numero-"):]

    def on_button_pressed(self, evento):
        acao = getattr(self, "action_%s" % evento.button.id, None)
        if acao:
            acao()

    # ações
    def action_buscar(self):
        self.query_one("#busca", Input).focus()

    def action_recarregar(self):
        self.recarregar()

    def action_nova(self):
        """Passo 3."""
        self.app.push_screen(TelaFormularioTarefa("nova"), self._depois_do_formulario)

    def action_editar(self):
        """Passo 4. Concluida nao abre o formulario: oferece reabrir (RN04)."""
        tarefa = self.tarefa_selecionada()
        if tarefa is None:
            return
        try:
            atual = self.app.tarefas.buscar_por_id(tarefa.id, self.app.usuario)
        except ErroDeRegra as erro:
            self.app.avisar_erro(erro)
            self.recarregar()
            return
        if validacoes.validar_edicao_permitida(atual):
            self.app.push_screen(TarefaConcluida(atual), self._depois_de_reabrir_para_editar)
            return
        self.app.push_screen(TelaFormularioTarefa("editar", atual), self._depois_do_formulario)

    def action_concluir(self):
        """Passo 5."""
        self._executar(self.app.tarefas.concluir, "Tarefa concluída.")

    def action_reabrir(self):
        """Passo 5.7."""
        self._executar(self.app.tarefas.reabrir, "Tarefa reaberta.")

    def action_excluir(self):
        """Passo 6 - RN06: pergunta antes; so o dialogo confirmado remove."""
        tarefa = self.tarefa_selecionada()
        if tarefa is None:
            return
        try:
            alvo = self.app.tarefas.buscar_por_id(tarefa.id, self.app.usuario)
        except ErroDeRegra as erro:
            self.app.avisar_erro(erro)
            self.recarregar()
            return
        self.app.push_screen(
            ConfirmarExclusao(alvo),
            lambda confirmado: self._depois_de_confirmar_exclusao(alvo, confirmado))

    def action_relatorio(self):
        """Passo 8 - o relatorio enxerga o mesmo recorte que o painel."""
        self.app.push_screen(TelaRelatorio(), self._depois_de_voltar)

    def action_admin(self):
        """Passo 9 - alterna entre o painel pessoal e a visao de todos (RN05)."""
        erro = validacoes.validar_acesso_administrativo(self.app.usuario)
        if erro:
            self.app.avisar_erro(erro)
            return
        app = self.app
        app.visao_admin = not app.visao_admin
        # Entrar na administracao abre em "todas", como a rota /admin; voltar
        # ao painel recomeça do recorte padrao, como o link "Meu painel".
        app.filtros = app.filtros_padrao("todas" if app.visao_admin else configuracao.PERIODO_PADRAO)
        self.query_one("#admin", Button).label = "Meu painel" if app.visao_admin else "Administração"
        self._montar_colunas()
        self._sincronizar_filtros()
        self.recarregar()

    def action_sair(self):
        self.app.sair_da_conta()

    # retornos
    def _executar(self, operacao, mensagem):
        tarefa = self.tarefa_selecionada()
        if tarefa is None:
            return
        try:
            operacao(self.app.usuario, tarefa.id)
            self.app.avisar_sucesso(mensagem)
        except ErroDeRegra as erro:
            self.app.avisar_erro(erro)
        self.recarregar()

    def _depois_do_formulario(self, _gravou):
        self.recarregar()
        self.query_one("#tabela", DataTable).focus()

    def _depois_de_reabrir_para_editar(self, reaberta):
        self.recarregar()
        if reaberta:
            self.action_editar()
        else:
            self.query_one("#tabela", DataTable).focus()

    def _depois_de_confirmar_exclusao(self, alvo, confirmado):
        """Passo 6.5 - so chega ao servico depois do "Sim, excluir"."""
        if confirmado:
            try:
                self.app.tarefas.excluir(self.app.usuario, alvo.id)
                self.app.avisar_sucesso("Tarefa excluída.")
            except ErroDeRegra as erro:
                self.app.avisar_erro(erro)
        self.recarregar()
        self.query_one("#tabela", DataTable).focus()

    def _depois_de_voltar(self, _resultado):
        """O relatorio compartilha os filtros: o que mudou la vale aqui."""
        self._sincronizar_filtros()
        self.recarregar()
        self.query_one("#tabela", DataTable).focus()
