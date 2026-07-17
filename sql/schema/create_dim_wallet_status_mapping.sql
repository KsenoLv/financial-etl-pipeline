CREATE TABLE IF NOT EXISTS dim_wallet_status_mapping (
    wallet_bank        STRING,
    source_status      STRING,
    normalized_status  STRING
)
USING DELTA;