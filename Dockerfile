# Dockerfile pour le projet OpenFoodFacts ETL
# Auteurs: Félicien, Charif, Clément
# Module: TRDE703 - M1 EISI/CDPIA/CYBER

FROM python:3.9-slim

# Métadonnées
LABEL maintainer="Félicien, Charif, Clément"
LABEL description="OpenFoodFacts ETL - TRDE703"
LABEL version="1.0"

# Variables d'environnement
ENV PYTHONUNBUFFERED=1
ENV SPARK_HOME=/opt/spark
ENV JAVA_HOME=/usr/lib/jvm/java-21-openjdk-amd64

# Installation des dépendances système
RUN apt-get update && apt-get install -y \
    openjdk-21-jdk \
    wget \
    procps \
    curl \
    mariadb-client \
    && rm -rf /var/lib/apt/lists/*

# Téléchargement et installation de Spark
RUN wget -q https://archive.apache.org/dist/spark/spark-3.5.0/spark-3.5.0-bin-hadoop3.tgz \
    && tar -xzf spark-3.5.0-bin-hadoop3.tgz -C /opt \
    && mv /opt/spark-3.5.0-bin-hadoop3 /opt/spark \
    && rm spark-3.5.0-bin-hadoop3.tgz

# Configuration Spark
ENV PATH=$PATH:$SPARK_HOME/bin:$SPARK_HOME/sbin
ENV PYSPARK_PYTHON=python3

# Répertoire de travail
WORKDIR /app

# Copie des fichiers de requirements
COPY requirements.txt .

# Installation des dépendances Python
RUN pip install --no-cache-dir -r requirements.txt

# Téléchargement du connecteur MariaDB pour Spark
RUN wget -q https://repo1.maven.org/maven2/org/mariadb/jdbc/mariadb-java-client/3.3.2/mariadb-java-client-3.3.2.jar \
    -P $SPARK_HOME/jars/

# Copie du projet
COPY . .

# Création des répertoires nécessaires
RUN mkdir -p data/sample data/bronze data/silver data/gold logs reports

# Script de démarrage par défaut (attente, pas de téléchargement)
CMD ["tail", "-f", "/dev/null"]
