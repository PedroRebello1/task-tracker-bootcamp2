"""Operacoes sobre tarefas - Passos 2 a 8 do algoritmo da Etapa 1.

Criar, editar, concluir, reabrir, excluir, filtrar por periodo e situacao,
buscar e ordenar. Nenhuma tela e tocada aqui, este modulo só conhece dados e
regras.

Cada operacao de escrita le o arquivo UMA vez, trabalha sobre essa lista e
regrava. Ler duas vezes (uma para achar a tarefa, outra para alterar) alem de
desperdicar disco abre uma janela em que as duas leituras podem discordar.
"""
import unicodedata
from datetime import timedelta

from src import configuracao
from src.modelos.tarefa import Tarefa
from src.repositorio.repositorio_json import RepositorioJson
from src.servicos import relogio, validacoes
from src.servicos.validacoes import ErroDeRegra


class GerenciadorTarefas:
    def __init__(self, repositorio=None):
        self.repositorio = repositorio or RepositorioJson(configuracao.ARQUIVO_TAREFAS)

    # carga e escrita
    def listar_todas(self):
        return [Tarefa.de_dict(registro) for registro in self.repositorio.carregar()]

    def _gravar(self, tarefas):
        self.repositorio.salvar([tarefa.para_dict() for tarefa in tarefas])

    def _proximo_id(self, tarefas):
        """Maior identificador ja existente, mais um (Passo 3.6.1)."""
        return max((tarefa.id for tarefa in tarefas), default=0) + 1

    @staticmethod
    def _localizar(tarefas, id_tarefa, usuario):
        """Acha a tarefa na lista ja carregada e confere a posse (Passos 4.2 e 4.3)."""
        for tarefa in tarefas:
            if tarefa.id == id_tarefa:
                erro = validacoes.validar_permissao(tarefa, usuario)
                if erro:
                    raise ErroDeRegra(erro)
                return tarefa
        raise ErroDeRegra("Tarefa não encontrada.")

    # consulta
    def buscar_por_id(self, id_tarefa, usuario):
        """Passo 4.2 e 4.3: encontra a tarefa e confere a propriedade (RN05)."""
        return self._localizar(self.listar_todas(), id_tarefa, usuario)

    def listar(self, usuario, periodo=configuracao.PERIODO_PADRAO, busca="",
               situacao=configuracao.SITUACAO_PADRAO, visao_admin=False, hoje=None):
        """Passo 2: decide o conjunto, filtra, busca e ordena."""
        hoje = hoje or relogio.hoje()
        tarefas = self.listar_todas()

        # 2.2 - quais tarefas considerar
        if not (visao_admin and usuario.eh_admin):
            tarefas = [t for t in tarefas if t.usuario_id == usuario.id]

        # 2.3 - filtro de periodo
        tarefas = [t for t in tarefas if self._dentro_do_periodo(t, periodo, hoje)]

        # filtro de situacao (acrescimo da Etapa 2, fora da especificacao)
        tarefas = [t for t in tarefas if self._na_situacao(t, situacao, hoje)]

        # 2.4 - busca por palavra no titulo, ignorando maiusculas e acentos
        if busca and busca.strip():
            alvo = _normalizar(busca)
            tarefas = [t for t in tarefas if alvo in _normalizar(t.titulo)]

        # 2.5 - data, depois prioridade, depois identificador
        tarefas.sort(key=lambda t: (t.data_prevista, t.peso_prioridade, t.id))
        return tarefas

    @staticmethod
    def _dentro_do_periodo(tarefa, periodo, hoje):
        if periodo == "hoje":
            return tarefa.data_prevista == hoje
        if periodo == "semana":
            segunda = hoje - timedelta(days=hoje.weekday())
            return segunda <= tarefa.data_prevista <= segunda + timedelta(days=6)
        if periodo == "mes":
            return (tarefa.data_prevista.year == hoje.year
                    and tarefa.data_prevista.month == hoje.month)
        return True # "todas" e qualquer valor desconhecido

    @staticmethod
    def _na_situacao(tarefa, situacao, hoje):
        if situacao == "pendentes":
            return not tarefa.concluida
        if situacao == "concluidas":
            return tarefa.concluida
        if situacao == "atrasadas":
            return tarefa.esta_atrasada(hoje)
        return True # "todas" e qualquer valor desconhecido

    @classmethod
    def filtrar_por_situacao(cls, tarefas, situacao, hoje=None):
        """Aplica so o filtro de situacao a uma lista ja carregada.

        Existe para o painel poder fazer duas coisas com uma unica leitura do
        disco: contar a faixa de resumo sobre TODO o periodo - se ela contasse
        so o que esta filtrado, "0 concluidas" apareceria sempre que o filtro
        fosse "pendentes" - e listar abaixo apenas a situacao escolhida.
        """
        hoje = hoje or relogio.hoje()
        return [t for t in tarefas if cls._na_situacao(t, situacao, hoje)]

    # criacao
    def criar(self, usuario, titulo, descricao, texto_data, prioridade, categoria,
              hoje=None, momento=None):
        """Passo 3. Devolve (tarefa, erros); a tarefa e None quando ha erro."""
        categoria = validacoes.normalizar_categoria(categoria)
        data_prevista, erro_data = validacoes.converter_data(texto_data)
        erros = validacoes.validar_dados_da_tarefa(
            titulo, descricao, data_prevista, prioridade, categoria, hoje=hoje)
        if erro_data and erro_data not in erros:
            erros.insert(0, erro_data)
        if erros:
            return None, erros

        tarefas = self.listar_todas()
        tarefa = Tarefa(
            id=self._proximo_id(tarefas),
            titulo=titulo.strip(),
            descricao=(descricao or "").strip(),
            data_prevista=data_prevista,
            prioridade=prioridade,
            categoria=categoria,
            usuario_id=usuario.id,
            status=configuracao.STATUS_PENDENTE,
            data_criacao=momento or relogio.agora(),
            data_conclusao=None,
        )
        tarefas.append(tarefa)
        self._gravar(tarefas)
        return tarefa, []

    # edicao
    def editar(self, usuario, id_tarefa, titulo, descricao, texto_data,
               prioridade, categoria, hoje=None):
        """Passo 4. Devolve (tarefa, erros)."""
        tarefas = self.listar_todas()
        alvo = self._localizar(tarefas, id_tarefa, usuario)

        # RN04 - concluida nao se edita; e preciso reabrir antes
        erro = validacoes.validar_edicao_permitida(alvo)
        if erro:
            raise ErroDeRegra(erro)

        categoria = validacoes.normalizar_categoria(categoria)
        data_prevista, erro_data = validacoes.converter_data(texto_data)
        erros = validacoes.validar_dados_da_tarefa(
            titulo, descricao, data_prevista, prioridade, categoria,
            data_anterior=alvo.data_prevista, hoje=hoje)
        if erro_data and erro_data not in erros:
            erros.insert(0, erro_data)
        if erros:
            return None, erros

        alvo.titulo = titulo.strip()
        alvo.descricao = (descricao or "").strip()
        alvo.data_prevista = data_prevista
        alvo.prioridade = prioridade
        alvo.categoria = categoria
        self._gravar(tarefas)
        return alvo, []

    # conclusao e reabertura
    def concluir(self, usuario, id_tarefa, momento=None):
        """Passo 5."""
        momento = momento or relogio.agora()
        tarefas = self.listar_todas()
        alvo = self._localizar(tarefas, id_tarefa, usuario)
        if alvo.concluida:
            raise ErroDeRegra("Esta tarefa já está concluída.")

        # RN07 - a conclusao nunca pode anteceder a criacao
        erro = validacoes.validar_conclusao(alvo, momento)
        if erro:
            raise ErroDeRegra(erro)

        alvo.status = configuracao.STATUS_CONCLUIDA
        alvo.data_conclusao = momento
        self._gravar(tarefas)
        return alvo

    def reabrir(self, usuario, id_tarefa):
        """Passo 5.7 - devolve a tarefa para Pendente e limpa a conclusao."""
        tarefas = self.listar_todas()
        alvo = self._localizar(tarefas, id_tarefa, usuario)
        if not alvo.concluida:
            raise ErroDeRegra("Esta tarefa já está pendente.")

        alvo.status = configuracao.STATUS_PENDENTE
        alvo.data_conclusao = None
        self._gravar(tarefas)
        return alvo

    # exclusao
    def excluir(self, usuario, id_tarefa):
        """Passo 6.5 - so e chamado DEPOIS da confirmacao explicita (RN06)."""
        tarefas = self.listar_todas()
        alvo = self._localizar(tarefas, id_tarefa, usuario)
        self._gravar([t for t in tarefas if t.id != alvo.id])
        return alvo

    # integridade
    def incoerencias(self):
        """Tarefas gravadas que violam a RN07 (conclusao antes da criacao).

        O arquivo e texto e pode ser editado a mao. Esta e a unica forma de a
        RN07 dizer alguma coisa sobre dados que ja estao no disco.
        """
        avisos = []
        for tarefa in self.listar_todas():
            erro = validacoes.validar_coerencia_temporal(tarefa)
            if erro:
                avisos.append(erro)
        return avisos


def _normalizar(texto):
    """Minusculas e sem acentos, para a busca do Passo 2.4."""
    sem_acento = unicodedata.normalize("NFKD", texto or "")
    return "".join(c for c in sem_acento if not unicodedata.combining(c)).lower()
