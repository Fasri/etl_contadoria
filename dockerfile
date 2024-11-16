# Use uma imagem Python oficial como base
FROM python:3.10-slim

# Definir o diretório de trabalho dentro do container
WORKDIR /app

# Copiar o arquivo de requisitos e instalar as dependências
COPY src/requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# Copiar o código-fonte para dentro do container
COPY src /app/src
COPY /contadoria_tempo_real/pipeline/credentials.json /app/contadoria_tempo_real/pipeline/credentials.json

# Definir o comando que será executado ao iniciar o container
CMD ["python", "app.py"]
