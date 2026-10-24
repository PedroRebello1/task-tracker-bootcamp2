# Imagem do TaskTracker

# O código é o da Etapa 2, a imagem só o empacota.

FROM python:3.11-slim

WORKDIR /app

# Logs sem buffer: cada print() do menu chega na hora ao terminal.
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1
ENV PIP_DISABLE_PIP_VERSION_CHECK=1
ENV PIP_ROOT_USER_ACTION=ignore

# Dependências antes do código, esta camada fica em cache
COPY implementacao/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY implementacao/pytest.ini .
COPY implementacao/src/ /app/src/
COPY implementacao/dados/ /app/dados/
COPY implementacao/tests/ /app/tests/

# Modo web. Dentro do container, o Flask escuta em todas as 
# interfaces para ser alcançado pela porta publicada.
ENV TASKTRACKER_HOST=0.0.0.0
EXPOSE 5000

CMD ["python", "src/main.py"]