import pathlib

import click
import click_completion

import encapsia_cli.completion
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


DEFAULT_CONFIG_FILE = f"""
# Encapsia CLI config file
# Automatically created by encapsia-cli=={encapsia_cli.__version__}

# Unlikely to want to fix the host here, but you can.
# host = "localhost"

# Control colour output to console.
colour = "auto"

# Options for the plugins subcommand.
[plugins]

# Always fetch/build/etc again.
force = false

# Name of local directory used to store plugins.
local_dir = "~/.encapsia/plugins"

# List of AWS S3 buckets (with optional paths) in which to search for plugins.
# The ice-plugins bucket should be considered legacy, and will be removed.
s3_buckets = [
    "encapsia-plugins/cmedtech/pd/staging/apps",
    "encapsia-plugins/cmedtech/pd/staging/middleware",
    "encapsia-plugins/cmedtech/pd/staging/insights",
    "ice-plugins"
]
""".strip()


def create_default_config_file_if_needed(filename):
    filename.parent.mkdir(parents=True, exist_ok=True)
    if not filename.exists():
        with filename.open("w") as f:
            f.write(DEFAULT_CONFIG_FILE)
        lib.log(f"Created default user configuration file in: {str(filename)}")


def get_user_config():
    filename = pathlib.Path.home() / ".encapsia" / "config.toml"
    create_default_config_file_if_needed(filename)
    config = lib.read_toml(filename)

    # Make directories into Path directories which exist.
    for k, d in [("plugins", "local_dir")]:
        config[k][d] = pathlib.Path(config[k][d]).expanduser()
        config[k][d].mkdir(parents=True, exist_ok=True)

    return config


@click.group(context_settings=dict(default_map=get_user_config()))
@click.option(
    "--colour",
    type=click.Choice(["always", "never", "auto"]),
    default="auto",
    help="Control colour on stdout.",
)
@click.option(
    "--host",
    help="Name to use to lookup credentials in .encapsia/credentials.toml",
)
@click.pass_context
def main(ctx, colour, host):
    """CLI to talk to an encapsia host.

    Options can be provided in one of three ways, in this priority order:

    \b
    1. On the command line as an --option.
    2. In an environment variable as ENCAPSIA_<OPTION> or ENCAPSIA_<SUBCOMMAND>_<OPTION>.
    3. In your config file located at ~/.encapsia/config.toml

    If the config file does not exist then it will be created with documentation and defaults.

    Although not needed by all the sub-commands, the host is so frequently used that it
    is a top level option.

    When needed, the following steps are used to determine the server URL and token:

    \b
    If provided, use the --host option to reference an entry in ~/.encapsia/credentials.toml
    Else if set, use ENCAPSIA_HOST to reference an entry in ~/.encapsia/credentials.toml
    Else if set, take the top level `host` option from ~/.encapsia/config.toml
    Else if set, use ENCAPSIA_URL and ENCAPSIA_TOKEN directly.
    Else abort.

    The tool will also abort if instructed to lookup in ~/.encapsia/credentials.toml
    but cannot find a correct entry.

    """
    ctx.color = {"always": True, "never": False, "auto": None}[colour]
    ctx.obj = dict(host=host)


COMMANDS = [
    encapsia_cli.completion.main,
    encapsia_cli.config.main,
    encapsia_cli.database.main,
    encapsia_cli.fixtures.main,
    encapsia_cli.help.main,
    encapsia_cli.httpie.main,
    encapsia_cli.plugins.main,
    encapsia_cli.run.main,
    encapsia_cli.schedule.main,
    encapsia_cli.shell.main,
    encapsia_cli.token.main,
    encapsia_cli.users.main,
    encapsia_cli.version.main,
]

for command in COMMANDS:
    main.add_command(command)


def encapsia():
    main(auto_envvar_prefix="ENCAPSIA")
