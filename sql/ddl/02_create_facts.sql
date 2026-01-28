-- =====================================================
-- Table de Faits - Nutrition Snapshot
-- =====================================================

USE openfoodfacts_dw;

DROP TABLE IF EXISTS fact_nutrition_snapshot;
CREATE TABLE fact_nutrition_snapshot (
    fact_id BIGINT PRIMARY KEY AUTO_INCREMENT,
    product_sk BIGINT NOT NULL,
    time_sk INT NOT NULL,
    
    -- Mesures nutritionnelles (pour 100g)
    energy_kcal_100g DECIMAL(10,2),
    energy_kj_100g DECIMAL(10,2),
    fat_100g DECIMAL(10,2),
    saturated_fat_100g DECIMAL(10,2),
    carbohydrates_100g DECIMAL(10,2),
    sugars_100g DECIMAL(10,2),
    fiber_100g DECIMAL(10,2),
    proteins_100g DECIMAL(10,2),
    salt_100g DECIMAL(10,2),
    sodium_100g DECIMAL(10,2),
    
    -- Scores et grades
    nutriscore_grade VARCHAR(20),
    nutriscore_score INT,
    nova_group TINYINT,
    ecoscore_grade VARCHAR(20),
    ecoscore_score INT,
    
    -- Métriques de qualité
    completeness_score DECIMAL(3,2) COMMENT '0.00 à 1.00',
    nb_nutrients_filled TINYINT,
    has_image BOOLEAN,
    has_ingredients BOOLEAN,
    
    -- Anomalies (JSON)
    quality_issues_json TEXT,
    
    -- Audit
    last_modified_t BIGINT COMMENT 'Timestamp OpenFoodFacts',
    loaded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    FOREIGN KEY (product_sk) REFERENCES dim_product(product_sk),
    FOREIGN KEY (time_sk) REFERENCES dim_time(time_sk),
    
    INDEX idx_product (product_sk),
    INDEX idx_time (time_sk),
    INDEX idx_nutriscore (nutriscore_grade),
    INDEX idx_nova (nova_group),
    INDEX idx_loaded_at (loaded_at),
    INDEX idx_completeness (completeness_score)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
