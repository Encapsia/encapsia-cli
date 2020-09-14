import pathlib

import click

from encapsia_cli import lib


@click.group("database")
def main():
    """Backups and Restore encapsia databases."""


@main.command()
@click.argument(
    "filename", type=click.Path(writable=True, readable=False), required=False
)
@click.pass_obj
def backup(obj, filename):
    """Backup database to given filename. (or create a temp one if not given)."""
    if filename:
        filename = pathlib.Path(filename)
    api = lib.get_api(**obj)
    handle = lib.dbctl_action(api, "backup_database", dict(), "Backing up database")
    filename = api.dbctl_download_data(handle, filename)
    lib.log(f"Downloaded {filename.stat().st_size} bytes to {filename}")


@main.command()
@click.argument("filename", type=click.Path(exists=True))
@click.option("--force", is_flag=True, help="Don't prompt the user for confirmation.")
@click.pass_obj
def restore(obj, filename, force):
    """Restore database from given backup file."""
    filename = pathlib.Path(filename)
    if not force:
        click.confirm(
            f'Are you sure you want to restore the database from "{filename}"?',
            abort=True,
        )
    api = lib.get_api(**obj)
    handle = api.dbctl_upload_data(filename)
    # On a restore, the server is temporarily stopped.
    # This means that attempts to use it will generate a 500 error when
    # Nginx tries to check the permission.
    # Further, the current token may no longer work.
    poll, NoResultYet = api.dbctl_action("restore_database", dict(data_handle=handle))
    lib.log("Database restore requested.")
    lib.log("Please verify by other means (e.g. look at the logs).")
