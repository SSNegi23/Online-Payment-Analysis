from .gpay  import GPayParser
from .paytm import PaytmParser
from .base  import BaseParser, Transaction

# -----------------------------------------------------------------------
# PROVIDER REGISTRY
# To add a new provider (e.g. PhonePe):
#   1. Create src/parsers/phonepe.py with class PhonePeParser(BaseParser)
#   2. Add one line below: "phonepe": PhonePeParser
# Nothing else needs to change.
# -----------------------------------------------------------------------
PROVIDER_REGISTRY: dict[str, type[BaseParser]] = {
    "gpay":  GPayParser,
    "paytm": PaytmParser,
}


def get_parser(provider: str) -> BaseParser:
    key = provider.strip().lower()
    if key not in PROVIDER_REGISTRY:
        supported = ", ".join(PROVIDER_REGISTRY.keys())
        raise ValueError(f"Unknown provider '{provider}'. Supported: {supported}")
    return PROVIDER_REGISTRY[key]()


def supported_providers() -> list[str]:
    return list(PROVIDER_REGISTRY.keys())
