from pathlib import Path

from rich.table import Table

from ..cli import UntagArgs
from ..console import console
from ..logger import logger
from ..utils import find_all_video_files
from .base_command import BaseCommand


def handle_untag_command(args: UntagArgs) -> None:
    try:
        UntagDirectory(args).execute()
    except (FileNotFoundError, NotADirectoryError, ValueError) as e:
        logger.error(str(e))
        raise
    except KeyboardInterrupt:
        message = "User cancelled untag operation."
        logger.info(message)


class UntagDirectory(BaseCommand):
    def __init__(self, args: UntagArgs) -> None:
        super().__init__(args.directory)
        self.args = args
        self.videos = find_all_video_files(self.directory, optimized_only=True)
        if not self.videos:
            raise ValueError(f"There are no videos to untag in '{self.directory.name}'.")

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
        return video.with_name(video.name.replace(".optimized", ""))
