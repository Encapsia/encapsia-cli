import contextlib
import datetime
import io
import json
import os
import re
import shutil
import subprocess
import tarfile
import tempfile
import time
from pathlib import Path

import click
import toml
from encapsia_api import CredentialsStore, EncapsiaApi


def error(message):
    click.secho(message, fg="red")


def log(message, nl=True):
    click.secho(message, fg="yellow", nl=nl)


def log_output(message):
    click.secho(message, fg="green")


def get_env_var(name):
    try:
        return os.environ[name]
    except KeyError:
        error("Environment variable {} does not exist!".format(name))
        raise click.Abort()


def discover_credentials(host, hostname_env_var, token_env_var):
    if host:
        store = CredentialsStore()
        try:
            hostname, token = store.get(host)
        except KeyError:
            error(f"Cannot find entry for '{host}' in encapsia credentials file.")
            raise click.Abort()
    else:
        hostname, token = get_env_var(hostname_env_var), get_env_var(token_env_var)
    return hostname, token


def get_api(**obj):
    hostname, token = discover_credentials(obj["host"], obj["hostname_env_var"], obj["token_env_var"])
    return EncapsiaApi(hostname, token)


def add_docstring(value):
    """Decorator to add a docstring to a function."""
    def _doc(func):
        func.__doc__ = value
        return func
    return _doc


def make_main(docstring):
    @click.group()
    @click.option(
        "--host", help="Name to use to lookup credentials in .encapsia/credentials.toml"
    )
    @click.option(
        "--hostname-env-var",
        default="ENCAPSIA_HOSTNAME",
        show_default=True,
        help="Environment variable containing DNS hostname",
    )
    @click.option(
        "--token-env-var",
        default="ENCAPSIA_TOKEN",
        show_default=True,
        help="Environment variable containing server token",
    )
    @click.pass_context
    @add_docstring(docstring)
    def main(ctx, host, hostname_env_var, token_env_var):
        ctx.obj = dict(host=host, hostname_env_var=hostname_env_var, token_env_var=token_env_var)

    return main



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
        yield Path(directory)
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


def pretty_print(obj, format, output=None):
    if format == "json":
        formatted = json.dumps(obj, sort_keys=True, indent=4).strip()
    elif format == "toml":
        formatted = toml.dumps(obj)
    if output is None:
        click.echo(formatted)
    else:
        output.write(formatted)


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


def run_task(api, namespace, name, params, message, data=None):
    poll, NoTaskResultYet = api.run_task(
        namespace, name, params, data
    )
    result = visual_poll(message, poll, NoTaskResultYet)
    log_output(result["output"].strip())
    if result["status"] != "ok":
        raise click.Abort()


def run_plugins_task(api, name, params, message, data=None):
    run_task(api, "pluginsmanager", "icepluginsmanager.{}".format(name), params, message, data)


def dbctl_action(api, name, params, message):
    poll, NoTaskResultYet = api.dbctl_action(name, params)
    result = visual_poll(message, poll, NoTaskResultYet)
    if result["status"] != "ok":
        raise click.Abort()
    return result["result"]