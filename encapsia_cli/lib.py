import contextlib
import datetime
import io
import json
import os
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


def discover_credentials(name, host_env_var, token_env_var):
    if name:
        store = CredentialsStore()
        try:
            host, token = store.get(name)
        except KeyError:
            error(f"Cannot find entry for '{name}' in encapsia credentials file.")
            raise click.Abort()
    else:
        host, token = get_env_var(host_env_var), get_env_var(token_env_var)
    return host, token


def get_api(name, host_env_var, token_env_var):
    host, token = discover_credentials(name, host_env_var, token_env_var)
    return EncapsiaApi(host, token)


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


def create_targz(directory, filename):
    with tarfile.open(filename, "w:gz") as tar:
        tar.add(directory, arcname=directory.name)


def create_targz_as_bytes(directory):
    data = io.BytesIO()
    with tarfile.open(mode="w:gz", fileobj=data) as tar:
        tar.add(directory, arcname=directory.name)
    return data.getvalue()


def pretty_print(obj, format="toml", output=None):
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


def run_plugins_task(host, token, name, params, message, data=None):
    api = EncapsiaApi(host, token)
    poll, NoTaskResultYet = api.run_task(
        "pluginsmanager", "icepluginsmanager.{}".format(name), params, data
    )
    result = visual_poll(message, poll, NoTaskResultYet)
    log_output(result["output"].strip())
    if result["status"] != "ok":
        raise click.Abort()
