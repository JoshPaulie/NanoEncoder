import math
import random
import re
import subprocess
from pathlib import Path

from rich import box
from rich.progress import (
    BarColumn,
    Progress,
    SpinnerColumn,
    TaskProgressColumn,
    TextColumn,
    TimeElapsedColumn,
)
from rich.table import Table
from rich.text import Text

from ..console import console
from ..logger import DEBUG_LOG_FILE, logger
from ..utils import find_all_video_files, has_optimized_version, humanize_file_size, validate_directory


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
        BarColumn(),
        TextColumn("{task.completed}/{task.total}"),
        TaskProgressColumn(),
        TimeElapsedColumn(),
        expand=True,
        console=console,
    )

    health_table = Table(box=box.ASCII, show_lines=True)
    health_table.add_column("Original")
    health_table.add_column("Optimized")
    health_table.add_column("SSIM")
    health_table.add_column("Grade")
    health_table.add_column("Size diff")  # + / -
    health_table.caption = f"Also logged at {DEBUG_LOG_FILE.absolute()}"

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
        if not pairs:
            raise FileNotFoundError(f"'{self.directory}' directory doesn't have any pairs to compare.")
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

    def check_health(self) -> None:
        """Checks the health of optimized videos by comparing each original-optimized pair using SSIM."""
        sample = self._get_sample()

        with self.ProgressBar as progress:
            # Create "overall" progress bar for the entire directory
            overall_progress_id = progress.add_task(
                f"Performing healthcheck for [blue]{self.directory.name}[/]..",
                total=len(sample),
            )

            for original_video, optimized_video in sample:
                # String name for pair
                current_pair = f"'{original_video.name}' & '{optimized_video.name}'"

                # Perform compairson
                logger.info(f"Starting SSIM comparison for {current_pair}.")
                ssim = self._compare_videos_ssim(original_video, optimized_video)
                logger.info(f"{current_pair} = {ssim} SSIM")

                # Size column
                size_diff = optimized_video.stat().st_size - original_video.stat().st_size
                diff_sign = "+" if size_diff >= 0 else "-"
                ssim_grade, healthcolor = self._grade_ssim(ssim)

                self.health_table.add_row(
                    Text(original_video.name),
                    Text(optimized_video.name),
                    Text(str(round(ssim, 3))),
                    Text(ssim_grade),
                    Text(diff_sign + humanize_file_size(abs(size_diff))),
                    style="red" if size_diff >= 0 else healthcolor,
                )

                progress.update(overall_progress_id, advance=1)

            progress.update(
                overall_progress_id,
                description=f"[green]Finished[/] performing healthcheck for {self.directory}",
            )

        console.print(self.health_table)

    @staticmethod
    def _grade_ssim(score: float) -> tuple[str, str]:
        """Grades the SSIM score into descriptive text."""
        score = round(score, 3)
        if score == 1.0:
            return "Identical", "green"
        elif score >= 0.998:
            return "Excellent (visually identical)", "green"
        elif score >= 0.996:
            return "Good (nearly indistinguishable)", "green"
        elif score >= 0.994:
            return "OK (subtle artifacts)", "yellow"
        elif score >= 0.992:
            return "Fair (minor artifacts)", "yellow"
        elif score >= 0.990:
            return "Poor (noticeable artifacts)", "red"
        else:
            return "Garbage (not visually usable)", "red"
