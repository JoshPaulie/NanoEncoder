import math
import subprocess
from pathlib import Path

from .exceptions import EmptyDirectoryError

# --- Constants ---
VIDEO_FILE_EXTENSIONS: list[str] = ["mov", "mkv", "mp4"]


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
        msg = "File size cannot be negative"
        raise ValueError(msg)
    size = float(size_bytes)
    units = ["bytes", "KB", "MB", "GB"]
    bytes_in_kib = 1024
    for unit in units:
        if size < bytes_in_kib:
            break
        if unit != units[-1]:
            size /= bytes_in_kib
    return f"{size:.2f} {unit}" if unit != "bytes" else f"{int(size)} {unit}"


def validate_directory(path: Path) -> None:
    """
    User validation for passed directory
    """
    if not path.exists():
        msg = f"Directory {path} does not exist"
        raise FileNotFoundError(msg)
    if not path.is_dir():
        msg = f"{path} is not a directory"
        raise NotADirectoryError(msg)
    if not any(path.iterdir()):
        msg = f"{path} is an empty directory"
        raise EmptyDirectoryError(msg)


def has_optimized_version(file_path: Path) -> None | Path:
    """
    Check if original video has accompanying optimized video, and return it if so
    """
    optimized_path = file_path.with_stem(f"{file_path.stem}.optimized")
    if optimized_path.exists():
        return optimized_path
    return None


def find_all_video_files(
    directory: Path,
    *,
    originals_only: bool = False,
    optimized_only: bool = False,
) -> list[Path]:
    """Collect all files of given directory."""
    if all([optimized_only, originals_only]):
        # can't be both
        msg = "Cannot specify both 'originals_only' and 'optimized_only'."
        raise ValueError(msg)

    video_files: list[Path] = []
    for ext in VIDEO_FILE_EXTENSIONS:
        video_files.extend(directory.rglob(f"*.{ext}"))

    video_files = sorted(video_files)

    if originals_only:
        video_files = [video for video in video_files if ".optimized" not in video.name]

    if optimized_only:
        video_files = [video for video in video_files if ".optimized" in video.name]

    return video_files


def directory_fully_processed(directory: Path) -> bool:
    """Predicate for if directory is fully processed."""
    video_files = find_all_video_files(directory, originals_only=True)
    return all(has_optimized_version(video) for video in video_files)


def get_video_duration(video: Path) -> float:
    """Get video duration (in seconds) using ffprobe."""
    result = subprocess.run(
        [
            "ffprobe",
            *["-i", str(video)],
            *["-show_entries", "format=duration"],
            *["-v", "quiet"],
            *["-of", "csv=p=0"],
        ],
        capture_output=True,
        text=True,
        check=True,
    )
    return float(result.stdout.strip())


def get_video_resolution(video: Path) -> str:
    """Get video resolution, returned in '1920x1080' format using ffprobe."""
    result = subprocess.run(
        [
            "ffprobe",
            *["-i", str(video)],
            *["-select_streams", "v:0"],
            *["-show_entries", "stream=width,height"],
            *["-v", "quiet"],
            *["-of", "csv=s=x:p=0"],
        ],
        capture_output=True,
        text=True,
        check=True,
    )
    return result.stdout.strip()


def get_video_codec(video: Path) -> str:
    """Get video codec using ffprobe."""
    result = subprocess.run(
        [
            "ffprobe",
            *["-i", str(video)],
            *["-select_streams", "v:0"],
            *["-show_entries", "stream=codec_name"],
            *["-v", "quiet"],
            *["-of", "csv=p=0"],
        ],
        capture_output=True,
        text=True,
        check=True,
    )
    return result.stdout.strip()


def shorten_path(file_path: Path, length: int) -> Path:
    """Truncate a given path."""
    return Path(*Path(file_path).parts[-length:])
