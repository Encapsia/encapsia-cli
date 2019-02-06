"""Run an arbitrary Encapsia task."""
import click
from encapsia_api import EncapsiaApi

from encapsia_cli import lib


@click.command()
@click.argument("namespace")
@click.argument("function")
@click.argument("args", nargs=-1)
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
def main(namespace, function, args, host, host_env_var, token_env_var):
    """Run an arbitrary task in given plugin NAMESPACE and qualified FUNCTION e.g.
    encapsia-task example_namespace test_module.test_function x=3 y=tim "z=hello stranger"

    Note that all args must be named and the values are all considered strings (not
    least because task arguments are encoded over a URL string).

    """
    api = lib.get_api(host, host_env_var, token_env_var)
    params = {}
    for arg in args:
        left, right = arg.split("=", 1)
        params[left.strip()] = right.strip()
    poll, NoTaskResultYet = api.run_task(namespace, function, params)
    result = lib.visual_poll(f"Running task {namespace}", poll, NoTaskResultYet)
    lib.log_output(str(result))
