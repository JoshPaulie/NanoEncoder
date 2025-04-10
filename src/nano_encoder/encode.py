import subprocess
import time
from pathlib import Path
from typing import List

from .utils import (
    CRF_MAX,
    CRF_MIN,
    VIDEO_FILE_EXTENSIONS,
    has_optimized_version,
    humanize_duration,
    humanize_file_size,
    print_log,
    validate_directory,
)
from .video_encoder import VideoEncoder


def handle_encode_command(args) -> None:
    try:
        validate_directory(args.directory)
        if not CRF_MIN <= args.crf <= CRF_MAX:
            raise ValueError(f"CRF must be between {CRF_MIN} and {CRF_MAX}")
        process_directory(args.directory.resolve(), args.crf)
    except (FileNotFoundError, NotADirectoryError, ValueError) as e:
        print_log(str(e), "error")
        raise


def _video_already_optimized(file_path: Path) -> bool:
    if has_optimized_version(file_path):
        print_log(f"'{file_path.name}' has optimized version. Skipping.")
        return True
    return False


def _find_video_files(directory: Path) -> List[Path]:
    print("Scanning directory for video files..", end="")
    video_files = []
    for ext in VIDEO_FILE_EXTENSIONS:
        video_files.extend(directory.rglob(f"*.{ext}"))

    video_files = [
        video
        for video in video_files
        if all(exclude not in video.name for exclude in ["optimized", "optimizing"])
        and not _video_already_optimized(video)
    ]

    print(f"found {len(video_files)} original video files.")
    print_log(f"Found {len(video_files)} original video files in '{directory.name}'", log_only=True)
    return video_files


def process_directory(directory: Path, crf: int) -> None:
    print_log(f"Starting processing for '{directory}'..")
    start_time = time.perf_counter()
    total_saved = 0
    video_files = _find_video_files(directory)

    for video in video_files:
        try:
            encoder = VideoEncoder(video, crf)
            encoder.encode()
            print_log(encoder.generate_report())
            total_saved += encoder.disk_space_change
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
