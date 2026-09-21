# Entidade Usuario - tradução direta do modelo de dados da Etapa 1.
from werkzeug.security import check_password_hash, generate_password_hash

from src import configuracao


class Usuario:
    # Classe Usuario representa um usuario do sistema. 
    # Cada usuario tem um perfil, que define o que ele pode fazer.

    def __init__(self, id, nome, login, senha_hash, perfil=configuracao.PERFIL_COMUM,
                 tema=configuracao.TEMA_PADRAO):
        self.id = id
        self.nome = nome
        self.login = login
        self.senha_hash = senha_hash # A senha nunca e guardada em texto puro.

        self.perfil = perfil
        # Preferencia de tema. É armazenado na conta.
        self.tema = tema if tema in configuracao.TEMAS else configuracao.TEMA_PADRAO

    # criacao
    @classmethod
    def criar(cls, id, nome, login, senha, perfil=configuracao.PERFIL_COMUM):
        """Cria o usuario ja embaralhando a senha."""
        return cls(id=id, nome=nome, login=login.strip().lower(),
                   senha_hash=generate_password_hash(senha), perfil=perfil)

    # checagens
    def senha_confere(self, senha):
        return check_password_hash(self.senha_hash, senha)

    @property
    def eh_admin(self):
        return self.perfil == configuracao.PERFIL_ADMIN

    # conversao
    def para_dict(self):
        return {
            "id": self.id,
            "nome": self.nome,
            "login": self.login,
            "senha": self.senha_hash,
            "perfil": self.perfil,
            "tema": self.tema,
        }

    @classmethod
    def de_dict(cls, dados):
        return cls(
            id=dados["id"],
            nome=dados["nome"],
            login=dados["login"],
            senha_hash=dados["senha"],
            perfil=dados.get("perfil", configuracao.PERFIL_COMUM),
            tema=dados.get("tema", configuracao.TEMA_PADRAO),
        )

    def __repr__(self):
        return "<Usuario #%s %r (%s)>" % (self.id, self.login, self.perfil)
