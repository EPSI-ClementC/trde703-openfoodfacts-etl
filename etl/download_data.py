#!/usr/bin/env python3
"""
Script de téléchargement des données OpenFoodFacts - Version FR optimisée
"""
import requests
import gzip
import shutil
import os
from pathlib import Path

def download_french_data():
    """
    Télécharge uniquement les produits français (beaucoup plus léger)
    """
    print("🇫🇷 Téléchargement des produits français uniquement...")
    
    # URL du dataset français complet
    url = "https://fr.openfoodfacts.org/data/fr.openfoodfacts.org.products.csv"
    
    output_dir = Path("data/sample")
    output_dir.mkdir(parents=True, exist_ok=True)
    
    output_file = output_dir / "openfoodfacts-fr.csv"
    
    try:
        print(f"📥 Téléchargement depuis: {url}")
        print("⏳ Cela peut prendre 2-3 minutes...")
        
        response = requests.get(url, stream=True)
        response.raise_for_status()
        
        # Téléchargement avec progress
        total_size = int(response.headers.get('content-length', 0))
        block_size = 8192
        downloaded = 0
        
        with open(output_file, 'wb') as f:
            for chunk in response.iter_content(chunk_size=block_size):
                if chunk:
                    f.write(chunk)
                    downloaded += len(chunk)
                    if total_size > 0:
                        percent = (downloaded / total_size) * 100
                        print(f"\r  Progression: {percent:.1f}%", end='', flush=True)
        
        print(f"\n✅ Fichier téléchargé: {output_file}")
        
        # Stats du fichier
        file_size_mb = output_file.stat().st_size / (1024 * 1024)
        print(f"📊 Taille: {file_size_mb:.1f} MB")
        
        # Compte les lignes
        print("📈 Comptage des produits...")
        with open(output_file, 'r', encoding='utf-8') as f:
            line_count = sum(1 for _ in f) - 1  # -1 pour l'en-tête
        
        print(f"✅ Total produits français: {line_count:,}")
        
        return output_file
        
    except Exception as e:
        print(f"❌ Erreur: {e}")
        return None

def create_sample(input_file, sample_size=30000):
    """
    Crée un sample encore plus petit pour les tests rapides
    """
    print(f"\n🎯 Création d'un sample de {sample_size:,} produits pour le dev...")
    
    input_path = Path(input_file)
    output_file = input_path.parent / f"openfoodfacts-fr-sample-{sample_size}.csv"
    
    try:
        with open(input_path, 'r', encoding='utf-8') as f_in:
            with open(output_file, 'w', encoding='utf-8') as f_out:
                # Copie l'en-tête
                header = f_in.readline()
                f_out.write(header)
                
                # Copie N lignes
                for i, line in enumerate(f_in):
                    if i >= sample_size:
                        break
                    f_out.write(line)
                    
                    if (i + 1) % 10000 == 0:
                        print(f"  ✓ {i + 1:,} produits copiés...")
        
        file_size_mb = output_file.stat().st_size / (1024 * 1024)
        print(f"✅ Sample créé: {output_file}")
        print(f"📊 Taille: {file_size_mb:.1f} MB")
        
        return output_file
        
    except Exception as e:
        print(f"❌ Erreur: {e}")
        return None

if __name__ == "__main__":
    print("=" * 60)
    print("OpenFoodFacts - Téléchargement données françaises")
    print("=" * 60)
    
    # Télécharge le dataset français complet
    french_file = download_french_data()
    
    if french_file:
        # Crée un sample de 30k pour dev rapide
        sample_file = create_sample(french_file, sample_size=30000)
        
        print("\n" + "=" * 60)
        print("✅ Téléchargement terminé!")
        print("=" * 60)
        print(f"\n📁 Fichiers disponibles:")
        print(f"  - Complet FR: {french_file}")
        print(f"  - Sample dev: {sample_file}")
        print(f"\n💡 Recommandation: Utilise le sample pour développer,")
        print(f"   puis le fichier complet pour la version finale.")
