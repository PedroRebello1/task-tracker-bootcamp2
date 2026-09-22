"""Ponto de entrada do Task Tracker.

Cria o servidor Flask, define os enderecos que o navegador pode acessar e,
para cada um, chama o servico correspondente e devolve a pagina montada.

Executado diretamente (`python -m src.app`), pergunta primeiro se
quer usar o terminal ou o navegador. A interface de terminal mora em
src/cli/ e usa exatamente os mesmos servicos e arquivos de dados.
"""
import argparse
import os
import secrets
import sys
import threading
import webbrowser
from datetime import timedelta
from functools import wraps
from urllib.parse import urlsplit

# Garante que a pasta implementacao/ esteja no caminho de importação, para que
# `python src/app.py` funcione tanto quanto `python -m src.app`.
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from flask import (Flask, abort, flash, g, redirect, render_template, request,
                   session, url_for)

from src import configuracao
from src.repositorio.repositorio_json import ArquivoCorrompido
from src.servicos import relatorio as servico_relatorio
from src.servicos import relogio, validacoes
from src.servicos.gerenciador_tarefas import GerenciadorTarefas
from src.servicos.gerenciador_usuarios import GerenciadorUsuarios
from src.servicos.validacoes import ErroDeRegra

app = Flask(__name__, static_folder="estaticos", static_url_path="/estaticos")
app.secret_key = configuracao.CHAVE_SECRETA
app.config.update(
    SESSION_COOKIE_HTTPONLY=True, # o cookie não é legivel por JavaScript
    SESSION_COOKIE_SAMESITE="Lax", # nao viaja em requisição vinda de outro site
    SESSION_COOKIE_SECURE=configuracao.COOKIE_SEGURO,
    PERMANENT_SESSION_LIFETIME=timedelta(hours=configuracao.HORAS_DE_SESSAO),
    MAX_CONTENT_LENGTH=256 * 1024, # nenhum formulario daqui chega perto disso
    TEMPLATES_AUTO_RELOAD=configuracao.MODO_DEBUG,
)

usuarios = GerenciadorUsuarios()
tarefas = GerenciadorTarefas()

_preparado = False

# Quantos titulos o relatorio lista antes de mandar o leitor ao painel. 
LIMITE_DA_LISTA_DO_RELATORIO = 50


# sessão
def usuario_atual(silencioso=False):
    """O usuario da sessao, lido do disco uma unica vez por requisicao.

    Sem o cache em `g`, a mesma requisicao leria usuarios.json duas vezes, uma
    no decorador de login e outra no processador de contexto dos templates.

    `silencioso` existe por causa de um loop: se usuarios.json estáilegivel, 
    a pagina de erro que avisa isso é montada a partir do mesmo template que 
    pergunta quem esta logado, e estouraria de novo dentro do proprio tratador.
    """
    if "usuario_atual" in g:
        return g.usuario_atual

    id_usuario = session.get("usuario_id")
    if not id_usuario:
        g.usuario_atual = None
        return None

    try:
        g.usuario_atual = usuarios.buscar_por_id(id_usuario)
    except ArquivoCorrompido:
        if not silencioso:
            raise
        return None # nao guarda em `g`: a proxima tenta de novo
    return g.usuario_atual


def exige_login(rota):
    """Passa o usuario da sessão como primeiro argumento da rota."""
    @wraps(rota)
    def envolvida(*args, **kwargs):
        usuario = usuario_atual()
        if usuario is not None:
            return rota(usuario, *args, **kwargs)

        # Só quem tentava ir a algum lugar especifico recebe o aviso
        # e volta para lá depois de entrar.
        destino = caminho_atual()
        if destino == url_for("painel"):
            return redirect(url_for("login"))
        flash("Faça login para continuar.", "erro")
        return redirect(url_for("login", proximo=destino))
    return envolvida


def caminho_atual():
    """O endereco desta requisicao, sem o '?' vazio que `full_path` acrescenta."""
    return request.full_path if request.query_string else request.path


def token_csrf():
    """Token por sessao, conferido em todo POST."""
    if "csrf" not in session:
        session["csrf"] = secrets.token_urlsafe(32)
    return session["csrf"]


@app.before_request
def preparo_unico():
    """Passo 0 - roda na primeira requisicao, seja qual for o servidor.

    Deixar isto apenas no bloco `__main__` faria o administrador padrão nunca
    ser criado quando a aplicacao subisse por `flask run` ou por um servidor
    WSGI, que é exatamente o esperado da Etapa 3.
    """
    global _preparado
    if not _preparado:
        preparar()
        _preparado = True


@app.before_request
def protege_csrf():
    """Recusa POST sem o token da sessao."""
    if request.method == "POST":
        enviado = request.form.get("csrf", "")
        esperado = session.get("csrf", "")
        if not esperado or not secrets.compare_digest(enviado, esperado):
            abort(400)


def tema_atual():
    """O tema da conta quando se está alguem logado, ou da sessao quando não.

    Ele e resolvido no servidor e sai no proprio `<html>`. Se fosse decidido por
    JavaScript, a pagina apareceria clara por um instante antes de escurecer.
    """
    usuario = usuario_atual(silencioso=True)
    if usuario is not None:
        return usuario.tema
    tema = session.get("tema")
    return tema if tema in configuracao.TEMAS else configuracao.TEMA_PADRAO


@app.route("/tema", methods=["POST"])
def alternar_tema():
    """Troca claro/escuro. Grava na conta de quem esta logado"""
    novo = "escuro" if tema_atual() == "claro" else "claro"
    usuario = usuario_atual(silencioso=True)
    if usuario is not None:
        usuarios.definir_tema(usuario.id, novo)
    else:
        session["tema"] = novo
    return redirect(_voltar())


@app.context_processor
def variaveis_globais():
    """Valores disponiveis em todos os templates."""
    return {
        "usuario": usuario_atual(silencioso=True),
        "tema": tema_atual(),
        "hoje": relogio.hoje(),
        "caminho_atual": caminho_atual(),
        "csrf_token": token_csrf,
        "filtros_atuais": _filtros_para_links(),
        "filtros_pessoais": _filtros_para_links(com_admin=False),
        "link": _link,
        "versao_css": configuracao.VERSAO_ESTATICOS,
        "PRIORIDADES": configuracao.PRIORIDADES,
        "CATEGORIAS": configuracao.CATEGORIAS,
        "PERIODOS": [("hoje", "Hoje"), ("semana", "Semana"),
                     ("mes", "Mês"), ("todas", "Todas")],
        "SITUACOES": [("todas", "Todas"), ("pendentes", "Pendentes"),
                      ("concluidas", "Concluídas"), ("atrasadas", "Atrasadas")],
    }


# Passo 1: entrar
@app.route("/login", methods=["GET", "POST"])
def login():
    if usuario_atual():
        return redirect(url_for("painel"))

    if request.method == "POST":
        email = request.form.get("login", "")
        try:
            usuario = usuarios.autenticar(email, request.form.get("senha", ""))
        except ErroDeRegra as erro:
            flash(str(erro), "erro")
            return render_template("login.html", login_digitado=email,
                                   bloqueio=usuarios.segundos_de_bloqueio(email))
        # Sessao nova a cada login: o identificador antigo deixa de valer.
        session.clear()
        session.permanent = True
        session["usuario_id"] = usuario.id
        session["csrf"] = secrets.token_urlsafe(32)
        flash("Bem-vindo, %s." % usuario.nome.split()[0], "sucesso")
        return redirect(_destino_seguro(request.args.get("proximo")) or url_for("painel"))

    return render_template("login.html", login_digitado="", bloqueio=0)


@app.route("/cadastro", methods=["GET", "POST"])
def cadastro():
    if usuario_atual():
        return redirect(url_for("painel"))

    if request.method == "POST":
        nome = request.form.get("nome", "")
        email = request.form.get("login", "")
        _, erros = usuarios.cadastrar(nome, email, request.form.get("senha", ""))
        if erros:
            for erro in erros:
                flash(erro, "erro")
            return render_template("cadastro_usuario.html", nome=nome, login_digitado=email)
        flash("Conta criada. Faça login para continuar.", "sucesso")
        return redirect(url_for("login"))

    return render_template("cadastro_usuario.html", nome="", login_digitado="")


@app.route("/sair", methods=["POST"])
def sair():
    """Passo 10 - encerra a sessao. Nenhum dado se perde, cada operação já gravou.

    É POST, e nao um link: sair é uma ação que altera estado, e um GET pode ser
    disparado por qualquer imagem embutida numa página de terceiro.
    """
    session.clear()
    flash("Sessão encerrada.", "sucesso")
    return redirect(url_for("login"))


# Passo 2: painel
@app.route("/")
@exige_login
def painel(usuario):
    filtros = filtros_da_requisicao()
    do_periodo, lista = _listar(usuario, filtros)
    return render_template("painel.html", tarefas=lista, filtros=filtros,
                           resumo=servico_relatorio.gerar(do_periodo))


# Passos 3 e 4: criar/editar
@app.route("/tarefas/nova", methods=["GET", "POST"])
@exige_login
def nova_tarefa(usuario):
    if request.method == "POST":
        dados = _dados_do_formulario()
        _, erros = tarefas.criar(usuario, **dados)
        if erros:
            for erro in erros:
                flash(erro, "erro")
            # Reexibe o formulario preservando o que já havia sido digitado.
            return render_template("formulario_tarefa.html", modo="nova", valores=dados)
        flash("Tarefa criada com sucesso.", "sucesso")
        return redirect(_voltar())

    return render_template("formulario_tarefa.html", modo="nova", valores={
        "titulo": "", "descricao": "", "texto_data": relogio.hoje().isoformat(),
        "prioridade": configuracao.PRIORIDADE_PADRAO,
        "categoria": configuracao.CATEGORIA_PADRAO,
    })


@app.route("/tarefas/<int:id_tarefa>/editar", methods=["GET", "POST"])
@exige_login
def editar_tarefa(usuario, id_tarefa):
    try:
        atual = tarefas.buscar_por_id(id_tarefa, usuario)

        # RN04 - Passo 4.4: nao abre o formulario e oferece o botao Reabrir.
        if validacoes.validar_edicao_permitida(atual):
            return render_template("tarefa_concluida.html", tarefa=atual)

        if request.method == "POST":
            dados = _dados_do_formulario()
            _, erros = tarefas.editar(usuario, id_tarefa, **dados)
            if erros:
                for erro in erros:
                    flash(erro, "erro")
                return render_template("formulario_tarefa.html", modo="editar",
                                       valores=dados, tarefa=atual)
            flash("Tarefa atualizada com sucesso.", "sucesso")
            return redirect(_voltar())
    except ErroDeRegra as erro:
        flash(str(erro), "erro")
        return redirect(_voltar())

    return render_template("formulario_tarefa.html", modo="editar", tarefa=atual, valores={
        "titulo": atual.titulo, "descricao": atual.descricao,
        "texto_data": atual.data_prevista.isoformat(),
        "prioridade": atual.prioridade, "categoria": atual.categoria,
    })


# Passo 5: concluir e reabrir
@app.route("/tarefas/<int:id_tarefa>/concluir", methods=["POST"])
@exige_login
def concluir_tarefa(usuario, id_tarefa):
    try:
        tarefas.concluir(usuario, id_tarefa)
        flash("Tarefa concluída.", "sucesso")
    except ErroDeRegra as erro:
        flash(str(erro), "erro")
    return redirect(_voltar())


@app.route("/tarefas/<int:id_tarefa>/reabrir", methods=["POST"])
@exige_login
def reabrir_tarefa(usuario, id_tarefa):
    try:
        tarefas.reabrir(usuario, id_tarefa)
        flash("Tarefa reaberta.", "sucesso")
    except ErroDeRegra as erro:
        flash(str(erro), "erro")
    return redirect(_voltar())


# Passo 6: excluir
@app.route("/tarefas/<int:id_tarefa>/excluir", methods=["GET", "POST"])
@exige_login
def excluir_tarefa(usuario, id_tarefa):
    """RN06 - o GET mostra a confirmacao, só o POST remove de fato."""
    try:
        alvo = tarefas.buscar_por_id(id_tarefa, usuario)
        if request.method == "POST":
            tarefas.excluir(usuario, id_tarefa)
            flash("Tarefa excluída.", "sucesso")
            return redirect(_voltar())
    except ErroDeRegra as erro:
        flash(str(erro), "erro")
        return redirect(_voltar())

    return render_template("confirmar_exclusao.html", tarefa=alvo)


# Passo 8: relatorio
@app.route("/relatorio")
@exige_login
def relatorio(usuario):
    """Passo 8.2 - o relatorio enxerga exatamente o conjunto que o painel exibe."""
    visao_admin = _pediu_visao_admin()
    if visao_admin:
        erro = validacoes.validar_acesso_administrativo(usuario)
        if erro:
            flash(erro, "erro")
            return redirect(url_for("painel"))

    # O Passo 8.2 lista do que o relatorio deve respeitar: mesmo dono, mesmo
    # periodo, mesma busca. A situacao fica de fora de proposito, pois um relatorio
    # de "só concluidas" teria 100% de conclusao, o que não informa nada.
    filtros = filtros_da_requisicao(periodo_padrao="todas" if visao_admin else None)
    filtros["situacao"] = "todas"         # nao carrega adiante um filtro que ignora
    do_periodo, _ = _listar(usuario, filtros, visao_admin=visao_admin)
    # As tarefas vão junto: poder buscar por titulo sem ver quais titulos
    # bateram deixaria a busca sem resposta.
    return render_template("relatorio.html", resumo=servico_relatorio.gerar(do_periodo),
                           tarefas=do_periodo, limite_lista=LIMITE_DA_LISTA_DO_RELATORIO,
                           donos=usuarios.nomes_por_id() if visao_admin else {},
                           filtros=filtros, visao_admin=visao_admin)


# Passo 9: visao administrativa
@app.route("/admin")
@exige_login
def visao_admin(usuario):
    erro = validacoes.validar_acesso_administrativo(usuario)
    if erro:
        flash(erro, "erro")
        return redirect(url_for("painel"))

    filtros = filtros_da_requisicao(periodo_padrao="todas")
    do_periodo, lista = _listar(usuario, filtros, visao_admin=True)
    return render_template("admin.html", tarefas=lista, filtros=filtros,
                           donos=usuarios.nomes_por_id(),
                           resumo=servico_relatorio.gerar(do_periodo))


# auxiliares
def filtros_da_requisicao(periodo_padrao=None):
    """Lê o periodo, situacao e busca da URL, recusando valores desconhecidos.

    Guarda o resultado em `g` para que os links do menu, montados na
    hora de renderizar, carreguem exatamente o filtro que a tela esta usando,
    e o relatorio enxergue o mesmo conjunto que o painel.
    """
    padrao = periodo_padrao or configuracao.PERIODO_PADRAO
    periodo = request.args.get("periodo", padrao)
    if periodo not in configuracao.PERIODOS:
        periodo = padrao

    situacao = request.args.get("situacao", configuracao.SITUACAO_PADRAO)
    if situacao not in configuracao.SITUACOES:
        situacao = configuracao.SITUACAO_PADRAO

    g.filtros = {"periodo": periodo, "situacao": situacao,
                 "busca": request.args.get("busca", "").strip()}
    return g.filtros


def _filtros_para_links(com_admin=True):
    """Os filtros da tela atual, prontos para virar parametros de URL."""
    filtros = {chave: valor for chave, valor in (g.get("filtros") or {}).items() if valor}
    if com_admin and (_pediu_visao_admin() or request.endpoint == "visao_admin"):
        filtros["admin"] = 1
    return filtros


def _link(endpoint, **mudancas):
    """Monta um endereço preservando os filtros da tela e trocando só o pedido.

    É o que faz um clique em "Semana" manter a busca digitada, e um clique em
    "Relatório" chegar la com o mesmo recorte que o painel estava mostrando.
    """
    parametros = dict(_filtros_para_links())
    parametros.update(mudancas)
    return url_for(endpoint, **{chave: valor for chave, valor in parametros.items()
                                if valor not in (None, "", False)})


def _listar(usuario, filtros, visao_admin=False):
    """Devolve com uma unica leitura.

    A faixa de resumo conta o primeiro, a tabela mostra o segundo: assim os
    quatro numeros continuam sendo uma decomposição do período, e não viram
    "0 concluidas" toda vez que o filtro estiver em "pendentes".
    """
    do_periodo = tarefas.listar(usuario, periodo=filtros["periodo"],
                                busca=filtros["busca"], situacao="todas",
                                visao_admin=visao_admin)
    return do_periodo, tarefas.filtrar_por_situacao(do_periodo, filtros["situacao"])


def _pediu_visao_admin():
    return request.args.get("admin") in ("1", "true", "sim")


def _dados_do_formulario():
    return {
        "titulo": request.form.get("titulo", ""),
        "descricao": request.form.get("descricao", ""),
        "texto_data": request.form.get("data_prevista", ""),
        "prioridade": request.form.get("prioridade", ""),
        "categoria": request.form.get("categoria", ""),
    }


def _destino_seguro(destino):
    """Aceita apenas caminhos deste servidor.

    Um `//outro-site.com` comeca com barra e passaria por uma checagem ingenua,
    mas o navegador o interpreta como endereco absoluto e sai da aplicacao.
    """
    if not destino:
        return None
    partes = urlsplit(destino)
    if partes.scheme or partes.netloc or not partes.path.startswith("/"):
        return None
    return destino


def _voltar():
    """Volta para a tela de origem preservando filtro, busca e situacao."""
    origem = request.form.get("voltar_para") or request.args.get("voltar_para")
    return _destino_seguro(origem) or url_for("painel")


# paginas de erro
@app.errorhandler(400)
def requisicao_invalida(_erro):
    return render_template(
        "erro.html", codigo=400, titulo="Requisição recusada",
        mensagem="O formulário expirou ou veio de outra origem. "
                 "Volte, recarregue a página e tente de novo."), 400


@app.errorhandler(404)
def pagina_nao_encontrada(_erro):
    return render_template("erro.html", codigo=404,
                           titulo="Página não encontrada",
                           mensagem="O endereço acessado não existe no sistema."), 404


@app.errorhandler(405)
def metodo_nao_permitido(_erro):
    return render_template(
        "erro.html", codigo=405, titulo="Ação inválida",
        mensagem="Esta página não aceita esse tipo de envio."), 405


@app.errorhandler(413)
def conteudo_grande_demais(_erro):
    return render_template(
        "erro.html", codigo=413, titulo="Envio grande demais",
        mensagem="O formulário enviado excede o tamanho aceito pelo sistema."), 413


@app.errorhandler(ArquivoCorrompido)
def arquivo_corrompido(erro):
    return render_template("erro.html", codigo=500,
                           titulo="Arquivo de dados ilegível",
                           mensagem=str(erro)), 500


@app.errorhandler(500)
def erro_interno(_erro):
    return render_template(
        "erro.html", codigo=500, titulo="Erro interno",
        mensagem="Algo deu errado ao processar a página. "
                 "Nenhum dado foi alterado."), 500


# Passo 0: preparacao
def preparar():
    """Cria a pasta e os arquivos de dados e garante o administrador padrao."""
    os.makedirs(configuracao.PASTA_DADOS, exist_ok=True)
    tarefas.repositorio.garantir_arquivo()
    usuarios.repositorio.garantir_arquivo()
    return usuarios.garantir_admin_padrao()


def usar_pasta_de_dados(pasta):
    """Aponta o sistema para outra pasta de dados.

    Serve aos testes de rota, que precisam de um disco proprio, e a quem quiser
    rodar duas instancias na mesma maquina.
    """
    global _preparado
    configuracao.PASTA_DADOS = pasta
    configuracao.ARQUIVO_TAREFAS = os.path.join(pasta, "tarefas.json")
    configuracao.ARQUIVO_USUARIOS = os.path.join(pasta, "usuarios.json")
    tarefas.repositorio.caminho = configuracao.ARQUIVO_TAREFAS
    usuarios.repositorio.caminho = configuracao.ARQUIVO_USUARIOS
    usuarios._falhas.clear()
    _preparado = False


def _avisos_de_inicializacao(admin):
    avisos = []
    if admin:
        avisos.append("Administrador padrão criado: %s / %s"
                      % (configuracao.ADMIN_PADRAO_LOGIN, configuracao.ADMIN_PADRAO_SENHA))
    if configuracao.ADMIN_SENHA_PADRAO_EM_USO:
        avisos.append("A senha do administrador é a padrão. "
                      "Defina TASKTRACKER_ADMIN_SENHA antes do primeiro uso real.")
    if configuracao.CHAVE_SECRETA_SORTEADA:
        avisos.append("TASKTRACKER_CHAVE_SECRETA não definida: uma chave "
                      "aleatória foi sorteada e as sessões caem a cada reinício.")
    if configuracao.MODO_DEBUG:
        avisos.append("Modo de depuração LIGADO — não use assim fora da sua máquina.")
    avisos.extend(tarefas.incoerencias())
    return avisos


# modo de execucao
def _modo_de_execucao(argumentos, interativo=None):
    """Decide entre "cli" e "web" a partir da linha de comando.

    Sem argumento e com um terminal interativo, o programa abre a tela de
    escolha entre o terminal e o web app. Sem terminal (Docker, redirecionamento,
    CI) nao há a quem perguntar: sobe o web app, que é o comportamento planejado.
    `--web` e `--cli` pulam a pergunta.
    """
    analisador = argparse.ArgumentParser(
        prog="python -m src.app",
        description="Task Tracker — sem opção, pergunta qual interface usar.")
    grupo = analisador.add_mutually_exclusive_group()
    grupo.add_argument("--web", action="store_true", help="sobe o web app direto, sem perguntar")
    grupo.add_argument("--cli", action="store_true",
                       help="entra na interface de terminal direto, sem perguntar")
    opcoes = analisador.parse_args(argumentos)
    if opcoes.web:
        return "web"
    if opcoes.cli:
        return "cli"
    # O recarregador do modo de depuracao do Flask relança este arquivo num
    # processo filho: lá a escolha já foi feita, e perguntar de novo travaria.
    if os.environ.get("WERKZEUG_RUN_MAIN") == "true":
        return "web"
    if interativo is None:
        interativo = sys.stdin.isatty() and sys.stdout.isatty()
    return "escolher" if interativo else "web"


def _endereco_do_servidor():
    host = "127.0.0.1" if configuracao.HOST == "0.0.0.0" else configuracao.HOST
    return "http://%s:%d" % (host, configuracao.PORTA)


def _abrir_navegador_em_breve(endereco, atraso=1.0):
    """Abre o navegador logo depois do servidor comecar a escutar."""
    cronometro = threading.Timer(atraso, webbrowser.open, [endereco])
    cronometro.daemon = True
    cronometro.start()


if __name__ == "__main__":
    modo = _modo_de_execucao(sys.argv[1:])
    print("\n  Task Tracker — Bootcamp II")
    try:
        novo_admin = preparar()
        _preparado = True
    except ArquivoCorrompido as erro:
        print("\n  ERRO: %s\n" % erro)
        sys.exit(1)
    avisos = _avisos_de_inicializacao(novo_admin)

    abrir_navegador = False
    if modo != "web":
        from src.cli import iniciar
        pedido = iniciar(usuarios, tarefas, avisos, direto_no_cli=(modo == "cli"))
        if pedido != "web":
            print("  Até logo.\n")
            sys.exit(0)
        # Quem escolheu o app web pela tela quer ve-lo aberto, não ter que abrir tudo.
        abrir_navegador = True

    for aviso in avisos:
        print("  · %s" % aviso)
    print("  Servidor em http://%s:%d\n" % (configuracao.HOST, configuracao.PORTA))
    if abrir_navegador:
        _abrir_navegador_em_breve(_endereco_do_servidor())
    app.run(host=configuracao.HOST, port=configuracao.PORTA, debug=configuracao.MODO_DEBUG)
