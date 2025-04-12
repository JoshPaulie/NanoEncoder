import logging
from pathlib import Path

NANO_ENCODER_LOG_FILE: Path = Path.cwd() / "NanoEncoder.log"
DEBUG_LOG_FILE: Path = Path.cwd() / "NanoEncoder_ffmpeg.log"


class NanoEncoderLogger(logging.Logger):
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


logging.setLoggerClass(NanoEncoderLogger)
logger: NanoEncoderLogger = logging.getLogger("NanoEncoder")  # type: ignore
logger.setLevel(logging.INFO)
file_handler = logging.FileHandler(NANO_ENCODER_LOG_FILE)
formatter = logging.Formatter("%(asctime)s - %(levelname)-8s - %(message)s")
file_handler.setFormatter(formatter)
logger.addHandler(file_handler)
