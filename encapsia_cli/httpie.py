"""Helper to use httpie with the URL and credentials passed in."""
import subprocess

import click

from encapsia_cli import lib

main = lib.make_main(__doc__)


@main.command("shell")
@click.pass_obj
def shell(obj):
    """Launch an httpie interactive shell with passed-in credentials."""
    url, token = lib.discover_credentials(
        host=obj["host"],
    )
    argv = [
        "http-prompt",
        url,
        f"Authorization: Bearer {token}",
        "Accept: application/json",
    ]
    subprocess.run(argv)
