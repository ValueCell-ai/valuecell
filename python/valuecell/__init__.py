"""ValueCell - A community-driven, multi-agent platform for financial applications."""

__version__ = "0.1.0"
__author__ = "ValueCell Team"
__description__ = "A community-driven, multi-agent platform for financial applications"

# Core package information - only import what's absolutely necessary
# For i18n functionality, import from specific modules:
# from valuecell.services.i18n_service import get_i18n_service, t
# from valuecell.config.settings import get_settings

__all__ = [
    "__version__",
    "__author__",
    "__description__",
]

# registers agents on import
import valuecell.agents as _  # noqa: F401
