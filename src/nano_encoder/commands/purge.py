from pathlib import Path

from rich.progress import track
from send2trash import send2trash

from ..cli import PurgeArgs
from ..console import console
from ..logger import logger
from ..utils import VIDEO_FILE_EXTENSIONS, find_all_video_files, has_optimized_version
from .base_command import BaseCommand


def handle_purge_command(args: PurgeArgs) -> None:
    try:
        PurgeDirectory(args).execute()
    except (FileNotFoundError, NotADirectoryError, ValueError) as e:
        logger.error(str(e))
        raise
    except KeyboardInterrupt:
        message = "User cancelled purge operation."
        console.print(f"\n{message}\n")
        logger.info(message)


class PurgeDirectory(BaseCommand):
    def __init__(self, args: PurgeArgs) -> None:
        super().__init__(args.directory)
        self.permanent = args.permanent
        self.skip_confirmation = args.skip_confirmation
        self.original_files = self._find_original_files_to_purge()

    def execute(self) -> None:
        """Execute the purge operation."""
        if unfinished_video := self._has_unfinished_video():
            console.print(
                f"Encountered unfinished video: '{unfinished_video}', unable to purge originals. "
                "Remove this file, or re-run the encode command against the directory to resolve."
            )
            logger.error(f"Unfinished video: {unfinished_video.absolute()}")
            console.print(f"\n[green]Suggested fix[/]:\nnen optimize {self.directory.absolute()}")
            return

        if not self.original_files:
            console.print(f"No originals with optimized versions found in '{self.directory.name}'")
            return

        logger.info(f"Found the following to purge: {', '.join([p.name for p in self.original_files])}")

        message = (
            "Permanently delete these ORIGINAL files?"
            if self.permanent
            else "Send these ORIGINAL files to recycling bin/trash?"
        )

        # Skip confirmation if flag is set, otherwise ask for confirmation
        if self.skip_confirmation or self._confirm_purge(message):
            if self.skip_confirmation:
                console.print("[red]Forcefully purging")
            self._purge_files()

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

    def _confirm_purge(self, message: str) -> bool:
        """Show files to be purged and confirm the operation."""
        console.print(f"Found {len(self.original_files)} originals with optimized versions:")
        for orig in self.original_files:
            console.print(f" - {orig.name} → {orig.with_name(f'{orig.stem}.optimized{orig.suffix}').name}")
        console.print()

        return self._confirm_action(message)

    def _purge_files(self) -> None:
        """Delete or move files to trash based on permanent flag."""
        for orig in self.original_files:
            console.print(f"Deleting '{orig}'.")
            logger.info(f"Purged '{orig}'.")
            orig.unlink() if self.permanent else send2trash(orig)

        purge_type_msg = "Permanently" if self.permanent else "Sent to recycling bin"
        purged_message = f"Purged {len(self.original_files)} original files ({purge_type_msg})"
        console.print(purged_message)
        logger.info(purged_message)
