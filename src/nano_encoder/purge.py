from pathlib import Path
from typing import List, Optional

from .utils import VIDEO_FILE_EXTENSIONS, find_all_video_files, has_optimized_version, print_log


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
        print_log(
            f"Encountered unfinished video: '{unfinished_video}', unable to purge originals. Remove this file, or re-run the encode command against the directory to resolve.",
            "error",
        )
        print(f"\nSuggested fix:\nnen encode {directory.absolute()}")
        return

    originals = _find_originals_to_purge(directory)

    if not originals:
        print_log(f"No originals with optimized versions found in '{directory.name}'")
        return

    print_log(f"Found the following to purge: {', '.join([p.name for p in originals])}", log_only=True)
    print(f"Found {len(originals)} originals with optimized versions:")
    for orig in originals:
        print(f" - {orig.name} -> {orig.with_name(f'{orig.stem}.optimized{orig.suffix}').name}")
    print()

    confirm = input("Confirm deletion of these ORIGINAL files? (Cannot be undone) [y/n]: ").lower()
    if confirm != "y":
        print_log("Deletion cancelled by user.")
        return

    for orig in originals:
        print(f"Deleting '{orig}'.")
        print_log(f"Purged '{orig}'.", log_only=True)
        orig.unlink()

    print_log(f"Purged {len(originals)} original files")
