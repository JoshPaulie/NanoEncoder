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
from send2trash import send2trash

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

# Constants for better maintainability
MICROSECONDS_PER_SECOND = 1_000_000
DEFAULT_CRF = 28
DEFAULT_PRESET: Literal[
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
EXCLUDED_FILENAME_PARTS = ["optimized", "optimizing"]
HEVC_CODEC_IDENTIFIERS = ["hevc", "h265", "h.265"]


@dataclass
class OptimizeArgs:
    """
    Arguments for video optimization operations.

    Attributes:
        directory: Directory containing videos to optimize
        crf: Constant Rate Factor (quality setting, lower = better quality)
        preset: Encoding speed preset (faster = lower quality/smaller file)
        downscale: Target height for downscaling (maintains aspect ratio)
        tune: Optimization tuning for specific content types
        force_encode: Re-encode videos even if already in h.265 format
        halt_on_increase: Stop optimization if file size increases
        delete_after: Delete original file after successful optimization
        untag_after: Remove '.optimized' from filename after optimization

    """

    directory: Path
    crf: int = DEFAULT_CRF
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
    ] = DEFAULT_PRESET
    downscale: int | None = None
    tune: Literal["animation", "grain", "stillimage", "fastdecode", "zerolatency"] | None = None
    force_encode: bool = False
    halt_on_increase: bool = False
    delete_after: bool = False
    untag_after: bool = False


def handle_optimize_command(args: argparse.Namespace) -> None:
    """
    Handle optimize command execution with comprehensive error handling.

    Args:
        args: Parsed command line arguments containing optimization parameters

    Raises:
        FileNotFoundError: If the specified directory doesn't exist
        NotADirectoryError: If the path exists but isn't a directory
        ValueError: If invalid arguments are provided

    """
    optimize_args = OptimizeArgs(
        directory=args.directory,
        crf=args.crf,
        preset=args.preset,
        downscale=args.downscale,
        tune=args.tune,
        force_encode=args.force_encode,
        halt_on_increase=args.halt_on_increase,
        delete_after=args.delete_after,
        untag_after=args.untag_after,
    )

    try:
        OptimizeDirectory(optimize_args).execute()
    except (FileNotFoundError, NotADirectoryError, ValueError) as e:
        logger.error(f"Optimization failed: {e}")
        raise
    except KeyboardInterrupt:
        message = "User cancelled optimization operation"
        console.print(f"\n[yellow]{message}[/]\n")
        logger.info(message)
        raise


class OptimizeDirectory(BaseCommand):
    """
    Handles batch optimization of videos in a directory.

    This class orchestrates the video optimization process, managing progress
    tracking, file discovery, and coordination of individual video encoding tasks.
    """

    # Shared progress bar configuration for all optimization operations
    ProgressBar = Progress(
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        TaskProgressColumn(),
        TimeRemainingColumn(),
        expand=True,
        console=console,
    )

    def __init__(self, args: OptimizeArgs) -> None:
        """
        Initialize directory optimization with the provided arguments.

        Args:
            args: Configuration parameters for the optimization process

        """
        super().__init__(args.directory)

        # Encoding parameters
        self.crf = args.crf
        self.preset = args.preset
        self.downscale = args.downscale
        self.tune = args.tune
        self.force_encode = args.force_encode
        self.halt_on_increase = args.halt_on_increase
        self.delete_after = args.delete_after
        self.untag_after = args.untag_after

        # Processing state tracking
        self.total_disk_space_change = 0
        self.processing_duration = 0.0
        self.completed_duration_of_previous_videos: float = 0.0

        # File management
        self.skipped_hevc: list[str] = []
        self.video_files: list[Path] = self._find_video_files()

    def execute(self) -> None:
        """Process all video files in the directory with progress tracking."""
        if not self._has_videos_to_process():
            return

        logger.info(f"Starting optimization for '{self.directory}'")
        start_time = time.perf_counter()
        console.print()

        self._process_videos_with_progress()
        self.processing_duration = time.perf_counter() - start_time
        self._log_completion_summary()
        self._all_done_message()

    def _has_videos_to_process(self) -> bool:
        """Check if there are videos available for processing."""
        if not self.video_files:
            console.print("There's no original videos to optimize!")
            console.print("Another job well done!")
            logger.info("Found no original videos to optimize.")
            return False
        return True

    def _process_videos_with_progress(self) -> None:
        """Process all videos with progress bar tracking."""
        with self.ProgressBar as progress:
            total_duration = sum(get_video_duration(video) for video in self.video_files)
            overall_progress_id = progress.add_task(
                f"Optimizing '{shorten_path(self.directory, 3)}'",
                total=total_duration,
            )

            for video in self.video_files:
                if not self._process_single_video(video, progress, overall_progress_id):
                    break  # Halt on increase if configured

            progress.update(overall_progress_id, description=f"[green]{self.directory.name}")

    def _process_single_video(
        self,
        video: Path,
        progress: Progress,
        overall_progress_id: TaskID,
    ) -> bool:
        """
        Process a single video file.

        Args:
            video: Path to the video file to process
            progress: Progress bar instance for tracking
            overall_progress_id: ID of the overall progress task

        Returns:
            bool: True to continue processing, False to halt

        """
        task_id = progress.add_task(f"[yellow]{video.name}", total=get_video_duration(video))

        try:
            optimizer = VideoOptimizer(
                video,
                self,
                overall_progress_id,
                self.completed_duration_of_previous_videos,
            )
            optimizer.task_id = task_id
            optimizer.optimize()

            if self._should_halt_on_size_increase(optimizer, video):
                return False

            # Post-optimization actions
            if self.delete_after:
                self._delete_original_file(video)

            if self.untag_after:
                self._untag_optimized_file(optimizer.output_file)

            self.total_disk_space_change += optimizer.disk_space_change

        except (subprocess.CalledProcessError, FileNotFoundError) as e:
            logger.error(f"Failed to process '{video}': {e}")

        # Update progress tracking
        video_duration = get_video_duration(video)
        progress.update(task_id, completed=video_duration, description=f"[green]{video.name}")
        self.completed_duration_of_previous_videos += video_duration

        return True

    def _should_halt_on_size_increase(self, optimizer: "VideoOptimizer", video: Path) -> bool:
        """Check if processing should halt due to file size increase."""
        if self.halt_on_increase and optimizer.disk_space_change < 0:
            message = f"Halting optimization as '{video.name}' size increased"
            logger.warning(message)
            console.print(f"\n[yellow]{message}. Try increasing your CRF.[/]")
            return True
        return False

    def _log_completion_summary(self) -> None:
        """Log summary information about the completed optimization."""
        space_change_desc = "saved" if self.total_disk_space_change > 0 else "increased"
        logger.info(
            f"Completed optimizing '{self.directory}'. "
            f"Total duration: {humanize_duration(self.processing_duration)}. "
            f"Total disk space: {humanize_file_size(abs(self.total_disk_space_change))} {space_change_desc}.",
        )

    def _video_already_optimized(self, file_path: Path) -> bool:
        """Check if the file already has an optimized version."""
        if has_optimized_version(file_path):
            logger.info(f"'{file_path.name}' has optimized version. Skipping.")
            return True
        return False

    def _is_hevc_video(self, video: Path) -> bool:
        """
        Check if video is already encoded with HEVC/h.265.

        Args:
            video: Path to the video file to check

        Returns:
            bool: True if the video is already HEVC encoded

        """
        # If --force is used, treat all videos as non-HEVC to ensure they are processed
        if self.force_encode:
            return False

        video_codec = get_video_codec(video)
        is_hevc = any(codec in video_codec.lower() for codec in HEVC_CODEC_IDENTIFIERS)

        if is_hevc:
            self.skipped_hevc.append(video.name)
            logger.info(f"'{video.name}' is already h.265 encoded. Skipping.")

        return is_hevc

    def _should_exclude_video(self, video: Path) -> bool:
        """
        Determine if a video should be excluded from processing.

        Args:
            video: Path to the video file to check

        Returns:
            bool: True if the video should be excluded

        """
        # Check for excluded filename parts
        if any(exclude in video.name for exclude in EXCLUDED_FILENAME_PARTS):
            return True

        # Check if already optimized
        if self._video_already_optimized(video):
            return True

        # Check if already HEVC encoded (unless forced)
        return self._is_hevc_video(video)

    def _find_video_files(self) -> list[Path]:
        """
        Scan the directory for video files that need optimization.

        Returns:
            list[Path]: Sorted list of video files ready for processing

        """
        console.print("Scanning directory for video files..", end="")

        # Collect all video files by extension
        video_files: list[Path] = []
        for ext in VIDEO_FILE_EXTENSIONS:
            video_files.extend(self.directory.rglob(f"*.{ext}"))

        # Filter out videos that should be excluded
        video_files = [video for video in video_files if not self._should_exclude_video(video)]

        self._display_scan_results(video_files)
        return sorted(video_files)

    def _display_scan_results(self, video_files: list[Path]) -> None:
        """Display the results of the video file scan."""
        if self.skipped_hevc:
            console.print(f"\nSkipped [blue]{len(self.skipped_hevc)}[/] video(s) already in h.265 format.")
            console.print("Use --force to encode them anyway.")

        file_count = len(video_files)
        plural = "s" if file_count != 1 else ""
        console.print(f"found [blue]{file_count}[/] original video{plural}.")
        logger.info(f"Found {file_count} original video files in '{self.directory.name}'.")

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

    def _delete_original_file(self, original_file: Path) -> None:
        """
        Delete the original video file after successful optimization.

        Args:
            original_file: Path to the original video file to delete

        """
        try:
            send2trash(str(original_file))
            logger.info(f"Deleted original file: {original_file.name}")
            console.print(f"[yellow]Deleted original file: {original_file.name}[/]")
        except OSError as e:
            error_msg = f"Failed to delete original file '{original_file.name}': {e}"
            logger.error(error_msg)
            console.print(f"[red]Error: {error_msg}[/]")

    def _untag_optimized_file(self, optimized_file: Path) -> None:
        """
        Remove '.optimized' from the optimized video filename.

        Args:
            optimized_file: Path to the optimized video file to untag

        """
        try:
            # Generate untagged filename
            untagged_name = optimized_file.with_name(
                optimized_file.name.replace(".optimized", ""),
            )

            # Check if untagged file already exists
            if untagged_name.exists():
                logger.warning(
                    f"Cannot untag '{optimized_file.name}': '{untagged_name.name}' already exists",
                )
                console.print(
                    f"[yellow]Warning: Cannot untag '{optimized_file.name}': '{untagged_name.name}' already exists[/]",
                )
                return

            # Rename the file
            optimized_file.rename(untagged_name)
            logger.info(f"Untagged file: {optimized_file.name} → {untagged_name.name}")
            console.print(f"[blue]Untagged file: {optimized_file.name} → {untagged_name.name}[/]")

        except OSError as e:
            error_msg = f"Failed to untag file '{optimized_file.name}': {e}"
            logger.error(error_msg)
            console.print(f"[red]Error: {error_msg}[/]")


class VideoOptimizer:
    """
    Handles individual video encoding operations using ffmpeg.

    This class manages the encoding of a single video file, including
    command construction, progress tracking, and result validation.
    """

    def __init__(
        self,
        video_file: Path,
        optimize_dir: "OptimizeDirectory",
        overall_progress_id: TaskID,
        completed_duration_of_previous_videos: float,
    ) -> None:
        """
        Initialize video optimizer for a single file.

        Args:
            video_file: Path to the input video file
            optimize_dir: Parent optimization directory instance
            overall_progress_id: Progress task ID for overall operation
            completed_duration_of_previous_videos: Duration of previously processed videos

        """
        # Input/output file management
        self.input_file = video_file
        self.output_file = self._create_optimizing_output_path()
        self._cleanup_existing_optimizing_file()

        # Encoding configuration from parent
        self.crf = optimize_dir.crf
        self.downscale = optimize_dir.downscale
        self.preset = optimize_dir.preset
        self.tune = optimize_dir.tune

        # Size and performance tracking
        self.original_size = self.input_file.stat().st_size
        self.post_optimization_size: int = 0
        self.disk_space_change = 0
        self.encoding_duration = 0.0
        self.speed_factor = 0.0

        # Progress tracking integration
        self.progress = optimize_dir.ProgressBar
        self.task_id: TaskID = TaskID(0)
        self.overall_progress_id = overall_progress_id
        self.video_duration = get_video_duration(self.input_file)
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
        command = self._build_ffmpeg_command()
        logger.info(f"Starting encoding for '{self.input_file.name}'.")

        start_time = time.perf_counter()
        self._execute_ffmpeg_process(command)
        self.encoding_duration = time.perf_counter() - start_time

    def _build_ffmpeg_command(self) -> list[str]:
        """
        Construct the ffmpeg command with all necessary parameters.

        Returns:
            list[str]: Complete ffmpeg command as a list of arguments

        """
        # Build video filters
        video_filters = ["format=yuv420p"]  # QuickTime compatibility
        if self.downscale:
            video_filters.append(f"scale=-2:{self.downscale}")

        # Base command structure
        command = ["ffmpeg"]

        # Input file
        command.extend(["-i", str(self.input_file)])

        # Video encoding settings
        command.extend(["-c:v", "libx265"])  # HEVC (h.265) codec
        command.extend(["-crf", str(self.crf)])  # Constant rate factor
        command.extend(["-preset", self.preset])  # Encoding speed/efficiency preset

        # Optional tuning parameter
        if self.tune:
            command.extend(["-tune", self.tune])

        # Performance and compatibility settings
        command.extend(["-threads", "0"])  # Use all available threads
        command.extend(["-c:a", "copy"])  # Copy audio stream as-is
        command.extend(["-c:s", "copy"])  # Copy subtitle streams as-is
        command.extend(["-tag:v", "hvc1"])  # Apple compatibility tag
        command.extend(["-vf", ",".join(video_filters)])  # Apply video filters

        # Progress and logging settings
        command.extend(["-progress", "pipe:1"])  # Output progress to stdout
        command.extend(["-nostats"])  # Disable default stats
        command.extend(["-loglevel", "error"])  # Only show errors

        # Output file
        command.append(str(self.output_file))

        return command

    def _execute_ffmpeg_process(self, command: list[str]) -> None:
        """
        Execute the ffmpeg process and handle progress updates.

        Args:
            command: The complete ffmpeg command to execute

        """
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
                        self._update_progress_from_ffmpeg_output(line)

    def _update_progress_from_ffmpeg_output(self, line: str) -> None:
        """
        Parse ffmpeg progress output and update progress bars.

        Args:
            line: A line of ffmpeg progress output

        """
        try:
            progress_data = {
                k.strip(): v.strip() for k, v in (item.split("=") for item in line.split("\n") if "=" in item)
            }

            out_time_ms = int(progress_data.get("out_time_ms", 0))
            current_video_completed_seconds = out_time_ms / MICROSECONDS_PER_SECOND

            # Update individual video progress
            self.progress.update(self.task_id, completed=current_video_completed_seconds)

            # Update overall batch progress
            total_completed = self.completed_duration_of_previous_videos + current_video_completed_seconds
            self.progress.update(self.overall_progress_id, completed=total_completed)

        except (ValueError, KeyError) as e:
            logger.debug(f"Failed to parse progress data: {e}")

    def _validate_output(self) -> None:
        """
        Validate encoding results and calculate file size changes.

        Raises:
            FileNotFoundError: If the optimized file was not created

        """
        if not self.output_file.exists():
            error_msg = f"Optimized file not created for '{self.input_file.name}'"
            logger.error(error_msg)
            raise FileNotFoundError(error_msg)

        self.post_optimization_size = int(self.output_file.stat().st_size)
        self.disk_space_change = self.original_size - self.post_optimization_size

    def _rename_final_output(self) -> None:
        """
        Finalize output file by renaming from .optimizing.ext to .optimized.ext.

        This marks the completion of the encoding process and makes the file
        available for use while preventing conflicts with future operations.
        """
        final_name = self.output_file.with_name(
            self.output_file.name.replace("optimizing", "optimized"),
        )
        self.output_file.rename(final_name)
        self.output_file = final_name

    def _log_report(self) -> None:
        """Generate and log comprehensive encoding results report."""
        self.speed_factor = self.video_duration / self.encoding_duration

        space_change_desc = "saved" if self.disk_space_change > 0 else "increased"

        report_lines = [
            f"Finished encoding '{self.input_file.name}'.",
            f"Duration: {humanize_duration(self.encoding_duration)} ({self.speed_factor:.2f}x).",
            f"Size: {humanize_file_size(self.original_size)} → {humanize_file_size(self.post_optimization_size)}.",
            f"Disk space: {humanize_file_size(abs(self.disk_space_change))} {space_change_desc}.",
        ]

        for line in report_lines:
            logger.info(line)
