import subprocess
import time
from pathlib import Path

from ...logger import DEBUG_LOG_FILE, logger
from ...utils import get_video_duration, humanize_duration, humanize_file_size


class VideoOptimizer:
    """Handles video encoding operations using ffmpeg."""

    def __init__(self, video_file: Path, crf: int, downscale: int | None = None) -> None:
        # User args
        self.input_file = video_file
        self.crf = crf
        self.downscale = downscale

        # The resulting "optimized" file. Starts with ".optimizing" label
        self.output_file = self._create_optimizing_output_path()

        # Remove unfinished field if present
        self._cleanup_existing_optimizing_file()

        # Stats for report
        self.original_size = self.input_file.stat().st_size
        self.encoding_duration = 0.0
        self.disk_space_change = 0

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
            *["-preset", "medium"],  # Compression/efficiency presets
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
