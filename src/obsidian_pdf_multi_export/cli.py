import click
import logging
from pathlib import Path

from pathlib import Path

# Import implementations directly here for dependency injection
from .config.ini_config_manager import IniConfigManager, DEFAULT_CONFIG_FILE
from .sync.synchronizer import DirectorySynchronizer

logger = logging.getLogger(__name__)

# Instantiate components (Dependency Injection)
# In a larger app, this might be handled by a framework or a dedicated container
config_manager = IniConfigManager(config_path=DEFAULT_CONFIG_FILE)
synchronizer = DirectorySynchronizer()


@click.group()
@click.option("--debug", is_flag=True, help="Enable debug logging.")
@click.version_option()  # Reads version from pyproject.toml
def cli(debug):
    """🔄 Obsidian PDF Multi Export Tool

    Synchronizes directories, converting Markdown files to PDF using Pandoc.
    Configuration is stored in ~/.config/obsidian_pdf_multi_export/config.ini
    """
    log_level = logging.DEBUG if debug else logging.INFO
    logging.basicConfig(level=log_level, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
    logger.debug("CLI started")
    # Ensure config exists on first run or if deleted
    config_manager._ensure_config_exists()


@cli.command()
def sync():
    """🔄 Synchronize configured directories."""
    click.echo("⏳ Starting synchronization process...")
    logger.info("Sync command initiated.")
    try:
        mappings = config_manager.get_mappings()
        pandoc_config = config_manager.get_pandoc_config()
        synchronizer.run_sync(mappings, pandoc_config)
        # Success message is now printed within run_sync
        logger.info("Sync command completed successfully.")
    except Exception as e:
        # Catch any unexpected errors during the sync process setup or execution
        click.echo(f"❌ An unexpected error occurred during synchronization: {e}", err=True)
        logger.exception("Unexpected error during sync command execution:")


@cli.group()
def config():
    """⚙️ Manage configuration."""
    logger.debug("Config command group invoked")


@config.command(name="add")
@click.argument("input_dir", type=click.Path(exists=True, file_okay=False, resolve_path=True))
@click.argument("output_dir", type=click.Path(file_okay=False, resolve_path=True))
def add_mapping(input_dir, output_dir):
    """➕ Add a new input/output directory mapping."""
    input_path = Path(input_dir)
    output_path = Path(output_dir)
    try:
        config_manager.add_mapping(input_path, output_path)
        click.echo(f"✅ Successfully added mapping: {input_path} -> {output_path}")
        logger.info(f"Config add command executed for {input_path} -> {output_path}")
    except Exception as e:
        click.echo(f"❌ Error adding mapping: {e}", err=True)
        logger.error(f"Error during config add for {input_path} -> {output_path}: {e}")


@config.command(name="remove")
@click.argument("input_dir", type=click.Path(exists=True, file_okay=False, resolve_path=True))
def remove_mapping(input_dir):
    """➖ Remove an existing input directory mapping."""
    input_path = Path(input_dir)
    try:
        if config_manager.remove_mapping(input_path):
            click.echo(f"✅ Successfully removed mapping for: {input_path}")
            logger.info(f"Config remove command executed for {input_path}")
        else:
            click.echo(f"⚠️ Mapping not found for: {input_path}")
            logger.warning(f"Config remove command: mapping not found for {input_path}")
    except Exception as e:
        click.echo(f"❌ Error removing mapping: {e}", err=True)
        logger.error(f"Error during config remove for {input_path}: {e}")


@config.command(name="list")
def list_mappings():
    """📄 List configured input/output directory mappings."""
    click.echo("📂 Configured Mappings:")
    try:
        mappings = config_manager.get_mappings()
        if not mappings:
            click.echo("  No mappings configured.")
        else:
            for input_p, output_p in mappings.items():
                click.echo(f"  ➡️ {input_p} -> {output_p}")

        pandoc_path, pandoc_args = config_manager.get_pandoc_config()
        click.echo("\n🔧 Pandoc Configuration:")
        click.echo(f"  Path: {pandoc_path or 'Not set (using default "pandoc")'}")
        click.echo(f"  Args: {pandoc_args or 'None'}")

        logger.info("Config list command executed")
    except Exception as e:
        click.echo(f"❌ Error listing configuration: {e}", err=True)
        logger.error(f"Error during config list: {e}")


@config.command(name="set-pandoc")
@click.option(
    "--path",
    "pandoc_path_str",
    type=click.Path(exists=True, dir_okay=False, resolve_path=True),
    help="Path to the pandoc executable.",
)
@click.option(
    "--args",
    "pandoc_args",
    default=None,
    help="Additional arguments for pandoc command (e.g., '--pdf-engine=xelatex'). Provide as a single string.",
)
def set_pandoc(pandoc_path_str, pandoc_args):
    """🔧 Set the pandoc executable path and/or optional arguments."""
    if pandoc_path_str is None and pandoc_args is None:
        click.echo("⚠️ Please provide either --path or --args.", err=True)
        return

    pandoc_path = Path(pandoc_path_str) if pandoc_path_str else None

    try:
        config_manager.set_pandoc_config(path=pandoc_path, args=pandoc_args)
        if pandoc_path:
            click.echo(f"✅ Set pandoc path to: {pandoc_path}")
        if pandoc_args is not None:  # Check for None explicitly to allow setting empty args
            click.echo(f"✅ Set pandoc arguments to: '{pandoc_args}'")
        logger.info(f"Config set-pandoc command executed for path={pandoc_path}, args='{pandoc_args}'")
    except Exception as e:
        click.echo(f"❌ Error setting pandoc config: {e}", err=True)
        logger.error(f"Error during config set-pandoc: {e}")


if __name__ == "__main__":
    cli()
