# O relogio do sistema

# Existe por um motivo concreto: o Task Tracker inteiro gira em torno de "o que eu tenho para hoje". 
# É fundamental para o funcionamento do sistema que a data seja consistente.

from datetime import datetime

from src import configuracao

try:
    from zoneinfo import ZoneInfo, ZoneInfoNotFoundError
except ImportError:
    ZoneInfo = None
    ZoneInfoNotFoundError = Exception


def fuso():
    # Devolve o fuso configurado, ou None quando ele nao esta disponivel.
    # Caso não encontre o fuso, usa a hora local da maquina
    
    if ZoneInfo is None:
        return None
    try:
        return ZoneInfo(configuracao.FUSO)
    except (ZoneInfoNotFoundError, ValueError):
        return None


def agora():
    # Data e hora atuais no fuso configurado, sem carregar o fuso junto.
    zona = fuso()
    if zona is None:
        return datetime.now()
    return datetime.now(zona).replace(tzinfo=None)


def hoje():
    # A data de hoje no fuso configurado.
    return agora().date()
