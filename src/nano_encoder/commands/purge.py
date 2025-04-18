from pathlib import Path

from rich.progress import track
from send2trash import send2trash

from ..console import console
from ..logger import logger
from ..utils import VIDEO_FILE_EXTENSIONS, find_all_video_files, has_optimized_version


def handle_purge_command(args) -> None:
    try:
        PurgeDirectory(args.directory, args.permanent).purge()
    except (FileNotFoundError, NotADirectoryError, ValueError) as e:
        logger.error(str(e))
        raise
    except KeyboardInterrupt:
        message = "User cancelled purge operation."
        console.print(f"\n{message}\n")
        logger.info(message)


class PurgeDirectory:
    """Manages purging of original video files which have optimized versions."""

    def __init__(self, directory: Path, permanent: bool = False) -> None:
        self.directory = directory
        self.permanent = permanent

    def _find_original_files_to_purge(self) -> list[Path]:
        """Scan directory for candidate original video files to purge."""
        console.print("Looking for original files with optimized files..")
        candidates = []
        for ext in VIDEO_FILE_EXTENSIONS:
            candidates.extend(self.directory.rglob(f"*.{ext}"))

        original_files = []
        for file in track(candidates, "Finding pairs..", transient=True):
            if "optimized" not in file.name and has_optimized_version(file):
                original_files.append(file)
        return original_files

    def _has_unfinished_video(self) -> Path | None:
        """Check if there's any unfinished video in the directory."""
        videos = find_all_video_files(self.directory)
        for video in videos:
            if ".optimizing." in video.name:
                return video
        return None

    def _confirm_deletion(self, original_files: list[Path]) -> bool:
        """Confirm deletion by listing originals and prompting user."""
        console.print(f"Found {len(original_files)} originals with optimized versions:")
        for orig in original_files:
            console.print(f" - {orig.name} → {orig.with_name(f'{orig.stem}.optimized{orig.suffix}').name}")
        print()

        confirm = console.input(
            "Confirm deletion of these ORIGINAL files? [y/N]: "
            if self.permanent
            else "Confirm sending of these ORIGINAL files to recycling bin/trash? [y/N]: "
        )
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
            console.print(f"\n[green]Suggested fix[/]:\nnen optimize {self.directory.absolute()}")
            return

        originals = self._find_original_files_to_purge()

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
            orig.unlink() if self.permanent else send2trash(orig)

        purged_message = f"Purged {len(originals)} original files"
        print(purged_message)
        logger.info(purged_message)
