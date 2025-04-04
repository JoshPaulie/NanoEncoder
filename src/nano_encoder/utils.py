import logging
import math
from pathlib import Path
from typing import List, Literal

# --- Constants ---
VIDEO_FILE_EXTENSIONS: List[str] = ["mov", "mkv", "mp4"]
CRF_MIN: int = 0
CRF_MAX: int = 51

# --- Logging Setup ---
NANO_ENCODER_LOG_FILE: Path = Path.cwd() / "NanoEncoder.log"
DEBUG_LOG_FILE: Path = Path.cwd() / "NanoEncoder_ffmpeg.log"

logger: logging.Logger = logging.getLogger("NanoEncoder")
logger.setLevel(logging.INFO)
file_handler: logging.FileHandler = logging.FileHandler(NANO_ENCODER_LOG_FILE)
formatter: logging.Formatter = logging.Formatter("%(asctime)s - %(levelname)-8s - %(message)s")
file_handler.setFormatter(formatter)
logger.addHandler(file_handler)


# --- Utility Functions ---
def print_log(
    message: str | List[str],
    log_level: Literal["error", "info"] = "info",
    log_only: bool = False,
) -> None:
    """
    Helper for when information needs relayed to use and logged
    """
    if isinstance(message, list):
        message = " ".join(message)

    getattr(logger, log_level)(message)

    if not log_only:
        print(message)


def humanize_duration(seconds: float) -> str:
    """
    Converts seconds to minutes & seconds, pretty much divmod() but for floats
    """
    minutes = seconds // 60
    seconds = math.floor(seconds % 60)
    return f"{minutes}m {seconds}s"


def humanize_file_size(size_bytes: int) -> str:
    """
    Convert bytes to KB, MB, and GB.
    """
    if size_bytes < 0:
        raise ValueError("File size cannot be negative")
    size = float(size_bytes)
    units = ["bytes", "KB", "MB", "GB"]
    for unit in units[:-1]:
        if size < 1024:
            break
        size /= 1024
    return f"{size:.2f} {unit}" if unit != "bytes" else f"{int(size)} {unit}"


def validate_directory(path: Path) -> None:
    """
    User validation for passed directory
    """
    if not path.exists():
        raise FileNotFoundError(f"Directory {path} does not exist")
    if not path.is_dir():
        raise NotADirectoryError(f"{path} is not a directory")


def has_optimized_version(file_path: Path) -> bool:
    """
    Predicate to see if source video has accompanying optimized video
    """
    optimized_path = file_path.with_name(f"{file_path.stem}.optimized{file_path.suffix}")
    return optimized_path.exists()
