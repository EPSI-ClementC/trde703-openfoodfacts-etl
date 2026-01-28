# Dictionnaire de Données - Datamart OpenFoodFacts

## Informations

**Projet :** ETL OpenFoodFacts - Datamart Nutrition & Qualité
**Auteurs :** Félicien, Charif, Clément
**Date :** 25 janvier 2026

---

## Vue d'ensemble

Datamart organisé en **schéma en étoile** pour l'analyse nutritionnelle des produits OpenFoodFacts.

**Statistiques (sample 30k) :**
- Produits : ~29,999
- Marques : ~3,800
- Catégories : ~1,900
- Pays : ~150

**Conventions :**
- Clés surrogates : `<table>_sk` (ex: `product_sk`)
- Clés naturelles : `code`, `category_code`, `country_code`
- Booléens : Préfixe `is_`, `has_`
- Dates : Suffixe `_at`, `_from/_to` (SCD2)

---

## Dimensions

### dim_time

**Description :** Dimension temporelle (granularité : jour)

| Colonne | Type | Description |
|---------|------|-------------|
| `time_sk` | INT PK | Clé surrogate |
| `date` | DATE UNIQUE | Date (YYYY-MM-DD) |
| `year`, `month`, `day` | SMALLINT/TINYINT | Composantes date |
| `week`, `quarter` | TINYINT | Semaine ISO, trimestre |
| `day_of_week` | TINYINT | 1=dimanche, 7=samedi |
| `is_weekend` | BOOLEAN | TRUE si samedi/dimanche |

**Index :** `idx_date`, `idx_year_month`

---

### dim_brand

**Description :** Marques de produits

| Colonne | Type | Description |
|---------|------|-------------|
| `brand_sk` | INT PK | Clé surrogate |
| `brand_name` | VARCHAR(255) UNIQUE | Nom marque (original) |
| `brand_clean` | VARCHAR(255) | Version normalisée (sans accents) |

**Index :** `uk_brand (UNIQUE)`, `idx_brand_clean`

**Note :** Normalisation Unicode pour dédoublonnage (Nestlé → Nestle)

---

### dim_category

**Description :** Catégories de produits (structure hiérarchique)

| Colonne | Type | Description |
|---------|------|-------------|
| `category_sk` | INT PK | Clé surrogate |
| `category_code` | VARCHAR(255) UNIQUE | Code OFF (ex: `en:beverages`) |
| `category_name_fr` | VARCHAR(255) | Nom français |
| `level` | TINYINT | Niveau hiérarchique (1=racine) |
| `parent_category_sk` | INT FK | Catégorie parente |

**Index :** `uk_category_code`, `idx_level`, `idx_parent`

**Note :** Hiérarchie préparée mais actuellement aplatie (level=1)

---

### dim_country

**Description :** Pays de vente/production

| Colonne | Type | Description |
|---------|------|-------------|
| `country_sk` | INT PK | Clé surrogate |
| `country_code` | VARCHAR(10) UNIQUE | Code pays (nettoyé) |
| `country_name_fr` | VARCHAR(100) | Nom français |

**Index :** `uk_country_code`, `idx_country_name_fr`

**Note :** Nettoyage `en:france` → `france`, tronqué à 10 chars

---

### dim_product

**Description :** Produits (SCD Type 2)

| Colonne | Type | Description |
|---------|------|-------------|
| `product_sk` | BIGINT PK | Clé surrogate |
| `code` | VARCHAR(50) | Code-barres EAN-13 (clé naturelle) |
| `product_name` | VARCHAR(500) | Nom produit |
| `brand_sk` | INT FK | Marque |
| `primary_category_sk` | INT FK | Catégorie principale |
| `countries_tags` | TEXT | Liste pays (JSON) |
| `effective_from` | TIMESTAMP | Date début validité |
| `effective_to` | TIMESTAMP | Date fin (NULL si actif) |
| `is_current` | BOOLEAN | TRUE si version active |
| `row_hash` | VARCHAR(64) | MD5 pour détecter changements |

**Index :** `idx_code`, `idx_code_current`, `idx_brand`, `idx_category`

**SCD Type 2 :**
- Un `code` peut avoir plusieurs `product_sk` (historique)
- Un seul `product_sk` avec `is_current=TRUE` par `code`
- `row_hash` = MD5 de (product_name + brands + categories + nutriscore)

---

## Table de faits

### fact_nutrition_snapshot

**Description :** Mesures nutritionnelles + scores + qualité

| Colonne | Type | Description |
|---------|------|-------------|
| `fact_id` | BIGINT PK | Identifiant unique |
| `product_sk` | BIGINT FK | Produit |
| `time_sk` | INT FK | Date modification |

**Mesures nutritionnelles (pour 100g) :**
- `energy_kcal_100g`, `energy_kj_100g` : Énergie
- `fat_100g`, `saturated_fat_100g` : Lipides
- `carbohydrates_100g`, `sugars_100g` : Glucides
- `fiber_100g`, `proteins_100g` : Fibres, protéines
- `salt_100g`, `sodium_100g` : Sel, sodium

**Scores :**
- `nutriscore_grade` : CHAR(10), valeurs a-e
- `nutriscore_score` : INT, -15 à +40
- `nova_group` : TINYINT, 1-4 (transformation)
- `ecoscore_grade` : CHAR(10), valeurs a-e

**Métriques qualité :**
- `completeness_score` : DECIMAL(3,2), 0.00-1.00
- `nb_nutrients_filled` : TINYINT, 0-9
- `has_image`, `has_ingredients` : BOOLEAN
- `quality_issues_json` : TEXT, anomalies (JSON array)

**Audit :**
- `last_modified_t` : BIGINT, timestamp UNIX OFF
- `loaded_at` : TIMESTAMP, date chargement DW

**Index :** `idx_product`, `idx_time`, `idx_nutriscore`, `idx_nova`

**Formules :**

**Completeness Score :**
```
score = nb_champs_critiques_renseignés / 8
Champs : product_name, brands, categories, 5 nutriments clés
```

**Anomalies (quality_issues_json) :**
```json
["sugars_100g_out_of_bounds", "salt_100g_out_of_bounds"]
```

---

## Bridge table

### bridge_product_category

**Description :** Relation N-N produits ↔ catégories

| Colonne | Type | Description |
|---------|------|-------------|
| `product_sk` | BIGINT PK, FK | Produit |
| `category_sk` | INT PK, FK | Catégorie |
| `is_primary` | BOOLEAN | TRUE si catégorie principale |

**Index :** `PRIMARY KEY (product_sk, category_sk)`, `idx_product`, `idx_category`


---

## Glossaire métier

### Nutri-Score
Système d'étiquetage nutritionnel à 5 niveaux (A-E) évaluant la qualité nutritionnelle.
- **A (vert)** : Meilleur
- **E (rouge)** : Moins bon
- **Calcul :** Points négatifs (énergie, sucres, graisses, sel) - Points positifs (fruits, fibres, protéines)

### Groupe NOVA
Classification des aliments selon leur degré de transformation industrielle.
- **1** : Aliments non transformés (fruits, légumes)
- **2** : Ingrédients culinaires (huile, sucre, sel)
- **3** : Aliments transformés (pain, fromages)
- **4** : Produits ultra-transformés (sodas, snacks)

### Eco-Score
Note environnementale (A-E) évaluant l'impact écologique (ACV, bio, origine, emballage).

### EAN-13
Code-barres international 13 chiffres identifiant un produit commercial.
- Format : `3 274 080 005 003`
- 3 premiers : Pays (300-379 = France)
- Dernier : Clé de contrôle

### SCD Type 2
Technique de modélisation conservant l'historique des modifications.
- `effective_from` : Date début validité
- `effective_to` : Date fin (NULL si actif)
- `is_current` : TRUE pour version actuelle

---

## Sources de données

### OpenFoodFacts

**URL :** https://fr.openfoodfacts.org/
**Licence :** Open Database License (ODbL)
**Format :** CSV (séparateur tabulation)
**Fréquence :** Quotidienne

**Mapping colonnes principales :**

| Colonne OFF | Table DW | Transformation |
|-------------|----------|----------------|
| `code` | `dim_product.code` | Aucune |
| `product_name` | `dim_product.product_name` | Trim, normalisation |
| `brands` | `dim_brand.brand_name` | Split `,`, garde 1ère |
| `categories_tags` | `dim_category.category_code` | Split `,` |
| `energy-kcal_100g` | `fact_nutrition.energy_kcal_100g` | Cast DECIMAL |
| `salt_100g` | `fact_nutrition.salt_100g` | Harmonisation sodium |
| `nutriscore_grade` | `fact_nutrition.nutriscore_grade` | Lowercase |
| `last_modified_t` | `dim_time.date` | Conversion UNIX → DATE |

**Taille datasets :**
- Monde : ~3M produits (~40 GB)
- France : ~500k produits (~3 GB)
- Sample : 30k produits (~73 MB)

---

## Vérification intégrité

**Vérifier FK orphelines :**
```sql
SELECT COUNT(*) FROM fact_nutrition_snapshot f
LEFT JOIN dim_product p ON f.product_sk = p.product_sk
WHERE p.product_sk IS NULL;
-- Doit retourner 0
```

**Vérifier unicité codes actifs :**
```sql
SELECT code, COUNT(*) as cnt
FROM dim_product
WHERE is_current = TRUE
GROUP BY code
HAVING cnt > 1;
-- Doit retourner 0 ligne
```

---

**Auteurs :** Félicien, Charif, Clément
**Dernière mise à jour :** 25 janvier 2026
