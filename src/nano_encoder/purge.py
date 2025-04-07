from pathlib import Path
from typing import List, Optional

from .logger import logger
from .utils import VIDEO_FILE_EXTENSIONS, find_all_video_files, has_optimized_version


def handle_purge_command(args) -> None:
    purge_originals(args.directory)


def _find_originals_to_purge(directory: Path) -> List[Path]:
    candidates = []
    for ext in VIDEO_FILE_EXTENSIONS:
        candidates.extend(directory.rglob(f"*.{ext}"))

    originals = []
    for file in candidates:
        if "optimized" not in file.name and has_optimized_version(file):
            originals.append(file)
    return originals


def _has_unfinished_video(directory: Path) -> Optional[Path]:
    videos = find_all_video_files(directory)
    for video in videos:
        if ".optimizing." in video.name:
            return video
    return None


def purge_originals(directory: Path) -> None:
    if unfinished_video := _has_unfinished_video(directory):
        error_message = f"Encountered unfinished video: '{unfinished_video}', unable to purge originals. Remove this file, or re-run the encode command against the directory to resolve."
        print(error_message)
        logger.error(error_message)
        print(f"\nSuggested fix:\nnen encode {directory.absolute()}")
        return

    originals = _find_originals_to_purge(directory)

    if not originals:
        no_originals_message = f"No originals with optimized versions found in '{directory.name}'"
        print(no_originals_message)
        return

    logger.info(f"Found the following to purge: {', '.join([p.name for p in originals])}")
    print(f"Found {len(originals)} originals with optimized versions:")
    for orig in originals:
        print(f" - {orig.name} -> {orig.with_name(f'{orig.stem}.optimized{orig.suffix}').name}")
    print()

    confirm = input("Confirm deletion of these ORIGINAL files? (Cannot be undone) [y/n]: ").lower()
    if confirm != "y":
        print("Deletion cancelled by user.")
        logger.info("User declined to purge originals.")
        return

    for orig in originals:
        print(f"Deleting '{orig}'.")
        logger.info(f"Purged '{orig}'.")
        orig.unlink()

    purged_message = f"Purged {len(originals)} original files"
    print(purged_message)
    logger.info(purged_message)
