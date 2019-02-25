import os

import click
import click_shell


@click.command("shell")
@click.option(
    "--host", help="Name to use to lookup credentials in .encapsia/credentials.toml"
)
@click.pass_context
def main(ctx, host):
    """Start an interactive shell for running the encapsia commands.

    The --host option internally sets the ENCAPSIA_HOST environment variable,
    which subsequent commands will pick up if a --host option is not set again.

    """
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
