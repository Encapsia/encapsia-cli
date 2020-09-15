import click
from encapsia_api import CredentialsStore, EncapsiaApiError

from encapsia_cli import lib


@click.group("token")
def main():
    """Do things with an encapsia token."""


@main.command()
@click.pass_obj
def expire(obj):
    """Expire token from server, and update encapsia credentials if used."""
    api = lib.get_api(**obj)
    try:
        api.delete("logout")
        lib.log("Expired token on server.")
    except EncapsiaApiError as e:
        lib.log_error("Failed to expire given token!")
        lib.log_error(str(e), abort=True)
    host = obj.get("host")
    if host:
        CredentialsStore().remove(host)
        lib.log("Removed entry from encapsia credentials file.")


@main.command()
@click.pass_obj
def whoami(obj):
    """Print information about current owner of token."""
    api = lib.get_api(**obj)
    lib.pretty_print(api.whoami(), "toml")


@main.command()
@click.option(
    "--lifespan",
    default=60 * 60 * 24 * 365,
    help="New lifespan of token. Default is 1 year.",
)
@click.pass_obj
def extend(obj, lifespan):
    """Extend the lifespan of token and update encapsia credentials (if used)."""
    api = lib.get_api(**obj)
    new_token = api.login_again(lifespan=lifespan)
    host = obj.get("host")
    if host:
        store = CredentialsStore()
        url, old_token = store.get(host)
        store.set(host, url, new_token)
        lib.log("Encapsia credentials file updated.")
    else:
        lib.log(new_token)
