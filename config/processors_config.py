"""Registry of public payment-provider mappings."""

from .processors import AIFORY, BISO, JETON, TUNZER

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
