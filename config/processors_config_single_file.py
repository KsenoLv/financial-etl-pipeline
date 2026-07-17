"""Single-file payment-provider mapping registry.

This variant keeps all provider mappings in one module. It is useful for
small projects or deployments where centralized configuration is preferred.
"""

AIFORY = {
    "wallet_bank": "Aifory",
    "columns": {
        "date": "время",
        "depositdate": "завершен",
        "withdrawaldate": "успешнооплачено",
        "pay_id": "clientorderid",
        "status": "Статус изменен",
        "amount": "сумма",
        "currency": "валюта",
        "commission": "комиссия",
        "commissioncurrency": ("no_data", "no_data"),
        "exchangerate": ("no_data", "no_data"),
        "finalamount": ("no_data", "no_data"),
        "project": ("project", "no_data"),
        "notes": ("organization", "no_data"),
        "reference": ("тип", "deposit"),
        "paymentmethod": ("no_data", "no_data"),
        "settlement": ("no_data", "no_data"),
        "settlementcomission": ("no_data", "no_data"),
        "topups": ("no_data", "no_data"),
        "topupscomission": ("no_data", "no_data"),
        "affilates": ("no_data", "no_data"),
        "affilatescommission": ("no_data", "no_data"),
        "chargebacksrefunds": ("no_data", "no_data"),
        "chargebacksrefundscommission": ("no_data", "no_data"),
        "expenses": ("no_data", "no_data"),
        "expensescommission": ("no_data", "no_data"),
        "notes222": ("no_data", "no_data"),
        "notes333": ("no_data", "no_data"),
        "notes444": ("no_data", "no_data"),
    },
}

BISO = {
    "wallet_bank": "Biso",
    "columns": {
        "date": "created",
        "depositdate": "created",
        "withdrawaldate": "created",
        "pay_id": "customerorderreference",
        "status": "status",
        "amount": "amount",
        "currency": "currency",
        "commission": ("fee_total", "no_data"),
        "commissioncurrency": ("no_data", "no_data"),
        "exchangerate": ("no_data", "no_data"),
        "finalamount": ("no_data", "no_data"),
        "project": "website",
        "notes": ("organization", "no_data"),
        "reference": "type",
        "paymentmethod": ("paymentmethod", "no_data"),
        "settlement": ("no_data", "no_data"),
        "settlementcomission": ("no_data", "no_data"),
        "topups": ("no_data", "no_data"),
        "topupscomission": ("no_data", "no_data"),
        "affilates": ("no_data", "no_data"),
        "affilatescommission": ("no_data", "no_data"),
        "chargebacksrefunds": ("no_data", "no_data"),
        "chargebacksrefundscommission": ("no_data", "no_data"),
        "expenses": ("no_data", "no_data"),
        "expensescommission": ("no_data", "no_data"),
        "notes222": ("no_data", "no_data"),
        "notes333": ("no_data", "no_data"),
        "notes444": ("no_data", "no_data"),
    },
}

JETON = {
    "wallet_bank": "Jeton",
    "columns": {
        "date": "time",
        "depositdate": "time",
        "withdrawaldate": "time",
        "pay_id": "reference",
        "status": "status",
        "amount": "processingamount",
        "currency": "processingcurrency",
        "commission": ("fee_total", "no_data"),
        "commissioncurrency": ("no_data", "no_data"),
        "exchangerate": ("no_data", "no_data"),
        "finalamount": ("no_data", "no_data"),
        "project": "merchantname",
        "notes": ("organization", "no_data"),
        "reference": "category",
        "paymentmethod": ("no_data", "E-Wallet"),
        "settlement": ("no_data", "no_data"),
        "settlementcomission": ("no_data", "no_data"),
        "topups": ("no_data", "no_data"),
        "topupscomission": ("no_data", "no_data"),
        "affilates": ("no_data", "no_data"),
        "affilatescommission": ("no_data", "no_data"),
        "chargebacksrefunds": ("no_data", "no_data"),
        "chargebacksrefundscommission": ("no_data", "no_data"),
        "expenses": ("no_data", "no_data"),
        "expensescommission": ("no_data", "no_data"),
        "notes222": ("no_data", "no_data"),
        "notes333": ("no_data", "no_data"),
        "notes444": ("no_data", "no_data"),
    },
}

TUNZER = {
    "wallet_bank": "Tunzer",
    "columns": {
        "date": "ordercreatedsystemtimestamp",
        "depositdate": "orderchangedsystemtimestamp",
        "withdrawaldate": "ordercreatedsystemtimestamp",
        "pay_id": "ordermerchantid",
        "status": "transactionstatus",
        "amount": "transactionamount",
        "currency": "transactioncurrencycode",
        "commission": "transactioncommission",
        "commissioncurrency": ("no_data", "no_data"),
        "exchangerate": ("no_data", "no_data"),
        "finalamount": ("no_data", "no_data"),
        "project": "requestorname",
        "notes": ("transactiontype", "no_data"),
        "reference": "orderdescription",
        "paymentmethod": ("cardtype", "no_data"),
        "settlement": ("no_data", "no_data"),
        "settlementcomission": ("no_data", "no_data"),
        "topups": ("no_data", "no_data"),
        "topupscomission": ("no_data", "no_data"),
        "affilates": ("no_data", "no_data"),
        "affilatescommission": ("no_data", "no_data"),
        "chargebacksrefunds": ("no_data", "no_data"),
        "chargebacksrefundscommission": ("no_data", "no_data"),
        "expenses": ("no_data", "no_data"),
        "expensescommission": ("no_data", "no_data"),
        "notes222": ("no_data", "no_data"),
        "notes333": ("no_data", "no_data"),
        "notes444": ("no_data", "no_data"),
    },
}

PROCESSORS = [AIFORY, BISO, JETON, TUNZER]

PROCESSORS_BY_WALLET = {
    processor["wallet_bank"].casefold(): processor
    for processor in PROCESSORS
}


def get_processor(wallet_bank: str) -> dict:
    """Return a provider configuration by wallet name."""
    try:
        return PROCESSORS_BY_WALLET[wallet_bank.casefold()]
    except KeyError as error:
        available = ", ".join(item["wallet_bank"] for item in PROCESSORS)
        raise KeyError(
            f"Unknown wallet '{wallet_bank}'. Available wallets: {available}"
        ) from error
