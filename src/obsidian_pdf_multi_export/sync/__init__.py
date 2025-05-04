import abc
from pathlib import Path
from typing import Dict, Tuple, Optional, Literal


ConverterChoice = Literal["pandoc", "typst"]
ConverterConfig = Tuple[Optional[str], Optional[str]] # (path, args_string)


class Synchronizer(abc.ABC):
    """Abstract base class for directory synchronization."""

    @abc.abstractmethod
    def run_sync(
        self,
        mappings: Dict[Path, Path],
        converter: ConverterChoice,
        converter_config: ConverterConfig,
    ) -> None:
        """
        Runs the synchronization process for all configured mappings using the specified converter.

        Args:
            mappings: A dictionary where keys are input directories and values are output directories.
            converter: The chosen converter ('pandoc' or 'typst').
            converter_config: A tuple containing the converter executable path (or None for default)
                              and additional arguments string (or None).
        """
        pass
