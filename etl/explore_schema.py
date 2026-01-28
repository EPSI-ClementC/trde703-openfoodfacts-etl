#!/usr/bin/env python3
"""
Script d'exploration du schéma CSV OpenFoodFacts
"""
from pyspark.sql import SparkSession
import sys
from pathlib import Path

sys.path.append(str(Path(__file__).parent.parent))
from etl.config import config

def explore_schema():
    spark = SparkSession.builder \
        .appName("Schema-Explorer") \
        .master("local[2]") \
        .getOrCreate()
    
    print("🔍 Exploration du schéma OpenFoodFacts CSV\n")
    
    df = spark.read \
        .option("header", "true") \
        .option("sep", "\t") \
        .option("inferSchema", "false") \
        .csv(str(config.OFF_SAMPLE_FILE))
    
    print(f"📊 Total colonnes: {len(df.columns)}\n")
    
    # Groupe par catégorie
    categories = {
        'Identifiants': ['code', 'url', 'creator', 'created', 'modified'],
        'Noms': ['product_name', 'abbreviated', 'generic_name'],
        'Marque/Catégorie': ['brands', 'categories', 'origins', 'manufacturing'],
        'Pays': ['countries', 'purchase'],
        'Packaging': ['packaging', 'quantity'],
        'Energie': ['energy', 'kcal', 'kj'],
        'Macros': ['fat', 'carbohydrate', 'sugar', 'protein', 'fiber', 'salt', 'sodium'],
        'Scores': ['nutriscore', 'nova', 'ecoscore'],
        'Autres': ['image', 'ingredients', 'additives', 'allergens', 'traces']
    }
    
    print("=" * 80)
    print("COLONNES PAR CATÉGORIE")
    print("=" * 80)
    
    for category, keywords in categories.items():
        print(f"\n📁 {category}:")
        matching = [col for col in df.columns if any(kw.lower() in col.lower() for kw in keywords)]
        for col in sorted(matching)[:15]:  # Limite à 15 par catégorie
            print(f"  - {col}")
    
    # Colonnes nutriments 100g
    print("\n" + "=" * 80)
    print("🥗 NUTRIMENTS (100g)")
    print("=" * 80)
    nutrients_100g = [col for col in df.columns if '_100g' in col]
    for col in sorted(nutrients_100g)[:30]:
        print(f"  - {col}")
    
    # Affichage d'un échantillon de données
    print("\n" + "=" * 80)
    print("📋 ÉCHANTILLON (5 premières lignes)")
    print("=" * 80)
    
    key_columns = [
        'code', 'product_name', 'brands', 
        'categories_tags', 'countries_tags',
        'nutriscore_grade', 'nova_group',
        'energy-kcal_100g', 'fat_100g', 'sugars_100g',
        'last_modified_t'
    ]
    
    available_cols = [col for col in key_columns if col in df.columns]
    df.select(available_cols).show(5, truncate=50)
    
    spark.stop()

if __name__ == "__main__":
    explore_schema()
