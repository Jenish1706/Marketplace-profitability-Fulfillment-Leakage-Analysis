-- ============================================================================
-- 01_SCHEMA.SQL: RAW RELATIONAL SCHEMA DEFINITIONS
-- Project: Marketplace Profitability & Fulfillment Leakage Diagnostic
-- Dialect: DuckDB-first analytical SQL with PostgreSQL-portable DDL
-- Description: Defines explicit staging tables, constraints, primary keys, and
--              ingestion commands for the 9 official Olist relational datasets.
-- ============================================================================

-- 1. Orders Core Table
CREATE TABLE IF NOT EXISTS olist_orders (
    order_id VARCHAR PRIMARY KEY,
    customer_id VARCHAR NOT NULL,
    order_status VARCHAR NOT NULL,
    order_purchase_timestamp TIMESTAMP NOT NULL,
    order_approved_at TIMESTAMP,
    order_delivered_carrier_date TIMESTAMP,
    order_delivered_customer_date TIMESTAMP,
    order_estimated_delivery_date TIMESTAMP NOT NULL
);

-- 2. Order Line Items Table (Grain: order_id + order_item_id)
CREATE TABLE IF NOT EXISTS olist_order_items (
    order_id VARCHAR NOT NULL,
    order_item_id INTEGER NOT NULL,
    product_id VARCHAR NOT NULL,
    seller_id VARCHAR NOT NULL,
    shipping_limit_date TIMESTAMP NOT NULL,
    price NUMERIC(10, 2) NOT NULL,
    freight_value NUMERIC(10, 2) NOT NULL,
    PRIMARY KEY (order_id, order_item_id)
);

-- 3. Order Payments Table (Grain: order_id + payment_sequential)
CREATE TABLE IF NOT EXISTS olist_order_payments (
    order_id VARCHAR NOT NULL,
    payment_sequential INTEGER NOT NULL,
    payment_type VARCHAR NOT NULL,
    payment_installments INTEGER NOT NULL,
    payment_value NUMERIC(10, 2) NOT NULL,
    PRIMARY KEY (order_id, payment_sequential)
);

-- 4. Order Reviews Table (Grain: review_id + order_id)
CREATE TABLE IF NOT EXISTS olist_order_reviews (
    review_id VARCHAR NOT NULL,
    order_id VARCHAR NOT NULL,
    review_score INTEGER NOT NULL,
    review_comment_title VARCHAR,
    review_comment_message VARCHAR,
    review_creation_date TIMESTAMP NOT NULL,
    review_answer_timestamp TIMESTAMP NOT NULL
);

-- 5. Products Catalog Table
CREATE TABLE IF NOT EXISTS olist_products (
    product_id VARCHAR PRIMARY KEY,
    product_category_name VARCHAR,
    product_name_lenght INTEGER,
    product_description_lenght INTEGER,
    product_photos_qty INTEGER,
    product_weight_g NUMERIC(10, 2),
    product_length_cm NUMERIC(10, 2),
    product_height_cm NUMERIC(10, 2),
    product_width_cm NUMERIC(10, 2)
);

-- 6. Sellers Directory Table
CREATE TABLE IF NOT EXISTS olist_sellers (
    seller_id VARCHAR PRIMARY KEY,
    seller_zip_code_prefix VARCHAR NOT NULL,
    seller_city VARCHAR NOT NULL,
    seller_state VARCHAR(5) NOT NULL
);

-- 7. Customers Directory Table
CREATE TABLE IF NOT EXISTS olist_customers (
    customer_id VARCHAR PRIMARY KEY,
    customer_unique_id VARCHAR NOT NULL,
    customer_zip_code_prefix VARCHAR NOT NULL,
    customer_city VARCHAR NOT NULL,
    customer_state VARCHAR(5) NOT NULL
);

-- 8. Geolocation Reference Table
CREATE TABLE IF NOT EXISTS olist_geolocation (
    geolocation_zip_code_prefix VARCHAR NOT NULL,
    geolocation_lat DOUBLE PRECISION NOT NULL,
    geolocation_lng DOUBLE PRECISION NOT NULL,
    geolocation_city VARCHAR NOT NULL,
    geolocation_state VARCHAR(5) NOT NULL
);

-- 9. Category Name Translation Table (Portuguese -> English)
CREATE TABLE IF NOT EXISTS product_category_name_translation (
    product_category_name VARCHAR PRIMARY KEY,
    product_category_name_english VARCHAR NOT NULL
);

-- DuckDB Automated CSV Ingestion Commands:
-- COPY olist_orders FROM 'data/raw/olist_orders_dataset.csv' (HEADER, AUTO_DETECT TRUE);
-- COPY olist_order_items FROM 'data/raw/olist_order_items_dataset.csv' (HEADER, AUTO_DETECT TRUE);
-- COPY olist_order_payments FROM 'data/raw/olist_order_payments_dataset.csv' (HEADER, AUTO_DETECT TRUE);
-- COPY olist_order_reviews FROM 'data/raw/olist_order_reviews_dataset.csv' (HEADER, AUTO_DETECT TRUE);
-- COPY olist_products FROM 'data/raw/olist_products_dataset.csv' (HEADER, AUTO_DETECT TRUE);
-- COPY olist_sellers FROM 'data/raw/olist_sellers_dataset.csv' (HEADER, AUTO_DETECT TRUE);
-- COPY olist_customers FROM 'data/raw/olist_customers_dataset.csv' (HEADER, AUTO_DETECT TRUE);
-- COPY olist_geolocation FROM 'data/raw/olist_geolocation_dataset.csv' (HEADER, AUTO_DETECT TRUE);
-- COPY product_category_name_translation FROM 'data/raw/product_category_name_translation.csv' (HEADER, AUTO_DETECT TRUE);
