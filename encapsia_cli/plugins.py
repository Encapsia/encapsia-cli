"""Install, uninstall, create, and update plugins."""
import datetime
import re
import shutil
import sys
import tempfile
import urllib.request
from contextlib import contextmanager
from pathlib import Path

import click
import toml

from encapsia_cli import lib

main = lib.make_main(__doc__, for_plugins=True)


def _fetch_plugin_and_store_in_cache(url, plugins_cache_dir, force=False):
    full_name = url.rsplit("/", 1)[-1]
    m = re.match(r"plugin-([^-]*)-([^-]*).tar.gz", full_name)
    if m:
        output_filename = plugins_cache_dir / full_name
        if not force and output_filename.exists():
            lib.log(f"Found: {output_filename} (Skipping)")
        else:
            filename, headers = urllib.request.urlretrieve(url, tempfile.mkstemp()[1])
            shutil.move(filename, output_filename)
            lib.log(f"Created: {output_filename}")
    else:
        lib.log_error("That doesn't look like a plugin. Aborting!", abort=True)


def _install_plugin(api, filename):
    """Use the API to install plugin directly from a file."""
    if not filename.exists():
        lib.log_error(f"Cannot find plugin: {filename}", abort=True)
    # TODO only upload if not already installed? (unless --force)
    blob_id = api.upload_file_as_blob(filename.as_posix())
    # TODO create plugin entity and pass that in
    # TODO (the pluginsmanager creates the pluginlogs entity)
    lib.log(f"Uploaded {filename} to blob: {blob_id}")
    lib.run_plugins_task(api, "install_plugin", dict(blob_id=blob_id), "Installing")


@main.command()
@click.pass_obj
def info(obj):
    """Provide some information about installed plugins."""
    api = lib.get_api(**obj)
    lib.run_plugins_task(api, "list_namespaces", dict(), "Fetching list of namespaces")


@main.command()
@click.argument("url")
@click.pass_obj
def fetch_from_url(obj, url):
    """Copy a plugin from given URL into the plugin cache."""
    plugins_cache_dir = obj["plugins_cache_dir"]
    force = obj["force"]
    _fetch_plugin_and_store_in_cache(url, plugins_cache_dir, force)


@main.command()
@click.option(
    "--versions", default=None, help="TOML file containing webapp names and versions."
)
@click.argument("plugin_filenames", nargs=-1)
@click.pass_obj
def install(obj, versions, plugin_filenames):
    """Install plugins from files and/or an optional versions.toml file.

    Plugins named directly will be put in the cache before being installed.

    Plugins specified in the versions.toml file will be taken from the cache.

    """
    plugins_cache_dir = obj["plugins_cache_dir"]
    api = lib.get_api(**obj)
    for plugin_filename in plugin_filenames:
        plugin_filename = Path(plugin_filename).resolve()
        _fetch_plugin_and_store_in_cache(
            plugin_filename.as_uri(), plugins_cache_dir, force=True
        )
        _install_plugin(api, plugins_cache_dir / plugin_filename.name)
    if versions:
        versions = Path(versions)
        for name, version in lib.read_toml(versions).items():
            _install_plugin(api, plugins_cache_dir / f"plugin-{name}-{version}.tar.gz")


@main.command()
@click.argument("namespace")
@click.pass_obj
def uninstall(obj, namespace):
    """Uninstall named plugin."""
    if not obj["force"]:
        click.confirm(
            f"Are you sure you want to uninstall the plugin " + \
            f"(delete all!) from namespace {namespace}",
            abort=True,
        )
    api = lib.get_api(**obj)
    lib.run_plugins_task(
        api, "uninstall_plugin", dict(namespace=namespace), f"Uninstalling {namespace}"
    )


class LastUploadedVsModifiedTracker:

    DIRECTORIES = ["tasks", "views", "wheels", "webfiles", "schedules"]

    def __init__(self, directory, reset=False):
        self.directory = directory
        encapsia_directory = directory / ".encapsia"
        encapsia_directory.mkdir(parents=True, exist_ok=True)
        self.filename = encapsia_directory / "last_uploaded_plugin_parts.toml"
        if reset:
            self.make_empty()
        else:
            self.load()

    def make_empty(self):
        self.data = {}
        self.save()

    def load(self):
        if not self.filename.exists():
            self.make_empty()
        else:
            with self.filename.open() as f:
                self.data = toml.load(f)

    def save(self):
        with self.filename.open("w") as f:
            toml.dump(self.data, f)

    def get_modified_directories(self):
        for name in self.DIRECTORIES:
            last_modified = lib.most_recently_modified(self.directory / name)
            if last_modified is not None:
                if name in self.data:
                    if last_modified > self.data[name]:
                        yield Path(name)
                        self.data[name] = datetime.datetime.utcnow()
                else:
                    yield Path(name)
                    self.data[name] = datetime.datetime.utcnow()


class PluginsTaskError(Exception):

    pass


@contextmanager
def get_modified_plugin_directories(directory, reset=False):
    tracker = LastUploadedVsModifiedTracker(directory, reset=reset)
    try:
        yield list(tracker.get_modified_directories())
    except PluginsTaskError:
        pass
    except Exception:
        raise
    else:
        tracker.save()


@main.command("dev-update")
@click.argument("directory", default=".")
@click.pass_obj
def dev_update(obj, directory):
    """Update plugin parts which have changed since previous update.

    Optionally pass in the DIRECTORY of the plugin (defaults to cwd).

    """
    directory = Path(directory)
    plugin_toml_path = directory / "plugin.toml"
    if not plugin_toml_path.exists():
        lib.log_error("Not in a plugin directory.")
        sys.exit(1)

    with get_modified_plugin_directories(
        directory, reset=obj["force"]
    ) as modified_plugin_directories:
        if modified_plugin_directories:
            with lib.temp_directory() as temp_directory:
                shutil.copy(plugin_toml_path, temp_directory)
                for modified_directory in modified_plugin_directories:
                    lib.log(f"Including: {modified_directory}")
                    shutil.copytree(
                        directory / modified_directory,
                        temp_directory / modified_directory,
                    )
                api = lib.get_api(**obj)
                lib.run_plugins_task(
                    api,
                    "dev_update_plugin",
                    dict(),
                    "Uploading to server",
                    data=lib.create_targz_as_bytes(temp_directory),
                )
        else:
            lib.log("Nothing to do.")


@main.command("dev-create-namespace")
@click.argument("namespace")
@click.argument("n_task_workers", default=1)
@click.pass_obj
def dev_create_namespace(obj, namespace, n_task_workers):
    """Create namespace of given name. Only useful during developmment."""
    api = lib.get_api(**obj)
    lib.run_plugins_task(
        api,
        "dev_create_namespace",
        dict(namespace=namespace, n_task_workers=n_task_workers),
        "Creating namespace",
    )


@main.command("dev-destroy-namespace")
@click.argument("namespace")
@click.pass_obj
def dev_destroy_namespace(obj, namespace):
    """Destroy namespace of given name. Only useful during development"""
    api = lib.get_api(**obj)
    lib.run_plugins_task(
        api, "dev_destroy_namespace", dict(namespace=namespace), "Destroying namespace"
    )


def make_plugin_toml_file(filename, name, description, version, created_by):
    obj = dict(
        name=name,
        description=description,
        version=version,
        created_by=created_by,
        n_task_workers=1,
        reset_on_install=True,
    )
    lib.write_toml(filename, obj)


@main.command()
@click.option(
    "--versions",
    type=click.Path(exists=True),
    help="TOML file containing webapp names and versions.",
)
@click.option("--email", prompt="Your email", help="Email creator of the plugins.")
@click.option(
    "--s3-directory", default="ice-webapp-builds", help="Base directory on S3."
)
@click.pass_obj
def build_from_legacy_s3(obj, versions, email, s3_directory):
    """Build plugins from legacy webapps hosted on AWS S3."""
    plugins_cache_dir = obj["plugins_cache_dir"]
    force = obj["force"]
    versions = Path(versions)
    for name, version in lib.read_toml(versions).items():
        output_filename = Path(plugins_cache_dir, f"plugin-{name}-{version}.tar.gz")
        if not force and output_filename.exists():
            lib.log(f"Found: {output_filename} (Skipping)")
        else:
            _download_and_build_plugin_from_s3(
                s3_directory, name, version, email, output_filename
            )
            lib.log(f"Created: {output_filename}")


def _download_and_build_plugin_from_s3(
    s3_directory, name, version, email, output_filename
):
    with lib.temp_directory() as temp_directory:
        base_dir = temp_directory / f"plugin-{name}-{version}"
        base_dir.mkdir()

        # Download everything from S3 into the webfiles folder.
        # (we will move out the views and tasks if present).
        files_directory = base_dir / "webfiles"
        files_directory.mkdir()
        lib.run(
            "aws",
            "s3",
            "cp",
            f"s3://{s3_directory}/{name}/{version}",
            files_directory.as_posix(),
            "--recursive",
        )

        # Move out the views if they exist.
        views_directory = files_directory / "views"
        if views_directory.exists():
            views_directory.rename(base_dir / "views")

        # Move out the wheels if they exist.
        wheels_directory = files_directory / "tasks/wheels"
        if wheels_directory.exists():
            wheels_directory.rename(base_dir / "wheels")

        # Move out the tasks if they exist.
        tasks_directory = files_directory / "tasks"
        if tasks_directory.exists():
            tasks_directory.rename(base_dir / "tasks")

        # Create a plugin.toml manifest.
        make_plugin_toml_file(
            base_dir / "plugin.toml", name, f"Webapp {name}", version, email
        )

        # Convert all into tar.gz
        lib.create_targz(base_dir, output_filename)


@main.command()
@click.argument("sources", nargs=-1)
@click.pass_obj
def build_from_src(obj, sources):
    """Build plugins from given source directories."""
    plugins_cache_dir = obj["plugins_cache_dir"]
    force = obj["force"]
    for source_directory in sources:
        source_directory = Path(source_directory)
        manifest = lib.read_toml(source_directory / "plugin.toml")
        name = manifest["name"]
        version = manifest["version"]
        output_filename = plugins_cache_dir / f"plugin-{name}-{version}.tar.gz"
        if not force and output_filename.exists():
            lib.log(f"Found: {output_filename} (Skipping)")
        else:
            with lib.temp_directory() as temp_directory:
                base_dir = temp_directory / f"plugin-{name}-{version}"
                base_dir.mkdir()
                for t in (
                    "webfiles",
                    "views",
                    "tasks",
                    "wheels",
                    "schedules",
                    "plugin.toml",
                ):
                    source_t = source_directory / t
                    if source_t.exists():
                        if source_t.is_file():
                            shutil.copy(source_t, base_dir / t)
                        else:
                            shutil.copytree(source_t, base_dir / t)
                lib.create_targz(base_dir, output_filename)
                lib.log(f"Created: {output_filename}")
