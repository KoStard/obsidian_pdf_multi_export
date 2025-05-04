import logging
import os
import shlex
import shutil
import subprocess
from pathlib import Path
from typing import Dict, Tuple, Optional, Set

from typing import Literal

import click

from . import Synchronizer, ConverterChoice, ConverterConfig

logger = logging.getLogger(__name__)


class DirectorySynchronizer(Synchronizer):
    """Handles the synchronization logic between input and output directories."""

    def run_sync(
        self,
        mappings: Dict[Path, Path],
        converter: ConverterChoice,
        converter_config: ConverterConfig,
    ) -> None:
        """Runs the synchronization process for all configured mappings using the specified converter."""
        if not mappings:
            click.echo("⚠️ No directory mappings configured. Use 'config add' first.")
            logger.warning("Sync process skipped: No mappings found.")
            return

        converter_path_str, converter_args_str = converter_config
        converter_path = converter_path_str or converter # Default to 'pandoc' or 'typst' if path not set
        converter_args = shlex.split(converter_args_str or "")
        logger.info(f"Selected converter: {converter}")
        logger.debug(f"Using {converter} path: {converter_path}")
        logger.debug(f"Using {converter} args: {converter_args}")

        # Check if the selected converter exists
        if not shutil.which(converter_path):
            click.echo(f"❌ Error: {converter.capitalize()} executable not found at '{converter_path}'.", err=True)
            click.echo(
                f"Please install {converter.capitalize()} or configure the correct path using 'config set-{converter} --path /path/to/{converter}'."
            )
            logger.error(f"{converter.capitalize()} executable not found at '{converter_path}'. Sync aborted.")
            return

        total_mappings = len(mappings)
        for i, (input_dir, output_dir) in enumerate(mappings.items(), 1):
            click.echo(f"\n🔄 Processing mapping {i}/{total_mappings}: {input_dir} -> {output_dir}")
            if not input_dir.is_dir():
                click.echo(f"⚠️ Skipping: Input directory '{input_dir}' not found or is not a directory.", err=True)
                logger.warning(f"Skipping mapping: Input directory not found: {input_dir}")
                continue

            try:
                # Ensure output directory exists
                output_dir.mkdir(parents=True, exist_ok=True)
                logger.debug(f"Ensured output directory exists: {output_dir}")

                # 1. Clean output directory (prompt for stale files)
                self._clean_output_directory(input_dir, output_dir)

                # 2. Process files: Copy non-markdown, convert markdown using selected converter
                self._process_directory(input_dir, output_dir, converter, converter_path, converter_args)

            except Exception as e:
                click.echo(f"❌ Error processing mapping {input_dir} -> {output_dir}: {e}", err=True)
                logger.exception(f"Unhandled exception during sync for mapping {input_dir} -> {output_dir}:")

        click.echo("\n✅ Synchronization complete.")

    def _get_expected_output_path(self, input_file: Path, input_base: Path, output_base: Path) -> Path:
        """Calculates the expected path in the output directory for a given input file."""
        relative_path = input_file.relative_to(input_base)
        output_path = output_base / relative_path
        if input_file.suffix.lower() == ".md":
            output_path = output_path.with_suffix(".pdf")
        return output_path

    def _clean_output_directory(self, input_dir: Path, output_dir: Path):
        """Identifies and prompts for deletion of stale files/directories in the output directory."""
        logger.info(f"Starting cleanup phase for output directory: {output_dir}")
        expected_output_items: Set[Path] = set()

        # Build set of expected output paths based on input directory contents
        for root, _, files in os.walk(input_dir):
            current_input_dir = Path(root)
            relative_dir_path = current_input_dir.relative_to(input_dir)
            current_output_dir = output_dir / relative_dir_path

            # Add expected directory path itself (relative to output_dir)
            if relative_dir_path != Path("."):  # Don't add the root output dir itself
                expected_output_items.add(current_output_dir)

            for file in files:
                input_file_path = current_input_dir / file
                expected_path = self._get_expected_output_path(input_file_path, input_dir, output_dir)
                expected_output_items.add(expected_path)

        logger.debug(f"Expected output items ({len(expected_output_items)}): {expected_output_items}")

        actual_output_items: Set[Path] = set()
        if output_dir.exists():
            for root, dirs, files in os.walk(output_dir):
                current_output_root = Path(root)
                for d in dirs:
                    actual_output_items.add(current_output_root / d)
                for f in files:
                    actual_output_items.add(current_output_root / f)

        logger.debug(f"Actual output items ({len(actual_output_items)}): {actual_output_items}")

        stale_items = actual_output_items - expected_output_items
        logger.debug(f"Stale items found ({len(stale_items)}): {stale_items}")

        if not stale_items:
            logger.info("No stale items found in output directory.")
            return

        click.echo(f"🧹 Found {len(stale_items)} item(s) in '{output_dir}' that are not in the source '{input_dir}'.")

        delete_all = False
        skip_all = False
        deleted_count = 0
        skipped_count = 0

        # Sort for consistent prompting order
        sorted_stale_items = sorted(list(stale_items), key=lambda p: (p.is_dir(), str(p)))

        for item in sorted_stale_items:
            if skip_all:
                skipped_count += 1
                logger.debug(f"Skipping stale item (Skip All): {item}")
                continue

            relative_item_path = item.relative_to(output_dir)
            item_type = "directory" if item.is_dir() else "file"

            if delete_all:
                try:
                    if item.is_dir():
                        shutil.rmtree(item)
                        click.echo(f"  🗑️ Deleted directory (All): {relative_item_path}")
                        logger.info(f"Deleted stale directory (All): {item}")
                    else:
                        item.unlink()
                        click.echo(f"  🗑️ Deleted file (All): {relative_item_path}")
                        logger.info(f"Deleted stale file (All): {item}")
                    deleted_count += 1
                except OSError as e:
                    click.echo(f"  ❌ Error deleting {item_type} {relative_item_path}: {e}", err=True)
                    logger.error(f"Error deleting stale {item_type} {item}: {e}")
                continue

            # Prompt user
            prompt_text = f"  ❓ Delete stale {item_type} '{relative_item_path}'? [y/N/a(ll)/s(kip all)]"
            choice = click.prompt(
                prompt_text,
                default="n",
                type=click.Choice(["y", "n", "a", "s"], case_sensitive=False),
                show_choices=False,
            )

            if choice == "y":
                try:
                    if item.is_dir():
                        shutil.rmtree(item)
                        click.echo(f"    🗑️ Deleted directory: {relative_item_path}")
                        logger.info(f"Deleted stale directory (User choice 'y'): {item}")
                    else:
                        item.unlink()
                        click.echo(f"    🗑️ Deleted file: {relative_item_path}")
                        logger.info(f"Deleted stale file (User choice 'y'): {item}")
                    deleted_count += 1
                except OSError as e:
                    click.echo(f"    ❌ Error deleting {item_type} {relative_item_path}: {e}", err=True)
                    logger.error(f"Error deleting stale {item_type} {item} (User choice 'y'): {e}")
            elif choice == "a":
                delete_all = True
                try:
                    if item.is_dir():
                        shutil.rmtree(item)
                        click.echo(f"  🗑️ Deleted directory (All): {relative_item_path}")
                        logger.info(f"Deleted stale directory (User choice 'a'): {item}")
                    else:
                        item.unlink()
                        click.echo(f"  🗑️ Deleted file (All): {relative_item_path}")
                        logger.info(f"Deleted stale file (User choice 'a'): {item}")
                    deleted_count += 1
                except OSError as e:
                    click.echo(f"  ❌ Error deleting {item_type} {relative_item_path}: {e}", err=True)
                    logger.error(f"Error deleting stale {item_type} {item} (User choice 'a'): {e}")
            elif choice == "s":
                skip_all = True
                skipped_count += 1
                logger.info(f"Skipping stale item and all subsequent items (User choice 's'): {item}")
            else:  # 'n' or default
                skipped_count += 1
                logger.info(f"Skipped stale item (User choice 'n'): {item}")

        click.echo(f"🧹 Cleanup finished for '{output_dir}'. Deleted: {deleted_count}, Skipped: {skipped_count}.")
        logger.info(f"Cleanup phase finished for {output_dir}. Deleted: {deleted_count}, Skipped: {skipped_count}.")

    def _process_directory(
        self,
        input_dir: Path,
        output_dir: Path,
        converter: ConverterChoice,
        converter_path: str,
        converter_args: list,
    ):
        """Recursively processes files in the input directory using the selected converter."""
        logger.info(f"Starting processing phase for: {input_dir} -> {output_dir} using {converter}")
        copied_count = 0
        converted_count = 0
        skipped_count = 0
        error_count = 0

        for root, dirs, files in os.walk(input_dir):
            current_input_dir = Path(root)
            relative_dir_path = current_input_dir.relative_to(input_dir)
            current_output_dir = output_dir / relative_dir_path

            # Ensure corresponding output subdirectory exists
            if not current_output_dir.exists():
                logger.debug(f"Creating output subdirectory: {current_output_dir}")
                current_output_dir.mkdir(parents=True, exist_ok=True)

            for file in files:
                input_file_path = current_input_dir / file
                output_file_path = self._get_expected_output_path(input_file_path, input_dir, output_dir)
                relative_file_path = input_file_path.relative_to(input_dir)  # For logging/echo

                try:
                    # Ensure parent directory of the output file exists (needed if _clean_output_directory removed it)
                    output_file_path.parent.mkdir(parents=True, exist_ok=True)

                    if input_file_path.suffix.lower() == ".md":
                        # Convert Markdown to PDF using the selected converter
                        logger.debug(f"Attempting conversion of '{input_file_path}' to '{output_file_path}' using {converter}")
                        click.echo(f"  📄 Converting ({converter}): {relative_file_path} -> {relative_file_path.with_suffix('.pdf')}")
                        if converter == "pandoc":
                            self._convert_markdown_pandoc(input_file_path, output_file_path, converter_path, converter_args)
                        elif converter == "typst":
                            self._convert_markdown_typst(input_file_path, output_file_path, converter_path, converter_args)
                        else:
                            # Should not happen due to CLI choices, but good practice
                            raise ValueError(f"Unsupported converter type: {converter}")
                        converted_count += 1
                    else:
                        # Copy other files
                        logger.debug(f"Copying '{input_file_path}' to '{output_file_path}'")
                        click.echo(f"  📎 Copying: {relative_file_path}")
                        shutil.copy2(input_file_path, output_file_path)  # copy2 preserves metadata
                        copied_count += 1
                except subprocess.CalledProcessError as e:
                    # Provide more context in the error message
                    stderr_output = e.stderr.strip() if e.stderr else str(e)
                    click.echo(f"  ❌ {converter.capitalize()} Error converting {relative_file_path}: {stderr_output}", err=True)
                    logger.error(f"{converter.capitalize()} error converting {input_file_path}: {stderr_output}")
                    error_count += 1
                except Exception as e:
                    click.echo(f"  ❌ Error processing file {relative_file_path} with {converter}: {e}", err=True)
                    logger.exception(f"Error processing file {input_file_path}:")
                    error_count += 1

        click.echo(
            f"✨ Processing finished for '{input_dir}'. Converted: {converted_count}, Copied: {copied_count}, Errors: {error_count}."
        )
        logger.info(
            f"Processing phase finished for {input_dir} using {converter}. Converted: {converted_count}, Copied: {copied_count}, Errors: {error_count}."
        )

    def _run_conversion_command(self, command: list, input_file: Path, converter_name: str):
        """Executes a conversion command and handles common errors."""
        logger.debug(f"Executing {converter_name} command: {' '.join(shlex.quote(str(c)) for c in command)}")
        try:
            # Using check=True raises CalledProcessError on non-zero exit code
            # Capture output, ensure UTF-8 decoding
            result = subprocess.run(
                command,
                check=True,
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace", # Handle potential decoding errors
            )
            # Log warnings even if successful
            if result.stderr:
                logger.warning(f"{converter_name} stderr for {input_file}:\n{result.stderr.strip()}")
            if result.stdout: # Also log stdout for potential info/warnings
                 logger.info(f"{converter_name} stdout for {input_file}:\n{result.stdout.strip()}")

        except FileNotFoundError as e:
            # This check should ideally be caught earlier in run_sync, but catch here as a fallback
            logger.error(f"{converter_name} executable not found at '{command[0]}' when trying to convert {input_file}")
            # Re-raise with a more specific message if possible
            raise FileNotFoundError(f"{converter_name} executable not found at '{command[0]}'. Please check installation and configuration.") from e
        except subprocess.CalledProcessError as e:
            # Log details before re-raising
            logger.error(f"{converter_name} failed for {input_file}. Return code: {e.returncode}")
            logger.error(f"{converter_name} stderr:\n{e.stderr.strip()}")
            logger.error(f"{converter_name} stdout:\n{e.stdout.strip()}")
            raise e # Re-raise the original exception to be handled by the caller (_process_directory)
        except Exception as e:
            logger.exception(f"Unexpected error during {converter_name} conversion for {input_file}:")
            raise # Re-raise unexpected errors

    def _convert_markdown_pandoc(self, input_file: Path, output_file: Path, pandoc_path: str, pandoc_args: list):
        """Converts a single markdown file to PDF using Pandoc."""
        command = [pandoc_path, *pandoc_args, "-i", str(input_file), "-o", str(output_file)]
        self._run_conversion_command(command, input_file, "Pandoc")

    def _convert_markdown_typst(self, input_file: Path, output_file: Path, typst_path: str, typst_args: list):
        """Converts a single markdown file to PDF using Typst."""
        # Typst command structure: typst compile [options] <input> [output]
        # We place args *before* the input/output files.
        command = [typst_path, "compile", *typst_args, str(input_file), str(output_file)]
        self._run_conversion_command(command, input_file, "Typst")
