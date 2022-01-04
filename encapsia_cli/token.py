import click
from encapsia_api import CredentialsStore, EncapsiaApi, EncapsiaApiError

from encapsia_cli import lib


# By default, create tokens with one year lifespan when extending, transfering.
DEFAULT_LIFESPAN = 60 * 60 * 24 * 365


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
    default=DEFAULT_LIFESPAN,
    help="New lifespan of token. Default is 1 year.",
)
@click.option(
    "--capabilities",
    default=None,
    help="New capabilities of token. Default is to keep the same.",
)
@click.option(
    "--store/--no-store",
    default=True,
    is_flag=True,
    help="Replace new token in credentials file.",
)
@click.option(
    "--plain",
    "display",
    flag_value="plain",
    default=True,
)
@click.option(
    "--env",
    "display",
    flag_value="shell",
)
@click.option(
    "--shell",
    type=click.Choice(["auto", "bash", "fish", "zsh"], case_sensitive=False),
    default="auto",
    help="Target shell. Default is to autodetect.",
)
@click.pass_obj
def extend(obj, lifespan, capabilities, store, display, shell):
    """Extend the lifespan of token and update encapsia credentials (if used)."""
    api = lib.get_api(**obj)
    if capabilities is not None:
        capabilities = [c.strip() for c in capabilities.split(",")]
    new_token = api.login_again(lifespan=lifespan, capabilities=capabilities)
    host = obj.get("host")
    if host and store:
        store = CredentialsStore()
        url, _ = store.get(host)
        store.set(host, url, new_token)
        lib.log("Encapsia credentials file updated.")
    else:
        lib.print_token(new_token, display, url=api.url, shell=shell)


@main.command()
@click.option(
    "--lifespan",
    default=DEFAULT_LIFESPAN,
    help="New lifespan of token. Default is 1 year.",
)
@click.option(
    "--plain",
    "display",
    flag_value="plain",
    default=True,
)
@click.option(
    "--env",
    "display",
    flag_value="shell",
)
@click.option(
    "--shell",
    type=click.Choice(["auto", "bash", "fish", "zsh"], case_sensitive=False),
    default="auto",
    help="Target shell. Default is to autodetect.",
)
@click.argument(
    "user",
)
@click.pass_obj
def transfer(obj, lifespan, display, shell, user):
    """Get a token for `user` (subject to proper capabilities)"""
    api = lib.get_api(**obj)
    user_token = api.login_transfer(user, lifespan=lifespan)
    # login_transfer does not use the lifespan argument;
    # see https://github.com/tcorbettclark/encapsia-api/issues/32
    user_api = EncapsiaApi(api.url, user_token)
    extended_user_token = user_api.login_again(lifespan=lifespan)
    lib.print_token(extended_user_token, display, url=api.url, shell=shell)


@main.command()
@click.option(
    "--shell",
    type=click.Choice(["auto", "bash", "fish", "zsh"], case_sensitive=False),
    default="auto",
    help="Target shell. Default is to autodetect.",
)
@click.pass_obj
def env(obj, shell):
    """Generate shell commands to populate encapsia host environment variables."""
    host = obj.get("host")
    url, token = CredentialsStore().get(host)
    lib.print_token(token, "shell", url, shell)
