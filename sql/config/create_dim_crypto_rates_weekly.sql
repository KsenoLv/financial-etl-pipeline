CREATE TABLE IF NOT EXISTS dim_crypto_rates_weekly (
    period_start        DATE,
    period_end          DATE,
    target_time         TIMESTAMP,
    rate_time           TIMESTAMP,
    currency            STRING,
    normalized_currency STRING,
    rate                DOUBLE,
    source              STRING,
    created_at          TIMESTAMP
)
USING DELTA;