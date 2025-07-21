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


@dataclass
class HealthArgs:
    """Health command args."""

    directory: Path
    sample_ratio: float = 0.05
    all: bool = False


def handle_health_command(args: argparse.Namespace) -> None:
    """Handle health command and errors."""
    try:
        HealthChecker(HealthArgs(
            directory=args.directory,
            sample_ratio=args.sample_ratio,
            all=args.all,
        )).execute()
    except (FileNotFoundError, NotADirectoryError, ValueError) as e:
        logger.error(str(e))
        raise
    except KeyboardInterrupt:
        message = "User cancelled healthcheck operation."
        console.print(message, end="\n\n")
        logger.info(message)



class HealthChecker(BaseCommand):
    """Encapsulates health command functionally."""

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
    health_table.add_column("Size diff")
    health_table.caption = f"Also logged at {DEBUG_LOG_FILE.absolute()}"

    def __init__(self, args: HealthArgs) -> None:
        super().__init__(args.directory)
        self.sample_ratio = args.sample_ratio
        self.process_all = args.all
        self.sample = self._get_sample()

    def execute(self) -> None:
        """Execute the health check operation."""
        with self.ProgressBar as progress:
            overall_progress_id = progress.add_task(
                f"Performing healthcheck for [blue]{self.directory.name}[/]..",
                total=len(self.sample),
            )

            for original_video, optimized_video in self.sample:
                self._check_video_pair(original_video, optimized_video)
                progress.update(overall_progress_id, advance=1)

            progress.update(
                overall_progress_id,
                description=f"[green]Finished[/] performing healthcheck for {self.directory}",
            )

        console.print(self.health_table)

    def _check_video_pair(self, original_video: Path, optimized_video: Path) -> None:
        """Compare an original-optimized video pair."""
        current_pair = f"'{original_video.name}' & '{optimized_video.name}'"
        size_diff = optimized_video.stat().st_size - original_video.stat().st_size
        diff_sign = "+" if size_diff >= 0 else "-"

        if not self._is_same_resolution(original_video, optimized_video):
            self.health_table.add_row(
                Text(original_video.name),
                Text(optimized_video.name),
                Text("0"),
                Text("Varying resolutions, unable to compare."),
                Text(diff_sign + humanize_file_size(abs(size_diff))),
                style="red",
            )
            return

        logger.info(f"Starting SSIM comparison for {current_pair}.")
        ssim = self._compare_videos_ssim(original_video, optimized_video)
        logger.info(f"{current_pair} = {ssim} SSIM")
        healthcolor = self._ssim_health_color(ssim)

        self.health_table.add_row(
            Text(original_video.name),
            Text(optimized_video.name),
            Text(str(round(ssim, 3))),
            Text(diff_sign + humanize_file_size(abs(size_diff))),
            style="red" if size_diff >= 0 else healthcolor,
        )

    def _pair_videos(self) -> list[tuple[Path, Path]]:
        """Create pairs of original and optimized videos."""
        original_files = find_all_video_files(self.directory, originals_only=True)
        pairs: list[tuple[Path, Path]] = [
            (original, optimized_video)
            for original in original_files
            if (optimized_video := has_optimized_version(original))
        ]
        if not pairs:
            msg = f"'{self.directory}' directory doesn't have any pairs to compare."
            raise FileNotFoundError(msg)
        return pairs

    def _get_sample(self) -> list[tuple[Path, Path]]:
        """
        Sample a percentage of the paired videos to check.

        If --all flag was passed, returns all video pairs.
        Otherwise, sample_ratio is used to return a percentage of videos (1 minimum)
        """
        video_pairs = self._pair_videos()
        if self.process_all:
            return video_pairs

        sample_size = math.floor(len(video_pairs) * self.sample_ratio) or 1
        return random.choices(video_pairs, k=sample_size)

    @staticmethod
    def _is_same_resolution(video1: Path, video2: Path) -> bool:
        """Check if two videos have the same resolution."""
        return get_video_resolution(video1) == get_video_resolution(video2)

    def _compare_videos_ssim(self, original_file: Path, optimized_file: Path) -> float:
        """Perform SSIM comparison between two videos."""
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
            logger.error(f"Failed to compare {original_file.name} & {optimized_file.name}: {e!s}")
            raise

        with DEBUG_LOG_FILE.open("a") as log_file:
            log_file.write(process.stderr)

        matches = re.findall(r"All:(\d+\.\d+)", process.stderr)
        if not matches:
            msg = "SSIM score not found in ffmpeg output"
            raise ValueError(msg)
        return float(matches[-1])

    @staticmethod
    def _ssim_health_color(score: float) -> str:
        """Grade SSIM score and return description and color."""
        score = round(score, 3)
        if score >= 0.990:  # noqa: PLR2004
            return "green"
        if score >= 0.980:  # noqa: PLR2004
            return "yellow"
        return "red"
