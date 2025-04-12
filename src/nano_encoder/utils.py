import math
from pathlib import Path

from .exceptions import EmptyDirectory

# --- Constants ---
VIDEO_FILE_EXTENSIONS: list[str] = ["mov", "mkv", "mp4"]
CRF_MIN: int = 0
CRF_MAX: int = 51


# --- Utility Functions ---
def humanize_duration(seconds: float) -> str:
    """
    Converts seconds to hours, minutes & seconds, pretty much divmod() but for floats
    """
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    seconds = math.floor(seconds % 60)

    if hours:
        return f"{hours}h {minutes}m {seconds}s"
    return f"{minutes}m {seconds}s"


def humanize_file_size(size_bytes: int) -> str:
    """
    Convert bytes to KB, MB, and GB.
    """
    if size_bytes < 0:
        raise ValueError("File size cannot be negative")
    size = float(size_bytes)
    units = ["bytes", "KB", "MB", "GB"]
    for unit in units:
        if size < 1024:
            break
        if unit != units[-1]:
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
    if not any(path.iterdir()):
        raise EmptyDirectory(f"{path} is an empty directory")


def has_optimized_version(file_path: Path) -> None | Path:
    """
    Check if source video has accompanying optimized video, and return it if so
    """
    optimized_path = file_path.with_stem(f"{file_path.stem}.optimized")
    if optimized_path.exists():
        return optimized_path
    return None


def find_all_video_files(directory: Path, source_only: bool = False) -> list[Path]:
    video_files: list[Path] = []
    for ext in VIDEO_FILE_EXTENSIONS:
        video_files.extend(directory.rglob(f"*.{ext}"))

    if source_only:
        video_files = [video for video in video_files if "optimized" not in video.name]

    return video_files


def directory_fully_processed(directory: Path):
    video_files = find_all_video_files(directory, source_only=True)
    for video in video_files:
        if not has_optimized_version(video):
            return False
    return True
