-- ============================================================================
-- AMAZON REDSHIFT COMPLEX ETL WORKFLOW
-- ============================================================================
-- This script handles Bronze ingestion via COPY, Silver transformations, 
-- and Gold dimensional modeling (including SCD Type 2).
-- Parameters surrounded by {{ }} will be replaced by the Python executor.
-- ============================================================================

-- Set session timezone to UTC for consistency
SET timezone TO 'UTC';

-- ============================================================================
-- STEP 1: BRONZE LAYER - Load raw data from S3 into Staging tables
-- ============================================================================
-- We truncate staging tables before loading to ensure a fresh batch process.

TRUNCATE TABLE {{schemas.bronze}}.{{st_orders}};  --- scenario 1 -- dyanmic schema || table  
COPY {{schemas.bronze}}.{{st_orders}} 
FROM '{{aws.s3_base_path}}/transactions/orders/' 
IAM_ROLE '{{aws.iam_role_arn}}' FORMAT AS PARQUET;

TRUNCATE TABLE {{schemas.bronze}}.stg_order_items;
COPY {{schemas.bronze}}.stg_order_items 
FROM '{{aws.s3_base_path}}/transactions/order_items/' 
IAM_ROLE '{{aws.iam_role_arn}}' FORMAT AS PARQUET;

-- Load messy CSV customers
TRUNCATE TABLE {{schemas.bronze}}.stg_customers_raw;
COPY {{schemas.bronze}}.stg_customers_raw
FROM '{{aws.s3_base_path}}/crm/customers_dump.csv' 
IAM_ROLE '{{aws.iam_role_arn}}' CSV DELIMITER ',' IGNOREHEADER 1;

-- Load nested JSON products (Redshift 'auto' flattens top level)
TRUNCATE TABLE {{schemas.bronze}}.stg_products_nested;
COPY {{schemas.bronze}}.stg_products_nested
FROM '{{aws.s3_base_path}}/pim/products_nested.json' 
IAM_ROLE '{{aws.iam_role_arn}}' JSON 'auto';

-- Load Clickstream logs (Gzipped JSON)
TRUNCATE TABLE {{schemas.bronze}}.stg_web_clickstream;
COPY {{schemas.bronze}}.stg_web_clickstream
FROM '{{aws.s3_base_path}}/logs/web_server_logs.json.gz' 
IAM_ROLE '{{aws.iam_role_arn}}' JSON 'auto' GZIP;

-- (Shipping manifest XML loading omitted for brevity as Redshift lacks native easy XML parsing 
-- without external libraries/UDFs, assume pre-parsed to CSV for this example)


-- ============================================================================
-- STEP 2: SILVER LAYER - Clean, Deduplicate, Conform
-- ============================================================================

-- --- 2a. Silver Customers (Cleaning and Deduplication) ---
TRUNCATE TABLE {{schemas.silver}}.customers_master;

INSERT INTO {{schemas.silver}}.customers_master (customer_id, email, cleaned_phone, city, country, ingestion_dt)
WITH ranked_customers AS (
    -- Deduplicate by email, taking the most recently updated record if duplicates exist
    SELECT 
        customer_id,
        email,
        -- Basic cleaning of phone and address splitting (simplified for SQL)
        COALESCE(NULLIF(phone, ''), 'N/A') AS cleaned_phone,
        SPLIT_PART(full_address_messy, ',', 2) AS city_extract,
        SPLIT_PART(full_address_messy, ',', 3) AS country_extract,
        ROW_NUMBER() OVER (PARTITION BY email ORDER BY updated_at DESC) as rn
    FROM {{schemas.bronze}}.stg_customers_raw
)
SELECT 
    CAST(customer_id AS INT), 
    email, 
    cleaned_phone, 
    TRIM(city_extract), 
    TRIM(country_extract), 
    GETDATE() -- Redshift UTC timestamp
FROM ranked_customers
WHERE rn = 1;


-- --- 2b. Silver Products (Standardizing Categories) ---
TRUNCATE TABLE {{schemas.silver}}.products_catalog;

INSERT INTO {{schemas.silver}}.products_catalog (product_id, product_name, standardize_cat, unit_price, ingestion_dt)
SELECT DISTINCT
    product_id,
    product_name,
    -- Standardize category names dynamically
    CASE 
        WHEN category IN ('Cell Phones', 'Mobile Devs') THEN 'Electronics - Mobile'
        WHEN category IS NULL THEN 'Uncategorized'
        ELSE category 
    END AS standardize_cat,
    CAST(json_extract_path_text(specs, 'price') AS DECIMAL(10,2)) as unit_price, -- Extracting from nested JSON string if needed
    GETDATE()
FROM {{schemas.bronze}}.stg_products_nested;


-- --- 2c. Silver Orders Enriched (The Great Join) ---
TRUNCATE TABLE {{schemas.silver}}.orders_enriched;

INSERT INTO {{schemas.silver}}.orders_enriched
SELECT 
    o.order_id,
    o.customer_id,
    oi.product_id,
    CAST(o.order_date AS DATE),
    oi.quantity,
    oi.unit_price,
    (oi.quantity * oi.unit_price) AS gross_sales_line_total,
    GETDATE() AS ingestion_dt
FROM {{schemas.bronze}}.{{st_orders}} o   ------ scenario 2 - table alias
LEFT JOIN {{schemas.bronze}}.stg_order_items oi ON o.order_id = oi.order_id
-- Business Logic: Filter out internal QA test accounts
WHERE o.customer_id > 100;


-- --- 2d. Silver Web Sessions (Complex Windowing/Sessionization) ---
-- Redshift is excellent at window functions for this task.
TRUNCATE TABLE {{schemas.silver}}.user_sessions;

INSERT INTO {{schemas.silver}}.user_sessions
WITH lagged_clicks AS (
    SELECT 
        cookie_id,
        timestamp_utc,
        page_url,
        -- Get timestamp of previous click by same cookie
        LAG(timestamp_utc, 1) OVER (PARTITION BY cookie_id ORDER BY timestamp_utc) AS prev_timestamp
    FROM {{schemas.bronze}}.stg_web_clickstream
),
session_flags AS (
    SELECT 
        *,
        -- Flag as new session if time difference exceeds configured minutes
        CASE 
            WHEN DATEDIFF(minute, prev_timestamp, timestamp_utc) >= {{params.session_timeout_minutes}} THEN 1 
            WHEN prev_timestamp IS NULL THEN 1 -- First event is always a new session
            ELSE 0 
        END AS is_new_session
    FROM lagged_clicks
),
session_grouping AS (
    SELECT 
        *,
        -- Create unique session ID by running sum of flags
        SUM(is_new_session) OVER (PARTITION BY cookie_id ORDER BY timestamp_utc ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW) AS session_seq_id
    FROM session_flags
)
-- Final aggregation by session
SELECT 
    cookie_id || '-' || CAST(session_seq_id AS VARCHAR) AS unique_session_id,
    cookie_id,
    MIN(timestamp_utc) AS session_start_utc,
    MAX(timestamp_utc) AS session_end_utc,
    COUNT(DISTINCT page_url) AS total_pages_viewed,
    DATEDIFF(second, MIN(timestamp_utc), MAX(timestamp_utc)) AS session_duration_sec,
    GETDATE()
FROM session_grouping
GROUP BY 1, 2;


-- ============================================================================
-- STEP 3: GOLD LAYER - Dimensional Modeling & Aggregation
-- ============================================================================

-- --- 3a. Dim Product (SCD Type 1 - Simple Overwrite/Upsert) ---
-- We use a staging table approach for efficient Redshift upserts.
BEGIN TRANSACTION;

CREATE TEMP TABLE tmp_dim_product (LIKE {{schemas.gold}}.dim_product);

INSERT INTO tmp_dim_product (product_sk, product_id, product_name, category, current_price)
SELECT 
    -- Generate surrogate key based on natural key ordering
    ROW_NUMBER() OVER (ORDER BY product_id) + (SELECT COALESCE(MAX(product_sk),0) FROM {{schemas.gold}}.dim_product),
    product_id,
    product_name,
    standardize_cat,
    unit_price
FROM {{schemas.silver}}.products_catalog
-- Only insert products that don't exist in dim yet (Simplified SCD1 for brevity)
WHERE product_id NOT IN (SELECT product_id FROM {{schemas.gold}}.dim_product);

INSERT INTO {{schemas.gold}}.dim_product SELECT * FROM tmp_dim_product;
DROP TABLE tmp_dim_product;

END TRANSACTION;


-- --- 3b. Dim Customer (SCD Type 2 - Historical Tracking) ---
-- This is the most complex part in SQL. We need to expire old records and insert new ones.
BEGIN TRANSACTION;

-- 1. Identify records that have changed in Silver compared to current Gold active records
CREATE TEMP TABLE tmp_changed_customers AS
SELECT 
    s.customer_id, s.email, s.city, s.country, -- New values
    d.customer_sk AS existing_sk_to_expire      -- Old SK
FROM {{schemas.silver}}.customers_master s
INNER JOIN {{schemas.gold}}.dim_customer_scd2 d 
    ON s.customer_id = d.customer_id 
    AND d.is_current = TRUE
WHERE 
    -- Check if critical attributes changed
    s.email <> d.email OR s.city <> d.city OR s.country <> d.country;

-- 2. Expire the old records in Gold
UPDATE {{schemas.gold}}.dim_customer_scd2
SET is_current = FALSE, 
    end_date = GETDATE()::DATE - 1 -- Set end date to yesterday
FROM tmp_changed_customers tmp
WHERE {{schemas.gold}}.dim_customer_scd2.customer_sk = tmp.existing_sk_to_expire;

-- 3. Identify net-new customers who have never been in Gold
CREATE TEMP TABLE tmp_new_customers AS
SELECT s.*
FROM {{schemas.silver}}.customers_master s
LEFT JOIN {{schemas.gold}}.dim_customer_scd2 d ON s.customer_id = d.customer_id
WHERE d.customer_id IS NULL;

-- 4. Insert new versions of changed customers AND net-new customers
INSERT INTO {{schemas.gold}}.dim_customer_scd2 (customer_sk, customer_id, email, city, country, start_date, end_date, is_current)
WITH all_new_records AS (
    SELECT customer_id, email, city, country FROM tmp_changed_customers
    UNION ALL
    SELECT customer_id, email, city, country FROM tmp_new_customers
)
SELECT 
    -- Generate new surrogate keys
    ROW_NUMBER() OVER (ORDER BY customer_id) + (SELECT COALESCE(MAX(customer_sk),0) FROM {{schemas.gold}}.dim_customer_scd2),
    customer_id, email, city, country,
    GETDATE()::DATE AS start_date,
    '{{params.future_date}}'::DATE AS end_date,
    TRUE AS is_current
FROM all_new_records;

DROP TABLE tmp_changed_customers;
DROP TABLE tmp_new_customers;
END TRANSACTION;


-- --- 3c. Fact Sales Transactions (Star Schema Join) ---
BEGIN TRANSACTION;
-- Truncating Fact for daily full reload pattern (incremental is harder but possible)
TRUNCATE TABLE {{schemas.gold}}.fact_sales_transactions;

INSERT INTO {{schemas.gold}}.fact_sales_transactions (order_id, date_key, customer_sk, product_sk, quantity, sales_amount)
SELECT 
    oe.order_id,
    -- Create integer date key (e.g., 20231027)
    CAST(TO_CHAR(oe.order_date, 'YYYYMMDD') AS INT) AS date_key,
    -- Lookup active customer surrogate key
    COALESCE(dc.customer_sk, -1) AS customer_sk, 
    -- Lookup product surrogate key
    COALESCE(dp.product_sk, -1) AS product_sk,
    oe.quantity,
    oe.gross_sales_line_total
FROM {{schemas.silver}}.orders_enriched oe
-- Join to SCD2 dimension filtering for currently active records
LEFT JOIN {{schemas.gold}}.dim_customer_scd2 dc 
    ON oe.customer_id = dc.customer_id AND dc.is_current = TRUE
-- Join to SCD1 dimension
LEFT JOIN {{schemas.gold}}.dim_product dp 
    ON oe.product_id = dp.product_id;

END TRANSACTION;


-- --- 3d. Aggregation: Daily Regional Performance ---
TRUNCATE TABLE {{schemas.gold}}.agg_regional_daily;

INSERT INTO {{schemas.gold}}.agg_regional_daily
SELECT 
    order_date,
    -- Join back to customer silver/gold to get country if needed, assuming it's in enriched for now
    'USA' as country_code_simulated, 
    COUNT(DISTINCT order_id) as total_orders,
    SUM(gross_sales_line_total) as total_sales
FROM {{schemas.silver}}.orders_enriched
GROUP BY 1, 2;

-- (Customer 360 wide table creation omitted for length, but follows similar INSERT INTO ... SELECT joins)

VACUUM;
ANALYZE;