import argparse
from pathlib import Path

from nano_encoder import __version__

from .utils import CRF_MAX, CRF_MIN


def create_parser() -> argparse.ArgumentParser:
    # Primary parent parser
    parser = argparse.ArgumentParser(
        prog="NanoEncoder",
        description="A lightweight ffmpeg wrapper to reduce your video collection size (while preserving quality)",
        epilog="Please report any bugs to https://github.com/JoshPaulie/NanoEncoder/issues",
    )

    # Version flag
    parser.add_argument(
        "-v",
        "--version",
        action="version",
        version=f"%(prog)s {__version__}",
        help="Print NanoEncoder version and exit",
    )

    parser.add_argument("--dev", action="store_true", help="Include full stacktrace on error")

    # Subparser
    subparsers = parser.add_subparsers(dest="command", required=True)

    # Optimize subcommand
    optimize_parser = subparsers.add_parser("optimize", help="Optimize (re-encode) video files")
    optimize_parser.add_argument("directory", type=Path, help="Path to the target directory")
    optimize_parser.add_argument(
        "--crf",
        type=int,
        default=28,
        help=f"Constant rate factor ({CRF_MIN}-{CRF_MAX}, default: %(default)s)",
    )
    optimize_parser.add_argument(
        "--downscale",
        type=int,
        help="Downscale video resolution to a specified height (e.g., 1080 or 720). Maintains aspect ratio.",
    )
    optimize_parser.add_argument(
        "--preset",
        type=str,
        choices=[
            "ultrafast",
            "superfast",
            "veryfast",
            "faster",
            "fast",
            "medium",
            "slow",
            "slower",
            "veryslow",
        ],
        default="medium",
        help="Set the encoding speed/efficiency preset (default: %(default)s)",
    )

    # Purge subcommand
    purge_parser = subparsers.add_parser(
        "purge", help="Purge (delete) original video files which have accompanying optimized version"
    )
    purge_parser.add_argument("directory", type=Path, help="Path to the target directory")
    purge_parser.add_argument(
        "-p",
        "--perm",
        "--permanent",
        action="store_true",
        help="Permanently delete files instead of sending them to trash",
    )

    # Healthcheck subcommand
    health_check_parser = subparsers.add_parser(
        "health", help="After encoding, check the quality of your optimized files"
    )
    health_check_parser.add_argument(
        "directory",
        type=Path,
        help="Check a small sample of original and optimized files, comparing similarity",
    )
    health_check_parser.add_argument(
        "--sample-ratio",
        type=float,
        help="Percentage of video to check (ignored if --all is set)",
        default=0.05,
    )
    health_check_parser.add_argument(
        "--all",
        action="store_true",
        help="Check all video pairs rather than a sample",
    )

    # Untag subcommand
    untag_parser = subparsers.add_parser("untag", help="Remove '.optimized' from file names")
    untag_parser.add_argument("directory", type=Path, help="Path to the target directory")

    return parser
