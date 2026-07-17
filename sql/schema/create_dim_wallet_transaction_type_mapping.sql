CREATE TABLE IF NOT EXISTS dim_wallet_transaction_type_mapping (
    wallet_bank       STRING,
    source_reference  STRING,
    transaction_type  STRING
)
USING DELTA;