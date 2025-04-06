import math
import random
import re
import subprocess
from pathlib import Path

from .utils import DEBUG_LOG_FILE, find_all_video_files, has_optimized_version, print_log, validate_directory


def handle_health_command(args) -> None:
    try:
        validate_directory(args.directory)
        check_directory_health(args.directory)
    except (FileNotFoundError, NotADirectoryError, ValueError) as e:
        print_log(str(e), "error")
        raise


def pair_videos(directory: Path) -> list[tuple[Path, Path]]:
    pairs: list[tuple[Path, Path]] = []
    source_videos_files = find_all_video_files(directory, source_only=True)
    for source_video in source_videos_files:
        if optimized_video := has_optimized_version(source_video):
            pairs.append((source_video, optimized_video))
    return pairs


# todo: sample size needs to be an arg, probably an int
def get_sample(directory: Path, sample_size: float = 0.5):
    """
    sample_size: % of directory we'd like to check
    """
    video_pairs = pair_videos(directory)
    size_for_pairs = math.floor(len(video_pairs) * sample_size) or 1
    sample = random.choices(video_pairs, k=size_for_pairs)
    return sample


def check_directory_health(directory: Path):
    sample = get_sample(directory)
    for source_video, optimized_video in sample:
        print_log(f"Checking the health of '{source_video.name}' & '{optimized_video.name}'..")
        result = ssim_compare_videos(source_video, optimized_video)
        print(f"'{source_video.name}' & '{optimized_video.name}' = {round(result, 3) * 100}%")


def ssim_compare_videos(source_file: Path, optimized_file: Path) -> float:
    command = [
        "ffmpeg",
        *["-i", str(source_file)],
        *["-i", str(optimized_file)],
        *["-lavfi", "[0:v][1:v]ssim=stats_file=-"],
        *["-f", "null", "-"],
    ]

    try:
        process = subprocess.run(
            command,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.PIPE,
            text=True,
            check=True,
        )
    except (subprocess.CalledProcessError, FileNotFoundError) as e:
        print_log(f"Failed to compare {source_file.name} & {optimized_file.name}: {str(e)}", "error")

    with open(DEBUG_LOG_FILE, "a") as log_file:
        log_file.write(process.stderr)

    matches = re.findall(r"All:(\d+\.\d+)", process.stderr)
    return float(matches[-1])
