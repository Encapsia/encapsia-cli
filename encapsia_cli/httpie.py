"""Helper to launch the httpie shell with the URL and credentials passed in."""
import click

from encapsia_cli import lib


main = lib.make_main(__doc__)


@main.command("shell")
@click.pass_obj
def shell(obj):
    """Print the command to launch an httpie session with passed-in credentials."""
    hostname, token = lib.discover_credentials(host=obj["host"], hostname_env_var=obj["hostname_env_var"], token_env_var=obj["token_env_var"])
    argv = ["http", f"https://{hostname}", f"'Authorization: Bearer {token}'", "'Accept: application/json'"]
    click.echo(" ".join(argv))