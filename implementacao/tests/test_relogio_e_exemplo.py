"""Testa o relógio do sistema e o instalador dos dados de exemplo."""
import json
import os
from datetime import date, datetime

import pytest

from src import configuracao, exemplo
from src.modelos.tarefa import Tarefa
from src.servicos import relogio


class TestRelogio:
    def test_hoje_e_uma_data(self):
        assert isinstance(relogio.hoje(), date)

    def test_agora_nao_carrega_fuso_junto(self):
        """As datas são gravadas sem fuso; o relógio devolve no mesmo formato."""
        assert relogio.agora().tzinfo is None

    def test_hoje_e_a_data_de_agora(self):
        agora = relogio.agora()
        assert relogio.hoje() in (agora.date(), relogio.agora().date())

    def test_o_fuso_configurado_e_carregado(self):
        assert relogio.fuso() is not None, (
            "a base de fusos não está disponível — instale o pacote tzdata")

    def test_fuso_invalido_nao_derruba_o_sistema(self, monkeypatch):
        monkeypatch.setattr(configuracao, "FUSO", "Nao/Existe")
        assert relogio.fuso() is None
        assert isinstance(relogio.agora(), datetime)     # cai na hora da máquina


class TestExemplo:
    def test_os_arquivos_de_exemplo_existem_e_sao_validos(self):
        for nome in ("usuarios", "tarefas"):
            caminho = os.path.join(exemplo.PASTA_EXEMPLOS, "%s.exemplo.json" % nome)
            with open(caminho, encoding="utf-8") as arquivo:
                assert isinstance(json.load(arquivo), list)

    def test_reancoragem_traz_a_referencia_para_hoje(self):
        original = [{"data_prevista": exemplo.REFERENCIA.isoformat(),
                     "data_criacao": "2026-09-14T09:00:00",
                     "data_conclusao": None}]
        alvo = date(2030, 1, 15)
        ajustada = exemplo.reancorar_tarefas(original, hoje=alvo)[0]
        assert ajustada["data_prevista"] == alvo.isoformat()
        assert ajustada["data_conclusao"] is None

    def test_reancoragem_preserva_a_distancia_entre_as_datas(self):
        original = [{"data_prevista": "2026-09-20", "data_criacao": "2026-09-16T08:00:00",
                     "data_conclusao": "2026-09-18T10:30:00"}]
        ajustada = exemplo.reancorar_tarefas(original, hoje=date(2030, 1, 15))[0]
        prevista = date.fromisoformat(ajustada["data_prevista"])
        criada = datetime.fromisoformat(ajustada["data_criacao"])
        assert (prevista - criada.date()).days == 4
        assert criada.hour == 8 and criada.minute == 0

    def test_so_a_tarefa_deliberadamente_atrasada_nasce_atrasada(self):
        """A REFERENCIA é o "hoje" do arquivo de exemplo.

        Se ela se descolar das datas gravadas, a instalacao cai na semana
        errada e o painel abre cheio de tarefas atrasadas.
        """
        hoje = date(2030, 1, 15)
        tarefas = [Tarefa.de_dict(registro) for registro
                   in exemplo.reancorar_tarefas(exemplo._ler("tarefas"), hoje=hoje)]
        atrasadas = [tarefa.titulo for tarefa in tarefas if tarefa.esta_atrasada(hoje)]
        assert atrasadas == ["Renovar o empréstimo da biblioteca"]
        assert any(tarefa.data_prevista == hoje for tarefa in tarefas)

    def test_instalar_em_pasta_vazia(self, tmp_path, monkeypatch):
        monkeypatch.setattr(configuracao, "PASTA_DADOS", str(tmp_path))
        monkeypatch.setattr(configuracao, "ARQUIVO_TAREFAS", str(tmp_path / "tarefas.json"))
        monkeypatch.setattr(configuracao, "ARQUIVO_USUARIOS", str(tmp_path / "usuarios.json"))
        escritos = exemplo.instalar()
        assert len(escritos) == 2
        with open(tmp_path / "tarefas.json", encoding="utf-8") as arquivo:
            assert len(json.load(arquivo)) == 12

    def test_instalar_recusa_sobrescrever_sem_forcar(self, tmp_path, monkeypatch):
        monkeypatch.setattr(configuracao, "PASTA_DADOS", str(tmp_path))
        monkeypatch.setattr(configuracao, "ARQUIVO_TAREFAS", str(tmp_path / "tarefas.json"))
        monkeypatch.setattr(configuracao, "ARQUIVO_USUARIOS", str(tmp_path / "usuarios.json"))
        (tmp_path / "tarefas.json").write_text("[]", encoding="utf-8")
        with pytest.raises(FileExistsError):
            exemplo.instalar()

    def test_forcar_guarda_uma_copia_antes(self, tmp_path, monkeypatch):
        monkeypatch.setattr(configuracao, "PASTA_DADOS", str(tmp_path))
        monkeypatch.setattr(configuracao, "ARQUIVO_TAREFAS", str(tmp_path / "tarefas.json"))
        monkeypatch.setattr(configuracao, "ARQUIVO_USUARIOS", str(tmp_path / "usuarios.json"))
        (tmp_path / "tarefas.json").write_text('["antigo"]', encoding="utf-8")
        exemplo.instalar(forcar=True)
        assert (tmp_path / "tarefas.json.bak").read_text(encoding="utf-8") == '["antigo"]'

    def test_as_tarefas_de_exemplo_carregam_como_objetos(self, tmp_path, monkeypatch):
        """Prova que o exemplo usa o mesmo esquema que o sistema grava."""
        from src.modelos.tarefa import Tarefa
        monkeypatch.setattr(configuracao, "PASTA_DADOS", str(tmp_path))
        monkeypatch.setattr(configuracao, "ARQUIVO_TAREFAS", str(tmp_path / "tarefas.json"))
        monkeypatch.setattr(configuracao, "ARQUIVO_USUARIOS", str(tmp_path / "usuarios.json"))
        exemplo.instalar()
        with open(tmp_path / "tarefas.json", encoding="utf-8") as arquivo:
            tarefas = [Tarefa.de_dict(registro) for registro in json.load(arquivo)]
        assert all(t.prioridade in configuracao.PRIORIDADES for t in tarefas)
        assert all(t.categoria in configuracao.CATEGORIAS for t in tarefas)
        assert any(t.concluida for t in tarefas) and any(not t.concluida for t in tarefas)