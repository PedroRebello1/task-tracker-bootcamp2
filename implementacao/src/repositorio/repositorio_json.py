"""Acesso ao disco - unico ponto do sistema que le e grava os arquivos JSON.

Isolar a persistencia aqui tem um beneficio concreto. Se um dia o JSON for
trocado por um banco SQLite, só este arquivo precisa mudar.
"""
import json
import os
import time

# No Windows, o antivirus ou o indexador podem segurar o arquivo recem-escrito
# por alguns milissegundos e fazer a troca falhar com "Acesso negado". 

TENTATIVAS_DE_TROCA = 5
ESPERA_ENTRE_TENTATIVAS = 0.05


class ArquivoCorrompido(Exception):
    """O arquivo existe mas nao pode ser lido como JSON valido.

    O sistema avisa e NAO sobrescreve, para nao destruir dados recuperaveis.
    """


class RepositorioJson:
    """Le e grava uma lista de dicionarios em um arquivo JSON."""

    def __init__(self, caminho, conteudo_inicial=None):
        self.caminho = caminho
        self.conteudo_inicial = conteudo_inicial if conteudo_inicial is not None else []

    # leitura
    def carregar(self):
        """Devolve a lista gravada, criando o arquivo se ele ainda nao existir."""
        if not os.path.exists(self.caminho):
            self.garantir_arquivo()
            return list(self.conteudo_inicial)

        try:
            with open(self.caminho, "r", encoding="utf-8") as arquivo:
                dados = json.load(arquivo)
        except json.JSONDecodeError as erro:
            raise ArquivoCorrompido(
                "O arquivo %s não pôde ser lido (%s). "
                "Ele não foi alterado — corrija-o ou restaure uma cópia."
                % (os.path.basename(self.caminho), erro)
            )
        except UnicodeDecodeError:
            raise ArquivoCorrompido(
                "O arquivo %s não está em UTF-8 e não pôde ser lido. "
                "Ele não foi alterado — corrija-o ou restaure uma cópia."
                % os.path.basename(self.caminho)
            )

        if not isinstance(dados, list):
            raise ArquivoCorrompido(
                "O arquivo %s não contém uma lista de registros. "
                "Ele não foi alterado — corrija-o ou restaure uma cópia."
                % os.path.basename(self.caminho)
            )
        return dados

    # escrita
    def salvar(self, registros):
        """Regrava o arquivo inteiro. Chamado a cada operacao que altera dados."""
        self._garantir_pasta()
        provisorio = self.caminho + ".tmp"
        try:
            with open(provisorio, "w", encoding="utf-8") as arquivo:
                json.dump(registros, arquivo, ensure_ascii=False, indent=2)
                arquivo.flush()
                # Leva o conteudo ao disco antes da troca: sem isto, o os.replace
                # pode publicar um arquivo que ainda esta no cache do sistema.
                os.fsync(arquivo.fileno())
            # os.replace e atomico: o arquivo antigo só some quando o novo está
            # pronto, entao uma queda no meio da gravacao nao deixa dados pela metade.
            self._trocar(provisorio)
        except Exception:
            # Não deixa lixo para tras se a gravacao falhar no meio.
            if os.path.exists(provisorio):
                try:
                    os.remove(provisorio)
                except OSError:
                    pass
            raise

    def _trocar(self, provisorio):
        """Publica o arquivo provisorio, insistindo se o disco estiver ocupado."""
        for tentativa in range(TENTATIVAS_DE_TROCA):
            try:
                os.replace(provisorio, self.caminho)
                return
            except PermissionError:
                if tentativa == TENTATIVAS_DE_TROCA - 1:
                    raise
                time.sleep(ESPERA_ENTRE_TENTATIVAS)

    # inicializacao
    def garantir_arquivo(self):
        """Cria o arquivo com o conteudo inicial, se ele ainda nao existir."""
        if not os.path.exists(self.caminho):
            self.salvar(list(self.conteudo_inicial))

    def _garantir_pasta(self):
        pasta = os.path.dirname(self.caminho)
        if pasta:
            os.makedirs(pasta, exist_ok=True)
