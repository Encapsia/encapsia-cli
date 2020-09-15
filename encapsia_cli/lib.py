import contextlib
import datetime
import io
import json
import pathlib
import re
import shutil
import subprocess
import tarfile
import tempfile
import time

import click
import encapsia_api
import toml


def log(message="", nl=True):
    click.secho(message, fg="yellow", nl=nl)


def log_output(message=""):
    click.secho(message, fg="green")


def log_error(message="", abort=False):
    click.secho(message, fg="red", err=True)
    if abort:
        raise click.Abort()


def pretty_print(obj, format, output=None):
    if format == "json":
        formatted = json.dumps(obj, sort_keys=True, indent=4).strip()
    elif format == "toml":
        formatted = toml.dumps(obj)
    if output is None:
        log_output(formatted)
    else:
        output.write(formatted)


def get_api(**obj):
    host = obj.get("host")
    if host is None:
        log_error("Unable to determine host.")
        log_error(
            "Please specify via the command line, env variable, or ~/.encapsia/config.toml file.",
            abort=True,
        )
    try:
        url, token = encapsia_api.discover_credentials(obj["host"])
    except encapsia_api.EncapsiaApiError as e:
        log_error(str(e), abort=True)
    return encapsia_api.EncapsiaApi(url, token)


def add_docstring(value):
    """Decorator to add a docstring to a function."""

    def _doc(func):
        func.__doc__ = value
        return func

    return _doc


# See http://www.regular-expressions.info/email.html
EMAIL_REGEX = re.compile(r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$")


def validate_email(ctx, param, value):
    if not EMAIL_REGEX.match(value):
        raise click.BadParameter("Not a valid email address")
    return value


def get_utc_now_as_iso8601():
    return str(datetime.datetime.utcnow())


@contextlib.contextmanager
def temp_directory():
    """Context manager for creating a temporary directory.

    Cleans up afterwards.

    """
    directory = tempfile.mkdtemp()
    try:
        yield pathlib.Path(directory)
    finally:
        shutil.rmtree(directory)


def most_recently_modified(directory):
    """Return datetime of most recently changed file in directory."""
    files = list(directory.glob("**/*.*"))
    if files:
        return datetime.datetime.utcfromtimestamp(max(t.stat().st_mtime for t in files))
    else:
        return None


def run(*args, **kwargs):
    """Run external command."""
    return subprocess.check_output(args, stderr=subprocess.STDOUT, **kwargs)


def read_toml(filename):
    with filename.open() as f:
        return toml.load(f)


def write_toml(filename, obj):
    with filename.open("w") as f:
        toml.dump(obj, f)


def create_targz(directory, filename):
    with tarfile.open(filename, "w:gz") as tar:
        tar.add(directory, arcname=directory.name)


def create_targz_as_bytes(directory):
    data = io.BytesIO()
    with tarfile.open(mode="w:gz", fileobj=data) as tar:
        tar.add(directory, arcname=directory.name)
    return data.getvalue()


def extract_targz(filename, directory):
    with tarfile.open(filename) as tar:
        tar.extractall(directory)


def parse(obj, format):
    if format == "json":
        return json.loads(obj)
    elif format == "toml":
        return toml.loads(obj)


def visual_poll(message, poll, NoTaskResultYet, wait=0.2):
    log(message, nl=False)
    result = poll()
    count = 0
    while result is NoTaskResultYet:
        time.sleep(wait)
        log(".", nl=False)
        count += 1
        result = poll()
    if count < 3:
        log("." * (3 - count), nl=False)
    log("Done")
    return result


def run_task(api, namespace, name, params, message, upload=None, download=None):
    """Return the raw json result or log (HTTP) error and abort."""
    poll, NoTaskResultYet = api.run_task(
        namespace, name, params, upload=upload, download=download
    )
    try:
        return visual_poll(message, poll, NoTaskResultYet)
    except encapsia_api.EncapsiaApiFailedTaskError as e:
        result = e.payload
        log_error(f"\nStatus: {result['status']}")
        log_error(result.get("exc_info"), abort=True)


def run_plugins_task(api, name, params, message, data=None, print_output=True):
    """Log the result from pluginmanager, which will either be successful or not."""
    reply = run_task(
        api,
        "pluginsmanager",
        "icepluginsmanager.{}".format(name),
        params,
        message,
        upload=data,
    )
    if reply["status"] == "ok":
        if print_output:
            log_output(reply["output"].strip())
        return True
    else:
        log_error(f"Status: {reply['status']}")
        log_error(reply["output"].strip())
        return False


def run_job(api, namespace, function, params, message, upload=None, download=None):
    """Run job, wait for it to complete, and log all joblogs; or log error from task."""
    poll, NoResultYet = api.run_job(
        namespace, function, params, upload=upload, download=download
    )
    try:
        return visual_poll(message, poll, NoResultYet)
    except encapsia_api.EncapsiaApiFailedTaskError as e:
        result = e.payload
        log_error(f"\nStatus: {result['status']}")
        log_error(result.get("exc_info"), abort=True)


def dbctl_action(api, name, params, message):
    poll, NoTaskResultYet = api.dbctl_action(name, params)
    result = visual_poll(message, poll, NoTaskResultYet)
    if result["status"] != "ok":
        raise click.Abort()
    return result["result"]
