"""Helper to use httpie with the URL and credentials passed in."""
import importlib
import subprocess

import click

from encapsia_cli import lib

main = lib.make_main(__doc__)


@main.command("shell")
@click.pass_obj
def shell(obj):
    """Launch an httpie interactive shell with passed-in credentials."""
    try:
        importlib.import_module("http_prompt")
    except ModuleNotFoundError:
        lib.log_error("Please install http-prompt first.", abort=True)
    api = lib.get_api(**obj)
    argv = [
        "http-prompt",
        api.url,
        f"Authorization: Bearer {api.token}",
        "Accept: application/json",
    ]
    subprocess.run(argv)
