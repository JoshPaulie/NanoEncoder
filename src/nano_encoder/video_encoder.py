import subprocess
import time
from pathlib import Path
from typing import List

from .utils import DEBUG_LOG_FILE, humanize_duration, humanize_file_size, print_log


class VideoEncoder:
    """Handles video encoding operations using ffmpeg."""

    def __init__(self, video_file: Path, crf: int) -> None:
        self.input_file = video_file
        self.crf = crf
        self.output_file = self._create_output_path()
        self._cleanup_existing_optimizing_file()
        self.encoding_duration = 0.0
        self.space_saved = 0

    def _cleanup_existing_optimizing_file(self) -> None:
        """Delete existing .optimizing file if present."""
        if self.output_file.exists():
            print_log(f"Found existing .optimizing file '{self.output_file.name}', deleting.")
            self.output_file.unlink()

    def _create_output_path(self) -> Path:
        """Create output path with 'optimizing' status marker."""
        return self.input_file.with_name(f"{self.input_file.stem}.optimizing{self.input_file.suffix}")

    def encode(self) -> None:
        """Perform video encoding and post-processing."""
        self._run_ffmpeg()
        self._validate_output()
        self._rename_final_output()

    def _run_ffmpeg(self) -> None:
        """Execute ffmpeg command with configured parameters."""
        command = [
            "ffmpeg",
            *["-i", str(self.input_file)],
            *["-c:v", "libx265"],
            *["-crf", str(self.crf)],
            *["-preset", "fast"],
            *["-threads", "0"],
            *["-c:a", "copy"],
            *["-c:s", "copy"],
            *["-loglevel", "error"],
            str(self.output_file),
        ]

        print_log(f"Starting encoding for '{self.input_file.name}'..")
        start_time = time.perf_counter()

        with open(DEBUG_LOG_FILE, "a") as log_file:
            subprocess.run(command, stdout=log_file, stderr=log_file, text=True, check=True)

        self.encoding_duration = time.perf_counter() - start_time

    def _validate_output(self) -> None:
        """Validate encoding results and calculate savings."""
        if not self.output_file.exists():
            raise FileNotFoundError("Encoded file not created")

        original_size = self.input_file.stat().st_size
        encoded_size = self.output_file.stat().st_size
        self.space_saved = original_size - encoded_size

    def _rename_final_output(self) -> None:
        """Finalize file name by changing .optimizing.ext → .optimized.ext"""
        final_name = self.output_file.with_name(self.output_file.name.replace("optimizing", "optimized"))
        self.output_file.rename(final_name)
        self.output_file = final_name

    def generate_report(self) -> List[str]:
        """Generate encoding results report."""
        original_size = self.input_file.stat().st_size
        encoded_size = self.output_file.stat().st_size
        speed_factor = self._get_video_duration() / self.encoding_duration

        return [
            f"Finished encoding '{self.input_file.name}'.",
            f"Duration: {humanize_duration(self.encoding_duration)} ({speed_factor:.2f}x).",
            f"Size: {humanize_file_size(original_size)} → {humanize_file_size(encoded_size)}.",
            f"Disk space: {humanize_file_size(abs(self.space_saved))} "
            f"({'saved' if self.space_saved > 0 else 'increased'}).",
        ]

    def _get_video_duration(self) -> float:
        """Get video duration using ffprobe."""
        result = subprocess.run(
            [
                "ffprobe",
                *["-i", str(self.input_file)],
                *["-show_entries", "format=duration"],
                *["-v", "quiet"],
                *["-of", "csv=p=0"],
            ],
            capture_output=True,
            text=True,
            check=True,
        )
        return float(result.stdout.strip())
