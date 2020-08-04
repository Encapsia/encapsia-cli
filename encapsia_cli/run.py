"""Run an Encapsia task, job, or view."""
import json

import click
from encapsia_api import FileDownloadResponse

from encapsia_cli import lib

main = lib.make_main(__doc__)


def _log_result(result):
    """Pretty-print log the result from running a task, job, or view."""
    if isinstance(result, FileDownloadResponse):
        lib.log(f"Response saved to: {result.filename} (mime_type={result.mime_type})")
    else:
        try:
            # Try to pretty print if it converts to JSON.
            lib.pretty_print(result, "json")
        except json.decoder.JSONDecodeError:
            # Otherwise print normally.
            lib.log_output(str(result))


@main.command("task")
@click.argument("namespace")
@click.argument("function")
@click.argument("args", nargs=-1)
@click.option(
    "--upload",
    type=click.File("rb"),
    help="Name of file to upload and hence pass to the task",
)
@click.option(
    "--save-as",
    type=click.Path(readable=False),
    help="Name of file in which to save result",
)
@click.pass_obj
def run_task(obj, namespace, function, args, upload, save_as):
    """Run a task in given plugin NAMESPACE and FUNCTION with ARGS.

    E.g.

    \b
    encapsia run task example_namespace test_module.test_function x=3 y=tim

    Note that all args must be named and the values are all considered strings (not
    least because arguments are encoded over a URL string).

    """
    api = lib.get_api(**obj)
    params = {}
    for arg in args:
        left, right = arg.split("=", 1)
        params[left.strip()] = right.strip()
    result = lib.run_task(
        api,
        namespace,
        function,
        params,
        f"Running task {namespace}",
        upload=upload,
        download=save_as,
    )
    _log_result(result)


@main.command("job")
@click.argument("namespace")
@click.argument("function")
@click.argument("args", nargs=-1)
@click.option(
    "--upload",
    type=click.File("rb"),
    help="Name of file to upload and hence pass to the job",
)
@click.option(
    "--save-as",
    type=click.Path(readable=False),
    help="Name of file in which to save result",
)
@click.pass_obj
def run_job(obj, namespace, function, args, upload, save_as):
    """Run a job in given plugin NAMESPACE and FUNCTION with ARGS.

    E.g.

    \b
    encapsia run job example_namespace test_module.test_function x=3 y=tim "z=hello"

    Note that all args must be named and the values are all considered strings (not
    least because arguments are encoded over a URL string).

    """
    api = lib.get_api(**obj)
    params = {}
    for arg in args:
        left, right = arg.split("=", 1)
        params[left.strip()] = right.strip()
    result = lib.run_job(
        api,
        namespace,
        function,
        params,
        f"Running job {namespace}",
        upload=upload,
        download=save_as,
    )
    _log_result(result)


@main.command("view")
@click.argument("namespace")
@click.argument("function")
@click.argument("args", nargs=-1)
@click.option(
    "--post",
    is_flag=True,
    help="Use POST instead of GET (for view functions that change the database or create temp view etc)",
)
@click.option(
    "--upload",
    type=click.File("rb"),
    help="Name of file to upload and hence pass to the view",
)
@click.option(
    "--save-as",
    type=click.Path(readable=False),
    help="Name of file in which to save result",
)
@click.pass_obj
def run_view(obj, namespace, function, args, post, upload, save_as):
    """Run a view in given plugin NAMESPACE and FUNCTION with ARGS.

    e.g.

    \b
    encapsia run view example_namespace test_view 3 tim limit=45

    If an ARGS contains an "=" sign then send it as an optional query string argument.
    Otherwise send it as a URL path segment.

    """
    api = lib.get_api(**obj)
    query_args = {}
    path_segments = []
    for arg in args:
        if "=" in arg:
            left, right = arg.split("=", 1)
            query_args[left] = right
        else:
            path_segments.append(arg)

    result = api.run_view(
        namespace,
        function,
        view_arguments=path_segments,
        view_options=query_args,
        use_post=post,
        upload=upload,
        download=save_as,
    )
    _log_result(result)
