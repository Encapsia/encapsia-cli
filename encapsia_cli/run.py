"""Run an Encapsia task or view."""
import click

from encapsia_cli import lib

main = lib.make_main(__doc__)


@main.command("task")
@click.argument("namespace")
@click.argument("function")
@click.argument("args", nargs=-1)
@click.pass_obj
def run_task(obj, namespace, function, args):
    """Run a task in given plugin NAMESPACE and FUNCTION with ARGS.

    E.g.

    \b
    encapsia run task example_namespace test_module.test_function x=3 y=tim "z=hello stranger"

    Note that all args must be named and the values are all considered strings (not
    least because arguments are encoded over a URL string).

    """
    api = lib.get_api(**obj)
    params = {}
    for arg in args:
        left, right = arg.split("=", 1)
        params[left.strip()] = right.strip()
    lib.run_task(api, namespace, function, params, f"Running task {namespace}")


@main.command("view")
@click.argument("namespace")
@click.argument("function")
@click.argument("args", nargs=-1)
@click.pass_obj
def run_view(obj, namespace, function, args):
    """Run a view in given plugin NAMESPACE and FUNCTION with ARGS.

    e.g.

    \b
    encapsia run view example_namespace test_view 3 tim

    Note that ARGS will be passed in as URL path segments.

    """
    api = lib.get_api(**obj)
    result = api.get(["view", namespace, function] + list(args))
    lib.pretty_print(result, "json")
