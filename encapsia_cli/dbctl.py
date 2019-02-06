"""Encapsia Database control actions e.g. backups, restores, and fixtures."""
import os
import os.path
import sys
import time

import click
from encapsia_api import EncapsiaApi

from encapsia_cli import lib


def visual_poll(message, poll, NoTaskResultYet, wait=0.5):
    out = sys.stdout
    out.write(message)
    out.flush()
    result = poll()
    while result is NoTaskResultYet:
        time.sleep(wait)
        out.write(".")
        out.flush()
        result = poll()
    out.write("Done\n")
    out.flush()
    return result


def dbctl_action(host, token, name, params, message):
    api = EncapsiaApi(host, token)
    poll, NoTaskResultYet = api.dbctl_action(name, params)
    result = visual_poll(message, poll, NoTaskResultYet)
    if result["status"] != "ok":
        raise click.Abort()
    return result["result"]


@click.group()
@click.option("--host", help="Name to use to lookup credentials in .encapsia/credentials.toml")
@click.option("--host-env-var", default="ENCAPSIA_HOST", help="Environment variable containing DNS hostname (default ENCAPSIA_HOST)")
@click.option(
    "--token-env-var",
    default="ENCAPSIA_TOKEN",
    help="Environment variable containing server token (default ENCAPSIA_TOKEN)",
)
@click.pass_context
def main(ctx, host, host_env_var, token_env_var):
    """Low-level Encapsia Database control."""
    host, token = lib.discover_credentials(host, host_env_var, token_env_var)
    ctx.obj = dict(host=host, token=token)


@main.command()
@click.pass_context
def list_fixtures(ctx):
    """List available fixtures."""
    print(
        dbctl_action(
            ctx.obj["host"],
            ctx.obj["token"],
            "list_fixtures",
            dict(),
            "Fetching list of fixtures...",
        )
    )


@main.command()
@click.argument("name")
@click.pass_context
def create_fixture(ctx, name):
    """Create new fixture with given name."""
    print(
        dbctl_action(
            ctx.obj["host"],
            ctx.obj["token"],
            "create_fixture",
            dict(name=name),
            "Create fixture {}...".format(name),
        )
    )


@main.command()
@click.argument("name")
@click.pass_context
def use_fixture(ctx, name):
    """Switch to fixture with given name."""
    print(
        dbctl_action(
            ctx.obj["host"],
            ctx.obj["token"],
            "use_fixture",
            dict(name=name),
            "Switching to fixture {}...".format(name),
        )
    )


@main.command()
@click.argument("name")
@click.pass_context
def delete_fixture(ctx, name):
    """Delete fixture with given name."""
    print(
        dbctl_action(
            ctx.obj["host"],
            ctx.obj["token"],
            "delete_fixture",
            dict(name=name),
            "Deleting fixture {}...".format(name),
        )
    )


@main.command()
@click.argument("name")
@click.pass_context
def create_extension_schema(ctx, name):
    """Create extension schema."""
    print(
        dbctl_action(
            ctx.obj["host"],
            ctx.obj["token"],
            "create_extension_schema",
            dict(name=name),
            "Creating schema {}...".format(name),
        )
    )


@main.command()
@click.argument("name")
@click.pass_context
def delete_extension_schema(ctx, name):
    """Delete extension schema."""
    print(
        dbctl_action(
            ctx.obj["host"],
            ctx.obj["token"],
            "delete_extension_schema",
            dict(name=name),
            "Deleting schema {}...".format(name),
        )
    )


@main.command()
@click.argument("name")
@click.argument("filename")
@click.pass_context
def load_extension_sql(ctx, name, filename):
    """Load SQL from given file into extension schema."""
    api = EncapsiaApi(ctx.obj["host"], ctx.obj["token"])
    handle = api.dbctl_upload_data(filename)
    dbctl_action(
        ctx.obj["host"],
        ctx.obj["token"],
        "load_extension_sql",
        dict(name=name, data_handle=handle),
        "Loading SQL into schema {}...".format(name),
    )


@main.command()
@click.argument("handle")
@click.option(
    "--filename",
    default=None,
    help="Optional filename into which the data will be downloaded.",
)
@click.pass_context
def download_data(ctx, handle, filename):
    """Download data of given handle."""
    api = EncapsiaApi(ctx.obj["host"], ctx.obj["token"])
    temp_filename = api.dbctl_download_data(handle)
    if filename is None:
        filename = temp_filename
    else:
        os.rename(temp_filename, filename)
    size = os.path.getsize(filename)
    print("Downloaded {} bytes to {}".format(size, filename))


@main.command()
@click.argument("filename")
@click.pass_context
def upload_data(ctx, filename):
    """Upload data in given file, printing a handle for re-use."""
    api = EncapsiaApi(ctx.obj["host"], ctx.obj["token"])
    handle = api.dbctl_upload_data(filename)
    size = os.path.getsize(filename)
    print("Uploaded {} bytes from {}".format(size, filename))
    print("Handle: {}".format(handle))
    return handle


@main.command()
@click.option(
    "--filename",
    default=None,
    help="Optional filename into which the data will be downloaded.",
)
@click.pass_context
def backup(ctx, filename):
    """Backup database to given filename (or temp one if not given)."""
    handle = dbctl_action(
        ctx.obj["host"],
        ctx.obj["token"],
        "backup_database",
        dict(),
        "Backing up database...",
    )
    api = EncapsiaApi(ctx.obj["host"], ctx.obj["token"])
    temp_filename = api.dbctl_download_data(handle)
    if filename is None:
        filename = temp_filename
    else:
        os.rename(temp_filename, filename)
    size = os.path.getsize(filename)
    print("Downloaded {} bytes to {}".format(size, filename))


@main.command()
@click.argument("filename")
@click.pass_context
def restore(ctx, filename):
    """Restore database from given backup file."""
    api = EncapsiaApi(ctx.obj["host"], ctx.obj["token"])
    handle = api.dbctl_upload_data(filename)
    # On a restore, the server is temporarily stopped.
    # This means that attempts to use it will generate a 500 error when
    # Nginx tries to check the permission.
    # Further, the current token may no longer work.
    api = EncapsiaApi(ctx.obj["host"], ctx.obj["token"])
    poll, NoTaskResultYet = api.dbctl_action(
        "restore_database", dict(data_handle=handle)
    )
    print("Database restore requested.")
    print("Please verify by other means (e.g. look at the logs).")
