#!/usr/bin/env python3
"""
Quality Checks - Génération de métriques de qualité des données
"""
from pyspark.sql import SparkSession
from pyspark.sql.functions import col, count, when, sum as spark_sum, avg, isnan, isnull
import json
from datetime import datetime
from pathlib import Path
import sys

sys.path.append(str(Path(__file__).parent.parent))
from etl.config import config

def create_spark_session():
    return SparkSession.builder \
        .appName("OpenFoodFacts-QualityChecks") \
        .master(config.SPARK_MASTER) \
        .config("spark.driver.memory", config.SPARK_DRIVER_MEMORY) \
        .config("spark.executor.memory", config.SPARK_EXECUTOR_MEMORY) \
        .config("spark.jars.packages", "mysql:mysql-connector-java:8.0.33") \
        .getOrCreate()

def load_from_mysql(spark: SparkSession, table: str):
    """Charge une table depuis MySQL"""
    return spark.read \
        .format("jdbc") \
        .option("url", config.jdbc_url) \
        .option("dbtable", table) \
        .option("user", config.DB_USER) \
        .option("password", config.DB_PASSWORD) \
        .option("driver", "com.mysql.cj.jdbc.Driver") \
        .load()

def check_completeness(df_product, df_fact):
    """Vérifie la complétude des données"""
    total_products = df_product.count()
    
    # Complétude produits
    completeness = {
        "total_products": total_products,
        "with_name": df_product.filter(col('product_name').isNotNull()).count(),
        "with_brand": df_product.filter(col('brand_sk').isNotNull()).count(),
        "with_category": df_product.filter(col('primary_category_sk').isNotNull()).count(),
    }
    
    # Complétude nutriments
    nutrient_fields = [
        'energy_kcal_100g', 'fat_100g', 'saturated_fat_100g',
        'carbohydrates_100g', 'sugars_100g', 'proteins_100g',
        'fiber_100g', 'salt_100g', 'sodium_100g'
    ]
    
    for field in nutrient_fields:
        completeness[f"with_{field}"] = df_fact.filter(
            col(field).isNotNull() & ~isnan(col(field))
        ).count()
    
    # Calcul des pourcentages
    completeness_pct = {
        "product_name_pct": round(completeness["with_name"] / total_products * 100, 2),
        "brand_pct": round(completeness["with_brand"] / total_products * 100, 2),
        "category_pct": round(completeness["with_category"] / total_products * 100, 2),
    }
    
    for field in nutrient_fields:
        completeness_pct[f"{field}_pct"] = round(
            completeness[f"with_{field}"] / total_products * 100, 2
        )
    
    return completeness, completeness_pct

def check_uniqueness(df_product):
    """Vérifie l'unicité des codes-barres"""
    total = df_product.count()
    unique_codes = df_product.select('code').distinct().count()
    duplicates = total - unique_codes
    
    return {
        "total_records": total,
        "unique_codes": unique_codes,
        "duplicates": duplicates,
        "uniqueness_pct": round(unique_codes / total * 100, 2) if total > 0 else 0
    }

def check_anomalies(df_fact):
    """Détecte les anomalies dans les nutriments"""
    
    anomalies = {}
    
    # Sugars > 80g/100g
    anomalies["sugars_gt_80"] = df_fact.filter(
        col('sugars_100g') > 80
    ).count()
    
    # Salt > 25g/100g
    anomalies["salt_gt_25"] = df_fact.filter(
        col('salt_100g') > 25
    ).count()
    
    # Fat > 100g/100g (impossible)
    anomalies["fat_gt_100"] = df_fact.filter(
        col('fat_100g') > 100
    ).count()
    
    # Proteins > 100g/100g (impossible)
    anomalies["proteins_gt_100"] = df_fact.filter(
        col('proteins_100g') > 100
    ).count()
    
    # Energy négative
    anomalies["negative_energy"] = df_fact.filter(
        col('energy_kcal_100g') < 0
    ).count()
    
    # Valeurs négatives (sauf energy déjà traité)
    negative_fields = ['fat_100g', 'sugars_100g', 'salt_100g', 'proteins_100g']
    for field in negative_fields:
        anomalies[f"negative_{field}"] = df_fact.filter(
            col(field) < 0
        ).count()
    
    return anomalies

def check_nutriscore_distribution(df_fact):
    """Distribution du Nutri-Score"""
    nutriscore_dist = df_fact.groupBy('nutriscore_grade') \
        .agg(count('*').alias('count')) \
        .orderBy('nutriscore_grade') \
        .collect()
    
    return {row['nutriscore_grade']: row['count'] for row in nutriscore_dist}

def check_nova_distribution(df_fact):
    """Distribution des groupes NOVA"""
    nova_dist = df_fact.groupBy('nova_group') \
        .agg(count('*').alias('count')) \
        .orderBy('nova_group') \
        .collect()
    
    return {str(row['nova_group']): row['count'] for row in nova_dist}

def generate_quality_report(spark: SparkSession):
    """Génère le rapport de qualité complet"""
    
    print("=" * 70)
    print("GÉNÉRATION DU RAPPORT DE QUALITÉ")
    print("=" * 70)
    
    # Chargement des données
    print("\n📊 Chargement des données...")
    df_product = load_from_mysql(spark, "dim_product")
    df_fact = load_from_mysql(spark, "fact_nutrition_snapshot")
    df_brand = load_from_mysql(spark, "dim_brand")
    df_category = load_from_mysql(spark, "dim_category")
    df_country = load_from_mysql(spark, "dim_country")
    
    # Métriques de base
    metrics = {
        "run_timestamp": datetime.now().isoformat(),
        "dimensions": {
            "products": df_product.count(),
            "brands": df_brand.count(),
            "categories": df_category.count(),
            "countries": df_country.count(),
        },
        "facts": {
            "nutrition_records": df_fact.count(),
        }
    }
    
    # Complétude
    print("✅ Analyse de complétude...")
    completeness, completeness_pct = check_completeness(df_product, df_fact)
    metrics["completeness"] = completeness
    metrics["completeness_pct"] = completeness_pct
    
    # Unicité
    print("🔑 Vérification de l'unicité...")
    uniqueness = check_uniqueness(df_product)
    metrics["uniqueness"] = uniqueness
    
    # Anomalies
    print("⚠️  Détection des anomalies...")
    anomalies = check_anomalies(df_fact)
    metrics["anomalies"] = anomalies
    metrics["anomalies"]["total_anomalies"] = sum(anomalies.values())
    
    # Distributions
    print("📈 Calcul des distributions...")
    metrics["distributions"] = {
        "nutriscore": check_nutriscore_distribution(df_fact),
        "nova_group": check_nova_distribution(df_fact),
    }
    
    return metrics

def save_report(metrics: dict, output_path: str):
    """Sauvegarde le rapport en JSON"""
    Path(output_path).parent.mkdir(parents=True, exist_ok=True)
    
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(metrics, f, indent=2, ensure_ascii=False)
    
    print(f"\n💾 Rapport sauvegardé : {output_path}")

def print_summary(metrics: dict):
    """Affiche un résumé du rapport"""
    print("\n" + "=" * 70)
    print("RÉSUMÉ DU RAPPORT DE QUALITÉ")
    print("=" * 70)
    
    print(f"\n📊 DIMENSIONS:")
    for dim, count in metrics["dimensions"].items():
        print(f"  • {dim}: {count:,}")
    
    print(f"\n📈 FAITS:")
    print(f"  • Enregistrements nutritionnels: {metrics['facts']['nutrition_records']:,}")
    
    print(f"\n✅ COMPLÉTUDE (%):")
    comp_pct = metrics["completeness_pct"]
    print(f"  • Nom produit: {comp_pct['product_name_pct']}%")
    print(f"  • Marque: {comp_pct['brand_pct']}%")
    print(f"  • Catégorie: {comp_pct['category_pct']}%")
    print(f"  • Énergie: {comp_pct['energy_kcal_100g_pct']}%")
    print(f"  • Sucres: {comp_pct['sugars_100g_pct']}%")
    
    print(f"\n🔑 UNICITÉ:")
    uniq = metrics["uniqueness"]
    print(f"  • Codes uniques: {uniq['unique_codes']:,} / {uniq['total_records']:,}")
    print(f"  • Taux d'unicité: {uniq['uniqueness_pct']}%")
    print(f"  • Duplicatas: {uniq['duplicates']:,}")
    
    print(f"\n⚠️  ANOMALIES:")
    anom = metrics["anomalies"]
    print(f"  • Total: {anom['total_anomalies']:,}")
    print(f"  • Sucres > 80g: {anom['sugars_gt_80']:,}")
    print(f"  • Sel > 25g: {anom['salt_gt_25']:,}")
    print(f"  • Graisses > 100g: {anom['fat_gt_100']:,}")
    
    print(f"\n📊 NUTRI-SCORE:")
    for grade, count in sorted((k, v) for k, v in metrics["distributions"]["nutriscore"].items() if k is not None):
        if grade:
            print(f"  • Grade {grade}: {count:,}")
    
    print("\n" + "=" * 70)

def main():
    spark = create_spark_session()
    
    try:
        metrics = generate_quality_report(spark)
        
        # Sauvegarde
        output_dir = Path(__file__).parent.parent / "reports"
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_path = output_dir / f"quality_report_{timestamp}.json"
        
        save_report(metrics, str(output_path))
        print_summary(metrics)
        
        print("\n✅ Rapport de qualité généré avec succès!")
        
    except Exception as e:
        print(f"\n❌ ERREUR: {e}")
        import traceback
        traceback.print_exc()
        raise
    finally:
        spark.stop()

if __name__ == "__main__":
    main()
