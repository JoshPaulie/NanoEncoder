"""Untag command functionality for removing optimization markers from filenames."""

import argparse
from dataclasses import dataclass
from pathlib import Path

from rich.table import Table

from nano_encoder.console import console
from nano_encoder.logger import logger
from nano_encoder.utils import find_all_video_files

from .base_command import BaseCommand

# Constants
OPTIMIZED_FILENAME_MARKER = ".optimized"
UNTAG_CONFIRMATION_MESSAGE = "Are you sure you want to rename?"
UNTAG_WARNING_MESSAGE = "[i]Cannot be undone![/]"
TABLE_COLUMN_CURRENT = "Current"
TABLE_COLUMN_UNTAGGED = "Untagged"


@dataclass(frozen=True)
class UntagArgs:
    """
    Arguments for the untag command operation.

    Attributes:
        directory: Target directory containing optimized videos to untag

    """

    directory: Path


def handle_untag_command(args: argparse.Namespace) -> None:
    """Handle untag command and errors."""
    try:
        UntagDirectory(UntagArgs(directory=args.directory)).execute()
    except (FileNotFoundError, NotADirectoryError, ValueError, UntaggedVideoOverwriteError) as e:
        logger.error(str(e))
        raise
    except KeyboardInterrupt:
        message = "User cancelled untag operation."
        console.print(f"\n{message}\n")
        logger.info(message)


class UntaggedVideoOverwriteError(Exception):
    """
    Exception raised when untag operation would overwrite an existing file.

    This prevents accidental overwriting of original files that are still present.
    """

    def __init__(self, video_name: str) -> None:
        """
        Initialize the exception.

        Args:
            video_name: Name of the video file that would be overwritten

        """
        message = f"{video_name} already exists. Consider running purge command."
        super().__init__(message)


class UntagDirectory(BaseCommand):
    """
    Handles untag operations for removing optimization markers from video filenames.

    This class processes optimized video files in a directory and removes the
    optimization markers from their filenames, effectively "untagging" them.
    """

    def __init__(self, args: UntagArgs) -> None:
        """
        Initialize the untag directory handler.

        Args:
            args: UntagArgs containing the target directory

        Raises:
            ValueError: If no optimized videos are found in the directory

        """
        super().__init__(args.directory)
        self.args = args
        self.videos = find_all_video_files(self.directory, optimized_only=True)

        if not self.videos:
            msg = f"There are no videos to untag in '{self.directory.name}'."
            raise ValueError(msg)

    def execute(self) -> None:
        """
        Execute the untag operation.

        Shows a preview of the changes and processes the untag operation
        if confirmed by the user.
        """
        if self._confirm_untag():
            self._perform_untag_operation()

    def _perform_untag_operation(self) -> None:
        """Perform the actual file renaming operations."""
        renamed_count = 0

        for video in self.videos:
            try:
                new_name = self._generate_untagged_name(video)
                video.rename(new_name)
                renamed_count += 1
                console.print(f"Renamed: {video.name} → {new_name.name}")
                logger.info(f"Successfully untagged: {video} → {new_name}")
            except (OSError, UntaggedVideoOverwriteError) as e:
                error_msg = f"Failed to rename '{video.name}': {e}"
                console.print(f"[red]Error: {error_msg}[/]")
                logger.error(error_msg)

        # Log completion summary
        if renamed_count > 0:
            summary_msg = f"Successfully untagged {renamed_count} video file(s)"
            console.print(f"[green]{summary_msg}[/]")
            logger.info(summary_msg)
        else:
            console.print("[yellow]No files were successfully renamed[/]")

    def _confirm_untag(self) -> bool:
        """
        Display comparison table and confirm the untag operation.

        Returns:
            bool: True if user confirms the operation

        """
        comparison_table = Table(TABLE_COLUMN_CURRENT, TABLE_COLUMN_UNTAGGED)

        for video in self.videos:
            untagged_name = self._generate_untagged_name(video)
            comparison_table.add_row(video.name, untagged_name.name)

        console.print(comparison_table)
        return self._confirm_action(UNTAG_CONFIRMATION_MESSAGE, warning=UNTAG_WARNING_MESSAGE)

    def _generate_untagged_name(self, video: Path) -> Path:
        """
        Generate the untagged version of the filename.

        Args:
            video: Path to the video file to untag

        Returns:
            Path: New path with optimization marker removed

        Raises:
            UntaggedVideoOverwriteError: If the untagged name would overwrite an existing file

        """
        untagged_video = video.with_name(video.name.replace(OPTIMIZED_FILENAME_MARKER, ""))

        if untagged_video.exists():
            raise UntaggedVideoOverwriteError(untagged_video.name)

        return untagged_video
