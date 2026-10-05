"""Formulario de tarefa. Passos 3 e 4 (rotas /tarefas/nova e /tarefas/<id>/editar).

A mesma tela cria e edita, como formulario_tarefa.html na web. Prioridade e
categoria sao listas fechadas (RN03), então viram caixas de seleção. A data
usa um campo com mascara, o equivalente do <input type="date">.
"""
from textual.binding import Binding
from textual.containers import Horizontal, Vertical, VerticalScroll
from textual.screen import Screen
from textual.widgets import Button, Footer, Input, Label, MaskedInput, Select, Static, TextArea

from src import configuracao
from src.cli import formato
from src.servicos import relogio
from src.servicos.validacoes import ErroDeRegra, data_para_iso

MASCARA_DATA = "00/00/0000"


class TelaFormularioTarefa(Screen[bool]):
    """Devolve True quando gravou alguma coisa, False quando foi cancelada."""
    BINDINGS = [
        Binding("escape", "cancelar", "Cancelar"),
        Binding("ctrl+s", "salvar", "Salvar"),
    ]

    def __init__(self, modo, tarefa=None):
        super().__init__()
        self.modo = modo # "nova" ou "editar"
        self.tarefa = tarefa

    # montagem
    def compose(self):
        hoje = relogio.hoje()
        if self.modo == "nova":
            valores = {"titulo": "", "descricao": "", "data": formato.data(hoje),
                       "prioridade": configuracao.PRIORIDADE_PADRAO,
                       "categoria": configuracao.CATEGORIA_PADRAO}
            titulo = "Nova tarefa"
            subtitulo = ""
        else:
            valores = {"titulo": self.tarefa.titulo, "descricao": self.tarefa.descricao,
                       "data": formato.data(self.tarefa.data_prevista),
                       "prioridade": self.tarefa.prioridade, "categoria": self.tarefa.categoria}
            titulo = "Editar tarefa #%s" % self.tarefa.id
            subtitulo = "Criada em %s" % formato.momento(self.tarefa.data_criacao)

        # RN02 
        if self.modo == "editar" and self.tarefa.data_prevista < hoje:
            ajuda_data = ("Esta tarefa já venceu. Você pode manter %s ou escolher "
                          "uma data de hoje em diante." % formato.data(self.tarefa.data_prevista))
        else:
            ajuda_data = "Não é possível escolher uma data anterior a hoje (%s)." % formato.data(hoje)

        with VerticalScroll(classes="formulario"):
            yield Static(titulo, classes="titulo-secao")
            if subtitulo:
                yield Static(subtitulo, classes="subtitulo")
            yield Static("", id="erros", classes="mensagem")

            yield Label("Título *")
            yield Input(value=valores["titulo"], max_length=configuracao.TAMANHO_MAXIMO_TITULO,
                        placeholder="Estudar para a prova de Bootcamp II", id="titulo")
            yield Static("Até %d caracteres." % configuracao.TAMANHO_MAXIMO_TITULO, classes="ajuda")

            yield Label("Descrição")
            yield TextArea(valores["descricao"], id="descricao",
                           placeholder="Opcional — o que precisa ser feito, em uma frase")
            yield Static("Opcional, até %d caracteres." % configuracao.TAMANHO_MAXIMO_DESCRICAO,
                         classes="ajuda")

            with Horizontal(classes="linha"):
                with Vertical(classes="campo"):
                    yield Label("Data prevista *")
                    yield MaskedInput(MASCARA_DATA, value=valores["data"],
                                      placeholder="DD/MM/AAAA", id="data")
                    yield Static(ajuda_data, classes="ajuda")
                with Vertical(classes="campo"):
                    # RN03 - lista fechada, nunca texto livre.
                    yield Label("Prioridade *")
                    yield Select([(opcao, opcao) for opcao in configuracao.PRIORIDADES],
                                 value=valores["prioridade"], allow_blank=False, id="prioridade")
                with Vertical(classes="campo"):
                    yield Label("Categoria")
                    yield Select([(opcao, opcao) for opcao in configuracao.CATEGORIAS],
                                 value=valores["categoria"], allow_blank=False, id="categoria")

            with Horizontal(classes="acoes"):
                yield Button("Criar tarefa" if self.modo == "nova" else "Salvar alterações",
                             id="salvar", variant="primary")
                yield Button("Cancelar", id="cancelar")
        yield Footer()

    def on_mount(self):
        self.query_one("#titulo", Input).focus()

    # eventos
    def on_input_submitted(self, _evento):
        self.action_salvar()

    def on_button_pressed(self, evento):
        if evento.button.id == "salvar":
            self.action_salvar()
        elif evento.button.id == "cancelar":
            self.action_cancelar()

    def action_cancelar(self):
        self.dismiss(False)

    # envio
    def dados_do_formulario(self):
        """O `_dados_do_formulario` de app.py, lendo os widgets em vez do POST."""
        prioridade = self.query_one("#prioridade", Select).value
        categoria = self.query_one("#categoria", Select).value
        return {
            "titulo": self.query_one("#titulo", Input).value,
            "descricao": self.query_one("#descricao", TextArea).text,
            "texto_data": data_para_iso(self.query_one("#data", MaskedInput).value),
            "prioridade": "" if prioridade is Select.BLANK else prioridade,
            "categoria": "" if categoria is Select.BLANK else categoria,
        }

    def action_salvar(self):
        dados = self.dados_do_formulario()
        try:
            if self.modo == "nova":
                _, erros = self.app.tarefas.criar(self.app.usuario, **dados)
            else:
                _, erros = self.app.tarefas.editar(self.app.usuario, self.tarefa.id, **dados)
        except ErroDeRegra as erro:
            # Tarefa sumiu, mudou de dono ou foi concluida por outra janela
            # (a web, por exemplo) enquanto o formulario estava aberto.
            erros = [str(erro)]
        if erros:
            self.query_one("#erros", Static).update("\n".join(erros))
            return
        self.app.avisar_sucesso("Tarefa criada com sucesso." if self.modo == "nova"
                                else "Tarefa atualizada com sucesso.")
        self.dismiss(True)
