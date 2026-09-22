"""Cadastro, autenticacao e controle de perfil - Passos 0 e 1 do algoritmo."""
from datetime import timedelta

from src import configuracao
from src.modelos.usuario import Usuario
from src.repositorio.repositorio_json import RepositorioJson
from src.servicos import relogio, validacoes
from src.servicos.validacoes import ErroDeRegra


class GerenciadorUsuarios:
    def __init__(self, repositorio=None):
        self.repositorio = repositorio or RepositorioJson(configuracao.ARQUIVO_USUARIOS)
        # login {"tentativas": int, "bloqueado_ate": datetime | None}
        # Fica em memoria de proposito. O bloqueio protege contra tentativa em
        # sequência, não precisa sobreviver a reinicializacao do servidor.
        self._falhas = {}

    # carga e escrita
    def listar_todos(self):
        return [Usuario.de_dict(registro) for registro in self.repositorio.carregar()]

    def _gravar(self, usuarios):
        self.repositorio.salvar([usuario.para_dict() for usuario in usuarios])

    def _proximo_id(self, usuarios):
        return max((usuario.id for usuario in usuarios), default=0) + 1

    # consulta
    def buscar_por_id(self, id_usuario):
        for usuario in self.listar_todos():
            if usuario.id == id_usuario:
                return usuario
        return None

    def buscar_por_login(self, login):
        alvo = (login or "").strip().lower()
        for usuario in self.listar_todos():
            if usuario.login == alvo:
                return usuario
        return None

    def nomes_por_id(self):
        """Mapa {id: nome}, usado pela visao administrativa."""
        return {usuario.id: usuario.nome for usuario in self.listar_todos()}

    # Passo 0: admin seed
    def garantir_admin_padrao(self):
        """Passo 0.2 - na primeira execucao, cria o administrador padrao."""
        usuarios = self.listar_todos()
        if any(usuario.eh_admin for usuario in usuarios):
            return None
        admin = Usuario.criar(
            id=self._proximo_id(usuarios),
            nome=configuracao.ADMIN_PADRAO_NOME,
            login=configuracao.ADMIN_PADRAO_LOGIN,
            senha=configuracao.ADMIN_PADRAO_SENHA,
            perfil=configuracao.PERFIL_ADMIN,
        )
        usuarios.append(admin)
        self._gravar(usuarios)
        return admin

    # Passo 1.2: conta
    def cadastrar(self, nome, login, senha):
        """Devolve (usuario, erros). Novas contas nascem sempre com perfil comum."""
        erros = [erro for erro in (validacoes.validar_nome(nome),
                                   validacoes.validar_email(login),
                                   validacoes.validar_senha(senha)) if erro]
        if erros:
            return None, erros

        usuarios = self.listar_todos()
        alvo = login.strip().lower()
        if any(usuario.login == alvo for usuario in usuarios):
            return None, ["Já existe uma conta com este e-mail."]

        novo = Usuario.criar(
            id=self._proximo_id(usuarios),
            nome=nome.strip(),
            login=login,
            senha=senha,
            perfil=configuracao.PERFIL_COMUM,
        )
        usuarios.append(novo)
        self._gravar(usuarios)
        return novo, []

    # aparencia
    def definir_tema(self, id_usuario, tema):
        """Grava a preferencia de tema na conta. Devolve o tema em vigor."""
        if tema not in configuracao.TEMAS:
            tema = configuracao.TEMA_PADRAO
        usuarios = self.listar_todos()
        for usuario in usuarios:
            if usuario.id == id_usuario:
                usuario.tema = tema
                self._gravar(usuarios)
                return tema
        return configuracao.TEMA_PADRAO

    # Passo 1.3 a 1.7
    def autenticar(self, login, senha):
        """Confere as credenciais, respeitando o limite de tentativas."""
        chave = (login or "").strip().lower()

        restantes = self.segundos_de_bloqueio(chave)
        if restantes:
            raise ErroDeRegra(
                "Muitas tentativas seguidas. Tente novamente em %d segundos."
                % restantes)

        usuario = self.buscar_por_login(chave)
        # Mensagem generica de proposito, sem revelar se o erro foi e-mail ou senha.
        if usuario is None or not usuario.senha_confere(senha or ""):
            self._registrar_falha(chave)
            raise ErroDeRegra("E-mail ou senha inválidos.")

        self._falhas.pop(chave, None)
        return usuario

    # bloqueio
    def segundos_de_bloqueio(self, login, agora=None):
        """Quantos segundos ainda faltam para o login ser liberado (0 = liberado)."""
        agora = agora or relogio.agora()
        registro = self._falhas.get((login or "").strip().lower())
        if not registro or not registro["bloqueado_ate"]:
            return 0
        if agora >= registro["bloqueado_ate"]:
            return 0
        return int((registro["bloqueado_ate"] - agora).total_seconds()) + 1

    def _registrar_falha(self, login, agora=None):
        agora = agora or relogio.agora()
        registro = self._falhas.setdefault(login, {"tentativas": 0, "bloqueado_ate": None})
        registro["tentativas"] += 1
        if registro["tentativas"] >= configuracao.MAXIMO_TENTATIVAS_LOGIN:
            registro["bloqueado_ate"] = agora + timedelta(
                seconds=configuracao.SEGUNDOS_DE_BLOQUEIO)
            registro["tentativas"] = 0
