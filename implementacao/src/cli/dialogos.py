"""Dialogos sobrepostos ao painel: a confirmacao da RN06 e a tela da RN04."""
from textual.binding import Binding
from textual.containers import Horizontal, Vertical
from textual.screen import ModalScreen
from textual.widgets import Button, Static

from src.cli import formato
from src.servicos.validacoes import ErroDeRegra


def _detalhes(tarefa):
    linhas = [
        ("Identificador", "#%s" % tarefa.id),
        ("Prioridade", tarefa.prioridade),
        ("Categoria", tarefa.categoria),
        ("Status", tarefa.status),
        ("Prevista para", formato.data(tarefa.data_prevista)),
        ("Criada em", formato.momento(tarefa.data_criacao)),
    ]
    if tarefa.data_conclusao:
        linhas.append(("Concluída em", formato.momento(tarefa.data_conclusao)))
    return "\n".join("[dim]%-14s[/dim] %s" % (rotulo, valor) for rotulo, valor in linhas)


class ConfirmarExclusao(ModalScreen[bool]):
    """RN06 - nenhuma tarefa é removida no primeiro comando.

    Equivale ao GET de /tarefas/<id>/excluir: mostra a tarefa,
    pergunta e chama`tarefas.excluir`.
    """
    BINDINGS = [Binding("escape", "cancelar", "Cancelar")]

    def __init__(self, tarefa):
        super().__init__()
        self.tarefa = tarefa

    def compose(self):
        with Vertical(classes="dialogo perigo"):
            yield Static("Confirmação necessária", classes="sobrenome")
            yield Static("Excluir tarefa", classes="titulo-cartao")
            yield Static("Excluir a tarefa [b]“%s”[/b], prevista para [b]%s[/b]?"
                         % (self.tarefa.titulo, formato.data(self.tarefa.data_prevista)),
                         classes="pergunta")
            yield Static(_detalhes(self.tarefa), classes="detalhe")
            if self.tarefa.descricao:
                yield Static(self.tarefa.descricao, classes="descricao-longa", markup=False)
            yield Static("Esta ação não pode ser desfeita.", classes="alerta-texto")
            with Horizontal(classes="acoes"):
                yield Button("Sim, excluir", id="confirmar", variant="error")
                yield Button("Cancelar", id="cancelar")

    def on_mount(self):
        # O foco nasce em "Cancelar": um Enter a mais por distracao nao apaga nada.
        self.query_one("#cancelar", Button).focus()

    def on_button_pressed(self, evento):
        self.dismiss(evento.button.id == "confirmar")

    def action_cancelar(self):
        self.dismiss(False)


class TarefaConcluida(ModalScreen[bool]):
    """RN04 / Passo 4.4 - o formulario nao abre, a tela oferece o botao Reabrir.

    Devolve True quando a tarefa foi reaberta (e o painel pode abrir a edicao).
    """
    BINDINGS = [Binding("escape", "voltar", "Voltar")]

    def __init__(self, tarefa):
        super().__init__()
        self.tarefa = tarefa

    def compose(self):
        with Vertical(classes="dialogo"):
            yield Static("Regra RN04", classes="sobrenome")
            yield Static("Esta tarefa está concluída", classes="titulo-cartao")
            yield Static("Reabra-a para poder editar. Uma conclusão registrada não é "
                         "reescrita por acidente — é isso que mantém o histórico confiável.",
                         classes="apoio")
            yield Static(_detalhes(self.tarefa), classes="detalhe")
            with Horizontal(classes="acoes"):
                yield Button("Reabrir e editar", id="reabrir", variant="primary")
                yield Button("Voltar", id="voltar")

    def on_button_pressed(self, evento):
        if evento.button.id == "reabrir":
            self.reabrir()
        else:
            self.dismiss(False)

    def action_voltar(self):
        self.dismiss(False)

    def reabrir(self):
        try:
            self.app.tarefas.reabrir(self.app.usuario, self.tarefa.id)
        except ErroDeRegra as erro:
            self.app.avisar_erro(erro)
            self.dismiss(False)
            return
        self.app.avisar_sucesso("Tarefa reaberta.")
        self.dismiss(True)
