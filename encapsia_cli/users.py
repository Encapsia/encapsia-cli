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
@click.option("--super-users/--no-super-users", default=False)
@click.option("--system-users/--no-system-users", default=False)
@click.option("--all-users/--no-all-users", default=False)
@click.pass_obj
def list_users(obj, super_users, system_users, all_users):
    """List out information about users."""
    api = lib.get_api(**obj)
    if not (super_users or system_users or all_users):
        # If no specific type of user specified then assume all-users was intended.
        all_users = True
    if super_users:
        lib.log_output("[Super users]")
        users = api.get_super_users()
        headers = ["email", "first_name", "last_name"]
        lib.log_output(
            tabulate.tabulate(
                [[getattr(row, header) for header in headers] for row in users],
                headers=headers,
            )
        )
        lib.log_output()
    if system_users:
        lib.log_output("[System users]")
        users = api.get_system_users()
        headers = ["email", "description", "capabilities"]
        lib.log_output(
            tabulate.tabulate(
                [[getattr(row, header) for header in headers] for row in users],
                headers=headers,
            )
        )
        lib.log_output()
    if all_users:
        lib.log_output("[All users]")
        users = api.get_all_users()
        headers = [
            "email",
            "first_name",
            "last_name",
            "role",
            "enabled",
            "is_site_user",
        ]
        lib.log_output(
            tabulate.tabulate(
                [[row[header] for header in headers] for row in users], headers=headers
            )
        )
        lib.log_output()


@main.command("delete")
@click.argument("email", callback=lib.validate_email)
@click.pass_obj
def delete_user(obj, email):
    """Delete user (but *do not* delete any related role)."""
    api = lib.get_api(**obj)
    api.delete_user(email)
