import math
import subprocess
from pathlib import Path

from .exceptions import EmptyDirectory

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
    Check if original video has accompanying optimized video, and return it if so
    """
    optimized_path = file_path.with_stem(f"{file_path.stem}.optimized")
    if optimized_path.exists():
        return optimized_path
    return None


def find_all_video_files(
    directory: Path,
    originals_only: bool = False,
    optimized_only: bool = False,
) -> list[Path]:
    if all([optimized_only, originals_only]):
        # can't be both
        raise Exception  # todo

    video_files: list[Path] = []
    for ext in VIDEO_FILE_EXTENSIONS:
        video_files.extend(directory.rglob(f"*.{ext}"))

    video_files = sorted(video_files)

    if originals_only:
        video_files = [video for video in video_files if ".optimized" not in video.name]

    if optimized_only:
        video_files = [video for video in video_files if ".optimized" in video.name]

    return video_files


def directory_fully_processed(directory: Path):
    video_files = find_all_video_files(directory, originals_only=True)
    for video in video_files:
        if not has_optimized_version(video):
            return False
    return True


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


def shorten_path(file_path: Path, length: int):
    return Path(*Path(file_path).parts[-length:])
