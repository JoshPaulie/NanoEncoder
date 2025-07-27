import argparse
from pathlib import Path

from nano_encoder import __version__

CRF_MIN: int = 0
CRF_MAX: int = 51


def valid_crf_range(value: str) -> int:
    """Validate crf argument in optimize command, ensure crf is within bounds."""
    if not value.isdigit():
        msg = f"{value} must be a str which is a digit."
        raise TypeError(msg)
    int_value = int(value)
    if not CRF_MIN <= int_value <= CRF_MAX:
        msg = f"CRF must be between {CRF_MIN} and {CRF_MAX}"
        raise argparse.ArgumentTypeError(msg)
    return int_value


def create_parser() -> argparse.ArgumentParser:
    """Create the primary argument parser."""
    primary_parser = argparse.ArgumentParser(
        prog="NanoEncoder",
        description="A lightweight ffmpeg wrapper to reduce your video collection size (while preserving quality)",
        epilog="Please report any bugs to https://github.com/JoshPaulie/NanoEncoder/issues",
    )

    primary_parser.add_argument(
        "-v",
        "--version",
        action="version",
        version=f"%(prog)s {__version__}",
        help="Print NanoEncoder version and exit",
    )

    primary_parser.add_argument("--dev", action="store_true", help="Include full stacktrace on error")

    subparsers = primary_parser.add_subparsers(dest="command", required=True)

    add_optimize_parser(subparsers)
    add_purge_parser(subparsers)
    add_health_parser(subparsers)
    add_untag_parser(subparsers)

    return primary_parser


def add_optimize_parser(subparsers: argparse._SubParsersAction) -> None:
    """Add the 'optimize' command parser."""
    optimize_parser = subparsers.add_parser("optimize", help="Optimize (re-encode) video files")
    optimize_parser.add_argument("directory", type=Path, help="Path to the target directory")
    optimize_parser.add_argument(
        "--crf",
        type=valid_crf_range,
        default=28,
        help=f"Constant rate factor, between {CRF_MIN}-{CRF_MAX} (default %(default)s))",
    )
    optimize_parser.add_argument(
        "--downscale",
        type=int,
        help="Downscale video resolution to a specified height (e.g., 1080 or 720). "
        "Maintains aspect ratio (default %(default)s)",
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
    optimize_parser.add_argument(
        "--tune",
        type=str,
        choices=["animation", "grain", "stillimage", "fastdecode", "zerolatency"],
        help="Set the tuning profile (default: %(default)s)",
    )
    optimize_parser.add_argument(
        "--force",
        action="store_true",
        dest="force_encode",
        help="Force encode even if video is already in h.265 format",
    )
    optimize_parser.add_argument(
        "--halt-on-increase",
        action="store_true",
        help="Stop processing if any video's size increases after optimization",
    )
    optimize_parser.add_argument(
        "--replace-after",
        "--replace",
        action="store_true",
        dest="replace_after",
        help="Replace the original video file with the optimized version (recycle original; remove '.optimized' tag)",
    )


def add_purge_parser(subparsers: argparse._SubParsersAction) -> None:
    """Add the 'purge' command parser."""
    purge_parser = subparsers.add_parser(
        "purge",
        help="Purge (delete) original video files which have accompanying optimized version",
    )
    purge_parser.add_argument("directory", type=Path, help="Path to the target directory")
    purge_parser.add_argument(
        "--permanent",
        action="store_true",
        dest="permanent",
        help="Permanently delete files instead of sending them to trash",
    )
    purge_parser.add_argument(
        "--skip",
        "--skip-confirmation",
        "--force",
        action="store_true",
        dest="skip_confirmation",
        help="Skip confirmation when purging original files (DANGEROUS!)",
    )


def add_health_parser(subparsers: argparse._SubParsersAction) -> None:
    """Add the 'health' command parser."""
    health_check_parser = subparsers.add_parser(
        "health",
        help="After encoding, check the quality of your optimized files",
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


def add_untag_parser(subparsers: argparse._SubParsersAction) -> None:
    """Add the 'untag' command parser."""
    untag_parser = subparsers.add_parser("untag", help="Remove '.optimized' from file names")
    untag_parser.add_argument("directory", type=Path, help="Path to the target directory")
