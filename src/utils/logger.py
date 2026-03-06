import logging
from typing import Literal
from rich.console import Console
from rich.logging import RichHandler

# Global namespace for all loggers
BASE_LOGGER_NAMESPACE = "multi_mcp"


def get_logger(name: str) -> logging.Logger:
    """
    Returns a logger nested under the base project namespace.

    Example: get_logger("ClientManager") → "multi_mcp.ClientManager"
    """
    return logging.getLogger(f"{BASE_LOGGER_NAMESPACE}.{name}")


def configure_logging(
    level: Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"] = "INFO",
) -> None:
    """
    Configures logging globally for the entire app using RichHandler.

    Should be called once (e.g., in MultiMCP.__init__).

    Args:
        level: Logging level as a string.
    """

    logging.basicConfig(
        level=level,
        format="%(message)s",  # Rich handles formatting
        handlers=[RichHandler(console=Console(stderr=True), rich_tracebacks=True, show_time=False)],
    )

    # Suppress noisy watchfiles Rust-backend poll-timeout debug messages.
    # These appear as "rust notify timeout, continuing" on every poll interval
    # even when nothing has changed — not useful at any log level.
    logging.getLogger("watchfiles").setLevel(logging.WARNING)
