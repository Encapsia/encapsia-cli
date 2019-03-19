import click

from encapsia_cli import lib


@click.command("help")
@lib.colour_option
@click.argument("command", required=False)
@click.pass_context
def main(ctx, colour, command):
    """Print longer help information about the CLI."""
    ctx.color = {"always": True, "never": False, "auto": None}[colour]
    root_command = ctx.parent.command
    if command:
        lib.log(root_command.get_command(ctx, command).get_help(ctx))
    else:
        lib.log(root_command.get_help(ctx))
        lib.log()
        lib.log("Subcommands:")
        long_list = []
        for name in root_command.list_commands(ctx):
            command = root_command.get_command(ctx, name)
            if isinstance(command, click.Group):
                for subname in command.list_commands(ctx):
                    subcommand = command.get_command(ctx, subname)
                    help_str = subcommand.get_short_help_str()
                    long_list.append((name, subname, help_str))
        width = max(len(name) + len(subname) for (name, subname, _) in long_list)
        for name, subname, help_str in long_list:
            left = f"{name} {subname}"
            left = left + " " * (width + 2 - len(left))
            lib.log(f"  {left} {help_str}")
