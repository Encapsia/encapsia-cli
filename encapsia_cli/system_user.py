"""Manage system users (create, list, delete etc)."""
import click
from encapsia_api import EncapsiaApi

from encapsia_cli import lib


@click.group()
def main():
    """Manage system users."""


@main.command()
@click.argument("description")
@click.argument("capabilities")
@click.option("--host", envvar="ENCAPSIA_HOST", help="DNS name of Encapsia host (or ENCAPSIA_HOST).")
@click.option(
    "--token",
    default="ENCAPSIA_TOKEN",
    help="Environment variable containing server token (default ENCAPSIA_TOKEN)",
)
def add(description, capabilities, host, token):
    """Create system user with suitable user and role details.

    Use quoting in the shell appropriately. For example:

    encapsia-system-user add "This is a description" "capability1, capability2"

    """
    api = EncapsiaApi(host, lib.get_env_var(token))
    api.add_system_user(description, [x.strip() for x in capabilities.split(",")])


@main.command()
@click.option("--host", envvar="ENCAPSIA_HOST", help="DNS name of Encapsia host (or ENCAPSIA_HOST).")
@click.option(
    "--token",
    default="ENCAPSIA_TOKEN",
    help="Environment variable containing server token (default ENCAPSIA_TOKEN)",
)
def show(host, token):
    """Print system users."""
    api = EncapsiaApi(host, lib.get_env_var(token))
    for su in api.get_system_users():
        print(su)
