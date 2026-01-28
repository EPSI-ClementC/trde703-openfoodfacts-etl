#!/bin/bash
# Script d'exécution du pipeline ETL complet
# Auteurs: Félicien, Charif, Clément
# Module: TRDE703 - M1 EISI/CDPIA/CYBER

set -e  # Arrêt en cas d'erreur

echo "======================================"
echo "🚀 OpenFoodFacts ETL Pipeline"
echo "======================================"
echo ""

# Vérification que le sample existe
if [ ! -f "data/sample/openfoodfacts-fr-sample-30000.csv" ]; then
    echo "❌ Erreur: Le fichier data/sample/openfoodfacts-fr-sample-30000.csv n'existe pas!"
    echo "   Assurez-vous que le sample est bien présent dans le projet."
    exit 1
fi

echo "✅ Fichier sample trouvé: data/sample/openfoodfacts-fr-sample-30000.csv"
echo ""

# Attendre que MariaDB soit prêt
echo "⏳ Attente de MariaDB..."
while ! mariadb-admin ping -h"$DB_HOST" -u"$DB_USER" -p"$DB_PASSWORD" --silent 2>/dev/null; do
    echo "   MariaDB n'est pas encore prêt, attente..."
    sleep 2
done
echo "✅ MariaDB est prêt!"
echo ""

# Nettoyer la base de données
echo "🧹 Nettoyage de la base de données..."
mariadb -h"$DB_HOST" -u"$DB_USER" -p"$DB_PASSWORD" "$DB_NAME" -e "
    SET FOREIGN_KEY_CHECKS = 0;
    DROP TABLE IF EXISTS fact_nutrition_snapshot;
    DROP TABLE IF EXISTS bridge_product_category;
    DROP TABLE IF EXISTS dim_product;
    DROP TABLE IF EXISTS dim_category;
    DROP TABLE IF EXISTS dim_brand;
    DROP TABLE IF EXISTS dim_country;
    DROP TABLE IF EXISTS dim_time;
    SET FOREIGN_KEY_CHECKS = 1;
" 2>/dev/null || echo "   (Pas de tables à supprimer)"
echo "✅ Base de données nettoyée"
echo ""

# Exécution des scripts DDL
echo "📊 Création des tables (DDL)..."
echo "   - Dimensions..."
mariadb -h"$DB_HOST" -u"$DB_USER" -p"$DB_PASSWORD" "$DB_NAME" < sql/ddl/01_create_dimensions.sql
echo "   - Tables de faits..."
mariadb -h"$DB_HOST" -u"$DB_USER" -p"$DB_PASSWORD" "$DB_NAME" < sql/ddl/02_create_facts.sql
echo "   - Bridge tables..."
mariadb -h"$DB_HOST" -u"$DB_USER" -p"$DB_PASSWORD" "$DB_NAME" < sql/ddl/03_create_bridge.sql
echo "✅ Tables créées avec succès"
echo ""

# Étape 1: Bronze → Silver
echo "======================================"
echo "📦 ÉTAPE 1/3: Bronze → Silver"
echo "======================================"
python etl/bronze_to_silver.py
echo ""

# Étape 2: Silver → Gold
echo "======================================"
echo "📦 ÉTAPE 2/3: Silver → Gold (MariaDB)"
echo "======================================"
python etl/silver_to_gold.py
echo ""

# Étape 3: Rapport de qualité
echo "======================================"
echo "📦 ÉTAPE 3/3: Rapport de qualité"
echo "======================================"
python etl/quality_checks.py
echo ""

# Résumé
echo "======================================"
echo "✅ Pipeline terminé avec succès!"
echo "======================================"
echo ""
echo "📊 Statistiques:"
mariadb -h"$DB_HOST" -u"$DB_USER" -p"$DB_PASSWORD" "$DB_NAME" -e "
    SELECT 'Produits' as table_name, COUNT(*) as nb_lignes FROM dim_product
    UNION ALL SELECT 'Marques', COUNT(*) FROM dim_brand
    UNION ALL SELECT 'Catégories', COUNT(*) FROM dim_category
    UNION ALL SELECT 'Pays', COUNT(*) FROM dim_country
    UNION ALL SELECT 'Temps', COUNT(*) FROM dim_time
    UNION ALL SELECT 'Faits nutrition', COUNT(*) FROM fact_nutrition_snapshot;
"
echo ""
echo "📁 Rapport qualité disponible dans: reports/"
echo ""
echo "Pour exécuter les requêtes analytiques:"
echo "  mariadb -h\$DB_HOST -u\$DB_USER -p\$DB_PASSWORD \$DB_NAME < sql/queries/analytics.sql"
echo ""
