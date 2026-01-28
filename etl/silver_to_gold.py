#!/usr/bin/env python3
"""
ETL Silver → Gold - Version finale avec normalisation Unicode + substring
"""
from pyspark.sql import SparkSession
from pyspark.sql.functions import (
    col, lit, current_timestamp, to_date, from_unixtime,
    year, month, dayofmonth, weekofyear, quarter, dayofweek,
    split, explode, trim, row_number, coalesce, lower, substring, udf
)
from pyspark.sql.window import Window
from pyspark.sql.types import StringType
import sys
from pathlib import Path
import unicodedata

sys.path.append(str(Path(__file__).parent.parent))
from etl.config import config

def normalize_string(s):
    """Normalise les chaînes : supprime accents, caractères spéciaux, espaces multiples"""
    if s is None or s == '':
        return s
    s = unicodedata.normalize('NFD', s)
    s = ''.join(c for c in s if unicodedata.category(c) != 'Mn')
    s = ' '.join(s.split())
    return s

normalize_udf = udf(normalize_string, StringType())

def create_spark_session():
    return SparkSession.builder \
        .appName("OpenFoodFacts-Silver-to-Gold") \
        .master(config.SPARK_MASTER) \
        .config("spark.driver.memory", config.SPARK_DRIVER_MEMORY) \
        .config("spark.executor.memory", config.SPARK_EXECUTOR_MEMORY) \
        .config("spark.jars.packages", "mysql:mysql-connector-java:8.0.33") \
        .config("spark.sql.shuffle.partitions", "8") \
        .getOrCreate()

def load_silver_data(spark: SparkSession):
    print("📖 Chargement des données Silver...")
    silver_path = str(config.DATA_DIR / "silver" / "products")
    df = spark.read.parquet(silver_path)
    print(f"✅ {df.count()} produits chargés")
    return df

def write_to_mysql(df, table_name: str):
    print(f"💾 Écriture dans {table_name}...")
    count = df.count()
    df.coalesce(1).write \
        .format("jdbc") \
        .option("url", config.jdbc_url) \
        .option("dbtable", table_name) \
        .option("user", config.DB_USER) \
        .option("password", config.DB_PASSWORD) \
        .option("driver", "com.mysql.cj.jdbc.Driver") \
        .option("batchsize", "1000") \
        .mode("append") \
        .save()
    print(f"✅ {count} lignes écrites")

def populate_dim_time(spark: SparkSession, df):
    print("\n🕐 Remplissage de dim_time...")
    df_dates = df.filter(col('last_modified_t').isNotNull()) \
        .select(from_unixtime(col('last_modified_t')).alias('datetime')) \
        .select(to_date(col('datetime')).alias('date')) \
        .distinct()
    
    df_time = df_dates.select(
        col('date'),
        year(col('date')).cast('smallint').alias('year'),
        month(col('date')).cast('tinyint').alias('month'),
        dayofmonth(col('date')).cast('tinyint').alias('day'),
        weekofyear(col('date')).cast('tinyint').alias('week'),
        quarter(col('date')).cast('tinyint').alias('quarter'),
        dayofweek(col('date')).cast('tinyint').alias('day_of_week'),
        lit(None).cast('string').alias('day_name'),
        lit(None).cast('string').alias('month_name'),
        (dayofweek(col('date')).isin([1, 7])).alias('is_weekend')
    ).orderBy('date')
    
    write_to_mysql(df_time, "dim_time")
    return df_time.withColumn('time_sk', row_number().over(Window.orderBy('date')))

def populate_dim_brand(spark: SparkSession, df):
    print("\n🏢 Remplissage de dim_brand...")
    df_brands = df.filter(col('brands').isNotNull()) \
        .select(explode(split(col('brands'), ',')).alias('brand_name')) \
        .select(trim(col('brand_name')).alias('brand_name')) \
        .filter((col('brand_name') != '') & (col('brand_name').isNotNull()))
    
    df_brands_normalized = df_brands \
        .withColumn('brand_normalized', normalize_udf(lower(col('brand_name')))) \
        .dropDuplicates(['brand_normalized']) \
        .drop('brand_normalized') \
        .orderBy('brand_name')
    
    print(f"  ℹ️  Brands avant dédoublonnage: {df_brands.count()}")
    print(f"  ℹ️  Brands après dédoublonnage: {df_brands_normalized.count()}")
    
    df_brands_final = df_brands_normalized.select(
        col('brand_name'),
        trim(col('brand_name')).alias('brand_clean')
    )
    
    write_to_mysql(df_brands_final, "dim_brand")
    return df_brands_final.withColumn('brand_sk', row_number().over(Window.orderBy('brand_name')))

def populate_dim_category(spark: SparkSession, df):
    print("\n📁 Remplissage de dim_category...")
    df_cats = df.filter(col('categories_tags').isNotNull()) \
        .select(explode(split(col('categories_tags'), ',')).alias('category_code')) \
        .select(trim(col('category_code')).alias('category_code')) \
        .filter((col('category_code') != '') & (col('category_code').isNotNull()))
    
    df_cats_normalized = df_cats \
        .withColumn('cat_normalized', normalize_udf(lower(col('category_code')))) \
        .dropDuplicates(['cat_normalized']) \
        .drop('cat_normalized') \
        .orderBy('category_code')
    
    df_cats_final = df_cats_normalized.select(
        col('category_code'),
        col('category_code').alias('category_name_fr'),
        lit(None).cast('string').alias('category_name_en'),
        lit(1).cast('tinyint').alias('level'),
        lit(None).cast('int').alias('parent_category_sk'),
        col('category_code').alias('full_path')
    )
    
    write_to_mysql(df_cats_final, "dim_category")
    return df_cats_final.withColumn('category_sk', row_number().over(Window.orderBy('category_code')))

def populate_dim_country(spark: SparkSession, df):
    print("\n🌍 Remplissage de dim_country...")
    df_countries = df.filter(col('countries_tags').isNotNull()) \
        .select(explode(split(col('countries_tags'), ',')).alias('country_code')) \
        .select(trim(col('country_code')).alias('country_code')) \
        .filter((col('country_code') != '') & (col('country_code').isNotNull()))
    
    df_countries = df_countries.withColumn(
        'country_code_clean',
        trim(split(col('country_code'), ':').getItem(1))
    )
    
    df_countries_normalized = df_countries.select(
        coalesce(col('country_code_clean'), col('country_code')).alias('country_code'),
        coalesce(col('country_code_clean'), col('country_code')).alias('country_name_fr'),
        coalesce(col('country_code_clean'), col('country_code')).alias('country_name_en')
    )
    
    # TRONQUE à 10 caractères + normalisation
    df_countries_final = df_countries_normalized \
        .withColumn('country_code', substring(col('country_code'), 1, 10)) \
        .withColumn('country_name_fr', substring(col('country_name_fr'), 1, 100)) \
        .withColumn('country_name_en', substring(col('country_name_en'), 1, 100)) \
        .withColumn('country_normalized', normalize_udf(lower(col('country_code')))) \
        .dropDuplicates(['country_normalized']) \
        .drop('country_normalized') \
        .orderBy('country_code')
    
    write_to_mysql(df_countries_final, "dim_country")
    return df_countries_final.withColumn('country_sk', row_number().over(Window.orderBy('country_code')))

def populate_dim_product(spark: SparkSession, df, df_brands, df_cats):
    print("\n📦 Remplissage de dim_product...")
    df_with_brand = df.withColumn(
        'first_brand',
        trim(split(col('brands'), ',').getItem(0))
    )
    
    df_with_brand_sk = df_with_brand.join(
        df_brands.select(col('brand_sk'), col('brand_name').alias('first_brand')),
        on='first_brand',
        how='left'
    )
    
    df_with_cat = df_with_brand_sk.withColumn(
        'first_category',
        trim(split(col('categories_tags'), ',').getItem(0))
    )
    
    df_with_cat_sk = df_with_cat.join(
        df_cats.select(col('category_sk'), col('category_code').alias('first_category')),
        on='first_category',
        how='left'
    )
    
    df_product = df_with_cat_sk.select(
        col('code'),
        col('product_name'),
        lit(None).cast('string').alias('product_name_fr'),
        lit(None).cast('string').alias('product_name_en'),
        col('brand_sk'),
        col('category_sk').alias('primary_category_sk'),
        col('countries_tags'),
        col('packaging'),
        col('quantity'),
        coalesce(
            from_unixtime(col('last_modified_t')).cast('timestamp'),
            current_timestamp()
        ).alias('effective_from'),
        lit(None).cast('timestamp').alias('effective_to'),
        lit(True).alias('is_current'),
        col('row_hash')
    ).orderBy('code')
    
    write_to_mysql(df_product, "dim_product")
    return df_product.withColumn('product_sk', row_number().over(Window.orderBy('code')))

def populate_fact_nutrition(spark: SparkSession, df, df_product, df_time):
    print("\n📊 Remplissage de fact_nutrition_snapshot...")
    df_with_product = df.join(
        df_product.select('product_sk', 'code'),
        on='code',
        how='inner'
    )
    
    df_with_time = df_with_product \
        .withColumn('date', to_date(from_unixtime(coalesce(col('last_modified_t'), lit(0))))) \
        .join(
            df_time.select('time_sk', 'date'),
            on='date',
            how='left'
        )
    
    df_fact = df_with_time.select(
        col('product_sk'),
        coalesce(col('time_sk'), lit(1)).alias('time_sk'),
        col('energy_kcal_100g'),
        col('energy_kj_100g'),
        col('fat_100g'),
        col('saturated_fat_100g'),
        col('carbohydrates_100g'),
        col('sugars_100g'),
        col('fiber_100g'),
        col('proteins_100g'),
        col('salt_100g'),
        col('sodium_100g'),
        substring(col('nutriscore_grade'), 1, 10).alias('nutriscore_grade'),
        col('nutriscore_score'),
        col('nova_group'),
        lit(None).cast('string').alias('ecoscore_grade'),
        lit(None).cast('int').alias('ecoscore_score'),
        col('completeness_score'),
        col('nb_nutrients_filled'),
        col('has_image'),
        col('has_ingredients'),
        col('quality_issues_json'),
        col('last_modified_t')
    )
    
    write_to_mysql(df_fact, "fact_nutrition_snapshot")
    print(f"✅ {df_fact.count()} faits nutritionnels chargés")

def main():
    print("=" * 70)
    print("ETL SILVER → GOLD - Chargement dans MariaDB")
    print("=" * 70)
    
    spark = create_spark_session()
    
    try:
        df = load_silver_data(spark)
        
        df_time = populate_dim_time(spark, df)
        df_brands = populate_dim_brand(spark, df)
        df_cats = populate_dim_category(spark, df)
        df_countries = populate_dim_country(spark, df)
        df_product = populate_dim_product(spark, df, df_brands, df_cats)
        
        populate_fact_nutrition(spark, df, df_product, df_time)
        
        print("\n" + "=" * 70)
        print("✅ ETL Silver → Gold terminé!")
        print("=" * 70)
        
    except Exception as e:
        print(f"\n❌ ERREUR: {e}")
        import traceback
        traceback.print_exc()
        raise
    finally:
        spark.stop()

if __name__ == "__main__":
    main()
