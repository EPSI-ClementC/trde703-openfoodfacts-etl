-- ============================================================================
-- REQUÊTES ANALYTIQUES - OpenFoodFacts Datamart
-- ============================================================================

-- ----------------------------------------------------------------------------
-- 1. TOP 10 MARQUES PAR PROPORTION DE NUTRI-SCORE A/B
-- ----------------------------------------------------------------------------
SELECT 
    b.brand_name,
    COUNT(*) as total_produits,
    SUM(CASE WHEN f.nutriscore_grade IN ('a', 'b') THEN 1 ELSE 0 END) as produits_ab,
    ROUND(SUM(CASE WHEN f.nutriscore_grade IN ('a', 'b') THEN 1 ELSE 0 END) * 100.0 / COUNT(*), 2) as pct_ab
FROM fact_nutrition_snapshot f
JOIN dim_product p ON f.product_sk = p.product_sk
JOIN dim_brand b ON p.brand_sk = b.brand_sk
WHERE f.nutriscore_grade IS NOT NULL
GROUP BY b.brand_name
HAVING COUNT(*) >= 10  -- Au moins 10 produits
ORDER BY pct_ab DESC, total_produits DESC
LIMIT 10;

-- ----------------------------------------------------------------------------
-- 2. DISTRIBUTION NUTRI-SCORE PAR CATÉGORIE (Niveau 1)
-- ----------------------------------------------------------------------------
SELECT 
    c.category_name_fr as categorie,
    f.nutriscore_grade as nutriscore,
    COUNT(*) as nb_produits,
    ROUND(COUNT(*) * 100.0 / SUM(COUNT(*)) OVER (PARTITION BY c.category_name_fr), 2) as pct_dans_categorie
FROM fact_nutrition_snapshot f
JOIN dim_product p ON f.product_sk = p.product_sk
JOIN dim_category c ON p.primary_category_sk = c.category_sk
WHERE f.nutriscore_grade IN ('a', 'b', 'c', 'd', 'e')
  AND c.level = 1
GROUP BY c.category_name_fr, f.nutriscore_grade
ORDER BY categorie, nutriscore;

-- ----------------------------------------------------------------------------
-- 3. ANALYSE PAR CATÉGORIE : MOYENNE SUCRES (TOP 15 catégories)
-- Note: Pays non inclus car stockés en JSON dans dim_product.countries_tags
-- ----------------------------------------------------------------------------
WITH top_categories AS (
    SELECT primary_category_sk
    FROM dim_product
    WHERE primary_category_sk IS NOT NULL
    GROUP BY primary_category_sk
    ORDER BY COUNT(*) DESC
    LIMIT 15
)
SELECT
    ca.category_name_fr as categorie,
    ca.category_code,
    COUNT(*) as nb_produits,
    ROUND(AVG(f.sugars_100g), 2) as avg_sucres_100g,
    ROUND(MIN(f.sugars_100g), 2) as min_sucres_100g,
    ROUND(MAX(f.sugars_100g), 2) as max_sucres_100g,
    ROUND(STDDEV(f.sugars_100g), 2) as stddev_sucres_100g
FROM fact_nutrition_snapshot f
JOIN dim_product p ON f.product_sk = p.product_sk
JOIN dim_category ca ON p.primary_category_sk = ca.category_sk
WHERE f.sugars_100g IS NOT NULL
  AND ca.category_sk IN (SELECT primary_category_sk FROM top_categories)
GROUP BY ca.category_name_fr, ca.category_code
HAVING COUNT(*) >= 10  -- Au moins 10 produits
ORDER BY avg_sucres_100g DESC;

-- ----------------------------------------------------------------------------
-- 4. TAUX DE COMPLÉTUDE DES NUTRIMENTS PAR MARQUE (TOP 20)
-- ----------------------------------------------------------------------------
WITH brand_completeness AS (
    SELECT 
        b.brand_name,
        COUNT(*) as total_produits,
        SUM(CASE WHEN f.energy_kcal_100g IS NOT NULL THEN 1 ELSE 0 END) as with_energy,
        SUM(CASE WHEN f.fat_100g IS NOT NULL THEN 1 ELSE 0 END) as with_fat,
        SUM(CASE WHEN f.carbohydrates_100g IS NOT NULL THEN 1 ELSE 0 END) as with_carbs,
        SUM(CASE WHEN f.sugars_100g IS NOT NULL THEN 1 ELSE 0 END) as with_sugars,
        SUM(CASE WHEN f.proteins_100g IS NOT NULL THEN 1 ELSE 0 END) as with_proteins,
        SUM(CASE WHEN f.salt_100g IS NOT NULL THEN 1 ELSE 0 END) as with_salt
    FROM fact_nutrition_snapshot f
    JOIN dim_product p ON f.product_sk = p.product_sk
    JOIN dim_brand b ON p.brand_sk = b.brand_sk
    GROUP BY b.brand_name
    HAVING COUNT(*) >= 20  -- Au moins 20 produits
)
SELECT 
    brand_name,
    total_produits,
    ROUND((with_energy + with_fat + with_carbs + with_sugars + with_proteins + with_salt) * 100.0 / (total_produits * 6), 2) as taux_completude_pct,
    ROUND(with_energy * 100.0 / total_produits, 1) as pct_energy,
    ROUND(with_sugars * 100.0 / total_produits, 1) as pct_sugars,
    ROUND(with_salt * 100.0 / total_produits, 1) as pct_salt
FROM brand_completeness
ORDER BY taux_completude_pct DESC
LIMIT 20;

-- ----------------------------------------------------------------------------
-- 5. LISTE DES ANOMALIES NUTRITIONNELLES
-- ----------------------------------------------------------------------------
SELECT 
    p.code,
    p.product_name,
    b.brand_name,
    f.sugars_100g,
    f.salt_100g,
    f.fat_100g,
    f.proteins_100g,
    CASE 
        WHEN f.sugars_100g > 80 THEN 'Sucres > 80g'
        WHEN f.salt_100g > 25 THEN 'Sel > 25g'
        WHEN f.fat_100g > 100 THEN 'Graisses > 100g'
        WHEN f.proteins_100g > 100 THEN 'Protéines > 100g'
        ELSE 'Autre anomalie'
    END as type_anomalie
FROM fact_nutrition_snapshot f
JOIN dim_product p ON f.product_sk = p.product_sk
LEFT JOIN dim_brand b ON p.brand_sk = b.brand_sk
WHERE f.sugars_100g > 80 
   OR f.salt_100g > 25
   OR f.fat_100g > 100
   OR f.proteins_100g > 100
ORDER BY type_anomalie, p.product_name
LIMIT 100;

-- ----------------------------------------------------------------------------
-- 6. ÉVOLUTION HEBDOMADAIRE DE LA COMPLÉTUDE (6 derniers mois)
-- ----------------------------------------------------------------------------
WITH weekly_completeness AS (
    SELECT 
        t.year,
        t.week,
        t.date as week_date,
        COUNT(*) as total_produits,
        SUM(CASE WHEN f.energy_kcal_100g IS NOT NULL THEN 1 ELSE 0 END) as with_energy,
        SUM(CASE WHEN f.sugars_100g IS NOT NULL THEN 1 ELSE 0 END) as with_sugars,
        SUM(CASE WHEN f.salt_100g IS NOT NULL THEN 1 ELSE 0 END) as with_salt,
        SUM(CASE WHEN f.nutriscore_grade IN ('a','b','c','d','e') THEN 1 ELSE 0 END) as with_nutriscore
    FROM fact_nutrition_snapshot f
    JOIN dim_time t ON f.time_sk = t.time_sk
    WHERE t.date >= DATE_SUB(CURDATE(), INTERVAL 6 MONTH)
    GROUP BY t.year, t.week, t.date
)
SELECT 
    year,
    week,
    MIN(week_date) as semaine,
    SUM(total_produits) as produits_semaine,
    ROUND(AVG(with_energy * 100.0 / total_produits), 2) as avg_pct_energy,
    ROUND(AVG(with_sugars * 100.0 / total_produits), 2) as avg_pct_sugars,
    ROUND(AVG(with_salt * 100.0 / total_produits), 2) as avg_pct_salt,
    ROUND(AVG(with_nutriscore * 100.0 / total_produits), 2) as avg_pct_nutriscore
FROM weekly_completeness
GROUP BY year, week
ORDER BY year DESC, week DESC
LIMIT 26;  -- 6 mois ≈ 26 semaines

-- ----------------------------------------------------------------------------
-- 7. BONUS : TOP 10 CATÉGORIES AVEC LE PLUS D'ADDITIFS (si données disponibles)
-- ----------------------------------------------------------------------------
-- Note: Cette requête nécessite des données d'additifs dans quality_issues_json
-- À adapter selon vos données réelles
SELECT 
    c.category_name_fr as categorie,
    COUNT(DISTINCT p.product_sk) as nb_produits,
    COUNT(*) as nb_produits_avec_issues,
    ROUND(COUNT(*) * 100.0 / COUNT(DISTINCT p.product_sk), 2) as pct_avec_issues
FROM fact_nutrition_snapshot f
JOIN dim_product p ON f.product_sk = p.product_sk
JOIN dim_category c ON p.primary_category_sk = c.category_sk
WHERE f.quality_issues_json IS NOT NULL
  AND f.quality_issues_json != ''
  AND f.quality_issues_json != '{}'
GROUP BY c.category_name_fr
HAVING COUNT(DISTINCT p.product_sk) >= 10
ORDER BY pct_avec_issues DESC, nb_produits DESC
LIMIT 10;

-- ============================================================================
-- FIN DES REQUÊTES ANALYTIQUES
-- ============================================================================
