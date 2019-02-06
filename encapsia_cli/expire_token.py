"""Expire Encapsia token from a server."""
import click
from encapsia_api import EncapsiaApiError, CredentialsStore

from encapsia_cli import lib


@click.command()
@click.option(
    "--host", help="Name to use to lookup credentials in .encapsia/credentials.toml"
)
@click.option(
    "--host-env-var",
    default="ENCAPSIA_HOST",
    help="Environment variable containing DNS hostname (default ENCAPSIA_HOST)",
)
@click.option(
    "--token-env-var",
    default="ENCAPSIA_TOKEN",
    help="Environment variable containing server token (default ENCAPSIA_TOKEN)",
)
def main(host, host_env_var, token_env_var):
    """Expire token from server, and update encapsia credentials if used."""
    api = lib.get_api(host, host_env_var, token_env_var)
    try:
        api.delete("logout")
        lib.log("Expired token on server.")
    except EncapsiaApiError as e:
        lib.error("Failed to expire given token!")
        lib.error(str(e))
        raise click.Abort()
    if host:
        CredentialsStore().remove(host)
        lib.log("Removed entry from encapsia credentials file.")
