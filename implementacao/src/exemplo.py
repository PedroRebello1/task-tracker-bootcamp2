"""Instala os dados de exemplo em `dados/`.

    python -m src.exemplo            # recusa sobrescrever dados existentes
    python -m src.exemplo --forcar   # substitui o que estiver la

Senhas do conjunto de exemplo:
    admin@tasktracker.local / admin123   (perfil admin)
    pedro@exemplo.local     / senha123
    ana@exemplo.local       / senha123
"""
import json
import os
import shutil
import sys
from datetime import date, datetime

from src import configuracao
from src.servicos import relogio

REFERENCIA = date(2026, 9, 23)

# Os arquivos de exemplo são versionados junto com o codigo, entao moram sempre
# em implementacao/dados/ - e nao na pasta de dados.
PASTA_EXEMPLOS = os.path.join(configuracao.RAIZ, "dados")


def _deslocamento(hoje=None):
    """Quantos dias somar para que a REFERENCIA caia sobre hoje."""
    return (hoje or relogio.hoje()) - REFERENCIA


def _deslocar(texto, dias):
    """Soma `dias` a uma data ou data-hora em ISO, preservando o formato."""
    if texto is None:
        return None
    if "T" in texto:
        return (datetime.fromisoformat(texto) + dias).isoformat()
    return (date.fromisoformat(texto) + dias).isoformat()


def reancorar_tarefas(tarefas, hoje=None):
    """Desloca data_prevista, data_criacao e data_conclusao de cada tarefa."""
    dias = _deslocamento(hoje)
    ajustadas = []
    for tarefa in tarefas:
        copia = dict(tarefa)
        for campo in ("data_prevista", "data_criacao", "data_conclusao"):
            copia[campo] = _deslocar(copia.get(campo), dias)
        ajustadas.append(copia)
    return ajustadas


def _ler(nome):
    caminho = os.path.join(PASTA_EXEMPLOS, "%s.exemplo.json" % nome)
    with open(caminho, "r", encoding="utf-8") as arquivo:
        return json.load(arquivo)


def instalar(forcar=False, hoje=None):
    """Grava os exemplos em dados/. Devolve a lista de arquivos escritos."""
    os.makedirs(configuracao.PASTA_DADOS, exist_ok=True)
    destinos = {"usuarios": configuracao.ARQUIVO_USUARIOS,
                "tarefas": configuracao.ARQUIVO_TAREFAS}

    existentes = [caminho for caminho in destinos.values() if os.path.exists(caminho)]
    if existentes and not forcar:
        raise FileExistsError(
            "Já existem dados em %s. Use --forcar para substituí-los "
            "(uma cópia .bak é guardada antes)." % configuracao.PASTA_DADOS)

    escritos = []
    for nome, destino in destinos.items():
        if os.path.exists(destino):
            shutil.copy2(destino, destino + ".bak")
        conteudo = _ler(nome)
        if nome == "tarefas":
            conteudo = reancorar_tarefas(conteudo, hoje=hoje)
        with open(destino, "w", encoding="utf-8") as arquivo:
            json.dump(conteudo, arquivo, ensure_ascii=False, indent=2)
            arquivo.write("\n")
        escritos.append(destino)
    return escritos


def main(argumentos=None):
    argumentos = sys.argv[1:] if argumentos is None else argumentos
    forcar = "--forcar" in argumentos or "-f" in argumentos
    try:
        escritos = instalar(forcar=forcar)
    except FileExistsError as erro:
        print("  %s" % erro)
        return 1
    print("\n  Dados de exemplo instalados:")
    for caminho in escritos:
        print("   · %s" % caminho)
    print("\n  Entre com admin@tasktracker.local / admin123 (administrador),")
    print("  pedro@exemplo.local / senha123 ou ana@exemplo.local / senha123.\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
