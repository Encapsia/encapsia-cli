"""Get/set server configuration."""
import click
from encapsia_api import EncapsiaApi

from encapsia_cli import lib


@click.group()
@click.option("--host", envvar="ENCAPSIA_HOST", help="DNS name of Encapsia host (or ENCAPSIA_HOST).")
@click.option(
    "--token",
    default="ENCAPSIA_TOKEN",
    help="Environment variable containing server token (default ENCAPSIA_TOKEN)",
)
@click.option(
    "--format",
    type=click.Choice(["json", "toml"]),
    default="toml",
    help="Format as JSON or TOML (default TOML)",
)
@click.pass_context
def app(ctx, host, token, format):
    """Get/set server configuration (not *trial* configuration)."""
    if "." not in host:
        host = host + ".encapsia.com"
    token = lib.get_env_var(token)
    ctx.obj["host"] = host
    ctx.obj["token"] = token
    ctx.obj["format"] = format


@app.command()
@click.pass_context
def show(ctx):
    """Show entire configuration."""
    api = EncapsiaApi(ctx.obj["host"], ctx.obj["token"])
    lib.pretty_print(api.get_all_config(), ctx.obj["format"])


@app.command()
@click.argument("output", type=click.File("w"))
@click.pass_context
def save(ctx, output):
    """Save entire configuration to given file."""
    api = EncapsiaApi(ctx.obj["host"], ctx.obj["token"])
    lib.pretty_print(api.get_all_config(), ctx.obj["format"], output=output)


@app.command()
@click.argument("input", type=click.File("r"))
@click.pass_context
def load(ctx, input):
    """Load (merge) configuration from given file."""
    api = EncapsiaApi(ctx.obj["host"], ctx.obj["token"])
    data = lib.parse(input.read(), ctx.obj["format"])
    api.set_config_multi(data)


@app.command()
@click.argument("key")
@click.pass_context
def get(ctx, key):
    """Retrieve value against given key."""
    api = EncapsiaApi(ctx.obj["host"], ctx.obj["token"])
    lib.pretty_print(api.get_config(key), ctx.obj["format"])


@app.command()
@click.argument("key")
@click.argument("value")
@click.pass_context
def set(ctx, key, value):
    """Store value against given key."""
    api = EncapsiaApi(ctx.obj["host"], ctx.obj["token"])
    value = lib.parse(value, ctx.obj["format"])
    api.set_config(key, value)


@app.command()
@click.argument("key")
@click.pass_context
def delete(ctx, key):
    """Delete value against given key."""
    api = EncapsiaApi(ctx.obj["host"], ctx.obj["token"])
    api.delete_config(key)


def main():
    app(obj={})
