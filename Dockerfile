FROM python:3.12-slim

# Evitar que o Python grave arquivos .pyc no disco e faça buffering de stdout/stderr
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /app

# Instalar dependências de compilação básicas se necessário (PyMuPDF não necessita no slim usual)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copiar a estrutura do app
COPY app/ ./app/

# Porta do contêiner
EXPOSE 8000

# Comando para rodar a aplicação, compatível com a porta dinâmica do Railway
CMD ["sh", "-c", "uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000} --workers 1"]
