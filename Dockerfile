FROM python:3.9-slim

WORKDIR /app

# Installation des dépendances système
RUN apt-get update && apt-get install -y \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Copie du requirements.txt
COPY app/requirements.txt .

# Installation des dépendances (les versions sont DANS requirements.txt)
RUN pip install --no-cache-dir -r requirements.txt

# Copie de l'application
COPY app/ .
COPY data/ /app/data/

EXPOSE 5000

CMD ["python", "app.py"]
