from pathlib import Path

from rich.progress import track

from .console import console
from .logger import logger
from .utils import VIDEO_FILE_EXTENSIONS, find_all_video_files, has_optimized_version


def handle_purge_command(args) -> None:
    try:
        PurgeDirectory(args.directory).purge()
    except (FileNotFoundError, NotADirectoryError, ValueError) as e:
        logger.error(str(e))
        raise
    except KeyboardInterrupt:
        message = "User cancelled purge operation."
        console.print(f"\n{message}\n")
        logger.info(message)


class PurgeDirectory:
    """Manages purging of original video files which have optimized versions."""

    def __init__(self, directory: Path) -> None:
        self.directory = directory

    def _find_originals_to_purge(self) -> list[Path]:
        """Scan directory for candidate original video files to purge."""
        console.print("Looking for original files with optimized files..")
        candidates = []
        for ext in VIDEO_FILE_EXTENSIONS:
            candidates.extend(self.directory.rglob(f"*.{ext}"))

        originals = []
        for file in track(candidates, "Finding pairs..", transient=True):
            if "optimized" not in file.name and has_optimized_version(file):
                originals.append(file)
        return originals

    def _has_unfinished_video(self) -> Path | None:
        """Check if there's any unfinished video in the directory."""
        videos = find_all_video_files(self.directory)
        for video in videos:
            if ".optimizing." in video.name:
                return video
        return None

    def _confirm_deletion(self, originals: list[Path]) -> bool:
        """Confirm deletion by listing originals and prompting user."""
        console.print(f"Found {len(originals)} originals with optimized versions:")
        for orig in originals:
            console.print(f" - {orig.name} → {orig.with_name(f'{orig.stem}.optimized{orig.suffix}').name}")
        print()

        confirm = console.input("Confirm deletion of these ORIGINAL files? ([i]Cannot be undone![/]) [y/N]: ")
        if confirm.lower() != "y":
            console.print("Got it! No files deleted.")
            logger.info("User declined to purge originals.")
            return False
        return True

    def purge(self) -> None:
        """Main method to purge original files if conditions are met."""
        if unfinished_video := self._has_unfinished_video():
            console.print(
                (
                    f"Encountered unfinished video: '{unfinished_video}', unable to purge originals. "
                    "Remove this file, or re-run the encode command against the directory to resolve."
                )
            )
            logger.error(f"Unfinished video: {unfinished_video.absolute()}")
            console.print(f"\n[green]Suggested fix[/]:\nnen encode {self.directory.absolute()}")
            return

        originals = self._find_originals_to_purge()

        if not originals:
            no_originals_message = f"No originals with optimized versions found in '{self.directory.name}'"
            print(no_originals_message)
            return

        logger.info(f"Found the following to purge: {', '.join([p.name for p in originals])}")

        if not self._confirm_deletion(originals):
            return

        for orig in originals:
            print(f"Deleting '{orig}'.")
            logger.info(f"Purged '{orig}'.")
            orig.unlink()

        purged_message = f"Purged {len(originals)} original files"
        print(purged_message)
        logger.info(purged_message)
