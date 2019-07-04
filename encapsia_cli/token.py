"""Do things with an encapsia token."""
import click
from encapsia_api import CredentialsStore, EncapsiaApiError

from encapsia_cli import lib

main = lib.make_main(__doc__)


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
    if obj["host"]:
        CredentialsStore().remove(obj["host"])
        lib.log("Removed entry from encapsia credentials file.")


@main.command()
@click.pass_obj
def whoami(obj):
    """Print information about current owner of token."""
    api = lib.get_api(**obj)
    lib.pretty_print(api.whoami(), "toml")
