"""Helper to use httpie with the URL and credentials passed in."""
import subprocess

import click

from encapsia_cli import lib

main = lib.make_main(__doc__)


@main.command("shell")
@click.pass_obj
def shell(obj):
    """Launch an httpie interactive shell with passed-in credentials."""
    api = lib.get_api(**obj)
    argv = [
        "http-prompt",
        api.url,
        f"Authorization: Bearer {api.token}",
        "Accept: application/json",
    ]
    subprocess.run(argv)
