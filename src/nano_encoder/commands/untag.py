from pathlib import Path

from rich.table import Table

from nano_encoder.cli import UntagArgs
from nano_encoder.console import console
from nano_encoder.logger import logger
from nano_encoder.utils import find_all_video_files

from .base_command import BaseCommand


def handle_untag_command(args: UntagArgs) -> None:
    """Handle untag command and errors."""
    try:
        UntagDirectory(args).execute()
    except (FileNotFoundError, NotADirectoryError, ValueError, UntaggedVideoOverwriteError) as e:
        logger.error(str(e))
        raise
    except KeyboardInterrupt:
        message = "User cancelled untag operation."
        console.print(f"\n{message}\n")
        logger.info(message)


class UntaggedVideoOverwriteError(Exception):
    """
    An exception for when the "would-be-untagged" would overwrite and existing file.

    Effectively, this means it won't overwrite the original if it's still present.
    """

    def __init__(self, video_name: str) -> None:
        super().__init__(f"{video_name} already exists. Consider running purge command.")


class UntagDirectory(BaseCommand):
    """Encapsulates untag command functionally."""

    def __init__(self, args: UntagArgs) -> None:
        super().__init__(args.directory)
        self.args = args
        self.videos = find_all_video_files(self.directory, optimized_only=True)
        if not self.videos:
            msg = f"There are no videos to untag in '{self.directory.name}'."
            raise ValueError(msg)

    def execute(self) -> None:
        """Execute the untag operation."""
        if self._confirm_untag():
            for video in self.videos:
                video.rename(self._untagged_name(video))

    def _confirm_untag(self) -> bool:
        """Show comparison table and confirm the untag operation."""
        comparison_table = Table("Current", "Untagged")
        for video in self.videos:
            comparison_table.add_row(video.name, self._untagged_name(video).name)
        console.print(comparison_table)

        return self._confirm_action("Are you sure you want to rename?", warning="[i]Cannot be undone![/]")

    @staticmethod
    def _untagged_name(video: Path) -> Path:
        """Generate the untagged version of the filename."""
        untagged_video = video.with_name(video.name.replace(".optimized", ""))
        if untagged_video.exists():
            raise UntaggedVideoOverwriteError(untagged_video.name)
        return untagged_video
