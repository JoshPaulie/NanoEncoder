import math
import random
import re
import subprocess
from pathlib import Path

from rich.progress import (
    Progress,
    SpinnerColumn,
    TaskProgressColumn,
    TextColumn,
    TimeElapsedColumn,
)

from .console import console
from .logger import DEBUG_LOG_FILE, logger
from .utils import find_all_video_files, has_optimized_version, validate_directory


def handle_health_command(args) -> None:
    try:
        HealthChecker(args.directory, args.sample_ratio, args.all).check_health()
    except (FileNotFoundError, NotADirectoryError, ValueError) as e:
        logger.error(str(e))
        raise
    except KeyboardInterrupt:
        message = "User cancelled healthcheck operation."
        console.print(message, end="\n\n")
        logger.info(message)


class HealthChecker:
    """Handles health check operations to validate optimized videos against their originals."""

    ProgressBar = Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        TaskProgressColumn(),
        TimeElapsedColumn(),
        expand=True,
    )

    def __init__(self, directory: Path, sample_ratio: float, process_all: bool = False) -> None:
        validate_directory(directory)
        self.directory = directory
        self.sample_ratio = sample_ratio
        self.process_all = process_all

    def _pair_videos(self) -> list[tuple[Path, Path]]:
        """
        Create pairs of original and optimized videos.
        Iterates over all original-only videos and finds their optimized counterparts.
        """
        pairs: list[tuple[Path, Path]] = []
        original_files = find_all_video_files(self.directory, originals_only=True)
        for original in original_files:
            if optimized_video := has_optimized_version(original):
                pairs.append((original, optimized_video))
        return pairs

    def _get_sample(self) -> list[tuple[Path, Path]]:
        """
        Sample a percentage of the paired videos to check.
        If process_all is True, returns all video pairs.
        Otherwise, sample_ratio is used to return a percentage of videos (1 minimum)
        """
        video_pairs = self._pair_videos()
        if self.process_all:
            return video_pairs

        sample_size = math.floor(len(video_pairs) * self.sample_ratio) or 1
        return random.choices(video_pairs, k=sample_size)

    def _grade_ssim(self, score: float) -> str:
        """Grades the SSIM score into descriptive text."""
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

    def _compare_videos_ssim(self, original_file: Path, optimized_file: Path) -> float:
        """Perform an SSIM comparison using ffmpeg between a original and optimized video."""
        command = [
            "ffmpeg",
            *["-i", str(original_file)],
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
            logger.error(f"Failed to compare {original_file.name} & {optimized_file.name}: {str(e)}")
            raise

        with open(DEBUG_LOG_FILE, "a") as log_file:
            log_file.write(process.stderr)

        matches = re.findall(r"All:(\d+\.\d+)", process.stderr)
        if not matches:
            raise ValueError("SSIM score not found in ffmpeg output")
        return float(matches[-1])

    def _all_done_message(self):
        console.print(f"\n[green]All done[/] checking the health of {self.directory}!")
        console.print("Your results can be viewed above, but also at:")
        console.print(DEBUG_LOG_FILE.absolute())

    def check_health(self) -> None:
        """Checks the health of optimized videos by comparing each original-optimized pair using SSIM."""
        sample = self._get_sample()

        with self.ProgressBar as progress:
            # Create "overall" progress bar for the entire directory
            overall_progress_id = progress.add_task(
                f"Performing healthcheck for {self.directory.name}. Sample size: {len(sample) if not self.process_all else 'all'}",
                total=len(sample),
            )

            for original_video, optimized_video in sample:
                current_pair = f"'{original_video.name}' & '{optimized_video.name}'"
                current_pair_progress_id = progress.add_task(f"Comparing {current_pair}..", total=None)
                # Get ssim value between the two
                logger.info(f"Starting SSIM comparison for {current_pair}.")

                # Perform compairson
                ssim = self._compare_videos_ssim(original_video, optimized_video)

                # Log result
                logger.info(f"{current_pair} = {ssim} SSIM")

                # Update video progress bars
                progress.update(current_pair_progress_id, total=1, completed=1)
                progress.update(
                    current_pair_progress_id,
                    description=f"{current_pair} are [green]{self._grade_ssim(ssim).lower()}[/] [{round(ssim, 3) * 100}%]",
                )
                # Advance overall progress bar
                progress.update(overall_progress_id, advance=1)

            progress.update(
                overall_progress_id,
                description=f"[green]Finished[/] performing healthcheck for {self.directory}",
            )

        self._all_done_message()
