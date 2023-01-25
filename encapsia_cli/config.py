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
    config = api.get_all_config()
    lib.pretty_print(config, "json")


@main.command()
@click.argument("output", type=click.File("w"))
@click.pass_obj
def save(obj, output):
    """Save entire configuration to given file."""
    api = lib.get_api(**obj)
    config = api.get_all_config()
    lib.pretty_print(config, "json", output=output)
    lib.log_output(f"Configuration saved to {output.name}")


@main.command()
@click.argument("input", type=click.File("r"))
@click.pass_obj
def load(obj, input):
    """Load (merge) configuration from given file."""
    api = lib.get_api(**obj)
    data = lib.parse(input.read(), "json")
    api.set_config_multi(data)
    lib.log_output(f"Configuration loaded from {input.name}")


@main.command()
@click.argument("key")
@click.pass_obj
def get(obj, key):
    """Retrieve value against given key."""
    api = lib.get_api(**obj)
    try:
        value = api.get_config(key)
    except KeyError as e:
        lib.log_error(
            f"error: could not get key {e}: No configuration with this key!", abort=True
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
    api.set_config(key, value)
    new_value = api.get_config(key)
    lib.log_output(f"Configuration entry {key} has been set to {new_value}")


@main.command()
@click.argument("key")
@click.pass_obj
def delete(obj, key):
    """Delete value against given key."""
    api = lib.get_api(**obj)
    api.delete_config(key)
    lib.log_output(f"Configuration entry {key} deleted")
