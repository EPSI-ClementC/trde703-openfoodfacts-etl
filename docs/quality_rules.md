# Règles de Qualité des Données - OpenFoodFacts

## Informations

**Projet :** ETL OpenFoodFacts - Datamart Nutrition & Qualité
**Auteurs :** Félicien, Charif, Clément
**Date :** 25 janvier 2026

---

## Introduction

Ce document décrit les **règles de qualité des données** appliquées au projet, organisées selon le **framework DAMA** (6 dimensions).

**Objectifs :**
- Garantir fiabilité des analyses
- Détecter anomalies et erreurs
- Tracer la qualité dans le temps

**Métriques générées :**
- `logs/quality_report_*.json` (Bronze → Silver)
- `reports/quality_report_*.json` (post-chargement Gold)

---

## Complétude (Completeness)

### Définition
Taux de renseignement des champs critiques pour l'analyse nutritionnelle.

### Règle : Score de complétude (0-1)

**Formule :**
```python
completeness_score = nb_champs_renseignés / 8
```

**Champs critiques (8) :**
1. `product_name` (12.5%)
2. `brands` (12.5%)
3. `categories_tags` (12.5%)
4. `energy_kcal_100g` (12.5%)
5. `fat_100g` (12.5%)
6. `carbohydrates_100g` (12.5%)
7. `sugars_100g` (12.5%)
8. `proteins_100g` (12.5%)
9. `salt_100g` (12.5%)

### Seuils de qualité

| Score | Interprétation | Action |
|-------|----------------|--------|
| 0.00 - 0.30 | ❌ Mauvaise | Exclure ou signaler |
| 0.31 - 0.60 | ⚠️ Moyenne | Utiliser avec prudence |
| 0.61 - 0.85 | ✅ Bonne | Exploitable |
| 0.86 - 1.00 | ⭐ Excellente | Données de référence |

### Implémentation (PySpark)

```python
filled_count = lit(0)
for field in critical_fields:
    filled_count = filled_count + when(
        (col(field).isNotNull()) & (col(field) != ''), 1
    ).otherwise(0)

df = df.withColumn('completeness_score', (filled_count / 8).cast('decimal(3,2)'))
```

### Résultats (sample 30k)

```json
{
  "avg_completeness": 0.71,
  "completeness_pct": {
    "product_name_pct": 91.86,
    "brand_pct": 54.64,
    "category_pct": 48.60,
    "energy_kcal_100g_pct": 74.42,
    "sugars_100g_pct": 69.01
  }
}
```

**Analyse :** Score moyen 71% (Bonne qualité ✅)

---

## Unicité (Uniqueness)

### Définition
Un code-barres correspond à **un seul produit actif** dans le datamart.

### Règle 1 : Un code = Un produit courant

**Contrainte SQL :**
```sql
SELECT code, COUNT(*) as cnt
FROM dim_product
WHERE is_current = TRUE
GROUP BY code
HAVING cnt > 1;
-- Doit retourner 0 ligne
```

### Règle 2 : Déduplication

**Implémentation (PySpark) :**
```python
window = Window.partitionBy('code').orderBy(
    desc(coalesce(col('last_modified_t'), lit(0)))
)

df_dedup = df.withColumn('row_num', row_number().over(window)) \
             .filter(col('row_num') == 1) \
             .drop('row_num')
```

**Stratégie :** Garde le produit le plus récent (last_modified_t)

### Règle 3 : Filtrage codes invalides

```python
df = df.filter(
    (col('code').isNotNull()) &
    (col('code') != '') &
    (col('code') != '0') &
    (col('code') != 'null')
)
```

### Résultats

```json
{
  "uniqueness": {
    "total_records": 29999,
    "unique_codes": 29999,
    "duplicates": 0,
    "uniqueness_pct": 100.0
  }
}
```

**Analyse :** Taux unicité parfait (100% ✅)

---

## Cohérence (Consistency)

### Définition
Les valeurs respectent les **relations logiques** entre elles.

### Règle 1 : Harmonisation sel/sodium

**Relation chimique :**
```
sel (NaCl) ≈ 2.5 × sodium (Na)
```

**Implémentation :**
```python
# Si sel manque mais sodium présent
df = df.withColumn('salt_100g',
    when(col('salt_100g').isNull() & col('sodium_100g').isNotNull(),
         col('sodium_100g') * 2.5
    ).otherwise(col('salt_100g'))
)

# Si sodium manque mais sel présent
df = df.withColumn('sodium_100g',
    when(col('sodium_100g').isNull() & col('salt_100g').isNotNull(),
         col('salt_100g') / 2.5
    ).otherwise(col('sodium_100g'))
)
```

### Règle 2 : Cohérence énergétique (future)

**Formule théorique :**
```
Énergie (kcal) ≈ Protéines×4 + Glucides×4 + Lipides×9
```

### Règle 3 : Cohérence sucres/glucides

**Relation logique :**
```
sucres_100g ≤ carbohydrates_100g
(les sucres sont un sous-ensemble des glucides)
```

---

## Conformité (Validity)

### Définition
Les valeurs respectent des **bornes réalistes** pour des données nutritionnelles.

### Règle : Bornes nutritionnelles pour 100g

**Configuration (etl/config.py) :**
```python
NUTRIENT_BOUNDS = {
    'energy_kcal_100g': (0, 900),      # Max: huile pure
    'fat_100g': (0, 100),               # Max: 100% lipides
    'carbohydrates_100g': (0, 100),    # Max: 100% glucides
    'sugars_100g': (0, 100),           # Max: sucre pur
    'proteins_100g': (0, 100),         # Max: protéine pure
    'salt_100g': (0, 100),             # Max: sel pur
    'sodium_100g': (0, 40)             # Max: 40g/100g
}
```

### Seuils d'alerte spécifiques

| Anomalie | Seuil | Cause probable |
|----------|-------|----------------|
| `sugars_100g > 80` | 80g | Sucre pur ou erreur saisie |
| `salt_100g > 25` | 25g | Sel pur ou confusion mg/g |
| `fat_100g > 100` | 100g | Impossible (erreur) |
| `proteins_100g > 100` | 100g | Impossible (erreur) |

### Implémentation (PySpark)

```python
for field, (min_val, max_val) in NUTRIENT_BOUNDS.items():
    anomaly = when(
        (col(field).isNotNull()) &
        ((col(field) < min_val) | (col(field) > max_val)),
        lit(f"{field}_out_of_bounds")
    )
    anomaly_conditions.append(anomaly)

df = df.withColumn('quality_issues', array(*anomaly_conditions))
```

### Résultats (sample 30k)

```json
{
  "anomalies": {
    "total_anomalies": 1330,
    "sugars_gt_80": 1135,
    "salt_gt_25": 207,
    "fat_gt_100": 775,
    "proteins_gt_100": 98
  }
}
```

**Analyse :** 4.4% anomalies (< 5% ✅), majoritairement légitimes (sucre, sel pur)

---

## Exactitude (Accuracy)

### Définition
Conformité aux **référentiels officiels** (taxonomies OpenFoodFacts).

### Règle 1 : Nutri-Score valide

**Valeurs autorisées :**
```python
valid_nutriscore = ['a', 'b', 'c', 'd', 'e', 'not-applicable', 'unknown']
```

### Règle 2 : NOVA valide

**Valeurs autorisées :**
```python
valid_nova = [1, 2, 3, 4]
```

### Règle 3 : Catégories conformes

**Référentiel :** OpenFoodFacts Taxonomy
- URL : https://world.openfoodfacts.org/data/taxonomies/categories.json
- Format : `en:beverages`, `fr:boissons`

---

## Traçabilité (Timeliness)

### Définition
Mesure la **fraîcheur des données** et leur mise à jour.

### Règle : Horodatage systématique

**Colonnes de traçabilité :**
```sql
-- Dans fact_nutrition_snapshot
last_modified_t BIGINT     -- Timestamp OFF (source)
loaded_at TIMESTAMP        -- Timestamp chargement DW

-- Dans dim_product
effective_from TIMESTAMP   -- Début validité (SCD2)
effective_to TIMESTAMP     -- Fin validité (SCD2)
created_at TIMESTAMP       -- Création initiale
updated_at TIMESTAMP       -- Dernière modification
```

---

## Rapport de qualité

### Génération automatique

**Script :**
```bash
python etl/quality_checks.py
```

**Sortie :** `reports/quality_report_YYYYMMDD_HHMMSS.json`

### Structure du rapport

```json
{
  "run_timestamp": "2026-01-25T22:50:03",
  "dimensions": {
    "products": 29999,
    "brands": 3800,
    "categories": 1900
  },
  "completeness": {
    "product_name_pct": 91.86,
    "brand_pct": 54.64
  },
  "uniqueness": {
    "unique_codes": 29999,
    "duplicates": 0,
    "uniqueness_pct": 100.0
  },
  "anomalies": {
    "total_anomalies": 1330,
    "sugars_gt_80": 1135
  }
}
```

---

## Actions correctives

### Niveau 1 : Alerte (Monitoring)

**Seuils d'alerte :**
- Complétude moyenne < 0.6 → ⚠️ Investigation requise
- Anomalies > 10% → ⚠️ Problème de source
- Duplicates > 0 → ⚠️ Bug déduplication

### Niveau 2 : Exclusion temporaire

**Créer vue qualité :**
```sql
CREATE VIEW v_produits_quality AS
SELECT *
FROM fact_nutrition_snapshot
WHERE completeness_score >= 0.6
  AND quality_issues_json IS NULL;
```

### Niveau 3 : Correction manuelle

**Processus :**
1. Identifier produits problématiques
2. Vérifier source OpenFoodFacts
3. Corriger si erreur ETL
4. Signaler à OFF si erreur source

---

## Évolution de la qualité

### Suivi dans le temps

**Requête :**
```sql
SELECT
    t.year, t.month,
    AVG(f.completeness_score) as avg_completeness,
    COUNT(CASE WHEN f.quality_issues_json IS NOT NULL THEN 1 END) * 100.0 / COUNT(*) as pct_anomalies
FROM fact_nutrition_snapshot f
JOIN dim_time t ON f.time_sk = t.time_sk
GROUP BY t.year, t.month
ORDER BY t.year, t.month;
```

### Objectifs qualité (KPI)

| KPI | Cible 2026 | Actuel | Statut |
|-----|------------|--------|--------|
| Complétude moyenne | > 0.75 | 0.71 | ⚠️ |
| Taux d'unicité | 100% | 100% | ✅ |
| Taux d'anomalies | < 3% | 4.4% | ⚠️ |
| Couverture marques | > 60% | 54.6% | ⚠️ |

---

**Auteurs :** Félicien, Charif, Clément
**Dernière mise à jour :** 25 janvier 2026
