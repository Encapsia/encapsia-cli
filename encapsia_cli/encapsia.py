"""CLI to talk to an encapsia host."""
import click
import click_completion

import encapsia_cli
import encapsia_cli.config
import encapsia_cli.database
import encapsia_cli.fixtures
import encapsia_cli.help
import encapsia_cli.httpie
import encapsia_cli.run
import encapsia_cli.schedule
import encapsia_cli.shell
import encapsia_cli.token
import encapsia_cli.users
import encapsia_cli.version


#: Initialise click completion.
click_completion.init()


COMMANDS = {
    "config": encapsia_cli.config.main,
    "database": encapsia_cli.database.main,
    "fixtures": encapsia_cli.fixtures.main,
    "help": encapsia_cli.help.main,
    "httpie": encapsia_cli.httpie.main,
    "run": encapsia_cli.run.main,
    "schedule": encapsia_cli.schedule.main,
    "shell": encapsia_cli.shell.main,
    "token": encapsia_cli.token.main,
    "users": encapsia_cli.users.main,
    "version": encapsia_cli.version.main,
}


class EncapsiaCli(click.MultiCommand):

    def list_commands(self, ctx):
        return sorted(COMMANDS.keys())

    def get_command(self, ctx, name):
        try:
            return COMMANDS[name]
        except KeyError:
            click.echo(ctx.get_help(), err=True)
            click.echo(err=True)
            raise click.UsageError(f"Unknown command {name}")


main = EncapsiaCli(help=__doc__)