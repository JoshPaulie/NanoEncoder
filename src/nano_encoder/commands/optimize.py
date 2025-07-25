import argparse
import subprocess
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Literal

from rich.progress import (
    BarColumn,
    Progress,
    TaskID,
    TaskProgressColumn,
    TextColumn,
    TimeRemainingColumn,
)

from nano_encoder.console import console
from nano_encoder.logger import logger
from nano_encoder.utils import (
    VIDEO_FILE_EXTENSIONS,
    get_video_codec,
    get_video_duration,
    has_optimized_version,
    humanize_duration,
    humanize_file_size,
    shorten_path,
)

from .base_command import BaseCommand


@dataclass
class OptimizeArgs:
    """Optimize command args."""

    directory: Path
    crf: int = 28
    preset: Literal[
        "ultrafast",
        "superfast",
        "veryfast",
        "faster",
        "fast",
        "medium",
        "slow",
        "slower",
        "veryslow",
    ] = "medium"
    downscale: int | None = None
    tune: Literal["animation", "grain", "stillimage", "fastdecode", "zerolatency"] | None = None
    force_encode: bool = False
    halt_on_increase: bool = False


def handle_optimize_command(args: argparse.Namespace) -> None:
    """Handle optimize command and errors."""
    try:
        OptimizeDirectory(
            OptimizeArgs(
                directory=args.directory,
                crf=args.crf,
                preset=args.preset,
                downscale=args.downscale,
                tune=args.tune,
                force_encode=args.force_encode,
                halt_on_increase=args.halt_on_increase,
            ),
        ).execute()
    except (FileNotFoundError, NotADirectoryError, ValueError) as e:
        logger.error(str(e))
        raise
    except KeyboardInterrupt:
        message = "User cancelled optimizing directory operation."
        console.print(message, end="\n\n")
        logger.info(message)


class OptimizeDirectory(BaseCommand):
    """Handles optimizing videos in a directory using VideoEncoder."""

    ProgressBar = Progress(
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        TaskProgressColumn(),
        TimeRemainingColumn(),
        expand=True,
        console=console,
    )

    def __init__(self, args: OptimizeArgs) -> None:
        super().__init__(args.directory)
        self.crf = args.crf
        self.preset = args.preset
        self.downscale = args.downscale
        self.tune = args.tune
        self.force_encode = args.force_encode
        self.halt_on_increase = args.halt_on_increase
        self.total_disk_space_change = 0
        self.processing_duration = 0.0
        self.skipped_hevc: list[str] = []
        self.video_files: list[Path] = self._find_video_files()
        self.completed_duration_of_previous_videos: float = 0.0

    def execute(self) -> None:
        """Process each video file in the directory."""
        if not self.video_files:
            console.print("There's no original videos to optimize!")
            console.print("Another job well done!")
            logger.info("Found no original videos to optimize.")
            return

        logger.info(f"Starting processing for '{self.directory}'..")
        start_time = time.perf_counter()
        console.print()

        with self.ProgressBar as progress:
            total_videos_duration = sum(get_video_duration(video) for video in self.video_files)
            overall_progress_id = progress.add_task(
                f"Optimizing '{shorten_path(self.directory, 3)}'",
                total=total_videos_duration,
            )

            for video in self.video_files:
                task_id = progress.add_task(
                    f"[yellow]{video.name}",
                    total=get_video_duration(video),
                )

                try:
                    optimizer = VideoOptimizer(
                        video,
                        self,
                        overall_progress_id,
                        self.completed_duration_of_previous_videos,
                    )
                    optimizer.task_id = task_id
                    optimizer.optimize()

                    if self.halt_on_increase and optimizer.disk_space_change < 0:
                        message = f"Halting optimization as '{video.name}' size increased."
                        logger.warning(message)
                        console.print(f"\n[yellow]{message} Try increasing your CRF.")
                        break

                    self.total_disk_space_change += optimizer.disk_space_change

                except (subprocess.CalledProcessError, FileNotFoundError) as e:
                    logger.error(f"Failed to process '{video}': {e!s}")

                progress.update(task_id, completed=get_video_duration(video))
                progress.update(task_id, description=f"[green]{video.name}")

                self.completed_duration_of_previous_videos += get_video_duration(video)

            progress.update(overall_progress_id, description=f"[green]{self.directory.name}")

        self.processing_duration = time.perf_counter() - start_time

        logger.info(
            f"Completed optimizing '{self.directory}'. "
            f"Total duration: {humanize_duration(self.processing_duration)}. "
            f"Total disk space: {humanize_file_size(abs(self.total_disk_space_change))} "
            f"{'saved' if self.total_disk_space_change > 0 else 'increased'}.",
        )

        self._all_done_message()

    def _video_already_optimized(self, file_path: Path) -> bool:
        """Check if the file already has an optimized version."""
        if has_optimized_version(file_path):
            logger.info(f"'{file_path.name}' has optimized version. Skipping.")
            return True
        return False

    def _is_hevc_video(self, video: Path) -> bool:
        """Check if video is already encoded with HEVC/h.265."""
        # If --force is used, treat all videos as non-HEVC to ensure they are processed.
        if self.force_encode:
            return False

        video_codec = get_video_codec(video)
        is_hevc = any(codec in video_codec.lower() for codec in ["hevc", "h265", "h.265"])
        if is_hevc:
            self.skipped_hevc.append(video.name)
            logger.info(f"'{video.name}' is already h.265 encoded. Skipping.")
        return is_hevc

    def _find_video_files(self) -> list[Path]:
        """Scan the directory for non-optimized video files."""
        console.print("Scanning directory for video files..", end="")

        video_files: list[Path] = []
        for ext in VIDEO_FILE_EXTENSIONS:
            video_files.extend(self.directory.rglob(f"*.{ext}"))

        video_files = [
            video
            for video in video_files
            if all(exclude not in video.name for exclude in ["optimized", "optimizing"])
            and not self._video_already_optimized(video)
            and not self._is_hevc_video(video)
        ]

        if self.skipped_hevc:
            console.print(f"\nSkipped [blue]{len(self.skipped_hevc)}[/] video(s) already in h.265 format.")
            console.print("Use --force to encode them anyway.")

        plural = "s" if len(video_files) != 1 else ""
        console.print(f"found [blue]{len(video_files)}[/] original video{plural}.")
        logger.info(f"Found {len(video_files)} original video files in '{self.directory.name}'.")
        return sorted(video_files)

    def _all_done_message(self) -> None:
        """Display completion message with statistics."""
        console.print()
        console.print(f"[green]All done[/] optimizing [b]{self.directory.name}[/]!")
        console.print(f"Total duration: [yellow]{humanize_duration(self.processing_duration)}")
        console.print(
            f"Total disk space: [yellow]{humanize_file_size(abs(self.total_disk_space_change))}",
            end="",
        )
        console.print(f" {'[green]saved[/]' if self.total_disk_space_change > 0 else '[red]increased[/]'}")
        console.print()

    def _average_video_length(self) -> float:
        """Calculate average video duration in the directory."""
        total_video_length = sum(get_video_duration(video) for video in self.video_files)
        return round(total_video_length / len(self.video_files))

    @staticmethod
    def _get_eta(videos_remaining: int, average_video_length: float, speed: float) -> str:
        """Calculate estimated time remaining."""
        time_left = videos_remaining * average_video_length
        time_remaining = time_left / (speed or 1)
        return humanize_duration(time_remaining)


class VideoOptimizer:
    """Handles video encoding operations using ffmpeg."""

    def __init__(
        self,
        video_file: Path,
        optimize_dir: "OptimizeDirectory",
        overall_progress_id: TaskID,
        completed_duration_of_previous_videos: float,
    ) -> None:
        self.input_file = video_file
        self.crf = optimize_dir.crf
        self.downscale = optimize_dir.downscale
        self.preset = optimize_dir.preset
        self.tune = optimize_dir.tune
        self.output_file = self._create_optimizing_output_path()
        self._cleanup_existing_optimizing_file()
        self.original_size = self.input_file.stat().st_size
        self.encoding_duration = 0.0
        self.disk_space_change = 0
        self.speed_factor = 0.0
        self.progress = optimize_dir.ProgressBar
        self.video_duration = get_video_duration(self.input_file)
        self.task_id: TaskID = TaskID(0)
        self.post_optimization_size: int = 0
        self.overall_progress_id = overall_progress_id
        self.completed_duration_of_previous_videos = completed_duration_of_previous_videos

    def _cleanup_existing_optimizing_file(self) -> None:
        """Delete existing .optimizing file if present."""
        if self.output_file.exists():
            logger.info(f"Deleted partially completed file '{self.output_file.name}'.")
            self.output_file.unlink()

    def _create_optimizing_output_path(self) -> Path:
        """Create output path with 'optimizing' status marker."""
        return self.input_file.with_name(f"{self.input_file.stem}.optimizing{self.input_file.suffix}")

    def optimize(self) -> None:
        """Perform video encoding and post-processing."""
        self._run_ffmpeg()
        self._validate_output()
        self._rename_final_output()
        self._log_report()

    def _run_ffmpeg(self) -> None:
        """Execute ffmpeg command with configured parameters."""
        # Build video filters
        video_filters = ["format=yuv420p"]  # QuickTime compatibility
        if self.downscale:
            video_filters.append(f"scale=-2:{self.downscale}")

        command = [
            "ffmpeg",  # GOAT
            *["-i", str(self.input_file)],  # Input file
            *["-c:v", "libx265"],  # HEVC (aka) h.265
            *["-crf", str(self.crf)],  # Constant refresh rate
            *["-preset", self.preset],  # Compression/efficiency presets
            *(["-tune", self.tune] if self.tune else []),  # Tune flag (or not)
            *["-threads", "0"],  # Use all available threads
            *["-c:a", "copy"],  # Copy audio "as is"
            *["-c:s", "copy"],  # Copy subtitles "as is"
            *["-tag:v", "hvc1"],  # Apple compatibility
            *["-vf", ",".join(video_filters)],  # Combined video filters
            *["-progress", "pipe:1"],  # Pipe progress to stdout
            *["-nostats"],  # Disable default stats output
            *["-loglevel", "error"],  # Only log errors
            str(self.output_file),
        ]

        logger.info(f"Starting encoding for '{self.input_file.name}'.")

        start_time = time.perf_counter()

        with subprocess.Popen(
            command,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            universal_newlines=True,
            encoding="utf-8",
        ) as process:
            if process.stdout:
                for line in process.stdout:
                    logger.debug(line.strip())
                    if "out_time_ms" in line:
                        progress_data = {
                            k.strip(): v.strip()
                            for k, v in (item.split("=") for item in line.split("\n") if "=" in item)
                        }
                        out_time_ms = int(progress_data.get("out_time_ms", 0))
                        current_video_completed_seconds = out_time_ms / 1_000_000
                        self.progress.update(self.task_id, completed=current_video_completed_seconds)
                        self.progress.update(
                            self.overall_progress_id,
                            completed=self.completed_duration_of_previous_videos + current_video_completed_seconds,
                        )

        self.encoding_duration = time.perf_counter() - start_time

    def _validate_output(self) -> None:
        """Validate encoding results and calculate savings."""
        if not self.output_file.exists():
            logger.error("Optimized file not created.")
            msg = "Optimized file not created."
            raise FileNotFoundError(msg)

        self.post_optimization_size = int(self.output_file.stat().st_size)
        self.disk_space_change = self.original_size - self.post_optimization_size

    def _rename_final_output(self) -> None:
        """Finalize file name by changing .optimizing.ext → .optimized.ext."""
        final_name = self.output_file.with_name(self.output_file.name.replace("optimizing", "optimized"))
        self.output_file.rename(final_name)
        self.output_file = final_name

    def _log_report(self) -> None:
        """Generate encoding results report."""
        self.speed_factor = get_video_duration(self.input_file) / self.encoding_duration

        report = [
            f"Finished encoding '{self.input_file.name}'.",
            f"Duration: {humanize_duration(self.encoding_duration)} ({self.speed_factor:.2f}x).",
            f"Size: {humanize_file_size(self.original_size)} → {humanize_file_size(self.post_optimization_size)}.",
            f"Disk space: {humanize_file_size(abs(self.disk_space_change))} "
            f"({'saved' if self.disk_space_change > 0 else 'increased'}).",
        ]

        logger.info(report)
