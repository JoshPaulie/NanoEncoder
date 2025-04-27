import logging
from pathlib import Path

NANO_ENCODER_LOG_FILE: Path = Path.cwd() / "NanoEncoder.log"
DEBUG_LOG_FILE: Path = Path.cwd() / "NanoEncoder_ffmpeg.log"


class NanoEncoderLogger(logging.Logger):
    """Custom logger."""

    def _stringify(self, msg: str | list[str]) -> str:
        if isinstance(msg, list):
            return " ".join(str(m) for m in msg)
        return str(msg)

    def debug(self, msg: str | list[str], *args, **kwargs):
        super().debug(self._stringify(msg), *args, **kwargs)

    def info(self, msg: str | list[str], *args, **kwargs):
        super().info(self._stringify(msg), *args, **kwargs)

    def warning(self, msg: str | list[str], *args, **kwargs):
        super().warning(self._stringify(msg), *args, **kwargs)

    def error(self, msg: str | list[str], *args, **kwargs):
        super().error(self._stringify(msg), *args, **kwargs)

    def critical(self, msg: str | list[str], *args, **kwargs):
        super().critical(self._stringify(msg), *args, **kwargs)


# Configure logging
logging.setLoggerClass(NanoEncoderLogger)
logger: NanoEncoderLogger = logging.getLogger("NanoEncoder")
logger.setLevel(logging.INFO)

# File handler
file_handler = logging.FileHandler(NANO_ENCODER_LOG_FILE, encoding="utf-8")
formatter = logging.Formatter("%(asctime)s - %(levelname)-8s - %(message)s")
file_handler.setFormatter(formatter)
logger.addHandler(file_handler)
