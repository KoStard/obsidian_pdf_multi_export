import logging
import os
import shlex
import shutil
import subprocess
from pathlib import Path
from typing import Dict, Tuple, Optional, Set

import click

from . import Synchronizer

logger = logging.getLogger(__name__)


class DirectorySynchronizer(Synchronizer):
    """Handles the synchronization logic between input and output directories."""

    def run_sync(self, mappings: Dict[Path, Path], pandoc_config: Tuple[Optional[str], Optional[str]]) -> None:
        """Runs the synchronization process for all configured mappings."""
        if not mappings:
            click.echo("⚠️ No directory mappings configured. Use 'config add' first.")
            logger.warning("Sync process skipped: No mappings found.")
            return

        pandoc_path, pandoc_args_str = pandoc_config
        pandoc_path = pandoc_path or "pandoc"  # Default to 'pandoc' if not set
        pandoc_args = shlex.split(pandoc_args_str or "")
        logger.debug(f"Using pandoc path: {pandoc_path}")
        logger.debug(f"Using pandoc args: {pandoc_args}")

        # Check if pandoc exists
        if not shutil.which(pandoc_path):
            click.echo(f"❌ Error: Pandoc executable not found at '{pandoc_path}'.", err=True)
            click.echo(
                "Please install Pandoc or configure the correct path using 'config set-pandoc --path /path/to/pandoc'."
            )
            logger.error(f"Pandoc executable not found at '{pandoc_path}'. Sync aborted.")
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

                # 2. Process files: Copy non-markdown, convert markdown
                self._process_directory(input_dir, output_dir, pandoc_path, pandoc_args)

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

    def _process_directory(self, input_dir: Path, output_dir: Path, pandoc_path: str, pandoc_args: list):
        """Recursively processes files in the input directory."""
        logger.info(f"Starting processing phase for: {input_dir} -> {output_dir}")
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
                        # Convert Markdown to PDF
                        logger.debug(f"Converting '{input_file_path}' to '{output_file_path}'")
                        click.echo(f"  📄 Converting: {relative_file_path} -> {relative_file_path.with_suffix('.pdf')}")
                        self._convert_markdown(input_file_path, output_file_path, pandoc_path, pandoc_args)
                        converted_count += 1
                    else:
                        # Copy other files
                        logger.debug(f"Copying '{input_file_path}' to '{output_file_path}'")
                        click.echo(f"  📎 Copying: {relative_file_path}")
                        shutil.copy2(input_file_path, output_file_path)  # copy2 preserves metadata
                        copied_count += 1
                except subprocess.CalledProcessError as e:
                    click.echo(f"  ❌ Pandoc Error converting {relative_file_path}: {e.stderr or e}", err=True)
                    logger.error(f"Pandoc error converting {input_file_path}: {e.stderr or e}")
                    error_count += 1
                except Exception as e:
                    click.echo(f"  ❌ Error processing file {relative_file_path}: {e}", err=True)
                    logger.exception(f"Error processing file {input_file_path}:")
                    error_count += 1

        click.echo(
            f"✨ Processing finished for '{input_dir}'. Converted: {converted_count}, Copied: {copied_count}, Errors: {error_count}."
        )
        logger.info(
            f"Processing phase finished for {input_dir}. Converted: {converted_count}, Copied: {copied_count}, Errors: {error_count}."
        )

    def _convert_markdown(self, input_file: Path, output_file: Path, pandoc_path: str, pandoc_args: list):
        """Converts a single markdown file to PDF using Pandoc."""
        command = [pandoc_path, *pandoc_args, "-i", str(input_file), "-o", str(output_file)]
        logger.debug(f"Executing Pandoc command: {' '.join(command)}")
        try:
            # Using check=True raises CalledProcessError on non-zero exit code
            # Capture stderr to show pandoc errors
            result = subprocess.run(command, check=True, capture_output=True, text=True, encoding="utf-8")
            if result.stderr:
                # Log Pandoc warnings even if successful
                logger.warning(f"Pandoc stderr for {input_file}:\n{result.stderr}")
        except FileNotFoundError:
            # This should ideally be caught earlier by the check in run_sync
            logger.error(f"Pandoc executable not found at '{pandoc_path}' when trying to convert {input_file}")
            raise  # Re-raise to be caught by the caller
        except subprocess.CalledProcessError as e:
            # Log the error and stderr, then re-raise to be handled in _process_directory
            logger.error(f"Pandoc failed for {input_file}. Return code: {e.returncode}")
            logger.error(f"Pandoc stderr:\n{e.stderr}")
            logger.error(f"Pandoc stdout:\n{e.stdout}")  # Sometimes useful info is here too
            raise e  # Re-raise the original exception
        except Exception as e:
            logger.exception(f"Unexpected error during Pandoc conversion for {input_file}:")
            raise  # Re-raise unexpected errors
