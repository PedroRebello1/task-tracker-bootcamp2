"""Peças compartilhadas pelos testes.

O cliente HTTP aponta para uma pasta de dados temporária: nenhum teste toca os
arquivos reais de `implementacao/dados/`. 
"""
import pytest

from src import app as modulo
from src import configuracao


@pytest.fixture
def pasta(tmp_path):
    """Redireciona o armazenamento do app para um disco só deste teste."""
    original = configuracao.PASTA_DADOS
    modulo.usar_pasta_de_dados(str(tmp_path))
    yield str(tmp_path)
    modulo.usar_pasta_de_dados(original)


@pytest.fixture
def aplicacao(pasta):
    modulo.app.config.update(TESTING=True, SERVER_NAME=None)
    modulo.app.secret_key = "chave-fixa-de-teste"
    return modulo.app


@pytest.fixture
def cliente(aplicacao):
    with aplicacao.test_client() as cliente:
        yield cliente


@pytest.fixture
def contas(cliente):
    """Duas contas comuns, criadas direto pelo serviço (o cadastro tem teste próprio)."""
    pedro, _ = modulo.usuarios.cadastrar("Pedro", "pedro@x.com", "senha123")
    ana, _ = modulo.usuarios.cadastrar("Ana", "ana@x.com", "senha123")
    return {"pedro": pedro, "ana": ana}


def csrf(cliente):
    """O token da sessão atual, semeado quando ainda não existe."""
    with cliente.session_transaction() as sessao:
        if "csrf" not in sessao:
            sessao["csrf"] = "token-de-teste"
        return sessao["csrf"]


def postar(cliente, url, **dados):
    """POST já com o token de CSRF anexado."""
    dados.setdefault("csrf", csrf(cliente))
    return cliente.post(url, data=dados, follow_redirects=True)


def entrar(cliente, login="pedro@x.com", senha="senha123"):
    resposta = postar(cliente, "/login", login=login, senha=senha)
    assert resposta.status_code == 200
    return resposta


def texto(resposta):
    return resposta.get_data(as_text=True)
