"""
NanoEncoder Logging Configuration

This module provides OS-specific logging with the following default locations:
- macOS: ~/Library/Logs/NanoEncoder/
- Windows: %LOCALAPPDATA%/NanoEncoder/logs/
- Linux: ~/.local/share/NanoEncoder/logs/

The log directory can be overridden using the NEN_LOG_DIR environment variable.

Log files:
- NanoEncoder.log: Main application log
- NanoEncoder_ffmpeg.log: FFmpeg command output and debugging
"""

import logging
import os
import platform
from pathlib import Path


def get_default_log_directory() -> Path:
    """Get the default log directory based on the operating system."""
    system = platform.system()

    if system == "Darwin":  # macOS
        return Path.home() / "Library" / "Logs" / "NanoEncoder"

    if system == "Windows":
        # Use LOCALAPPDATA if available, otherwise fallback to user profile
        local_app_data = os.environ.get("LOCALAPPDATA")
        if local_app_data:
            return Path(local_app_data) / "NanoEncoder" / "logs"
        return Path.home() / "AppData" / "Local" / "NanoEncoder" / "logs"

    # Linux and other Unix-like systems
    # Follow XDG Base Directory Specification
    xdg_data_home = os.environ.get("XDG_DATA_HOME")
    if xdg_data_home:
        return Path(xdg_data_home) / "NanoEncoder" / "logs"
    return Path.home() / ".local" / "share" / "NanoEncoder" / "logs"


def get_log_directory() -> Path:
    """Get the log directory, respecting the NEN_LOG_DIR environment variable."""
    env_log_dir = os.environ.get("NEN_LOG_DIR")
    if env_log_dir:
        return Path(env_log_dir)
    return get_default_log_directory()


# Ensure log directory exists
LOG_DIR = get_log_directory()
LOG_DIR.mkdir(parents=True, exist_ok=True)

# Define log file paths
NANO_ENCODER_LOG_FILE: Path = LOG_DIR / "NanoEncoder.log"
FFMPEG_LOG_FILE: Path = LOG_DIR / "NanoEncoder_ffmpeg.log"


class NanoEncoderLogger:
    """Custom logger wrapper that handles string and list messages."""

    def __init__(self, name: str = "NanoEncoder") -> None:
        self._logger = logging.getLogger(name)
        self._logger.setLevel(logging.INFO)

    def _stringify(self, msg: str | list[str]) -> str:
        """Convert message to string, joining lists with spaces."""
        if isinstance(msg, list):
            return " ".join(str(m) for m in msg)
        return str(msg)

    def debug(self, msg: str | list[str], *args: object, **kwargs: object) -> None:
        """Log a debug message."""
        self._logger.debug(self._stringify(msg), *args, **kwargs)  # type: ignore[arg-type]

    def info(self, msg: str | list[str], *args: object, **kwargs: object) -> None:
        """Log an info message."""
        self._logger.info(self._stringify(msg), *args, **kwargs)  # type: ignore[arg-type]

    def warning(self, msg: str | list[str], *args: object, **kwargs: object) -> None:
        """Log a warning message."""
        self._logger.warning(self._stringify(msg), *args, **kwargs)  # type: ignore[arg-type]

    def error(self, msg: str | list[str], *args: object, **kwargs: object) -> None:
        """Log an error message."""
        self._logger.error(self._stringify(msg), *args, **kwargs)  # type: ignore[arg-type]

    def critical(self, msg: str | list[str], *args: object, **kwargs: object) -> None:
        """Log a critical message."""
        self._logger.critical(self._stringify(msg), *args, **kwargs)  # type: ignore[arg-type]

    def set_level(self, level: int) -> None:
        """Set the logging level."""
        self._logger.setLevel(level)

    def add_handler(self, handler: logging.Handler) -> None:
        """Add a handler to the logger."""
        self._logger.addHandler(handler)


# Configure logging
logger = NanoEncoderLogger("NanoEncoder")

# File handler
file_handler = logging.FileHandler(NANO_ENCODER_LOG_FILE, encoding="utf-8")
formatter = logging.Formatter("%(asctime)s - %(levelname)-8s - %(message)s")
file_handler.setFormatter(formatter)
logger.add_handler(file_handler)
