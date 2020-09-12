import os

import click
import click_shell


@click.command("shell")
@click.pass_context
def main(ctx):
    """Start an interactive shell for running the encapsia commands."""
    host = ctx.obj.get("host")
    if host:
        os.environ["ENCAPSIA_HOST"] = host
        prompt = f"encapsia {host}> "
    else:
        prompt = "encapsia> "
    shell = click_shell.make_click_shell(
        ctx.parent,
        prompt=prompt,
        intro="Starting interactive shell...\nType help for help!",
    )
    shell.cmdloop()
