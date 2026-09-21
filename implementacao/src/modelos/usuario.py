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


