-- Nettoyage complet du datamart
-- À exécuter avant chaque chargement complet

USE openfoodfacts_dw;

SET FOREIGN_KEY_CHECKS = 0;

TRUNCATE TABLE bridge_product_category;
TRUNCATE TABLE fact_nutrition_snapshot;
TRUNCATE TABLE dim_product;
TRUNCATE TABLE dim_category;
TRUNCATE TABLE dim_brand;
TRUNCATE TABLE dim_country;
TRUNCATE TABLE dim_time;

SET FOREIGN_KEY_CHECKS = 1;

SELECT 'Tables vidées avec succès' AS status;
