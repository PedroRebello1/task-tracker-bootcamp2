"""Testes das rotas — o comportamento que o navegador realmente encontra.

Os outros arquivos testam as regras isoladas. Aqui o alvo é o que só existe na
camada HTTP: a confirmação em duas etapas da RN06, o isolamento da RN05 quando
alguém digita o endereço de outro usuário, a proteção contra CSRF, as páginas
de erro e a preservação dos filtros entre o painel e o relatório. 
"""
import re
from datetime import timedelta

import pytest

from src import app as modulo
from src import configuracao
from src.servicos import relogio

from .conftest import csrf, entrar, postar, texto


def criar_tarefa(cliente, titulo="Estudar", dias=0, prioridade="Média", categoria="Estudo"):
    data = (relogio.hoje() + timedelta(days=dias)).isoformat()
    resposta = postar(cliente, "/tarefas/nova", titulo=titulo, descricao="",
                      data_prevista=data, prioridade=prioridade, categoria=categoria)
    assert "Tarefa criada com sucesso" in texto(resposta)
    return modulo.tarefas.listar_todas()[-1]


# ------------------------------------------------------------- Passo 0 e 1
class TestAcessoESessao:
    def test_visitante_na_raiz_cai_no_login_limpo(self, cliente):
        """Abrir o sistema deslogado não é um erro: não há o que avisar."""
        resposta = cliente.get("/")
        assert resposta.headers["Location"] == "/login"
        assert "Faça login para continuar." not in texto(
            cliente.get("/", follow_redirects=True))

    def test_link_profundo_avisa_e_guarda_o_destino(self, cliente):
        resposta = cliente.get("/relatorio?periodo=todas")
        assert resposta.headers["Location"] == "/login?proximo=/relatorio?periodo%3Dtodas"
        assert "Faça login para continuar." in texto(
            cliente.get("/relatorio?periodo=todas", follow_redirects=True))

    def test_depois_de_entrar_volta_ao_destino_pedido(self, cliente, contas):
        cliente.get("/relatorio?periodo=todas", follow_redirects=True)
        resposta = cliente.post("/login?proximo=/relatorio?periodo%3Dtodas", data={
            "csrf": csrf(cliente), "login": "pedro@x.com", "senha": "senha123"})
        assert resposta.headers["Location"] == "/relatorio?periodo=todas"

    def test_administrador_padrao_e_criado_na_primeira_requisicao(self, cliente):
        cliente.get("/login")
        logins = [u.login for u in modulo.usuarios.listar_todos()]
        assert configuracao.ADMIN_PADRAO_LOGIN in logins

    def test_login_e_logout(self, cliente, contas):
        assert "Bem-vindo, Pedro." in texto(entrar(cliente))
        assert "Minhas tarefas" in texto(cliente.get("/"))
        assert "Sessão encerrada." in texto(postar(cliente, "/sair"))
        assert "Criar conta" in texto(cliente.get("/", follow_redirects=True))

    def test_sair_nao_responde_a_get(self, cliente, contas):
        entrar(cliente)
        assert cliente.get("/sair").status_code == 405

    def test_login_troca_o_identificador_da_sessao(self, cliente, contas):
        cliente.get("/login")
        with cliente.session_transaction() as sessao:
            antes = sessao.get("csrf")
        entrar(cliente)
        with cliente.session_transaction() as sessao:
            assert sessao["csrf"] != antes

    def test_cadastro_pela_tela_cria_conta_comum(self, cliente):
        resposta = postar(cliente, "/cadastro", nome="Novo",
                          login="novo@x.com", senha="senha123")
        assert "Conta criada" in texto(resposta)
        assert not modulo.usuarios.buscar_por_login("novo@x.com").eh_admin

    def test_bloqueio_aparece_na_tela_apos_tres_falhas(self, cliente, contas):
        for _ in range(configuracao.MAXIMO_TENTATIVAS_LOGIN):
            postar(cliente, "/login", login="pedro@x.com", senha="errada")
        resposta = postar(cliente, "/login", login="pedro@x.com", senha="senha123")
        corpo = texto(resposta)
        assert "Muitas tentativas" in corpo
        assert "disabled" in corpo          # o formulário fica realmente bloqueado


# ------------------------------------------------------------------- CSRF
class TestProtecaoCsrf:
    def test_post_sem_token_e_recusado(self, cliente, contas):
        entrar(cliente)
        resposta = cliente.post("/tarefas/nova", data={"titulo": "Sem token"})
        assert resposta.status_code == 400
        assert modulo.tarefas.listar_todas() == []

    def test_post_com_token_errado_e_recusado(self, cliente, contas):
        entrar(cliente)
        resposta = cliente.post("/tarefas/nova", data={"titulo": "X", "csrf": "outro"})
        assert resposta.status_code == 400

    def test_o_formulario_realmente_entrega_o_token(self, cliente, contas):
        """Garante que a proteção não depende de os testes semearem a sessão."""
        entrar(cliente)
        pagina = texto(cliente.get("/tarefas/nova"))
        achado = re.search(r'name="csrf" value="([^"]+)"', pagina)
        assert achado, "o formulário não trouxe o campo csrf"
        data = relogio.hoje().isoformat()
        resposta = cliente.post("/tarefas/nova", follow_redirects=True, data={
            "csrf": achado.group(1), "titulo": "Com token do HTML", "descricao": "",
            "data_prevista": data, "prioridade": "Alta", "categoria": "Estudo"})
        assert "Tarefa criada com sucesso" in texto(resposta)


# ------------------------------------------------------- Passos 3, 4 e 5
class TestCicloDaTarefa:
    def test_criar_editar_concluir_e_reabrir(self, cliente, contas):
        entrar(cliente)
        tarefa = criar_tarefa(cliente, "Original")

        editada = postar(cliente, "/tarefas/%d/editar" % tarefa.id,
                         titulo="Editada", descricao="detalhe",
                         data_prevista=relogio.hoje().isoformat(),
                         prioridade="Alta", categoria="Trabalho")
        assert "Tarefa atualizada com sucesso" in texto(editada)

        assert "Tarefa concluída." in texto(postar(cliente, "/tarefas/%d/concluir" % tarefa.id))
        assert "Tarefa reaberta." in texto(postar(cliente, "/tarefas/%d/reabrir" % tarefa.id))

    def test_rn01_titulo_vazio_reexibe_o_formulario_preservando_o_resto(self, cliente, contas):
        entrar(cliente)
        resposta = postar(cliente, "/tarefas/nova", titulo="  ", descricao="não perder isto",
                          data_prevista=relogio.hoje().isoformat(),
                          prioridade="Alta", categoria="Saúde")
        corpo = texto(resposta)
        assert "Informe um título para a tarefa." in corpo
        assert "não perder isto" in corpo          # Passo 3.5
        assert modulo.tarefas.listar_todas() == []

    def test_rn02_data_retroativa_e_recusada_pelo_servidor(self, cliente, contas):
        entrar(cliente)
        ontem = (relogio.hoje() - timedelta(days=1)).isoformat()
        resposta = postar(cliente, "/tarefas/nova", titulo="Atrasar", descricao="",
                          data_prevista=ontem, prioridade="Alta", categoria="Geral")
        assert "não pode ser anterior a hoje" in texto(resposta)

    def test_rn03_prioridade_forjada_e_recusada(self, cliente, contas):
        entrar(cliente)
        resposta = postar(cliente, "/tarefas/nova", titulo="Forjada", descricao="",
                          data_prevista=relogio.hoje().isoformat(),
                          prioridade="Urgentíssima", categoria="Geral")
        assert "Prioridade inválida" in texto(resposta)

    def test_categoria_ausente_cai_no_padrao(self, cliente, contas):
        """A Etapa 1 marca categoria como opcional — o envio sem ela tem de passar."""
        entrar(cliente)
        resposta = postar(cliente, "/tarefas/nova", titulo="Sem categoria", descricao="",
                          data_prevista=relogio.hoje().isoformat(), prioridade="Alta")
        assert "Tarefa criada com sucesso" in texto(resposta)
        assert modulo.tarefas.listar_todas()[0].categoria == configuracao.CATEGORIA_PADRAO

    def test_rn04_editar_concluida_mostra_a_tela_de_reabrir(self, cliente, contas):
        entrar(cliente)
        tarefa = criar_tarefa(cliente)
        postar(cliente, "/tarefas/%d/concluir" % tarefa.id)

        pagina = texto(cliente.get("/tarefas/%d/editar" % tarefa.id))
        assert "Esta tarefa está concluída" in pagina
        assert "Reabrir e editar" in pagina          # Passo 4.4
        assert "Salvar alterações" not in pagina     # o formulário não abriu

    def test_rn04_tambem_barra_o_post_direto(self, cliente, contas):
        entrar(cliente)
        tarefa = criar_tarefa(cliente, "Intocável")
        postar(cliente, "/tarefas/%d/concluir" % tarefa.id)
        postar(cliente, "/tarefas/%d/editar" % tarefa.id, titulo="Reescrita",
               descricao="", data_prevista=relogio.hoje().isoformat(),
               prioridade="Alta", categoria="Geral")
        assert modulo.tarefas.listar_todas()[0].titulo == "Intocável"

    def test_id_inexistente_avisa_e_volta(self, cliente, contas):
        entrar(cliente)
        assert "Tarefa não encontrada." in texto(
            cliente.get("/tarefas/999/editar", follow_redirects=True))


# ------------------------------------------------------------- Passo 6 / RN06
class TestRN06Confirmacao:
    def test_get_apenas_pergunta_e_nao_remove(self, cliente, contas):
        entrar(cliente)
        tarefa = criar_tarefa(cliente, "Sobrevivente")
        pagina = texto(cliente.get("/tarefas/%d/excluir" % tarefa.id))
        assert "Esta ação não pode ser desfeita." in pagina
        assert "Sobrevivente" in pagina
        assert len(modulo.tarefas.listar_todas()) == 1      # nada foi removido

    def test_post_remove(self, cliente, contas):
        entrar(cliente)
        tarefa = criar_tarefa(cliente)
        assert "Tarefa excluída." in texto(postar(cliente, "/tarefas/%d/excluir" % tarefa.id))
        assert modulo.tarefas.listar_todas() == []

    def test_cancelar_nao_altera_o_arquivo(self, cliente, contas):
        entrar(cliente)
        tarefa = criar_tarefa(cliente)
        cliente.get("/tarefas/%d/excluir" % tarefa.id)
        cliente.get("/")                                     # equivale a clicar em Cancelar
        assert len(modulo.tarefas.listar_todas()) == 1


# -------------------------------------------------------------- RN05 por HTTP
class TestRN05PorHttp:
    @pytest.fixture
    def tarefa_do_pedro(self, cliente, contas):
        entrar(cliente)
        tarefa = criar_tarefa(cliente, "Só do Pedro")
        postar(cliente, "/sair")
        return tarefa

    def test_outro_usuario_nao_abre_a_edicao(self, cliente, tarefa_do_pedro):
        entrar(cliente, "ana@x.com")
        resposta = cliente.get("/tarefas/%d/editar" % tarefa_do_pedro.id,
                               follow_redirects=True)
        assert "Você não tem permissão para acessar esta tarefa." in texto(resposta)

    def test_outro_usuario_nao_exclui(self, cliente, tarefa_do_pedro):
        entrar(cliente, "ana@x.com")
        postar(cliente, "/tarefas/%d/excluir" % tarefa_do_pedro.id)
        assert len(modulo.tarefas.listar_todas()) == 1

    def test_outro_usuario_nao_ve_no_painel(self, cliente, tarefa_do_pedro):
        entrar(cliente, "ana@x.com")
        assert "Só do Pedro" not in texto(cliente.get("/?periodo=todas"))

    def test_visao_administrativa_e_restrita(self, cliente, contas):
        entrar(cliente)
        assert "Acesso restrito ao administrador." in texto(
            cliente.get("/admin", follow_redirects=True))

    def test_relatorio_administrativo_tambem_e_restrito(self, cliente, contas):
        entrar(cliente)
        assert "Acesso restrito ao administrador." in texto(
            cliente.get("/relatorio?admin=1", follow_redirects=True))

    def test_admin_ve_tudo_com_a_coluna_do_dono(self, cliente, tarefa_do_pedro):
        entrar(cliente, configuracao.ADMIN_PADRAO_LOGIN, configuracao.ADMIN_PADRAO_SENHA)
        pagina = texto(cliente.get("/admin?periodo=todas"))
        assert "Só do Pedro" in pagina and "Pedro" in pagina


# ------------------------------------------------------- filtros e relatório
class TestFiltrosERelatorio:
    @pytest.fixture
    def povoado(self, cliente, contas):
        entrar(cliente)
        criar_tarefa(cliente, "De hoje", dias=0)
        futura = criar_tarefa(cliente, "Do mês que vem", dias=32)
        feita = criar_tarefa(cliente, "Já feita", dias=0)
        postar(cliente, "/tarefas/%d/concluir" % feita.id)
        return {"futura": futura, "feita": feita}

    def test_filtro_de_periodo(self, cliente, povoado):
        assert "Do mês que vem" not in texto(cliente.get("/?periodo=hoje"))
        assert "Do mês que vem" in texto(cliente.get("/?periodo=todas"))

    def test_filtro_de_situacao(self, cliente, povoado):
        pendentes = texto(cliente.get("/?periodo=todas&situacao=pendentes"))
        assert "De hoje" in pendentes and "Já feita" not in pendentes

        concluidas = texto(cliente.get("/?periodo=todas&situacao=concluidas"))
        assert "Já feita" in concluidas and "De hoje" not in concluidas

    def test_periodo_desconhecido_cai_no_padrao(self, cliente, povoado):
        assert "Do mês que vem" not in texto(cliente.get("/?periodo=seculo"))

    def test_busca_e_periodo_se_somam(self, cliente, povoado):
        assert "Nenhuma tarefa" in texto(cliente.get("/?periodo=hoje&busca=mês"))

    def test_data_de_conclusao_aparece_na_tela(self, cliente, povoado):
        """O histórico que a RN04 protege precisa ser visível para servir de algo."""
        pagina = texto(cliente.get("/?periodo=todas&situacao=concluidas"))
        assert "em %s" % relogio.hoje().strftime("%d/%m/%Y") in pagina

    def test_relatorio_herda_periodo_e_busca_do_painel(self, cliente, povoado):
        """Passo 8.2 — o relatório enxerga o mesmo conjunto que o painel."""
        pagina = texto(cliente.get("/relatorio?periodo=todas"))
        assert "3" in pagina                       # as três tarefas do período
        restrito = texto(cliente.get("/relatorio?periodo=todas&busca=inexistente"))
        assert "Não há dados suficientes" in restrito

    def test_o_menu_carrega_o_filtro_para_o_relatorio(self, cliente, povoado):
        pagina = texto(cliente.get("/?periodo=todas&situacao=pendentes"))
        assert "/relatorio?" in pagina and "periodo=todas" in pagina

    def test_relatorio_vazio_avisa(self, cliente, contas):
        entrar(cliente)
        assert "Não há dados suficientes" in texto(cliente.get("/relatorio"))


# --------------------------------------------------- páginas de erro
class TestPaginasDeErro:
    def test_endereco_inexistente(self, cliente):
        resposta = cliente.get("/nao-existe")
        assert resposta.status_code == 404
        assert "Página não encontrada" in texto(resposta)

    def test_arquivo_corrompido_mostra_a_tela_e_nao_estoura(self, cliente, contas, pasta):
        """A tela de erro não pode depender do arquivo que acabou de falhar."""
        entrar(cliente)
        with open(configuracao.ARQUIVO_USUARIOS, "w", encoding="utf-8") as arquivo:
            arquivo.write("{isto não é json}")
        resposta = cliente.get("/")
        assert resposta.status_code == 500
        assert "Arquivo de dados ilegível" in texto(resposta)
        assert "não foi alterado" in texto(resposta)

    def test_arquivo_corrompido_nao_e_sobrescrito(self, cliente, contas, pasta):
        entrar(cliente)
        with open(configuracao.ARQUIVO_TAREFAS, "w", encoding="utf-8") as arquivo:
            arquivo.write("quebrado")
        cliente.get("/")
        with open(configuracao.ARQUIVO_TAREFAS, encoding="utf-8") as arquivo:
            assert arquivo.read() == "quebrado"


# ----------------------------------------------- redirecionamento seguro
class TestRedirecionamento:
    def test_voltar_para_externo_e_ignorado(self, cliente, contas):
        """'//outro-site' começa com barra, mas o navegador o trata como externo."""
        entrar(cliente)
        tarefa = criar_tarefa(cliente)
        resposta = cliente.post("/tarefas/%d/concluir" % tarefa.id, data={
            "csrf": csrf(cliente), "voltar_para": "//exemplo-externo.test/x"})
        assert resposta.headers["Location"] == "/"

    def test_voltar_para_absoluto_e_ignorado(self, cliente, contas):
        entrar(cliente)
        tarefa = criar_tarefa(cliente)
        resposta = cliente.post("/tarefas/%d/reabrir" % tarefa.id, data={
            "csrf": csrf(cliente), "voltar_para": "https://exemplo-externo.test/x"})
        assert resposta.headers["Location"] == "/"

    def test_voltar_para_interno_e_respeitado(self, cliente, contas):
        entrar(cliente)
        tarefa = criar_tarefa(cliente)
        resposta = cliente.post("/tarefas/%d/concluir" % tarefa.id, data={
            "csrf": csrf(cliente), "voltar_para": "/?periodo=todas"})
        assert resposta.headers["Location"] == "/?periodo=todas"


# ------------------------------------------- contexto da visão administrativa
class TestContextoAdministrativo:
    @pytest.fixture
    def admin(self, cliente, contas):
        entrar(cliente)
        criar_tarefa(cliente, "Do Pedro")
        postar(cliente, "/sair")
        entrar(cliente, configuracao.ADMIN_PADRAO_LOGIN, configuracao.ADMIN_PADRAO_SENHA)
        return modulo.tarefas.listar_todas()[0]

    def test_a_listagem_administrativa_leva_o_caminho_de_volta(self, cliente, admin):
        pagina = texto(cliente.get("/admin?periodo=todas"))
        assert "voltar_para=%2Fadmin" in pagina or "voltar_para=/admin" in pagina

    def test_concluir_a_partir_do_admin_volta_ao_admin(self, cliente, admin):
        resposta = cliente.post("/tarefas/%d/concluir" % admin.id, data={
            "csrf": csrf(cliente), "voltar_para": "/admin?periodo=todas"})
        assert resposta.headers["Location"] == "/admin?periodo=todas"

    def test_excluir_a_partir_do_admin_volta_ao_admin(self, cliente, admin):
        resposta = cliente.post("/tarefas/%d/excluir?voltar_para=/admin" % admin.id, data={
            "csrf": csrf(cliente), "voltar_para": "/admin?periodo=todas"})
        assert resposta.headers["Location"] == "/admin?periodo=todas"
        assert modulo.tarefas.listar_todas() == []

    def test_o_admin_tem_atalho_para_o_relatorio_da_visao(self, cliente, admin):
        pagina = texto(cliente.get("/admin?periodo=todas"))
        assert "/relatorio?" in pagina and "admin=1" in pagina

    def test_relatorio_administrativo_conta_as_tarefas_de_todos(self, cliente, admin):
        pagina = texto(cliente.get("/relatorio?periodo=todas&admin=1"))
        assert "Todas as tarefas de todos os usuários" in pagina


# ------------------------------------------------ coerência da faixa de resumo
class TestFaixaDeResumo:
    @pytest.fixture
    def recorte(self, cliente, contas):
        entrar(cliente)
        criar_tarefa(cliente, "Pendente A")
        criar_tarefa(cliente, "Pendente B")
        feita = criar_tarefa(cliente, "Concluída")
        postar(cliente, "/tarefas/%d/concluir" % feita.id)
        return feita

    def _numeros(self, pagina):
        return re.findall(r"<strong>(\d+)</strong><span>([^<]+)</span>", pagina)

    def test_sem_filtro_de_situacao(self, cliente, recorte):
        numeros = dict((rotulo, int(n)) for n, rotulo in
                       self._numeros(texto(cliente.get("/?periodo=todas"))))
        assert numeros["no período"] == 3
        assert numeros["pendentes"] == 2 and numeros["concluídas"] == 1

    def test_a_contagem_nao_muda_com_o_filtro_de_situacao(self, cliente, recorte):
        """Os quatro números decompõem o período; a situação filtra só a tabela."""
        pagina = texto(cliente.get("/?periodo=todas&situacao=pendentes"))
        numeros = dict((rotulo, int(n)) for n, rotulo in self._numeros(pagina))
        assert numeros["no período"] == 3
        assert numeros["concluídas"] == 1        # continua contando, mesmo filtrado
        assert "Concluída" not in pagina.split('<table')[1]   # mas some da tabela

    def test_o_relatorio_ignora_a_situacao(self, cliente, recorte):
        """Um relatório de 'só as concluídas' teria 100% de conclusão — não informa nada."""
        pagina = texto(cliente.get("/relatorio?periodo=todas&situacao=concluidas"))
        assert "33.3%" in pagina                  # 1 de 3, e não 100%
        assert 'name="situacao"' not in pagina    # o filtro nem aparece lá


# ----------------------------------------------------------- tema claro/escuro
class TestTema:
    def test_o_padrao_e_o_tema_claro(self, cliente, contas):
        entrar(cliente)
        assert 'data-theme="claro"' in texto(cliente.get("/"))

    def test_alternar_troca_e_volta(self, cliente, contas):
        entrar(cliente)
        postar(cliente, "/tema", voltar_para="/")
        assert 'data-theme="escuro"' in texto(cliente.get("/"))
        postar(cliente, "/tema", voltar_para="/")
        assert 'data-theme="claro"' in texto(cliente.get("/"))

    def test_a_escolha_fica_gravada_na_conta(self, cliente, contas):
        """Sobrevive a sair e entrar de novo — não é preferência do navegador."""
        entrar(cliente)
        postar(cliente, "/tema", voltar_para="/")
        postar(cliente, "/sair")
        entrar(cliente)
        assert modulo.usuarios.buscar_por_login("pedro@x.com").tema == "escuro"
        assert 'data-theme="escuro"' in texto(cliente.get("/"))

    def test_cada_usuario_tem_o_seu(self, cliente, contas):
        entrar(cliente)
        postar(cliente, "/tema", voltar_para="/")
        postar(cliente, "/sair")
        entrar(cliente, "ana@x.com")
        assert 'data-theme="claro"' in texto(cliente.get("/"))

    def test_o_visitante_tambem_pode_alternar(self, cliente):
        assert 'data-theme="claro"' in texto(cliente.get("/login"))
        postar(cliente, "/tema", voltar_para="/login")
        assert 'data-theme="escuro"' in texto(cliente.get("/login"))

    def test_o_tema_volta_para_a_pagina_de_origem(self, cliente, contas):
        entrar(cliente)
        resposta = cliente.post("/tema", data={
            "csrf": csrf(cliente), "voltar_para": "/?periodo=todas"})
        assert resposta.headers["Location"] == "/?periodo=todas"

    def test_valor_invalido_gravado_a_mao_cai_no_padrao(self, cliente, contas):
        from src.modelos.usuario import Usuario
        usuario = Usuario(id=1, nome="X", login="x@x.com", senha_hash="h", tema="roxo")
        assert usuario.tema == configuracao.TEMA_PADRAO

    def test_alternar_exige_o_token(self, cliente, contas):
        entrar(cliente)
        assert cliente.post("/tema", data={"voltar_para": "/"}).status_code == 400


# ------------------------------------------- lista de tarefas no relatório
class TestTarefasNoRelatorio:
    @pytest.fixture
    def recorte(self, cliente, contas):
        entrar(cliente)
        criar_tarefa(cliente, "Revisar o cálculo", prioridade="Alta")
        criar_tarefa(cliente, "Comprar pão", prioridade="Baixa")
        feita = criar_tarefa(cliente, "Assistir à webaula")
        postar(cliente, "/tarefas/%d/concluir" % feita.id)
        return feita

    def test_os_titulos_aparecem_no_relatorio(self, cliente, recorte):
        pagina = texto(cliente.get("/relatorio?periodo=todas"))
        assert "Revisar o cálculo" in pagina
        assert "Comprar pão" in pagina
        assert "Assistir à webaula" in pagina

    def test_a_busca_mostra_quais_tarefas_bateram(self, cliente, recorte):
        """Buscar por palavra e ver só o total de volta não responde nada."""
        pagina = texto(cliente.get("/relatorio?periodo=todas&busca=pao"))
        assert "Comprar pão" in pagina
        assert "Revisar o cálculo" not in pagina
        assert "Tarefas com “pao”" in pagina

    def test_a_lista_marca_o_que_esta_concluido(self, cliente, recorte):
        pagina = texto(cliente.get("/relatorio?periodo=todas"))
        assert "item-titulo feita" in pagina

    def test_relatorio_vazio_nao_lista_nada(self, cliente, recorte):
        pagina = texto(cliente.get("/relatorio?periodo=todas&busca=inexistente"))
        assert "Não há dados suficientes" in pagina
        assert "lista-titulos" not in pagina

    def test_o_admin_ve_o_dono_de_cada_titulo(self, cliente, recorte):
        postar(cliente, "/sair")
        entrar(cliente, configuracao.ADMIN_PADRAO_LOGIN, configuracao.ADMIN_PADRAO_SENHA)
        pagina = texto(cliente.get("/relatorio?periodo=todas&admin=1"))
        assert "Comprar pão" in pagina and "dono-tarefa" in pagina

    def test_a_lista_tem_teto(self, cliente, contas, monkeypatch):
        monkeypatch.setattr(modulo, "LIMITE_DA_LISTA_DO_RELATORIO", 2)
        entrar(cliente)
        for i in range(4):
            criar_tarefa(cliente, "Tarefa %d" % i)
        pagina = texto(cliente.get("/relatorio?periodo=todas"))
        assert "Mostrando as 2 primeiras" in pagina
        assert pagina.count("item-titulo") == 2
