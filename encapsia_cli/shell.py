import click
import click_shell


@click.command("shell")
@click.pass_context
def main(ctx):
    """Start an interactive shell."""
    shell = click_shell.make_click_shell(
        ctx.parent,
        prompt="encapsia > ",
        intro="Starting interactive shell...\nType help for help!",
    )
    shell.cmdloop()
