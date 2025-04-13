from pathlib import Path

from rich.table import Table

from ..console import console
from ..logger import logger
from ..utils import find_all_video_files, validate_directory


def handle_untag_command(args) -> None:
    try:
        validate_directory(args.directory)
        UntagDirectory(args.directory).untag()
    except (FileNotFoundError, NotADirectoryError, ValueError) as e:
        logger.error(str(e))
        raise
    except KeyboardInterrupt:
        message = "User cancelled untag operation."
        logger.info(message)


class UntagDirectory:
    def __init__(self, directory: Path) -> None:
        self.directory = directory
        self.videos = find_all_video_files(self.directory, optimized_only=True)
        if not self.videos:
            raise ValueError(f"There are no videos to untag in '{self.directory.name}'.")  # todo

    def untag(self):
        if self._confirm_untag_directory():
            for video in self.videos:
                video.rename(self._untagged_name(video))

    def _confirm_untag_directory(self):
        comparison_table = Table("Current", "Untagged")
        for video in self.videos:
            comparison_table.add_row(video.name, self._untagged_name(video).name)
        console.print(comparison_table)

        console.print("The above videos will be renamed.")
        confirm = console.input("Are you sure you want to rename? ([i]Cannot be undone![/]) [y/N]: ")
        if confirm.lower() != "y":
            console.print("Got it! We'll keep the file names as they are.")
            logger.info("User declined to purge originals.")
            return False
        return True

    @staticmethod
    def _untagged_name(video: Path):
        return video.with_name(video.name.replace(".optimized", ""))
