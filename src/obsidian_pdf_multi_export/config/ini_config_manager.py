import configparser
import json
import logging
import os
from pathlib import Path
from typing import Dict, Optional, Tuple

from . import ConfigManager

logger = logging.getLogger(__name__)


DEFAULT_CONFIG_DIR = Path.home() / ".config" / "obsidian_pdf_multi_export"
DEFAULT_CONFIG_FILE = DEFAULT_CONFIG_DIR / "config.ini"
MAPPINGS_SECTION = "Mappings"
MAPPINGS_JSON_KEY = "data"  # Key to store the JSON blob
PANDOC_SECTION = "Pandoc"
PANDOC_PATH_KEY = "path"
PANDOC_ARGS_KEY = "args"
TYPST_SECTION = "Typst"
TYPST_PATH_KEY = "path"
TYPST_ARGS_KEY = "args"


class IniConfigManager(ConfigManager):
    """Manages configuration using an INI file."""

    def __init__(self, config_path: Path = DEFAULT_CONFIG_FILE):
        self.config_path = config_path
        # Use the standard parser now
        self.config = configparser.ConfigParser()
        self._ensure_config_exists()
        self.config.read(self.config_path)
        logger.debug(f"Initialized IniConfigManager with path: {self.config_path}")

    def _ensure_config_exists(self):
        """Ensures the configuration directory and file exist."""
        if not self.config_path.exists():
            logger.info(f"Configuration file not found at {self.config_path}. Creating...")
            try:
                self.config_path.parent.mkdir(parents=True, exist_ok=True)
                # Create a default structure
                self.config[MAPPINGS_SECTION] = {
                    MAPPINGS_JSON_KEY: "{}" # Store an empty JSON object string
                }
                self.config[PANDOC_SECTION] = {
                    PANDOC_PATH_KEY: "pandoc",  # Default to pandoc in PATH
                    PANDOC_ARGS_KEY: "",
                }
                self.config[TYPST_SECTION] = {
                    TYPST_PATH_KEY: "typst", # Default to typst in PATH
                    TYPST_ARGS_KEY: "",
                }
                with self.config_path.open("w") as configfile:
                    self.config.write(configfile)
                logger.info(f"Created default configuration file at {self.config_path}")
            except OSError as e:
                logger.error(f"Failed to create configuration directory or file at {self.config_path}: {e}")
                raise

    def _save_config(self):
        """Saves the current configuration to the file."""
        try:
            with self.config_path.open("w") as configfile:
                self.config.write(configfile)
            logger.debug(f"Configuration saved to {self.config_path}")
        except OSError as e:
            logger.error(f"Failed to save configuration file at {self.config_path}: {e}")
            raise

    def _load_mappings_dict(self) -> Dict[str, str]:
        """Loads the raw string-to-string dictionary from the JSON blob."""
        if not self.config.has_section(MAPPINGS_SECTION) or not self.config.has_option(MAPPINGS_SECTION, MAPPINGS_JSON_KEY):
            return {}
        try:
            mappings_json = self.config.get(MAPPINGS_SECTION, MAPPINGS_JSON_KEY)
            mappings_dict = json.loads(mappings_json)
            if not isinstance(mappings_dict, dict):
                 logger.warning(f"Invalid format for mappings JSON in config file. Expected a dictionary, got {type(mappings_dict)}. Returning empty mappings.")
                 return {}
            # Ensure keys and values are strings, though json.loads should handle this
            return {str(k): str(v) for k, v in mappings_dict.items()}
        except json.JSONDecodeError:
            logger.error(f"Failed to parse mappings JSON from config file. Content: '{mappings_json}'. Returning empty mappings.")
            return {}
        except Exception as e:
            logger.error(f"Unexpected error loading mappings dictionary: {e}")
            return {}

    def _save_mappings_dict(self, mappings_dict: Dict[str, str]) -> None:
        """Saves the raw string-to-string dictionary as a JSON blob."""
        if not self.config.has_section(MAPPINGS_SECTION):
            self.config.add_section(MAPPINGS_SECTION)
        try:
            mappings_json = json.dumps(mappings_dict, indent=4) # Use indent for readability in the ini file
            self.config.set(MAPPINGS_SECTION, MAPPINGS_JSON_KEY, mappings_json)
            self._save_config()
        except TypeError as e:
             logger.error(f"Failed to serialize mappings dictionary to JSON: {e}")
             # Avoid saving corrupted data
        except Exception as e:
             logger.error(f"Unexpected error saving mappings dictionary: {e}")


    def get_mappings(self) -> Dict[Path, Path]:
        """Get the configured input/output directory mappings."""
        mappings_dict = self._load_mappings_dict()
        resolved_mappings = {}
        for input_str, output_str in mappings_dict.items():
            try:
                # Resolve paths relative to home if they start with ~
                input_path = Path(os.path.expanduser(input_str)).resolve()
                output_path = Path(os.path.expanduser(output_str)).resolve()
                resolved_mappings[input_path] = output_path
            except Exception as e:
                logger.warning(f"Skipping invalid mapping from config: '{input_str}' -> '{output_str}'. Error resolving paths: {e}")
        logger.debug(f"Retrieved and resolved mappings: {resolved_mappings}")
        return resolved_mappings

    def add_mapping(self, input_dir: Path, output_dir: Path) -> None:
        """Add or update a directory mapping."""
        mappings_dict = self._load_mappings_dict()
        # Use string representation for keys/values in the dictionary
        input_str = str(input_dir)
        output_str = str(output_dir)
        mappings_dict[input_str] = output_str
        self._save_mappings_dict(mappings_dict)
        logger.info(f"Added/Updated mapping: {input_str} -> {output_str}")

    def remove_mapping(self, input_dir: Path) -> bool:
        """Remove a directory mapping. Returns True if removed, False otherwise."""
        mappings_dict = self._load_mappings_dict()
        input_str = str(input_dir)
        if input_str in mappings_dict:
            del mappings_dict[input_str]
            self._save_mappings_dict(mappings_dict)
            logger.info(f"Removed mapping for input directory: {input_str}")
            return True
        else:
            logger.warning(f"Attempted to remove non-existent mapping for: {input_str}")
            return False

    def get_pandoc_config(self) -> Tuple[Optional[str], Optional[str]]:
        """Get the configured pandoc path and arguments."""
        path = None
        args = None
        if self.config.has_section(PANDOC_SECTION):
            path = self.config.get(PANDOC_SECTION, PANDOC_PATH_KEY, fallback="pandoc")
            args = self.config.get(PANDOC_SECTION, PANDOC_ARGS_KEY, fallback="")
        logger.debug(f"Retrieved pandoc config: path='{path}', args='{args}'")
        return path, args

    def set_pandoc_config(self, path: Optional[Path] = None, args: Optional[str] = None) -> None:
        """Set the pandoc executable path and optional arguments."""
        if not self.config.has_section(PANDOC_SECTION):
            self.config.add_section(PANDOC_SECTION)

        if path is not None:
            path_str = str(path)
            self.config.set(PANDOC_SECTION, PANDOC_PATH_KEY, path_str)
            logger.info(f"Set pandoc path to: {path_str}")
        if args is not None:
            self.config.set(PANDOC_SECTION, PANDOC_ARGS_KEY, args)
            logger.info(f"Set pandoc args to: '{args}'")

        if path is not None or args is not None:
            self._save_config()

    def get_typst_config(self) -> Tuple[Optional[str], Optional[str]]:
        """Get the configured typst path and arguments."""
        path = None
        args = None
        if self.config.has_section(TYPST_SECTION):
            path = self.config.get(TYPST_SECTION, TYPST_PATH_KEY, fallback="typst")
            args = self.config.get(TYPST_SECTION, TYPST_ARGS_KEY, fallback="")
        else:
            # If section doesn't exist, ensure defaults are provided and section is created
            path = "typst"
            args = ""
            self.config.add_section(TYPST_SECTION)
            self.config.set(TYPST_SECTION, TYPST_PATH_KEY, path)
            self.config.set(TYPST_SECTION, TYPST_ARGS_KEY, args)
            self._save_config() # Save the newly added section
        logger.debug(f"Retrieved typst config: path='{path}', args='{args}'")
        return path, args

    def set_typst_config(self, path: Optional[Path] = None, args: Optional[str] = None) -> None:
        """Set the typst executable path and optional arguments."""
        if not self.config.has_section(TYPST_SECTION):
            self.config.add_section(TYPST_SECTION)

        if path is not None:
            path_str = str(path)
            self.config.set(TYPST_SECTION, TYPST_PATH_KEY, path_str)
            logger.info(f"Set typst path to: {path_str}")
        if args is not None:
            self.config.set(TYPST_SECTION, TYPST_ARGS_KEY, args)
            logger.info(f"Set typst args to: '{args}'")

        if path is not None or args is not None:
            self._save_config()
