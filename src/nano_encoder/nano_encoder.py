import shutil
import sys
import traceback

from .cli import (
    HealthArgs,
    OptimizeArgs,
    PurgeArgs,
    UntagArgs,
    dataclass_from_namespace,
    primary_parser,
)
from .commands.healthcheck import handle_health_command
from .commands.optimize import handle_optimize_command
from .commands.purge import handle_purge_command
from .commands.untag import handle_untag_command
from .console import console
from .logger import logger


def welcome_message() -> None:
    console.print()
    console.rule("Welcome to NanoEncoder!")
    console.print()


def ffmpeg_check() -> None:
    """Check if FFmpeg is installed."""
    required_apps = ["ffmpeg", "ffprobe"]
    for app in required_apps:
        if not shutil.which(app):
            print(f"NanoEncoder depends on {app}, which is not installed on this system.")
            print("Install from here: https://www.ffmpeg.org/download.html")
            if app == "ffprobe":
                print("The ffprobe binary is included with the FFmpeg installation.")
            logger.error(f"System doesn't have {app} installed.")
            sys.exit(1)


def main() -> None:
    parser = primary_parser
    args = parser.parse_args()

    welcome_message()
    ffmpeg_check()

    try:
        match args.command:
            case "optimize":
                optimize_args = dataclass_from_namespace(OptimizeArgs, args)
                handle_optimize_command(optimize_args)

            case "purge":
                purge_args = dataclass_from_namespace(PurgeArgs, args)
                handle_purge_command(purge_args)

            case "health":
                health_args = dataclass_from_namespace(HealthArgs, args)
                handle_health_command(health_args)

            case "untag":
                untag_args = dataclass_from_namespace(UntagArgs, args)
                handle_untag_command(untag_args)
    except Exception as e:  # noqa: BLE001 (todo)
        if args.dev:
            traceback.print_exc()
        parser.exit(1, str(e) + "\n")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        console.print()
