"""Single-file alternative for provider configuration.

This module demonstrates a simpler configuration structure suitable
for small ETL projects with a limited number of payment providers.
"""


AIFORY = {
    "wallet_bank": "Aifory",
    "columns": {
        # Mapping configuration
    },
}


BISO = {
    "wallet_bank": "Biso",
    "columns": {
        # Mapping configuration
    },
}


JETON = {
    "wallet_bank": "Jeton",
    "columns": {
        # Mapping configuration
    },
}


TUNZER = {
    "wallet_bank": "Tunzer",
    "columns": {
        # Mapping configuration
    },
}


PROCESSORS = [
    AIFORY,
    BISO,
    JETON,
    TUNZER,
]


PROCESSORS_BY_WALLET = {
    processor["wallet_bank"].casefold(): processor
    for processor in PROCESSORS
}