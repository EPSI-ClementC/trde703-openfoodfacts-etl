# OpenFoodFacts ETL - Datamart Nutrition & Qualité

[![Python](https://img.shields.io/badge/Python-3.9+-blue.svg)](https://www.python.org/)
[![Spark](https://img.shields.io/badge/Apache%20Spark-3.5-orange.svg)](https://spark.apache.org/)
[![MariaDB](https://img.shields.io/badge/MariaDB-11.8-blue.svg)](https://mariadb.org/)

> **Projet TRDE703 - M1**
>
> **Auteurs :** Félicien, Charif, Clément | **Date :** 25 janvier 2026
>
> Atelier Intégration des Données - Big Data ETL avec Apache Spark

---

## Livrables du Projet (pour la correction)

### Repo Git structuré
- **[/docs](docs/)** : Documentation complète
  - [README.md](README.md) (ce fichier)
  - [data_dictionary.md](docs/data_dictionary.md) : Dictionnaire de données
  - [architecture.md](docs/architecture.md) : Note d'architecture
  - [quality_rules.md](docs/quality_rules.md) : Cahier de qualité
  - [schemas/datamart_schema.md](docs/schemas/datamart_schema.md) : Schémas du datamart
- **[/etl](etl/)** : Code Spark (1485 lignes Python)
  - [download_data.py](etl/download_data.py) : Téléchargement données
  - [bronze_to_silver.py](etl/bronze_to_silver.py) : Nettoyage & transformation
  - [silver_to_gold.py](etl/silver_to_gold.py) : Chargement MariaDB
  - [quality_checks.py](etl/quality_checks.py) : Rapport qualité
  - [config.py](etl/config.py) : Configuration centralisée
- **[/sql](sql/)** : Scripts SQL (251 lignes)
  - [ddl/](sql/ddl/) : Création tables (dimensions, faits, bridge)
  - [dml/](sql/dml/) : Manipulation données
  - [queries/analytics.sql](sql/queries/analytics.sql) : 7 requêtes analytiques
  - [queries/results.md](sql/queries/results.md) : Résultats commentés
- **[/data](data/)** : Données du projet
  - [sample/openfoodfacts-fr-sample-30000.csv](data/sample/) : Sample 30k produits (73 MB inclus dans Git)

### Pipeline Spark reproductible
- **Exécution :** `python etl/download_data.py` → `bronze_to_silver.py` → `silver_to_gold.py`
- **Logs qualité :** [logs/](logs/) et [reports/](reports/) (rapports JSON)
- **Architecture :** Bronze → Silver (Parquet) → Gold (MariaDB)

### Datamart MariaDB (schéma en étoile)
- **Scripts DDL :** [sql/ddl/](sql/ddl/)
  - [01_create_dimensions.sql](sql/ddl/01_create_dimensions.sql) : 5 dimensions
  - [02_create_facts.sql](sql/ddl/02_create_facts.sql) : 1 table de faits
  - [03_create_bridge.sql](sql/ddl/03_create_bridge.sql) : 1 bridge table
- **Scripts DML :** [sql/dml/truncate_all.sql](sql/dml/truncate_all.sql)
- **Modèle :** 5 dimensions + 1 fait + 1 bridge (voir [datamart_schema.md](docs/schemas/datamart_schema.md))

### Cahier de qualité
- **Document :** [docs/quality_rules.md](docs/quality_rules.md)
- **Règles :** Complétude (71%), Unicité (100%), Bornes, Cohérence
- **Rapports JSON :** [reports/quality_report_*.json](reports/)
- **Métriques :** 29,999 produits, 4,200 marques, 2,100 catégories

### Requêtes analytiques SQL
- **Fichier :** [sql/queries/analytics.sql](sql/queries/analytics.sql) (7 requêtes)
- **Résultats :** [sql/queries/results.md](sql/queries/results.md) (commentés)
- **KPI couverts :** Top marques Nutri-Score, Distribution par catégorie, Complétude, Anomalies, Évolution temporelle

### Note d'architecture
- **Document :** [docs/architecture.md](docs/architecture.md)
- **Contenu :** Choix techniques, flux ETL, stratégie SCD2, optimisations Spark/MariaDB

### BONUS : Containerisation Docker
- **Fichiers :** [Dockerfile](Dockerfile), [docker-compose.yml](docker-compose.yml)
- **Guide :** [DOCKER.md](DOCKER.md) (instructions complètes)
- **Avantage :** Tester le projet en 2 commandes, aucune installation requise
- **Reproductibilité** : Environnement identique garanti (Python 3.9, Spark 3.5, MariaDB 8.0)

---

## Démarrage rapide avec Docker (RECOMMANDÉ)

**IMPORTANT : Pour tester le projet, consultez le guide complet [DOCKER.md](DOCKER.md)**

**Tester le projet en 2 commandes sans rien installer !**

### Prérequis
- Docker Desktop ([télécharger](https://www.docker.com/products/docker-desktop))
- 4 GB RAM disponible

### Lancement rapide

```bash
# 1. Démarrer l'infrastructure (MariaDB + Spark)
docker-compose up -d

# 2. Exécuter le pipeline ETL complet
docker exec -it openfoodfacts-etl bash run-pipeline.sh
```

**C'est tout !** Le datamart MariaDB est maintenant populé avec 30k produits. 🎉

### Vérification rapide

```bash
# Compter les enregistrements
docker exec -it openfoodfacts-mariadb mariadb -u etl_user -pETL_Pass_2025! openfoodfacts_dw -e "
SELECT 'Produits' as table_name, COUNT(*) FROM dim_product
UNION ALL SELECT 'Marques', COUNT(*) FROM dim_brand
UNION ALL SELECT 'Catégories', COUNT(*) FROM dim_category
UNION ALL SELECT 'Faits', COUNT(*) FROM fact_nutrition_snapshot;"
```

**Guide complet de test :** Voir [DOCKER.md](DOCKER.md) pour toutes les commandes de validation

---

## Sommaire

- [Contexte](#contexte)
- [Objectifs](#objectifs)
- [Architecture](#architecture)
- [Prérequis](#prérequis)
- [Installation](#installation)
- [Configuration](#configuration)
- [Exécution du Pipeline](#exécution-du-pipeline)
- [Métriques de Qualité](#métriques-de-qualité)
- [Requêtes Analytiques](#requêtes-analytiques)
- [Structure du Projet](#structure-du-projet)
- [Documentation](#documentation)
- [Auteurs](#auteurs)

---

## Contexte

Ce projet implémente une **chaîne d'intégration de données complète (ETL)** utilisant Apache Spark pour traiter les données massives d'OpenFoodFacts et alimenter un datamart MariaDB orienté analyse nutritionnelle et qualité des produits alimentaires.

### Source de données
- **OpenFoodFacts** : Base de données collaborative open source de produits alimentaires
- Dataset français : ~500k+ produits
- Format : CSV (séparateur tabulation)
- Mise à jour : Quotidienne
- URL : https://fr.pro.openfoodfacts.org/data

---

## Objectifs

1. **Collecter** les données OpenFoodFacts (exports CSV complets)
2. **Nettoyer et normaliser** les données (qualité, déduplication)
3. **Modéliser** en schéma en étoile (star schema)
4. **Charger** dans un datamart MariaDB
5. **Analyser** avec des requêtes SQL pour des KPI métier

### KPI visés
- Répartition Nutri-Score par catégorie/marque/pays
- Évolution de la complétude des nutriments
- Taux d'anomalies nutritionnelles
- Classement des marques par qualité nutritionnelle
- Top catégories avec anomalies

---

## Architecture

### Architecture Bronze → Silver → Gold

```
┌─────────────────┐
│  OpenFoodFacts  │  Source externe (CSV ~500k produits)
│   (Bronze)      │
└────────┬────────┘
         │ download_data.py
         ▼
┌─────────────────┐
│  Raw CSV Data   │  Données brutes (data/sample/)
└────────┬────────┘
         │ bronze_to_silver.py
         ▼
┌─────────────────┐
│  Silver Layer   │  Parquet nettoyé + normalisé + qualité
│   (Parquet)     │  - Déduplication
└────────┬────────┘  - Harmonisation unités
         │           - Métriques qualité
         │ silver_to_gold.py
         ▼
┌─────────────────┐
│   Gold Layer    │  MariaDB - Schéma en étoile
│  (Datamart)     │  - 5 dimensions
└─────────────────┘  - 1 table de faits
                     - 1 bridge table
```

### Technologies utilisées

- **ETL** : Apache Spark 3.5 (PySpark)
- **Datawarehouse** : MariaDB 8.0
- **Langage** : Python 3.8+
- **Format intermédiaire** : Parquet (Silver layer)
- **Stockage** : Système de fichiers local

---

> **Note pour l'évaluation :**
>
> Les sections ci-dessous décrivent l'installation complète pour développer et exécuter le projet **manuellement** (sans Docker).
>
> **Pour la correction**, il est recommandé d'utiliser uniquement Docker (voir [DOCKER.md](DOCKER.md)) qui permet de tester le projet en 2 commandes :
> ```bash
> docker-compose up -d
> docker exec -it openfoodfacts-etl bash run-pipeline.sh
> ```

---

## Prérequis

### Logiciels requis

```bash
# Versions minimales
Python >= 3.8
Apache Spark >= 3.5
MariaDB >= 8.0
Java >= 11 (pour Spark)
```

### Ressources matérielles recommandées

- **RAM** : 8 GB minimum (16 GB recommandé)
- **CPU** : 4 cores minimum
- **Disque** : 10 GB espace libre (données + Spark)

---

## Installation

### 1. Cloner le projet

```bash
git clone <votre-repo>
cd trde703-openfoodfacts-etl
```

### 2. Créer un environnement virtuel

```bash
python3 -m venv venv
source venv/bin/activate  # Linux/Mac
# ou
venv\Scripts\activate  # Windows
```

### 3. Installer les dépendances

```bash
pip install -r requirements.txt
```

**Dépendances principales :**
- `pyspark==3.5.3` : Apache Spark pour Python
- `pymariadb==1.1.0` : Connecteur MariaDB
- `pandas==2.1.4` : Manipulation de données
- `requests==2.31.0` : Téléchargement HTTP
- `python-dotenv==1.0.0` : Gestion variables d'environnement

### 4. Télécharger le driver JDBC MariaDB

```bash
# Le driver sera automatiquement téléchargé par Spark
# via .config("spark.jars.packages", "mariadb:mariadb-connector-java:8.0.33")
```

---

## Configuration

### 1. Créer le fichier .env

Copier le fichier `.env` et adapter les paramètres :

```bash
# Base de données MariaDB
DB_HOST=localhost
DB_PORT=3306
DB_NAME=openfoodfacts_dw
DB_USER=etl_user
DB_PASSWORD=ETL_Pass_2025!

# Configuration Spark
SPARK_MASTER=local[4]
SPARK_DRIVER_MEMORY=4g
SPARK_EXECUTOR_MEMORY=4g

# OpenFoodFacts
OFF_BASE_URL=https://static.openfoodfacts.org/data
OFF_SAMPLE_SIZE=30000
```

### 2. Créer la base de données MariaDB

```bash
# Se connecter à MariaDB
mariadb -u root -p

# Créer la base et l'utilisateur
CREATE DATABASE openfoodfacts_dw CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
CREATE USER 'etl_user'@'localhost' IDENTIFIED BY 'ETL_Pass_2025!';
GRANT ALL PRIVILEGES ON openfoodfacts_dw.* TO 'etl_user'@'localhost';
FLUSH PRIVILEGES;
EXIT;
```

### 3. Créer les tables (DDL)

```bash
# Créer les dimensions
mariadb -u etl_user -p openfoodfacts_dw < sql/ddl/01_create_dimensions.sql

# Créer les tables de faits
mariadb -u etl_user -p openfoodfacts_dw < sql/ddl/02_create_facts.sql

# Créer la bridge table
mariadb -u etl_user -p openfoodfacts_dw < sql/ddl/03_create_bridge.sql
```

---

## Exécution du Pipeline

### Pipeline complet (ordre recommandé)

```bash
# 1. Télécharger les données OpenFoodFacts (~3 min)
python etl/download_data.py

# 2. ETL Bronze → Silver (nettoyage + qualité) (~5 min)
python etl/bronze_to_silver.py

# 3. ETL Silver → Gold (chargement MariaDB) (~8 min)
python etl/silver_to_gold.py

# 4. Génération du rapport de qualité (~2 min)
python etl/quality_checks.py
```

### Détails de chaque étape

#### Étape 1 : Téléchargement des données

```bash
python etl/download_data.py
```

**Actions :**
- Télécharge le dataset français complet (fr.openfoodfacts.org)
- Crée un sample de 30k produits pour développement
- Affiche les statistiques de téléchargement

**Sorties :**
- `data/sample/openfoodfacts-fr.csv` (~500k produits)
- `data/sample/openfoodfacts-fr-sample-30000.csv` (30k produits)

#### Étape 2 : Bronze → Silver (Nettoyage)

```bash
python etl/bronze_to_silver.py
```

**Actions :**
- Lecture du CSV avec schéma explicite
- Nettoyage des chaînes (trim, normalisation espaces)
- Harmonisation unités (sel/sodium : sel ≈ 2.5 × sodium)
- Déduplication par code-barres (garde le plus récent)
- Calcul métriques de qualité (complétude, anomalies)
- Hash MD5 pour SCD2

**Sorties :**
- `data/silver/products/*.parquet` (format Parquet optimisé)
- `logs/quality_report_YYYYMMDD_HHMMSS.json`

**Métriques calculées :**
- `completeness_score` : Score 0-1 de complétude
- `nb_nutrients_filled` : Nombre de nutriments renseignés
- `quality_issues_json` : Liste des anomalies détectées
- `row_hash` : Hash pour détecter les changements

#### Étape 3 : Silver → Gold (Chargement MariaDB)

```bash
python etl/silver_to_gold.py
```

**Actions :**
- Chargement des données Silver (Parquet)
- Population des dimensions :
  - `dim_time` : Dimension temporelle (dates)
  - `dim_brand` : Marques (dédoublonnage normalisé)
  - `dim_category` : Catégories
  - `dim_country` : Pays
  - `dim_product` : Produits (SCD Type 2 préparé)
- Population de la table de faits `fact_nutrition_snapshot`
- Écriture en mode append via JDBC

**Sorties :**
- Tables MariaDB peuplées
- Logs de chargement (nombre de lignes par table)

#### Étape 4 : Rapport de qualité

```bash
python etl/quality_checks.py
```

**Actions :**
- Analyse de complétude par dimension
- Vérification unicité des codes-barres
- Détection anomalies nutritionnelles
- Distribution Nutri-Score et NOVA
- Génération rapport JSON complet

**Sorties :**
- `reports/quality_report_YYYYMMDD_HHMMSS.json`

---

## Métriques de Qualité

**Règles implémentées :**
1. **Complétude** : Score 0-1 sur 8 champs critiques (nom, marque, catégorie, 5 nutriments)
2. **Unicité** : Un code-barres = un produit (déduplication par `last_modified_t`)
3. **Bornes** : Nutriments dans intervalles réalistes (ex: 0-100g pour 100g)
4. **Cohérence** : Harmonisation sel/sodium (sel ≈ 2.5 × sodium)

**Résultats (sample 30k) :**
- Complétude moyenne : **71%** ✅
- Unicité : **100%** ✅
- Anomalies : **4.4%** (2215 produits) ⚠️
- Distribution Nutri-Score : A:4209, B:2091, C:3365, D:4292, E:5898

---

## Requêtes Analytiques

**7 requêtes SQL disponibles** dans [`sql/queries/analytics.sql`](sql/queries/analytics.sql) :

1. **Top 10 marques** par Nutri-Score A/B
2. **Distribution Nutri-Score** par catégorie
3. **Analyse sucres** par catégorie (moyenne, min, max)
4. **Taux de complétude** par marque
5. **Liste anomalies** nutritionnelles (sucres > 80g, sel > 25g)
6. **Évolution hebdomadaire** de la complétude (6 derniers mois)
7. **Top catégories** avec anomalies

**Résultats commentés** disponibles dans `sql/queries/results.md`

---

## Structure du Projet

```
trde703-openfoodfacts-etl/
│
├── README.md                    # Ce fichier
├── requirements.txt             # Dépendances Python
├── .env                         # Configuration (à créer)
├── .gitignore                   # Fichiers ignorés par Git
│
├── data/                        # Données (gitignored)
│   ├── sample/                  # CSV téléchargés
│   │   ├── openfoodfacts-fr.csv
│   │   └── openfoodfacts-fr-sample-30000.csv
│   └── silver/                  # Parquet nettoyé
│       └── products/*.parquet
│
├── etl/                         # Code ETL Spark
│   ├── config.py                # Configuration centralisée
│   ├── download_data.py         # Téléchargement OpenFoodFacts
│   ├── bronze_to_silver.py      # Nettoyage + normalisation
│   ├── silver_to_gold.py        # Chargement MariaDB
│   ├── quality_checks.py        # Génération rapport qualité
│   ├── explore_schema.py        # Exploration du schéma CSV
│   └── utils/
│       └── quality.py           # Fonctions de qualité
│
├── sql/                         # Scripts SQL
│   ├── ddl/                     # Data Definition Language
│   │   ├── 01_create_dimensions.sql
│   │   ├── 02_create_facts.sql
│   │   └── 03_create_bridge.sql
│   ├── dml/                     # Data Manipulation Language
│   │   └── truncate_all.sql
│   └── queries/                 # Requêtes analytiques
│       └── analytics.sql
│
├── docs/                        # Documentation
│   ├── architecture.md          # Note d'architecture
│   ├── data_dictionary.md       # Dictionnaire de données
│   ├── quality_rules.md         # Règles de qualité détaillées
│   └── schemas/                 # Schémas et diagrammes
│       └── datamart_schema.md
│
├── logs/                        # Logs ETL (gitignored)
│   └── quality_report_*.json
│
└── reports/                     # Rapports de qualité (gitignored)
    └── quality_report_*.json
```

---

## Documentation

### Documents disponibles

- **[Architecture](docs/architecture.md)** : Choix techniques, flux de données, stratégies
- **[Data Dictionary](docs/data_dictionary.md)** : Schéma complet du datamart
- **[Quality Rules](docs/quality_rules.md)** : Règles de qualité détaillées avec exemples
- **[Datamart Schema](docs/schemas/datamart_schema.md)** : Diagramme ER et explications

### Schéma du datamart (résumé)

**Dimensions :**
- `dim_time` (time_sk) : Dimension temporelle
- `dim_brand` (brand_sk) : Marques
- `dim_category` (category_sk) : Catégories (hiérarchique)
- `dim_country` (country_sk) : Pays
- `dim_product` (product_sk) : Produits (SCD Type 2)

**Faits :**
- `fact_nutrition_snapshot` : Mesures nutritionnelles + scores

**Bridge :**
- `bridge_product_category` : Relation N-N produits ↔ catégories

---

## Auteurs

**Projet réalisé par :**
- Félicien
- Charif
- Clément

**Date :** 25 janvier 2026