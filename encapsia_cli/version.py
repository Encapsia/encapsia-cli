import click
import encapsia_api

import encapsia_cli


@click.command("version")
def main():
    """Print version information about the CLI."""
    click.echo(f"Encapsia CLI version: {encapsia_cli.__version__}")
    click.echo(f"Encapsia API version: {encapsia_api.__version__}")
