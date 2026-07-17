"""Load pre-normalized transaction files into PostgreSQL.

This pipeline expects CSV or Excel files that already follow the repository's
normalized transaction schema. It performs lightweight type cleaning, adds
ingestion metadata, and bulk-inserts records into PostgreSQL.
"""

import os
import json
import uuid
import hashlib
import logging
from datetime import datetime, timezone
from pathlib import Path
import pandas as pd
import psycopg2
from psycopg2.extras import execute_values
from dotenv import load_dotenv

PROJECT_ROOT = Path(__file__).resolve().parents[2]

DATA_DIR = Path(
    os.getenv("NORMALIZED_DATA_DIR", PROJECT_ROOT / "data" / "normalized")
)
TARGET_SCHEMA = os.getenv("POSTGRES_TARGET_SCHEMA", "public")
TARGET_TABLE = os.getenv("POSTGRES_TARGET_TABLE", "normalized_transactions")
TRUNCATE_BEFORE_LOAD = os.getenv("TRUNCATE_BEFORE_LOAD", "false").lower() == "true"
INSERT_PAGE_SIZE = int(os.getenv("INSERT_PAGE_SIZE", "1000"))

# Load variables from the default .env file or from DB_ENV_FILE when supplied.
env_file = os.getenv("DB_ENV_FILE")
load_dotenv(env_file if env_file else None)

DB_CONFIG = {
    "host": os.getenv("DB_HOST"),
    "port": int(os.getenv("DB_PORT", "5432")),
    "dbname": os.getenv("DB_NAME"),
    "user": os.getenv("DB_USER"),
    "password": os.getenv("DB_PASSWORD"),
    "sslmode": os.getenv("DB_SSLMODE", "prefer"),
}

logging.basicConfig(
    level=os.getenv("LOG_LEVEL", "INFO"),
    format="%(asctime)s | %(levelname)s | %(message)s",
)
logger = logging.getLogger(__name__)


COLUMNS = [
    "company", "wallet_bank", "date", "depositdate", "withdrawaldate", "norm_date",
    "pay_id", "status", "amount", "currency", "commission", "commissioncurrency",
    "exchangerate", "finalamount", "project", "notes", "reference", "paymentmethod",
    "settlement", "settlementcomission", "topups", "topupscomission", "affilates",
    "affilatescommission", "chargebacksrefunds", "chargebacksrefundscommission",
    "expenses", "expensescommission", "notes222", "notes333", "notes444",
    "path", "ingestion_id", "ingestion_time", "raw_hash"
]

SOURCE_COLUMNS = [
    "date", "depositdate", "withdrawaldate", "pay_id", "status", "amount", "currency",
    "commission", "commissioncurrency", "exchangerate", "finalamount", "project",
    "notes", "reference", "paymentmethod", "settlement", "settlementcomission",
    "topups", "topupscomission", "affilates", "affilatescommission",
    "chargebacksrefunds", "chargebacksrefundscommission", "expenses",
    "expensescommission", "notes222", "notes333", "notes444"
]

DATE_COLUMNS = ["date", "depositdate", "withdrawaldate"]

NULL_VALUES = {
    "", "nan", "NaN", "NAN", "None", "none", "NULL", "null",
    "no_data", "No_data", "NO_DATA"
}

def clean_cell_value(x):
    if pd.isna(x):
        return None

    x = str(x).strip()

    while len(x) > 0 and x[0] in ['"', "'", "`", " ", "\t", "\n", "\r"]:
        x = x[1:].strip()

    while len(x) > 0 and x[-1] in ['"', "'", "`", " ", "\t", "\n", "\r"]:
        x = x[:-1].strip()

    if x in NULL_VALUES:
        return None

    return x

def read_file(path):
    ext = Path(path).suffix.lower()

    if ext == ".csv":
        encodings = ["utf-8-sig", "utf-8", "cp1251", "latin1"]

        for enc in encodings:
            try:
                return pd.read_csv(
                    path,
                    dtype=str,
                    sep=",",
                    encoding=enc,
                    index_col=False
                )
            except Exception:
                pass

        raise Exception(f"Не удалось прочитать CSV: {path}")

    if ext in [".xlsx", ".xls"]:
        return pd.read_excel(path, dtype=str)

    return None

def normalize_date_series(series):
    formats = [
        "%d %b %y %H:%M",
        "%d %b %Y. %H:%M",
        "%d/%m/%Y %H:%M:%S",
        "%d/%m/%Y %H:%M",
        "%m/%d/%Y %H:%M:%S",
        "%m/%d/%Y %H:%M",
        "%Y-%m-%d %H:%M:%S",
        "%Y-%m-%d %H:%M:%S.%f",
        "%Y-%m-%dT%H:%M:%S,%f",
        "%Y-%m-%dT%H:%M:%S%z",
        "%Y-%m-%dT%H:%M:%SZ",
        "%Y-%m-%d %H:%M:%S%z",
        "%Y-%m-%dT%H:%M:%S.%f",
        "%d-%m-%Y %H:%M:%S",
        "%d.%m.%Y %H:%M:%S",
        "%d.%m.%Y %H:%M",
        "%d-%m-%y %H:%M",
        "%B %d, %Y, %I:%M %p",
        "%B %d, %Y, %I:%M:%S %p",
        "%b %d, %Y, %I:%M %p",
        "%Y%m%d",
        "%b %d, %Y, %I:%M:%S %p"
    ]

    s = series.map(clean_cell_value)
    s = pd.Series(s, index=series.index, dtype="object")

    s = s.where(s.notna(), None)
    s = s.astype(object)

    s = s.apply(
        lambda x: (
            x.replace("T", " ")
            .replace("Z", "")
            .strip()
        )
        if isinstance(x, str)
        else x
    )

    # убираем timezone в конце даты: +01:00, +0300 и т.д.
    s = s.apply(
        lambda x: pd.Series([x]).str.replace(
            r"([+-]\d{2}:?\d{2})$",
            "",
            regex=True
        ).iloc[0].strip()
        if isinstance(x, str)
        else x
    )

    result = pd.Series(pd.NaT, index=s.index, dtype="datetime64[ns]")

    for fmt in formats:
        mask = result.isna() & s.notna()

        if not mask.any():
            break

        result.loc[mask] = pd.to_datetime(
            s.loc[mask],
            format=fmt,
            errors="coerce"
        )

    mask = result.isna() & s.notna()

    if mask.any():
        result.loc[mask] = pd.to_datetime(
            s.loc[mask],
            errors="coerce",
            dayfirst=True
        )

    return result.dt.strftime("%Y-%m-%d %H:%M:%S").where(result.notna(), None)

def get_company_wallet_and_short_path(path):
    rel_path = Path(path).relative_to(DATA_DIR)
    parts = rel_path.parts

    company = parts[0].strip() if len(parts) >= 1 else None
    wallet_bank = parts[1].strip() if len(parts) >= 2 else None

    if wallet_bank and wallet_bank.lower() == "flamingopay" and len(parts) >= 3:
        next_folder = parts[2].strip()
        next_folder = next_folder.split()[0].strip()
        wallet_bank = f"{wallet_bank}{next_folder}"

    short_path = "/" + rel_path.as_posix()

    return company, wallet_bank, short_path

def make_raw_hash(row):
    data = {
        col: None if pd.isna(row[col]) else str(row[col])
        for col in COLUMNS
        if col != "raw_hash"
    }

    raw_string = json.dumps(data, ensure_ascii=False, sort_keys=True)
    return hashlib.sha256(raw_string.encode("utf-8")).hexdigest()

def clean_df(df, path):
    df.columns = [
        str(c)
        .replace("\ufeff", "")
        .strip()
        .lower()
        for c in df.columns
    ]

    for col in SOURCE_COLUMNS:
        if col not in df.columns:
            df[col] = None

    df = df[SOURCE_COLUMNS]

    # чистим все значения в таблице
    df = df.map(clean_cell_value)

    for col in DATE_COLUMNS:
        df[col] = normalize_date_series(df[col])

    df["norm_date"] = df["date"]

    df["amount"] = (
        df["amount"]
        .astype(str)
        .str.replace(",", ".", regex=False)
    )

    df["amount"] = pd.to_numeric(df["amount"], errors="coerce")

    company, wallet_bank, short_path = get_company_wallet_and_short_path(path)
    ingestion_time = datetime.now(timezone.utc)

    df.insert(0, "wallet_bank", wallet_bank)
    df.insert(0, "company", company)
    df.insert(5, "norm_date", df.pop("norm_date"))

    df["path"] = short_path
    df["ingestion_id"] = [str(uuid.uuid4()) for _ in range(len(df))]
    df["ingestion_time"] = ingestion_time

    df = df.astype(object).where(pd.notna(df), None)

    df["raw_hash"] = df.apply(make_raw_hash, axis=1)

    df = df.astype(object).where(pd.notna(df), None)

    return df[COLUMNS]

def get_files():
    files = []

    for root, _, names in os.walk(DATA_DIR):
        for name in names:
            if name.lower().endswith((".csv", ".xlsx", ".xls")) and not name.startswith("~$"):
                files.append(Path(root) / name)

    return files

def insert_df(conn, df):
    df = df.astype(object).where(pd.notna(df), None)

    values = [tuple(row) for row in df.to_numpy()]

    column_list = ", ".join(f'"{column}"' for column in COLUMNS)
    query = f'INSERT INTO "{TARGET_SCHEMA}"."{TARGET_TABLE}" ({column_list}) VALUES %s'

    with conn.cursor() as cur:
        execute_values(cur, query, values, page_size=INSERT_PAGE_SIZE)

def validate_settings() -> None:
    missing = [key for key, value in DB_CONFIG.items() if key != "password" and not value]
    if missing:
        raise RuntimeError(
            "Missing PostgreSQL settings: " + ", ".join(sorted(missing))
        )

    if not DATA_DIR.exists():
        raise FileNotFoundError(f"Normalized data directory does not exist: {DATA_DIR}")


def main() -> None:
    validate_settings()

    files = get_files()
    logger.info("Discovered %s normalized files", len(files))

    if not files:
        logger.warning("No CSV or Excel files found in %s", DATA_DIR)
        return

    total_rows = 0

    with psycopg2.connect(**DB_CONFIG) as conn:
        if TRUNCATE_BEFORE_LOAD:
            with conn.cursor() as cur:
                cur.execute(
                    f'TRUNCATE TABLE "{TARGET_SCHEMA}"."{TARGET_TABLE}"'
                )
            logger.info("Truncated %s.%s", TARGET_SCHEMA, TARGET_TABLE)

        for path in files:
            logger.info("Reading %s", path)
            df = read_file(path)

            if df is None or df.empty:
                logger.warning("Skipping empty or unsupported file: %s", path)
                continue

            normalized_df = clean_df(df, path)
            insert_df(conn, normalized_df)

            total_rows += len(normalized_df)
            logger.info("Inserted %s rows", len(normalized_df))

    logger.info("Load completed. Total inserted rows: %s", total_rows)


if __name__ == "__main__":
    main()
