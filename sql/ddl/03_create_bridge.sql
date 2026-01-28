-- =====================================================
-- Bridge Table - Produit ↔ Catégories (N-N)
-- =====================================================

USE openfoodfacts_dw;

DROP TABLE IF EXISTS bridge_product_category;
CREATE TABLE bridge_product_category (
    product_sk BIGINT NOT NULL,
    category_sk INT NOT NULL,
    is_primary BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    PRIMARY KEY (product_sk, category_sk),
    FOREIGN KEY (product_sk) REFERENCES dim_product(product_sk),
    FOREIGN KEY (category_sk) REFERENCES dim_category(category_sk),
    
    INDEX idx_product (product_sk),
    INDEX idx_category (category_sk),
    INDEX idx_primary (is_primary)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
