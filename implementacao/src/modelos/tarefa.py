# Entidade Tarefa - traducao direta do modelo de dados da Etapa 1.
from datetime import date, datetime

from src import configuracao
from src.servicos import relogio


class Tarefa:
    # Uma tarefa pessoal pertencente a um usuario.

    def __init__(self, id, titulo, data_prevista, prioridade, usuario_id,
                 descricao="", categoria=configuracao.CATEGORIA_PADRAO,
                 status=configuracao.STATUS_PENDENTE,
                 data_criacao=None, data_conclusao=None):
        self.id = id
        self.titulo = titulo
        self.descricao = descricao
        self.data_prevista = data_prevista
        self.prioridade = prioridade
        self.categoria = categoria
        self.status = status
        self.data_criacao = data_criacao or relogio.agora()
        self.data_conclusao = data_conclusao
        self.usuario_id = usuario_id

    # propriedades
    @property
    def concluida(self):
        return self.status == configuracao.STATUS_CONCLUIDA

    def esta_atrasada(self, hoje):
        # Pendente e com a data prevista ja vencida em relacao a `hoje`.

        return not self.concluida and self.data_prevista < hoje

    @property
    def atrasada(self):
        # Atalho para as telas, que sempre querem o atraso de hoje.
        return self.esta_atrasada(relogio.hoje())

    @property
    def peso_prioridade(self):
        # Usado na ordenacao: Alta vem antes de Média, que vem antes de Baixa.
        return configuracao.PESO_PRIORIDADE.get(self.prioridade, 99)

    # conversao
    def para_dict(self):
        # Converte para o formato gravado em JSON.
        return {
            "id": self.id,
            "titulo": self.titulo,
            "descricao": self.descricao,
            "data_prevista": self.data_prevista.isoformat(),
            "prioridade": self.prioridade,
            "categoria": self.categoria,
            "status": self.status,
            "data_criacao": self.data_criacao.isoformat(),
            "data_conclusao": self.data_conclusao.isoformat() if self.data_conclusao else None,
            "usuario_id": self.usuario_id,
        }

    @classmethod
    def de_dict(cls, dados):
        # Reconstroi a tarefa a partir do dicionario lido do JSON.
        conclusao = dados.get("data_conclusao")
        return cls(
            id=dados["id"],
            titulo=dados["titulo"],
            descricao=dados.get("descricao", ""),
            data_prevista=date.fromisoformat(dados["data_prevista"]),
            prioridade=dados["prioridade"],
            categoria=dados.get("categoria", configuracao.CATEGORIA_PADRAO),
            status=dados.get("status", configuracao.STATUS_PENDENTE),
            data_criacao=datetime.fromisoformat(dados["data_criacao"]),
            data_conclusao=datetime.fromisoformat(conclusao) if conclusao else None,
            usuario_id=dados["usuario_id"],
        )

    def __repr__(self):
        return "<Tarefa #%s %r [%s]>" % (self.id, self.titulo, self.status)
