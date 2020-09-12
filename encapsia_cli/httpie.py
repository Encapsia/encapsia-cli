import importlib
import subprocess

import click

from encapsia_cli import lib


@click.command("httpie")
@click.pass_obj
def main(obj):
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
