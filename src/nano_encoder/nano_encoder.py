import argparse
import logging
import platform
import shutil
import subprocess
import sys
import time
from pathlib import Path
from typing import Literal

# --- Constants ---
VIDEO_FILE_EXTENSIONS = ["mov", "mkv", "mp4"]
CRF_MIN = 0
CRF_MAX = 51

# --- Logging Setup ---
NANO_ENCODER_LOG_FILE = Path.cwd() / "NanoEncoder.log"
DEBUG_LOG_FILE = Path.cwd() / "NanoEncoder_ffmpeg.log"

logger = logging.getLogger("NanoEncoder")
logger.setLevel(logging.INFO)
file_handler = logging.FileHandler(NANO_ENCODER_LOG_FILE)
formatter = logging.Formatter("%(asctime)s - %(levelname)-8s - %(message)s")
file_handler.setFormatter(formatter)
logger.addHandler(file_handler)


# --- Argument Parser ---
def create_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="NanoEncoder",
        description="Video encoder for reducing video file sizes",
        epilog="Please report any bugs to https://github.com/JoshPaulie/NanoEncoder/issues",
    )

    subparsers = parser.add_subparsers(dest="command", required=True)

    # Encode subcommand
    encode_parser = subparsers.add_parser("encode", help="Encode video files")
    encode_parser.add_argument("directory", type=Path, help="Path to the target directory")
    encode_parser.add_argument(
        "--crf",
        type=int,
        default=23,
        help=f"Constant rate factor ({CRF_MIN}-{CRF_MAX}, default: %(default)s)",
    )

    # Purge subcommand
    purge_parser = subparsers.add_parser(
        "purge", help="Purge (delete) original video files which have accompanying optimized version"
    )
    purge_parser.add_argument("directory", type=Path, help="Path to the target directory")

    return parser


# --- Utility Functions ---
def print_log(
    message: str | list[str], log_level: Literal["error", "info"] = "info", log_only: bool = False
) -> None:
    """Log and print messages with specified log level."""
    if isinstance(message, list):
        message = " ".join(message)

    getattr(logger, log_level)(message)

    if not log_only:
        print(message)


def humanize_duration(seconds: float) -> str:
    """Convert seconds to human-readable minutes/seconds format."""
    minutes = int(seconds // 60)
    seconds = int(round(seconds % 60))
    return f"{minutes}m {seconds}s"


def humanize_file_size(size_bytes: int) -> str:
    """Convert file size to human-readable format."""
    if size_bytes < 0:
        raise ValueError("File size cannot be negative")

    size = float(size_bytes)
    units = ["bytes", "KB", "MB", "GB"]

    for unit in units[:-1]:
        if size < 1024:
            break
        size /= 1024

    if unit == "bytes":
        return f"{int(size)} {unit}"
    return f"{size:.2f} {unit}"


def validate_directory(path: Path) -> None:
    """Validate directory exists and is accessible."""
    if not path.exists():
        raise FileNotFoundError(f"Directory {path} does not exist")
    if not path.is_dir():
        raise NotADirectoryError(f"{path} is not a directory")


def _has_optimized_version(file_path: Path) -> bool:
    """Check if optimized version exists (without logging)"""
    optimized_path = file_path.with_name(f"{file_path.stem}.optimized{file_path.suffix}")
    return optimized_path.exists()


# --- Video Processing ---
class VideoEncoder:
    """Handles video encoding operations using ffmpeg."""

    def __init__(self, video_file: Path, crf: int) -> None:
        self.input_file = video_file
        self.crf = crf
        self.output_file = self._create_output_path()
        self.encoding_duration = 0.0
        self.space_saved = 0

    def _create_output_path(self) -> Path:
        """Create output path with 'optimizing' status marker."""
        return self.input_file.with_name(f"{self.input_file.stem}.optimizing{self.input_file.suffix}")

    def encode(self) -> None:
        """Perform video encoding and post-processing."""
        self._run_ffmpeg()
        self._validate_output()
        self._rename_final_output()

    def _run_ffmpeg(self) -> None:
        """Execute ffmpeg command with configured parameters."""
        command = [
            "ffmpeg",
            *["-i", str(self.input_file)],
            *["-c:v", "libx265"],
            *["-crf", str(self.crf)],
            *["-preset", "fast"],
            *["-threads", "0"],
            *["-c:a", "copy"],
            *["-c:s", "copy"],
            *["-loglevel", "error"],
            str(self.output_file),
        ]

        print_log(f"Starting encoding for '{self.input_file}'")
        start_time = time.perf_counter()

        with open(DEBUG_LOG_FILE, "a") as log_file:
            subprocess.run(command, stdout=log_file, stderr=log_file, text=True, check=True)

        self.encoding_duration = time.perf_counter() - start_time

    def _validate_output(self) -> None:
        """Validate encoding results and calculate savings."""
        if not self.output_file.exists():
            raise FileNotFoundError("Encoded file not created")

        original_size = self.input_file.stat().st_size
        encoded_size = self.output_file.stat().st_size
        self.space_saved = original_size - encoded_size

    def _rename_final_output(self) -> None:
        """Rename temporary output file to final name."""
        final_name = self.output_file.with_name(self.output_file.name.replace("optimizing", "optimized"))
        self.output_file.rename(final_name)
        self.output_file = final_name

    def generate_report(self) -> list[str]:
        """Generate encoding results report."""
        original_size = self.input_file.stat().st_size
        encoded_size = self.output_file.stat().st_size
        speed_factor = self._get_video_duration() / self.encoding_duration

        return [
            f"Finished encoding '{self.input_file.name}'.",
            f"Duration: {humanize_duration(self.encoding_duration)} ({speed_factor:.2f}x).",
            f"Size: {humanize_file_size(original_size)} → {humanize_file_size(encoded_size)}.",
            f"Disk space: {humanize_file_size(abs(self.space_saved))} "
            f"({'saved' if self.space_saved > 0 else 'increased'}).",
        ]

    def _get_video_duration(self) -> float:
        """Get video duration using ffprobe."""
        result = subprocess.run(
            [
                "ffprobe",
                *["-i", str(self.input_file)],
                *["-show_entries", "format=duration"],
                *["-v", "quiet"],
                *["-of", "csv=p=0"],
            ],
            capture_output=True,
            text=True,
            check=True,
        )
        return float(result.stdout.strip())


def _check_and_log_optimized(file_path: Path) -> bool:
    """Check+log optimized version (for encode command)"""
    if _has_optimized_version(file_path):
        print_log(f"'{file_path.name}' has optimized version. Skipping.")
        return True
    return False


def _find_video_files(directory: Path) -> list[Path]:
    """Find videos needing encoding"""
    print("Scanning directory for video files..", end="")
    video_files = []
    for ext in VIDEO_FILE_EXTENSIONS:
        video_files.extend(directory.rglob(f"*.{ext}"))
    print_log(f"found {len(video_files)} video files.\n")
    return [f for f in video_files if "optimized" not in f.name and not _check_and_log_optimized(f)]


def process_directory(directory: Path, crf: int) -> None:
    """Process all video files in directory."""
    print_log(f"Starting processing for '{directory}'")
    start_time = time.perf_counter()
    total_saved = 0
    video_files = _find_video_files(directory)

    for video in video_files:
        # Handle partially encoded files
        if "optimizing" in video.name:
            print_log(f"Encountered unfinished file: '{video.name}'. Deleting.")
            video.unlink()
            continue

        try:
            encoder = VideoEncoder(video, crf)
            encoder.encode()
            print_log(encoder.generate_report())
            total_saved += encoder.space_saved
        except (subprocess.CalledProcessError, FileNotFoundError) as e:
            print_log(f"Failed to process {video}: {str(e)}", "error")

    duration = time.perf_counter() - start_time

    report = [
        f"Completed processing '{directory}'.",
        f"Total duration: {humanize_duration(duration)}.",
        f"Total disk space: {humanize_file_size(abs(total_saved))} "
        f"({'saved' if total_saved > 0 else 'increased'}).",
    ]
    print()
    print_log(report)


# --- Purge Originals Implementation ---
def _find_all_video_files(directory: Path) -> list[Path]:
    """Find all video files without optimization checks"""
    video_files = []
    for ext in VIDEO_FILE_EXTENSIONS:
        video_files.extend(directory.rglob(f"*.{ext}"))
    return [f for f in video_files if "optimized" not in f.name and "optimizing" not in f.name]


def _find_originals_to_purge(directory: Path) -> list[Path]:
    """Find original files that have optimized versions"""
    candidates = []
    for ext in VIDEO_FILE_EXTENSIONS:
        candidates.extend(directory.rglob(f"*.{ext}"))

    originals = []
    for file in candidates:
        if "optimized" not in file.name and _has_optimized_version(file):
            originals.append(file)
    return originals


def _has_unfinished_video(directory: Path) -> Path | None:
    videos = _find_all_video_files(directory)
    for video in videos:
        if ".optimizing." in video.name:
            return video
    return None


def purge_originals(directory: Path):
    """Purge (delete) original files that have optimized versions"""
    if unfinished_video := _has_unfinished_video(directory):
        print_log(
            f"Encountered unfinished video: '{unfinished_video}', unable to purge originals. Remove this file, or re-run the encode command against the directory to resolve.",
            "error",
        )
        print(f"Suggested fix:\nnen encode {directory}")
        return

    originals = _find_originals_to_purge(directory)

    if not originals:
        print_log(f"No originals with optimized versions found in '{directory.name}'")
        return

    print_log(f"Found the following to purge: {', '.join([p.name for p in originals])}", log_only=True)
    print(f"Found {len(originals)} originals with optimized versions:")
    for orig in originals:
        print(f" - {orig.name} -> {(orig.with_name(f"{orig.stem}.optimized{orig.suffix}")).name}")
    print()

    confirm = input("Confirm deletion of these ORIGINAL files? (Cannot be undone) [y/n]: ").lower()
    if confirm != "y":
        print_log("Deletion cancelled by user.")
        return

    for orig in originals:
        print(f"Deleting '{orig}'.")
        print_log(f"Purged '{orig}'.", log_only=True)
        orig.unlink()

    print_log(f"Purged {len(originals)} original files")


# --- Command Handlers ---
def handle_encode_command(args: argparse.Namespace) -> None:
    """Handle the encode subcommand"""
    try:
        validate_directory(args.directory)
        if not CRF_MIN <= args.crf <= CRF_MAX:
            raise ValueError(f"CRF must be between {CRF_MIN} and {CRF_MAX}")

        process_directory(args.directory.resolve(), args.crf)
    except (FileNotFoundError, NotADirectoryError, ValueError) as e:
        print_log(str(e), "error")
        raise  # Re-raise to handle exit code in main


def handle_purge_command(args: argparse.Namespace) -> None:
    """Handle the purge subcommand"""
    purge_originals(args.directory)


# --- Main Execution ---
def welcome_message():
    print()
    print("Welcome to NanoEncoder!")
    print()


def ffmpeg_check():
    required_apps = ["ffmpeg", "ffprobe"]
    for app in required_apps:
        if shutil.which(app) is None:
            print_log(f"NanoEncoder depends on {app}, which is not installed on this system.", "error")
            print("Install from here: https://www.ffmpeg.org/download.html")
            sys.exit(1)


def main() -> None:
    parser = create_parser()
    args = parser.parse_args()

    welcome_message()
    ffmpeg_check()

    try:
        if args.command == "encode":
            handle_encode_command(args)
        elif args.command == "purge":
            handle_purge_command(args)
    except Exception as e:
        parser.exit(1, str(e) + "\n")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print()
