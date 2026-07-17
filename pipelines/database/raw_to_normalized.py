#!/usr/bin/env python3

"""Normalize raw PostgreSQL records into a unified transaction table.

The script reads source rows stored as JSONB, applies provider mappings from
``config/processors_config.py``, normalizes dates and numeric fields, and
upserts the result into a PostgreSQL target table.
"""

import os
import re
import sys
import math
import logging
from datetime import datetime
from pathlib import Path
from decimal import Decimal, InvalidOperation
from typing import Any

import pandas as pd
import psycopg2
from psycopg2 import sql
from psycopg2.extras import Json, execute_values, RealDictCursor
from dotenv import load_dotenv


# ============================================================
# ПУТИ И НАСТРОЙКИ
# ============================================================

PROJECT_ROOT = Path(__file__).resolve().parents[2]
CONFIG_DIR = Path(
    os.getenv("PROCESSOR_CONFIG_DIR", PROJECT_ROOT / "config")
)
CONFIG_MODULE = os.getenv("PROCESSOR_CONFIG_MODULE", "processors_config")

SOURCE_SCHEMA = os.getenv("POSTGRES_SOURCE_SCHEMA", "public")
SOURCE_TABLE = os.getenv("POSTGRES_SOURCE_TABLE", "raw_data")

TARGET_SCHEMA = os.getenv("POSTGRES_TARGET_SCHEMA", "public")
TARGET_TABLE = os.getenv("POSTGRES_TARGET_TABLE", "normalized_data")

LOG_DIR = Path(os.getenv("LOG_DIR", PROJECT_ROOT / "logs"))
LOG_FILE = LOG_DIR / "raw_normalization.log"

FETCH_SIZE = int(os.getenv("FETCH_SIZE", "5000"))
INSERT_PAGE_SIZE = int(os.getenv("INSERT_PAGE_SIZE", "1000"))
TRUNCATE_BEFORE_LOAD = os.getenv("TRUNCATE_BEFORE_LOAD", "false").lower() == "true"


# ============================================================
# ЛОГИРОВАНИЕ
# ============================================================

LOG_DIR.mkdir(parents=True, exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s",
    handlers=[
        logging.FileHandler(
            str(LOG_FILE),
            encoding="utf-8",
        ),
        logging.StreamHandler(),
    ],
)

logger = logging.getLogger(__name__)


# ============================================================
# ПОДКЛЮЧЕНИЕ К POSTGRESQL
# ============================================================

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


# ============================================================
# ЗАГРУЗКА КОНФИГА
# ============================================================

sys.path.insert(0, str(CONFIG_DIR))

try:
    processors_module = __import__(
        CONFIG_MODULE,
        fromlist=["PROCESSORS"],
    )
    PROCESSORS = processors_module.PROCESSORS

except Exception as error:
    raise RuntimeError(
        f"Unable to load processor configuration "
        f"{CONFIG_DIR / (CONFIG_MODULE + '.py')}: {error}"
    ) from error


PROCESSORS_BY_WALLET = {
    str(item["wallet_bank"]).strip().casefold(): item
    for item in PROCESSORS
}


# ============================================================
# ЦЕЛЕВЫЕ КОЛОНКИ
# ============================================================

TARGET_COLUMNS = [
    "company",
    "wallet_bank",

    "transaction_date",
    "depositdate",
    "withdrawaldate",
    "norm_date",

    "pay_id",
    "status",

    "amount",
    "currency",
    "commission",
    "commissioncurrency",
    "exchangerate",
    "finalamount",

    "project",
    "notes",
    "reference",
    "paymentmethod",

    "settlement",
    "settlementcomission",
    "topups",
    "topupscomission",
    "affilates",
    "affilatescommission",
    "chargebacksrefunds",
    "chargebacksrefundscommission",
    "expenses",
    "expensescommission",

    "notes222",
    "notes333",
    "notes444",

    "source_path",
    "relative_source_path",
    "source_file",
    "source_row_number",
    "source_sheet_name",

    "folder_1",
    "folder_2",
    "folder_3",
    "folder_4",
    "folder_5",

    "ingestion_id",
    "ingestion_time",
    "raw_hash",

    "normalization_time",
    "normalization_error",
    "raw_data",
]


DATE_COLUMNS = {
    "date",
    "depositdate",
    "withdrawaldate",
}

NUMERIC_COLUMNS = {
    "amount",
    "commission",
    "exchangerate",
    "finalamount",
    "settlement",
    "settlementcomission",
    "topups",
    "topupscomission",
    "affilates",
    "affilatescommission",
    "chargebacksrefunds",
    "chargebacksrefundscommission",
    "expenses",
    "expensescommission",
}


NULL_STRINGS = {
    "",
    "none",
    "null",
    "nan",
    "nat",
    "no_data",
    "n/a",
    "na",
    "-",
}


# Для неоднозначных дат вида 06/07/2026.
# По умолчанию используется европейский вариант day/month/year.
DAYFIRST_BY_WALLET = {
    # При необходимости можно задавать исключения:
    # "somewallet": False,
    "biso": True,
}


# ============================================================
# НОРМАЛИЗАЦИЯ НАЗВАНИЙ JSON-КЛЮЧЕЙ
# ============================================================

def normalize_key(value: Any) -> str:
    """
    Приводит JSON-ключ к форме, похожей на названия в конфиге.

    Например:
        'TRANSACTION ID' -> 'transactionid'
        'Date Posted'    -> 'dateposted'
        'Сумма и валюта' -> 'суммаивалюта'
    """

    if value is None:
        return ""

    value = str(value).replace("\ufeff", "").strip().casefold()

    return re.sub(
        r"[\s_\-]+",
        "",
        value,
    )


def build_normalized_raw_data(
    raw_data: dict[str, Any],
) -> dict[str, Any]:
    """
    Создаёт словарь для нечувствительного поиска полей.
    """

    normalized = {}

    for original_key, value in raw_data.items():
        key = normalize_key(original_key)

        if key and key not in normalized:
            normalized[key] = value

    return normalized


# ============================================================
# ОЧИСТКА ЗНАЧЕНИЙ
# ============================================================

def clean_value(value: Any) -> Any:
    if value is None:
        return None

    if isinstance(value, float):
        if math.isnan(value) or math.isinf(value):
            return None

    if isinstance(value, str):
        value = value.strip()

        while value and value[0] in {
            '"', "'", "`", " ", "\t", "\n", "\r"
        }:
            value = value[1:].strip()

        while value and value[-1] in {
            '"', "'", "`", " ", "\t", "\n", "\r"
        }:
            value = value[:-1].strip()

        if value.casefold() in NULL_STRINGS:
            return None

    return value


def get_raw_value(
    raw_normalized: dict[str, Any],
    source_column: str,
) -> Any:
    """
    Получает значение исходного поля по нечувствительному ключу.
    """

    if not source_column:
        return None

    if source_column.casefold() == "no_data":
        return None

    key = normalize_key(source_column)

    return clean_value(
        raw_normalized.get(key)
    )


# ============================================================
# ОБРАБОТКА ПРАВИЛ КОНФИГА
# ============================================================

def resolve_mapping_rule(
    raw_normalized: dict[str, Any],
    rule: Any,
) -> Any:
    """
    Поддерживаемые правила:

    "amount"
        Взять raw_data["amount"].

    ("amount", "0")
        Взять amount, иначе использовать 0.

    ["[+]", "[-]"]
        Взять первое заполненное поле.

    "field1+field2"
        Сложить числовые значения.
    """

    default_value = None
    source_rule = rule

    if isinstance(rule, tuple):
        if len(rule) >= 1:
            source_rule = rule[0]

        if len(rule) >= 2:
            default_value = rule[1]

    if isinstance(source_rule, list):
        for source_column in source_rule:
            value = get_raw_value(
                raw_normalized,
                str(source_column),
            )

            if value is not None:
                return value

        return normalize_default(default_value)

    if source_rule is None:
        return normalize_default(default_value)

    source_rule = str(source_rule).strip()

    if source_rule.casefold() == "no_data":
        return normalize_default(default_value)

    # Формула сложения:
    # networkfeeequivalent+servicefeeequivalent
    if "+" in source_rule:
        source_columns = [
            item.strip()
            for item in source_rule.split("+")
            if item.strip()
        ]

        numeric_values = []

        for source_column in source_columns:
            raw_value = get_raw_value(
                raw_normalized,
                source_column,
            )

            numeric_value = normalize_number(raw_value)

            if numeric_value is not None:
                numeric_values.append(numeric_value)

        if numeric_values:
            return sum(
                numeric_values,
                Decimal("0"),
            )

        return normalize_default(default_value)

    value = get_raw_value(
        raw_normalized,
        source_rule,
    )

    if value is None:
        return normalize_default(default_value)

    return value


def normalize_default(value: Any) -> Any:
    value = clean_value(value)

    if value is None:
        return None

    if (
        isinstance(value, str)
        and value.casefold() == "no_data"
    ):
        return None

    return value


# ============================================================
# НОРМАЛИЗАЦИЯ ЧИСЕЛ
# ============================================================

def normalize_number(value: Any) -> Decimal | None:
    value = clean_value(value)

    if value is None:
        return None

    if isinstance(value, Decimal):
        return value

    if isinstance(value, (int, float)):
        try:
            return Decimal(str(value))
        except InvalidOperation:
            return None

    text = str(value).strip()

    if not text:
        return None

    # Удаляем валютные символы и текст.
    text = re.sub(
        r"[^\d,\.\-\+]",
        "",
        text,
    )

    if not text:
        return None

    # Определение десятичного разделителя.
    if "," in text and "." in text:
        if text.rfind(",") > text.rfind("."):
            # 1.234,56
            text = text.replace(".", "")
            text = text.replace(",", ".")
        else:
            # 1,234.56
            text = text.replace(",", "")

    elif "," in text:
        # 123,45
        text = text.replace(",", ".")

    # Убираем повторные знаки.
    if text.startswith("+"):
        text = text[1:]

    try:
        return Decimal(text)

    except InvalidOperation:
        return None


# ============================================================
# НОРМАЛИЗАЦИЯ ДАТ
# ============================================================

DATE_FORMATS_DAYFIRST = [
    "%Y-%m-%d %H:%M:%S.%f",
    "%Y-%m-%d %H:%M:%S",
    "%Y-%m-%dT%H:%M:%S.%f%z",
    "%Y-%m-%dT%H:%M:%S%z",
    "%Y-%m-%dT%H:%M:%S.%f",
    "%Y-%m-%dT%H:%M:%S",
    "%Y-%m-%d",
    "%d/%m/%Y %H:%M:%S",
    "%d/%m/%Y %H:%M",
    "%d/%m/%Y",
    "%d.%m.%Y %H:%M:%S",
    "%d.%m.%Y %H:%M",
    "%d.%m.%Y",
    "%d-%m-%Y %H:%M:%S",
    "%d-%m-%Y %H:%M",
    "%d-%m-%Y",
    "%d %b %Y %H:%M:%S",
    "%d %b %Y %H:%M",
    "%d %b %Y",
    "%d %B %Y %H:%M:%S",
    "%d %B %Y %H:%M",
    "%d %B %Y",
    "%b %d, %Y, %I:%M:%S %p",
    "%b %d, %Y, %I:%M %p",
    "%B %d, %Y, %I:%M:%S %p",
    "%B %d, %Y, %I:%M %p",
    "%Y%m%d",
]


DATE_FORMATS_MONTHFIRST = [
    "%m/%d/%Y %H:%M:%S",
    "%m/%d/%Y %H:%M",
    "%m/%d/%Y",
]


def normalize_datetime(
    value: Any,
    dayfirst: bool = True,
) -> datetime | None:
    value = clean_value(value)

    if value is None:
        return None

    if isinstance(value, pd.Timestamp):
        value = value.to_pydatetime()

    if isinstance(value, datetime):
        # PostgreSQL-колонка TIMESTAMP без timezone.
        return value.replace(tzinfo=None)

    text = str(value).strip()

    if not text:
        return None

    # Excel serial date.
    if re.fullmatch(r"\d{4,6}(\.\d+)?", text):
        try:
            serial = float(text)

            if 20000 <= serial <= 80000:
                result = pd.Timestamp(
                    "1899-12-30"
                ) + pd.to_timedelta(
                    serial,
                    unit="D",
                )

                return result.to_pydatetime()

        except (ValueError, OverflowError):
            pass

    # Исправляет:
    # 2026-06-0619:35:13
    text = re.sub(
        r"(\d{4}-\d{2}-\d{2})(\d{2}:\d{2}:\d{2})",
        r"\1 \2",
        text,
    )

    # Исправляет ISO с запятой перед миллисекундами.
    text = re.sub(
        r"(\d{2}:\d{2}:\d{2}),(\d+)",
        r"\1.\2",
        text,
    )

    formats = []

    if dayfirst:
        formats.extend(DATE_FORMATS_DAYFIRST)
        formats.extend(DATE_FORMATS_MONTHFIRST)
    else:
        formats.extend(DATE_FORMATS_MONTHFIRST)
        formats.extend(DATE_FORMATS_DAYFIRST)

    for date_format in formats:
        try:
            parsed = datetime.strptime(
                text,
                date_format,
            )

            return parsed.replace(tzinfo=None)

        except ValueError:
            continue

    # Последняя попытка через pandas.
    try:
        parsed = pd.to_datetime(
            text,
            errors="coerce",
            dayfirst=dayfirst,
            utc=False,
        )

        if pd.isna(parsed):
            return None

        result = parsed.to_pydatetime()

        if result.tzinfo is not None:
            result = result.replace(tzinfo=None)

        return result

    except Exception:
        return None


# ============================================================
# СПЕЦИАЛЬНЫЕ ПРАВИЛА КОШЕЛЬКОВ
# ============================================================

def apply_wallet_specific_rules(
    wallet_bank: str,
    mapped: dict[str, Any],
    raw_normalized: dict[str, Any],
) -> None:
    wallet_key = wallet_bank.casefold()

    # Flyk:
    # additionalinfo содержит:
    # transactionId: 0b0a3159...
    if wallet_key == "flyk":
        additional_info = get_raw_value(
            raw_normalized,
            "additionalinfo",
        )

        if additional_info:
            match = re.search(
                r"transactionid\s*:\s*"
                r"([a-zA-Z0-9_-]+)",
                str(additional_info),
                flags=re.IGNORECASE,
            )

            if match:
                mapped["pay_id"] = match.group(1)

    # Skrill:
    # [+] является поступлением,
    # [-] является списанием.
    if wallet_key == "skrill":
        positive = normalize_number(
            get_raw_value(raw_normalized, "[+]")
        )

        negative = normalize_number(
            get_raw_value(raw_normalized, "[-]")
        )

        if positive is not None:
            mapped["amount"] = abs(positive)

        elif negative is not None:
            mapped["amount"] = -abs(negative)

    # Coinbase:
    # Иногда валюта находится в той же колонке,
    # что и сумма: например "100 EUR".
    if wallet_key == "coinbase":
        raw_currency = mapped.get("currency")

        if raw_currency:
            match = re.search(
                r"\b([A-Z]{3,10})\b",
                str(raw_currency).upper(),
            )

            if match:
                mapped["currency"] = match.group(1)


# ============================================================
# МАППИНГ ОДНОЙ СТРОКИ
# ============================================================

def map_raw_row(
    source_row: dict[str, Any],
) -> dict[str, Any]:
    wallet_bank = clean_value(
        source_row.get("folder_2")
    )

    result = {
        column: None
        for column in TARGET_COLUMNS
    }

    result.update({
        "company": source_row.get("folder_1"),
        "wallet_bank": wallet_bank,

        "source_path": source_row.get("source_path"),
        "relative_source_path":
            source_row.get("relative_source_path"),
        "source_file": source_row.get("source_file"),
        "source_row_number":
            source_row.get("source_row_number"),
        "source_sheet_name":
            source_row.get("sheet_name"),

        "folder_1": source_row.get("folder_1"),
        "folder_2": source_row.get("folder_2"),
        "folder_3": source_row.get("folder_3"),
        "folder_4": source_row.get("folder_4"),
        "folder_5": source_row.get("folder_5"),

        "ingestion_id": source_row.get("ingestion_id"),
        "ingestion_time":
            source_row.get("ingestion_time"),
        "raw_hash": source_row.get("raw_hash"),

        "normalization_time":
            datetime.now().astimezone(),
        "raw_data": source_row.get("raw_data"),
    })

    if not wallet_bank:
        result["normalization_error"] = (
            "folder_2 / wallet_bank is missing"
        )
        return result

    processor = PROCESSORS_BY_WALLET.get(
        str(wallet_bank).strip().casefold()
    )

    if processor is None:
        result["normalization_error"] = (
            f"No configuration found for wallet_bank="
            f"{wallet_bank}"
        )
        return result

    raw_data = source_row.get("raw_data") or {}

    if not isinstance(raw_data, dict):
        result["normalization_error"] = (
            "raw_data is not a JSON object"
        )
        return result

    raw_normalized = build_normalized_raw_data(
        raw_data
    )

    mapping = processor.get("columns", {})

    mapped = {}

    for target_column, rule in mapping.items():
        mapped[target_column] = resolve_mapping_rule(
            raw_normalized,
            rule,
        )

    apply_wallet_specific_rules(
        wallet_bank=str(wallet_bank),
        mapped=mapped,
        raw_normalized=raw_normalized,
    )

    wallet_key = str(wallet_bank).casefold()

    dayfirst = DAYFIRST_BY_WALLET.get(
        wallet_key,
        True,
    )

    # Даты
    transaction_date = normalize_datetime(
        mapped.get("date"),
        dayfirst=dayfirst,
    )

    depositdate = normalize_datetime(
        mapped.get("depositdate"),
        dayfirst=dayfirst,
    )

    withdrawaldate = normalize_datetime(
        mapped.get("withdrawaldate"),
        dayfirst=dayfirst,
    )

    result["transaction_date"] = transaction_date
    result["depositdate"] = depositdate
    result["withdrawaldate"] = withdrawaldate

    # Общая нормализованная дата.
    result["norm_date"] = (
        transaction_date
        or depositdate
        or withdrawaldate
    )

    # Числа
    for column in NUMERIC_COLUMNS:
        result[column] = normalize_number(
            mapped.get(column)
        )

    # Текст
    for column in [
        "pay_id",
        "status",
        "currency",
        "commissioncurrency",
        "project",
        "notes",
        "reference",
        "paymentmethod",
        "notes222",
        "notes333",
        "notes444",
    ]:
        result[column] = clean_value(
            mapped.get(column)
        )

    return result


# ============================================================
# СОЗДАНИЕ ТАБЛИЦЫ
# ============================================================

def create_target_table(conn) -> None:
    query = sql.SQL("""
        CREATE TABLE IF NOT EXISTS {}.{}
        (
            company                       TEXT,
            wallet_bank                   TEXT,
            transaction_date              TIMESTAMP,
            depositdate                   TIMESTAMP,
            withdrawaldate                TIMESTAMP,
            norm_date                     TIMESTAMP,
            pay_id                        TEXT,
            status                        TEXT,
            amount                        NUMERIC,
            currency                      TEXT,
            commission                    NUMERIC,
            commissioncurrency            TEXT,
            exchangerate                  NUMERIC,
            finalamount                   NUMERIC,
            project                       TEXT,
            notes                         TEXT,
            reference                     TEXT,
            paymentmethod                 TEXT,
            settlement                    NUMERIC,
            settlementcomission           NUMERIC,
            topups                        NUMERIC,
            topupscomission               NUMERIC,
            affilates                     NUMERIC,
            affilatescommission           NUMERIC,
            chargebacksrefunds            NUMERIC,
            chargebacksrefundscommission  NUMERIC,
            expenses                      NUMERIC,
            expensescommission            NUMERIC,
            notes222                      TEXT,
            notes333                      TEXT,
            notes444                      TEXT,
            source_path                   TEXT,
            relative_source_path          TEXT,
            source_file                   TEXT,
            source_row_number             BIGINT,
            source_sheet_name             TEXT,
            folder_1                      TEXT,
            folder_2                      TEXT,
            folder_3                      TEXT,
            folder_4                      TEXT,
            folder_5                      TEXT,
            ingestion_id                  UUID PRIMARY KEY,
            ingestion_time                TIMESTAMPTZ,
            raw_hash                      CHAR(64),
            normalization_time            TIMESTAMPTZ
                                          NOT NULL
                                          DEFAULT NOW(),
            normalization_error           TEXT,
            raw_data                      JSONB
        );
    """).format(
        sql.Identifier(TARGET_SCHEMA),
        sql.Identifier(TARGET_TABLE),
    )

    with conn.cursor() as cursor:
        cursor.execute(query)

    conn.commit()


# ============================================================
# ЗАПИСЬ В POSTGRESQL
# ============================================================

def prepare_insert_tuple(
    row: dict[str, Any],
) -> tuple:
    values = []

    for column in TARGET_COLUMNS:
        value = row.get(column)

        if column == "raw_data":
            value = Json(value or {})

        values.append(value)

    return tuple(values)


def insert_rows(
    conn,
    rows: list[dict[str, Any]],
) -> int:
    if not rows:
        return 0

    column_identifiers = sql.SQL(", ").join(
        sql.Identifier(column)
        for column in TARGET_COLUMNS
    )

    update_columns = [
        column
        for column in TARGET_COLUMNS
        if column != "ingestion_id"
    ]

    update_clause = sql.SQL(", ").join(
        sql.SQL("{} = EXCLUDED.{}").format(
            sql.Identifier(column),
            sql.Identifier(column),
        )
        for column in update_columns
    )

    query = sql.SQL("""
        INSERT INTO {}.{}
        ({})
        VALUES %s
        ON CONFLICT (ingestion_id)
        DO UPDATE SET
        {}
    """).format(
        sql.Identifier(TARGET_SCHEMA),
        sql.Identifier(TARGET_TABLE),
        column_identifiers,
        update_clause,
    )

    values = [
        prepare_insert_tuple(row)
        for row in rows
    ]

    with conn.cursor() as cursor:
        execute_values(
            cursor,
            query.as_string(conn),
            values,
            page_size=INSERT_PAGE_SIZE,
        )

    return len(values)


# ============================================================
# ЧТЕНИЕ RAW-ДАННЫХ
# ============================================================

def get_source_query(conn) -> str:
    query = sql.SQL("""
        SELECT
            ingestion_id,
            ingestion_time,
            raw_hash,
            source_path,
            relative_source_path,
            source_file,
            file_extension,
            sheet_name,
            source_row_number,
            raw_data,
            folder_1,
            folder_2,
            folder_3,
            folder_4,
            folder_5
        FROM {}.{}
        ORDER BY ingestion_time, ingestion_id
    """).format(
        sql.Identifier(SOURCE_SCHEMA),
        sql.Identifier(SOURCE_TABLE),
    )

    return query.as_string(conn)


# ============================================================
# VALIDATION
# ============================================================

def validate_settings() -> None:
    missing = [
        key
        for key, value in DB_CONFIG.items()
        if key != "password" and not value
    ]

    if missing:
        raise RuntimeError(
            "Missing PostgreSQL settings: " + ", ".join(sorted(missing))
        )

    if not CONFIG_DIR.exists():
        raise FileNotFoundError(
            f"Processor configuration directory does not exist: {CONFIG_DIR}"
        )


# ============================================================
# MAIN
# ============================================================

def main() -> None:
    validate_settings()

    logger.info(
        "Loaded provider configurations: %s",
        len(PROCESSORS_BY_WALLET),
    )

    read_conn = None
    write_conn = None

    total_rows = 0
    error_rows = 0

    try:
        # Отдельное соединение для чтения.
        read_conn = psycopg2.connect(**DB_CONFIG)

        # Отдельное соединение для INSERT/UPDATE.
        write_conn = psycopg2.connect(**DB_CONFIG)

        logger.info("Connected to PostgreSQL")

        create_target_table(write_conn)

        if TRUNCATE_BEFORE_LOAD:
            with write_conn.cursor() as cursor:
                cursor.execute(
                    sql.SQL(
                        "TRUNCATE TABLE {}.{}"
                    ).format(
                        sql.Identifier(TARGET_SCHEMA),
                        sql.Identifier(TARGET_TABLE),
                    )
                )

            write_conn.commit()

            logger.info(
                "Truncated table %s.%s",
                TARGET_SCHEMA,
                TARGET_TABLE,
            )

        source_query = get_source_query(read_conn)

        # Именованный курсор работает внутри транзакции read_conn.
        # В read_conn нельзя выполнять commit, пока курсор открыт.
        with read_conn.cursor(
            name="raw_data_cursor",
            cursor_factory=RealDictCursor,
        ) as source_cursor:

            source_cursor.itersize = FETCH_SIZE
            source_cursor.execute(source_query)

            batch = []

            for source_row in source_cursor:
                normalized_row = map_raw_row(
                    dict(source_row)
                )

                if normalized_row.get(
                    "normalization_error"
                ):
                    error_rows += 1

                    logger.warning(
                        "%s | файл=%s | строка=%s",
                        normalized_row[
                            "normalization_error"
                        ],
                        normalized_row.get(
                            "source_file"
                        ),
                        normalized_row.get(
                            "source_row_number"
                        ),
                    )

                batch.append(normalized_row)

                if len(batch) >= INSERT_PAGE_SIZE:
                    inserted = insert_rows(
                        write_conn,
                        batch,
                    )

                    # Commit делаем только на write_conn.
                    write_conn.commit()

                    total_rows += inserted

                    logger.info(
                        "Processed rows: %s",
                        total_rows,
                    )

                    batch.clear()

            if batch:
                inserted = insert_rows(
                    write_conn,
                    batch,
                )

                write_conn.commit()

                total_rows += inserted
                batch.clear()

        # Завершаем транзакцию чтения только после закрытия курсора.
        read_conn.commit()

        logger.info("=" * 60)
        logger.info("Normalization completed")
        logger.info(
            "Total processed rows: %s",
            total_rows,
        )
        logger.info(
            "Rows with warnings: %s",
            error_rows,
        )
        logger.info(
            "Target table: %s.%s",
            TARGET_SCHEMA,
            TARGET_TABLE,
        )
        logger.info("=" * 60)

    except Exception:
        if write_conn is not None:
            write_conn.rollback()

        if read_conn is not None:
            read_conn.rollback()

        logger.exception(
            "Critical normalization error"
        )
        raise

    finally:
        if read_conn is not None:
            read_conn.close()
            logger.info(
                "PostgreSQL read connection closed"
            )

        if write_conn is not None:
            write_conn.close()
            logger.info(
                "PostgreSQL write connection closed"
            )


if __name__ == "__main__":
    main()