"""Expire Encapsia token from a server."""
import click
from encapsia_api import EncapsiaApi

from encapsia_cli import lib


def expire_token(host, token):
    api = EncapsiaApi("https://{}".format(host), token)
    try:
        api.delete("logout")
    except IceApiError as e:
        lib.error("Failed to expire given token!")
        lib.error(str(e))
        raise click.Abort()


@click.command()
@click.option("--host", envvar="ENCAPSIA_HOST", help="DNS name of Encapsia host (or ENCAPSIA_HOST).")
@click.option(
    "--token",
    default="ENCAPSIA_TOKEN",
    help="Environment variable containing server token (default ENCAPSIA_TOKEN)",
)
def main(host, token):
    """Expire token from server given by ENCAPSIA_HOST.

    The token itself should be in an environment variable (default ENCAPSIA_TOKEN).

    """
    if "." not in host:
        host += ".encapsia.com"
    expire_token(host, lib.get_env_var(token))
