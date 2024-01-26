import click
import encapsia_api

import encapsia_cli
from encapsia_cli import lib


@click.command("version")
@click.option(
    "--plain",
    is_flag=True,
    help="Print just the version. Otherwise be more verbose."
)
def main(plain):
    """Print version information and exit."""
    if plain:
        lib.log(f"{encapsia_cli.__version__}")
    else:
        lib.log(f"Encapsia CLI version: {encapsia_cli.__version__}")
        lib.log(f"Encapsia API version: {encapsia_api.__version__}")
