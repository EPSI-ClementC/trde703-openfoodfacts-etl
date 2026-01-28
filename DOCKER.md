# Guide Docker - OpenFoodFacts ETL

**Projet TRDE703 - Félicien, Charif, Clément**

---

## Démarrage rapide (2 commandes)

```bash
# 1. Lancer l'infrastructure (MariaDB + Spark)
docker-compose up -d

# 2. Exécuter le pipeline ETL complet
docker exec -it openfoodfacts-etl bash run-pipeline.sh
```

**C'est tout !** En quelques minutes, le datamart MariaDB est populé avec 30k produits.

---

## Vérifier les résultats

### Compter les enregistrements

```bash
docker exec -it openfoodfacts-mariadb mariadb -u etl_user -pETL_Pass_2025! openfoodfacts_dw -e "
SELECT 'Produits' as table_name, COUNT(*) as nb_lignes FROM dim_product
UNION ALL SELECT 'Marques', COUNT(*) FROM dim_brand
UNION ALL SELECT 'Catégories', COUNT(*) FROM dim_category
UNION ALL SELECT 'Pays', COUNT(*) FROM dim_country
UNION ALL SELECT 'Temps', COUNT(*) FROM dim_time
UNION ALL SELECT 'Faits nutrition', COUNT(*) FROM fact_nutrition_snapshot;"
```

**Résultat attendu :**
```
+------------------+-----------+
| table_name       | nb_lignes |
+------------------+-----------+
| Produits         |     29999 |
| Marques          |      5394 |
| Catégories       |      2598 |
| Pays             |       173 |
| Temps            |      1830 |
| Faits nutrition  |     29999 |
+------------------+-----------+
```

### Voir le rapport qualité

```bash
docker exec -it openfoodfacts-etl cat reports/quality_report_*.json
```

### Accéder à MariaDB

```bash
docker exec -it openfoodfacts-mariadb mariadb -u etl_user -pETL_Pass_2025! openfoodfacts_dw
```

**Dans MariaDB :**
```sql
-- Voir les tables
SHOW TABLES;

-- Requête exemple: Top 10 marques par nombre de produits
SELECT b.brand_name, COUNT(*) as nb_produits
FROM fact_nutrition_snapshot f
JOIN dim_product p ON f.product_sk = p.product_sk
JOIN dim_brand b ON p.brand_sk = b.brand_sk
GROUP BY b.brand_name
ORDER BY nb_produits DESC
LIMIT 10;

-- Distribution Nutri-Score
SELECT
    nutriscore_grade,
    COUNT(*) as nb_produits,
    ROUND(COUNT(*) * 100.0 / (SELECT COUNT(*) FROM fact_nutrition_snapshot), 2) as pourcentage
FROM fact_nutrition_snapshot
WHERE nutriscore_grade IS NOT NULL
GROUP BY nutriscore_grade
ORDER BY nutriscore_grade;
```

### Exécuter les requêtes analytiques

```bash
docker exec -it openfoodfacts-mariadb mariadb -u etl_user -pETL_Pass_2025! openfoodfacts_dw < sql/queries/analytics.sql
```

---

## Arrêter

```bash
# Arrêter les services
docker-compose down

# Tout supprimer (pour recommencer à zéro)
docker-compose down -v
```

---

## Prérequis

- **Docker Desktop** installé : https://www.docker.com/products/docker-desktop
- **4 GB RAM** disponible
- **2 GB espace disque**

---

## Architecture Docker

### Services déployés

1. **mariadb** (MariaDB 11.8)
   - Port: 3306
   - Database: openfoodfacts_dw
   - User: etl_user
   - Password: ETL_Pass_2025!

2. **spark-etl** (Python 3.9 + Spark 3.5 + OpenJDK 21)
   - Spark Master: local[4]
   - Spark Memory: 4g driver + 4g executor
   - ETL Pipeline complet

### Volumes montés

- `./data` → `/app/data` (données sample incluses)
- `./logs` → `/app/logs` (logs de pipeline)
- `./reports` → `/app/reports` (rapports qualité)
- `./etl` → `/app/etl` (code ETL)
- `./sql` → `/app/sql` (scripts SQL)

---

## Credentials MariaDB

- **Host** : localhost (depuis l'hôte) ou mariadb (depuis le container)
- **Port** : 3306
- **Database** : openfoodfacts_dw
- **User** : etl_user
- **Password** : ETL_Pass_2025!

**Note :** Les credentials sont volontairement simples car il s'agit d'un projet de test académique.

---

## Tests et validation du projet

### 1. Vérifier l'infrastructure

```bash
# Vérifier que les containers sont démarrés
docker ps

# Vous devez voir :
# - openfoodfacts-mariadb
# - openfoodfacts-etl
```

### 2. Vérifier les données source

```bash
# Vérifier que le sample existe
docker exec -it openfoodfacts-etl ls -lh data/sample/

# Vous devez voir : openfoodfacts-fr-sample-30000.csv (~73 MB)
```

### 3. Exécuter le pipeline

```bash
docker exec -it openfoodfacts-etl bash run-pipeline.sh
```

**Le pipeline va :**
1. Vérifier la présence du fichier sample
2. Attendre que MariaDB soit prêt
3. Nettoyer la base de données (DROP + CREATE tables)
4. Exécuter Bronze → Silver (nettoyage + normalisation)
5. Exécuter Silver → Gold (chargement MariaDB)
6. Générer le rapport de qualité

**Durée estimée :** 5-10 minutes selon votre machine.

### 4. Vérifier les résultats

```bash
# Compter les lignes dans les tables
docker exec -it openfoodfacts-mariadb mariadb -u etl_user -pETL_Pass_2025! openfoodfacts_dw -e "
SELECT 'Produits' as table_name, COUNT(*) FROM dim_product
UNION ALL SELECT 'Marques', COUNT(*) FROM dim_brand
UNION ALL SELECT 'Catégories', COUNT(*) FROM dim_category
UNION ALL SELECT 'Faits nutrition', COUNT(*) FROM fact_nutrition_snapshot;"

# Voir un échantillon de produits
docker exec -it openfoodfacts-mariadb mariadb -u etl_user -pETL_Pass_2025! openfoodfacts_dw -e "
SELECT p.product_name, b.brand_name, f.nutriscore_grade, f.sugars_100g
FROM fact_nutrition_snapshot f
JOIN dim_product p ON f.product_sk = p.product_sk
JOIN dim_brand b ON p.brand_sk = b.brand_sk
WHERE f.nutriscore_grade IS NOT NULL
LIMIT 10;"
```

### 5. Consulter le rapport de qualité

```bash
# Afficher le dernier rapport généré
docker exec -it openfoodfacts-etl cat reports/quality_report_*.json | head -50

# Ou copier le rapport sur votre machine
docker cp openfoodfacts-etl:/app/reports/ ./reports_backup/
```

### 6. Exécuter les requêtes analytiques

```bash
# Toutes les requêtes analytiques du projet
docker exec -it openfoodfacts-mariadb mariadb -u etl_user -pETL_Pass_2025! openfoodfacts_dw < sql/queries/analytics.sql > resultats_analytiques.txt

# Voir le fichier
cat resultats_analytiques.txt
```

---

## Dépannage

### Le container MariaDB ne démarre pas

```bash
# Vérifier les logs
docker logs openfoodfacts-mariadb

# Supprimer le volume et recommencer
docker-compose down -v
docker-compose up -d
```

### Le pipeline échoue avec "File not found"

```bash
# Vérifier que le sample est bien présent
ls -lh data/sample/openfoodfacts-fr-sample-30000.csv

# Si absent, le fichier doit être inclus dans le projet Git
# (73 MB, nécessaire pour que le prof puisse tester)
```

### Erreur de connexion à MariaDB

```bash
# Vérifier que MariaDB est prêt
docker exec -it openfoodfacts-mariadb mariadb -u root -proot_password -e "SHOW DATABASES;"

# Vérifier les credentials
docker exec -it openfoodfacts-mariadb mariadb -u etl_user -pETL_Pass_2025! openfoodfacts_dw -e "SHOW TABLES;"
```

### Manque de mémoire

Si vous voyez des erreurs "OutOfMemoryError" :

```bash
# Éditer docker-compose.yml et réduire la mémoire Spark
# SPARK_DRIVER_MEMORY: 2g
# SPARK_EXECUTOR_MEMORY: 2g

# Redémarrer les services
docker-compose down
docker-compose up -d
```

---

## Technologies utilisées

- **MariaDB 11.8** : Base de données relationnelle (compatible MySQL)
- **Apache Spark 3.5** : Framework ETL distribué
- **Python 3.9** : Langage du pipeline ETL (PySpark)
- **OpenJDK 21** : Java Runtime pour Spark
- **Docker Compose** : Orchestration des services

---

## Structure du projet dans Docker

```
/app/                          # Répertoire de travail dans le container
├── data/
│   └── sample/
│       └── openfoodfacts-fr-sample-30000.csv  # Sample 30k (fourni)
├── etl/                       # Code ETL
│   ├── bronze_to_silver.py
│   ├── silver_to_gold.py
│   └── quality_checks.py
├── sql/                       # Scripts SQL
│   ├── ddl/                   # Création tables
│   └── queries/               # Requêtes analytiques
├── logs/                      # Logs du pipeline
├── reports/                   # Rapports qualité
└── run-pipeline.sh            # Script principal
```

---


**Temps total pour tester le projet : ~10 minutes**

---

**Auteurs :** Félicien, Charif, Clément
**Date :** 25 janvier 2026
