import abc
from pathlib import Path
from typing import Dict, Tuple, Optional


class Synchronizer(abc.ABC):
    """Abstract base class for directory synchronization."""

    @abc.abstractmethod
    def run_sync(self, mappings: Dict[Path, Path], pandoc_config: Tuple[Optional[str], Optional[str]]) -> None:
        """
        Runs the synchronization process for all configured mappings.

        Args:
            mappings: A dictionary where keys are input directories and values are output directories.
            pandoc_config: A tuple containing the pandoc executable path (or None for default)
                           and additional pandoc arguments string (or None).
        """
        pass
