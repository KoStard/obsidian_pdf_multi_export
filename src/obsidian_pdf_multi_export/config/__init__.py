import abc
from pathlib import Path
from typing import Dict, Optional, Tuple


class ConfigManager(abc.ABC):
    """Abstract base class for configuration management."""

    @abc.abstractmethod
    def get_mappings(self) -> Dict[Path, Path]:
        """Get the configured input/output directory mappings."""
        pass

    @abc.abstractmethod
    def add_mapping(self, input_dir: Path, output_dir: Path) -> None:
        """Add or update a directory mapping."""
        pass

    @abc.abstractmethod
    def remove_mapping(self, input_dir: Path) -> bool:
        """Remove a directory mapping. Returns True if removed, False otherwise."""
        pass

    @abc.abstractmethod
    def get_pandoc_config(self) -> Tuple[Optional[str], Optional[str]]:
        """Get the configured pandoc path and arguments."""
        pass

    @abc.abstractmethod
    def set_pandoc_config(self, path: Optional[Path] = None, args: Optional[str] = None) -> None:
        """Set the pandoc executable path and optional arguments."""
        pass
