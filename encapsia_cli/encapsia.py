"""CLI to talk to an encapsia host.

The following steps are used to determine the server URL and token:

\b
  If provided, use the --host option to reference an entry in ~/.encapsia/credentials.toml
  Else if set, use ENCAPSIA_HOST to reference an entry in ~/.encapsia/credentials.toml
  Else if set, use ENCAPSIA_URL and ENCAPSIA_TOKEN directly.
  Else abort.

The tool will also abort if instructed to lookup in ~/.encapsia/credentials.toml
but cannot find a correct entry.

"""
import click
import click_completion

import encapsia_cli.config
import encapsia_cli.database
import encapsia_cli.fixtures
import encapsia_cli.help
import encapsia_cli.httpie
import encapsia_cli.plugins
import encapsia_cli.run
import encapsia_cli.schedule
import encapsia_cli.shell
import encapsia_cli.token
import encapsia_cli.users
import encapsia_cli.version
from encapsia_cli import lib

#: Initialise click completion.
click_completion.init()


COMMANDS = {
    "config": encapsia_cli.config.main,
    "database": encapsia_cli.database.main,
    "fixtures": encapsia_cli.fixtures.main,
    "help": encapsia_cli.help.main,
    "httpie": encapsia_cli.httpie.main,
    "plugins": encapsia_cli.plugins.main,
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
            lib.log_error(ctx.get_help())
            lib.log_error()
            raise click.UsageError(f"Unknown command {name}")


main = EncapsiaCli(help=__doc__)
