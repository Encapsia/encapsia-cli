"""Manage system users (create, list, delete etc)."""
import click
from encapsia_api import EncapsiaApi

from encapsia_cli import lib


@click.group()
@click.option("--host", help="Name to use to lookup credentials in .encapsia/credentials.toml")
@click.option("--host-env-var", default="ENCAPSIA_HOST", help="Environment variable containing DNS hostname (default ENCAPSIA_HOST)")
@click.option(
    "--token-env-var",
    default="ENCAPSIA_TOKEN",
    help="Environment variable containing server token (default ENCAPSIA_TOKEN)",
)
@click.pass_context
def main(ctx, host, host_env_var, token_env_var):
    """Manage system users."""
    ctx.obj = dict(api=lib.get_api(host, host_env_var, token_env_var))


@main.command()
@click.argument("description")
@click.argument("capabilities")
@click.pass_context
def add(ctx, description, capabilities):
    """Create system user with suitable user and role details.

    Use quoting in the shell appropriately. For example:

    encapsia-system-user add "This is a description" "capability1, capability2"

    """
    api = ctx.obj["api"]
    api.add_system_user(description, [x.strip() for x in capabilities.split(",")])


@main.command()
@click.pass_context
def show(ctx):
    """Print system users."""
    api = ctx.obj["api"]
    for su in api.get_system_users():
        print(su)
