import click
import encapsia_api

import encapsia_cli
from encapsia_cli import lib


@click.command("version")
def main():
    """Print version information and exits."""
    lib.log(f"Encapsia CLI version: {encapsia_cli.__version__}")
    lib.log(f"Encapsia API version: {encapsia_api.__version__}")
