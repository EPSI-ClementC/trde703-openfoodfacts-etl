-- =====================================================
-- Dimensions du DataMart OpenFoodFacts
-- =====================================================

USE openfoodfacts_dw;

-- Dimension Temps
DROP TABLE IF EXISTS dim_time;
CREATE TABLE dim_time (
    time_sk INT PRIMARY KEY AUTO_INCREMENT,
    date DATE NOT NULL UNIQUE,
    year SMALLINT NOT NULL,
    month TINYINT NOT NULL,
    day TINYINT NOT NULL,
    week TINYINT NOT NULL,
    quarter TINYINT NOT NULL,
    day_of_week TINYINT NOT NULL,
    day_name VARCHAR(10),
    month_name VARCHAR(10),
    is_weekend BOOLEAN,
    INDEX idx_date (date),
    INDEX idx_year_month (year, month)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Dimension Marque
DROP TABLE IF EXISTS dim_brand;
CREATE TABLE dim_brand (
    brand_sk INT PRIMARY KEY AUTO_INCREMENT,
    brand_name VARCHAR(255) NOT NULL,
    brand_clean VARCHAR(255),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE KEY uk_brand (brand_name),
    INDEX idx_brand_clean (brand_clean)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Dimension Catégorie (hiérarchique)
DROP TABLE IF EXISTS dim_category;
CREATE TABLE dim_category (
    category_sk INT PRIMARY KEY AUTO_INCREMENT,
    category_code VARCHAR(255) NOT NULL,
    category_name_fr VARCHAR(255),
    category_name_en VARCHAR(255),
    level TINYINT DEFAULT 1,
    parent_category_sk INT,
    full_path VARCHAR(500),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE KEY uk_category_code (category_code),
    FOREIGN KEY (parent_category_sk) REFERENCES dim_category(category_sk),
    INDEX idx_level (level),
    INDEX idx_parent (parent_category_sk)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Dimension Pays
DROP TABLE IF EXISTS dim_country;
CREATE TABLE dim_country (
    country_sk INT PRIMARY KEY AUTO_INCREMENT,
    country_code VARCHAR(10) NOT NULL,
    country_name_fr VARCHAR(100),
    country_name_en VARCHAR(100),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE KEY uk_country_code (country_code),
    INDEX idx_country_name_fr (country_name_fr)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Dimension Produit (SCD Type 2)
DROP TABLE IF EXISTS dim_product;
CREATE TABLE dim_product (
    product_sk BIGINT PRIMARY KEY AUTO_INCREMENT,
    code VARCHAR(50) NOT NULL COMMENT 'Code-barres EAN',
    product_name VARCHAR(500),
    product_name_fr VARCHAR(500),
    product_name_en VARCHAR(500),
    brand_sk INT,
    primary_category_sk INT,
    countries_tags TEXT COMMENT 'JSON array des pays',
    packaging TEXT,
    quantity VARCHAR(100),
    effective_from TIMESTAMP NOT NULL,
    effective_to TIMESTAMP NULL DEFAULT NULL,
    is_current BOOLEAN DEFAULT TRUE,
    row_hash VARCHAR(64) COMMENT 'Hash MD5 pour détecter changements',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    FOREIGN KEY (brand_sk) REFERENCES dim_brand(brand_sk),
    FOREIGN KEY (primary_category_sk) REFERENCES dim_category(category_sk),
    INDEX idx_code (code),
    INDEX idx_code_current (code, is_current),
    INDEX idx_brand (brand_sk),
    INDEX idx_category (primary_category_sk),
    INDEX idx_effective (effective_from, effective_to)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
