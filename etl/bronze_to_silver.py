#!/usr/bin/env python3
"""
ETL Bronze → Silver
Lecture CSV OpenFoodFacts + Nettoyage + Normalisation
"""
from pyspark.sql import SparkSession
from pyspark.sql.functions import (
    col, trim, lower, regexp_replace, when, 
    coalesce, lit, md5, concat_ws
)
import sys
from pathlib import Path
import json
from datetime import datetime

# Import config
sys.path.append(str(Path(__file__).parent.parent))
from etl.config import config
from etl.utils.quality import (
    calculate_completeness_score,
    detect_anomalies,
    count_filled_nutrients,
    generate_quality_report
)

def create_spark_session():
    """Initialise la session Spark"""
    return SparkSession.builder \
        .appName("OpenFoodFacts-Bronze-to-Silver") \
        .master(config.SPARK_MASTER) \
        .config("spark.driver.memory", config.SPARK_DRIVER_MEMORY) \
        .config("spark.executor.memory", config.SPARK_EXECUTOR_MEMORY) \
        .config("spark.sql.shuffle.partitions", "8") \
        .getOrCreate()

def read_csv(spark: SparkSession, file_path: Path):
    """Lit le CSV OpenFoodFacts"""
    print(f"📖 Lecture du fichier: {file_path}")
    
    df = spark.read \
        .option("header", "true") \
        .option("sep", "\t") \
        .option("quote", '"') \
        .option("escape", '"') \
        .option("encoding", "UTF-8") \
        .option("multiLine", "true") \
        .csv(str(file_path))
    
    print(f"✅ {df.count()} lignes lues")
    print(f"📊 {len(df.columns)} colonnes")
    
    return df

def clean_and_normalize(df):
    """Nettoie et normalise les données"""
    print("🧹 Nettoyage et normalisation...")
    
    # Liste des colonnes à garder avec leurs transformations
    available_cols = df.columns
    
    # Sélection de base
    select_exprs = []
    
    # Identifiants
    select_exprs.append(col('code'))
    
    # Noms
    if 'product_name' in available_cols:
        select_exprs.append(col('product_name'))
    else:
        select_exprs.append(lit(None).cast('string').alias('product_name'))
        
    if 'generic_name' in available_cols:
        select_exprs.append(col('generic_name'))
    else:
        select_exprs.append(lit(None).cast('string').alias('generic_name'))
    
    if 'abbreviated_product_name' in available_cols:
        select_exprs.append(col('abbreviated_product_name'))
    else:
        select_exprs.append(lit(None).cast('string').alias('abbreviated_product_name'))
    
    # Marque et catégories
    if 'brands' in available_cols:
        select_exprs.append(col('brands'))
    else:
        select_exprs.append(lit(None).cast('string').alias('brands'))
        
    if 'categories_tags' in available_cols:
        select_exprs.append(col('categories_tags'))
    else:
        select_exprs.append(lit(None).cast('string').alias('categories_tags'))
        
    if 'categories' in available_cols:
        select_exprs.append(col('categories'))
    else:
        select_exprs.append(lit(None).cast('string').alias('categories'))
    
    # Pays
    if 'countries_tags' in available_cols:
        select_exprs.append(col('countries_tags'))
    else:
        select_exprs.append(lit(None).cast('string').alias('countries_tags'))
        
    if 'countries' in available_cols:
        select_exprs.append(col('countries'))
    else:
        select_exprs.append(lit(None).cast('string').alias('countries'))
    
    # Packaging
    if 'packaging' in available_cols:
        select_exprs.append(col('packaging'))
    else:
        select_exprs.append(lit(None).cast('string').alias('packaging'))
        
    if 'quantity' in available_cols:
        select_exprs.append(col('quantity'))
    else:
        select_exprs.append(lit(None).cast('string').alias('quantity'))
    
    # Nutriments (cast en double)
    nutrient_mapping = {
        'energy-kcal_100g': 'energy_kcal_100g',
        'energy_100g': 'energy_kj_100g',
        'fat_100g': 'fat_100g',
        'saturated-fat_100g': 'saturated_fat_100g',
        'carbohydrates_100g': 'carbohydrates_100g',
        'sugars_100g': 'sugars_100g',
        'fiber_100g': 'fiber_100g',
        'proteins_100g': 'proteins_100g',
        'salt_100g': 'salt_100g',
        'sodium_100g': 'sodium_100g'
    }
    
    for source_col, target_col in nutrient_mapping.items():
        if source_col in available_cols:
            select_exprs.append(col(source_col).cast('double').alias(target_col))
        else:
            select_exprs.append(lit(None).cast('double').alias(target_col))
    
    # Scores - ajout direct avec transformation
    if 'nutriscore_grade' in available_cols:
        select_exprs.append(trim(lower(col('nutriscore_grade'))).alias('nutriscore_grade'))
    else:
        select_exprs.append(lit(None).cast('string').alias('nutriscore_grade'))
        
    if 'nutriscore_score' in available_cols:
        select_exprs.append(col('nutriscore_score').cast('int').alias('nutriscore_score'))
    else:
        select_exprs.append(lit(None).cast('int').alias('nutriscore_score'))
        
    if 'nova_group' in available_cols:
        select_exprs.append(col('nova_group').cast('int').alias('nova_group'))
    else:
        select_exprs.append(lit(None).cast('int').alias('nova_group'))
    
    # Images & ingrédients
    if 'image_url' in available_cols:
        select_exprs.append(
            when(col('image_url').isNotNull(), lit(True)).otherwise(lit(False)).alias('has_image')
        )
    else:
        select_exprs.append(lit(False).alias('has_image'))
        
    if 'ingredients_text' in available_cols:
        select_exprs.append(
            when(col('ingredients_text').isNotNull(), lit(True)).otherwise(lit(False)).alias('has_ingredients')
        )
    else:
        select_exprs.append(lit(False).alias('has_ingredients'))
    
    # Timestamps
    if 'last_modified_t' in available_cols:
        select_exprs.append(col('last_modified_t').cast('long').alias('last_modified_t'))
    else:
        select_exprs.append(lit(None).cast('long').alias('last_modified_t'))
        
    if 'created_t' in available_cols:
        select_exprs.append(col('created_t').cast('long').alias('created_t'))
    else:
        select_exprs.append(lit(None).cast('long').alias('created_t'))
    
    # Application de toutes les transformations en une fois
    df_clean = df.select(*select_exprs)
    
    # Nettoyage des strings (trim des espaces multiples)
    string_cols = ['product_name', 'generic_name', 'brands', 'categories', 'countries']
    for col_name in string_cols:
        df_clean = df_clean.withColumn(
            col_name,
            trim(regexp_replace(col(col_name), r'\s+', ' '))
        )
    
    # Harmonisation sel/sodium (sel ≈ 2.5 × sodium)
    df_clean = df_clean.withColumn(
        'salt_100g',
        when(
            col('salt_100g').isNull() & col('sodium_100g').isNotNull(),
            col('sodium_100g') * 2.5
        ).otherwise(col('salt_100g'))
    )
    
    df_clean = df_clean.withColumn(
        'sodium_100g',
        when(
            col('sodium_100g').isNull() & col('salt_100g').isNotNull(),
            col('salt_100g') / 2.5
        ).otherwise(col('sodium_100g'))
    )
    
    print(f"✅ Nettoyage terminé: {df_clean.count()} produits")
    
    return df_clean

def deduplicate(df):
    """Déduplique par code-barres"""
    print("🔍 Déduplication par code-barres...")
    
    from pyspark.sql.window import Window
    from pyspark.sql.functions import row_number, desc
    
    # Filtre les codes null/vides
    df = df.filter(
        (col('code').isNotNull()) & 
        (col('code') != '') &
        (col('code') != '0')
    )
    
    # Window par code, ordonné par last_modified_t desc
    window = Window.partitionBy('code').orderBy(
        desc(coalesce(col('last_modified_t'), lit(0)))
    )
    
    df_dedup = df.withColumn('row_num', row_number().over(window)) \
                 .filter(col('row_num') == 1) \
                 .drop('row_num')
    
    initial_count = df.count()
    final_count = df_dedup.count()
    duplicates = initial_count - final_count
    
    print(f"✅ Déduplication: {initial_count} → {final_count} ({duplicates} doublons)")
    
    return df_dedup

def apply_quality_checks(df):
    """Applique les contrôles qualité"""
    print("✅ Application des contrôles qualité...")
    
    df = calculate_completeness_score(df)
    df = count_filled_nutrients(df)
    df = detect_anomalies(df, config.NUTRIENT_BOUNDS)
    
    # Hash pour SCD2
    df = df.withColumn(
        'row_hash',
        md5(concat_ws('|',
            coalesce(col('product_name'), lit('')),
            coalesce(col('brands'), lit('')),
            coalesce(col('categories_tags'), lit('')),
            coalesce(col('nutriscore_grade'), lit(''))
        ))
    )
    
    return df

def save_silver(df, output_path: str):
    """Sauvegarde en Parquet"""
    print(f"💾 Sauvegarde: {output_path}")
    df.write.mode('overwrite').parquet(output_path)
    print(f"✅ Données sauvegardées")

def main():
    """Pipeline principal"""
    print("=" * 70)
    print("ETL BRONZE → SILVER - OpenFoodFacts")
    print("=" * 70)
    
    spark = create_spark_session()
    
    try:
        df_bronze = read_csv(spark, config.OFF_SAMPLE_FILE)
        df_silver = clean_and_normalize(df_bronze)
        df_silver = deduplicate(df_silver)
        df_silver = apply_quality_checks(df_silver)
        
        print("\n" + "=" * 70)
        print("📊 RAPPORT DE QUALITÉ")
        print("=" * 70)
        report = generate_quality_report(df_silver)
        for key, value in report.items():
            print(f"  {key}: {value}")
        
        report_file = config.LOGS_DIR / f"quality_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        config.LOGS_DIR.mkdir(exist_ok=True)
        with open(report_file, 'w') as f:
            json.dump(report, f, indent=2)
        print(f"\n📄 Rapport: {report_file}")
        
        output_path = str(config.DATA_DIR / "silver" / "products")
        save_silver(df_silver, output_path)
        
        print("\n" + "=" * 70)
        print("📋 ÉCHANTILLON (10 lignes)")
        print("=" * 70)
        df_silver.select(
            'code', 'product_name', 'brands', 'nutriscore_grade',
            'completeness_score', 'nb_nutrients_filled'
        ).show(10, truncate=50)
        
        print("\n✅ ETL Bronze → Silver terminé!")
        
    except Exception as e:
        print(f"\n❌ ERREUR: {e}")
        import traceback
        traceback.print_exc()
        raise
    finally:
        spark.stop()

if __name__ == "__main__":
    main()
