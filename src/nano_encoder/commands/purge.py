import argparse
from dataclasses import dataclass
from pathlib import Path

from send2trash import send2trash

from nano_encoder.console import console
from nano_encoder.logger import logger
from nano_encoder.utils import VIDEO_FILE_EXTENSIONS, find_all_video_files, has_optimized_version

from .base_command import BaseCommand

# Constants for better maintainability
OPTIMIZED_FILENAME_MARKER = "optimized"
OPTIMIZING_FILENAME_MARKER = ".optimizing."


@dataclass
class PurgeArgs:
    """
    Arguments for purge operations.

    Attributes:
        directory: Directory containing original videos to purge
        permanent: Whether to permanently delete files instead of moving to trash
        skip_confirmation: Whether to skip user confirmation prompt

    """

    directory: Path
    permanent: bool = False
    skip_confirmation: bool = False


def handle_purge_command(args: argparse.Namespace) -> None:
    """
    Handle purge command execution with comprehensive error handling.

    Args:
        args: Parsed command line arguments containing purge parameters

    Raises:
        FileNotFoundError: If the specified directory doesn't exist
        NotADirectoryError: If the path exists but isn't a directory
        ValueError: If invalid arguments are provided

    """
    purge_args = PurgeArgs(
        directory=args.directory,
        permanent=args.permanent,
        skip_confirmation=args.skip_confirmation,
    )

    try:
        PurgeDirectory(purge_args).execute()
    except (FileNotFoundError, NotADirectoryError, ValueError) as e:
        logger.error(f"Purge operation failed: {e}")
        raise
    except KeyboardInterrupt:
        message = "User cancelled purge operation"
        console.print(f"\n[yellow]{message}[/]\n")
        logger.info(message)
        raise


class PurgeDirectory(BaseCommand):
    """
    Handles safe removal of original video files after successful optimization.

    This class identifies original video files that have corresponding optimized
    versions and can remove them either by moving to trash or permanent deletion,
    with appropriate safety checks and user confirmation.
    """

    def __init__(self, args: PurgeArgs) -> None:
        """
        Initialize purge operation with the provided arguments.

        Args:
            args: Configuration parameters for the purge process

        """
        super().__init__(args.directory)

        # Operation configuration
        self.permanent = args.permanent
        self.skip_confirmation = args.skip_confirmation

        # File discovery
        self.original_files = self._find_original_files_to_purge()

    def execute(self) -> None:
        """Execute the purge operation with safety checks and user confirmation."""
        # Safety check: ensure no incomplete optimization operations
        if unfinished_video := self._has_unfinished_video():
            self._handle_unfinished_video_error(unfinished_video)
            return

        # Check if there are files to purge
        if not self.original_files:
            console.print(f"No original files with optimized versions found in '{self.directory.name}'")
            logger.info(f"No files to purge in '{self.directory.name}'")
            return

        self._log_files_to_purge()

        # Get user confirmation or proceed if skipping
        if self._should_proceed_with_purge():
            self._execute_purge_operation()

    def _handle_unfinished_video_error(self, unfinished_video: Path) -> None:
        """
        Handle the case where unfinished optimization files are found.

        Args:
            unfinished_video: Path to the unfinished video file

        """
        console.print(
            f"[red]Error:[/] Found unfinished optimization file: '{unfinished_video.name}'",
        )
        console.print(
            "Cannot safely purge original files while optimization is incomplete.",
        )
        console.print(
            "Please complete or remove the unfinished optimization before purging.",
        )
        console.print()
        console.print("[green]Suggested fix:[/]")
        console.print(f"  nen optimize {self.directory}")

        logger.error(f"Unfinished optimization file prevents purge: {unfinished_video}")

    def _log_files_to_purge(self) -> None:
        """Log the files that will be purged for audit purposes."""
        filenames = [file.name for file in self.original_files]
        logger.info(f"Found {len(self.original_files)} files to purge: {', '.join(filenames)}")

    def _should_proceed_with_purge(self) -> bool:
        """
        Determine if the purge operation should proceed.

        Returns:
            bool: True if operation should proceed, False otherwise

        """
        if self.skip_confirmation:
            console.print("[red]Force mode enabled - skipping confirmation[/]")
            return True

        confirmation_message = (
            "Permanently delete these ORIGINAL files?"
            if self.permanent
            else "Send these ORIGINAL files to trash/recycling bin?"
        )

        return self._confirm_purge_with_preview(confirmation_message)

    def _confirm_purge_with_preview(self, message: str) -> bool:
        """
        Show files to be purged and get user confirmation.

        Args:
            message: Confirmation message to display

        Returns:
            bool: True if user confirms, False otherwise

        """
        console.print(f"Found {len(self.original_files)} original(s) with optimized versions:")

        for original in self.original_files:
            optimized_name = f"{original.stem}.{OPTIMIZED_FILENAME_MARKER}{original.suffix}"
            console.print(f" - {original.name} → {optimized_name}")

        console.print()
        return self._confirm_action(message)

    def _execute_purge_operation(self) -> None:
        """Perform the actual file deletion or trash operation."""
        deletion_count = 0

        for original_file in self.original_files:
            try:
                console.print(f"Removing '{original_file.name}'")

                if self.permanent:
                    original_file.unlink()
                else:
                    send2trash(str(original_file))

                logger.info(f"Purged '{original_file.name}'")
                deletion_count += 1

            except (OSError, PermissionError) as e:
                error_msg = f"Failed to remove '{original_file.name}': {e}"
                logger.error(error_msg)
                console.print(f"[red]Error: {error_msg}[/]")

        self._log_completion_summary(deletion_count)

    def _log_completion_summary(self, deletion_count: int) -> None:
        """Log and display the purge operation summary."""
        operation_type = "Permanently deleted" if self.permanent else "Moved to trash"

        if deletion_count > 0:
            summary_message = f"{operation_type} {deletion_count} original file(s)"
            console.print(f"[green]{summary_message}[/]")
            logger.info(summary_message)
        else:
            console.print("[yellow]No files were successfully removed[/]")

    def _find_original_files_to_purge(self) -> list[Path]:
        """
        Scan directory for original video files that have optimized counterparts.

        Returns:
            list[Path]: List of original video files ready for purging

        """
        console.print("Scanning for original files with optimized versions..", end="")

        # Collect all video files in directory
        candidate_files: list[Path] = []
        for ext in VIDEO_FILE_EXTENSIONS:
            candidate_files.extend(self.directory.rglob(f"*.{ext}"))

        # Filter to only original files that have optimized versions
        original_files = [
            file
            for file in candidate_files
            if OPTIMIZED_FILENAME_MARKER not in file.name and has_optimized_version(file)
        ]

        console.print(f" found [blue]{len(original_files)}[/] candidate(s)")
        return original_files

    def _has_unfinished_video(self) -> Path | None:
        """
        Check for any unfinished optimization operations in the directory.

        Returns:
            Path | None: Path to unfinished video file if found, None otherwise

        """
        all_videos = find_all_video_files(self.directory)

        for video in all_videos:
            if OPTIMIZING_FILENAME_MARKER in video.name:
                return video

        return None
