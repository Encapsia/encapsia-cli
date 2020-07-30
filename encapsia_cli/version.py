import click
import encapsia_api

import encapsia_cli
from encapsia_cli import lib


@click.command("version")
@click.pass_context
@lib.colour_option
def main(ctx, colour):
    """Print version information about the CLI."""
    ctx.color = {"always": True, "never": False, "auto": None}[colour]
    lib.log(f"Encapsia CLI version: {encapsia_cli.__version__}")
    lib.log(f"Encapsia API version: {encapsia_api.__version__}")
