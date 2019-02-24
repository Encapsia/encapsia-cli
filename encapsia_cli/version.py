import click

import encapsia_cli
import encapsia_api


@click.command("version")
def main():
    """Print version information about the CLI."""
    click.echo(f"Encapsia CLI version: {encapsia_cli.__version__}")
    click.echo(f"Encapsia API version: {encapsia_api.__version__}")
