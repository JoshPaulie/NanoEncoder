import subprocess
import sys
import time
from pathlib import Path

from rich.progress import (
    BarColumn,
    Progress,
    SpinnerColumn,
    TaskProgressColumn,
    TextColumn,
    TimeElapsedColumn,
)

from .console import console
from .logger import logger
from .utils import (
    CRF_MAX,
    CRF_MIN,
    VIDEO_FILE_EXTENSIONS,
    has_optimized_version,
    humanize_duration,
    humanize_file_size,
    validate_directory,
)
from .video_optimizer import VideoOptimizer


def handle_optimize_command(args) -> None:
    try:
        # User input validation
        validate_directory(args.directory)
        if not CRF_MIN <= args.crf <= CRF_MAX:
            raise ValueError(f"CRF must be between {CRF_MIN} and {CRF_MAX}")

        OptimizeDirectory(args.directory, args.crf).optimize()
    except (FileNotFoundError, NotADirectoryError, ValueError) as e:
        logger.error(str(e))
        raise
    except KeyboardInterrupt:
        message = "User cancelled optimizing directory operation."
        print(message, end="\n\n")
        logger.info(message)


class OptimizeDirectory:
    """Handles optimizing videos in a directory using VideoEncoder."""

    ProgressBar = Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        TaskProgressColumn(),
        TimeElapsedColumn(),
        expand=True,
    )

    def __init__(self, directory: Path, crf: int) -> None:
        self.directory = directory.resolve()
        self.crf = crf
        self.total_disk_space_change = 0
        self.processing_duration = 0

    def _video_already_optimized(self, file_path: Path) -> bool:
        """Check if the file already has an optimized version."""
        if has_optimized_version(file_path):
            logger.info(f"'{file_path.name}' has optimized version. Skipping.")
            return True
        return False

    def _find_video_files(self) -> list[Path]:
        """Scan the directory for non-optimized video files."""
        console.print("Scanning directory for video files..", end="")

        video_files = []
        for ext in VIDEO_FILE_EXTENSIONS:
            video_files.extend(self.directory.rglob(f"*.{ext}"))

        video_files = [
            video
            for video in video_files
            if all(exclude not in video.name for exclude in ["optimized", "optimizing"])
            and not self._video_already_optimized(video)
        ]

        if not video_files:
            console.print("there's no original videos to optimize!")
            console.print("Another job well done!")
            logger.info("Found no original videos to optimize.")
            sys.exit()

        plural = "s" if len(video_files) != 1 else ""
        console.print(f"found [blue]{len(video_files)}[/] original video{plural}.")
        logger.info(f"Found {len(video_files)} original video files in '{self.directory.name}'.")
        return sorted(video_files)

    def _all_done_message(self) -> None:
        # User output
        console.print()
        console.print(f"[green]All done[/] optimizing [b]{self.directory.name}[/]!")
        console.print(f"Total duration: [yellow]{humanize_duration(self.processing_duration)}")
        console.print(
            f"Total disk space: [yellow]{humanize_file_size(abs(self.total_disk_space_change))}",
            end="",
        )
        console.print(f" {'[green]saved[/]' if self.total_disk_space_change > 0 else '[red]increased[/]'}")
        console.print()

    def optimize(self) -> None:
        """Process each video file in the directory."""
        logger.info(f"Starting processing for '{self.directory}'..")
        start_time = time.perf_counter()
        video_files = self._find_video_files()
        console.print()

        with self.ProgressBar as progress:
            # Create "overall" progress bar for the entire directory
            overall_progress_id = progress.add_task(
                f"Optimizing {self.directory.name}", total=len(video_files)
            )

            for video in video_files:
                # Add new progress bar for each video
                current_video_progress_id = progress.add_task(f"Optimizing [yellow]{video.name}", total=None)

                try:
                    optimizer = VideoOptimizer(video, self.crf)
                    optimizer.optimize()
                    self.total_disk_space_change += optimizer.disk_space_change
                except (subprocess.CalledProcessError, FileNotFoundError) as e:
                    logger.error(f"Failed to process '{video}': {str(e)}")

                # Update video progress bars
                progress.update(current_video_progress_id, total=1, completed=1)
                progress.update(current_video_progress_id, description=f"Finished [green]{video.name}")
                # Advance overall progress bar
                progress.update(overall_progress_id, advance=1)

            # Update overall progress
            progress.update(overall_progress_id, description=f"Finished [green]{self.directory.name}")

        # Elapsed time from optimizing directory
        self.processing_duration = time.perf_counter() - start_time

        # Log processing information
        logger.info(
            (
                f"Completed optimizing '{self.directory}'. "
                f"Total duration: {humanize_duration(self.processing_duration)}. "
                f"Total disk space: {humanize_file_size(abs(self.total_disk_space_change))} "
                f"{'saved' if self.total_disk_space_change > 0 else 'increased'}."
            )
        )

        self._all_done_message()
