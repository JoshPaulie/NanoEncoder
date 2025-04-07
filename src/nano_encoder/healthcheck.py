import math
import random
import re
import subprocess
from pathlib import Path

from .logger import DEBUG_LOG_FILE, logger
from .utils import find_all_video_files, has_optimized_version, validate_directory


def handle_health_command(args) -> None:
    try:
        validate_directory(args.directory)
        check_directory_health(args.directory, args.sample_ratio)
    except (FileNotFoundError, NotADirectoryError, ValueError) as e:
        logger.error(str(e))
        raise


def _pair_videos(directory: Path) -> list[tuple[Path, Path]]:
    pairs: list[tuple[Path, Path]] = []
    source_videos_files = find_all_video_files(directory, source_only=True)
    for source_video in source_videos_files:
        if optimized_video := has_optimized_version(source_video):
            pairs.append((source_video, optimized_video))
    return pairs


def _get_sample(directory: Path, sample_ratio: float) -> list[tuple[Path, Path]]:
    """
    sample_size: % of directory we'd like to check
    """
    video_pairs = _pair_videos(directory)
    sample_size = math.floor(len(video_pairs) * sample_ratio) or 1
    sample = random.choices(video_pairs, k=sample_size)
    return sample


def _grade_ssim(score: float) -> str:
    if score == 1.0:
        return "Identical"
    elif score >= 0.99:
        return "Excellent (visually identical)"
    elif score >= 0.97:
        return "Very Good (nearly indistinguishable)"
    elif score >= 0.95:
        return "Good (minor perceptual differences)"
    elif score >= 0.90:
        return "Fair (noticeable but acceptable loss)"
    elif score >= 0.85:
        return "Poor (visible degradation)"
    elif score >= 0.70:
        return "Bad (significant artifacts)"
    elif score >= 0.50:
        return "Very Bad (low fidelity)"
    elif score >= 0.30:
        return "Unusable (heavily degraded)"
    elif score >= 0.10:
        return "Broken (barely recognizable)"
    else:
        return "Garbage (not visually usable)"


def check_directory_health(directory: Path, sample_ratio: float):
    sample = _get_sample(directory, sample_ratio)
    for source_video, optimized_video in sample:
        print(f"Checking the health of '{source_video.name}' & '{optimized_video.name}'..")
        logger.info(f"Begging SSIM comparison for '{source_video.name}' & '{optimized_video.name}'.")
        ssim = _compare_videos_ssim(source_video, optimized_video)
        logger.info(f"'{source_video.name}' & '{optimized_video.name}' = {ssim} SSIM", log_only=True)
        print(
            (
                f"'{source_video.name}' & '{optimized_video.name}' are "
                f"{_grade_ssim(ssim).lower()} [{round(ssim, 3) * 100}%]"
            )
        )


def _compare_videos_ssim(source_file: Path, optimized_file: Path) -> float:
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
        logger.error(f"Failed to compare {source_file.name} & {optimized_file.name}: {str(e)}")

    with open(DEBUG_LOG_FILE, "a") as log_file:
        log_file.write(process.stderr)

    matches = re.findall(r"All:(\d+\.\d+)", process.stderr)

    if not matches:
        raise ValueError("SSIM score not found in ffmpeg output")
    return float(matches[-1])
