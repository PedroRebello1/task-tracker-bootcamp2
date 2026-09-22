"""As sete regras de negocio (RN01 a RN07).

Cada funcao devolve None quando a regra é respeitada, ou a mensagem de erro
que deve ser mostrada ao usuario. Elas vivem aqui, e não nas telas, para que
possam ser testadas sem abrir o navegador.

A RN06 (toda exclusao exige confirmacao) nao aparece como funcao porque não e
uma validação de dado: ela e garantida pelo fluxo de duas etapas da rota de
exclusão, que so remove a tarefa quando recebe a confirmacao explicita.
"""
from datetime import date

from src import configuracao
from src.servicos import relogio


class ErroDeRegra(Exception):
    """Levantado quando uma operacao viola uma regra de negocio.

    A mensagem carregada é a que deve ser mostrada ao usuario, por isso as
    rotas podem simplesmente capturar o erro e reexibi-lo na tela.
    """


# RN01
def validar_titulo(titulo):
    """RN01 - o titulo é obrigatorio e não pode ser vazio (ou espacos)."""
    if titulo is None or not titulo.strip():
        return "Informe um título para a tarefa."
    if len(titulo.strip()) > configuracao.TAMANHO_MAXIMO_TITULO:
        return ("O título deve ter no máximo %d caracteres."
                % configuracao.TAMANHO_MAXIMO_TITULO)
    return None


def validar_descricao(descricao):
    """Limite de tamanho da descricao (campo opcional)."""
    if descricao and len(descricao.strip()) > configuracao.TAMANHO_MAXIMO_DESCRICAO:
        return ("A descrição deve ter no máximo %d caracteres."
                % configuracao.TAMANHO_MAXIMO_DESCRICAO)
    return None


# RN02
def converter_data(texto):
    """Converte 'AAAA-MM-DD' em date. Devolve (data, erro)."""
    if not texto or not texto.strip():
        return None, "Selecione uma data válida no calendário."
    try:
        return date.fromisoformat(texto.strip()), None
    except ValueError:
        return None, "Selecione uma data válida no calendário."


def validar_data_prevista(data_prevista, data_anterior=None, hoje=None):
    """RN02 - a data prevista nao pode ser anterior a data atual.

    O seletor de calendario já nasce limitado, mas a regra é conferida de novo
    aqui. A tela previne o erro honesto, o servidor garante a integridade.

    Na edição, `data_anterior` traz a data que a tarefa já tinha. Uma tarefa
    antiga que ficou para trás continua editável e pode manter a propria data;
    """
    hoje = hoje or relogio.hoje()
    if data_prevista is None:
        return "Selecione uma data válida no calendário."
    if data_prevista == data_anterior:
        return None
    if data_prevista < hoje:
        return ("A data prevista não pode ser anterior a hoje (%s)."
                % hoje.strftime("%d/%m/%Y"))
    return None


# RN03
def normalizar_categoria(categoria):
    """A categoria é opcional. Vazia vira o padrao."""
    if categoria is None or not str(categoria).strip():
        return configuracao.CATEGORIA_PADRAO
    return str(categoria).strip()


def validar_prioridade(prioridade):
    """RN03 - prioridade só aceita valores da lista fechada (e é obrigatoria)."""
    if prioridade not in configuracao.PRIORIDADES:
        return ("Prioridade inválida. Os valores aceitos são %s."
                % _ou(configuracao.PRIORIDADES))
    return None


def validar_categoria(categoria):
    """RN03 - categoria só aceita valores da lista fechada."""
    if categoria not in configuracao.CATEGORIAS:
        return ("Categoria inválida. Os valores aceitos são %s."
                % _ou(configuracao.CATEGORIAS))
    return None


# RN04
def validar_edicao_permitida(tarefa):
    """RN04 - uma tarefa concluida não pode ser editada.

    Protege o historico, uma conclusao registrada não é reescrita por acidente.
    """
    if tarefa.concluida:
        return "Esta tarefa está concluída. Reabra-a para poder editar."
    return None


# RN05
def validar_permissao(tarefa, usuario):
    """RN05 - cada usuario só acessa as proprias tarefas, o admin é a excecao."""
    if usuario.eh_admin or tarefa.usuario_id == usuario.id:
        return None
    return "Você não tem permissão para acessar esta tarefa."


def validar_acesso_administrativo(usuario):
    """RN05 - a visao administrativa é restrita ao perfil admin."""
    if usuario.eh_admin:
        return None
    return "Acesso restrito ao administrador."


# RN07
def validar_conclusao(tarefa, momento=None):
    """RN07 - a data de conclusão nunca pode ser anterior a data de criação."""
    momento = momento or relogio.agora()
    if momento < tarefa.data_criacao:
        return ("Não foi possível concluir: a data de conclusão seria anterior "
                "à data de criação da tarefa.")
    return None


def validar_coerencia_temporal(tarefa):
    """RN07 aplicada ao que ja esta gravado, e nao ao ato de concluir.

    No fluxo normal a RN07 nunca dispara, porque a conclusão usa o relógio, que não anda pra trás. 
    Ela ganha utilidade real ao ler o arquivo, uma tarefa cuja conclusão
    antecede a criação é incoerente e precisa ser sinalizada.
    """
    if tarefa.data_conclusao and tarefa.data_conclusao < tarefa.data_criacao:
        return ("A tarefa #%s tem data de conclusão anterior à data de criação."
                % tarefa.id)
    return None


# validacao de conta
def validar_nome(nome):
    if not nome or not nome.strip():
        return "Informe o seu nome."
    return None


def validar_email(email):
    """Checagem simples de formato: algo@algo.algo, sem espacos."""
    if not email or not email.strip():
        return "Informe o seu e-mail."
    email = email.strip()
    if " " in email or email.count("@") != 1:
        return "Informe um e-mail válido."
    usuario, _, dominio = email.partition("@")
    if not usuario or "." not in dominio or dominio.startswith(".") or dominio.endswith("."):
        return "Informe um e-mail válido."
    return None


def validar_senha(senha):
    if not senha:
        return "Informe uma senha."
    if len(senha) < configuracao.TAMANHO_MINIMO_SENHA:
        return ("A senha deve ter pelo menos %d caracteres."
                % configuracao.TAMANHO_MINIMO_SENHA)
    return None


# agregador
def validar_dados_da_tarefa(titulo, descricao, data_prevista, prioridade,
                            categoria, data_anterior=None, hoje=None):
    """Roda as validacoes de uma tarefa na ordem do Passo 3 do algoritmo.

    Devolve a lista de mensagens de erro (vazia quando esta tudo certo).
    """
    verificacoes = [
        validar_titulo(titulo),
        validar_descricao(descricao),
        validar_data_prevista(data_prevista, data_anterior=data_anterior, hoje=hoje),
        validar_prioridade(prioridade),
        validar_categoria(normalizar_categoria(categoria)),
    ]
    return [erro for erro in verificacoes if erro]


def _ou(valores):
    """['a', 'b', 'c'] -> 'a, b ou c'"""
    valores = list(valores)
    if len(valores) == 1:
        return valores[0]
    return "%s ou %s" % (", ".join(valores[:-1]), valores[-1])
