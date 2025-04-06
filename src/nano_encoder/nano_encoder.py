import shutil
import sys

from .cli import create_parser
from .encode import handle_encode_command
from .purge import handle_purge_command
from .utils import print_log


def welcome_message() -> None:
    print("\nWelcome to NanoEncoder!\n")


def ffmpeg_check() -> None:
    """
    Check if FFmpeg is installed
    """
    required_apps = ["ffmpeg", "ffprobe"]
    for app in required_apps:
        if not shutil.which(app):
            print_log(f"NanoEncoder depends on {app}, which is not installed on this system.", "error")
            print("Install from here: https://www.ffmpeg.org/download.html")
            sys.exit(1)


def main() -> None:
    parser = create_parser()
    args = parser.parse_args()

    welcome_message()
    ffmpeg_check()

    try:
        match args.command:
            case "encode":
                handle_encode_command(args)
            case "purge":
                handle_purge_command(args)
    except Exception as e:
        parser.exit(1, str(e) + "\n")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print()
