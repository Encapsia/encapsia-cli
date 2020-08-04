"""Manage database fixtures."""
import click

from encapsia_cli import lib

main = lib.make_main(__doc__)


@main.command("list")
@click.pass_obj
def list_fixtures(obj):
    """List available fixtures."""
    api = lib.get_api(**obj)
    lib.log_output(
        lib.dbctl_action(api, "list_fixtures", dict(), "Fetching list of fixtures")
    )


@main.command("create")
@click.argument("name")
@click.pass_obj
def create_fixture(obj, name):
    """Create new fixture with given name."""
    api = lib.get_api(**obj)
    lib.log_output(
        lib.dbctl_action(
            api, "create_fixture", dict(name=name), f"Creating fixture {name}"
        )
    )


@main.command("use")
@click.argument("name")
@click.option("--yes", is_flag=True, help="Don't prompt the user for confirmation.")
@click.pass_obj
def use_fixture(obj, name, yes):
    """Switch to fixture with given name."""
    if not yes:
        click.confirm(
            f'Are you sure you want to change the database to fixture "{name}"?',
            abort=True,
        )
    api = lib.get_api(**obj)
    poll, NoTaskResultYet = api.dbctl_action("use_fixture", dict(name=name))
    lib.log(f"Requested change to fixture {name}.")
    lib.log("Please verify by other means (e.g. look at the logs).")


@main.command("delete")
@click.argument("name")
@click.option("--yes", is_flag=True, help="Don't prompt the user for confirmation.")
@click.pass_obj
def delete_fixture(obj, name, yes):
    """Delete fixture with given name."""
    if not yes:
        click.confirm(f'Are you sure you want to delete fixture "{name}"?', abort=True)
    api = lib.get_api(**obj)
    lib.log_output(
        lib.dbctl_action(
            api, "delete_fixture", dict(name=name), f"Deleting fixture {name}"
        )
    )
