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

    # Subparser
    subparsers = parser.add_subparsers(dest="command", required=True)

    # Encode subcommand
    encode_parser = subparsers.add_parser("encode", help="Encode video files")
    encode_parser.add_argument("directory", type=Path, help="Path to the target directory")
    encode_parser.add_argument(
        "--crf",
        type=int,
        default=23,
        help=f"Constant rate factor ({CRF_MIN}-{CRF_MAX}, default: %(default)s)",
    )

    # Purge subcommand
    purge_parser = subparsers.add_parser(
        "purge", help="Purge (delete) original video files which have accompanying optimized version"
    )
    purge_parser.add_argument("directory", type=Path, help="Path to the target directory")

    return parser
