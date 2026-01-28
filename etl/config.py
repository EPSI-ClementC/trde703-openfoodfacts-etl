"""
Configuration centrale du projet ETL
"""
import os
from pathlib import Path
from dotenv import load_dotenv

# Charge les variables d'environnement
load_dotenv()

class Config:
    # Paths
    PROJECT_ROOT = Path(__file__).parent.parent
    DATA_DIR = PROJECT_ROOT / "data"
    SAMPLE_DIR = DATA_DIR / "sample"
    LOGS_DIR = PROJECT_ROOT / "logs"
    
    # Database
    DB_HOST = os.getenv("DB_HOST", "localhost")
    DB_PORT = int(os.getenv("DB_PORT", 3306))
    DB_NAME = os.getenv("DB_NAME", "openfoodfacts_dw")
    DB_USER = os.getenv("DB_USER", "etl_user")
    DB_PASSWORD = os.getenv("DB_PASSWORD")
    
    @property
    def jdbc_url(self):
        return f"jdbc:mysql://{self.DB_HOST}:{self.DB_PORT}/{self.DB_NAME}?useSSL=false&allowPublicKeyRetrieval=true"
    
    @property
    def jdbc_properties(self):
        return {
            "user": self.DB_USER,
            "password": self.DB_PASSWORD,
            "driver": "com.mysql.cj.jdbc.Driver"
        }
    
    # Spark
    SPARK_MASTER = os.getenv("SPARK_MASTER", "local[4]")
    SPARK_DRIVER_MEMORY = os.getenv("SPARK_DRIVER_MEMORY", "4g")
    SPARK_EXECUTOR_MEMORY = os.getenv("SPARK_EXECUTOR_MEMORY", "4g")
    
    # OpenFoodFacts
    OFF_SAMPLE_FILE = SAMPLE_DIR / "openfoodfacts-fr-sample-30000.csv"
    OFF_FULL_FILE = SAMPLE_DIR / "openfoodfacts-fr.csv"
    
    # Quality thresholds
    NUTRIENT_BOUNDS = {
        'energy_kcal_100g': (0, 900),
        'fat_100g': (0, 100),
        'saturated_fat_100g': (0, 100),
        'carbohydrates_100g': (0, 100),
        'sugars_100g': (0, 100),
        'fiber_100g': (0, 100),
        'proteins_100g': (0, 100),
        'salt_100g': (0, 100),
        'sodium_100g': (0, 40)
    }

config = Config()
