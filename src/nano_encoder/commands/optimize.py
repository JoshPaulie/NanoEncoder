import subprocess
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

from ..cli import OptimizeArgs
from ..console import console
from ..logger import DEBUG_LOG_FILE, logger
from ..utils import (
    VIDEO_FILE_EXTENSIONS,
    get_video_codec,
    get_video_duration,
    has_optimized_version,
    humanize_duration,
    humanize_file_size,
    shorten_path,
)
from .base_command import BaseCommand


def handle_optimize_command(args: OptimizeArgs) -> None:
    try:
        OptimizeDirectory(args).execute()
    except (FileNotFoundError, NotADirectoryError, ValueError) as e:
        logger.error(str(e))
        raise
    except KeyboardInterrupt:
        message = "User cancelled optimizing directory operation."
        print(message, end="\n\n")
        logger.info(message)


class OptimizeDirectory(BaseCommand):
    """Handles optimizing videos in a directory using VideoEncoder."""

    ProgressBar = Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description} {task.fields[eta]}"),
        BarColumn(),
        TaskProgressColumn(),
        TimeElapsedColumn(),
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
        self.processing_duration = 0
        self.skipped_hevc = []
        self.video_files = self._find_video_files()

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
            overall_progress_id = progress.add_task(
                f"Optimizing '{shorten_path(self.directory, 3)}'",
                total=len(self.video_files),
                eta="",
            )

            for indx, video in enumerate(self.video_files):
                current_video_progress_id = progress.add_task(f"[yellow]{video.name}", total=None, eta="")

                try:
                    optimizer = VideoOptimizer(video, self)
                    optimizer.optimize()

                    if self.halt_on_increase and optimizer.disk_space_change < 0:
                        message = f"Halting optimization as '{video.name}' size increased."
                        logger.warning(message)
                        console.print(f"\n[yellow]{message} Try increasing your CRF.")
                        break

                    self.total_disk_space_change += optimizer.disk_space_change

                except (subprocess.CalledProcessError, FileNotFoundError) as e:
                    logger.error(f"Failed to process '{video}': {str(e)}")

                progress.update(current_video_progress_id, total=1, completed=1)
                progress.update(current_video_progress_id, description=f"[green]{video.name}")

                videos_remaining = len(self.video_files) - (indx + 1)
                progress.update(
                    overall_progress_id,
                    advance=1,
                    eta=f"Eta: {self._get_eta(videos_remaining, self._average_video_length(), optimizer.speed_factor)}",
                )

            progress.update(overall_progress_id, description=f"[green]{self.directory.name}", eta="")

        self.processing_duration = time.perf_counter() - start_time

        logger.info(
            f"Completed optimizing '{self.directory}'. "
            f"Total duration: {humanize_duration(self.processing_duration)}. "
            f"Total disk space: {humanize_file_size(abs(self.total_disk_space_change))} "
            f"{'saved' if self.total_disk_space_change > 0 else 'increased'}."
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
        # (Possibly incorrectly) report video is not HEVC
        # This way, those already in HEVC will still be optimized with the `--force` flag.
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

        video_files = []
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

    def __init__(self, video_file: Path, optimize_dir: OptimizeDirectory) -> None:
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
            *(["-vf", f"scale=-2:{self.downscale}"] if self.downscale else []),  # Downscale flag (or not)
            *["-tag:v", "hvc1"],  # Apple compatibility
            *["-loglevel", "error"],  # Only log errors
            str(self.output_file),
        ]

        logger.info(f"Starting encoding for '{self.input_file.name}'.")

        start_time = time.perf_counter()

        with open(DEBUG_LOG_FILE, "a") as log_file:
            subprocess.run(command, stdout=log_file, stderr=log_file, text=True, check=True)

        self.encoding_duration = time.perf_counter() - start_time

    def _validate_output(self) -> None:
        """Validate encoding results and calculate savings."""
        if not self.output_file.exists():
            logger.error("Optimized file not created.")
            raise FileNotFoundError("Optimized file not created.")

        self.post_optimization_size = self.output_file.stat().st_size
        self.disk_space_change = self.original_size - self.post_optimization_size

    def _rename_final_output(self) -> None:
        """Finalize file name by changing .optimizing.ext → .optimized.ext"""
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
