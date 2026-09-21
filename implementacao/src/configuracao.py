import os
import secrets


def _ligado(nome, padrao="0"):
    # Le uma variavel de ambiente booleana ('1', 'true', 'sim' -> True).
    return os.environ.get(nome, padrao).strip().lower() in ("1", "true", "sim", "on")


# caminhos

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PASTA_DADOS = os.environ.get("TASKTRACKER_PASTA_DADOS") or os.path.join(RAIZ, "dados")
ARQUIVO_TAREFAS = os.path.join(PASTA_DADOS, "tarefas.json")
ARQUIVO_USUARIOS = os.path.join(PASTA_DADOS, "usuarios.json")

# listas fechadas
# Sustentam a RN03: nenhum destes campos aceita texto livre.
PRIORIDADES = ("Alta", "Média", "Baixa")
PRIORIDADE_PADRAO = "Média"

CATEGORIAS = ("Estudo", "Trabalho", "Pessoal", "Saúde", "Geral")
CATEGORIA_PADRAO = "Geral"

STATUS_PENDENTE = "Pendente"
STATUS_CONCLUIDA = "Concluída"

PERFIL_ADMIN = "admin"
PERFIL_COMUM = "comum"

# Aparencia. O padrao é o tema claro. 
# A escolha de cada usuario e gravada no proprio cadastro.
TEMAS = ("claro", "escuro")
TEMA_PADRAO = "claro"

PERIODOS = ("hoje", "semana", "mes", "todas")
PERIODO_PADRAO = "hoje"

# Filtro de situacao.
SITUACOES = ("todas", "pendentes", "concluidas", "atrasadas")
SITUACAO_PADRAO = "todas"

# Ordem de exibicao quando duas tarefas caem no mesmo dia.
PESO_PRIORIDADE = {prioridade: peso for peso, prioridade in enumerate(PRIORIDADES)}

# limites
TAMANHO_MAXIMO_TITULO = 60
TAMANHO_MAXIMO_DESCRICAO = 300
TAMANHO_MINIMO_SENHA = 6

MAXIMO_TENTATIVAS_LOGIN = 3
SEGUNDOS_DE_BLOQUEIO = 60

# Fuso
# O sistema inteiro gira em torno de "o que eu tenho para hoje". Sem um fuso, um servidor em UTC faz uma tarefa criada 
# as 21h30 de Brasilia nascer com a data do dia seguinte.
FUSO = os.environ.get("TASKTRACKER_FUSO", "America/Sao_Paulo")

# Administrador padrao
# Criado automaticamente na primeira execucao
ADMIN_PADRAO_NOME = "Administrador"
ADMIN_PADRAO_LOGIN = os.environ.get("TASKTRACKER_ADMIN_LOGIN", "admin@tasktracker.local")
ADMIN_PADRAO_SENHA = os.environ.get("TASKTRACKER_ADMIN_SENHA", "admin123")
ADMIN_SENHA_PADRAO_EM_USO = "TASKTRACKER_ADMIN_SENHA" not in os.environ

# servidor
HOST = os.environ.get("TASKTRACKER_HOST", "127.0.0.1")
PORTA = int(os.environ.get("TASKTRACKER_PORTA", "5000"))

# Depuracao do flask desligada por padrao
MODO_DEBUG = _ligado("TASKTRACKER_DEBUG", "0")

# A chave assina o cookie de sessao. Uma chave aleatoria é sorteada a cada inicializacao.
CHAVE_SECRETA = os.environ.get("TASKTRACKER_CHAVE_SECRETA") or secrets.token_hex(32)
CHAVE_SECRETA_SORTEADA = "TASKTRACKER_CHAVE_SECRETA" not in os.environ
COOKIE_SEGURO = _ligado("TASKTRACKER_COOKIE_SEGURO", "0")

# Tempo de vida da sessao inativa.
HORAS_DE_SESSAO = int(os.environ.get("TASKTRACKER_HORAS_SESSAO", "12"))

# Entra na URL do CSS para que o navegador nao sirva a versao antiga guardada em cache.
VERSAO_ESTATICOS = "3"
