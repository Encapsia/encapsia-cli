"""Get/set server configuration."""
import click

from encapsia_cli import lib

main = lib.make_main(__doc__)


@main.command()
@click.pass_obj
def show(obj):
    """Show entire configuration."""
    api = lib.get_api(**obj)
    lib.pretty_print(api.get_all_config(), "json")


@main.command()
@click.argument("output", type=click.File("w"))
@click.pass_obj
def save(obj, output):
    """Save entire configuration to given file."""
    api = lib.get_api(**obj)
    lib.pretty_print(api.get_all_config(), "json", output=output)


@main.command()
@click.argument("input", type=click.File("r"))
@click.pass_obj
def load(obj, input):
    """Load (merge) configuration from given file."""
    api = lib.get_api(**obj)
    data = lib.parse(input.read(), "json")
    api.set_config_multi(data)


@main.command()
@click.argument("key")
@click.pass_obj
def get(obj, key):
    """Retrieve value against given key."""
    api = lib.get_api(**obj)
    lib.pretty_print(api.get_config(key), "json")


@main.command()
@click.argument("key")
@click.argument("value")
@click.pass_obj
def set(obj, key, value):
    """Store value against given key."""
    api = lib.get_api(**obj)
    value = lib.parse(value, "json")
    api.set_config(key, value)


@main.command()
@click.argument("key")
@click.pass_obj
def delete(obj, key):
    """Delete value against given key."""
    api = lib.get_api(**obj)
    api.delete_config(key)
