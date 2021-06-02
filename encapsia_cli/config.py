import click

from encapsia_cli import lib


@click.group("config")
def main():
    """Get/set server configuration."""


@main.command()
@click.pass_obj
def show(obj):
    """Show entire configuration."""
    api = lib.get_api(**obj)
    config = lib.resilient_call(
        api.get_all_config, description="api.get_all_config()", idempotent=True
    )
    lib.pretty_print(config, "json")


@main.command()
@click.argument("output", type=click.File("w"))
@click.pass_obj
def save(obj, output):
    """Save entire configuration to given file."""
    api = lib.get_api(**obj)
    config = lib.resilient_call(
        api.get_all_config, description="api.get_all_config()", idempotent=True
    )
    lib.pretty_print(config, "json", output=output)


@main.command()
@click.argument("input", type=click.File("r"))
@click.pass_obj
def load(obj, input):
    """Load (merge) configuration from given file."""
    api = lib.get_api(**obj)
    data = lib.parse(input.read(), "json")
    lib.resilient_call(api.set_config_multi, data, description="api.set_config_multi()")


@main.command()
@click.argument("key")
@click.pass_obj
def get(obj, key):
    """Retrieve value against given key."""
    api = lib.get_api(**obj)
    value = lib.resilient_call(
        api.get_config, key, description=f"api.get_config({key})", idempotent=True
    )
    lib.pretty_print(value, "json")


@main.command()
@click.argument("key")
@click.argument("value")
@click.pass_obj
def set(obj, key, value):
    """Store value against given key."""
    api = lib.get_api(**obj)
    value = lib.parse(value, "json")
    lib.resilient_call(
        api.set_config, key, value, description=f"api.set_config({key}, <value>)"
    )


@main.command()
@click.argument("key")
@click.pass_obj
def delete(obj, key):
    """Delete value against given key."""
    api = lib.get_api(**obj)
    lib.resilient_call(api.delete_config, key, description=f"api.delete_config({key})")
