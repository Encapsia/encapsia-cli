"""Print information about owner of token."""
import click
from encapsia_api import EncapsiaApi

from encapsia_cli import lib


@click.command()
@click.option("--host", envvar="ENCAPSIA_HOST", help="DNS name of Encapsia host (or ENCAPSIA_HOST).")
@click.option(
    "--token",
    default="ENCAPSIA_TOKEN",
    help="Environment variable containing server token (default ENCAPSIA_TOKEN)",
)
@click.option(
    "--format",
    type=click.Choice(["json", "toml"]),
    default="json",
    help="Format as JSON or TOML (default JSON)",
)
def main(host, token, format):
    """Print information about current owner of token.

    The token itself should be in an environment variable (default ENCAPSIA_TOKEN).

    """
    api = EncapsiaApi(host, lib.get_env_var(token))
    lib.pretty_print(api.whoami(), format)
