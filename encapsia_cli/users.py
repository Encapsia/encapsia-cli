"""Manage users, including superuser and system users."""
from pathlib import Path

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


@main.command("export")
@click.argument(
    "filename", type=click.Path(writable=True, readable=False), required=True
)
@click.option("--with-roles/--without-roles", default=True)
@click.pass_obj
def export_users_and_roles(obj, filename, with_roles):
    """Export users (and roles) to given TOML file."""
    filename = Path(filename)
    api = lib.get_api(**obj)
    export_data = {}
    export_data["users"] = api.get_all_users()
    if with_roles:
        export_data["roles"] = api.get_all_roles()
    with filename.open(mode="w") as f:
        lib.pretty_print(export_data, "toml", f)
        lib.log_output(
            f"Exported {len(export_data['users'])} users and {len(export_data.get('roles', []))} roles to {filename}"
        )


@main.command("import")
@click.argument(
    "filename", type=click.Path(writable=False, readable=True), required=True
)
@click.pass_obj
def import_users_and_roles(obj, filename):
    """Import users (and roles) from given TOML file."""
    filename = Path(filename)
    api = lib.get_api(**obj)
    import_data = lib.read_toml(filename)
    users = import_data.get("users", [])
    roles = import_data.get("roles", [])
    if users:
        api.post("users", json=users)
    if roles:
        api.post("roles", json=roles)
    lib.log_output(
        f"Imported {len(users)} users and {len(roles)} roles from {filename}"
    )
