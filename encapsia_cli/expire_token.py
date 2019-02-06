"""Expire Encapsia token from a server."""
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
def main(host, host_env_var, token_env_var):
    """Expire token from server given by ENCAPSIA_HOST.

    The token itself should be in an environment variable (default ENCAPSIA_TOKEN).

    """
    api = lib.get_api(host, host_env_var, token_env_var)
    try:
        api.delete("logout")
    except EncapsiaApiError as e:
        lib.error("Failed to expire given token!")
        lib.error(str(e))
        raise click.Abort()
