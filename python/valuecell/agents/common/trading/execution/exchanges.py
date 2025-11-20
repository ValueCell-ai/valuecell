"""Exchange metadata and special configurations for CCXT.

This module provides metadata about supported exchanges, including
authentication requirements and special handling notes.
"""

from __future__ import annotations

from typing import Dict, List, Optional

from pydantic import BaseModel


class ExchangeMetadata(BaseModel):
    """Metadata for a supported exchange.

    Attributes:
        id: CCXT exchange identifier
        name: Display name
        requires_passphrase: Whether the exchange requires a passphrase/password
        requires_api_key: Whether the exchange requires an API key
        requires_secret: Whether the exchange requires a secret key
        special_auth: Special authentication requirements (e.g., privateKey, walletAddress)
        testnet_supported: Whether testnet/sandbox mode is supported
        notes: Additional notes or warnings
    """

    id: str
    name: str
    requires_passphrase: bool = False
    requires_api_key: bool = True
    requires_secret: bool = True
    special_auth: Optional[List[str]] = None
    testnet_supported: bool = False
    notes: Optional[str] = None


# Supported exchanges metadata
SUPPORTED_EXCHANGES: Dict[str, ExchangeMetadata] = {
    "binance": ExchangeMetadata(
        id="binance",
        name="Binance",
        testnet_supported=True,
        notes="Most popular exchange with comprehensive CCXT support",
    ),
    "okx": ExchangeMetadata(
        id="okx",
        name="OKX",
        requires_passphrase=True,
        testnet_supported=True,
        notes="Requires passphrase for authentication",
    ),
    "blockchaincom": ExchangeMetadata(
        id="blockchaincom",
        name="Blockchain.com",
        requires_api_key=False,
        notes="Only requires secret key (no API key needed)",
    ),
    "coinbaseexchange": ExchangeMetadata(
        id="coinbaseexchange",
        name="Coinbase Exchange",
        requires_passphrase=True,
        testnet_supported=True,
        notes="Main Coinbase exchange (not Coinbase International). Requires passphrase.",
    ),
    "gate": ExchangeMetadata(
        id="gate",
        name="Gate.io",
        testnet_supported=True,
        notes="Gate.io main exchange with standard API key/secret authentication",
    ),
    "hyperliquid": ExchangeMetadata(
        id="hyperliquid",
        name="Hyperliquid",
        requires_api_key=False,
        requires_secret=False,
        special_auth=["privateKey", "walletAddress"],
        notes="Uses wallet-based authentication (privateKey + walletAddress). Not standard API key/secret.",
    ),
    "mexc": ExchangeMetadata(
        id="mexc",
        name="MEXC Global",
        testnet_supported=False,
        notes="MEXC main exchange with standard API key/secret authentication",
    ),
}


def get_exchange_metadata(exchange_id: str) -> Optional[ExchangeMetadata]:
    """Get metadata for a specific exchange.

    Args:
        exchange_id: CCXT exchange identifier

    Returns:
        ExchangeMetadata if exchange is supported, None otherwise
    """
    return SUPPORTED_EXCHANGES.get(exchange_id.lower())


def requires_passphrase(exchange_id: str) -> bool:
    """Check if an exchange requires a passphrase.

    Args:
        exchange_id: CCXT exchange identifier

    Returns:
        True if passphrase is required, False otherwise
    """
    metadata = get_exchange_metadata(exchange_id)
    return metadata.requires_passphrase if metadata else False


def get_supported_exchange_ids() -> List[str]:
    """Get list of supported exchange IDs.

    Returns:
        List of CCXT exchange identifiers
    """
    return list(SUPPORTED_EXCHANGES.keys())


def validate_exchange_credentials(
    exchange_id: str,
    api_key: Optional[str] = None,
    secret_key: Optional[str] = None,
    passphrase: Optional[str] = None,
) -> tuple[bool, Optional[str]]:
    """Validate that provided credentials match exchange requirements.

    Args:
        exchange_id: CCXT exchange identifier
        api_key: API key
        secret_key: Secret key
        passphrase: Passphrase/password

    Returns:
        Tuple of (is_valid, error_message)
    """
    metadata = get_exchange_metadata(exchange_id)
    if not metadata:
        return False, f"Exchange '{exchange_id}' is not supported"

    # Check for special authentication requirements
    if metadata.special_auth:
        return (
            False,
            f"Exchange '{exchange_id}' requires special authentication: {', '.join(metadata.special_auth)}",
        )

    # Check standard credentials
    if metadata.requires_api_key and not api_key:
        return False, f"Exchange '{exchange_id}' requires an API key"

    if metadata.requires_secret and not secret_key:
        return False, f"Exchange '{exchange_id}' requires a secret key"

    if metadata.requires_passphrase and not passphrase:
        return False, f"Exchange '{exchange_id}' requires a passphrase"

    return True, None
