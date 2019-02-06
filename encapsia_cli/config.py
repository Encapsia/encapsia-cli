"""Get/set server configuration."""
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
def app(ctx, host, host_env_var, token_env_var):
    """Get/set server configuration (not *trial* configuration)."""
    ctx.obj["api"] = lib.get_api(host, host_env_var, token_env_var)


@app.command()
@click.pass_context
def show(ctx):
    """Show entire configuration."""
    api = ctx.obj["api"]
    lib.pretty_print(api.get_all_config(), "json")


@app.command()
@click.argument("output", type=click.File("w"))
@click.pass_context
def save(ctx, output):
    """Save entire configuration to given file."""
    api = ctx.obj["api"]
    lib.pretty_print(api.get_all_config(), "json", output=output)


@app.command()
@click.argument("input", type=click.File("r"))
@click.pass_context
def load(ctx, input):
    """Load (merge) configuration from given file."""
    api = ctx.obj["api"]
    data = lib.parse(input.read(), "json")
    api.set_config_multi(data)


@app.command()
@click.argument("key")
@click.pass_context
def get(ctx, key):
    """Retrieve value against given key."""
    api = ctx.obj["api"]
    lib.pretty_print(api.get_config(key), "json")


@app.command()
@click.argument("key")
@click.argument("value")
@click.pass_context
def set(ctx, key, value):
    """Store value against given key."""
    api = ctx.obj["api"]
    value = lib.parse(value, "json")
    api.set_config(key, value)


@app.command()
@click.argument("key")
@click.pass_context
def delete(ctx, key):
    """Delete value against given key."""
    api = ctx.obj["api"]
    api.delete_config(key)


def main():
    app(obj={})
