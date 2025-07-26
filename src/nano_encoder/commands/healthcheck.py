import argparse
import math
import random
import re
import subprocess
from dataclasses import dataclass
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

from nano_encoder.console import console
from nano_encoder.logger import DEBUG_LOG_FILE, logger
from nano_encoder.utils import find_all_video_files, get_video_resolution, has_optimized_version, humanize_file_size

from .base_command import BaseCommand

# Constants for better maintainability
DEFAULT_SAMPLE_RATIO = 0.05
MINIMUM_SAMPLE_SIZE = 1
SSIM_EXCELLENT_THRESHOLD = 0.990
SSIM_GOOD_THRESHOLD = 0.980
FFMPEG_SSIM_PATTERN = r"All:(\d+\.\d+)"


@dataclass
class HealthArgs:
    """
    Arguments for health check operations.

    Attributes:
        directory: Directory containing video pairs to analyze
        sample_ratio: Fraction of video pairs to sample for analysis (0.0-1.0)
        all: Whether to analyze all video pairs instead of sampling

    """

    directory: Path
    sample_ratio: float = DEFAULT_SAMPLE_RATIO
    all: bool = False


def handle_health_command(args: argparse.Namespace) -> None:
    """
    Handle health check command execution with comprehensive error handling.

    Args:
        args: Parsed command line arguments containing health check parameters

    Raises:
        FileNotFoundError: If the specified directory doesn't exist
        NotADirectoryError: If the path exists but isn't a directory
        ValueError: If invalid arguments are provided

    """
    health_args = HealthArgs(
        directory=args.directory,
        sample_ratio=args.sample_ratio,
        all=args.all,
    )

    try:
        HealthChecker(health_args).execute()
    except (FileNotFoundError, NotADirectoryError, ValueError) as e:
        logger.error(f"Health check failed: {e}")
        raise
    except KeyboardInterrupt:
        message = "User cancelled health check operation"
        console.print(f"\n[yellow]{message}[/]\n")
        logger.info(message)
        raise


class HealthChecker(BaseCommand):
    """
    Analyzes video quality and compression efficiency through SSIM comparison.

    This class compares original videos with their optimized counterparts using
    Structural Similarity Index Measure (SSIM) to assess quality preservation
    and file size changes.
    """

    # Shared progress bar configuration for health check operations
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

    def __init__(self, args: HealthArgs) -> None:
        """
        Initialize health checker with the provided arguments.

        Args:
            args: Configuration parameters for the health check process

        """
        super().__init__(args.directory)

        # Analysis configuration
        self.sample_ratio = args.sample_ratio
        self.process_all = args.all

        # Results tracking
        self.sample = self._get_sample()
        self.health_table = self._create_results_table()

    def _create_results_table(self) -> Table:
        """
        Create and configure the results table for displaying comparison data.

        Returns:
            Table: Configured Rich table for displaying health check results

        """
        table = Table(box=box.ASCII, show_lines=True)
        table.add_column("Original")
        table.add_column("Optimized")
        table.add_column("SSIM")
        table.add_column("Size diff")
        table.caption = f"Detailed logs available at {DEBUG_LOG_FILE.absolute()}"
        return table

    def execute(self) -> None:
        """Execute comprehensive health check analysis."""
        if not self.sample:
            console.print("No video pairs found for health check analysis.")
            return

        logger.info(f"Starting health check for {len(self.sample)} video pair(s)")

        with self.ProgressBar as progress:
            overall_progress_id = progress.add_task(
                f"Analyzing video quality for [blue]{self.directory.name}[/]",
                total=len(self.sample),
            )

            for original_video, optimized_video in self.sample:
                self._check_video_pair(original_video, optimized_video)
                progress.update(overall_progress_id, advance=1)

            progress.update(
                overall_progress_id,
                description=f"[green]Completed[/] health check for {self.directory.name}",
            )

        self._display_results()

    def _display_results(self) -> None:
        """Display the health check results table."""
        console.print()
        console.print(self.health_table)
        console.print()

    def _check_video_pair(self, original_video: Path, optimized_video: Path) -> None:
        """
        Compare an original-optimized video pair using SSIM analysis.

        Args:
            original_video: Path to the original video file
            optimized_video: Path to the optimized video file

        """
        pair_description = f"'{original_video.name}' & '{optimized_video.name}'"
        size_diff = optimized_video.stat().st_size - original_video.stat().st_size
        size_diff_text = self._format_size_difference(size_diff)

        # Handle resolution mismatch case
        if not self._is_same_resolution(original_video, optimized_video):
            self._add_resolution_mismatch_row(original_video, optimized_video)
            return

        # Perform SSIM comparison
        logger.info(f"Starting SSIM comparison for {pair_description}")
        try:
            ssim_score = self._compare_videos_ssim(original_video, optimized_video)
            logger.info(f"{pair_description} SSIM score: {ssim_score:.3f}")

            health_color = self._ssim_health_color(ssim_score)
            row_style = "red" if size_diff >= 0 else health_color

            self.health_table.add_row(
                Text(original_video.name),
                Text(optimized_video.name),
                Text(str(round(ssim_score, 3))),
                Text(size_diff_text),
                style=row_style,
            )
        except (subprocess.CalledProcessError, ValueError) as e:
            logger.error(f"Failed to analyze {pair_description}: {e}")
            self._add_error_row(original_video, optimized_video, "Analysis failed")

    def _format_size_difference(self, size_diff: int) -> str:
        """
        Format file size difference with appropriate sign.

        Args:
            size_diff: Size difference in bytes (positive = increased, negative = decreased)

        Returns:
            str: Formatted size difference string with sign

        """
        sign = "+" if size_diff >= 0 else "-"
        return f"{sign}{humanize_file_size(abs(size_diff))}"

    def _add_resolution_mismatch_row(self, original: Path, optimized: Path) -> None:
        """Add a table row for videos with mismatched resolutions."""
        self.health_table.add_row(
            Text(original.name),
            Text(optimized.name),
            Text("N/A"),
            Text("Resolution mismatch - cannot compare"),
            style="yellow",
        )

    def _add_error_row(self, original: Path, optimized: Path, error_msg: str) -> None:
        """Add a table row for videos that failed analysis."""
        self.health_table.add_row(
            Text(original.name),
            Text(optimized.name),
            Text("Error"),
            Text(error_msg),
            style="red",
        )

    def _get_sample(self) -> list[tuple[Path, Path]]:
        """
        Sample video pairs for analysis based on configuration.

        Returns all pairs if --all flag is set, otherwise returns a random sample
        based on the configured sample ratio (minimum 1 pair).

        Returns:
            list[tuple[Path, Path]]: List of (original, optimized) video file pairs

        Raises:
            FileNotFoundError: If no video pairs are found for analysis

        """
        video_pairs = self._find_video_pairs()

        if self.process_all:
            logger.info(f"Processing all {len(video_pairs)} video pairs")
            return video_pairs

        sample_size = max(MINIMUM_SAMPLE_SIZE, math.floor(len(video_pairs) * self.sample_ratio))
        sample = random.choices(video_pairs, k=sample_size)

        logger.info(f"Randomly selected {len(sample)} of {len(video_pairs)} video pairs for analysis")
        return sample

    def _find_video_pairs(self) -> list[tuple[Path, Path]]:
        """
        Discover and pair original videos with their optimized counterparts.

        Returns:
            list[tuple[Path, Path]]: List of (original, optimized) video file pairs

        Raises:
            FileNotFoundError: If no video pairs are found in the directory

        """
        console.print("Scanning for video pairs to analyze..", end="")

        original_files = find_all_video_files(self.directory, originals_only=True)

        pairs = [
            (original, optimized_video)
            for original in original_files
            if (optimized_video := has_optimized_version(original))
        ]

        if not pairs:
            error_msg = f"No original-optimized video pairs found in '{self.directory.name}'"
            console.print(" [red]failed[/]")
            logger.error(error_msg)
            raise FileNotFoundError(error_msg)

        console.print(f" found [blue]{len(pairs)}[/] pair(s)")
        return pairs

    @staticmethod
    def _is_same_resolution(video1: Path, video2: Path) -> bool:
        """
        Check if two videos have identical resolution.

        Args:
            video1: First video file to compare
            video2: Second video file to compare

        Returns:
            bool: True if both videos have the same resolution

        """
        try:
            return get_video_resolution(video1) == get_video_resolution(video2)
        except (subprocess.CalledProcessError, FileNotFoundError, ValueError) as e:
            logger.warning(f"Failed to compare resolutions for {video1.name} and {video2.name}: {e}")
            return False

    def _compare_videos_ssim(self, original_file: Path, optimized_file: Path) -> float:
        """
        Perform SSIM (Structural Similarity Index) comparison between two videos.

        Args:
            original_file: Path to the original video file
            optimized_file: Path to the optimized video file

        Returns:
            float: SSIM score between 0.0 and 1.0 (higher = more similar)

        Raises:
            subprocess.CalledProcessError: If ffmpeg command fails
            ValueError: If SSIM score cannot be extracted from output

        """
        command = [
            "ffmpeg",
            "-i",
            str(original_file),
            "-i",
            str(optimized_file),
            "-lavfi",
            "[0:v][1:v]ssim=stats_file=-",
            "-f",
            "null",
            "-",
        ]

        try:
            process = subprocess.run(
                command,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.PIPE,
                text=True,
                check=True,
                timeout=300,  # 5-minute timeout for very large files
            )
        except subprocess.TimeoutExpired as e:
            error_msg = f"SSIM comparison timed out for {original_file.name} & {optimized_file.name}"
            logger.error(error_msg)
            raise ValueError(error_msg) from e
        except (subprocess.CalledProcessError, FileNotFoundError) as e:
            logger.error(f"Failed to compare {original_file.name} & {optimized_file.name}: {e}")
            raise

        # Log the detailed output for debugging
        with DEBUG_LOG_FILE.open("a", encoding="utf-8") as log_file:
            log_file.write(f"\n=== SSIM Analysis: {original_file.name} vs {optimized_file.name} ===\n")
            log_file.write(process.stderr)
            log_file.write("\n" + "=" * 80 + "\n")

        # Extract SSIM score from stderr output
        matches = re.findall(FFMPEG_SSIM_PATTERN, process.stderr)
        if not matches:
            error_msg = "SSIM score not found in ffmpeg output"
            logger.error(f"{error_msg}. Check {DEBUG_LOG_FILE} for details.")
            raise ValueError(error_msg)

        return float(matches[-1])

    @staticmethod
    def _ssim_health_color(score: float) -> str:
        """
        Determine display color based on SSIM score quality thresholds.

        Args:
            score: SSIM score between 0.0 and 1.0

        Returns:
            str: Color name for Rich console formatting

        """
        if score >= SSIM_EXCELLENT_THRESHOLD:
            return "green"
        if score >= SSIM_GOOD_THRESHOLD:
            return "yellow"
        return "red"
