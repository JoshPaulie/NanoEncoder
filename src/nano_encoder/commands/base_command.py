from abc import ABC, abstractmethod
from pathlib import Path

from nano_encoder.console import console
from nano_encoder.logger import logger
from nano_encoder.utils import validate_directory


class BaseCommand(ABC):
    """Base class for all NanoEncoder commands."""

    def __init__(self, directory: Path) -> None:
        """Initialize base command with directory validation."""
        self.directory = directory.resolve()
        self._validate_directory()

    def _validate_directory(self) -> None:
        """Validate the provided directory exists and is accessible."""
        try:
            validate_directory(self.directory)
        except (FileNotFoundError, NotADirectoryError) as e:
            logger.error(str(e))
            msg = f"Invalid directory: {self.directory}"
            raise ValueError(msg) from e

    def _confirm_action(self, message: str, warning: str | None = None) -> bool:
        """Prompt user for confirmation with optional warning message."""
        if warning:
            console.print(warning)
        confirm = console.input(f"{message} [y/N]: ")
        if confirm.lower() != "y":
            console.print("Operation canceled.")
            logger.info("User declined the operation.")
            return False
        return True

    @abstractmethod
    def execute(self) -> None:
        """Execute the command. Must be implemented by subclasses."""
