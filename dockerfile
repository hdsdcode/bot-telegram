FROM python:3.11-slim

WORKDIR /app

# Copia arquivos para o container
COPY . .

# Instala as dependências
RUN pip install --no-cache-dir -r requirements.txt

# Executa o bot
CMD ["python", "bot_curriculo.py"]
