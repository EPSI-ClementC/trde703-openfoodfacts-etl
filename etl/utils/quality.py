"""
Fonctions de calcul de qualité des données
"""
from pyspark.sql import DataFrame
from pyspark.sql.functions import col, when, count, sum as spark_sum, lit, array, size
import json

def calculate_completeness_score(df: DataFrame) -> DataFrame:
    """
    Calcule un score de complétude (0-1) pour chaque produit
    """
    # Champs importants à vérifier (avec les VRAIS noms du CSV)
    critical_fields = [
        'product_name', 'brands', 'categories_tags',
        'energy_kcal_100g', 'fat_100g', 'carbohydrates_100g',
        'sugars_100g', 'proteins_100g', 'salt_100g'
    ]
    
    # Compte combien de champs sont remplis
    filled_count = lit(0)
    for field in critical_fields:
        if field in df.columns:
            filled_count = filled_count + when(
                (col(field).isNotNull()) & (col(field) != ''),
                1
            ).otherwise(0)
    
    # Score = nb_champs_remplis / total_champs
    total_fields = len(critical_fields)
    
    return df.withColumn(
        'completeness_score',
        (filled_count / total_fields).cast('decimal(3,2)')
    )

def detect_anomalies(df: DataFrame, bounds: dict) -> DataFrame:
    """
    Détecte les anomalies dans les valeurs nutritionnelles
    """
    anomaly_conditions = []
    
    for field, (min_val, max_val) in bounds.items():
        if field in df.columns:
            anomaly = when(
                (col(field).isNotNull()) & 
                ((col(field) < min_val) | (col(field) > max_val)),
                lit(f"{field}_out_of_bounds")
            )
            anomaly_conditions.append(anomaly)
    
    # Crée un array des anomalies détectées
    if anomaly_conditions:
        df = df.withColumn(
            'quality_issues',
            array(*anomaly_conditions)
        )
        
        # Filtre les nulls et convertit en JSON string
        df = df.withColumn(
            'quality_issues_json',
            when(size(col('quality_issues')) > 0, 
                 col('quality_issues').cast('string')
            ).otherwise(lit(None))
        )
    else:
        df = df.withColumn('quality_issues_json', lit(None))
    
    return df

def count_filled_nutrients(df: DataFrame) -> DataFrame:
    """
    Compte le nombre de nutriments renseignés
    """
    nutrient_fields = [
        'energy_kcal_100g', 'fat_100g', 'saturated_fat_100g',
        'carbohydrates_100g', 'sugars_100g', 'fiber_100g',
        'proteins_100g', 'salt_100g', 'sodium_100g'
    ]
    
    filled_count = lit(0)
    for field in nutrient_fields:
        if field in df.columns:
            filled_count = filled_count + when(
                col(field).isNotNull(),
                1
            ).otherwise(0)
    
    return df.withColumn('nb_nutrients_filled', filled_count.cast('tinyint'))

def generate_quality_report(df: DataFrame) -> dict:
    """
    Génère un rapport de qualité global
    """
    total = df.count()
    
    report = {
        'total_products': total,
        'with_name': df.filter(col('product_name').isNotNull()).count(),
        'with_brand': df.filter(col('brands').isNotNull()).count(),
        'with_nutriscore': df.filter(col('nutriscore_grade').isNotNull()).count(),
        'with_categories': df.filter(col('categories_tags').isNotNull()).count(),
        'with_anomalies': df.filter(col('quality_issues_json').isNotNull()).count()
    }
    
    # Moyenne de complétude
    avg_result = df.agg({'completeness_score': 'avg'}).collect()[0][0]
    report['avg_completeness'] = round(float(avg_result) if avg_result else 0, 2)
    
    # Calcul des pourcentages
    for key in ['with_name', 'with_brand', 'with_nutriscore', 'with_categories']:
        report[f'{key}_pct'] = round((report[key] / total) * 100, 2) if total > 0 else 0
    
    return report
