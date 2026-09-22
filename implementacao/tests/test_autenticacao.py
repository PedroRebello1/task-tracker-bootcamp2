"""Testa cadastro, login, bloqueio por tentativas e o administrador padrao."""
import json
from datetime import datetime, timedelta

import pytest

from src import configuracao
from src.repositorio.repositorio_json import ArquivoCorrompido, RepositorioJson
from src.servicos.gerenciador_usuarios import GerenciadorUsuarios
from src.servicos.validacoes import ErroDeRegra


@pytest.fixture
def gerenciador(tmp_path):
    return GerenciadorUsuarios(RepositorioJson(str(tmp_path / "usuarios.json")))


# cadastro
class TestCadastro:
    def test_conta_valida_e_criada_com_perfil_comum(self, gerenciador):
        usuario, erros = gerenciador.cadastrar("Pedro", "pedro@x.com", "senha123")
        assert erros == []
        assert usuario.perfil == configuracao.PERFIL_COMUM

    def test_senha_nunca_e_guardada_em_texto_puro(self, gerenciador):
        usuario, _ = gerenciador.cadastrar("Pedro", "pedro@x.com", "senha123")
        assert usuario.senha_hash != "senha123"
        assert usuario.senha_confere("senha123")

    def test_email_duplicado_e_recusado(self, gerenciador):
        gerenciador.cadastrar("Pedro", "pedro@x.com", "senha123")
        _, erros = gerenciador.cadastrar("Outro", "pedro@x.com", "outrasenha")
        assert erros == ["Já existe uma conta com este e-mail."]

    def test_email_duplicado_ignora_caixa(self, gerenciador):
        gerenciador.cadastrar("Pedro", "pedro@x.com", "senha123")
        _, erros = gerenciador.cadastrar("Outro", "PEDRO@X.COM", "outrasenha")
        assert erros != []

    def test_senha_curta_e_recusada(self, gerenciador):
        _, erros = gerenciador.cadastrar("Pedro", "pedro@x.com", "123")
        assert "6 caracteres" in erros[0]

    def test_conta_recusada_nao_e_gravada(self, gerenciador):
        gerenciador.cadastrar("", "", "")
        assert gerenciador.listar_todos() == []


# autenticacao
class TestAutenticacao:
    def test_credenciais_corretas_devolvem_o_usuario(self, gerenciador):
        gerenciador.cadastrar("Pedro", "pedro@x.com", "senha123")
        assert gerenciador.autenticar("pedro@x.com", "senha123").nome == "Pedro"

    def test_login_aceita_caixa_diferente(self, gerenciador):
        gerenciador.cadastrar("Pedro", "pedro@x.com", "senha123")
        assert gerenciador.autenticar("PEDRO@x.com", "senha123") is not None

    def test_senha_errada_e_recusada(self, gerenciador):
        gerenciador.cadastrar("Pedro", "pedro@x.com", "senha123")
        with pytest.raises(ErroDeRegra, match="E-mail ou senha inválidos"):
            gerenciador.autenticar("pedro@x.com", "errada")

    def test_email_inexistente_da_a_mesma_mensagem_que_senha_errada(self, gerenciador):
        """De proposito: nao revela qual dos dois campos esta errado."""
        gerenciador.cadastrar("Pedro", "pedro@x.com", "senha123")
        with pytest.raises(ErroDeRegra) as sem_email:
            gerenciador.autenticar("ninguem@x.com", "qualquer")
        with pytest.raises(ErroDeRegra) as senha_ruim:
            gerenciador.autenticar("pedro@x.com", "errada")
        assert str(sem_email.value) == str(senha_ruim.value)


# bloqueio
class TestBloqueioPorTentativas:
    def test_bloqueia_na_terceira_falha(self, gerenciador):
        gerenciador.cadastrar("Pedro", "pedro@x.com", "senha123")
        for _ in range(configuracao.MAXIMO_TENTATIVAS_LOGIN):
            with pytest.raises(ErroDeRegra):
                gerenciador.autenticar("pedro@x.com", "errada")
        with pytest.raises(ErroDeRegra, match="Muitas tentativas"):
            gerenciador.autenticar("pedro@x.com", "senha123")

    def test_duas_falhas_ainda_nao_bloqueiam(self, gerenciador):
        gerenciador.cadastrar("Pedro", "pedro@x.com", "senha123")
        for _ in range(configuracao.MAXIMO_TENTATIVAS_LOGIN - 1):
            with pytest.raises(ErroDeRegra):
                gerenciador.autenticar("pedro@x.com", "errada")
        assert gerenciador.autenticar("pedro@x.com", "senha123") is not None

    def test_acerto_zera_a_contagem(self, gerenciador):
        gerenciador.cadastrar("Pedro", "pedro@x.com", "senha123")
        with pytest.raises(ErroDeRegra):
            gerenciador.autenticar("pedro@x.com", "errada")
        gerenciador.autenticar("pedro@x.com", "senha123")
        with pytest.raises(ErroDeRegra):
            gerenciador.autenticar("pedro@x.com", "errada")
        assert gerenciador.segundos_de_bloqueio("pedro@x.com") == 0

    def test_bloqueio_expira_depois_do_prazo(self, gerenciador):
        gerenciador.cadastrar("Pedro", "pedro@x.com", "senha123")
        for _ in range(configuracao.MAXIMO_TENTATIVAS_LOGIN):
            with pytest.raises(ErroDeRegra):
                gerenciador.autenticar("pedro@x.com", "errada")
        futuro = datetime.now() + timedelta(seconds=configuracao.SEGUNDOS_DE_BLOQUEIO + 1)
        assert gerenciador.segundos_de_bloqueio("pedro@x.com", agora=futuro) == 0

    def test_bloqueio_e_por_login(self, gerenciador):
        gerenciador.cadastrar("Pedro", "pedro@x.com", "senha123")
        gerenciador.cadastrar("Ana", "ana@x.com", "senha123")
        for _ in range(configuracao.MAXIMO_TENTATIVAS_LOGIN):
            with pytest.raises(ErroDeRegra):
                gerenciador.autenticar("pedro@x.com", "errada")
        assert gerenciador.autenticar("ana@x.com", "senha123") is not None


# administrador padrao
class TestAdministradorPadrao:
    def test_e_criado_na_primeira_execucao(self, gerenciador):
        admin = gerenciador.garantir_admin_padrao()
        assert admin is not None and admin.eh_admin

    def test_nao_e_duplicado_nas_execucoes_seguintes(self, gerenciador):
        gerenciador.garantir_admin_padrao()
        assert gerenciador.garantir_admin_padrao() is None
        assert len(gerenciador.listar_todos()) == 1

    def test_admin_padrao_consegue_entrar(self, gerenciador):
        gerenciador.garantir_admin_padrao()
        usuario = gerenciador.autenticar(configuracao.ADMIN_PADRAO_LOGIN,
                                         configuracao.ADMIN_PADRAO_SENHA)
        assert usuario.eh_admin

    def test_contas_novas_nunca_nascem_admin(self, gerenciador):
        gerenciador.garantir_admin_padrao()
        usuario, _ = gerenciador.cadastrar("Pedro", "pedro@x.com", "senha123")
        assert not usuario.eh_admin


# arquivos de dados
class TestArquivoDeDados:
    def test_arquivo_inexistente_e_criado_vazio(self, tmp_path):
        repo = RepositorioJson(str(tmp_path / "novo.json"))
        assert repo.carregar() == []

    def test_arquivo_corrompido_nao_e_sobrescrito(self, tmp_path):
        caminho = tmp_path / "quebrado.json"
        caminho.write_text("{isso não é json}", encoding="utf-8")
        repo = RepositorioJson(str(caminho))
        with pytest.raises(ArquivoCorrompido):
            repo.carregar()
        assert caminho.read_text(encoding="utf-8") == "{isso não é json}"

    def test_json_que_nao_e_lista_e_recusado(self, tmp_path):
        caminho = tmp_path / "objeto.json"
        caminho.write_text(json.dumps({"a": 1}), encoding="utf-8")
        with pytest.raises(ArquivoCorrompido):
            RepositorioJson(str(caminho)).carregar()

    def test_gravacao_e_releitura_preservam_acentos(self, tmp_path):
        repo = RepositorioJson(str(tmp_path / "acentos.json"))
        repo.salvar([{"titulo": "Revisão de Cálculo"}])
        assert repo.carregar()[0]["titulo"] == "Revisão de Cálculo"
