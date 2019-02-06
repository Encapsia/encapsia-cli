"""Print information about owner of token."""
import click
from encapsia_api import EncapsiaApi

from encapsia_cli import lib


@click.command()
@click.option("--host", help="Name to use to lookup credentials in .encapsia/credentials.toml")
@click.option("--host-env-var", default="ENCAPSIA_HOST", help="Environment variable containing DNS hostname (default ENCAPSIA_HOST)")
@click.option(
    "--token-env-var",
    default="ENCAPSIA_TOKEN",
    help="Environment variable containing server token (default ENCAPSIA_TOKEN)",
)
@click.option(
    "--format",
    type=click.Choice(["json", "toml"]),
    default="json",
    help="Format as JSON or TOML (default JSON)",
)
def main(host, host_env_var, token_env_var, format):
    """Print information about current owner of token."""
    api = lib.get_api(host, host_env_var, token_env_var)
    lib.pretty_print(api.whoami(), format)