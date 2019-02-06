"""Create a superuser e.g. for bootstrapping."""
import re

import click
from encapsia_api import EncapsiaApi

from encapsia_cli import lib

# See http://www.regular-expressions.info/email.html
EMAIL_REGEX = re.compile(r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$")


def validate_email(ctx, param, value):
    if not EMAIL_REGEX.match(value):
        raise click.BadParameter("Not a valid email address")
    return value


@click.command()
@click.argument("email", callback=validate_email)
@click.argument("first_name")
@click.argument("last_name")
@click.option(
    "--host", help="Name to use to lookup credentials in .encapsia/credentials.toml"
)
@click.option(
    "--host-env-var",
    default="ENCAPSIA_HOST",
    help="Environment variable containing DNS hostname (default ENCAPSIA_HOST)",
)
@click.option(
    "--token-env-var",
    default="ENCAPSIA_TOKEN",
    help="Environment variable containing server token (default ENCAPSIA_TOKEN)",
)
def main(email, first_name, last_name, host, host_env_var, token_env_var):
    """Create superuser with given name and email.

    In addition to adding the given user, this will also add a Superuser role.

    """
    api = lib.get_api(host, host_env_var, token_env_var)
    api.post(
        "roles",
        json=[
            {"name": "Superuser", "alias": "Superuser", "capabilities": ["superuser"]}
        ],
    )
    api.post(
        "users",
        json=[
            {
                "email": email,
                "first_name": first_name,
                "last_name": last_name,
                "role": "Superuser",
                "enabled": True,
                "is_site_user": False,
            }
        ],
    )
