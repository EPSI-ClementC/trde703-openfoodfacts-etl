# Note d'Architecture - OpenFoodFacts ETL

## Informations

**Projet :** ETL OpenFoodFacts - Datamart Nutrition & Qualité
**Auteurs :** Félicien, Charif, Clément
**Date :** 25 janvier 2026

---

## Vue d'ensemble

Le projet implémente une **chaîne ETL complète** transformant les données OpenFoodFacts (CSV 500k+ produits) en un **datamart relationnel** optimisé pour l'analyse nutritionnelle.

**Objectifs architecturaux :**
- Scalabilité (traitement 500k+ produits)
- Qualité (complétude, cohérence)
- Performance (requêtes < 1s)
- Reproductibilité (pipeline automatisable)

---

## Choix techniques

### 1. Apache Spark (PySpark)

**Justification :**
- ✅ Traitement distribué en mémoire
- ✅ API DataFrame riche
- ✅ Support Parquet et JDBC
- ✅ Python = rapidité développement vs Java

**Config retenue :**
- `SPARK_MASTER = "local[4]"` (4 cores)
- `SPARK_DRIVER_MEMORY = "4g"`
- `SPARK_EXECUTOR_MEMORY = "4g"`

### 2. MariaDB

**Justification :**
- ✅ SGBD relationnel standard
- ✅ Support ACID
- ✅ Performant pour jointures OLAP
- ✅ Outils monitoring matures

### 3. Parquet (Silver layer)

**Justification :**
- ✅ Format colonne (compression 5-10x)
- ✅ Typage fort
- ✅ Predicate pushdown
- ✅ Compatible Spark natif

### 4. Architecture Bronze-Silver-Gold

**Justification :**
- ✅ Séparation des responsabilités
- ✅ Traçabilité (conservation données brutes)
- ✅ Réexécution possible par niveau
- ✅ Standard industrie (Databricks, Delta Lake)

---

## Architecture des données

```
┌──────────────┐
│   BRONZE     │ CSV OpenFoodFacts (~500k lignes)
│   (Raw)      │ Format texte, doublons, erreurs
└──────┬───────┘
       │ etl/bronze_to_silver.py
       │ - Lecture schéma explicite
       │ - Nettoyage (trim, cast)
       │ - Normalisation (unités)
       │ - Déduplication
       │ - Métriques qualité
       ▼
┌──────────────┐
│   SILVER     │ Parquet partitionné
│  (Cleaned)   │ Données nettoyées, dédupliquées
│              │ + completeness_score, quality_issues_json
└──────┬───────┘
       │ etl/silver_to_gold.py
       │ - Population 5 dimensions
       │ - Génération surrogate keys
       │ - Jointures FK
       │ - Écriture JDBC MariaDB
       ▼
┌──────────────┐
│    GOLD      │ MariaDB - Schéma en étoile
│  (Datamart)  │ 5 dimensions + 1 fait + 1 bridge
└──────────────┘
```

### Modèle en étoile

```
    ┌─────────┐
    │dim_time │
    └────┬────┘
         │
    ┌────▼─────────┐
    │ dim_brand    │◄──┐
    └──────────────┘   │
                       │
    ┌──────────────────▼───────────┐
    │   fact_nutrition_snapshot    │
    │ ─────────────────────────── │
    │ fact_id, product_sk, time_sk │
    │ energy, fat, sugars, salt... │
    │ nutriscore, nova, ecoscore   │
    │ completeness_score           │
    └──────┬───────────────┬───────┘
           │               │
    ┌──────▼─────┐   ┌────▼─────┐
    │dim_category│   │dim_product│
    └────────────┘   └──────┬────┘
                            │
                     ┌──────▼──────┐
                     │ dim_country │
                     └─────────────┘
```

---

## Flux ETL détaillé

### Phase 1 : Bronze (Ingestion)

**Script :** `etl/download_data.py`

**Actions :**
- Téléchargement HTTP OpenFoodFacts
- Création sample 30k produits
- Validation basique

**Sortie :** `data/sample/openfoodfacts-fr.csv`

### Phase 2 : Silver (Transformation)

**Script :** `etl/bronze_to_silver.py`

**Transformations principales :**

1. **Lecture CSV schéma explicite** (évite inférence coûteuse)
2. **Nettoyage** : `trim(regexp_replace(col, r'\s+', ' '))`
3. **Harmonisation sel/sodium** : `sel ≈ 2.5 × sodium`
4. **Déduplication** : Window function sur `last_modified_t`
5. **Métriques qualité** : `completeness_score = nb_champs_renseignés / 8`
6. **Hash SCD2** : `md5(concat_ws('|', product_name, brands, ...))`

**Sortie :** `data/silver/products/*.parquet`

### Phase 3 : Gold (Chargement)

**Script :** `etl/silver_to_gold.py`

**Population dimensions :**

- **dim_time** : Extraction dates + calcul year, month, week, is_weekend
- **dim_brand** : Normalisation Unicode (Nestlé → Nestle)
- **dim_category** : Hiérarchie préparée
- **dim_country** : Nettoyage codes (`en:france` → `france`)
- **dim_product** : Structure SCD Type 2 (effective_from/to, is_current, row_hash)

**Table de faits :**
- Jointures dimensions → surrogate keys
- Nutriments + scores + métriques qualité

**Écriture JDBC :**
```python
df.write.format("jdbc") \
  .option("batchsize", "1000") \
  .mode("append") \
  .save()
```

---

## Stratégies de chargement

### Mode actuel : Append

**Principe :** Ajout snapshots horodatés, pas d'UPDATE/DELETE

**Avantages :**
- Simplicité
- Conservation historique

**Inconvénients :**
- Doublons si re-run (nécessite truncate manuel)

### Mode futur : Upsert (SCD Type 2)

**Principe :**
1. Calculer `row_hash` par produit
2. Comparer avec version courante (`is_current = TRUE`)
3. Si différent :
   - Fermer ancienne version (`effective_to = NOW()`, `is_current = FALSE`)
   - Insérer nouvelle version

**SQL :**
```sql
INSERT INTO dim_product (..., row_hash, is_current)
VALUES (..., 'hash123', TRUE)
ON DUPLICATE KEY UPDATE
  effective_to = IF(row_hash != VALUES(row_hash), NOW(), effective_to);
```

---

## Gestion de la qualité

### Règles implémentées

1. **Complétude** : Score pondéré 0-1 sur 8 champs critiques
2. **Unicité** : Déduplication par code-barres + `last_modified_t`
3. **Cohérence** : Harmonisation sel/sodium, bornes nutritionnelles
4. **Conformité** : Validation Nutri-Score (a-e), NOVA (1-4)

### Rapports automatiques

**Génération :** `python etl/quality_checks.py`

**Contenu JSON :**
- Dimensions (nb produits, marques, catégories)
- Complétude par champ (%)
- Unicité (% duplicates)
- Anomalies (sucres > 80g, sel > 25g, etc.)
- Distributions (Nutri-Score, NOVA)

---

## Optimisations

### Spark

1. **Partitionnement** : `df.write.partitionBy("category").parquet()`
2. **Broadcast joins** : Dimensions < 10MB (automatique)
3. **Coalesce JDBC** : `df.coalesce(1)` (évite multi-connexions)
4. **Batch size** : `batchsize=1000` (trade-off réseau/mémoire)

### MariaDB

**Index créés :**
```sql
CREATE INDEX idx_code ON dim_product(code);
CREATE INDEX idx_code_current ON dim_product(code, is_current);
CREATE INDEX idx_product ON fact_nutrition_snapshot(product_sk);
CREATE INDEX idx_nutriscore ON fact_nutrition_snapshot(nutriscore_grade);
```

**Statistiques :**
```sql
ANALYZE TABLE dim_product;
ANALYZE TABLE fact_nutrition_snapshot;
```

---

## Limites et évolutions

### Limites actuelles

1. **Pas de mode incrémental** : Full reload à chaque run (~30 min pour dataset complet)
2. **SCD2 incomplet** : Structure préparée mais pas d'UPSERT
3. **Bridge table non peuplée** : Relation N-N produits ↔ catégories définie mais vide
4. **Tests manquants** : Pas de tests unitaires

### Évolutions proposées

**Court terme :**
- Mode incrémental : `df.filter(col('last_modified_t') > last_run)`
- Bridge table : `df.withColumn('cat', explode(split('categories_tags', ',')))`
- Tests unitaires (pytest)

**Moyen terme :**
- SCD2 complet avec UPSERT
- Dashboard visualisation (Streamlit)
- Logs structurés (JSON)
- CI/CD (GitHub Actions)

**Long terme :**
- Détection anomalies ML (IQR, Isolation Forest)
- Orchestration Airflow
- Migration cloud (AWS S3 + Redshift)

---

## Métriques de succès

**Critères de validation :**
- ✅ Complétude moyenne > 70% : **71%** atteint
- ✅ Taux unicité = 100% : **100%** atteint
- ✅ Anomalies < 5% : **4.4%** atteint
- ✅ Temps exécution < 30 min : **~15 min** pour 30k

**Performance requêtes :**
- Top 10 marques : ~0.3s ✅
- Distribution Nutri-Score : ~0.5s ✅
- Heatmap pays×catégorie : ~0.8s ✅

---

## Conclusion

L'architecture mise en place respecte les **best practices industrie** (Bronze-Silver-Gold, Star Schema) et offre une **base solide** pour l'analyse nutritionnelle.

Les **choix techniques** (PySpark, MariaDB, Parquet) permettent d'atteindre les objectifs de performance avec un sample de 30k produits.

Les **limites identifiées** (mode incrémental, SCD2, tests) sont documentées avec des pistes d'évolution concrètes.

---

**Auteurs :** Félicien, Charif, Clément
**Dernière mise à jour :** 25 janvier 2026
