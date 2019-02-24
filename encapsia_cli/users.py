"""Manage users, including superuser and system users."""
import click
import tabulate

from encapsia_cli import lib


main = lib.make_main(__doc__)


@main.command()
@click.argument("description")
@click.argument("capabilities")
@click.pass_obj
def add_systemuser(obj, description, capabilities):
    """Create system user with suitable user and role."""
    api = lib.get_api(**obj)
    api.add_system_user(description, [x.strip() for x in capabilities.split(",")])


@main.command()
@click.argument("email", callback=lib.validate_email)
@click.argument("first_name")
@click.argument("last_name")
@click.pass_obj
def add_superuser(obj, email, first_name, last_name):
    """Create superuser with suitable user and role."""
    api = lib.get_api(**obj)
    api.add_super_user(email, first_name, last_name)


@main.command("list")
@click.option("--superusers/--no-superusers", default=False)
@click.option("--system-users/--no-system-users", default=False)
@click.option("--all-users/--no-all-users", default=True)
@click.pass_obj
def list_users(obj, superusers, systemusers, all_users):
    """List out information about users."""
    api = lib.get_api(**obj)
    if superusers:
        click.echo("[Superusers]")
        users = api.get_super_users()
        headers = ["email", "first_name", "last_name"]
        click.echo(tabulate.tabulate(
            [[getattr(row, header) for header in headers] for row in users],
            headers=headers
        ))
        click.echo()
    if system_users:
        click.echo("[System users]")
        users = api.get_system_users()
        headers = ["email", "description", "capabilities"]
        click.echo(tabulate.tabulate(
            [[getattr(row, header) for header in headers] for row in users],
            headers=headers
        ))
        click.echo()
    if all_users:
        click.echo("[All users]")
        users = api.get_all_users()
        headers = ["email", "first_name", "last_name", "role", "enabled", "is_site_user"]
        click.echo(tabulate.tabulate(
            [[row[header] for header in headers] for row in users],
            headers=headers
        ))
        click.echo()


@main.command("delete")
@click.argument("email", callback=lib.validate_email)
@click.pass_obj
def delete_user(obj, email):
    """Delete user (but *not* deleting any related role)."""
    api = lib.get_api(**obj)
    api.delete_user(email)
